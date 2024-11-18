# Copyright 2024 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 as found in the LICENSE file.
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

from pyfloyd import string_literal as lit


class Printer:
    def __init__(self, grammar):
        self._grammar = grammar
        self._max_rule_len = 0
        self._max_choice_len = 0

    def dumps(self) -> str:
        rules = self._build_rules()
        return self._format_rules(rules)

    def _build_rules(self):
        rules = []
        for ty, rule_name, node in self._grammar.ast[2]:
            if ty == 'pragma':
                rule_name = '%' + rule_name
                self._max_rule_len = max(len(rule_name), self._max_rule_len)
                if rule_name in ('%externs', '%tokens'):
                    cs = [(' '.join(node), '')]
                else:
                    assert rule_name in (
                        '%comment',
                        '%whitespace',
                    )
                    cs = self._fmt_rule(node[0])
            else:
                self._max_rule_len = max(len(rule_name), self._max_rule_len)
                cs = self._fmt_rule(node[0])
            rules.append((rule_name, cs))
        return rules

    def _fmt_rule(self, node):
        single_line_str = self._proc(node)
        if len(single_line_str) > 36 and node[0] == 'choice':
            cs = []
            for choice_node in node[2]:
                choice, action = self._split_action(choice_node)
                self._max_choice_len = max(len(choice), self._max_choice_len)
                cs.append((choice, action))
        else:
            choice, action = self._split_action(node)
            cs = [(choice, action)]
            self._max_choice_len = max(len(choice), self._max_choice_len)
        return cs

    def _split_action(self, node):
        if node[0] == 'scope':
            return self._split_action(node[2][0])
        if node[0] != 'seq' or node[2][-1][0] != 'action':
            return (self._proc(node), '')
        return (
            self._proc(['seq', None, node[2][:-1]]),
            self._proc(node[2][-1]),
        )

    def _format_rules(self, rules):
        line_fmt = (
            '%%-%ds' % self._max_rule_len
            + ' %s '
            + '%%-%ds' % self._max_choice_len
            + ' %s'
        )
        lines = []
        for rule_name, choices in rules:
            if rule_name in (
                '%token',
                '%tokens',
            ):
                lines.append(
                    rule_name + ' = ' + ' '.join(c[0] for c in choices)
                )
            else:
                choice, act = choices[0]
                lines.append(
                    (line_fmt % (rule_name, '=', choice, act)).rstrip()
                )
                for choice, act in choices[1:]:
                    lines.append((line_fmt % ('', '|', choice, act)).rstrip())
            lines.append('')
        return '\n'.join(lines).strip() + '\n'

    def _proc(self, node):
        fn = getattr(self, f'_ty_{node[0]}')
        return fn(node)

    #
    # Handlers for each node in the glop AST follow.
    #

    def _ty_action(self, node):
        return '-> %s' % self._proc(node[2][0])

    def _ty_apply(self, node):
        return node[1]

    def _ty_choice(self, node):
        return ' | '.join(self._proc(e) for e in node[2])

    def _ty_count(self, node):
        if node[1][0] == node[1][1]:
            return '%s{%d}' % (self._proc(node[2][0]), node[1][0])
        return '%s{%d,%d}' % (self._proc(node[2][0]), node[1][0], node[1][1])

    def _ty_e_arr(self, node):
        return '[%s]' % ', '.join(self._proc(el) for el in node[2])

    def _ty_e_call(self, node):
        return '(%s)' % ', '.join(self._proc(arg) for arg in node[2])

    def _ty_e_const(self, node):
        return node[1]

    def _ty_e_getitem(self, node):
        return '[%s]' % self._proc(node[2][0])

    def _ty_e_lit(self, node):
        return self._ty_lit(node)

    def _ty_e_minus(self, node):
        return '%s - %s' % (self._proc(node[2][0]), self._proc(node[2][1]))

    def _ty_e_num(self, node):
        return str(node[1])

    def _ty_e_plus(self, node):
        return '%s + %s' % (self._proc(node[2][0]), self._proc(node[2][1]))

    def _ty_e_qual(self, node):
        _, _, ops = node
        v = self._proc(ops[0])
        return '%s%s' % (v, ''.join(self._proc(op) for op in ops[1:]))

    def _ty_e_var(self, node):
        return node[1]

    def _ty_empty(self, node):
        del node
        return ''

    def _ty_ends_in(self, node):
        return '^.' + self._proc(node[2][0])

    def _ty_label(self, node):
        if node[1].startswith('$'):
            return '%s' % self._proc(node[2][0])
        return '%s:%s' % (self._proc(node[2][0]), node[1])

    def _ty_leftrec(self, node):
        return self._proc(node[2][0])

    def _ty_lit(self, node):
        return lit.encode(node[1])

    def _ty_not(self, node):
        return '~%s' % self._proc(node[2][0])

    def _ty_not_one(self, node):
        return '^%s' % self._proc(node[2][0])

    def _ty_opt(self, node):
        return self._proc(node[2][0]) + '?'

    def _ty_paren(self, node):
        return '(' + self._proc(node[2][0]) + ')'

    def _ty_plus(self, node):
        return self._proc(node[2][0]) + '+'

    def _ty_pred(self, node):
        return '?{ %s }' % self._proc(node[2][0])

    def _ty_range(self, node):
        return '%s..%s' % (lit.encode(node[1][0]), lit.encode(node[1][1]))

    def _ty_regexp(self, node):
        return f"/{lit.escape(node[1], '/')}/"

    def _ty_run(self, node):
        return '<%s>' % self._proc(node[2][0])

    def _ty_scope(self, node):
        return self._proc(node[2][0])

    def _ty_seq(self, node):
        return ' '.join(self._proc(e) for e in node[2])

    def _ty_set(self, node):
        return f"[{lit.escape(node[1], ']')}]"

    def _ty_star(self, node):
        return self._proc(node[2][0]) + '*'

    def _ty_unicat(self, node):
        return '\\p{%s}' % node[1]
