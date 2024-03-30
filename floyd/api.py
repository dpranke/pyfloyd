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

from floyd.analyzer import Analyzer
from floyd.compiler import Compiler
from floyd.interpreter import Interpreter
from floyd.parser import Parser


def parse(
    grammar, input, grammar_path='<string>', path='<string>', memoize=False
):
    """Match an input string against the specified grammar."""
    c, err = compile(grammar, grammar_path, memoize=memoize)
    if err:
        return c, err
    val, err, _ = c.parse(path, string)


def compile(grammar, path='<string>', memoize=False):
    p = CompiledParser()
    p.compile(grammar, path=path, memoize=memoize)
    return p


class CompiledParser:
    def __init__(self):
        self.parser_cls = None
        self.grammar_obj = None

    def compile(self, input, path='<string>', memoize=False):
        scope = {}
        parser = Parser(input, path)
        ast, err, _ = parser.parse()
        if err:
            return None, err
        grammar, err = Analyzer().analyze(ast)
        if err:
            return None, err
        comp = Compiler(grammar, 'Parser', main_wanted=False, memoize=memoize)
        compiled_text, err = comp.compile()
        if err:
            return None, err, 0
        exec(compiled_text, scope)  # pylint: disable=exec-used
        self.parser_cls = scope['Parser']

    def parse(self, input, path='<string>'):
        parser = self.parser_cls(input, path)
        obj, err, _ = parser.parse()
        return obj, err


def pretty_print(grammar):
    raise NotImplementedError
