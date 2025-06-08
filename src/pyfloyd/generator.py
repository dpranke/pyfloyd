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

import argparse
import shlex
import sys
from typing import Any, Optional, Sequence, Union

import pyfloyd
from pyfloyd import (
    attr_dict,
    datafile,
    support,
    type_desc,
)


DEFAULT_GENERATOR = 'datafile'


class GeneratorOptions(attr_dict.AttrDict):
    def __init__(self, *args, **kwargs):
        self.argv = []
        self.command_line = ''
        self.dialect = ''
        self.generator = pyfloyd.DEFAULT_GENERATOR
        self.indent = None
        self.language = None
        self.line_length = None
        self.main = False
        self.memoize = None
        self.output_as_format_tree = False
        self.as_json = False
        self.template = None
        self.version = pyfloyd.__version__
        self.unicodedata_needed = None
        super().__init__(*args, **kwargs)


class Generator:
    name: str = ''
    ext: str = ''
    indent: Union[int, str] = 2
    line_length: Optional[int] = 79
    help_str: Optional[str] = None

    def __init__(
        self,
        host: support.Host,
        data: dict[str, Any],
        options: GeneratorOptions,
    ):
        self.host = host
        data = data or {}
        self.data = attr_dict.AttrDict(
            name=self.name,
            starting_template=None,
            grammar=None,
            indent=self.indent,
            line_length=self.line_length,
            ext=self.ext,
            local_vars={},
            templates={},
            generator_options=options,
        )
        for k, v in data.items():
            self.data[k] = v

        self.grammar = self.data.grammar
        self.options = options
        self._update_options(options)

    def _update_options(self, options):
        self.data.generator_options = options
        self.options = self.data.generator_options

        if self.options.indent is not None:
            if isinstance(self.options.indent, int):
                self.data.indent = ' ' * self.options.indent
            else:
                self.data.indent = self.options.indent
            self.indent = self.data.indent
        elif self.data.indent is not None:
            if isinstance(self.data.indent, int):
                self.data.indent = ' ' * self.data.indent
            self.indent = self.data.indent
        else:
            if isinstance(self.indent, int):
                self.indent = ' ' * self.indent
            self.data.indent = self.indent

        if self.options.line_length is not None:
            self.line_length = self.data.line_length = self.options.line_length
        elif self.data.line_length is not None:
            self.line_length = self.data.line_length
        else:
            self.data.line_length = self.line_length

        assert self.indent == self.data.indent
        assert self.line_length == self.data.line_length

    def _process_grammar(self, local_var_map):
        grammar = self.data.grammar
        self.data.generator_options.unicodedata_needed = (
            grammar.unicat_needed
            or 'unicode_lookup' in grammar.needed_builtin_functions
            or 'ulookup' in grammar.needed_builtin_functions
        )

        self._derive_local_vars(grammar, local_var_map)
        self._derive_memoize()

    def _derive_memoize(self):
        grammar = self.grammar
        if self.data.generator_options.memoize is None:
            if 'memoize' in grammar.externs:
                memoize = grammar.externs['memoize']
            else:
                memoize = False
            self.data.generator_options.memoize = memoize
        if not self.data.generator_options.memoize:
            return

        def _walk(node):
            if node.t == 'apply':
                if node.rule_name.startswith('r_'):
                    name = node.rule_name[2:]
                    node.memoize = (
                        name not in self.grammar.operators
                        and name not in grammar.leftrec_rules
                    )
                else:
                    node.memoize = False
            else:
                for c in node.ch:
                    _walk(c)

        grammar.needed_operators = sorted(
            grammar.needed_operators + ['memoize']
        )
        _walk(grammar.ast)

    def _derive_local_vars(self, grammar, local_var_map):
        def _walk(node) -> dict[str, Any]:
            local_vars: dict[str, Any] = {}
            for decl in local_var_map.get(node.t, []):
                name, ty = decl.split(' ', maxsplit=1)
                local_vars[name] = type_desc.from_str(ty).to_dict()
            for c in node.ch:
                local_vars.update(_walk(c))
            return local_vars

        for _, node in grammar.rules.items():
            node.local_vars = _walk(node)

    def generate(self) -> str:
        raise NotImplementedError


def add_arguments(
    parser: argparse.ArgumentParser,
    generators: Optional[Sequence[type[Generator]]] = None,
) -> None:
    options = GeneratorOptions()
    if generators:
        parser.add_argument(
            '-g',
            '--generator',
            action='store',
            choices=[gen.name.lower() for gen in generators],
            default=pyfloyd.DEFAULT_GENERATOR,
            help=f'Generator to use (default is {pyfloyd.DEFAULT_GENERATOR})',
        )
        for lang in pyfloyd.KNOWN_LANGUAGES:
            ext = pyfloyd.KNOWN_LANGUAGES[lang]
            tmpl = pyfloyd.KNOWN_TEMPLATES[ext]
            if lang.lower() == pyfloyd.DEFAULT_LANGUAGE.lower():
                def_str = ' (the default)'
            else:
                def_str = ''
            help_str = f'Generate {lang} code (using templates)' + def_str
            parser.add_argument(
                '--' + lang,
                '--' + ext[1:],
                action='store_const',
                dest='template',
                const=tmpl,
                help=help_str,
            )

    parser.add_argument(
        '--indent',
        action='store',
        default=None,
        help='indentation to use in output (default is language-specific)',
    )
    parser.add_argument(
        '-L',
        '--dialect',
        action='store',
        default=None,
        help='Dialect (variant) of the language or template to use',
    )
    parser.add_argument(
        '--generator-options',
        '-G',
        action='append',
        default=[],
        metavar='DATAFILE-STRING',
        help='Pass arbitrary options to the generator',
    )
    parser.add_argument(
        '--output-as-format-tree',
        '--ft',
        action='store_true',
        default=False,
        help=(
            'Return the generated output as a tree of format objects '
            'instead of as a formatted string'
        ),
    )
    parser.add_argument(
        '-T',
        '--template',
        '--datafile-template',
        action='store',
        default=options.template,
        help=(
            f'datafile template to use for code generation '
            f'(default is "{pyfloyd.DEFAULT_TEMPLATE}")'
        ),
    )
    parser.add_argument(
        '--line-length',
        action='store',
        type=int,
        default=None,
        help='Line length to use (default is language-specific)',
    )
    parser.add_argument(
        '-m',
        '--main',
        action=argparse.BooleanOptionalAction,
        default=options.main,
        help=(
            'include a main() function in the generated code if possible '
            '(off by default)'
        ),
    )


def options_from_args(args: argparse.Namespace, argv: Sequence[str]):
    """Returns a dict containing the value of the generator args."""
    d = GeneratorOptions()
    vs = vars(args)
    for name in d:
        if name in vs:
            if name == 'version':
                # This is the boolean flag to show the version, not
                # the actual version string.
                continue
            d[name] = vs[name]
    if hasattr(args, 'generator_options') and args.generator_options:
        for opt_str in args.generator_options:
            opt_d = datafile.loads(opt_str)
            d.update(opt_d)

    d.argv = argv[1:] if argv else sys.argv[1:]
    d.command_line = shlex.join(d['argv'])
    if args.indent is None:
        pass
    elif args.indent.isspace():
        d.indent = args.indent
    elif args.indent.isdigit():
        d.indent = int(args.indent) * ' '
    else:
        d.indent = args.indent

    return d
