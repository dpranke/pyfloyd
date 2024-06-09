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

import floyd
import floyd.host


THIS_DIR = pathlib.Path(__file__).parent


SKIP = os.environ.get('SKIP', '')


def skip(kind):
    def decorator(fn):
        def wrapper(obj):
            if kind in SKIP:
                obj.skipTest(kind)
            else:
                fn(obj)

        return wrapper

    return decorator


class PrinterTest(unittest.TestCase):
    maxDiff = None

    def test_actions(self):
        # TODO: Improve printer algorithm so that choices with actions
        # are not printed on the same line.
        grammar = textwrap.dedent("""\
            grammar = 'foo' -> 'foo' | 'bar' -> 'bar'
            """)
        out, err = floyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_bad_grammar(self):
        grammar = 'grammar = end -> foo'
        out, err = floyd.pretty_print(grammar)
        self.assertIsNone(out)
        self.assertEqual(
            err,
            'Errors were found:\n  Unknown variable "foo" referenced\n',
        )

    def test_comment(self):
        grammar = textwrap.dedent("""\
            %comment = '//' (~'\\n' any)*

            %token foo

            grammar  = foo end

            foo      = 'foo'
            """)
        out, err = floyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_comment_style(self):
        grammar = textwrap.dedent("""\
            %comment_style C++

            %token foo

            grammar        = foo end

            foo            = 'foo'
            """)
        out, err = floyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_empty(self):
        grammar = textwrap.dedent("""\
            grammar = 'foo' |
            """)
        out, err = floyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_floyd(self):  # pragma: no cover
        return
        # TODO: Improve printer algorithm enough for this to work
        # without requiring all the rules to be more than 80 chars wide.
        # pylint: disable=unreachable
        host = floyd.host.Host()
        grammar = host.read_text_file(THIS_DIR / '../grammars/floyd.g')
        out, err = floyd.pretty_print(grammar)
        self.assertMultiLineEqual(grammar, out)
        self.assertIsNone(err)

    @skip('integration')
    def test_json5(self):
        host = floyd.host.Host()
        grammar = host.read_text_file(THIS_DIR / '../grammars/json5.g')
        out, err = floyd.pretty_print(grammar)
        self.assertMultiLineEqual(grammar, out)
        self.assertIsNone(err)

    def test_getitem(self):
        grammar = "grammar = 'foo'*:foos -> foos[0]\n"
        out, err = floyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_leftrec(self):
        grammar = "grammar = grammar 'a' | 'a'\n"
        out, err = floyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_token(self):
        grammar = textwrap.dedent("""\
            %token foo

            grammar = foo

            foo     = end
            """)
        out, err = floyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_tokens(self):
        grammar = textwrap.dedent("""\
            %tokens foo bar

            grammar = foo bar

            foo     = 'foo'

            bar     = 'bar'
            """)
        out, err = floyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_tokens_only_one_token(self):
        grammar = textwrap.dedent("""\
            %tokens foo

            grammar = foo

            foo     = 'foo'
            """)
        out, err = floyd.pretty_print(grammar)
        self.assertEqual(grammar.replace('%tokens', '%token'), out)
        self.assertIsNone(err)

    def test_whitespace(self):
        grammar = textwrap.dedent("""\
            %whitespace = ' '*

            %token foo

            grammar     = foo end

            foo         = 'foo'
            """)
        out, err = floyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)

    def test_whitespace_style(self):
        grammar = textwrap.dedent("""\
            %whitespace_style standard
           
            %token foo

            grammar           = foo end

            foo               = 'foo'
            """)
        out, err = floyd.pretty_print(grammar)
        self.assertEqual(grammar, out)
        self.assertIsNone(err)
