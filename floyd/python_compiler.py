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
        self._needed = set()
        self._methods = {}
        self._method_lines = []
        self._exception_needed = False
        self._unicodedata_needed = False
        self._operators = {}

    def compile(self):  # pylint: disable=too-many-statements
        for rule, node in self._grammar.rules.items():
            self._compile(node, rule, top_level=True)

        if self._unicodedata_needed:
            unicodedata_import = 'import unicodedata\n\n'
        else:
            unicodedata_import = ''

        # These methods are always needed.
        self._needed.update(
            {
                'err_offsets',
                'err_str',
                'fail',
                'rewind',
                'succeed',
            }
        )

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
            text += '        self.operators = {}\n'
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
                    text += "            '%s': self._%s,\n" % (
                        op,
                        o.choices[op],
                    )
                text += '        }\n'
                text += "        self.operators['%s'] = o\n" % rule
        text += '\n'

        if self._exception_needed:
            text += py.PARSE_WITH_EXCEPTION.format(
                starting_rule=self._grammar.starting_rule
            )
        else:
            text += py.PARSE.format(starting_rule=self._grammar.starting_rule)

        methods = set()
        for rule in self._grammar.rules.keys():
            methods.add(rule)
            text += self._method_text(
                rule, self._methods[rule], memoize=self._memoize
            )

            # Do not memoize the internal rules; it's not clear if that'd
            # ever be useful.
            names = [
                m
                for m in self._methods
                if m.startswith(rule + '_') and m not in methods
            ]
            for name in sorted(names):
                methods.add(name)
                text += self._method_text(
                    name, self._methods[name], memoize=False
                )
        text += '\n'

        builtins = self._load_builtins()
        text += '\n'.join(builtins[name] for name in sorted(self._needed))

        if self._main_wanted:
            text += py.MAIN_FOOTER
        else:
            text += py.DEFAULT_FOOTER
        return text, None

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

    def _method_text(self, name, lines, memoize):
        text = '\n'
        text += '    def _%s_(self):\n' % name
        if memoize:
            text += '        r = self.cache.get(("%s", self.pos))\n' % name
            text += '        if r is not None:\n'
            text += '            self.val, self.failed, self.pos = r\n'
            text += '            return\n'
            text += '        pos = self.pos\n'
        for line in lines:
            text += '        %s\n' % line
        if memoize:
            text += '        self.cache[("%s", pos)] = (' % name
            text += 'self.val, self.failed, self.pos)\n'
        return text

    def _compile(self, node, rule, sub_type='', index=0, top_level=False):
        assert node
        assert not self._method_lines
        # TODO: Figure out how to handle inlining methods more consistently
        # so that we don't have the special-casing logic here.
        if node[0] == 'apply':
            # Unknown rules were caught in analysis so if the rule isn't
            # one of the ones in the grammar it must be a built-in one.
            if node[1] not in self._grammar.rules:
                self._needed.add(node[1])
            return 'self._%s_' % node[1]
        if node[0] == 'lit' and not top_level:
            expr = string_literal.encode(node[1])
            if len(node[1]) == 1:
                self._needed.add('ch')
                return 'lambda: self._ch(%s)' % (expr,)
            self._needed.add('ch')
            self._needed.add('str')
            return 'lambda: self._str(%s)' % (expr,)
        if sub_type:
            sub_rule = '%s__%s%d' % (rule, sub_type, index)
        else:
            sub_rule = rule
        fn = getattr(self, '_%s_' % node[0])
        if top_level and node[0] in ('seq', 'choice'):
            fn(sub_rule, node, top_level)
        else:
            fn(sub_rule, node)

        assert sub_rule not in self._methods
        self._methods[sub_rule] = self._method_lines
        self._method_lines = []
        return 'self._%s_' % sub_rule

    def _fits(self, line):
        return len(line) < 72

    def _eval_rule(self, rule, node):
        fn = getattr(self, '_' + node[0] + '_')
        return fn(rule, node)

    def _ext(self, *lines):
        self._method_lines.extend(lines)

    def _indent(self, s):
        return self._depth * '    ' + s

    def _flatten(self, obj):
        lines = self._flatten_rec(obj, 0, self._max_depth(obj) + 1)
        for line in lines[:-1]:
            self._ext(line.rstrip())

        # TODO: Figure out how to handle blank lines at the end of a method
        # better. There will be a blank line if obj[-1] == UN.
        if lines[-1].rstrip():
            self._ext(lines[-1].rstrip())

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

    def _max_depth(self, obj):
        if isinstance(obj, list):
            return max(self._max_depth(el) + 1 for el in obj)
        return 1

    def _has_labels(self, node):
        if node and node[0] in ('label', 'll_var'):
            return True
        for n in node:
            if isinstance(n, list) and self._has_labels(n):
                return True
        return False

    def _chain(self, name, args):
        obj = ['self._', name, '(', IN, '[', IN]
        for i in range(len(args)):  # pylint: disable=consider-using-enumerate
            obj.append(args[i])
            if i < len(args) - 1:
                obj.append(',')
                obj.append(NL)
            else:
                obj.append(',')
                obj.append(UN)
        obj.extend([']', UN, ')'])
        self._flatten(obj)

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _choice_(self, rule, node, top_level=False):
        self._needed.add('choose')
        sub_rules = [
            self._compile(sub_node, rule, 'c', i, top_level)
            for i, sub_node in enumerate(node[2])
        ]
        self._chain('choose', sub_rules)

    def _seq_(self, rule, node, top_level=False):
        self._needed.add('seq')
        sub_rules = [
            self._compile(sub_node, rule, 's', i)
            for i, sub_node in enumerate(node[2])
        ]
        needs_scope = top_level and self._has_labels(node)
        if needs_scope:
            self._flatten(["self._push('", rule, "')"])
        self._chain('seq', sub_rules)
        if needs_scope:
            self._flatten(["self._pop('", rule, "')"])

    def _lit_(self, rule, node):
        del rule
        expr = string_literal.encode(node[1])
        if len(node[1]) == 1:
            method = 'ch'
        else:
            method = 'str'
            self._needed.add('ch')
        self._needed.add(method)
        self._flatten(['self._', method, '(', expr, ')'])

    def _label_(self, rule, node):
        self._needed.add('bind')
        sub_rule = self._compile(node[2][0], rule + '_l')
        self._flatten(
            [
                'self._bind(',
                sub_rule,
                ', ',
                string_literal.encode(node[1]),
                ')',
            ]
        )

    def _leftrec_(self, rule, node):
        sub_rule = self._compile(node[2][0], rule + '_l')
        self._needed.add('leftrec')
        left_assoc = self._grammar.assoc.get(node[1], 'left') == 'left'
        needs_scope = self._has_labels(node)
        if needs_scope:
            self._flatten(["self._push('", rule, "')"])
        self._flatten(
            [
                'self._leftrec(',
                OI,
                sub_rule,
                ',',
                "'",
                node[1],
                "'",
                ',',
                str(left_assoc),
                OU,
                ')',
            ]
        )
        if needs_scope:
            self._flatten(["self._pop('", rule, "')"])

    def _action_(self, rule, node):
        self._depth = 0
        obj = self._eval_rule(rule, node[2][0])
        self._flatten(['self._succeed(', OI, obj, OU, ')'])

    def _empty_(self, rule, node):
        del rule
        del node
        self._flatten(['self._succeed(None)'])

    def _not_(self, rule, node):
        self._needed.add('not')
        sub_rule = self._compile(node[2][0], rule + '_n')
        self._flatten(['self._not(', sub_rule, ')'])

    def _operator_(self, rule, node):
        self._needed.add('operator')
        o = _CompilerOperatorState()
        for i, operator in enumerate(node[2]):
            op = operator[1][0]
            prec = operator[1][1]
            sub_rule = operator[2][0]
            o.prec_ops.setdefault(prec, []).append(op)
            if self._grammar.assoc.get(op) == 'right':
                o.rassoc.add(op)
            o.choices[op] = '%s__o%d_' % (rule, i)
            self._compile(sub_rule, rule, 'o', i, self._has_labels(sub_rule))
        self._operators[rule] = o
        self._flatten(['self._operator(', "'%s'" % rule, ',', SN, '[]', ')'])

    def _paren_(self, rule, node):
        sub_rule = self._compile(node[2][0], rule + '_g')
        if sub_rule.startswith('lambda:'):
            self._flatten([sub_rule[8:]])
        else:
            self._flatten(['(', sub_rule, ')()'])

    def _post_(self, rule, node):
        sub_rule = self._compile(node[2][0], rule + '_p')
        if node[1] == '?':
            method = 'opt'
        elif node[1] == '+':
            method = 'plus'
            self._needed.add('star')
        else:
            assert node[1] == '*'
            method = 'star'
        self._needed.add(method)
        self._flatten(['self._', method, '(', OI, sub_rule, OU, ')'])

    def _pred_(self, rule, node):
        obj = self._eval_rule(rule, node[2][0])
        # TODO: Figure out how to statically analyze predicates to
        # catch ones that don't return booleans, so that we don't need
        # the _ParsingRuntimeError exception
        self._exception_needed = True
        self._flatten(
            [
                'v = ',
                obj,
                NL,
                'if v is True:',
                IN,
                'self._succeed(v)',
                UN,
                'elif v is False:',
                IN,
                'self._fail()',
                UN,
                'else:',
                IN,
                "raise _ParsingRuntimeError('Bad predicate value')",
                UN,
            ]
        )

    def _range_(self, rule, node):
        del rule
        self._needed.add('range')
        self._flatten(
            [
                'self._range(',
                string_literal.encode(node[2][0][1]),
                ', ',
                string_literal.encode(node[2][1][1]),
                ')',
            ]
        )

    def _unicat_(self, rule, node):
        del rule
        self._unicodedata_needed = True
        self._needed.add('unicat')
        self._flatten(['self._unicat(', string_literal.encode(node[1]), ')'])

    #
    # Handlers for the host nodes in the AST
    #

    def _ll_arr_(self, rule, node):
        line = ['[', OI]
        if len(node[2]):
            line.append(self._eval_rule(rule, node[2][0]))
            for e in node[2][1:]:
                line.extend([',', SN, self._eval_rule(rule, e)])
        line.extend([OU, ']'])
        return line

    def _ll_call_(self, rule, node):
        line = ['(', OI]

        # There are no built-in functions that take no arguments, so make
        # sure we're not being called that way.
        assert len(node[2]) != 0

        line.append(self._eval_rule(rule, node[2][0]))
        for e in node[2][1:]:
            line.extend([',', SN, self._eval_rule(rule, e)])
        line.extend([OU, ')'])
        return line

    def _ll_getitem_(self, rule, node):
        return ['['] + self._eval_rule(rule, node[2][0]) + [']']

    def _ll_lit_(self, rule, node):
        del rule
        return [string_literal.encode(node[1])]

    def _ll_minus_(self, rule, node):
        return (
            self._eval_rule(rule, node[2][0])
            + [SN, '- ']
            + self._eval_rule(rule, node[2][1])
        )

    def _ll_num_(self, rule, node):
        del rule
        return [node[1]]

    def _ll_paren_(self, rule, node):
        return self._eval_rule(rule, node[2][0])

    def _ll_plus_(self, rule, node):
        return (
            self._eval_rule(rule, node[2][0])
            + [SN, '+ ']
            + self._eval_rule(rule, node[2][1])
        )

    def _ll_qual_(self, rule, node):
        if node[2][1][0] == 'll_call':
            self._needed.add(node[2][0][1])
            v = ['self._%s' % node[2][0][1]]
        else:
            v = self._eval_rule(rule, node[2][0])
        for p in node[2][1:]:
            v += self._eval_rule(rule, p)
        return [v]

    def _ll_var_(self, rule, node):
        del rule
        return ["self._get('%s')" % node[1]]

    def _ll_const_(self, rule, node):
        del rule
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