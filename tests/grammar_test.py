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

import math
import pathlib
import textwrap
import unittest
import json

import floyd
import floyd.host


THIS_DIR = pathlib.Path(__file__).parent


class FloydTest(unittest.TestCase):
    maxDiff = None

    def test_floyd(self):
        h = floyd.host.Host()
        grammar = h.read_text_file(THIS_DIR / '../grammars/floyd.g')
        p, err = floyd.compile_parser(
            grammar, path=str(THIS_DIR / '../grammars/floyd.g')
        )
        self.assertIsNone(err)
        out, err = p.parse(grammar, '../grammars/floyd.g')
        # We don't check the actual output here because it is too long
        # and we don't want the test to be so sensitive to the AST for
        # the floyd grammar.
        self.assertEqual(out[0][:2], ['rule', 'grammar'])
        self.assertIsNone(err)


class GrammarTest(unittest.TestCase):
    maxDiff = None

    def check(self, grammar, inp, out=None, err=None):
        p, err = floyd.compile_parser(grammar)
        self.assertIsNone(err)
        actual_out, actual_err = p.parse(inp)
        self.assertEqual(out, actual_out)
        self.assertEqual(err, actual_err)

    def test_any_fails(self):
        p, err = floyd.compile_parser("grammar = '")
        self.assertEqual(err, '<string>:1 Unexpected end of input at column 12')
        self.assertIsNone(p)

    def test_c_style_comment(self):
        self.check('grammar = /* foo */ end -> true', inp='', out=True)

    def test_cpp_style_comment(self):
        self.check(textwrap.dedent("""\
            grammar = // ignore this line
                      end -> true
            """), inp='', out=True)

    def test_error_on_second_line(self):
        p, err = floyd.compile_parser(textwrap.dedent("""\
            grammar = 'foo'
                      4
            """))
        self.assertIsNone(p)
        self.assertEqual(err, '<string>:2 Unexpected "4" at column 11')

    def test_error_unexpected_thing(self):
        p, err = floyd.compile_parser('grammar = 1 2 3')
        self.assertIsNone(p)
        self.assertEqual(err, '<string>:1 Unexpected "1" at column 11')

    def test_escapes_in_string(self):
        self.check(
            'grammar = "\\n\\\'\\\"foo" -> true',
            inp = '\n\'"foo',
            out=True
        )

    def test_hex_digits_in_value(self):
        self.check('grammar = -> 0x20', inp='', out=32)

    def test_lit_str(self):
        self.check("grammar = ('foo')* -> true", inp='foofoo', out=True)

    def test_long_unicode_literals(self):
        self.check("grammar = '\\U00000020' -> true", inp=' ', out=True)

    def test_optional_comma(self):
        self.check('grammar = end -> true,', inp='', out=True)

    def test_paren_in_value(self):
        self.check('grammar = -> (true)', inp='', out=True)

    def test_rule_with_lit_str(self):
        self.check(textwrap.dedent("""\
                grammar = foo* -> true
                foo     = 'foo'
                """
            ),
            inp='foofoo',
            out=True
        )

class JSON5Test(unittest.TestCase):
    def check(self, host, grammar, text, output=None, error=None):
        if host.exists(THIS_DIR / text):
            text = host.read_text_file(THIS_DIR / text)
        if output:
            if host.exists(THIS_DIR / output):
                output = host.read_text_file(THIS_DIR / output)
            expected_obj = json.loads(output)

        actual_obj, actual_err = grammar.parse(text)
        if output:
            self.assertEqual(expected_obj, actual_obj)
        if error:
            self.assertEqual(error, actual_err)
        return actual_obj, actual_err

    def test_json5(self):
        h = floyd.host.Host()
        # We compile the parser outside of check so that we can reuse it
        # for multiple tests.
        g, _ = floyd.compile_parser(
            h.read_text_file(THIS_DIR / '../grammars/json5.g'),
            path=str(THIS_DIR / '../grammars/json5.g'),
        )
        self.check(
            h, g, 'grammars/json5_sample.inp', 'grammars/json5_sample.outp'
        )
        self.check(h, g, 'Infinity', 'Infinity')
        self.check(h, g, 'null', 'null')
        self.check(h, g, 'true', 'true')
        self.check(h, g, 'false', 'false')
        self.check(h, g, '{foo: "bar"}', '{"foo": "bar"}')
        self.check(h, g, '[1, 2]', '[1, 2]')

        # can't use check for this because NaN != NaN.
        obj, err = g.parse('NaN')
        self.assertTrue(math.isnan(obj))
        self.assertTrue(err is None)

        self.check(
            h, g, '[1', error='<string>:1 Unexpected end of input at column 3'
        )

