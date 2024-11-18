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

from typing import Dict, Optional

from pyfloyd.analyzer import Grammar


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

    def generate(self) -> str:  # pragma: no cover
        return ''
