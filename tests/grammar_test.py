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

import floyd
import floyd.host


THIS_DIR = pathlib.Path(__file__).parent


class GrammarTestsMixin:
    def check(self, grammar, text, out=None, err=None):
        p, p_err = self.compile(textwrap.dedent(grammar))
        self.assertIsNone(p_err)
        self.checkp(p, text, out, err)

    def checkp(self, parser, text, out=None, err=None):
        actual_out, actual_err = parser.parse(text)
        self.assertEqual(out, actual_out)
        self.assertEqual(err, actual_err)

    def check_grammar_error(self, grammar, err):
        p, p_err = self.compile(grammar)
        self.assertIsNone(p)
        self.assertEqual(err, p_err)

    def test_any_fails(self):
        self.check_grammar_error(
            "grammar = '",
            err='<string>:1 Unexpected end of input at column 12',
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

    def test_floyd(self):
        h = floyd.host.Host()
        path = str(THIS_DIR / '../grammars/floyd.g')
        grammar = h.read_text_file(path)
        p, err = self.compile(grammar, path)
        self.assertIsNone(err)
        out, err = p.parse(grammar, '../grammars/floyd.g')
        # We don't check the actual output here because it is too long
        # and we don't want the test to be so sensitive to the AST for
        # the floyd grammar.
        self.assertEqual(out[0][:2], ['rule', 'grammar'])
        self.assertIsNone(err)

    def test_hex_digits_in_value(self):
        self.check('grammar = -> 0x20', text='', out=32)

    def test_itou(self):
        self.check('grammar = -> itou(97)', text='', out='a')

    def test_json5(self):
        h = floyd.host.Host()
        path = str(THIS_DIR / '../grammars/json5.g')
        p, err = self.compile(h.read_text_file(path))
        self.checkp(p, text='123', out=123)
        self.checkp(p, text='Infinity', out=float('inf'))
        self.checkp(p, text='null', out=None)
        self.checkp(p, text='true', out=True)
        self.checkp(p, text='false', out=False)
        self.checkp(p, text='"foo"', out='foo')
        self.checkp(p, text='[]', out=[])
        self.checkp(p, text='[2]', out=[2])
        self.checkp(p, text='{}', out={})
        self.checkp(p, text='{foo: "bar"}', out={'foo': 'bar'})
        self.checkp(
            p, text='{foo: "bar", a: "b"}', out={'foo': 'bar', 'a': 'b'}
        )

        # Can't use check for this because NaN != NaN.
        obj, err = p.parse('NaN')
        self.assertTrue(math.isnan(obj))
        self.assertTrue(err is None)

        self.checkp(
            p, text='[1', err='<string>:1 Unexpected end of input at column 3'
        )

        # Check that leading whitespace is allowed.
        self.checkp(p, '  {}', {})

        # Check the sample file from pyjson5.
        self.checkp(
            p,
            textwrap.dedent("""\
            {
                foo: 'bar',
                while: true,

                this: 'is a \\
            multi-line string',

                // this is an inline comment
                here: 'is another', // inline comment

                /* this is a block comment
                   that continues on another line */

                hex: 0xDEADbeef,
                half: .5,
                delta: +10,
                to: Infinity,   // and beyond!

                finally: 'a trailing comma',
                oh: [
                    "we shouldn't forget",
                    'arrays can have',
                    'trailing commas too',
                ],
            }
            """),
            out={
                'foo': 'bar',
                'while': True,
                'this': 'is a multi-line string',
                'here': 'is another',
                'hex': 3735928559,
                'half': 0.5,
                'delta': 10.0,
                'to': float('inf'),
                'finally': 'a trailing comma',
                'oh': [
                    "we shouldn't forget",
                    'arrays can have',
                    'trailing commas too',
                ],
            },
        )

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

    def test_utoi(self):
        self.check('grammar = -> utoi("a")', text='', out=97)


class Interpreter(unittest.TestCase, GrammarTestsMixin):
    max_diff = None

    def compile(self, grammar, path='<string>'):
        return floyd.compile_parser(textwrap.dedent(grammar), path)


class Compiler(unittest.TestCase, GrammarTestsMixin):
    max_diff = None

    def compile(self, grammar, path='<string>'):
        source_code, err = floyd.generate_parser(
            grammar, main=False, memoize=False, path=path
        )
        if err:
            assert source_code is None
            return None, err

        scope = {}
        debug = False
        if debug:  # pragma: no cover
            h = floyd.host.Host()
            d = h.mkdtemp()
            h.write_text_file(d + '/parser.py', source_code)
        exec(source_code, scope)
        parser_cls = scope['Parser']

        return ParserWrapper(parser_cls), None

    def test_empty(self):
        pass

    def test_end(self):
        pass

    def test_error_on_second_line_of_grammar(self):
        pass

    def test_error_on_unknown_var(self):
        pass

    def test_pred(self):
        pass


class ParserWrapper:
    def __init__(self, parser_cls):
        self.parser_cls = parser_cls

    def parse(self, text, path='<string>'):
        parser = self.parser_cls(text, path)
        out, err, _ = parser.parse()
        return out, err
