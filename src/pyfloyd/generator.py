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

import shlex
import sys
import textwrap
from typing import Dict, Optional, Set

from pyfloyd import string_literal
from pyfloyd.ast import Apply, EMinus, EPlus, Regexp, Var
from pyfloyd.analyzer import Grammar, Node
from pyfloyd.formatter import (
    flatten,
    Comma,
    FormatObj,
    ListObj,
    Lit,
    HList,
    VList,
    Saw,
    Tree,
)
from pyfloyd.version import __version__


DEFAULT_LANGUAGE = 'python'

LANG_TO_EXT = {'javascript': '.js', 'python': '.py', 'datafile': '.dpy'}

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
        self.version = __version__
        self.args = shlex.join(sys.argv[1:])


class Generator:
    def __init__(self, host, grammar: Grammar, options: GeneratorOptions):
        self._host = host
        self._grammar = grammar
        self._options = options
        self._unicodedata_needed = (
            grammar.unicat_needed
            or 'unicode_lookup' in self._grammar.needed_builtin_functions
        )

        # Expected to be overridden in subclasses
        self._indent: str = '  '
        self._map: Dict[str, str] = {}
        self._builtin_methods: Dict[str, str] = {}
        self._local_vars: Dict[str, list[str]] = {}

        self._derive_memoize()

    def _derive_memoize(self):
        def _walk(node):
            if node.t == 'apply':
                if self._options.memoize and node.rule_name.startswith('r_'):
                    name = node.rule_name[2:]
                    node.memoize = (
                        name not in self._grammar.operators
                        and name not in self._grammar.leftrec_rules
                    )
                else:
                    node.memoize = False
            else:
                for c in node.ch:
                    _walk(c)

        _walk(self._grammar.ast)

    def _derive_local_vars(self):
        def _walk(node) -> Set[str]:
            local_vars: Set[str] = set()
            local_vars.update(set(self._local_vars.get(node.t, [])))
            for c in node.ch:
                local_vars.update(_walk(c))
            return local_vars

        for _, node in self._grammar.rules.items():
            node.local_vars = _walk(node)

    def generate(self) -> str:
        raise NotImplementedError


class HardCodedGenerator(Generator):
    def _defmt(self, s: str) -> VList:
        vl = VList(textwrap.dedent(s).splitlines())
        return vl

    def _defmtf(self, s: str, **kwargs) -> VList:
        vl = VList(textwrap.dedent(s).format(**kwargs).splitlines())
        return vl

    def _fmt(self, obj: FormatObj) -> str:
        text = '\n'.join(flatten(obj, indent=self._indent)) + '\n'
        return text

    def generate(self) -> str:
        raise NotImplementedError

    def _gen_extern(self, name: str) -> str:
        raise NotImplementedError

    def _gen_invoke(self, fn: str, *args) -> FormatObj:
        raise NotImplementedError

    def _gen_thisvar(self, name: str) -> str:
        raise NotImplementedError

    def _gen_rulename(self, name: str) -> str:
        raise NotImplementedError

    def _gen_varname(self, name: str) -> str:
        r = f'v_{name.replace("$", "_")}'
        return r

    def _gen_lit(self, lit: str) -> str:
        return string_literal.encode(lit)

    def _gen_expr(self, node: Node) -> FormatObj:
        fn = getattr(self, f'_ty_{node.t}')
        return fn(node)

    def _gen_stmts(self, node: Node) -> VList:
        fn = getattr(self, f'_ty_{node.t}')
        r = fn(node)
        if not isinstance(r, VList):
            r = VList([r])
        return r

    def _gen_needed_methods(self) -> FormatObj:
        obj = VList()

        def add_method(name: str):
            nonlocal obj
            obj += ''
            obj += self._defmt(self._builtin_methods[name])

        if self._grammar.ch_needed:
            add_method('ch')
        add_method('error')
        add_method('fail')
        if self._grammar.leftrec_needed:
            add_method('leftrec')
        if self._grammar.lookup_needed:
            add_method('lookup')
        add_method('offsets')
        if self._options.memoize:
            add_method('memoize')
        if self._grammar.operator_needed:
            add_method('operator')
        if self._grammar.range_needed:
            add_method('range')
        add_method('rewind')
        if self._grammar.str_needed:
            add_method('str')
        add_method('succeed')
        if self._grammar.unicat_needed:
            add_method('unicat')
        return obj

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _ty_action(self, node: Node) -> ListObj:
        return HList(
            [
                Saw(
                    self._gen_rulename('succeed') + '(',
                    self._gen_expr(node.child),
                    ')',
                ),
                self._map['end'],
            ]
        )

    def _ty_apply(self, node: Node) -> ListObj:
        assert isinstance(node, Apply)
        if node.memoize:
            return HList(
                [
                    self._gen_invoke(
                        'memoize',
                        f"'{node.rule_name}'",
                        self._gen_rulename(node.rule_name),
                    ),
                    self._map['end'],
                ]
            )
        return HList([self._gen_invoke(node.rule_name), self._map['end']])

    def _ty_e_arr(self, node: Node) -> Lit | Saw:
        if len(node.ch) == 0:
            return Lit('[]')
        args = [self._gen_expr(c) for c in node.ch]
        return Saw('[', Comma(args), ']')

    def _ty_e_call(self, node: Node) -> Saw:
        # There are no built-in functions that take no arguments, so make
        # sure we're not being called that way.
        # TODO: Figure out if we need this routine or not when we also
        # fix the quals.
        assert len(node.ch) != 0
        args = [self._gen_expr(c) for c in node.ch]
        return Saw('(', Comma(args), ')')

    def _ty_e_const(self, node: Node) -> Lit:
        assert isinstance(node.v, str)
        return Lit(self._map[node.v])

    def _ty_e_getitem(self, node: Node) -> Saw:
        return Saw('[', self._gen_expr(node.child), ']')

    def _ty_e_lit(self, node: Node) -> Lit:
        return Lit(self._gen_lit(node.v))

    def _ty_e_minus(self, node: Node) -> Tree:
        assert isinstance(node, EMinus)
        return Tree(self._gen_expr(node.left), '-', self._gen_expr(node.right))

    def _ty_e_not(self, node: Node) -> Tree:
        return Tree(None, self._map['not'], self._gen_expr(node.child))

    def _ty_e_num(self, node: Node) -> Lit:
        assert isinstance(node.v, str)
        return Lit(node.v)

    def _ty_e_paren(self, node: Node) -> FormatObj:
        return self._gen_expr(node.child)

    def _ty_e_plus(self, node: Node) -> Tree:
        assert isinstance(node, EPlus)
        return Tree(self._gen_expr(node.left), '+', self._gen_expr(node.right))

    def _ty_e_qual(self, node: Node) -> Saw:
        first = node.ch[0]
        second = node.ch[1]
        start: Lit
        if first.t == 'e_var':
            if second.t == 'e_call':
                # first is an identifier, but it must refer to a
                # built-in function if second is a call.
                function_name = first.v
                # Note that unknown functions were caught during analysis
                # so we don't have to worry about that here.
                start = Lit(self._gen_thisvar(f'fn_{function_name}'))
            else:
                # If second isn't a call, then first refers to a variable.
                v = self._ty_e_var(first)
                assert isinstance(v, Lit)
                start = v

            saw = self._gen_expr(second)
            assert isinstance(saw, Saw), f'{second} did not return a Saw'
            saw.start = start.s + saw.start
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
            assert isinstance(next_saw.end, str)
            new_saw.start = next_saw.end + new_saw.start
            next_saw.end = new_saw
            next_saw = new_saw
        return saw

    def _ty_e_var(self, node: Node) -> FormatObj:
        assert isinstance(node, Var)
        if node.outer_scope:
            return self._gen_invoke('lookup', "'" + node.v + "'")
        if node.v in self._grammar.externs:
            return Lit(self._gen_extern(node.v))
        return Lit(self._gen_varname(node.v))

    def _ty_empty(self, node) -> ListObj:
        del node
        return HList(
            [self._gen_invoke('succeed', self._map['null']), self._map['end']]
        )

    def _ty_equals(self, node) -> ListObj:
        arg = self._gen_expr(node.child)
        return HList([self._gen_invoke('str', arg), self._map['end']])

    def _ty_leftrec(self, node) -> ListObj:
        if node.left_assoc:
            left_assoc = self._map['true']
        else:
            left_assoc = self._map['false']

        return HList(
            [
                self._gen_invoke(
                    'leftrec',
                    self._gen_rulename(node.child.v),
                    "'" + node.v + "'",
                    left_assoc,
                ),
                self._map['end'],
            ]
        )

    def _ty_lit(self, node) -> ListObj:
        expr = self._gen_lit(node.v)
        if len(node.v) == 1:
            method = 'ch'
        else:
            method = 'str'
        return HList([self._gen_invoke(method, expr), self._map['end']])

    def _ty_operator(self, node) -> ListObj:
        # Operator nodes have no children, but subrules for each arm
        # of the expression cluster have been defined and are referenced
        # from self._grammar.operators[node.v].choices.
        assert node.ch == []
        return HList(
            [
                self._gen_invoke('operator', "'" + node.v + "'"),
                self._map['end'],
            ]
        )

    def _ty_range(self, node) -> ListObj:
        return HList(
            [
                self._gen_invoke(
                    'range',
                    self._gen_lit(node.start),
                    self._gen_lit(node.stop),
                ),
                self._map['end'],
            ]
        )

    def _ty_regexp(self, node) -> ListObj:
        raise NotImplementedError

    def _ty_set(self, node) -> ListObj:
        new_node = Regexp('[' + node.v + ']')
        return self._ty_regexp(new_node)

    def _ty_unicat(self, node) -> ListObj:
        return HList(
            [
                self._gen_invoke('unicat', self._gen_lit(node.v)),
                self._map['end'],
            ]
        )
