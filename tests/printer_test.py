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

import os
import pathlib
import textwrap
import unittest

import pyfloyd


THIS_DIR = pathlib.Path(__file__).parent


SKIP = os.environ.get('SKIP', '')


def skip(kind):
    def decorator(fn):
        def wrapper(obj):
            if kind in SKIP:  # pragma: no cover
                obj.skipTest(kind)
            else:
                fn(obj)

        return wrapper

    return decorator


class PrinterTest(unittest.TestCase):
    maxDiff = None

    def _read(self, *comps):
        path = os.path.join(*comps)
        with open(path, 'r', encoding='utf8') as fp:
            return fp.read()

    def test_actions(self):
        # TODO: Improve printer algorithm so that choices with actions
        # are not printed on the same line.
        grammar = textwrap.dedent("""\
            grammar = 'foo' -> 'foo'
                    | 'bar' -> 'bar'
            """)
        out, err = pyfloyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_bad_grammar(self):
        grammar = 'grammar'
        out, err = pyfloyd.pretty_print(grammar)
        self.assertIsNone(out)
        self.assertEqual(
            err,
            '<string>:1 Unexpected end of input at column 8',
        )

    def test_comment(self):
        grammar = textwrap.dedent("""\
            %comment = '//' (~'\\n' any)*

            %tokens  = foo

            grammar  = foo end

            foo      = 'foo'
            """)
        out, err = pyfloyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_empty(self):
        grammar = textwrap.dedent("""\
            grammar = 'foo'
                    |
            """)
        out, err = pyfloyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    @skip('integration')
    def test_floyd(self):
        grammar = self._read(THIS_DIR, '..', 'grammars', 'floyd.g')
        out, err = pyfloyd.pretty_print(grammar)
        self.assertIsNone(err)

        # TODO: Improve printer algorithm enough for this to work
        # without requiring all the rules to be more than 80 chars wide.
        # self.assertMultiLineEqual(grammar, out)
        del out

    @skip('integration')
    def test_json5(self):
        grammar = self._read(THIS_DIR, '..', 'grammars', 'json5.g')
        out, err = pyfloyd.pretty_print(grammar)
        self.assertIsNone(err)

        # TODO: Improve printer algorithm enough for this to work
        # without requiring all the rules to be more than 80 chars wide.
        # self.assertMultiLineEqual(grammar, out)
        del out

    def test_getitem(self):
        grammar = "grammar = 'foo'*:foos -> foos[0]\n"
        out, err = pyfloyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_leftrec(self):
        grammar = textwrap.dedent("""\
            grammar = grammar 'a'
                    | 'a'
            """)
        out, err = pyfloyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_pred(self):
        grammar = 'grammar = ?{ true } -> true\n'
        out, err = pyfloyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_token(self):
        grammar = textwrap.dedent("""\
            %tokens = foo

            grammar = foo

            foo     = end
            """)
        out, err = pyfloyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_tokens(self):
        grammar = textwrap.dedent("""\
            %tokens = foo bar

            grammar = foo bar

            foo     = 'foo'

            bar     = 'bar'
            """)
        out, err = pyfloyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_whitespace(self):
        grammar = textwrap.dedent("""\
            %whitespace = ' '*

            %tokens     = foo

            grammar     = foo end

            foo         = 'foo'
            """)
        out, err = pyfloyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)
