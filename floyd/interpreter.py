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

import unicodedata


class Interpreter:
    def __init__(self, grammar, memoize):
        self.memoize = memoize
        self.grammar = grammar
        self.grammar.rules = self.grammar.ast[1]

        self.msg = None
        self.fname = None
        self.failed = False
        self.val = None
        self.pos = 0
        self.end = -1
        self.errstr = 'Error: uninitialized'
        self.errpos = 0
        self.scopes = []

    def parse(self, msg, fname):
        self.msg = msg
        self.fname = fname
        self.failed = False
        self.val = None
        self.pos = 0
        self.end = len(self.msg)
        self.errstr = None
        self.errpos = 0
        self.scopes = []

        cur_node = None
        for node in self.grammar.rules:
            if node[0] == 'rule' and node[1] == self.grammar.starting_rule:
                cur_node = node
                break

        assert cur_node, (
            "Error: unknown starting rule '%s'" % self.grammar.starting_rule
        )

        self._interpret(cur_node[2])
        if self.failed:
            return self._format_error()
        return self.val, None, self.pos

    def _interpret(self, node):
        node_handler = getattr(self, '_handle_' + node[0], None)
        assert node_handler, "Unimplemented node type '%s'" % node[0]
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
        for ch in self.msg[: self.errpos]:
            if ch == '\n':
                lineno += 1
                colno = 1
            else:
                colno += 1
        if not self.errstr:
            if self.errpos == len(self.msg):
                thing = 'end of input'
            else:
                thing = repr(self.msg[self.errpos]).replace("'", '"')
            self.errstr = 'Unexpected %s at column %d' % (thing, colno)

        msg = '%s:%d %s' % (self.fname, lineno, self.errstr)
        return None, msg, self.errpos

    def _handle_action(self, node):
        self._interpret(node[1])

    def _handle_apply(self, node):
        rule_name = node[1]
        if rule_name == 'end':
            self._handle_end()
            return

        if rule_name == 'any':
            if self.pos != self.end:
                self._succeed(self.msg[self.pos], self.pos + 1)
                return

        for rule in self.grammar.rules:
            if rule_name == rule[1]:
                self._interpret(rule[2])
                return

        # TODO: figure out if/when this can actually be reached. Shouldn't
        # this be caught while validating the grammar?
        self._fail("Error: no rule named '%s'" % rule_name)

    def _handle_choice(self, node):
        pos = self.pos
        for rule in node[1][:-1]:
            self._interpret(rule)
            if not self.failed:
                return
            self._rewind(pos)
        self._interpret(node[1][-1])
        return

    def _handle_empty(self, node):
        del node
        self._succeed()

    def _handle_end(self):
        if self.pos != self.end:
            self._fail()
            return
        self._succeed()

    def _handle_label(self, node):
        self._interpret(node[1])
        if not self.failed:
            self.scopes[-1][node[2]] = self.val
            self._succeed()

    def _handle_lit(self, node):
        i = 0
        lit = node[1]
        lit_len = len(lit)
        while (
            i < lit_len
            and self.pos < self.end
            and self.msg[self.pos] == lit[i]
        ):
            self.pos += 1
            i += 1
        if i == lit_len:
            self._succeed(self.msg[self.pos - 1])
        else:
            self._fail()

    def _handle_ll_arr(self, node):
        vals = []
        for subnode in node[1]:
            self._interpret(subnode)
            vals.append(self.val)
        self._succeed(vals)

    def _handle_ll_call(self, node):
        vals = []
        for subnode in node[1]:
            self._interpret(subnode)
            vals.append(self.val)
        self._succeed(['ll_call', vals])

    def _handle_ll_const(self, node):
        if node[1] == 'true':
            self._succeed(True)
        elif node[1] == 'false':
            self._succeed(False)
        elif node[1] == 'null':
            self._succeed(None)
        elif node[1] == 'Infinity':
            self._succeed(float('inf'))
        elif node[1] == 'NaN':
            self._succeed(float('NaN'))

    def _handle_ll_getitem(self, node):
        self._interpret(node[1])
        if not self.failed:
            self._succeed(['ll_getitem', self.val])

    def _handle_ll_num(self, node):
        if node[1].startswith('0x'):
            self._succeed(int(node[1], base=16))
        else:
            self._succeed(int(node[1]))

    def _handle_ll_paren(self, node):
        self._interpret(node[1])

    def _handle_ll_plus(self, node):
        self._interpret(node[1])
        v1 = self.val
        self._interpret(node[2])
        v2 = self.val
        self._succeed(v1 + v2)

    def _handle_ll_qual(self, node):
        self._interpret(node[1])
        assert not self.failed
        lhs = self.val
        self._interpret(node[2][0])
        assert not self.failed
        op, rhs = self.val
        if op == 'll_getitem':
            self.val = lhs[rhs]
        else:
            assert op == 'll_call'
            fn = getattr(self, '_builtin_fn_' + lhs)
            self.val = fn(*rhs)

    def _handle_ll_lit(self, node):
        self._succeed(node[1])

    def _handle_ll_var(self, node):
        v = getattr(self, '_builtin_fn_' + node[1], None)
        if v:
            self._succeed(node[1])
            return

        if self.scopes and (node[1] in self.scopes[-1]):
            self._succeed(self.scopes[-1][node[1]])
            return

        self._fail('Reference to unknown variable "%s"' % node[1])

    def _handle_not(self, node):
        pos = self.pos
        val = self.val
        self._interpret(node[1])
        if self.failed:
            self._succeed(val, newpos=pos)
        else:
            self.pos = pos
            self._fail(val)

    def _handle_opt(self, node):
        pos = self.pos
        self._interpret(node[1])
        if self.failed:
            self.failed = False
            self.val = []
            self.pos = pos
        else:
            self.val = [self.val]

    def _handle_paren(self, node):
        self._interpret(node[1])

    def _handle_plus(self, node):
        self._interpret(node[1])
        hd = self.val
        if not self.failed:
            self._handle_star(node)
            self.val = [hd] + self.val

    def _handle_post(self, node):
        if node[2] == '?':
            self._handle_opt(node)
        elif node[2] == '*':
            self._handle_star(node)
        elif node[2] == '+':
            self._handle_plus(node)

    def _handle_pred(self, node):
        self._interpret(node[1])
        if self.val is True:
            self._succeed(True)
        elif self.val is False:
            self.val = False
            self._fail()
        else:
            self._fail('Bad predicate value')

    def _handle_range(self, node):
        assert node[1][0] == 'lit'
        assert node[2][0] == 'lit'
        if (
            self.pos != self.end
            and node[1][1] <= self.msg[self.pos] <= node[2][1]
        ):
            self._succeed(self.msg[self.pos], self.pos + 1)
            return
        self._fail()

    def _handle_seq(self, node):
        self.scopes.append({})
        for subnode in node[1]:
            self._interpret(subnode)
            if self.failed:
                break
        self.scopes.pop()

    def _handle_star(self, node):
        vs = []
        while not self.failed and self.pos < self.end:
            p = self.pos
            self._interpret(node[1])
            if self.failed:
                self.pos = p
                break
            vs.append(self.val)
        self._succeed(vs)

    def _builtin_fn_cat(self, val):
        return ''.join(val)

    def _builtin_fn_dict(self, val):
        return dict(val)

    def _builtin_fn_float(self, val):
        return float(val)

    def _builtin_fn_hex(self, val):
        return int(val, base=16)

    def _builtin_fn_is_unicat(self, var, cat):
        return unicodedata.category(var) == cat

    def _builtin_fn_itou(self, val):
        return chr(val)

    def _builtin_fn_join(self, val, vs):
        return val.join(vs)

    def _builtin_fn_atoi(self, val):
        return ord(val)

    def _builtin_fn_xtou(self, val):
        return chr(int(val, base=16))
