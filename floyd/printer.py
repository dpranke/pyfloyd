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

from floyd import string_literal as lit


class Printer:
    def __init__(self, grammar):
        self.grammar = grammar
        self.max_rule_len = 0
        self.max_choice_len = 0

    def dumps(self) -> str:
        rules = self._build_rules()
        return self._format_rules(rules)

    def _build_rules(self):
        rules = []
        for ty, rule_name, node in self.grammar.ast[2]:
            if ty == 'pragma':
                rule_name = '%' + rule_name
                self.max_rule_len = max(len(rule_name), self.max_rule_len)
                if rule_name == '%token':
                    cs = [(node[0], '')]
                elif rule_name == '%tokens':
                    if len(node) == 1:
                        rule_name = '%token'
                        cs = [(node[0], '')]
                    else:
                        cs = [(' '.join(node), '')]
                else:
                    assert rule_name in (
                        '%comment',
                        '%whitespace',
                    )
                    cs = self._fmt_rule(node[0])
            else:
                self.max_rule_len = max(len(rule_name), self.max_rule_len)
                cs = self._fmt_rule(node[0])
            rules.append((rule_name, cs))
        return rules

    def _fmt_rule(self, node):
        single_line_str = self._proc(node)
        if len(single_line_str) > 36 and node[0] == 'choice':
            cs = []
            for choice_node in node[2]:
                choice, action = self._split_action(choice_node)
                self.max_choice_len = max(len(choice), self.max_choice_len)
                cs.append((choice, action))
        else:
            choice, action = self._split_action(node)
            cs = [(choice, action)]
            self.max_choice_len = max(len(choice), self.max_choice_len)
        return cs

    def _split_action(self, node):
        if node[0] != 'seq' or node[2][-1][0] != 'action':
            return (self._proc(node), '')
        return (
            self._proc(['seq', None, node[2][:-1]]),
            self._proc(node[2][-1]),
        )

    def _format_rules(self, rules):
        line_fmt = (
            '%%-%ds' % self.max_rule_len
            + ' %s '
            + '%%-%ds' % self.max_choice_len
            + ' %s'
        )
        lines = []
        for rule_name, choices in rules:
            if rule_name in (
                '%token',
                '%tokens',
            ):
                lines.append(rule_name + ' = ' + ' '.join(c[0] for c in choices))
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
        fn = getattr(self, '_' + node[0] + '_')
        return fn(node)

    #
    # Handlers for each node in the glop AST follow.
    #

    def _action_(self, node):
        return '-> %s' % self._proc(node[2][0])

    def _apply_(self, node):
        return node[1]

    def _choice_(self, node):
        return ' | '.join(self._proc(e) for e in node[2])

    def _empty_(self, node):
        del node
        return ''

    def _label_(self, node):
        return '%s:%s' % (self._proc(node[2][0]), node[1])

    def _leftrec_(self, node):
        return self._proc(node[2][0])

    def _lit_(self, node):
        return lit.encode(node[1])

    def _unicat_(self, node):
        return '\\p{%s}' % node[1]

    def _ll_arr_(self, node):
        return '[%s]' % ', '.join(self._proc(el) for el in node[2])

    def _ll_call_(self, node):
        return '(%s)' % ', '.join(self._proc(arg) for arg in node[2])

    def _ll_const_(self, node):
        return node[1]

    def _ll_getitem_(self, node):
        return '[%s]' % self._proc(node[2][0])

    def _ll_lit_(self, node):
        return self._lit_(node)

    def _ll_minus_(self, node):
        return '%s - %s' % (self._proc(node[2][0]), self._proc(node[2][1]))

    def _ll_num_(self, node):
        return str(node[1])

    def _ll_plus_(self, node):
        return '%s + %s' % (self._proc(node[2][0]), self._proc(node[2][1]))

    def _ll_qual_(self, node):
        _, _, ops = node
        v = self._proc(ops[0])
        return '%s%s' % (v, ''.join(self._proc(op) for op in ops[1:]))

    def _ll_var_(self, node):
        return node[1]

    def _range_(self, node):
        return '%s..%s' % (lit.encode(node[1][0]), lit.encode(node[1][1]))

    def _not_(self, node):
        return '~%s' % self._proc(node[2][0])

    def _pred_(self, node):
        return '?{%s}' % self._proc(node[2][0])

    def _post_(self, node):
        return '%s%s' % (self._proc(node[2][0]), node[1])

    def _regexp_(self, node):
        return f"/{lit.escape(node[1], '/')}/"

    def _set_(self, node):
        return f"[{lit.escape(node[1], ']')}]"

    def _seq_(self, node):
        return ' '.join(self._proc(e) for e in node[2])

    def _paren_(self, node):
        return '(' + self._proc(node[2][0]) + ')'
