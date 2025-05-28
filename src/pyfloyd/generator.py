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
from typing import Optional, Sequence, Union

import pyfloyd
from pyfloyd import (
    attr_dict,
    datafile,
    grammar as m_grammar,
    support,
)


DEFAULT_GENERATOR = 'datafile'


class GeneratorOptions(attr_dict.AttrDict):
    def __init__(self, *args, **kwargs):
        self.argv = []
        self.command_line = ''
        self.dialect = ''
        self.generator = pyfloyd.DEFAULT_GENERATOR
        self.generator_options = {}
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
        grammar: m_grammar.Grammar,
        options: GeneratorOptions,
    ):
        self.host = host
        self.grammar = grammar
        self.options = options

        # Derive option values from the grammar if need be;
        # they will also be overridden by the codegen templates.
        if self.options.line_length is None:
            self.options.line_length = self.line_length
        if self.options.indent is None:
            self.options.indent = self.indent
        if isinstance(self.options.indent, int):
            self.options.indent = ' ' * self.options.indent
        self.options.unicodedata_needed = (
            grammar.unicat_needed
            or 'unicode_lookup' in self.grammar.needed_builtin_functions
        )

        self._derive_memoize()

    def _derive_memoize(self):
        def _walk(node):
            if node.t == 'apply':
                if node.rule_name.startswith('r_'):
                    name = node.rule_name[2:]
                    node.memoize = (
                        name not in self.grammar.operators
                        and name not in self.grammar.leftrec_rules
                    )
                else:
                    node.memoize = False
            else:
                for c in node.ch:
                    _walk(c)

        if self.options.memoize is None:
            if 'memoize' in self.grammar.externs:
                self.options.memoize = self.grammar.externs['memoize']
            else:
                self.options.memoize = False

        if self.options.memoize:
            self.grammar.needed_operators = sorted(
                self.grammar.needed_operators + ['memoize']
            )
            _walk(self.grammar.ast)

    def generate(self) -> str:
        raise NotImplementedError


def add_arguments(
    parser: argparse.ArgumentParser,
    generators: Sequence[type[Generator]],
) -> None:
    options = GeneratorOptions()
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
        default=options.indent,
        help='indentation to use in output (default is language-specific)',
    )
    parser.add_argument(
        '-L',
        '--dialect',
        action='store',
        default=options.dialect,
        help='Dialect (variant) of the language or template to use',
    )
    parser.add_argument(
        '--generator-options',
        '-G',
        action=datafile.ArgparseAppendAction,
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
        default=options.line_length,
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
    if hasattr(args, 'generator_options'):
        if isinstance(args.generator_options, dict):
            d.update(args.generator_options)
        elif isinstance(args.generator_options, list):
            for opt_str in args.generator_options:
                opt_d = datafile.loads(opt_str)
                d.update(opt_d)

    d.argv = argv[1:] if argv else sys.argv[1:]
    d.command_line = shlex.join(d['argv'])
    return d
