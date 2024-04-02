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

    def check(self, grammar, text, out=None, err=None):
        p, p_err = floyd.compile_parser(textwrap.dedent(grammar))
        self.assertIsNone(p_err)
        actual_out, actual_err = p.parse(text)
        self.assertEqual(out, actual_out)
        self.assertEqual(err, actual_err)

    def check_grammar_error(self, grammar, err):
        p, p_err = floyd.compile_parser(textwrap.dedent(grammar))
        self.assertIsNone(p)
        self.assertEqual(err, p_err)

    def test_any_fails(self):
        self.check_grammar_error(
            "grammar = '",
            err='<string>:1 Unexpected end of input at column 12'
        )

    def test_array(self):
        self.check(
            """\
            grammar = '[' value:v (',' value)*:vs ','? ']' -> [v] + vs
            value   = '2':v                                -> float(v)
            """,
            text='[2]',
            out=[2.0],
        )

    def test_atoi(self):
        self.check('grammar = -> atoi("a")', text='', out=97)

    def test_basic(self):
        self.check('grammar = end -> true', text='', out=True)

    def test_bind(self):
        self.check("grammar = 'a'*:v -> v", text='aa', out=['a', 'a'])

    def test_c_style_comment(self):
        self.check('grammar = /* foo */ end -> true', text='', out=True)

    def test_choice(self):
        self.check(
            """\
            grammar = 'foo' -> true
                    | 'bar' -> false
            """,
            text='foo',
            out=True,
        )

        self.check(
            """\
            grammar = 'foo' -> true
                    | 'bar' -> false
            """,
            text='bar',
            out=False,
        )

    def test_cpp_style_comment(self):
        self.check(
            """\
            grammar = // ignore this line
                      end -> true
            """,
            text='',
            out=True,
        )

    def test_empty(self):
        self.check('grammar = ', text='', out=None, err=None)

    def test_end(self):
        self.check(
            'grammar = end',
            text='foo',
            out=None,
            err='<string>:1 Unexpected "f" at column 1',
        )

    def test_error_on_second_line_of_grammar(self):
        self.check_grammar_error(
            """\
            grammar = 'foo'
                      4
            """,
            err='<string>:2 Unexpected "4" at column 11',
        )

    def test_error_on_second_line_of_input(self):
        self.check(
            "grammar = '\\nfoo'",
            text='\nbar',
            err='<string>:2 Unexpected "b" at column 1',
        )

    def test_error_on_unknown_var(self):
        # TODO: This could be rejected at compile time.
        self.check(
            'grammar = -> v',
            text='',
            err='<string>:1 Reference to unknown variable "v"',
        )

    def test_error_unexpected_thing(self):
        self.check_grammar_error(
            'grammar = 1 2 3', err='<string>:1 Unexpected "1" at column 11'
        )

    def test_escapes_in_string(self):
        self.check(
            'grammar = "\\n\\\'\\"foo" -> true', text='\n\'"foo', out=True
        )

    def test_hex_digits_in_value(self):
        self.check('grammar = -> 0x20', text='', out=32)

    def test_itou(self):
        self.check('grammar = -> itou(97)', text='', out='a')

    def test_lit_str(self):
        self.check("grammar = ('foo')* -> true", text='foofoo', out=True)

    def test_ll_plus(self):
        self.check(
            "grammar = 'a':a 'b'*:bs -> a + join('', bs)",
            text='abb',
            out='abb',
        )

    def test_long_unicode_literals(self):
        self.check("grammar = '\\U00000020' -> true", text=' ', out=True)

    def test_opt(self):
        self.check("grammar = 'a' 'b'? -> true", text='a', out=True)

    def test_optional_comma(self):
        self.check('grammar = end -> true,', text='', out=True)

    def test_paren_in_value(self):
        self.check('grammar = -> (true)', text='', out=True)

    def test_plus(self):
        self.check(
            "grammar = 'a'+ -> true",
            text='',
            err='<string>:1 Unexpected end of input at column 1',
        )

        self.check("grammar = 'a'+ -> true", text='a', out=True)
        self.check("grammar = 'a'+ -> true", text='aa', out=True)

    def test_pred(self):
        self.check('grammar = ?(true) end -> true', text='', out=True)
        self.check(
            textwrap.dedent("""\
            grammar = ?(false) end -> 'a'
                    | end -> 'b'
            """),
            text='',
            out='b',
        )
        self.check(
            'grammar = ?("foo") end',
            text='',
            out=None,
            err='<string>:1 Bad predicate value',
        )

    def test_rule_with_lit_str(self):
        self.check(
            """\
            grammar = foo* -> true
            foo     = 'foo'
            """,
            text='foofoo',
            out=True,
        )

    def test_seq(self):
        self.check("grammar = 'foo' 'bar' -> true", text='foobar', out=True)

    def test_star(self):
        self.check("grammar = 'a'* -> true", text='', out=True)
        self.check("grammar = 'a'* -> true", text='a', out=True)
        self.check("grammar = 'a'* -> true", text='aa', out=True)


class JSON5Test(unittest.TestCase):
    parser = None

    @classmethod
    def setUpClass(cls):
        h = floyd.host.Host()
        path = str(THIS_DIR / '../grammars/json5.g')
        cls.parser, err = floyd.compile_parser(h.read_text_file(path), path)
        assert err is None

    def check(self, text, out=None, err=None):
        actual_out, actual_err = self.parser.parse(text)
        self.assertEqual(out, actual_out)
        self.assertEqual(err, actual_err)

    def checkfiles(self, inp_path, outp_path):
        h = floyd.host.Host()
        out, err = self.parser.parse(h.read_text_file(THIS_DIR / inp_path))
        self.assertEqual(
            out, json.loads(h.read_text_file(THIS_DIR / outp_path))
        )
        self.assertIsNone(err)

    def test_full_grammar(self):
        self.checkfiles(
            'grammars/json5_sample.inp', 'grammars/json5_sample.outp'
        )

    def test_json5(self):
        self.check('123', 123)
        self.check('Infinity', float('inf'))
        self.check('null', None)
        self.check('true', True)
        self.check('false', False)
        self.check('"foo"', 'foo')
        self.check('[]', [])
        self.check('[2]', [2])
        self.check('{}', {})
        self.check('{foo: "bar"}', {'foo': 'bar'})
        self.check('{foo: "bar", a: "b"}', {'foo': 'bar', 'a': 'b'})

        # can't use check for this because NaN != NaN.
        obj, err = self.parser.parse('NaN')
        self.assertTrue(math.isnan(obj))
        self.assertTrue(err is None)

        self.check('[1', err='<string>:1 Unexpected end of input at column 3')
