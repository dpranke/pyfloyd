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

# pylint: disable=too-many-lines

import json
import math
import os
import pathlib
import subprocess
import textwrap
import unittest

import floyd
import floyd.host


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


class GrammarTestsMixin:
    def check(self, grammar, text, out=None, err=None, grammar_err=None):
        p, p_err, _ = self.compile(grammar)
        self.assertMultiLineEqual(grammar_err or '', p_err or '')
        if p:
            self.checkp(p, text, out, err)
        if hasattr(p, 'cleanup'):
            p.cleanup()

    def checkp(self, parser, text, out=None, err=None):
        actual_out, actual_err, _ = parser.parse(text)
        # Test err before out because it's probably more helpful to display
        # an unexpected error than it is to display an unexpected output.
        self.assertMultiLineEqual(err or '', actual_err or '')
        self.assertEqual(out, actual_out)

    def check_grammar_error(self, grammar, err):
        p, p_err, _ = self.compile(grammar)
        self.assertIsNone(p)
        self.assertMultiLineEqual(err, p_err)

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

    def test_quals(self):
        self.check("g = -> utoi(' ')", text='', out=32)
        self.check("g = 'x'*:l -> l[0]", text='xx', out='x')
        self.check("g = -> ['a', 'b'][1]", text='', out='b')
        self.check("g = -> [['a']][0][0]", text='', out='a')

    def test_array(self):
        self.check(
            """\
            grammar = '[' value:v (',' value)*:vs ','? ']' -> arrcat([v], vs)
            value   = '2':v                                -> float(v)
            """,
            text='[2]',
            out=[2],
        )

    def test_basic(self):
        self.check('grammar = end -> true', text='', out=True)

    def test_bind(self):
        self.check("grammar = 'a'*:v -> v", text='aa', out=['a', 'a'])

    def test_big_int(self):
        self.check(
            'grammar = { float("505874924095815700") }',
            text='',
            out=505874924095815700,
        )
        self.check(
            'grammar = { 505874924095815700 }', text='', out=505874924095815700
        )

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

    def test_choice_with_rewind(self):
        self.check(
            """\
            grammar = 'a' 'b' -> false 
                    | 'a' 'c' -> true
            """,
            text='ac',
            out=True,
        )

    def test_comment_pragma(self):
        grammar = """\
            %token foo
            %comment = '//' (~'\n' any)*
            grammar = (foo ' '* '\n')+  end -> true

            foo     = 'foo'
            """
        self.check(grammar, text='foo\nfoo\n', out=True)

    def test_count(self):
        grammar = "grammar = 'a'{3} 'b'{1,4} end"
        self.check(grammar, text='a',
                   err='<string>:1 Unexpected end of input at column 2')
        self.check(grammar, text='aaa',
                   err='<string>:1 Unexpected end of input at column 4')
        self.check(grammar, text='aaab', out=None)
        self.check(grammar, text='aaabbbbb',
                   err='<string>:1 Unexpected "b" at column 8')

    def test_cpp_style_comment_in_grammar(self):
        self.check(
            """\
            grammar = // ignore this line
                      end -> true
            """,
            text='',
            out=True,
        )

    def test_cpp_style_comment_eol(self):
        self.check('grammar = //\r\nend -> true', text='', out=True)
        self.check('grammar = //\nend -> true', text='', out=True)

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
        self.check('grammar = "\\n\\"foo" -> true', text='\n"foo', out=True)
        self.check("grammar = '\\'foo' -> true", text="'foo", out=True)

    def test_exclude(self):
        self.check('g = [^ab] -> true', text='c', out=True)
        self.check(
            'g = [^a] -> true',
            text='a',
            err='<string>:1 Unexpected "a" at column 1',
        )
        self.check(
            'g = [^a] -> true',
            text='',
            err='<string>:1 Unexpected end of input at column 1',
        )
        self.check(
            'g = [^\\]] -> true',
            text=']',
            err='<string>:1 Unexpected "]" at column 1',
        )
        self.check(
            'g = [^] -> true',
            text='',
            grammar_err='<string>:1 Unexpected "]" at column 7',
        )
        self.check(
            'g = [^',
            text='',
            grammar_err='<string>:1 Unexpected end of input at column 7',
        )
        self.check('g = [^\\ta\\n] -> true', text='e', out=True)

    def test_exclude_esc_char(self):
        self.check(
            'g = [^\\n] -> true',
            text='\n',
            err='<string>:1 Unexpected "\\n" at column 1',
        )

    @skip('integration')
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
        self.assertIsNone(err)
        self.assertEqual(out[0], 'rules')

    @skip('integration')
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
        self.assertIsNone(err)
        self.assertEqual(out[0], 'rules')

    def test_fn_arrcat(self):
        self.check('g = -> arrcat([1], [2])', text='', out=[1, 2])

    def test_fn_strcat(self):
        self.check("g = -> strcat('foo', 'bar')", text='', out='foobar')

    def test_fn_dict(self):
        self.check(
            "g = -> dict([['a', 1], ['b', 2]])", text='', out={'a': 1, 'b': 2}
        )

    def test_fn_float(self):
        self.check("g = -> float('4.3')", text='', out=4.3)

    def test_fn_is_unicat(self):
        self.check("g = -> is_unicat('1', 'Nd')", text='', out=True)

    def test_fn_itou(self):
        self.check('grammar = -> itou(97)', text='', out='a')

    def test_fn_join(self):
        self.check("g = -> join('x', ['1', '2', '3'])", text='', out='1x2x3')

    def test_fn_utoi(self):
        self.check('grammar = -> utoi("a")', text='', out=97)

    def test_fn_xtoi(self):
        self.check("g = -> xtoi('0x41')", text='', out=65)

    def test_fn_xtou(self):
        self.check("g = -> xtou('0x41')", text='', out='A')

    def test_hex_digits_in_value(self):
        self.check('grammar = -> 0x20', text='', out=32)

    def test_hex_digits_invalid(self):
        # '0xtt' is an invalid hex number, so that ll_prim check fails and
        # we go on to digits, so '0' is parsed successfully. We next parse
        # 'xtt' as an ident as the first part of the next rule but run out
        # of input.
        # TODO: Reject this earlier as an invalid hex/invalid num.
        self.check(
            'grammar = -> 0xtt',
            text='',
            # grammar_err='<string>:1 Unexpected end of input at column 18',
            grammar_err='Errors were found:\n  Unknown rule "xtt"\n',
        )

    def test_inline_seq(self):
        # This checks that we correctly include the builtin `end` rule
        # when it is part of a parenthesized choice.
        self.check("g = ('foo'|end) -> true", text='', out=True)

    def test_inline_parens(self):
        # This is a regression test for a subtle bug found when working
        # on the inlining code in the generator; the method for the second
        # choice was overwriting the method for the first choice.
        self.check(
            """
            g  = (sp '*') | (sp '+')
            sp = ' '
            """,
            text=' *',
            out='*',
        )

    @skip('integration')
    def test_json5(self):
        h = floyd.host.Host()
        path = str(THIS_DIR / '../grammars/json5.g')
        p, err, _ = self.compile(h.read_text_file(path))
        self.assertIsNone(err)
        self._common_json5_checks(p)

    @skip('integration')
    def test_json5_special_floats(self):
        h = floyd.host.Host()
        path = str(THIS_DIR / '../grammars/json5.g')
        p, err, _ = self.compile(h.read_text_file(path))
        self.assertIsNone(err)

        self.checkp(p, text='Infinity', out=float('inf'))

        # Can't use check() for this because NaN != NaN.
        obj, err, _ = p.parse('NaN')
        self.assertTrue(math.isnan(obj))
        self.assertTrue(err is None)

        if hasattr(p, 'cleanup'):
            p.cleanup()

    def _common_json5_checks(self, p):
        self.checkp(p, text='123', out=123)
        self.checkp(p, text='1.5', out=1.5)
        self.checkp(p, text='+1.5', out=1.5)
        self.checkp(p, text='-1.5', out=-1.5)
        self.checkp(p, text='1.5e2', out=150)
        self.checkp(p, text='.5e-2', out=0.005)
        self.checkp(p, text='null', out=None)
        self.checkp(p, text='true', out=True)
        self.checkp(p, text='false', out=False)
        self.checkp(p, text='"foo"', out='foo')
        self.checkp(p, text='[]', out=[])
        self.checkp(p, text='[2]', out=[2])
        self.checkp(p, text='{}', out={})
        self.checkp(p, text='{foo: "bar"}', out={'foo': 'bar'})

        self.checkp(
            p, text='[1', err='<string>:1 Unexpected end of input at column 3'
        )

        # Check that leading whitespace is allowed.
        self.checkp(p, '  {}', {})

        if hasattr(p, 'cleanup'):
            p.cleanup()

    @skip('integration')
    def test_json5_sample(self):
        # Check the sample file from pyjson5.
        # this skips the `'to': Infinity` pair because that can't
        # be marshalled in and out of JSON.
        h = floyd.host.Host()
        path = str(THIS_DIR / '../grammars/json5.g')
        p, err, _ = self.compile(h.read_text_file(path))
        self.assertIsNone(err)
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
                'finally': 'a trailing comma',
                'oh': [
                    "we shouldn't forget",
                    'arrays can have',
                    'trailing commas too',
                ],
            },
        )
        if hasattr(p, 'cleanup'):
            p.cleanup()

    @skip('integration')
    def test_json5_2(self):
        h = floyd.host.Host()
        path = str(THIS_DIR / '../grammars/json5_2.g')
        grammar = h.read_text_file(path)
        p, err, _ = self.compile(grammar)
        self.assertIsNone(err)
        self.checkp(
            p, text='{foo: "bar", a: "b"}', out={'foo': 'bar', 'a': 'b'}
        )
        # self._common_json5_checks(p)

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

    def test_ll_num(self):
        self.check('grammar = end -> 1', text='', out=1)
        self.check('grammar = end -> 0x20', text='', out=32)

    def test_ll_plus(self):
        self.check(
            "grammar = 'a':a 'b'*:bs -> a + join('', bs)",
            text='abb',
            out='abb',
        )

    def test_long_unicode_literals(self):
        self.check("grammar = '\\U00000020' -> true", text=' ', out=True)

    def test_not_not(self):
        self.check("grammar = ~~('a') 'a' -> true", text='a', out=True)

    @skip('operators')
    def test_not_quite_operators(self):
        # This tests things that will currently not be classified as
        # operator expressions.

        # Too many terms.
        self.check("expr = expr '+' expr '++' expr | 'x'", 'x+x++x', out='x')

        # Can't use a range instead of a literal as an operator.
        self.check("expr = expr '0'..'9' expr | 'x'", 'x', out='x')

        # The precedence of '+' is not specified. TODO: handle this.
        self.check("expr = expr '+' expr | 'x'", 'x+x', out='x')

        # rhs isn't recursive.
        self.check(
            """
            %prec '+'
            expr = expr '+' '0'
                 | 'x'
            """,
            'x+0',
            out='0',
        )

        # Too many base cases. TODO: handle this.
        self.check(
            """
            %prec '+'
            expr = expr '+' expr
                 | '0'
                 | 'x'
            """,
            '0+x',
            out='x',
        )

        # Base case isn't a single expr. TODO: handle this.
        self.check(
            """
            %prec '+'
            expr = expr '+' expr
                 | 'x' 'y'
            """,
            'xy',
            out='y',
        )

        # Fourth term isn't an action: TODO: handle 'end' as a special case.
        self.check(
            """
            %prec '+'
            expr = expr '+' expr end
                | 'x'
            """,
            'x+x',
            out=None,
        )

    def test_operator_invalid(self):
        g = """
           %prec a
           expr = expr 'a' expr -> [$1, 'a', $3]
                | '0'..'9'
        """
        self.check(
            g, text='1', grammar_err='<string>:2 Unexpected "a" at column 7'
        )

    @skip('operators')
    def test_operators(self):
        # For now, precedence has no effect but this at least tests
        # that the pragmas get parsed.
        g = """
            %prec '+' '-'
            %prec '*' '/'
            %prec '^'
            %assoc '^' right
            %assoc '+' left   // this is unnecessary but gets us coverage.
            expr = expr '+' expr -> [$1, '+', $3]
                 | expr '-' expr -> [$1, '-', $3]
                 | expr '*' expr -> [$1, '*', $3]
                 | expr '/' expr -> [$1, '/', $3]
                 | expr '^' expr -> [$1, '^', $3]
                 | '0'..'9'
            """
        self.check(g, text='1', out='1')
        self.check(g, text='1+2', out=['1', '+', '2'])
        self.check(g, text='1+2*3', out=['1', '+', ['2', '*', '3']])
        self.check(g, text='1+2-3', out=[['1', '+', '2'], '-', '3'])

        self.check(
            g,
            text='1^2^3+4*5/6',
            out=[
                ['1', '^', ['2', '^', '3']],
                '+',
                [['4', '*', '5'], '/', '6'],
            ],
        )

    @skip('operators')
    def test_operators_multichar_is_valid(self):
        # This tests that operators do not have to be just a single character.
        g = """
           %prec '++'
           expr = expr '++' expr -> [$1, '++', $3]
                | '0'..'9'
        """
        self.check(g, text='1++2', out=['1', '++', '2'])

    @skip('operators')
    def test_operators_with_whitespace(self):
        # For now, precedence has no effect but this at least tests
        # that the pragmas get parsed.
        g = """
            %whitespace = (' '|'\n'|'\r'|'\t')*
            %prec '+' '-'
            %prec '*' '/'
            %prec '^'
            %assoc '^' right
            expr = expr '+' expr -> [$1, '+', $3]
                 | expr '-' expr -> [$1, '-', $3]
                 | expr '*' expr -> [$1, '*', $3]
                 | expr '/' expr -> [$1, '/', $3]
                 | expr '^' expr -> [$1, '^', $3]
                 | '0'..'9'
            """
        self.check(g, text='1', out='1')
        self.check(g, text='1 + 2', out=['1', '+', '2'])
        self.check(
            g,
            text='1^2^3 + 4 * 5 / 6',
            out=[
                ['1', '^', ['2', '^', '3']],
                '+',
                [['4', '*', '5'], '/', '6'],
            ],
        )

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

    @skip('leftrec')
    def test_recursion_both(self):
        grammar = """\
            expr = expr:l '+' expr:r -> [l, '+', r]
                 | '0'..'9':d        -> d
            """
        # Note that a grammar that is both left- and right-recursive
        # is left-associative by default.
        self.check(grammar, '1+2+3', [['1', '+', '2'], '+', '3'])

    @skip('leftrec')
    def test_recursion_direct_left(self):
        self.check(
            """\
            grammar = grammar:g '+' 'a' -> [g, '+', 'a']
                    | 'a'               -> 'a'
            """,
            'a+a+a',
            [['a', '+', 'a'], '+', 'a'],
        )

    @skip('leftrec')
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

    @skip('leftrec')
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

    @skip('leftrec')
    def test_recursion_left_opt(self):
        grammar = """\
            grammar = 'b'?:b grammar:g 'c' -> join('', b) + g + 'c'
                    | 'a'           -> 'a'
            """
        # self.check(grammar, 'ac', 'ac')
        # self.check(grammar, 'acc', 'acc')

        # This result happens because grammar is left-associative by
        # default, and so when grammar is invoked the second time,
        # it is blocked and fails to recurse a third time; that allows
        # it to consume the 'a' and then complete. The first invocation
        # is then free to consume the 'c'.
        # self.check(grammar, 'bac', 'bac')

        # Now, since the grammar is now declared to be right-associative,
        # when grammar is invoked for the second time, it is not blocked,
        # and it can consume the 'a' and then the 'c' before completing.
        # Once that completes, there is no longer any input left for the
        # first invocation to consume and so it fails to find the 'c' it
        # needs.
        grammar = """\
            %assoc 'grammar#1' right
            grammar = 'b'?:b grammar:g 'c' -> join('', b) + g + 'c'
                    | 'a'           -> 'a'
            """
        self.check(
            grammar,
            'bac',
            err='<string>:1 Unexpected end of input at column 4',
        )

    @skip('leftrec')
    def test_recursion_repeated(self):
        self.check(
            """
            grammar = grammar:x grammar:y 'a' -> [x, y, 'a']
                    | 'a'                     -> 'a'
            """,
            'aaa',
            ['a', 'a', 'a'],
        )

    def test_regexp(self):
        self.check('g = /.+/', text='abc', out='abc')

    def test_rule_with_lit_str(self):
        self.check(
            """\
            grammar = foo* -> true
            foo     = 'foo'
            """,
            text='foofoo',
            out=True,
        )

    def test_run(self):
        self.check("g = <'a' 'b' 'c'> -> true", text='abc', out=True)
        self.check("g = <'a' 'b' 'c'> -> true", text='d',
                   err= '<string>:1 Unexpected "d" at column 1')

    def test_seq(self):
        self.check("grammar = 'foo' 'bar' -> true", text='foobar', out=True)

    def test_star(self):
        self.check("grammar = 'a'* -> true", text='', out=True)
        self.check("grammar = 'a'* -> true", text='a', out=True)
        self.check("grammar = 'a'* -> true", text='aa', out=True)

    def test_star_nested(self):
        # This checks to make sure we don't get stuck in an infinite
        # loop where the inner star always succeeds so the outer star
        # keeps looping. The implementation should break out if it
        # doesn't actually consume anything.
        self.check("grammar = ('a'*)* 'b' -> true", text='b', out=True)

    def test_tabs_are_whitespace(self):
        self.check("grammar\t=\t'a'\t->\ttrue", text='a', out=True)

    def test_token_is_invalid(self):
        self.check(
            '%tokens 1234',
            text='',
            grammar_err='<string>:1 Unexpected "1" at column 9',
        )

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

    def test_whitespace_chars(self):
        self.check('g = \t\n\r { true }', text='', out=True)

    def test_whitespace_pragma(self):
        grammar = """\
            %token foo
            %whitespace = ' '

            grammar = foo foo end -> true

            foo     = 'foo'
            """
        self.check(grammar, text='foofoo', out=True)


class Interpreter(unittest.TestCase, GrammarTestsMixin):
    max_diff = None

    def compile(self, grammar, path='<string>', memoize=False):
        return floyd.compile(textwrap.dedent(grammar), path, memoize=memoize)


class PythonGenerator(unittest.TestCase, GrammarTestsMixin):
    max_diff = None

    def compile(self, grammar, path='<string>', memoize=False):
        source_code, err, endpos = floyd.generate(
            textwrap.dedent(grammar),
            path=path,
            options=floyd.GeneratorOptions(main=False, memoize=memoize),
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
        parse_fn = scope['parse']
        if debug:  # pragma: no cover
            h.rmtree(d)
        return _PythonParserWrapper(parse_fn), None, 0


class _PythonParserWrapper:
    def __init__(self, parse_fn):
        self.parse_fn = parse_fn

    def parse(self, text, path='<string>'):
        return self.parse_fn(text, path)

    def cleanup(self):
        pass


class JavaScriptGenerator(unittest.TestCase, GrammarTestsMixin):
    maxDiff = None

    def compile(self, grammar, path='<string>', memoize=False):
        del memoize
        source_code, err, endpos = floyd.generate(
            textwrap.dedent(grammar),
            path=path,
            options=floyd.GeneratorOptions(
                language='javascript', main=True, memoize=False
            ),
        )
        if err:
            assert source_code is None
            return None, err, endpos

        h = floyd.host.Host()
        d = h.mkdtemp()
        h.write_text_file(d + '/parser.js', source_code)
        return _JavaScriptParserWrapper(h, d), None, 0

    def test_exclude_esc_char(self):
        # The JS implementation isn't smart enough to escape unexpected
        # characters yet.
        # TODO: Fix this.
        pass

    def test_fn_is_unicat(self):
        # Can't implement this in JavaScript.
        pass

    @skip('integration')
    def test_json5_special_floats(self):
        # TODO: `Infinity` and `NaN` are legal Python values and legal
        # JavaScript values, but they are not legal JSON values, and so
        # we can't read them in from output that is JSON.
        pass


class _JavaScriptParserWrapper:
    def __init__(self, h, d):
        self.h = h
        self.d = d
        self.source = d + '/parser.js'

    def parse(self, text, path='<string>'):
        del path
        inp = self.d + '/input.txt'
        self.h.write_text_file(inp, text)
        proc = subprocess.run(
            ['node', self.source, inp], check=False, capture_output=True
        )
        if proc.returncode == 0:
            return json.loads(proc.stdout), None, 0
        return None, proc.stderr.decode('utf8'), 0

    def cleanup(self):
        self.h.rmtree(self.d)
