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

from typing import Dict, List, Union

from floyd.formatter import flatten, Comma, Saw, Tree
from floyd import python_templates as py
from floyd import string_literal as lit


_FormatObj = Union[Comma | Tree | Saw | str]


class _CompilerOperatorState:
    def __init__(self):
        self.prec_ops = {}
        self.rassoc = set()
        self.choices = {}


class Compiler:
    def __init__(self, grammar, main_wanted=True, memoize=True):
        self._grammar = grammar
        self._builtin_methods = self._load_builtin_methods()
        self._builtin_functions = self._load_builtin_functions()
        self._exception_needed = False
        self._has_scopes = False
        self._main_wanted = main_wanted
        self._memoize = memoize
        self._methods = {}
        self._method_lines = []
        self._operators = {}
        self._unicodedata_needed = False
        self._rule = None
        self._sub_rules = {}
        self._counter = 1

        # These methods are always needed.
        self._needed_methods = set(
            {
                'err_offsets',
                'err_str',
                'fail',
                'rewind',
                'succeed',
            }
        )
        self._needed_functions = set()

    def compile(self) -> str:
        self._compile_rules()
        return self._gen_text()

    def _compile_rules(self) -> None:
        for rule, node in self._grammar.rules.items():
            self._rule = rule
            self._sub_rules = {}
            self._counter = 0
            lines = self._compile(node)
            self._methods[f'r_{rule}'] = lines
            sub_rules = sorted(self._sub_rules.keys(), key=self._sub_rule_key)
            for sub_rule in sub_rules:
                self._methods[sub_rule] = self._sub_rules[sub_rule]

    def _sub_rule_key(self, s: str) -> int:
        return int(s.replace(f's_{self._rule}_', ''))

    def _gen_text(self) -> str:
        unicodedata_import = ''
        if self._unicodedata_needed:
            unicodedata_import = 'import unicodedata\n\n'

        if self._main_wanted:
            text = py.MAIN_HEADER.format(
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

        text += py.CLASS

        text += self._state()
        text += '\n'

        if self._exception_needed:
            text += py.PARSE_WITH_EXCEPTION.format(
                starting_rule=self._grammar.starting_rule
            )
        else:
            text += py.PARSE.format(starting_rule=self._grammar.starting_rule)

        text += self._gen_methods()
        if self._needed_functions:
            text += '\n\n'
            text += self._gen_functions()
        if self._main_wanted:
            text += py.MAIN_FOOTER
        else:
            text += py.DEFAULT_FOOTER
        return text

    def _state(self) -> str:
        text = ''
        if self._memoize:
            text += '        self.cache = {}\n'
        if (
            'leftrec' in self._needed_methods
            or 'operator' in self._needed_methods
        ):
            text += '        self.seeds = {}\n'
        if 'leftrec' in self._needed_methods:
            text += '        self.blocked = set()\n'
        if self._operators:
            text += self._operator_state()
            text += '\n'

        return text

    def _operator_state(self) -> str:
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

    def _load_builtin_methods(self) -> Dict[str, str]:
        blocks = py.BUILTIN_METHODS.split('\n    def ')
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

    def _load_builtin_functions(self) -> Dict[str, str]:
        blocks = py.BUILTIN_FUNCTIONS[:-1].split('\n\n')
        builtins = {}
        for block in blocks:
            name = block[5 : block.find('(')]
            builtins[name] = block + '\n'
        return builtins

    def _gen_methods(self) -> str:
        text = ''
        for rule, method_body in self._methods.items():
            memoize = self._memoize and rule[2:] in self._grammar.rules
            text += self._gen_method_text(rule, method_body, memoize)

        text += '\n'

        text += '\n'.join(
            self._builtin_methods[name]
            for name in sorted(self._needed_methods)
        )
        return text

    def _gen_method_text(self, method_name, method_body, memoize) -> str:
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

    def _gen_functions(self) -> str:
        return '\n\n'.join(
            self._builtin_functions[name]
            for name in sorted(self._needed_functions)
        )

    def _compile(self, node) -> List[str]:
        # All of the rule methods return a list of lines.
        fn = getattr(self, f'_{node[0]}_')
        return fn(node)

    def _eval(self, node) -> _FormatObj:
        # All of the host methods return a formatter object.
        fn = getattr(self, f'_{node[0]}_')
        return fn(node)

    def _inline_args(self, children) -> List[List[str]]:
        lines = []
        for child in children:
            if self._can_inline(child):
                lines.append(self._compile(child))
            else:
                sub_rule = self._sub_rule()
                lines.append([f'self._{sub_rule}_()'])
                self._sub_rules[sub_rule] = self._compile(child)
        return lines

    def _can_inline(self, node) -> bool:
        if node[0] in ('action', 'apply', 'label', 'lit', 'paren', 'pred'):
            return True
        return False

    def _sub_rule(self) -> str:
        self._counter += 1
        return f's_{self._rule}_{self._counter}'

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _action_(self, node) -> List[str]:
        obj = self._eval(node[2][0])
        return flatten(Saw('self._succeed(', obj, ')'))

    def _apply_(self, node) -> List[str]:
        # Unknown rules were caught in analysis so if the rule isn't
        # one of the ones in the grammar it must be a built-in one.
        if node[1] not in self._grammar.rules:
            self._needed_methods.add(node[1])
            return [f'self._{node[1]}_()']
        return [f'self._r_{node[1]}_()']

    def _choice_(self, node) -> List[str]:
        sub_lines = self._inline_args(node[2])
        lines = ['p = self.pos']
        for sub_line in sub_lines[:-1]:
            lines.extend(sub_line)
            lines.append('if not self.failed:')
            lines.append('    return')
            lines.append('self._rewind(p)')
        lines.extend(sub_lines[-1])
        return lines

    def _empty_(self, node) -> List[str]:
        del node
        return ['self._succeed(None)']

    def _label_(self, node) -> List[str]:
        sub_node = node[2][0]
        can_inline = self._can_inline(sub_node)
        if can_inline:
            lines = self._compile(sub_node)
        else:
            sub_rule = self._sub_rule()
            self._sub_rules[sub_rule] = self._compile(sub_node)
            lines = [f'self._{sub_rule}_()']
        lines.extend(
            [
                'if not self.failed:',
                f'    v_{node[1].replace("$", "_")} = self.val',
            ]
        )
        return lines

    def _leftrec_(self, node) -> List[str]:
        sub_rule = self._sub_rule()
        left_assoc = self._grammar.assoc.get(node[1], 'left') == 'left'
        self._needed_methods.add('leftrec')
        lines = []
        lines.append(
            f'self._leftrec(self._{sub_rule}_, '
            + f"'{node[1]}', {str(left_assoc)})"
        )
        self._sub_rules[sub_rule] = self._compile(node[2][0])
        return lines

    def _lit_(self, node) -> List[str]:
        expr = lit.encode(node[1])
        if len(node[1]) == 1:
            method = 'ch'
        else:
            method = 'str'
            self._needed_methods.add('ch')
        self._needed_methods.add(method)
        return [f'self._{method}({expr})']

    def _not_(self, node) -> List[str]:
        sub_node = node[2][0]
        can_inline = self._can_inline(sub_node)
        if can_inline:
            inlined_lines = self._compile(sub_node)
        else:
            sub_rule = self._sub_rule()
            self._sub_rules[sub_rule] = self._compile(sub_node)
            inlined_lines = [f'self._{sub_rule}_()']
        lines = (
            [
                'p = self.pos',
                'errpos = self.errpos',
            ]
            + inlined_lines
            + [
                'if self.failed:',
                '    self._succeed(None, p)',
                'else:',
                '    self._rewind(p)',
                '    self.errpos = errpos',
                '    self._fail()',
            ]
        )
        return lines

    def _operator_(self, node) -> List[str]:
        self._needed_methods.add('operator')
        o = _CompilerOperatorState()
        for operator in node[2]:
            op, prec = operator[1]
            sub_node = operator[2][0]
            o.prec_ops.setdefault(prec, []).append(op)
            if self._grammar.assoc.get(op) == 'right':
                o.rassoc.add(op)
            sub_rule = self._sub_rule()
            o.choices[op] = sub_rule
            self._sub_rules[sub_rule] = self._compile(sub_node)
        self._operators[self._rule] = o
        return [f"self._operator(f'{self._rule}')"]

    def _paren_(self, node) -> List[str]:
        sub_rule = self._sub_rule()
        self._sub_rules[sub_rule] = self._compile(node[2][0])
        return [f'self._{sub_rule}_()']

    def _post_(self, node) -> List[str]:
        sub_node = node[2][0]
        can_inline = self._can_inline(sub_node)
        if can_inline:
            inlined_lines = self._compile(sub_node)
        else:
            sub_rule = self._sub_rule()
            self._sub_rules[sub_rule] = self._compile(sub_node)
            inlined_lines = [f'self._{sub_rule}_()']
        if node[1] == '?':
            lines = (
                [
                    'p = self.pos',
                ]
                + inlined_lines
                + [
                    'if self.failed:',
                    '    self._succeed([], p)',
                    'else:',
                    '    self._succeed([self.val])',
                ]
            )
        else:
            lines = ['vs = []']
            if node[1] == '+':
                lines.extend(inlined_lines)
                lines.extend(
                    [
                        'vs.append(self.val)',
                        'if self.failed:',
                        '    return',
                    ]
                )
            lines.extend(
                [
                    'while True:',
                    '    p = self.pos',
                ]
                + ['    ' + line for line in inlined_lines]
                + [
                    '    if self.failed:',
                    '        self._rewind(p)',
                    '        break',
                    '    vs.append(self.val)',
                    'self._succeed(vs)',
                ]
            )
        return lines

    def _pred_(self, node) -> List[str]:
        arg = self._eval(node[2][0])
        # TODO: Figure out how to statically analyze predicates to
        # catch ones that don't return booleans, so that we don't need
        # the _ParsingRuntimeError exception
        self._exception_needed = True
        return [
            'v = ' + flatten(arg)[0],
            'if v is True:',
            '    self._succeed(v)',
            'elif v is False:',
            '    self._fail()',
            'else:',
            "    raise _ParsingRuntimeError('Bad predicate value')",
        ]

    def _range_(self, node) -> List[str]:
        self._needed_methods.add('range')
        return [
            'self._range(%s, %s)'
            % (lit.encode(node[2][0][1]), lit.encode(node[2][1][1]))
        ]

    def _seq_(self, node) -> List[str]:
        lines = []
        sub_rules = self._inline_args(node[2])
        lines.extend(sub_rules[0])
        for sub_rule_lines in sub_rules[1:]:
            lines.append('if not self.failed:')
            lines.extend('    ' + line for line in sub_rule_lines)
        return lines

    def _unicat_(self, node) -> List[str]:
        self._unicodedata_needed = True
        self._needed_methods.add('unicat')
        return ['self._unicat(%s)' % lit.encode(node[1])]

    #
    # Handlers for the host nodes in the AST
    #
    def _ll_arr_(self, node) -> _FormatObj:
        if len(node[2]) == 0:
            return '[]'
        args = [self._compile(n) for n in node[2]]
        return Saw('[', Comma(args), ']')

    def _ll_call_(self, node) -> Saw:
        # There are no built-in functions that take no arguments, so make
        # sure we're not being called that way.
        # TODO: Figure out if we need this routine or not when we also
        # fix the quals.
        assert len(node[2]) != 0
        args = [self._compile(n) for n in node[2]]
        return Saw('(', Comma(args), ')')

    def _ll_getitem_(self, node) -> Saw:
        return Saw('[', self._compile(node[2][0]), ']')

    def _ll_lit_(self, node) -> str:
        return lit.encode(node[1])

    def _ll_minus_(self, node) -> Tree:
        return Tree(self._eval(node[2][0]), '-', self._eval(node[2][1]))

    def _ll_num_(self, node) -> str:
        return node[1]

    def _ll_paren_(self, node) -> _FormatObj:
        return self._eval(node[2][0])

    def _ll_plus_(self, node) -> Tree:
        return Tree(self._eval(node[2][0]), '+', self._eval(node[2][1]))

    def _ll_qual_(self, node) -> Saw:
        first = node[2][0]
        second = node[2][1]
        if first[0] == 'll_var':
            if second[0] == 'll_call':
                # first is an identifier, but it must refer to a
                # built-in function if second is a call.
                fn = first[1]
                self._needed_functions.add(fn)
                # Note that unknown functions were caught during analysis
                # so we don't have to worry about that here.
                start = f'_{fn}'
            else:
                # If second isn't a call, then first refers to a variable.
                start = self._ll_var_(first)
            saw = self._eval(second)
            if not isinstance(saw, Saw):  # pragma: no cover
                raise TypeError(second)
            saw.start = start + saw.start
            i = 2
        else:
            # TODO: We need to do typechecking, and figure out a better
            # strategy for propagating errors/exceptions.
            saw = self._eval(first)
            if not isinstance(saw, Saw):  # pragma: no cover
                raise TypeError(first)
            i = 1
        next_saw = saw
        for n in node[2][i:]:
            new_saw = self._eval(n)
            if not isinstance(new_saw, Saw):  # pragma: no cover
                raise TypeError(n)
            new_saw.start = next_saw.end + new_saw.start
            next_saw.end = new_saw
            next_saw = new_saw
        return saw

    def _ll_var_(self, node) -> str:
        return 'v_' + node[1].replace('$', '_')

    def _ll_const_(self, node) -> str:
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
