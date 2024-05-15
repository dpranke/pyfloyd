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

        self.msg = None
        self.fname = None
        self.failed = False
        self.val = None
        self.pos = 0
        self.end = -1
        self.errstr = 'Error: uninitialized'
        self.errpos = 0
        self.scopes = []
        self.seeds = {}
        self.blocked = set()
        self.debug = False
        self.depth = 0

        self.current_prec = 0
        self.prec_ops = {}
        for op in grammar.prec:
            self.prec_ops.setdefault(grammar.prec[op], []).append(op)
        self.precs = sorted(self.prec_ops, reverse=True)
        self.operator_count = 0

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

        # self.debug = True
        self._interpret(self.grammar.rules[self.grammar.starting_rule])
        if self.failed:
            return self._format_error()
        return self.val, None, self.pos

    def log_start(self, rule_name):
        if not self.debug:
            return
        print('%s%s @ %s start' % ('  ' * self.depth, rule_name, self.pos))
        self.depth += 1

    def log_end(self, rule_name, pos):
        if not self.debug:
            return
        self.depth -= 1
        if self.failed:
            print('%s%s @ %s %s' % ('  ' * self.depth, rule_name, pos, 'fail'))
        else:
            print(
                '%s%s @ %s %s -> %s'
                % ('  ' * self.depth, rule_name, pos, 'succ', repr(self.val))
            )

    def log_match(self, match, pos, res):
        if not self.debug:
            return
        print("%s'%s' @ %s %s" % ('  ' * self.depth, match, pos, res))

    def log_range(self, low, hi, pos, res):
        if not self.debug:
            return
        print("%s'%s'..'%s' @ %s %s" % ('  ' * self.depth, low, hi, pos, res))

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
        self._interpret(node[2][0])

    def _handle_apply(self, node):
        rule_name = node[1]
        pos = self.pos
        self.log_start(rule_name)
        if rule_name == 'end':
            self._handle_end()
            self.log_end(rule_name, pos)
            return

        if rule_name == 'any':
            if self.pos != self.end:
                self._succeed(self.msg[self.pos], self.pos + 1)
                self.log_end(rule_name, pos)
                return
            self._fail()
            self.log_end(rule_name, pos)
            return

        # Unknown rules should have been caught in analysis, so we don't
        # need to worry about one here and can jump straight to the rule.
        self._interpret(self.grammar.rules[rule_name])
        self.log_end(rule_name, pos)

    def _handle_choice(self, node):
        count = 1
        pos = self.pos
        for rule in node[2][:-1]:
            if self.debug:
                print('%s-- choice %s' % ('  ' * self.depth, count))
            self._interpret(rule)
            if not self.failed:
                return
            self._rewind(pos)
            count += 1
        self._interpret(node[2][-1])
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
        self._interpret(node[2][0])
        if not self.failed:
            self.scopes[-1][node[1]] = self.val
            self._succeed()

    def _handle_leftrec(self, node):
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
                if self.debug:
                    print('%s-- loop' % ('  ' * self.depth))
            else:
                del self.seeds[key]
                self.val, self.failed, self.pos = current
                if assoc == 'left':
                    self.blocked.remove(rule_name)
                if self.debug:
                    print('%s-- exit' % ('  ' * self.depth))
                return

    def _handle_lit(self, node):
        i = 0
        lit = node[1]
        lit_len = len(lit)
        pos = self.pos
        while (
            i < lit_len
            and self.pos < self.end
            and self.msg[self.pos] == lit[i]
        ):
            self.pos += 1
            i += 1
        if i == lit_len:
            self._succeed(self.msg[pos : self.pos])
            self.log_match(lit, pos, 'succ')
        else:
            self._fail()
            self.log_match(lit, pos, 'fail')

    def _handle_unicat(self, node):
        p = self.pos
        if p < self.end and unicodedata.category(self.msg[p]) == node[1]:
            self._succeed(self.msg[p], newpos=p + 1)
        else:
            self._fail()

    def _handle_ll_arr(self, node):
        vals = []
        for subnode in node[2]:
            self._interpret(subnode)
            vals.append(self.val)
        self._succeed(vals)

    def _handle_ll_call(self, node):
        vals = []
        for subnode in node[2]:
            self._interpret(subnode)
            vals.append(self.val)
        # Return 'll_call' as a tag here so we can check it in ll_qual.
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
        else:
            assert node[1] == 'NaN'
            self._succeed(float('NaN'))

    def _handle_ll_getitem(self, node):
        self._interpret(node[2][0])
        assert not self.failed
        # Return 'll_getitem' as a tag here so we can check it in ll_qual.
        self._succeed(['ll_getitem', self.val])

    def _handle_ll_minus(self, node):
        self._interpret(node[2][0])
        v1 = self.val
        self._interpret(node[2][1])
        v2 = self.val
        self._succeed(v1 - v2)

    def _handle_ll_num(self, node):
        if node[1].startswith('0x'):
            self._succeed(int(node[1], base=16))
        else:
            self._succeed(int(node[1]))

    def _handle_ll_paren(self, node):
        self._interpret(node[2][0])

    def _handle_ll_plus(self, node):
        self._interpret(node[2][0])
        v1 = self.val
        self._interpret(node[2][1])
        v2 = self.val
        self._succeed(v1 + v2)

    def _handle_ll_qual(self, node):
        self._interpret(node[2][0])
        assert not self.failed
        lhs = self.val
        self._interpret(node[2][1])
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

        # Unknown variables should have been caught in analysis.
        assert self.scopes and (node[1] in self.scopes[-1])
        self._succeed(self.scopes[-1][node[1]])

    def _handle_not(self, node):
        pos = self.pos
        val = self.val
        self._interpret(node[2][0])
        if self.failed:
            self._succeed(val, newpos=pos)
        else:
            self.pos = pos
            self._fail(val)

    def _handle_operator(self, node):
        pos = self.pos
        rule_name = node[1]
        key = (rule_name, self.pos)
        seed = self.seeds.get(key)
        if seed:
            self.val, self.failed, self.pos = seed
            return

        self.operator_count += 1
        current = (None, True, self.pos)
        self.seeds[key] = current
        min_prec = self.current_prec

        i = 0
        while i < len(self.precs):
            repeat = False
            prec = self.precs[i]
            if prec < min_prec:
                break
            self.current_prec = prec
            if self.grammar.assoc.get(self.prec_ops[prec][0], 'left') == 'left':
                self.current_prec += 1

            for j in range(len(self.prec_ops[prec])):
                op = self.prec_ops[prec][j]
                choice = self._find_choice(node, op)
                self._interpret(choice)
                if not self.failed and self.pos > pos:
                    current = (self.val, self.failed, self.pos)
                    self.seeds[key] = current
                    repeat = True
                    break
                else:
                    self._rewind(pos)
            if not repeat:
                i += 1
        del self.seeds[key]
        self.operator_count -= 1
        if self.operator_count == 0:
            self.current_prec = 0
        self.val, self.failed, self.pos = current

    def _find_choice(self, node, op):
        if len(node[2][0][2]) == 6:
            index = 2
        else:
            index = 1
        for choice in node[2]:
            if choice[2][index] == ['lit', op, []]:
                return choice
        assert False, 'Could not find op in choices'  # pragma: no cover

    def _handle_opt(self, node):
        pos = self.pos
        self._interpret(node[2][0])
        if self.failed:
            self.failed = False
            self.val = []
            self.pos = pos
        else:
            self.val = [self.val]

    def _handle_paren(self, node):
        self._interpret(node[2][0])

    def _handle_plus(self, node):
        self._interpret(node[2][0])
        hd = self.val
        if not self.failed:
            self._handle_star(node)
            self.val = [hd] + self.val

    def _handle_post(self, node):
        if node[1] == '?':
            self._handle_opt(node)
        elif node[1] == '*':
            self._handle_star(node)
        else:
            assert node[1] == '+'
            self._handle_plus(node)

    def _handle_pred(self, node):
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

    def _handle_range(self, node):
        assert node[2][0][0] == 'lit'
        assert node[2][1][0] == 'lit'
        pos = self.pos
        if (
            self.pos != self.end
            and node[2][0][1] <= self.msg[self.pos] <= node[2][1][1]
        ):
            self._succeed(self.msg[self.pos], self.pos + 1)
            self.log_range(node[2][0][1], node[2][1][1], pos, 'succ')
            return
        self._fail()
        self.log_range(node[2][0][1], node[2][1][1], pos, 'fail')

    def _handle_seq(self, node):
        self.scopes.append({})
        for subnode in node[2]:
            self._interpret(subnode)
            if self.failed:
                break
        self.scopes.pop()

    def _handle_star(self, node):
        vs = []
        while not self.failed and self.pos < self.end:
            p = self.pos
            self._interpret(node[2][0])
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

    def _builtin_fn_utoi(self, val):
        return ord(val)

    def _builtin_fn_xtou(self, val):
        return chr(int(val, base=16))
