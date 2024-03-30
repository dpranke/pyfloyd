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
from floyd.parser import Parser
from floyd.printer import Printer


def compile_parser(grammar, path='<string>', memoize=False):
    p = CompiledParser()
    _, err = p.compile(grammar, path=path, memoize=memoize)
    if err:
        return None, err
    return p, None


class CompiledParser:
    def __init__(self):
        self.parser_cls = None
        self.grammar_obj = None

    def compile(self, grammar, path='<string>', memoize=False):
        scope = {}
        parser = Parser(grammar, path)
        ast, err, _ = parser.parse()
        if err:
            return None, err
        grammar = Analyzer().analyze(ast)

        comp = Compiler(grammar, 'Parser', main_wanted=False, memoize=memoize)
        compiled_text, err = comp.compile()
        assert err is None  # comp.compile() can't currently fail.

        try:
            exec(compiled_text, scope)  # pylint: disable=exec-used
        except Exception:
            return None, 'Error compiling grammar.'
        self.parser_cls = scope['Parser']
        return None, None

    def parse(self, text, path='<string>'):
        parser = self.parser_cls(text, path)
        obj, err, _ = parser.parse()
        return obj, err


def generate_parser(
    grammar, class_name='Parser', main=False, memoize=False, path='<string>'
):
    ast, err, _ = Parser(grammar, path).parse()
    if err:
        return None, err
    ast = Analyzer().analyze(ast)
    return Compiler(ast, class_name, main, memoize).compile()


def parse(
    grammar, text, grammar_path='<string>', path='<string>', memoize=False
):
    """Match an input text against the specified grammar."""
    c, err = compile_parser(grammar, grammar_path, memoize=memoize)
    if err:
        return c, err
    val, err = c.parse(text, path)
    return val, err


def pretty_print(grammar):
    parser = Parser(grammar, '<string>')
    ast, err, _ = parser.parse()
    if err:
        return None, err
    grammar = Analyzer().analyze(ast)
    return Printer(grammar).dumps(), None
