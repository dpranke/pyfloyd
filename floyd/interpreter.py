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

from floyd import parser


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
        self.memoize = memoize
        self.grammar = grammar

        self.text = None
        self.path = None
        self.failed = False
        self.val = None
        self.pos = 0
        self.end = -1
        self.errstr = 'Error: uninitialized'
        self.errpos = 0
        self.cache = {}
        self.scopes = []
        self.seeds = {}
        self.blocked = set()
        self.operators = {}
        self.regexps = {}

    def parse(self, text: str, path: str = '<string>') -> parser.Result:
        self.text = text
        self.path = path
        self.failed = False
        self.val = None
        self.pos = 0
        self.end = len(self.text)
        self.errstr = None
        self.errpos = 0
        self.scopes = []

        self._interpret(self.grammar.rules[self.grammar.starting_rule])
        if self.failed:
            return self._format_error()
        return parser.Result(self.val, None, self.pos)

    def _interpret(self, node):
        node_handler = getattr(self, f'_ty_{node[0]}', None)
        assert node_handler, f"Unimplemented node type '{node[0]}'"
        node_handler(node)

    def _fail(self, errstr=None):
        self.failed = True
        self.val = None
        if self.pos >= self.errpos:
            self.errpos = self.pos
            self.errstr = errstr

    def _succeed(self, val=None, newpos=None):
        self.val = val
        self.failed = False
        self.errstr = None
        if newpos is not None:
            self.pos = newpos

    def _rewind(self, newpos):
        self._succeed(None, newpos)

    def _format_error(self):
        lineno = 1
        colno = 1
        for ch in self.text[: self.errpos]:
            if ch == '\n':
                lineno += 1
                colno = 1
            else:
                colno += 1
        if not self.errstr:
            if self.errpos == len(self.text):
                thing = 'end of input'
            else:
                thing = repr(self.text[self.errpos]).replace("'", '"')
            self.errstr = 'Unexpected %s at column %d' % (thing, colno)

        msg = '%s:%d %s' % (self.path, lineno, self.errstr)
        return parser.Result(None, msg, self.errpos)

    def _r_any(self):
        if self.pos != self.end:
            self._succeed(self.text[self.pos], self.pos + 1)
            return
        self._fail()

    def _r_end(self):
        if self.pos != self.end:
            self._fail()
            return
        self._succeed()

    def _ty_action(self, node):
        self._interpret(node[2][0])

    def _ty_apply(self, node):
        rule_name = node[1]
        if rule_name == 'any':
            self._r_any()
            return

        if rule_name == 'end':
            self._r_end()
            return

        # Unknown rules should have been caught in analysis, so we don't
        # need to worry about one here and can jump straight to the rule.
        pos = self.pos
        if self.memoize:
            r = self.cache.get((rule_name, pos))
            if r is not None:
                self.val, self.failed, self.pos = r
                return
        self._interpret(self.grammar.rules[rule_name])
        if self.memoize:
            self.cache[(rule_name, pos)] = self.val, self.failed, self.pos

    def _ty_choice(self, node):
        count = 1
        pos = self.pos
        for rule in node[2][:-1]:
            self._interpret(rule)
            if not self.failed:
                return
            self._rewind(pos)
            count += 1
        self._interpret(node[2][-1])
        return

    def _ty_count(self, node):
        vs = []
        i = 0
        cmin, cmax = node[1]
        while i < cmax:
            self._interpret(node[2][0])
            if self.failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self.val)
            i += 1
        self._succeed(vs)

    def _ty_empty(self, node):
        del node
        self._succeed()

    def _ty_ends_in(self, node):
        while True:
            self._interpret(node[2][0])
            if not self.failed:
                return
            self._ty_apply(['apply', 'any', []])
            if self.failed:
                return

    def _ty_label(self, node):
        self._interpret(node[2][0])
        if not self.failed:
            self.scopes[-1][node[1]] = self.val
            self._succeed()

    def _ty_leftrec(self, node):
        # This approach to handling left-recursion is based on the approach
        # described in "Parsing Expression Grammars Made Practical" by
        # Laurent and Mens, 2016.
        pos = self.pos
        rule_name = node[1]
        assoc = self.grammar.assoc.get(rule_name, 'left')
        key = (rule_name, pos)
        seed = self.seeds.get(key)
        if seed:
            self.val, self.failed, self.pos = seed
            return
        if rule_name in self.blocked:
            self.val = None
            self.failed = True
            return
        current = (None, True, self.pos)
        self.seeds[key] = current
        if assoc == 'left':
            self.blocked.add(rule_name)
        while True:
            self._interpret(node[2][0])
            if self.pos > current[2]:
                current = (self.val, self.failed, self.pos)
                self.seeds[key] = current
                self.pos = pos
            else:
                del self.seeds[key]
                self.val, self.failed, self.pos = current
                if assoc == 'left':
                    self.blocked.remove(rule_name)
                return

    def _ty_lit(self, node):
        i = 0
        lit = node[1]
        lit_len = len(lit)
        pos = self.pos
        while (
            i < lit_len
            and self.pos < self.end
            and self.text[self.pos] == lit[i]
        ):
            self.pos += 1
            i += 1
        if i == lit_len:
            self._succeed(self.text[pos : self.pos])
        else:
            self._fail()

    def _ty_not_one(self, node):
        self._ty_not(['not', None, node[2]])
        if not self.failed:
            self._ty_apply(['apply', 'any', []])

    def _ty_run(self, node):
        start = self.pos
        self._interpret(node[2][0])
        if self.failed:
            return
        end = self.pos
        self.val = self.text[start:end]

    def _ty_unicat(self, node):
        p = self.pos
        if p < self.end and unicodedata.category(self.text[p]) == node[1]:
            self._succeed(self.text[p], newpos=p + 1)
        else:
            self._fail()

    def _ty_ll_arr(self, node):
        vals = []
        for subnode in node[2]:
            self._interpret(subnode)
            vals.append(self.val)
        self._succeed(vals)

    def _ty_ll_call(self, node):
        vals = []
        for subnode in node[2]:
            self._interpret(subnode)
            vals.append(self.val)
        # Return 'll_call' as a tag here so we can check it in ll_qual.
        self._succeed(['ll_call', vals])

    def _ty_ll_const(self, node):
        if node[1] == 'true':
            self._succeed(True)
        elif node[1] == 'false':
            self._succeed(False)
        elif node[1] == 'null':
            self._succeed(None)
        elif node[1] == 'Infinity':
            self._succeed(float('inf'))
        else:
            assert node[1] == 'NaN'
            self._succeed(float('NaN'))

    def _ty_ll_getitem(self, node):
        self._interpret(node[2][0])
        assert not self.failed
        # Return 'll_getitem' as a tag here so we can check it in ll_qual.
        self._succeed(['ll_getitem', self.val])

    def _ty_ll_minus(self, node):
        self._interpret(node[2][0])
        v1 = self.val
        self._interpret(node[2][1])
        v2 = self.val
        self._succeed(v1 - v2)

    def _ty_ll_num(self, node):
        if node[1].startswith('0x'):
            self._succeed(int(node[1], base=16))
        else:
            self._succeed(int(node[1]))

    def _ty_ll_paren(self, node):
        self._interpret(node[2][0])

    def _ty_ll_plus(self, node):
        self._interpret(node[2][0])
        v1 = self.val
        self._interpret(node[2][1])
        v2 = self.val
        self._succeed(v1 + v2)

    def _ty_ll_qual(self, node):
        # TODO: is it possible for this to fail?
        self._interpret(node[2][0])
        assert not self.failed
        for n in node[2][1:]:
            lhs = self.val
            # TODO: is it possible for this to fail?
            self._interpret(n)
            assert not self.failed
            op, rhs = self.val
            if op == 'll_getitem':
                self.val = lhs[rhs]
            else:
                assert op == 'll_call'
                # Note that unknown functions were caught during analysis
                # so it's safe to dereference this without checking.
                fn = getattr(self, '_fn_' + lhs, None)
                self.val = fn(*rhs)

    def _ty_ll_lit(self, node):
        self._succeed(node[1])

    def _ty_ll_var(self, node):
        v = getattr(self, '_fn_' + node[1], None)
        if v:
            self._succeed(node[1])
            return

        # Unknown variables should have been caught in analysis.
        assert self.scopes and (node[1] in self.scopes[-1])
        self._succeed(self.scopes[-1][node[1]])

    def _ty_not(self, node):
        pos = self.pos
        val = self.val
        self._interpret(node[2][0])
        if self.failed:
            self._succeed(val, newpos=pos)
        else:
            self.pos = pos
            self._fail(val)

    def _ty_operator(self, node):
        pos = self.pos
        rule_name = node[1]
        key = (rule_name, self.pos)
        seed = self.seeds.get(key)
        if seed:
            self.val, self.failed, self.pos = seed
            return

        o = self.operators.get(node[1])
        if o is None:
            o = _OperatorState()
            for op_node in node[2]:
                op, prec = op_node[1]
                o.prec_ops.setdefault(prec, []).append(op)
                if self.grammar.assoc.get(op) == 'right':
                    o.rassoc.add(op)
                o.choices[op] = op_node[2]
            o.precs = sorted(o.prec_ops, reverse=True)
            self.operators[node[1]] = o

        o.current_depth += 1
        current = (None, True, self.pos)
        self.seeds[key] = current
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
                if not self.failed and self.pos > pos:
                    current = (self.val, self.failed, self.pos)
                    self.seeds[key] = current
                    repeat = True
                    break
                self._rewind(pos)
            if not repeat:
                i += 1
        del self.seeds[key]
        o.current_depth -= 1
        if o.current_depth == 0:
            o.current_prec = 0
        self.val, self.failed, self.pos = current

    def _ty_opt(self, node):
        pos = self.pos
        self._interpret(node[2][0])
        if self.failed:
            self.failed = False
            self.val = []
            self.pos = pos
        else:
            self.val = [self.val]

    def _ty_paren(self, node):
        self._interpret(node[2][0])

    def _ty_plus(self, node):
        self._interpret(node[2][0])
        hd = self.val
        if not self.failed:
            self._ty_star(node)
            self.val = [hd] + self.val

    def _ty_pred(self, node):
        self._interpret(node[2][0])
        if self.val is True:
            self._succeed(True)
        elif self.val is False:
            self.val = False
            self._fail()
        else:
            # TODO: Figure out how to statically analyze predicates to
            # catch ones that don't return booleans, so that we don't need
            # this code path.
            self._fail('Bad predicate value')

    def _ty_range(self, node):
        if (
            self.pos != self.end
            and node[1][0] <= self.text[self.pos] <= node[1][1]
        ):
            self._succeed(self.text[self.pos], self.pos + 1)
            return
        self._fail()

    def _ty_regexp(self, node):
        if node[1] not in self.regexps:
            self.regexps[node[1]] = re.compile(node[1])
        m = self.regexps[node[1]].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _ty_seq(self, node):
        self.scopes.append({})
        for subnode in node[2]:
            self._interpret(subnode)
            if self.failed:
                break
        self.scopes.pop()

    def _ty_set(self, node):
        new_node = ['regexp', '[' + node[1] + ']', []]
        self._interpret(new_node)

    def _ty_star(self, node):
        vs = []
        while not self.failed and self.pos < self.end:
            p = self.pos
            self._interpret(node[2][0])
            if self.failed:
                self._rewind(p)
                break
            if self.pos == p:
                # We didn't actually consume anything, so break out so
                # that we don't get stuck in an infinite loop.
                break
            vs.append(self.val)
        self._succeed(vs)

    def _fn_atoi(self, val):
        return int(val, base=10)

    def _fn_cat(self, val):
        return ''.join(val)

    def _fn_concat(self, xs, ys):
        return xs + ys

    def _fn_cons(self, hd, tl):
        return [hd] + tl

    def _fn_dict(self, val):
        return dict(val)

    def _fn_float(self, val):
        if '.' in val or 'e' in val or 'E' in val:
            return float(val)
        return int(val)

    def _fn_hex(self, val):
        return int(val, base=16)

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

    def _fn_xtoi(self, val):
        return int(val, base=16)

    def _fn_xtou(self, val):
        return chr(int(val, base=16))
