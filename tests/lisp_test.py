# Copyright 2025 Dirk Pranke. All rights reserved.
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

from typing import Any
import unittest

from pyfloyd import datafile
from pyfloyd import lisp_interpreter


class Tests(unittest.TestCase):
    def check(self, s, v):
        interp = lisp_interpreter.Interpreter()

        def _parse_bareword(bw: str, as_key: bool) -> Any:
            if as_key:
                return bw
            return ['symbol', bw]

        expr = datafile.loads(s, parse_bareword=_parse_bareword)
        got_v = interp.eval(expr)
        self.assertEqual(v, got_v)

    def test_cond(self):
        self.check(
            """
            [cond [[equal 'foo' 'bar'] 'bar']
                  [[equal 'foo' 'qux'] 'qux']
                  [else 'foo']]
            """,
            'foo',
        )

    def test_hello(self):
        self.check("[strcat 'hello, ' 'world']", 'hello, world')

    def test_let(self):
        self.check(
            """
            [let [[h 'hello, ']
                  [w 'world']]
              [strcat h w]]
            """,
            'hello, world',
        )
