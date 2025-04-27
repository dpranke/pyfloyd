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
import textwrap
from typing import Dict, List, Optional, Set, Union

from pyfloyd.ast import Regexp
from pyfloyd.analyzer import Grammar, Node
from pyfloyd.formatter import flatten, Comma, FormatObj, Saw, Tree
from pyfloyd import string_literal as lit


DEFAULT_LANGUAGE = 'python'

LANG_TO_EXT = {
    'javascript': '.js',
    'python': '.py',
}

EXT_TO_LANG = {v: k for k, v in LANG_TO_EXT.items()}

SUPPORTED_LANGUAGES = LANG_TO_EXT.keys()


def add_language_arguments(parser):
    parser.add_argument(
        '-l',
        '--language',
        action='store',
        choices=SUPPORTED_LANGUAGES,
        help=(
            'Language to generate (derived from the output '
            'file extension if necessary)'
        ),
    )
    parser.add_argument(
        '--js',
        '--javascript',
        dest='language',
        action='store_const',
        const='javascript',
        help='Generate Javascript code',
    )
    parser.add_argument(
        '--py',
        '--python',
        dest='language',
        action='store_const',
        const='python',
        help='Generate Python code (the default)',
    )


class GeneratorOptions:
    """Options that control the code generation.

    `language`: Which language to generate.
    `main`:     Whether to include a `main()`-like function.
    `memoize`:  Whether to memoize the intermediate results when parsing.
                Some generators may ignore this.
    `defines`:  A dictionary of generator-specific options.
    """

    def __init__(
        self,
        language: str = DEFAULT_LANGUAGE,
        main: bool = False,
        memoize: bool = False,
        defines: Optional[Dict[str, str]] = None,
    ):
        self.language = language
        self.main = main
        self.memoize = memoize
        self.defines = defines or {}


class Generator:
    def __init__(self, grammar: Grammar, options: GeneratorOptions):
        self._grammar = grammar
        self._options = options
        self._unicodedata_needed = (
            grammar.unicat_needed
            or 'unicode_lookup' in self._grammar.needed_builtin_functions
        )
        self._current_rule: str = ''
        self._base_rule_regex = re.compile(r's_(.+)_\d+$')

        # Expected to be overridden in subclasses
        self._indent: str = '  '
        self._map: Dict[str, str] = {}
        self._builtin_methods: Dict[str, str] = {}

    def generate(self) -> str:
        return self._gen_text()

    def _extern(self, varname: str) -> str:
        raise NotImplementedError

    def _invoke(self, method: str, *args) -> str:
        raise NotImplementedError

    def _thisvar(self, varname: str) -> str:
        raise NotImplementedError

    def _gen_text(self) -> str:
        raise NotImplementedError

    def _gen_expr(self, node: Node) -> FormatObj:
        fn = getattr(self, f'_ty_{node.t}')
        return fn(node)

    def _gen_stmts(self, node: Node) -> List[str]:
        try:
            fn = getattr(self, f'_ty_{node.t}')
        except Exception as e:
            import pdb; pdb.set_trace()
        return fn(node)

    def _dedent(self, s: str, level=0) -> str:
        s = textwrap.dedent(s)
        return (
            '\n'.join(
                ((self._indent * level) + line) for line in s.splitlines()
            )
            + '\n'
        )

    def _rulename(self, v: str) -> str:
        raise NotImplementedError

    def _varname(self, v: str) -> str:
        r = f'v_{v.replace("$", "_")}'
        return r

    def _find_vars(self, node) -> Set[str]:
        vs = set()
        if node.t == 'label':
            vs.add(self._varname(node.name))
        for c in node.ch:
            vs = vs.union(self._find_vars(c))
        return vs

    def _base_rule_name(self, rule_name: str) -> str:
        if rule_name.startswith('r_'):
            return rule_name[2:]
        m = self._base_rule_regex.match(rule_name)
        assert m is not None
        return m.group(1)

    def _can_fail(self, node: Node) -> bool:
        return self._grammar.can_fail(node)

    def _needed_methods(self) -> str:
        text = ''
        if self._grammar.ch_needed:
            text += self._builtin_methods['ch'] + '\n'
        text += self._builtin_methods['error'] + '\n'
        text += self._builtin_methods['fail'] + '\n'
        if self._grammar.leftrec_needed:
            text += self._builtin_methods['leftrec'] + '\n'
        if self._grammar.outer_scope_rules:
            text += self._builtin_methods['lookup'] + '\n'
        text += self._builtin_methods['offsets'] + '\n'
        if self._options.memoize:
            text += self._builtin_methods['memoize'] + '\n'
        if self._grammar.operator_needed:
            text += self._builtin_methods['operator'] + '\n'
        if self._grammar.range_needed:
            text += self._builtin_methods['range'] + '\n'
        text += self._builtin_methods['rewind'] + '\n'
        if self._grammar.str_needed:
            text += self._builtin_methods['str'] + '\n'
        text += self._builtin_methods['succeed'] + '\n'
        if self._grammar.unicat_needed:
            text += self._builtin_methods['unicat'] + '\n'
        return text

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _ty_action(self, node: Node) -> List[str]:
        obj = self._gen_expr(node.child)
        return flatten(
            Saw(self._rulename('succeed') + '(', obj, ')' + self._map['end']),
            indent=self._map['indent'],
        )

    def _ty_apply(self, node: Node) -> List[str]:
        if self._options.memoize and node.rule_name.startswith('r_'):
            name = node.rule_name[2:]
            if (
                name not in self._grammar.operators
                and name not in self._grammar.leftrec_rules
            ):
                return [
                    self._invoke(
                        'memoize', f"'{node.rule_name}'", self._rulename(node.rule_name)
                    )
                ]

        return [self._invoke(node.rule_name) + self._map['end']]

    def _ty_e_arr(self, node: Node) -> str | Saw:
        if len(node.ch) == 0:
            return '[]'
        args = [self._gen_expr(c) for c in node.ch]
        return Saw('[', Comma(args), ']')

    def _ty_e_call(self, node: Node) -> Saw:
        # There are no built-in functions that take no arguments, so make
        # sure we're not being called that way.
        # TODO: Figure out if we need this routine or not when we also
        # fix the quals.
        assert len(node[2]) != 0
        args = [self._gen_expr(n) for n in node[2]]
        return Saw('(', Comma(args), ')')

    def _ty_e_const(self, node: Node) -> str:
        return self._map[node[1]]

    def _ty_e_getitem(self, node: Node) -> Saw:
        return Saw('[', self._gen_expr(node[2][0]), ']')

    def _ty_e_lit(self, node: Node) -> str:
        return lit.encode(node.v)

    def _ty_e_minus(self, node: Node) -> Tree:
        return Tree(
            self._gen_expr(node.ch[0]), '-', self._gen_expr(node.ch[1])
        )

    def _ty_e_not(self, node: Node) -> Tree:
        return Tree(None, self._map['not'], self._gen_expr(node.child))

    def _ty_e_num(self, node: Node) -> str:
        return node[1]

    def _ty_e_paren(self, node: Node) -> FormatObj:
        return self._gen_expr(node.child)

    def _ty_e_plus(self, node: Node) -> Tree:
        return Tree(
            self._gen_expr(node.ch[0]), '+', self._gen_expr(node.ch[1])
        )

    def _ty_e_qual(self, node: Node) -> Saw:
        first = node.ch[0]
        second = node.ch[1]
        start: str
        if first.t == 'e_var':
            if second.t == 'e_call':
                # first is an identifier, but it must refer to a
                # built-in function if second is a call.
                function_name = first.v
                # Note that unknown functions were caught during analysis
                # so we don't have to worry about that here.
                start = self._thisvar(f'fn_{function_name}')
            else:
                # If second isn't a call, then first refers to a variable.
                start = self._ty_e_var(first)
            saw = self._gen_expr(second)
            assert isinstance(saw, Saw), f'{second} did not return a Saw'
            saw.start = start + saw.start
            i = 2
        else:
            # TODO: We need to do typechecking, and figure out a better
            # strategy for propagating errors/exceptions.
            saw = self._gen_expr(first)
            assert isinstance(saw, Saw), f'{first} did not return a Saw'
            i = 1
        next_saw: Saw = saw
        for n in node.ch[i:]:
            new_saw = self._gen_expr(n)
            assert isinstance(new_saw, Saw), f'{n} did not return a Saw'
            new_saw.start = next_saw.end + new_saw.start
            next_saw.end = new_saw
            next_saw = new_saw
        return saw

    def _ty_e_var(self, node: Node) -> str:
        if self._current_rule in self._grammar.outer_scope_rules:
            return self._invoke('lookup', "'" + node.v + "'")
        if node[1] in self._grammar.externs:
            return self._extern(node.v)
        return self._varname(node.v)

    def _ty_empty(self, node) -> List[str]:
        del node
        return [self._invoke('succeed', self._map['null']) + self._map['end']]

    def _ty_equals(self, node) -> List[str]:
        arg = self._gen_expr(node.child)
        return [self._invoke('str', flatten(arg)[0]) + self._map['end']]

    def _ty_leftrec(self, node) -> List[str]:
        if self._grammar.assoc.get(node.name, 'left') == 'left':
            left_assoc = self._map['true']
        else:
            left_assoc = self._map['false']

        lines = [
            self._invoke(
                'leftrec',
                self._rulename(node.child.v),
                "'" + node[1] + "'",
                left_assoc,
            )
        ]
        return lines

    def _ty_lit(self, node) -> List[str]:
        expr = lit.encode(node.v)
        if len(node.v) == 1:
            method = 'ch'
        else:
            method = 'str'
        return [self._invoke(method, expr)]

    def _ty_operator(self, node) -> List[str]:
        # Operator nodes have no children, but subrules for each arm
        # of the expression cluster have been defined and are referenced
        # from self._grammar.operators[node[1]].choices.
        assert node.ch == []
        return [self._invoke('operator', "'" + node.v + "'")]

    def _ty_range(self, node) -> List[str]:
        return [
            self._invoke(
                'range', lit.encode(node.start), lit.encode(node.stop)
            )
        ]

    def _ty_regexp(self, node) -> List[str]:
        raise NotImplementedError

    def _ty_set(self, node) -> List[str]:
        new_node = Regexp('[' + node.v + ']')
        return self._ty_regexp(new_node)

    def _ty_unicat(self, node) -> List[str]:
        return [self._invoke('unicat', lit.encode(node.v)) + self._map['end']]
