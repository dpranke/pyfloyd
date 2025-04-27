# Copyright 2024 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import unicodedata

from pyfloyd.ast import Apply, Not, Regexp
from pyfloyd import parser


class _OperatorState:
    def __init__(self):
        self.current_depth = 0
        self.current_prec = 0
        self.prec_ops = {}
        self.precs = []
        self.rassoc = set()
        self.choices = {}


class Interpreter:
    def __init__(self, grammar, memoize):
        self._memoize = memoize
        self._grammar = grammar

        self._text = None
        self._path = None
        self._failed = False
        self._val = None
        self._pos = 0
        self._end = -1
        self._errstr = 'Error: uninitialized'
        self._errpos = 0
        self._cache = {}
        self._scopes = []
        self._seeds = {}
        self._blocked = set()
        self._operators = {}
        self._regexps = {}
        self._externs = grammar.externs

    def parse(
        self, text: str, path: str = '<string>', externs=None
    ) -> parser.Result:
        self._text = text
        self._path = path
        self._failed = False
        self._val = None
        self._pos = 0
        self._end = len(self._text)
        self._errstr = None
        self._errpos = 0
        self._scopes = [{}]

        errors = ''
        if externs:
            for k, v in externs.items():
                if k in self._externs:
                    self._externs[k] = v
                else:
                    errors += f'Missing extern "{k}"\n'
        if errors:
            return parser.Result(None, errors.strip(), 0)

        self._interpret(self._grammar.rules[self._grammar.starting_rule])
        if self._failed:
            return self._format_error()
        return parser.Result(self._val, None, self._pos)

    def _interpret(self, node):
        node_handler = getattr(self, f'_ty_{node.t}', None)
        assert node_handler, f"Unimplemented node type '{node.t}'"
        node_handler(node)

    def _fail(self, errstr=None):
        self._failed = True
        self._val = None
        if self._pos >= self._errpos:
            self._errpos = self._pos
            self._errstr = errstr

    def _str(self, s):
        s_len = len(s)
        pos = self._pos
        i = 0
        while (
            i < s_len
            and self._pos < self._end
            and self._text[self._pos] == s[i]
        ):
            self._pos += 1
            i += 1
        if i == s_len:
            self._succeed(self._text[pos : self._pos])
        else:
            self._fail()

    def _succeed(self, val=None, newpos=None):
        self._val = val
        self._failed = False
        self._errstr = None
        if newpos is not None:
            self._pos = newpos

    def _rewind(self, newpos):
        self._succeed(None, newpos)

    def _format_error(self):
        lineno = 1
        colno = 1
        for ch in self._text[: self._errpos]:
            if ch == '\n':
                lineno += 1
                colno = 1
            else:
                colno += 1
        if not self._errstr:
            if self._errpos == len(self._text):
                thing = 'end of input'
            else:
                thing = repr(self._text[self._errpos]).replace("'", '"')
            self._errstr = 'Unexpected %s at column %d' % (thing, colno)

        msg = '%s:%d %s' % (self._path, lineno, self._errstr)
        return parser.Result(None, msg, self._errpos)

    def _r_any(self):
        if self._pos != self._end:
            self._succeed(self._text[self._pos], self._pos + 1)
            return
        self._fail()

    def _r_end(self):
        if self._pos != self._end:
            self._fail()
            return
        self._succeed()

    def _ty_action(self, node):
        self._interpret(node.child)

    def _ty_apply(self, node):
        rule_name = node.rule_name
        if rule_name == 'any':
            self._r_any()
            return

        if rule_name == 'end':
            self._r_end()
            return

        # Unknown rules should have been caught in analysis, so we don't
        # need to worry about one here and can jump straight to the rule.

        # Start each rule w/ a fresh set of scopes.
        scopes = self._scopes
        self._scopes = [{}]

        pos = self._pos
        if self._memoize:
            r = self._cache.get((rule_name, pos))
            if r is not None:
                self._val, self._failed, self._pos = r
                self._scopes = scopes
                return
        self._interpret(self._grammar.rules[rule_name])
        if self._memoize:
            self._cache[(rule_name, pos)] = self._val, self._failed, self._pos
        self._scopes = scopes

    def _ty_choice(self, node):
        count = 1
        pos = self._pos
        for rule in node.ch[:-1]:
            self._interpret(rule)
            if not self._failed:
                return
            self._rewind(pos)
            count += 1
        self._interpret(node.ch[-1])
        return

    def _ty_count(self, node):
        vs = []
        i = 0
        cmin, cmax = node.start, node.stop
        while i < cmax:
            self._interpret(node.child)
            if self._failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self._val)
            i += 1
        self._succeed(vs)

    def _ty_e_arr(self, node):
        vals = []
        for subnode in node.ch:
            self._interpret(subnode)
            vals.append(self._val)
        self._succeed(vals)

    def _ty_e_call(self, node):
        vals = []
        for subnode in node.ch:
            self._interpret(subnode)
            vals.append(self._val)
        # Return 'e_call' as a tag here so we can check it in e_qual.
        self._succeed(['e_call', vals])

    def _ty_e_const(self, node):
        if node.v == 'true':
            self._succeed(True)
        elif node.v == 'false':
            self._succeed(False)
        elif node.v == 'null':
            self._succeed(None)
        elif node.v == 'Infinity':
            self._succeed(float('inf'))
        else:
            assert node.v == 'NaN'
            self._succeed(float('NaN'))

    def _ty_e_getitem(self, node):
        self._interpret(node.child)
        assert not self._failed
        # Return 'e_getitem' as a tag here so we can check it in e_qual.
        self._succeed(['e_getitem', self._val])

    def _ty_e_lit(self, node):
        self._succeed(node.v)

    def _ty_e_minus(self, node):
        self._interpret(node.ch[0])
        v1 = self._val
        self._interpret(node.ch[1])
        v2 = self._val
        self._succeed(v1 - v2)

    def _ty_e_not(self, node):
        self._interpret(node.child)
        # TODO: Should we be stricter about node.child needing to result
        # in a boolean?
        if self._val:
            self._succeed(False)
        else:
            self._succeed(True)

    def _ty_e_num(self, node):
        if node.v.startswith('0x'):
            self._succeed(int(node.v, base=16))
        else:
            self._succeed(int(node.v))

    def _ty_e_paren(self, node):
        self._interpret(node.child)

    def _ty_e_plus(self, node):
        self._interpret(node.ch[0])
        v1 = self._val
        self._interpret(node.ch[1])
        v2 = self._val
        self._succeed(v1 + v2)

    def _ty_e_qual(self, node):
        # TODO: is it possible for this to fail?
        self._interpret(node.ch[0])
        assert not self._failed
        for n in node.ch[1:]:
            lhs = self._val
            # TODO: is it possible for this to fail?
            self._interpret(n)
            assert not self._failed
            op, rhs = self._val
            if op == 'e_getitem':
                self._val = lhs[rhs]
            else:
                assert op == 'e_call'
                # Note that unknown functions were caught during analysis
                # so it's safe to dereference this without checking.
                fn = getattr(self, '_fn_' + lhs, None)
                self._val = fn(*rhs)

    def _ty_e_var(self, node):
        v = getattr(self, '_fn_' + node.v, None)
        if v:
            self._succeed(node.v)
            return

        # Unknown variables should have been caught in analysis.
        v = node.v
        if v[0] == '$':
            # Look up positional labels in the current scope.
            self._succeed(self._scopes[-1][v])
        else:
            # Look up named labels in any scope.
            i = len(self._scopes) - 1
            while i >= 0:
                if v in self._scopes[i]:
                    self._succeed(self._scopes[i][v])
                    return
                i -= 1
            if v in self._externs:
                self._succeed(self._externs[v])
                return
            assert False, f'Unknown label "{v}"'

    def _ty_empty(self, node):
        del node
        self._succeed()

    def _ty_ends_in(self, node):
        while True:
            self._interpret(node.child)
            if not self._failed:
                return
            self._ty_apply(self._grammar.node(Apply, 'any'))
            if self._failed:
                return

    def _ty_equals(self, node):
        self._interpret(node.child)
        if self._failed:
            # TODO: Should this be even possible?
            return
        self._str(self._val)

    def _ty_label(self, node):
        self._interpret(node.child)
        if not self._failed:
            self._scopes[-1][node.v] = self._val
            self._succeed()

    def _ty_leftrec(self, node):
        # This approach to handling left-recursion is based on the approach
        # described in "Parsing Expression Grammars Made Practical" by
        # Laurent and Mens, 2016.
        pos = self._pos
        rule_name = node.name
        assoc = self._grammar.assoc.get(rule_name, 'left')
        key = (rule_name, pos)
        seed = self._seeds.get(key)
        if seed:
            self._val, self._failed, self._pos = seed
            return
        if rule_name in self._blocked:
            self._val = None
            self._failed = True
            return
        current = (None, True, self._pos)
        self._seeds[key] = current
        if assoc == 'left':
            self._blocked.add(rule_name)
        while True:
            self._interpret(node.child)
            if self._pos > current[2]:
                current = (self._val, self._failed, self._pos)
                self._seeds[key] = current
                self._pos = pos
            else:
                del self._seeds[key]
                self._val, self._failed, self._pos = current
                if assoc == 'left':
                    self._blocked.remove(rule_name)
                return

    def _ty_lit(self, node):
        self._str(node.v)

    def _ty_not(self, node):
        pos = self._pos
        val = self._val
        self._interpret(node.child)
        if self._failed:
            self._succeed(val, newpos=pos)
        else:
            self._pos = pos
            self._fail(val)

    def _ty_not_one(self, node):
        self._ty_not(self._grammar.node(Not, node.child))
        if not self._failed:
            self._ty_apply(self._grammar.node(Apply, 'any'))

    def _ty_operator(self, node):
        pos = self._pos
        rule_name = node.name
        key = (rule_name, self._pos)
        seed = self._seeds.get(key)
        if seed:
            self._val, self._failed, self._pos = seed
            return

        o = self._operators.get(node.name)
        if o is None:
            o = _OperatorState()
            for op_node in node.ch:
                o.prec_ops.setdefault(op_node.prec, []).append(op_node.op)
                if self._grammar.assoc.get(op_node.op) == 'right':
                    o.rassoc.add(op_node.op)
                o.choices[op_node.op] = op_node.ch
            o.precs = sorted(o.prec_ops, reverse=True)
            self._operators[node.name] = o

        o.current_depth += 1
        current = (None, True, self._pos)
        self._seeds[key] = current
        min_prec = o.current_prec
        i = 0
        while i < len(o.precs):
            repeat = False
            prec = o.precs[i]
            if prec < min_prec:
                break
            o.current_prec = prec
            ops = o.prec_ops[prec]
            if ops[0] not in o.rassoc:
                o.current_prec += 1

            for op in ops:
                self._interpret(o.choices[op][0])
                if not self._failed and self._pos > pos:
                    current = (self._val, self._failed, self._pos)
                    self._seeds[key] = current
                    repeat = True
                    break
                self._rewind(pos)
            if not repeat:
                i += 1
        del self._seeds[key]
        o.current_depth -= 1
        if o.current_depth == 0:
            o.current_prec = 0
        self._val, self._failed, self._pos = current

    def _ty_opt(self, node):
        pos = self._pos
        self._interpret(node.child)
        if self._failed:
            self._failed = False
            self._val = []
            self._pos = pos
        else:
            self._val = [self._val]

    def _ty_paren(self, node):
        self._interpret(node.child)

    def _ty_plus(self, node):
        self._interpret(node.child)
        hd = self._val
        if not self._failed:
            self._ty_star(node)
            self._val = [hd] + self._val

    def _ty_pred(self, node):
        self._interpret(node.child)
        if self._val is True:
            self._succeed(True)
        elif self._val is False:
            self._val = False
            self._fail()
        else:
            # TODO: Figure out how to statically analyze predicates to
            # catch ones that don't return booleans, so that we don't need
            # this code path.
            self._fail('Bad predicate value')

    def _ty_range(self, node):
        if (
            self._pos != self._end
            and node.start <= self._text[self._pos] <= node.stop
        ):
            self._succeed(self._text[self._pos], self._pos + 1)
            return
        self._fail()

    def _ty_regexp(self, node):
        if node.v not in self._regexps:
            self._regexps[node.v] = re.compile(node.v)
        m = self._regexps[node.v].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _ty_run(self, node):
        start = self._pos
        self._interpret(node.child)
        if self._failed:
            return
        end = self._pos
        self._val = self._text[start:end]

    def _ty_scope(self, node):
        self._scopes.append({})
        self._interpret(node.child)
        self._scopes.pop()

    def _ty_seq(self, node):
        for subnode in node.ch:
            self._interpret(subnode)
            if self._failed:
                break

    def _ty_set(self, node):
        new_node = self._grammar.node(Regexp, '[' + node.v + ']')
        self._interpret(new_node)

    def _ty_star(self, node):
        vs = []
        while not self._failed and self._pos < self._end:
            p = self._pos
            self._interpret(node.child)
            if self._failed:
                self._rewind(p)
                break
            if self._pos == p:
                # We didn't actually consume anything, so break out so
                # that we don't get stuck in an infinite loop.
                break
            vs.append(self._val)
        self._succeed(vs)

    def _ty_unicat(self, node):
        p = self._pos
        if p < self._end and unicodedata.category(self._text[p]) == node.v:
            self._succeed(self._text[p], newpos=p + 1)
        else:
            self._fail()

    def _fn_atof(self, val):
        if '.' in val or 'e' in val or 'E' in val:
            return float(val)
        return int(val)

    def _fn_atoi(self, val, base):
        return int(val, base=base)

    def _fn_atou(self, val, base):
        return chr(int(val, base))

    def _fn_cat(self, val):
        return ''.join(val)

    def _fn_concat(self, xs, ys):
        return xs + ys

    def _fn_cons(self, hd, tl):
        return [hd] + tl

    def _fn_dedent(self, s):
        return s

    def _fn_dict(self, val):
        return dict(val)

    def _fn_float(self, val):
        return float(val)

    def _fn_int(self, val):
        return int(val)

    def _fn_itou(self, val):
        return chr(val)

    def _fn_join(self, val, vs):
        return val.join(vs)

    def _fn_scat(self, xs):
        return ''.join(xs)

    def _fn_scons(self, hd, tl):
        return [hd] + tl

    def _fn_strcat(self, a, b):
        return a + b

    def _fn_utoi(self, val):
        return ord(val)

    def _fn_xtou(self, s):
        return chr(int(s, base=16))
