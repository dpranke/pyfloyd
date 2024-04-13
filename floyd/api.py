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

from typing import Any, Optional, Tuple

from floyd import analyzer
from floyd.compiler import Compiler
from floyd.interpreter import Interpreter
from floyd.parser import Parser
from floyd.printer import Printer


class ParserInterface:
    def parse(
        self, text: str, path: str = '<string>'
    ) -> Tuple[Any, Optional[str], int]:
        raise NotImplementedError  # pragma: no cover


class _CompiledParser(ParserInterface):
    def __init__(self):
        self.grammar = None
        self.interpreter = None

    def compile(
        self, grammar: str, path: str = '<string>', memoize: bool = False
    ) -> Tuple[Optional[str], int]:
        parser = Parser(grammar, path)
        ast, err, endpos = parser.parse()
        if err:
            return err, endpos
        try:
            self.grammar = analyzer.analyze(ast)
            self.interpreter = Interpreter(self.grammar, memoize=memoize)
            return None, 0
        except analyzer.AnalysisError as e:
            return str(e), endpos

    def parse(
        self, text: str, path: str = '<string>'
    ) -> Tuple[Any, Optional[str], int]:
        out, err, endpos = self.interpreter.parse(text, path)
        return out, err, endpos


def compile_parser(
    grammar: str, path: str = '<string>', memoize: bool = False
) -> Tuple[Optional[ParserInterface], Optional[str], int]:
    p = _CompiledParser()
    err, endpos = p.compile(grammar, path=path, memoize=memoize)
    if err:
        return None, err, endpos
    return p, None, endpos


def generate_parser(
    grammar: str,
    class_name: str = 'Parser',
    main: bool = False,
    memoize: bool = False,
    path: str = '<string>',
) -> Tuple[Optional[str], Optional[str], int]:
    ast, err, endpos = Parser(grammar, path).parse()
    if err:
        return None, err, endpos
    try:
        grammar = analyzer.analyze(ast)
        text, err = Compiler(grammar, class_name, main, memoize).compile()
        return text, err, 0
    except analyzer.AnalysisError as e:
        return None, str(e), 0


def parse(
    grammar: str,
    text: str,
    grammar_path: str = '<string>',
    path: str = '<string>',
    memoize: bool = False,
) -> Tuple[Any, Optional[str], int]:
    """Match an input text against the specified grammar."""
    c, err, endpos = compile_parser(grammar, grammar_path, memoize=memoize)
    if err:
        return c, 'Error in grammar: ' + err, endpos
    assert c is not None  # This makes mypy not warn about a union-attr
    return c.parse(text, path)


def pretty_print(
    grammar: str, path: str = '<string>'
) -> Tuple[Optional[str], Optional[str]]:
    parser = Parser(grammar, path)
    ast, err, _ = parser.parse()
    if err:
        return None, err

    try:
        grammar = analyzer.analyze(ast)
        return Printer(grammar).dumps(), None
    except analyzer.AnalysisError as e:
        return None, str(e)
