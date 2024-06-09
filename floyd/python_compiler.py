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

import enum

from floyd import python_templates as py
from floyd import string_literal


Whitespace = enum.Enum(
    'Whitespace',
    [
        'Indent',
        'Newline',
        'OptionalIndent',
        'OptionalUnindent',
        'SpaceOrNewline',
        'SpaceOrIndent',
        'Unindent',
    ],
)

IN = Whitespace.Indent
NL = Whitespace.Newline
OI = Whitespace.OptionalIndent
OU = Whitespace.OptionalUnindent
SN = Whitespace.SpaceOrNewline
UN = Whitespace.Unindent


class _CompilerOperatorState:
    def __init__(self):
        self.prec_ops = {}
        self.rassoc = set()
        self.choices = {}


class Compiler:
    def __init__(self, grammar, classname, main_wanted=True, memoize=True):
        self._grammar = grammar
        self._classname = classname
        self._depth = 0
        self._main_wanted = main_wanted
        self._memoize = memoize
        self._methods = {}
        self._method_lines = []
        self._exception_needed = False
        self._unicodedata_needed = False
        self._operators = {}

        # These methods are always needed.
        self._needed = set(
            {
                'err_offsets',
                'err_str',
                'fail',
                'rewind',
                'succeed',
            }
        )

    def compile(self):
        for rule, node in self._grammar.rules.items():
            self._compile(node, rule)

        return self._gen_text()

    def _gen_text(self):
        unicodedata_import = ''
        if self._unicodedata_needed:
            unicodedata_import = 'import unicodedata\n\n'

        if self._main_wanted:
            text = py.MAIN_HEADER.format(
                classname=self._classname,
                unicodedata_import=unicodedata_import,
            )
        else:
            text = py.DEFAULT_HEADER.format(
                unicodedata_import=unicodedata_import
            )

        if self._exception_needed:
            text += py.PARSING_RUNTIME_EXCEPTION

        if self._operators:
            text += py.OPERATOR_CLASS

        text += py.CLASS.format(classname=self._classname)

        text += self._state()
        text += '\n'

        if self._exception_needed:
            text += py.PARSE_WITH_EXCEPTION.format(
                starting_rule=self._grammar.starting_rule
            )
        else:
            text += py.PARSE.format(starting_rule=self._grammar.starting_rule)

        text += self._gen_methods()
        if self._main_wanted:
            text += py.MAIN_FOOTER
        else:
            text += py.DEFAULT_FOOTER
        return text

    def _state(self):
        text = ''
        if self._memoize:
            text += '        self.cache = {}\n'
        if 'bind' in self._needed:
            text += '        self.scopes = []\n'
            self._needed.update(
                {
                    'get',
                    'push',
                    'pop',
                    'set',
                }
            )
        if 'leftrec' in self._needed or 'operator' in self._needed:
            text += '        self.seeds = {}\n'
        if 'leftrec' in self._needed:
            text += '        self.blocked = set()\n'
        if self._operators:
            text += self._operator_state()
            text += '\n'

        return text

    def _operator_state(self):
        text = '        self.operators = {}\n'
        for rule, o in self._operators.items():
            text += '        o = _OperatorState()\n'
            text += '        o.prec_ops = {\n'
            for prec in sorted(o.prec_ops):
                text += '            %d: [' % prec
                text += ', '.join("'%s'" % op for op in o.prec_ops[prec])
                text += '],\n'
            text += '        }\n'
            text += '        o.precs = sorted(o.prec_ops, reverse=True)\n'
            text += '        o.rassoc = set(['
            text += ', '.join("'%s'" % op for op in o.rassoc)
            text += '])\n'
            text += '        o.choices = {\n'
            for op in o.choices:
                text += "            '%s': self._%s_,\n" % (op, o.choices[op])
            text += '        }\n'
            text += "        self.operators['%s'] = o\n" % rule
        return text

    def _load_builtins(self):
        blocks = py.BUILTINS.split('\n    def ')
        blocks[0] = blocks[0][8:]
        builtins = {}
        for block in blocks:
            name = block[1 : block.find('(')]
            if name == 'end_':
                name = 'end'
            if name == 'any_':
                name = 'any'
            text = '    def ' + block
            builtins[name] = text
        return builtins

    def _gen_methods(self):
        text = ''
        for rule, method_body in self._methods.items():
            memoize = self._memoize and rule in self._grammar.rules
            text += self._gen_method_text(rule, method_body, memoize)

        text += '\n'

        builtins = self._load_builtins()
        text += '\n'.join(builtins[name] for name in sorted(self._needed))
        return text

    def _gen_method_text(self, method_name, method_body, memoize):
        text = '\n'
        text += '    def _%s_(self):\n' % method_name
        if memoize:
            text += '        r = self.cache.get(("%s", ' % method_name
            text += 'self.pos))\n'
            text += '        if r is not None:\n'
            text += '            self.val, self.failed, self.pos = r\n'
            text += '            return\n'
            text += '        pos = self.pos\n'
        for line in method_body:
            text += f'        {line}\n'
        if memoize:
            text += f'        self.cache[("{method_name}", pos)] = ('
            text += 'self.val, self.failed, self.pos)\n'
        return text

    def _compile(self, node, rule):
        fn = getattr(self, f'_{node[0]}_')
        fn(rule, node)

    def _eval(self, node):
        fn = getattr(self, f'_{node[0]}_')
        return fn(node)

    def _has_labels(self, node):
        if node and node[0] in ('label', 'll_var'):
            return True
        for n in node:
            if isinstance(n, list) and self._has_labels(n):
                return True
        return False

    def _gen_method_call(self, name, args):
        method_len = len(name) + 10
        args_txt = ', '.join(args)
        args_len = len(args_txt)
        if method_len + args_len <= 72:
            return [f'self._{name}([' + args_txt + '])']
        if args_len <= 66:
            return [f'self._{name}(', f'    [{args_txt}]', ')']
        lines = [f'self._{name}(', '    [']
        for arg in args:
            lines.append(f'        {arg},')
        lines.extend(['    ]', ')'])
        return lines

    def _indent(self, s):
        return self._depth * '    ' + s

    def _flatten(self, obj):
        return self._flatten_rec(obj, 0, self._max_depth(obj) + 1)
        for line in lines:
            lines.append(line.rstrip())

        # TODO: Figure out how to handle blank lines at the end of a method
        # better. There will be a blank line if obj[-1] == UN.
        return lines

    def _flatten_rec(self, obj, current_depth, max_depth):
        for i in range(current_depth, max_depth):
            lines = []
            s = ''
            for el in obj:
                if isinstance(el, str):
                    s += el
                elif el == IN:
                    lines.append(self._indent(s))
                    self._depth += 1
                    s = ''
                elif el == NL:
                    lines.append(self._indent(s))
                    s = ''
                elif el == OI:
                    if i > 0:
                        lines.append(self._indent(s))
                        self._depth += 1
                        s = ''
                elif el == OU:
                    if i > 0:
                        lines.append(self._indent(s))
                        self._depth -= 1
                        s = ''
                elif el == SN:
                    if i == 0:
                        s += ' '
                    else:
                        lines.append(self._indent(s))
                        s = ''
                elif el == UN:
                    lines.append(self._indent(s))
                    self._depth -= 1
                    s = ''
                else:  # el must be an obj
                    new_lines = self._flatten_rec(el, max(i - 1, 0), max(i, 1))
                    s += new_lines[0]
                    if len(new_lines) > 1:
                        lines.append(s)
                        lines.extend(new_lines[1:-1])
                        s = new_lines[-1]

            lines.append(s)
            if all(self._fits(line) for line in lines):
                break
        return lines

    def _fits(self, line):
        return len(line) < 72

    def _max_depth(self, obj):
        if isinstance(obj, list):
            return max(self._max_depth(el) + 1 for el in obj)
        return 1

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _action_(self, rule, node):
        obj = self._eval(node[2][0])
        self._methods[rule] = self._flatten(
            ['self._succeed(', OI, obj, OU, ')']
        )

    def _apply_(self, rule, node):
        # Unknown rules were caught in analysis so if the rule isn't
        # one of the ones in the grammar it must be a built-in one.
        if node[1] not in self._grammar.rules:
            self._needed.add(node[1])
        self._methods[rule] = [f'self._{node[1]}_()']

    def _choice_(self, rule, node):
        self._needed.add('choose')
        args = [f'self._{rule}_c{i}_' for i, _ in enumerate(node[2])]
        self._methods[rule] = self._gen_method_call('choose', args)
        for i, sub_node in enumerate(node[2]):
            self._compile(sub_node, f'{rule}_c{i}')

    def _empty_(self, rule, node):
        del node
        self._methods[rule] = ['self._succeed(None)']

    def _label_(self, rule, node):
        self._needed.add('bind')
        sub_rule = rule + '_l'
        self._methods[rule] = [
            'self._bind(self._%s_, %s)'
            % (sub_rule, string_literal.encode(node[1]))
        ]
        self._compile(node[2][0], sub_rule)

    def _leftrec_(self, rule, node):
        sub_rule = 'rule' + '_l'
        left_assoc = self._grammar.assoc.get(node[1], 'left') == 'left'
        self._needed.add('leftrec')
        needs_scope = self._has_labels(node)
        lines = []
        if needs_scope:
            lines.append(f"self._push('{rule}')")
        lines.append(
            f'self._leftrec(self._{sub_rule}_, '
            + f"'{node[1]}', {str(left_assoc)})"
        )
        if needs_scope:
            lines.append(f"self._pop('{rule}')")
        self._methods[rule] = lines
        self._compile(node[2][0], sub_rule)

    def _lit_(self, rule, node):
        expr = string_literal.encode(node[1])
        if len(node[1]) == 1:
            method = 'ch'
        else:
            method = 'str'
            self._needed.add('ch')
        self._needed.add(method)
        self._methods[rule] = [f'self._{method}({expr})']

    def _not_(self, rule, node):
        self._needed.add('not')
        sub_rule = rule + '_n'
        self._methods[rule] = [f'self._not(self._{sub_rule}_)']
        self._compile(node[2][0], sub_rule)

    def _operator_(self, rule, node):
        self._needed.add('operator')
        o = _CompilerOperatorState()
        lines = []
        self._methods[rule] = lines
        for i, operator in enumerate(node[2]):
            op = operator[1][0]
            prec = operator[1][1]
            sub_rule = operator[2][0]
            o.prec_ops.setdefault(prec, []).append(op)
            if self._grammar.assoc.get(op) == 'right':
                o.rassoc.add(op)
            o.choices[op] = '%s_o%d' % (rule, i)
            self._compile(sub_rule, f'{o.choices[op]}')
        self._operators[rule] = o
        lines.append(f'self._operator("{rule}")')

    def _paren_(self, rule, node):
        sub_rule = rule + '_g'
        self._methods[rule] = [f'self._{sub_rule}_()']
        self._compile(node[2][0], sub_rule)

    def _post_(self, rule, node):
        sub_rule = rule + '_p'
        if node[1] == '?':
            method = 'opt'
        elif node[1] == '+':
            method = 'plus'
            self._needed.add('star')
        else:
            assert node[1] == '*'
            method = 'star'
        self._needed.add(method)
        self._methods[rule] = [f'self._{method}(self._{sub_rule}_)']
        self._compile(node[2][0], sub_rule)

    def _pred_(self, rule, node):
        obj = self._eval(node[2][0])
        # TODO: Figure out how to statically analyze predicates to
        # catch ones that don't return booleans, so that we don't need
        # the _ParsingRuntimeError exception
        self._exception_needed = True
        self._methods[rule] = [
            'v = ' + obj,
            'if v is True:',
            '    self._succeed(v)',
            'elif v is False:',
            '    self._fail()',
            'else:',
            "    raise _ParsingRuntimeError('Bad predicate value')",
        ]

    def _range_(self, rule, node):
        self._needed.add('range')
        self._methods[rule] = [
            'self._range(%s, %s)'
            % (
                string_literal.encode(node[2][0][1]),
                string_literal.encode(node[2][1][1]),
            )
        ]

    def _seq_(self, rule, node):
        self._needed.add('seq')
        args = [f'self._{rule}_s{i}_' for i, _ in enumerate(node[2])]
        needs_scope = self._has_labels(node)
        lines = []
        if needs_scope:
            lines.append(f"self._push('{rule}')")
        lines.extend(self._gen_method_call('seq', args))
        if needs_scope:
            lines.append(f"self._pop('{rule}')")
        self._methods[rule] = lines
        for i, sub_node in enumerate(node[2]):
            self._compile(sub_node, f'{rule}_s{i}')

    def _unicat_(self, rule, node):
        self._unicodedata_needed = True
        self._needed.add('unicat')
        self._methods[rule] = [
            'self._unicat(%s)' % string_literal.encode(node[1])
        ]

    #
    # Handlers for the host nodes in the AST
    #
    def _ll_arr_(self, node):
        line = ['[', OI]
        if len(node[2]):
            line.append(self._eval(node[2][0]))
            for e in node[2][1:]:
                line.extend([',', SN, self._eval(e)])
        line.extend([OU, ']'])
        return line

    def _ll_call_(self, node):
        line = ['(', OI]

        # There are no built-in functions that take no arguments, so make
        # sure we're not being called that way.
        assert len(node[2]) != 0

        line.append(self._eval(node[2][0]))
        for e in node[2][1:]:
            line.extend([',', SN, self._eval(e)])
        line.extend([OU, ')'])
        return line

    def _ll_getitem_(self, node):
        return ['['] + self._eval(node[2][0]) + [']']

    def _ll_lit_(self, node):
        return [string_literal.encode(node[1])]

    def _ll_minus_(self, node):
        return self._eval(node[2][0]) + [SN, '- '] + self._eval(node[2][1])

    def _ll_num_(self, node):
        return [node[1]]

    def _ll_paren_(self, node):
        return self._eval(node[2][0])

    def _ll_plus_(self, node):
        return self._eval(node[2][0]) + [SN, '+ '] + self._eval(node[2][1])

    def _ll_qual_(self, node):
        if node[2][1][0] == 'll_call':
            self._needed.add(node[2][0][1])
            v = ['self._%s' % node[2][0][1]]
        else:
            v = self._eval(node[2][0])
        for p in node[2][1:]:
            v += self._eval(p)
        return [v]

    def _ll_var_(self, node):
        return ["self._get('%s')" % node[1]]

    def _ll_const_(self, node):
        if node[1] == 'false':
            return 'False'
        if node[1] == 'null':
            return 'None'
        if node[1] == 'true':
            return 'True'
        if node[1] == 'Infinity':
            return "float('inf')"
        assert node[1] == 'NaN'
        return "float('NaN')"
