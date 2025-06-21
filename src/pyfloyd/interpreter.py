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
from typing import Any
import unicodedata

from pyfloyd import (
    functions,
    grammar as m_grammar,
    grammar_parser,
)


class _OperatorState:
    def __init__(self):
        self.current_depth = 0
        self.current_prec = 0
        self.prec_ops = {}
        self.precs = []
        self.rassoc = set()
        self.choices = {}


class Interpreter:
    def __init__(
        self, grammar: m_grammar.Grammar, memoize: bool, tokenize: bool
    ):
        self._memoize = memoize
        self._tokenize = tokenize
        self._grammar = grammar

        self._text = ''
        self._path = ''
        self._failed = False
        self._val = None
        self._pos = 0
        self._end = -1
        self._errstr = 'Error: uninitialized'
        self._errpos = 0
        self._cache: dict[int, dict[str, Any]] = {}
        self._scopes: list[dict[str, Any]] = []
        self._seeds: dict[str, Any] = {}
        self._blocked: set[str] = set()
        self._operators: dict[str, m_grammar.OperatorState] = {}
        self._regexps: dict[str, re.Pattern] = {}
        self._externs: dict[str, Any] = grammar.externs
        self._functions = functions.ALL
        self._nodes: list[tuple[int, str]] = []
        self._tokens: list[tuple[int, str]] = []
        self._in_token = False

    def parse(
        self, text: str, path: str = '<string>', externs=None
    ) -> grammar_parser.Result:
        self._text = text
        self._path = path
        self._failed = False
        self._val = None
        self._pos = 0
        self._end = len(self._text)
        self._errstr = ''
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
            return grammar_parser.Result(None, errors.strip(), 0)

        try:
            self._interpret(self._grammar.rules[self._grammar.starting_rule])
            if self._failed:
                return self._format_error()
            return grammar_parser.Result(self._val, None, self._pos)
        except functions.UserError as exc:
            return grammar_parser.Result(None, str(exc), self._pos)
        except functions.HostError as exc:
            return grammar_parser.Result(None, str(exc), self._pos)

    def _interpret(self, node):
        fn = getattr(self, f'_ty_{node.t}', None)
        assert fn, f"Unimplemented node type '{node.t}'"
        fn(node)  # pylint: disable=not-callable

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
        self._tok(pos, False)

    def _succeed(self, val=None, newpos=None):
        self._val = val
        self._failed = False
        self._errstr = None
        if newpos is not None:
            self._pos = newpos

    def _rewind(self, newpos):
        self._succeed(None, newpos)
        while self._tokens and self._tokens[-1][0] > newpos:
            self._tokens.pop()

    def _tok(self, pos, in_token):
        if not self._tokenize or (not in_token and self._in_token):
            return
        if not self._failed and self._pos > pos:
            val = (pos, self._text[pos : self._pos])
            if self._tokens and self._tokens[-1][0] == pos:
                assert self._tokens[-1] == val
            else:
                self._tokens.append(val)
        if in_token:
            self._in_token = False

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
            self._errstr = f'Unexpected {thing} at column {colno}'

        msg = f'{self._path}:{lineno} {self._errstr}'
        return grammar_parser.Result(None, msg, self._errpos)

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
        rule_name = node.v
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
        cmin, cmax = node.v
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
        # e_{call,getitem,qual} have been rewritten to e_{call,getitem}_infix.
        del node
        assert False, '`e_call` should never be invoked'

    def _ty_e_call_infix(self, node):
        vals = []
        self._interpret(node.ch[0])
        left = self._val
        vals = []
        for subnode in node.ch[1:]:
            self._interpret(subnode)
            vals.append(self._val)
        if node.ch[0].t == 'e_ident' and node.ch[0].v in self._externs:
            if self._grammar.externs[node.ch[0].v] == 'func':
                self._val = left(*vals)
            else:
                assert self._grammar.externs[node.ch[0].v] == 'pfunc'
                self._val = left(self, *vals)
        else:
            self._val = left(*vals)

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
        # e_{call,getitem,qual} have been rewritten to e_{call,getitem}_infix.
        del node
        assert False, '`e_getitem` should never be invoked'

    def _ty_e_getitem_infix(self, node):
        self._interpret(node.ch[0])
        left = self._val
        self._interpret(node.ch[1])
        right = self._val
        self._val = left[right]

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
        # e_{call,getitem,qual} have been rewritten to e_{call,getitem}_infix.
        del node
        assert False, '`e_qual` should never be invoked'

    def _ty_e_ident(self, node):
        # Unknown variables should have been caught in analysis.
        v = node.v
        if v[0] == '$':
            # Look up positional labels in the current scope.
            self._succeed(self._scopes[-1][v])
            return

        if node.attrs.kind == 'extern':
            self._succeed(self._externs[v])
            return
        if node.attrs.kind == 'function':
            if (
                node.v in self._functions
                and self._functions[node.v]
                and self._functions[node.v]['func']
            ):
                self._succeed(self._functions[node.v]['func'])
                return
            v = getattr(self, '_fn_' + node.v, None)
            if v:
                self._succeed(v)
                return
            assert False, f"Function '{node.v}()' isn't implemented"
        if node.attrs.kind == 'local':
            self._succeed(self._scopes[-1][v])
            return

        # Look up named labels in any scope.
        assert node.attrs.kind == 'outer'
        i = len(self._scopes) - 1
        while i >= 0:
            if v in self._scopes[i]:
                self._succeed(self._scopes[i][v])
                return
            i -= 1
        assert False, f'Unknown label "{v}"'

    def _ty_empty(self, node):
        del node
        self._succeed()

    def _ty_ends_in(self, node):
        while True:
            self._interpret(node.child)
            if not self._failed:
                return
            self._ty_apply(m_grammar.Node('apply', 'any'))
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
        rule_name = node.v
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
        self._ty_not(m_grammar.Node('not', None, [node.child]))
        if not self._failed:
            self._ty_apply(m_grammar.Node('apply', 'any'))

    def _ty_operator(self, node):
        pos = self._pos
        rule_name = node.v
        key = (rule_name, self._pos)
        seed = self._seeds.get(key)
        if seed:
            self._val, self._failed, self._pos = seed
            return

        o = self._operators.get(node.v)
        if o is None:
            o = _OperatorState()
            for op_node in node.ch:
                op = op_node.v[0]
                o.prec_ops.setdefault(op_node.v[1], []).append(op)
                if self._grammar.assoc.get(op) == 'right':
                    o.rassoc.add(op)
                o.choices[op] = op_node.ch
            o.precs = sorted(o.prec_ops, reverse=True)
            self._operators[node.v] = o

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
            and node.v[0] <= self._text[self._pos] <= node.v[1]
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

    def _ty_rule_wrapper(self, node):
        rule_name = node.v
        self._nodes.append((self._pos, rule_name))
        if rule_name in self._grammar.tokens():
            pos = self._pos
            self._in_token = True
        self._interpret(node.child)
        if rule_name in self._grammar.tokens():
            self._tokens.append((pos, self._text[pos : self._pos]))
            self._in_token = False
        self._nodes.pop()

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
        new_node = m_grammar.Node('regexp', '[' + node.v + ']')
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

    def _fn_colno(self) -> int:
        colno = 0
        if self._pos == self._end:
            colno += 1
        while self._pos >= colno and self._text[self._pos - colno] != '\n':
            colno += 1
        return colno

    def _fn_node(self, parser, *args) -> Any:
        del parser
        return args[0]
