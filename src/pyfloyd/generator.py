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
from typing import Dict, List, Optional, Set, Union

from pyfloyd.analyzer import Grammar
from pyfloyd.formatter import flatten, Comma, Saw, Tree
from pyfloyd import string_literal as lit

FormatObj = Union[Comma, Tree, Saw, str]


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
        self._exception_needed = False
        self._unicodedata_needed = (
            grammar.unicat_needed
            or 'unicode_lookup' in self._grammar.needed_builtin_functions
        )
        self._current_rule = None
        self._base_rule_regex = re.compile(r's_(.+)_\d+$')

    def generate(self) -> str:
        self._gen_rules()
        return self._gen_text()

    def _gen_expr(self, node) -> List[str]:
        fn = getattr(self, f'_ty_{node[0]}')
        return fn(node)

    def _varname(self, v):
        r = f'v_{v.replace("$", "_")}'
        return r

    def _find_vars(self, node) -> Set[str]:
        vs = set()
        if node[0] == 'label':
            vs.add(self._varname(node[1]))
        for c in node[2]:
            vs = vs.union(self._find_vars(c))
        return vs

    def _base_rule_name(self, rule_name):
        if rule_name.startswith('r_'):
            return rule_name[2:]
        return self._base_rule_regex.match(rule_name).group(1)

    def _can_fail(self, node, inline):
        if node[0] in ('action', 'empty', 'opt', 'star'):
            return False
        if node[0] == 'apply':
            if node[1] in ('r_any', 'r_end'):
                return True
            return self._can_fail(self._grammar.rules[node[1]], inline=False)
        if node[0] == 'label':
            # When the code for a label is being inlined, if the child
            # node can fail, its return will exit the outer method as well,
            # so we don't have to worry about it. At that point, then
            # we just have the label code itself, which can't fail.
            # When the code isn't being inlined into the outer method,
            # we do have to include the failure of the child node.
            # TODO: This same reasoning may be true for other types of nodes.
            return False if inline else self._can_fail(node[2][0], inline)
        if node[0] in ('label', 'paren', 'run'):
            return self._can_fail(node[2][0], inline)
        if node[0] == 'count':
            return node[1][0] != 0
        if node[0] in ('leftrec', 'operator'):
            # TODO: Figure out if there's a way to tell if these can not fail.
            return True
        if node[0] == 'choice':
            r = all(self._can_fail(n, inline) for n in node[2])
            return r
        if node[0] == 'scope':
            return self._can_fail(node[2][0], False)
        if node[0] == 'seq':
            r = any(self._can_fail(n, inline) for n in node[2])
            return r

        # You might think that if a not's child node can fail, then
        # the not can't fail, but it doesn't work that way. If the
        # child == ['lit', 'foo'], then it'll fail if foo isn't next,
        # so it can fail, but ['not', [child]] can fail also (if
        # foo is next).
        # Note that some regexps might not fail, but to figure that
        # out we'd have to analyze the regexp itself, which I don't want to
        # do yet.
        assert node[0] in (
            'ends_in',
            'equals',
            'lit',
            'not',
            'not_one',
            'plus',
            'pred',
            'range',
            'regexp',
            'set',
            'unicat',
        )
        return True

    def _needed_methods(self):
        text = ''
        if self._grammar.ch_needed:
            text += self._builtin_methods['ch'] + '\n'
        text += self._builtin_methods['error'] + '\n'
        text += self._builtin_methods['fail']  + '\n'
        if self._grammar.leftrec_needed:
            text += self._builtin_methods['leftrec']  + '\n'
        if self._grammar.outer_scope_rules:
            text += self._builtin_methods['lookup'] + '\n'
        text += self._builtin_methods['offsets']  + '\n'
        if self._options.memoize:
            text += self._builtin_methods['memoize'] + '\n'
        if self._grammar.operator_needed:
            text += self._builtin_methods['operator']  + '\n'
        if self._grammar.range_needed:
            text += self._builtin_methods['range'] + '\n'
        text += self._builtin_methods['rewind']  + '\n'
        if self._grammar.str_needed:
            text += self._builtin_methods['str'] + '\n'
        text += self._builtin_methods['succeed']  + '\n'
        if self._grammar.unicat_needed:
            text += self._builtin_methods['unicat']  + '\n'
        text += '\n'
        return text

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _ty_action(self, node) -> List[str]:
        obj = self._gen_expr(node[2][0])
        return flatten(
            Saw(self._rulename('succeed') + '(', obj, ')' + self._map['end']),
            indent=self._map['indent'],
        )

    def _ty_apply(self, node) -> List[str]:
        if self._options.memoize and node[1].startswith('r_'):
            name = node[1][2:]
            if (
                name not in self._grammar.operators
                and name not in self._grammar.leftrec_rules
            ):
                return [
                    self._invoke(
                        'memoize', f"'{node[1]}'", self._rulename(node[1])
                    )
                ]

        return [self._invoke(node[1]) + self._map['end']]

    def _ty_e_arr(self, node) -> FormatObj:
        if len(node[2]) == 0:
            return '[]'
        args = [self._gen_expr(n) for n in node[2]]
        return Saw('[', Comma(args), ']')

    def _ty_e_call(self, node) -> Saw:
        # There are no built-in functions that take no arguments, so make
        # sure we're not being called that way.
        # TODO: Figure out if we need this routine or not when we also
        # fix the quals.
        assert len(node[2]) != 0
        args = [self._gen_expr(n) for n in node[2]]
        return Saw('(', Comma(args), ')')

    def _ty_e_const(self, node) -> str:
        return self._map[node[1]]

    def _ty_e_getitem(self, node) -> Saw:
        return Saw('[', self._gen_expr(node[2][0]), ']')

    def _ty_e_lit(self, node) -> str:
        return lit.encode(node[1])

    def _ty_e_minus(self, node) -> Tree:
        return Tree(
            self._gen_expr(node[2][0]), '-', self._gen_expr(node[2][1])
        )

    def _ty_e_not(self, node) -> Tree:
        return Tree(None, self._map['not'], self._gen_expr(node[2][0]))

    def _ty_e_num(self, node) -> str:
        return node[1]

    def _ty_e_paren(self, node) -> FormatObj:
        return self._gen_expr(node[2][0])

    def _ty_e_plus(self, node) -> Tree:
        return Tree(
            self._gen_expr(node[2][0]), '+', self._gen_expr(node[2][1])
        )

    def _ty_e_qual(self, node) -> Saw:
        first = node[2][0]
        second = node[2][1]
        if first[0] == 'e_var':
            if second[0] == 'e_call':
                # first is an identifier, but it must refer to a
                # built-in function if second is a call.
                fn = first[1]
                # Note that unknown functions were caught during analysis
                # so we don't have to worry about that here.
                start = self._thisvar(f'fn_{fn}')
            else:
                # If second isn't a call, then first refers to a variable.
                start = self._ty_e_var(first)
            saw = self._gen_expr(second)
            if not isinstance(saw, Saw):  # pragma: no cover
                raise TypeError(second)
            saw.start = start + saw.start
            i = 2
        else:
            # TODO: We need to do typechecking, and figure out a better
            # strategy for propagating errors/exceptions.
            saw = self._gen_expr(first)
            if not isinstance(saw, Saw):  # pragma: no cover
                raise TypeError(first)
            i = 1
        next_saw = saw
        for n in node[2][i:]:
            new_saw = self._gen_expr(n)
            if not isinstance(new_saw, Saw):  # pragma: no cover
                raise TypeError(n)
            new_saw.start = next_saw.end + new_saw.start
            next_saw.end = new_saw
            next_saw = new_saw
        return saw

    def _ty_e_var(self, node) -> str:
        if self._current_rule in self._grammar.outer_scope_rules:
            return self._invoke('lookup', "'" + node[1] + "'")
        if node[1] in self._grammar.externs:
            return self._extern(node[1])
        return self._varname(node[1])

    def _ty_empty(self, node) -> List[str]:
        del node
        return [self._invoke('succeed', self._map['null']) + self._map['end']]

    def _ty_equals(self, node) -> List[str]:
        arg = self._gen_expr(node[2][0])
        return [self._invoke('str', flatten(arg)[0]) + self._map['end']]

    def _ty_leftrec(self, node) -> List[str]:
        if self._grammar.assoc.get(node[1], 'left') == 'left':
            left_assoc = self._map['true']
        else:
            left_assoc = self._map['false']

        lines = [
            self._invoke(
                'leftrec',
                self._rulename(node[2][0][1]),
                "'" + node[1] + "'",
                left_assoc,
            )
        ]
        return lines

    def _ty_lit(self, node) -> List[str]:
        expr = lit.encode(node[1])
        if len(node[1]) == 1:
            method = 'ch'
        else:
            method = 'str'
        return [self._invoke(method, expr)]

    def _ty_operator(self, node) -> List[str]:
        # Operator nodes have no children, but subrules for each arm
        # of the expression cluster have been defined and are referenced
        # from self._grammar.operators[node[1]].choices.
        assert node[2] == []
        return [self._invoke('operator', "'" + node[1] + "'")]

    def _ty_range(self, node) -> List[str]:
        return [
            self._invoke(
                'range', lit.encode(node[1][0]), lit.encode(node[1][1])
            )
        ]

    def _ty_set(self, node) -> List[str]:
        new_node = ['regexp', '[' + node[1] + ']', []]
        return self._ty_regexp(new_node)

    def _ty_unicat(self, node) -> List[str]:
        return [self._invoke('unicat', lit.encode(node[1])) + self._map['end']]
