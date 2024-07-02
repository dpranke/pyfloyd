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

from floyd.analyzer import Grammar


class GeneratorOptions:
    """Options that control the code generation.

    `language`: Which language to generate.
    `main`:     Whether to include a `main()`-like function.
    `memoize`:  Whether to memoize the intermediate results when parsing.
                Some generators may ignore this.
    `defines`:  A dictionary of generator-specific options.
    """

    language: str = 'python'
    main: bool = False
    memoize: bool = False
    defines: Dict[str, str] = {}

    def __init__(
        self,
        language: str = 'python',
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
        self.grammar = grammar
        self.options = options

    def generate(self) -> str:
        return ''
