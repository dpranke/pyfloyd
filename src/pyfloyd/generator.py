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

from typing import Dict, Optional, Set, Union

from pyfloyd.analyzer import Grammar, Node
from pyfloyd import attr_dict
from pyfloyd import datafile
from pyfloyd import generator_options
from pyfloyd import support


class Generator:
    def __init__(self, 
        host: support.Host, 
        grammar: analyzer.Grammar,
        options: generator_options.GeneratorOptions
    ):
        self.host = host
        self.grammar = grammar
        self.options = options

        # Derive option values from the grammar if need be.
        lang = LANGUAGE_MAP[self.options.language]
        if self.options.line_length is None:
            self.options.line_length = lang.line_length
        if self.options.indent is None:
            self.options.indent = lang.indent
        elif isinstance(self.options.indent, int):
            self.options.indent = ' ' * self.options.indent
        self.options.unicodedata_needed = (
            grammar.unicat_needed
            or 'unicode_lookup' in self.grammar.needed_builtin_functions
        )

        # TODO: Pull this from the grammar.
        if self.options.memoize is None:
            self.options.memoize = False

        self._derive_memoize()

    def _derive_memoize(self):
        def _walk(node):
            if node.t == 'apply':
                if self.options.memoize and node.rule_name.startswith('r_'):
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

        _walk(self.grammar.ast)

    def _derive_local_vars(self):
        def _walk(node) -> Set[str]:
            local_vars: Set[str] = set()
            local_vars.update(set(self._local_vars.get(node.t, [])))
            for c in node.ch:
                local_vars.update(_walk(c))
            return local_vars

        for _, node in self.grammar.rules.items():
            node.local_vars = _walk(node)

    def generate(self) -> str:
        raise NotImplementedError
