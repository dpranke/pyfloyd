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

from pyfloyd import string_literal


class Printer:
    def __init__(self, ast):
        self._ast = ast
        self._max_rule_len = 0
        self._max_choice_len = 0

    def dumps(self) -> str:
        rules = self._build_rules()
        return self._format_rules(rules)

    def _build_rules(self):
        rules = []
        for _, rule_name, node in self._ast[2]:
            self._max_rule_len = max(len(rule_name), self._max_rule_len)
            cs = self._fmt_rule(node[0])
            rules.append((rule_name, cs))
        return rules

    def _fmt_rule(self, node):
        cs = []
        if node[0] == 'choice':
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
        line_fmt = f'%-{self._max_rule_len}s %s %-{self._max_choice_len}s %s'
        lines = []
        for rule_name, choices in rules:
            choice, act = choices[0]
            lines.append((line_fmt % (rule_name, '=', choice, act)).rstrip())
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
        return '-> ' + self._proc(node[2][0])

    def _ty_apply(self, node):
        return node[1]

    def _ty_choice(self, node):
        return ' | '.join(self._proc(e) for e in node[2])

    def _ty_count(self, node):
        if node[1][0] == node[1][1]:
            return '%s{%d}' % (self._proc(node[2][0]), node[1][0])
        return '%s{%d,%d}' % (self._proc(node[2][0]), node[1][0], node[1][1])

    def _ty_e_arr(self, node):
        return '[' + ', '.join(self._proc(el) for el in node[2]) + ']'

    def _ty_e_call(self, node):
        return '(' + ', '.join(self._proc(arg) for arg in node[2]) + ')'

    def _ty_e_const(self, node):
        return node[1]

    def _ty_e_getitem(self, node):
        return '[' + self._proc(node[2][0]) + ']'

    def _ty_e_lit(self, node):
        return self._ty_lit(node)

    def _ty_e_minus(self, node):
        return self._proc(node[2][0]) + ' - ' + self._proc(node[2][1])

    def _ty_e_not(self, node):
        return '!' + self._proc(node[2][0])

    def _ty_e_num(self, node):
        return str(node[1])

    def _ty_e_plus(self, node):
        return self._proc(node[2][0]) + ' + ' + self._proc(node[2][1])

    def _ty_e_qual(self, node):
        _, _, ops = node
        v = self._proc(ops[0])
        return v + ''.join(self._proc(op) for op in ops[1:])

    def _ty_e_ident(self, node):
        return node[1]

    def _ty_empty(self, node):
        del node
        return ''

    def _ty_ends_in(self, node):
        return '^.' + self._proc(node[2][0])

    def _ty_label(self, node):
        if node[1].startswith('$'):
            return self._proc(node[2][0])
        return self._proc(node[2][0]) + ':' + node[1]

    def _ty_leftrec(self, node):
        return self._proc(node[2][0])

    def _ty_lit(self, node):
        return string_literal.encode(node[1])

    def _ty_not(self, node):
        return '~' + self._proc(node[2][0])

    def _ty_not_one(self, node):
        return '^' + self._proc(node[2][0])

    def _ty_opt(self, node):
        return self._proc(node[2][0]) + '?'

    def _ty_paren(self, node):
        return '(' + self._proc(node[2][0]) + ')'

    def _ty_plus(self, node):
        return self._proc(node[2][0]) + '+'

    def _ty_pred(self, node):
        return '?{ ' + self._proc(node[2][0]) + ' }'

    def _ty_range(self, node):
        return (
            string_literal.encode(node[1][0])
            + '..'
            + string_literal.encode(node[1][1])
        )

    def _ty_regexp(self, node):
        return '/' + string_literal.escape(node[1], '/') + '/'

    def _ty_run(self, node):
        return '<' + self._proc(node[2][0]) + '>'

    def _ty_scope(self, node):
        return self._proc(node[2][0])

    def _ty_seq(self, node):
        return ' '.join(self._proc(e) for e in node[2])

    def _ty_set(self, node):
        return '[' + string_literal.escape(node[1], ']') + ']'

    def _ty_star(self, node):
        return self._proc(node[2][0]) + '*'

    def _ty_unicat(self, node):
        return '\\p{' + node[1] + '}'
