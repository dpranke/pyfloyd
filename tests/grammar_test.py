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
    def check(self, grammar, text, out=None, err=None, grammar_err=None):
        p, p_err, _ = self.compile(grammar)
        self.assertEqual(grammar_err, p_err)
        if p:
            self.checkp(p, text, out, err)

    def checkp(self, parser, text, out=None, err=None):
        actual_out, actual_err, _ = parser.parse(text)
        self.assertEqual(out, actual_out)
        self.assertEqual(err, actual_err)

    def check_grammar_error(self, grammar, err):
        p, p_err, _ = self.compile(grammar)
        self.assertIsNone(p)
        self.assertEqual(err, p_err)

    def test_action(self):
        self.check('grammar = end -> true', text='', out=True)
        self.check('grammar = end { true }', text='', out=True)

    def test_any_fails(self):
        self.check(
            'grammar = any',
            '',
            err='<string>:1 Unexpected end of input at column 1',
        )

    def test_any_fails_in_parser(self):
        # This tests what happens when a grammar itself fails the 'any' test.
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

    def test_c_comment_style_with_range(self):
        # This tests both the 'C' comment style and that filler around
        # ranges are handled properly.
        grammar = textwrap.dedent("""\
            %whitespace_style standard
            %comment_style    C

            grammar = num '+' num end -> true

            num     = '1'..'9'
            """)
        p, err, _ = self.compile(grammar)
        self.assertIsNone(err)
        self.checkp(p, ' 1 + 2 ', out=True)
        self.checkp(p, ' 1/* comment */+2', out=True)

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

    def test_comment_pragma(self):
        grammar = """\
            %token foo
            %comment = '//' (~'\n' any)*
            grammar = (foo ' '* '\n')+  end -> true

            foo     = 'foo'
            """
        self.check(grammar, text='foo\nfoo\n', out=True)

    def test_comment_style_pragma(self):
        grammar = """\
            %token foo
            %comment_style Python

            grammar = (foo ' '* '\n')+  end -> true

            foo     = 'foo'
            """
        self.check(grammar, text='foo\nfoo\n', out=True)
        self.check(grammar, text='foo # bar\nfoo\n', out=True)

    def test_comment_style_unknown(self):
        grammar = """\
            %token foo
            %comment_style X
            grammar = foo

            foo     = "foo"
            """
        self.check(
            grammar,
            text='foo',
            grammar_err=(
                'Errors were found:\n' '  Unknown %comment_style "X"\n'
            ),
        )

    def test_comment_style_pragma_both_is_an_error(self):
        grammar = """\
            %token foo
            %comment = '//' (~'\n' any)*
            %comment_style Python

            grammar = (foo ' '* '\n')+  end -> true

            foo     = 'foo'
            """
        self.check(
            grammar,
            text='foo\nfoo\n',
            grammar_err="Errors were found:\n  Can't set both comment and comment_style pragmas\n",
        )

    def test_cpp_style_comment_in_grammar(self):
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

    def test_error_on_unknown_function(self):
        self.check(
            'grammar = -> foo()',
            text='',
            grammar_err=(
                'Errors were found:\n' '  Unknown function "foo" called\n'
            ),
        )

    def test_error_on_unknown_var(self):
        self.check(
            'grammar = -> v',
            text='',
            grammar_err=(
                'Errors were found:\n' '  Unknown variable "v" referenced\n'
            ),
        )

    def test_error_on_unknown_rule(self):
        self.check(
            'grammar = foo',
            text='',
            grammar_err=('Errors were found:\n' '  Unknown rule "foo"\n'),
        )

    def test_error_unexpected_thing(self):
        self.check_grammar_error(
            'grammar = 1 2 3', err='<string>:1 Unexpected "1" at column 11'
        )

    def test_escape_unicat(self):
        self.check('grammar = \\p{Nd} -> true', text='1', out=True)

    def test_escapes_in_string(self):
        self.check(
            'grammar = "\\n\\\'\\"foo" -> true', text='\n\'"foo', out=True
        )

    def test_floyd(self):
        h = floyd.host.Host()
        path = str(THIS_DIR / '../grammars/floyd.g')
        grammar = h.read_text_file(path)
        p, err, _ = self.compile(grammar, path)
        self.assertIsNone(err)
        out, err, _ = p.parse(grammar, '../grammars/floyd.g')
        # We don't check the actual output here because it is too long
        # and we don't want the test to be so sensitive to the AST for
        # the floyd grammar.
        self.assertEqual(out[0], 'rules')
        self.assertIsNone(err)

    def test_floyd2(self):
        h = floyd.host.Host()
        path = str(THIS_DIR / '../grammars/floyd2.g')
        grammar = h.read_text_file(path)
        p, err, _ = self.compile(grammar, path)
        self.assertIsNone(err)
        out, err, _ = p.parse(grammar, '../grammars/floyd2.g')
        # We don't check the actual output here because it is too long
        # and we don't want the test to be so sensitive to the AST for
        # the floyd grammar.
        self.assertEqual(out[0], 'rules')
        self.assertIsNone(err)

    def test_hex_digits_in_value(self):
        self.check('grammar = -> 0x20', text='', out=32)

    def test_itou(self):
        self.check('grammar = -> itou(97)', text='', out='a')

    def test_json5(self):
        h = floyd.host.Host()
        path = str(THIS_DIR / '../grammars/json5.g')
        p, err, _ = self.compile(h.read_text_file(path))
        self.assertIsNone(err)
        self._common_json5_checks(p)

    def _common_json5_checks(self, p):
        self.checkp(p, text='123', out=123)
        self.checkp(p, text='1.5', out=1.5)
        self.checkp(p, text='+1.5', out=1.5)
        self.checkp(p, text='-1.5', out=-1.5)
        self.checkp(p, text='1.5e2', out=150)
        self.checkp(p, text='.5e-2', out=0.005)
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
        obj, err, _ = p.parse('NaN')
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

    def test_json5_2(self):
        h = floyd.host.Host()
        path = str(THIS_DIR / '../grammars/json5_2.g')
        grammar = h.read_text_file(path)
        p, err, _ = self.compile(grammar)
        self.assertIsNone(err)
        self._common_json5_checks(p)

    def test_label(self):
        self.check("grammar = 'foobar':v -> v", text='foobar', out='foobar')
        self.check("grammar = 'foobar' -> $1", text='foobar', out='foobar')
        self.check(
            "grammar = 'foobar':$1 -> $1",
            text='foobar',
            grammar_err=(
                'Errors were found:\n'
                '  "$1" is a reserved variable name '
                'and cannot be explicitly defined\n'
            ),
        )
        self.check(
            "grammar = 'foobar' -> $2",
            text='foobar',
            grammar_err=(
                'Errors were found:\n  Unknown variable "$2" referenced\n'
            ),
        )

    def test_lit_str(self):
        self.check("grammar = ('foo')* -> true", text='foofoo', out=True)

    def test_ll_getitem(self):
        self.check("grammar = end -> ['a', 'b'][1]", text='', out='b')

    def test_ll_minus(self):
        self.check('grammar = end -> 1 - 4', text='', out=-3)

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
        g = "grammar = 'a'+ -> true"
        self.check(
            g,
            text='',
            err='<string>:1 Unexpected end of input at column 1',
        )

        self.check(g, text='a', out=True)
        self.check(g, text='aa', out=True)

    def test_operator(self):
        # For now, precedence has no effect but this at least tests
        # that the pragmas get parsed.
        g = """
            %prec + -
            %prec * /
            %prec ^
            %assoc ^ right
            expr = expr '+' expr -> [$1, '+', $3]
                 | expr '-' expr -> [$1, '-', $3]
                 | expr '*' expr -> [$1, '*', $3]
                 | expr '/' expr -> [$1, '/', $3]
                 | expr '^' expr -> [$1, '^', $3]
                 | '0'..'9'
            """
        # self.check(g, text='1', out='1')
        # self.check(g, text='1+2', out=['1', '+', '2'])
        # self.check(g, text='1+2*3', out=['1', '+', ['2', '*', '3']])
        self.check(g, text='1+2-3', out=[['1', '+', '2'], '-', '3'])

        self.check(g, text='1^2^3+4*5/6', 
                   out=[['1', '^', ['2', '^', '3']], '+',
                        [['4', '*', '5'], '/', '6']])

    def test_pred(self):
        self.check('grammar = ?(true) end -> true', text='', out=True)
        self.check('grammar = ?{true} end { true }', text='', out=True)
        self.check(
            """\
            grammar = ?(false) end -> 'a'
                    | end -> 'b'
            """,
            text='',
            out='b',
        )
        self.check(
            'grammar = ?("foo") end -> false',
            text='',
            out=None,
            err='<string>:1 Bad predicate value',
        )

    def test_recursion_both(self):
        grammar = """\
            expr = expr:l '+' expr:r -> [l, '+', r]
                 | '0'..'9':d        -> d
            """
        # Note that a grammar that is both left- and right-recursive
        # is left-associative by default.
        self.check(grammar, '1+2+3', [['1', '+', '2'], '+', '3'])

    def test_recursion_direct_left(self):
        self.check(
            """\
            grammar = grammar:g '+' 'a' -> [g, '+', 'a']
                    | 'a'               -> 'a'
            """,
            'a+a+a',
            [['a', '+', 'a'], '+', 'a'],
        )

    def test_recursion_without_a_label(self):
        # This covers the code path where left recursion happens but
        # we don't need to save the value from it.
        self.check(
            """\
            grammar = grammar 'a'
                    | 'a'
            """,
            'aaa',
            out='a',
        )

    def test_recursion_direct_right(self):
        self.check(
            """\
            grammar = 'a' '+' grammar:g -> ['a', '+', g]
                    | 'a'               -> 'a'
            """,
            'a+a+a',
            ['a', '+', ['a', '+', 'a']],
        )

    def test_recursion_indirect_left(self):
        self.check(
            """\
            grammar = b:b '+' 'a'   -> [b, '+', 'a']
                    | 'a'           -> 'a'
            b       = grammar:g     -> g
            """,
            'a+a+a',
            [['a', '+', 'a'], '+', 'a'],
        )

    def test_recursion_indirect_right(self):
        self.check(
            """\
            grammar = 'a' '+' b:b   -> ['a', '+', b]
                    | 'a'           -> 'a'
            b       = grammar:g     -> g
            """,
            'a+a+a',
            ['a', '+', ['a', '+', 'a']],
        )

    def test_recursion_interior(self):
        self.check(
            """\
            grammar = 'a' grammar:g 'b' -> 'a' + g + 'b'| 'ab' -> 'ab'
            """,
            'aabb',
            'aabb',
        )

    def test_recursion_left_opt(self):
        grammar = """\
            grammar = 'b'?:b grammar:g 'c' -> join('', b) + g + 'c'
                    | 'a'           -> 'a'
            """
        self.check(grammar, 'ac', 'ac')
        self.check(grammar, 'acc', 'acc')

        # This result happens because grammar is left-associative by
        # default, and so when grammar is invoked the second time,
        # it is blocked and fails to recurse a third time; that allows
        # it to consume the 'a' and then complete. The first invocation
        # is then free to consume the 'c'.
        self.check(grammar, 'bac', 'bac')

        # Now, since the grammar is now declared to be right-associative,
        # when grammar is invoked for the second time, it is not blocked,
        # and it can consume the 'a' and then the 'c' before completing.
        # Once that completes, there is no longer any input left for the
        # first invocation to consume and so it fails to find the 'c' it
        # needs.
        grammar = """\
            %assoc grammar#1 right
            grammar = 'b'?:b grammar:g 'c' -> join('', b) + g + 'c'
                    | 'a'           -> 'a'
            """
        self.check(
            grammar,
            'bac',
            err='<string>:1 Unexpected end of input at column 4',
        )

    def test_recursion_repeated(self):
        self.check(
            """
            grammar = grammar:x grammar:y 'a' -> [x, y, 'a']
                    | 'a'                     -> 'a'
            """,
            'aaa',
            ['a', 'a', 'a'],
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

    def test_token_pragma(self):
        self.check(
            """\
            %token foo
            grammar = foo -> true
            foo     = bar
            bar     = 'baz'
            """,
            text='baz',
            out=True,
        )

    def test_token_pragma_token_is_unknown(self):
        self.check(
            """\
            %token quux
            grammar = foo -> true
            foo     = bar
            bar     = 'baz'
            """,
            text='baz',
            grammar_err='Errors were found:\n  Unknown token rule "quux"\n',
        )

    def test_tokens_pragma(self):
        grammar = """\
            %tokens foo bar
            grammar = (foo bar)+ end -> true
            foo     = 'foo'
            bar     = 'bar'
            """
        self.check(grammar, text='foobar', out=True)

    def test_utoi(self):
        self.check('grammar = -> utoi("a")', text='', out=97)

    def test_whitespace_pragma(self):
        grammar = """\
            %token foo
            %whitespace = ' '
           
            grammar = foo foo end -> true

            foo     = 'foo'
            """
        self.check(grammar, text='foofoo', out=True)

    def test_whitespace_style_pragma(self):
        grammar = """\
            %token foo
            %whitespace_style standard
           
            grammar = foo foo end -> true

            foo     = 'foo'
            """
        self.check(grammar, text='foofoo', out=True)

        grammar = """\
            %token foo
            %whitespace_style X
            grammar = foo

            foo     = "foo"
            """
        self.check(
            grammar,
            text='foo',
            grammar_err=(
                'Errors were found:\n' '  Unknown %whitespace_style "X"\n'
            ),
        )

    def test_whitespace_style_pragma_both_is_an_error(self):
        grammar = """\
            %token foo
            %whitespace = ' '
            %whitespace_style standard
           
            grammar = foo foo end -> true

            foo     = 'foo'
            """
        self.check(
            grammar,
            text='foofoo',
            grammar_err=(
                'Errors were found:\n'
                "  Can't set both whitespace and whitespace_style pragmas\n"
            ),
        )


class Interpreter(unittest.TestCase, GrammarTestsMixin):
    max_diff = None

    def compile(self, grammar, path='<string>'):
        return floyd.compile_parser(textwrap.dedent(grammar), path)


class Compiler(unittest.TestCase, GrammarTestsMixin):
    max_diff = None

    def compile(self, grammar, path='<string>'):
        source_code, err, endpos = floyd.generate_parser(
            textwrap.dedent(grammar), main=False, memoize=False, path=path
        )
        if err:
            assert source_code is None
            return None, err, endpos

        scope = {}
        debug = False
        if debug:  # pragma: no cover
            h = floyd.host.Host()
            d = h.mkdtemp()
            h.write_text_file(d + '/parser.py', source_code)
        exec(source_code, scope)
        parser_cls = scope['Parser']
        if debug:  # pragma: no cover
            h.rmtree(d)
        return _ParserWrapper(parser_cls), None, 0


class _ParserWrapper:
    def __init__(self, parser_cls):
        self.parser_cls = parser_cls

    def parse(self, text, path='<string>'):
        parser = self.parser_cls(text, path)
        return parser.parse()
