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
from dataclasses import dataclass
import os
import shlex
from typing import Dict, Optional, Set, Union

from pyfloyd import attr_dict
from pyfloyd import datafile
from pyfloyd.version import __version__


@dataclass
class LanguageDescriptor:
    name: str
    ext: str
    printed: str
    indent: Optional[Union[int | str]] = '    '
    line_length: int = 79
    dialect: Optional[str] = None
    help_str: Optional[str] = None


LANGUAGES = [
    LanguageDescriptor('javascript', 'js', 'JavaScript', indent=2),
    LanguageDescriptor('python', 'py', 'Python'),
    LanguageDescriptor(
        'datafile',
        'dft',
        'datafile template',
        help_str='Generate code using a datafile template',
    ),
]

DEFAULT_LANGUAGE = 'python'

LANGUAGE_MAP = {lang.name: lang for lang in LANGUAGES}

EXT_TO_LANG = {lang.ext: lang for lang in LANGUAGES}

SUPPORTED_LANGUAGES = [lang.name for lang in LANGUAGES]

DEFAULT_TEMPLATE = os.path.join(os.path.dirname(__file__), 'python.dft')


class GeneratorOptions(attr_dict.AttrDict):
    def __init__(self, *args, **kwargs):
        self.argv = None
        self.command_line = None
        self.dialect = None
        self.formatter_list = False
        self.generator_options = None
        self.indent = None
        self.language = DEFAULT_LANGUAGE
        self.line_length = None
        self.main = False
        self.memoize = None
        self.template = DEFAULT_TEMPLATE
        self.version = __version__
        self.unicodedata_needed = None
        super().__init__(*args, **kwargs)


def add_arguments(parser, language=DEFAULT_LANGUAGE):
    default = GeneratorOptions(language=language)
    parser.add_argument(
        '-l',
        '--language',
        action='store',
        choices=SUPPORTED_LANGUAGES,
        default=default.language,
        help=(
            'Language to generate (derived from the output '
            'file extension if necessary)'
        ),
    )
    for lang in LANGUAGES:
        def_str = ' (the default)' if lang.name == DEFAULT_LANGUAGE else ''
        if lang.help_str:
            help_str = lang.help_str
        else:
            help_str = f'Generate {lang.printed} code'
        help_str += def_str
        parser.add_argument(
            '--' + lang.ext,
            '--' + lang.name,
            action='store_const',
            dest='language',
            const=lang.name,
            help=help_str,
        )
    parser.add_argument(
        '--indent',
        action='store',
        default=default.indent,
        help='indentation to use in output (default is language-specific)',
    )
    parser.add_argument(
        '-L',
        '--dialect',
        action='store',
        default=default.dialect,
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
        '--formatter-list',
        '--fl',
        action='store_true',
        default=default.formatter_list,
        help=(
            'Return the formatter tree as a list of objects of objects '
            'instead of as a string'
        ),
    )
    parser.add_argument(
        '-T',
        '--template',
        '--datafile-template',
        action='store',
        default=default.template,
        help='datafile template to use for code generation',
    )
    parser.add_argument(
        '--line-length',
        action='store',
        default=default.line_length,
        help='Line length to use (default is language-specific)',
    )
    parser.add_argument(
        '--memoize',
        dest='memoize',
        action=argparse.BooleanOptionalAction,
        default=default.memoize,
        help=(
            'Memoize parse results (default is grammar-specific, '
            'off if not specified)'
        ),
    )
    parser.add_argument(
        '-m',
        '--main',
        action=argparse.BooleanOptionalAction,
        default=default.main,
        help=(
            'include a main() function in the generated code if possible '
            '(off by default)'
        ),
    )


def default_options(*args, **kwargs):
    return GeneratorOptions(*args, **kwargs)


def options_from_args(
    args: argparse.ArgumentParser, argv: list[str], language=DEFAULT_LANGUAGE
):
    """Returns a dict containing the value of the generator args."""
    d = default_options(language=language)
    vs = vars(args)
    for name in d:
        if name in vs:
            d[name] = vs[name]
    if hasattr(args, 'generator_options'):
        if isinstance(args.generator_options, dict):
            d.update(args.generator_options)
        elif isinstance(args.generator_options, list):
            for opt_str in args.generator_options:
                opt_d = datafile.loads(opt_str)
                d.update(opt_d)

    d.argv = argv[1:] if argv else []
    d.command_line = shlex.join(d['argv'])
    return d
