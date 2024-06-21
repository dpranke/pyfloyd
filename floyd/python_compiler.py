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

from floyd.formatter import flatten, Comma, Saw, Tree
from floyd import python_templates as py
from floyd import string_literal as lit


class _CompilerOperatorState:
    def __init__(self):
        self.prec_ops = {}
        self.rassoc = set()
        self.choices = {}


class Compiler:
    def __init__(self, grammar, classname, main_wanted=True, memoize=True):
        self._grammar = grammar
        self._classname = classname
        self._builtins = self._load_builtins()
        self._exception_needed = False
        self._main_wanted = main_wanted
        self._memoize = memoize
        self._methods = {}
        self._method_lines = []
        self._operators = {}
        self._unicodedata_needed = False

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
        # import pdb; pdb.set_trace()
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

        text += '\n'.join(
            self._builtins[name] for name in sorted(self._needed)
        )
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
        return flatten(Saw(f'self._{name}(', Saw('[', Comma(args), ']'), ')'))

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _action_(self, rule, node):
        obj = self._eval(node[2][0])
        self._methods[rule] = flatten(Saw('self._succeed(', obj, ')'))

    def _apply_(self, rule, node):
        # Unknown rules were caught in analysis so if the rule isn't
        # one of the ones in the grammar it must be a built-in one.
        if node[1] not in self._grammar.rules:
            self._needed.add(node[1])
        self._methods[rule] = [f'self._{node[1]}_()']

    def _choice_(self, rule, node):
        self._needed.add('choose')
        args, sub_rules = self._inline_args(rule, 'c', node[2])
        self._methods[rule] = self._gen_method_call('choose', args)
        for sub_rule, sub_node in sub_rules:
            self._compile(sub_node, sub_rule)

    def _empty_(self, rule, node):
        del node
        self._methods[rule] = ['self._succeed(None)']

    def _label_(self, rule, node):
        self._needed.add('bind')
        sub_rule = rule + '_l'
        self._methods[rule] = [
            'self._bind(self._%s_, %s)'
            % (sub_rule, lit.encode(node[1]))
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
        expr = lit.encode(node[1])
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
        if self._can_inline(node[2][0]):
            txt = self._inline(node[2][0])
            self._methods[rule] = [f'self._{method}({txt})']
        else:
            self._methods[rule] = [f'self._{method}(self._{sub_rule}_)']
            self._compile(node[2][0], sub_rule)

    def _pred_(self, rule, node):
        obj = self._eval(node[2][0])
        # TODO: Figure out how to statically analyze predicates to
        # catch ones that don't return booleans, so that we don't need
        # the _ParsingRuntimeError exception
        self._exception_needed = True
        self._methods[rule] = [
            'v = ' + flatten(obj)[0],
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
            % (lit.encode(node[2][0][1]), lit.encode(node[2][1][1]))
        ]

    def _seq_(self, rule, node):
        self._needed.add('seq')
        needs_scope = self._has_labels(node)
        lines = []
        if needs_scope:
            lines.append(f"self._push('{rule}')")
        args, sub_rules = self._inline_args(rule, 's', node[2])
        lines += self._gen_method_call('seq', args)
        if needs_scope:
            lines.append(f"self._pop('{rule}')")
        self._methods[rule] = lines
        for sub_rule, sub_node in sub_rules:
            self._compile(sub_node, sub_rule)

    def _unicat_(self, rule, node):
        self._unicodedata_needed = True
        self._needed.add('unicat')
        self._methods[rule] = [
            'self._unicat(%s)' % lit.encode(node[1])
        ]

    def _inline_args(self, rule, sub_rule_type, children):
        args = []
        sub_rules = []
        i = 0
        for child in children:
            if self._can_inline(child):
                args.append(self._inline(child))
            else:
                sub_rule = f'{rule}_{sub_rule_type}{i}'
                args.append(f'self._{sub_rule}_')
                sub_rules.append((sub_rule, child))
                i += 1
        return args, sub_rules

    def _can_inline(self, node):
        if node[0] in ('lit', 'apply'):
            return True
        if node[0] == 'seq' and len(node[2]) == 1:
            return True
        if node[0] == 'post' and node[2][0][0] in ('lit', 'apply'):
            return True
        return False

    def _inline(self, node):
        if node[0] == 'apply':
            if node[1] not in self._grammar.rules:
                self._needed.add(node[1])
            return f'self._{node[1]}_'
        self._compile(node, 'tmp')
        txt = self._methods['tmp'][0]
        del self._methods['tmp']
        return 'lambda: ' + txt

    #
    # Handlers for the host nodes in the AST
    #
    def _ll_arr_(self, node):
        if len(node[2]) == 0:
            return '[]'
        args = [self._eval(n) for n in node[2]]
        return Saw('[', Comma(args), ']')

    def _ll_call_(self, node):
        # There are no built-in functions that take no arguments, so make
        # sure we're not being called that way.
        # TODO: Figure out if we need this routine or not when we also
        # fix the quals.
        assert len(node[2]) != 0
        args = [self._eval(n) for n in node[2]]
        return Saw('(', Comma(args), ')')

    def _ll_getitem_(self, node):
        return Saw('[', self._eval(node[2][0]), ']')

    def _ll_lit_(self, node):
        return lit.encode(node[1])

    def _ll_minus_(self, node):
        return Tree(self._eval(node[2][0]), '-', self._eval(node[2][1]))

    def _ll_num_(self, node):
        return node[1]

    def _ll_paren_(self, node):
        return self._eval(node[2][0])

    def _ll_plus_(self, node):
        return Tree(self._eval(node[2][0]), '+', self._eval(node[2][1]))

    def _ll_qual_(self, node):
        if node[2][0][0] == 'll_var':
            if node[2][1][0] == 'll_call':
                fn = node[2][0][1]
                self._needed.add(fn)
                # Note that unknown functions were caught during analysis
                # so we don't have to worry about that here.
                start = f'self._{fn}'
            else:
                start = self._eval(node[2][0])
            saw = self._eval(node[2][1])
            saw.start = start + saw.start
            i = 2
        else:
            saw = self._eval(node[2][0])
            i = 1
        next_saw = saw
        for n in node[2][i:]:
            new_saw = self._eval(n)
            new_saw.start = next_saw.end + new_saw.start
            next_saw.end = new_saw
            next_saw = new_saw
        return saw

    def _ll_var_(self, node):
        return "self._get('%s')" % node[1]

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
