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
import os
import pathlib
import shutil
import subprocess
import sys
import textwrap
from typing import Optional, Dict
import unittest

import pyfloyd
import pyfloyd.host


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
    max_diff = None
    floyd_externs: Optional[Dict[str, bool]] = None

    def check(
        self,
        grammar,
        text,
        out=None,
        err=None,
        grammar_err=None,
    ):
        p, p_err, _ = self.compile(grammar)
        self.assertMultiLineEqual(grammar_err or '', p_err or '')
        if p:
            self.checkp(p, text, out, err)
        if hasattr(p, 'cleanup'):
            p.cleanup()

    def checkp(self, parser, text, out=None, err=None, externs=None):
        actual_out, actual_err, _ = parser.parse(
            text, path='<string>', externs=externs
        )
        # Test err before out because it's probably more helpful to display
        # an unexpected error than it is to display an unexpected output.
        self.assertMultiLineEqual(err or '', actual_err or '')
        self.assertEqual(out, actual_out)

    def check_grammar_error(self, grammar, err):
        p, p_err, _ = self.compile(grammar)
        self.assertIsNone(p)
        self.assertMultiLineEqual(err, p_err)

    def test_action(self):
        # self.check('grammar = end { true }', text='', out=True)
        self.check('grammar = end -> true', text='', out=True)

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

    def test_e_not(self):
        self.check('g = -> !false', text='', out=True)
        self.check('g = -> !true', text='', out=False)
        self.check('g = (?{true}):x -> !x', text='', out=False)

    def test_quals(self):
        self.check("g = -> utoi(' ')", text='', out=32)
        self.check("g = 'x'*:l -> l[0]", text='xx', out='x')
        self.check("g = -> ['a', 'b'][1]", text='', out='b')
        self.check("g = -> [['a']][0][0]", text='', out='a')

    def test_array(self):
        self.check(
            """\
            grammar = '[' value:v (',' value)*:vs ','? ']' -> concat([v], vs)
            value   = '2':v                                -> atof(v)
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
            # 'grammar = { float("505874924095815700") }',
            'grammar = -> atof("505874924095815700")',
            text='',
            out=505874924095815700,
        )
        self.check(
            # 'grammar = { 505874924095815700 }', text='',
            # out=505874924095815700
            'grammar = -> 505874924095815700',
            text='',
            out=505874924095815700,
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
            %tokens = foo
            %comment = '//' (~'\n' any)*
            grammar = (foo ' '* '\n')+  end -> true

            foo     = 'foo'
            """
        self.check(grammar, text='foo\nfoo\n', out=True)

    def test_count(self):
        grammar = "grammar = 'a'{3} 'b'{1,4} end"
        self.check(
            grammar,
            text='a',
            err='<string>:1 Unexpected end of input at column 2',
        )
        self.check(
            grammar,
            text='aaa',
            err='<string>:1 Unexpected end of input at column 4',
        )
        self.check(grammar, text='aaab', out=None)
        self.check(
            grammar,
            text='aaabbbbb',
            err='<string>:1 Unexpected "b" at column 8',
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

    def test_ends_in(self):
        g = "g = ^.'a' -> true"
        self.check(g, '', err='<string>:1 Unexpected end of input at column 1')
        self.check(
            g, 'b', err='<string>:1 Unexpected end of input at column 2'
        )
        self.check(g, 'ba', out=True)

    def test_equals(self):
        g = "g = ={'foo'}"
        self.check(g, 'foo', out='foo')
        self.check(g, 'bar', err='<string>:1 Unexpected "b" at column 1')

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
                'Errors were found:\n  Unknown function "foo" called\n'
            ),
        )

    def test_error_on_unknown_var(self):
        self.check(
            'grammar = -> v',
            text='',
            grammar_err=(
                'Errors were found:\n  Unknown variable "v" referenced\n'
            ),
        )

    def test_error_on_unknown_rule(self):
        self.check(
            'grammar = foo',
            text='',
            grammar_err=('Errors were found:\n  Unknown rule "foo"\n'),
        )

        # Check that referring to a reserved rule is caught when the rule
        # isn't defined.
        self.check(
            textwrap.dedent("""\
            grammar = _whitespace
            """),
            text='',
            grammar_err=('Errors were found:\n  Unknown rule "_whitespace"\n'),
        )

        # Check that referring to a reserved rule is caught when the rule
        # is defined.
        self.check(
            textwrap.dedent("""\
            %whitespace = ' '
            grammar = _whitespace
            """),
            text='',
            grammar_err=('Errors were found:\n  Unknown rule "_whitespace"\n'),
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

    @skip('integration')
    def test_floyd(self):
        h = pyfloyd.host.Host()
        path = str(THIS_DIR / '../grammars/floyd.g')
        grammar = h.read_text_file(path)
        p, err, _ = self.compile(
            grammar, path, memoize=True, externs=self.floyd_externs
        )
        self.assertIsNone(err)
        out, err, _ = p.parse(grammar, '../grammars/floyd.g')
        # We don't check the actual output here because it is too long
        # and we don't want the test to be so sensitive to the AST for
        # the floyd grammar.
        self.assertIsNone(err)
        self.assertEqual(out[0], 'rules')

    @skip('integration')
    def test_floyd_ws(self):
        h = pyfloyd.host.Host()
        path = str(THIS_DIR / '../grammars/floyd_ws.g')
        grammar = h.read_text_file(path)
        p, err, _ = self.compile(grammar, path, externs=self.floyd_externs)
        self.assertIsNone(err)
        out, err, _ = p.parse(grammar, '../grammars/floyd.g')
        # We don't check the actual output here because it is too long
        # and we don't want the test to be so sensitive to the AST for
        # the floyd grammar.
        self.assertIsNone(err)
        self.assertEqual(out[0], 'rules')

    def test_fn_atof(self):
        self.check("g = -> atof('1.3')", text='', out=1.3)

    def test_fn_atoi(self):
        self.check("g = -> atoi('0x41', 16)", text='', out=65)

    def test_fn_atou(self):
        self.check("g = -> atou('65', 10)", text='', out='A')
        self.check("g = -> atou('0x41', 16)", text='', out='A')

    def test_fn_cat(self):
        self.check("g = -> cat(['1', '2'])", text='', out='12')

    def test_fn_concat(self):
        self.check('g = -> concat([1], [2])', text='', out=[1, 2])

    def test_fn_cons(self):
        self.check('g = -> cons(1, [2, 3])', text='', out=[1, 2, 3])

    def test_fn_dedent(self):
        self.check('g = -> dedent("foo")', text='', out='foo')

    def test_fn_dict(self):
        self.check(
            "g = -> dict([['a', 1], ['b', 2]])", text='', out={'a': 1, 'b': 2}
        )

    def disabled_test_fn_int(self):
        self.check('g = int(4.0)', text='', out=4)

    def test_fn_itou(self):
        self.check('grammar = -> itou(97)', text='', out='a')

    def test_fn_join(self):
        self.check("g = -> join('x', ['1', '2', '3'])", text='', out='1x2x3')

    def test_fn_scons(self):
        self.check(
            "g = -> scons('a', ['b', 'c'])", text='', out=['a', 'b', 'c']
        )

    def test_fn_strcat(self):
        self.check("g = -> strcat('foo', 'bar')", text='', out='foobar')

    def test_fn_utoi(self):
        self.check('grammar = -> utoi("a")', text='', out=97)

    def test_fn_xtou(self):
        self.check("g = -> xtou('0x41')", text='', out='A')

    def test_hex_digits_in_value(self):
        self.check('grammar = -> 0x20', text='', out=32)

    def test_hex_digits_invalid(self):
        self.check(
            'grammar = -> 0xtt',
            text='',
            grammar_err='<string>:1 Unexpected "t" at column 16',
        )

    def test_illegal_rule_names(self):
        self.check(
            '_foo = end',
            '',
            grammar_err=(
                'Errors were found:\n'
                '  Illegal rule name "_foo": names starting with '
                'an "_" are reserved\n'
            ),
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
    def test_json(self):
        h = pyfloyd.host.Host()
        path = str(THIS_DIR / '../grammars/json.g')
        p, err, _ = self.compile(h.read_text_file(path), path)
        self.assertIsNone(err)
        self._common_json_checks(p, {})

        self.checkp(p, text='"foo"', out='"foo"', externs={})

        if hasattr(p, 'cleanup'):
            p.cleanup()

    @skip('integration')
    def test_json5(self):
        externs = {'strict': True}
        h = pyfloyd.host.Host()
        path = str(THIS_DIR / '../grammars/json5.g')
        p, err, _ = self.compile(h.read_text_file(path), path)
        self.assertIsNone(err)
        self._common_json_checks(p, externs=externs)
        self._common_json5_checks(p, externs=externs)

    @skip('integration')
    def test_json5_special_floats(self):
        externs = {'strict': True}
        h = pyfloyd.host.Host()
        path = str(THIS_DIR / '../grammars/json5.g')
        p, err, _ = self.compile(h.read_text_file(path), path)
        self.assertIsNone(err)

        # TODO: Figure out what to do with 'Infinity' and 'NaN'.
        # self.checkp(p, text='Infinity', out=float('inf'))
        self.checkp(p, text='Infinity', out='Infinity', externs=externs)

        # Can't use check() for this because NaN != NaN.
        # obj, err, _ = p.parse('NaN')
        # self.assertTrue(math.isnan(obj))
        # self.assertTrue(err is None)
        self.checkp(p, text='NaN', out='NaN', externs=externs)

        if hasattr(p, 'cleanup'):
            p.cleanup()

    def _common_json_checks(self, p, externs):
        self.checkp(p, text='123', out=123, externs=externs)
        self.checkp(p, text='1.5', out=1.5, externs=externs)
        self.checkp(p, text='-1.5', out=-1.5, externs=externs)
        self.checkp(p, text='1.5e2', out=150, externs=externs)
        self.checkp(p, text='null', out=None, externs=externs)
        self.checkp(p, text='true', out=True, externs=externs)
        self.checkp(p, text='false', out=False, externs=externs)

        self.checkp(p, text='[]', out=[], externs=externs)
        self.checkp(p, text='[2]', out=[2], externs=externs)
        self.checkp(p, text='{}', out={}, externs=externs)

        self.checkp(
            p,
            text='[1',
            err='<string>:1 Unexpected end of input at column 3',
            externs=externs,
        )

        # Check that leading whitespace is allowed.
        self.checkp(p, '  {}', {}, externs=externs)

    def _common_json5_checks(self, p, externs):
        self.checkp(p, text='+1.5', out=1.5, externs=externs)
        self.checkp(p, text='.5e-2', out=0.005, externs=externs)
        self.checkp(p, text='"foo"', out='foo', externs=externs)
        self.checkp(
            p,
            text='{foo: "bar", a: "b"}',
            out={'foo': 'bar', 'a': 'b'},
            externs=externs,
        )

    @skip('integration')
    def test_json5_sample(self):
        # Check the sample file from pyjson5.
        # this skips the `'to': Infinity` pair because that can't
        # be marshalled in and out of JSON.
        h = pyfloyd.host.Host()
        path = str(THIS_DIR / '../grammars/json5.g')
        p, err, _ = self.compile(h.read_text_file(path), path)
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
            externs={'strict': False},
        )
        if hasattr(p, 'cleanup'):
            p.cleanup()

    @skip('integration')
    def test_json5_ws(self):
        externs = {'strict': False}
        h = pyfloyd.host.Host()
        path = str(THIS_DIR / '../grammars/json5_ws.g')
        grammar = h.read_text_file(path)
        p, err, _ = self.compile(grammar, path)
        self.assertIsNone(err)
        self._common_json_checks(p, externs=externs)
        self._common_json5_checks(p, externs=externs)

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
                'Errors were found:\n'
                '  Variable "$2" referenced before it was available\n'
            ),
        )

    def test_label_nested_works(self):
        # Named variables defined in an outer sequence *should* be
        # visible in an inner sequence. This shows that either dynamically
        # or lexically scoped variables *might* work.
        # TODO: Make this work.
        g = "g = 'foo':f ('x'+ ={f})* -> true"
        self.check(g, text='fooxfoo', out=True)

    def test_label_inner_not_in_outer(self):
        # Named variables defined in an inner sequence should *not* be
        # visible in an outer sequence. This shows that there are different
        # scopes for inner and outer sequences.
        # TODO: Can we provide a better error here?
        self.check(
            "g = 'foo' ('x'+:x) -> cat(x)",
            text='fooxxx',
            grammar_err=(
                'Errors were found:\n'
                '  Variable "x" never used\n'
                '  Unknown variable "x" referenced\n'
            ),
        )

    def test_label_separate_rule_does_not_work(self):
        # Named variables defined in an outer sequence should *not* be
        # visible in separate rules referenced as inner terms.
        # This shows that 'dynamically scoped' variables aren't supported.
        g = """
        g   = 'foo':f bar -> true

        bar = 'x'+ ={f}
        """
        self.check(
            g,
            text='fooxfoo',
            grammar_err=(
                'Errors were found:\n'
                '  Variable "f" never used\n'
                '  Unknown variable "f" referenced\n'
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

    def test_not_one(self):
        self.check("grammar = ^'a' 'b'-> true", text='cb', out=True)
        self.check(
            "grammar = ^'a' 'b'-> true",
            text='a',
            err='<string>:1 Unexpected "a" at column 1',
        )
        self.check(
            "grammar = ^'a' 'b'-> true",
            text='',
            err='<string>:1 Unexpected end of input at column 1',
        )

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
            %prec = '+'
            expr = expr '+' '0'
                 | 'x'
            """,
            'x+0',
            out='0',
        )

        # Too many base cases. TODO: handle this.
        self.check(
            """
            %prec = '+'
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
            %prec = '+'
            expr = expr '+' expr
                 | 'x' 'y'
            """,
            'xy',
            out='y',
        )

        # Fourth term isn't an action: TODO: handle 'end' as a special case.
        self.check(
            """
            %prec = '+'
            expr = expr '+' expr end
                | 'x'
            """,
            'x+x',
            out=None,
        )

    def test_operator_indirect(self):
        # Tests that you can specify the list of operators in a rule
        # separate from the actual pragma.
        g = """
            %prec = op
            expr  = expr op expr -> [$1, $2, $3]
                  | '0'..'9'
            op    = '+' | '-'
        """
        self.check(g, '1+2', out=['1', '+', '2'])

    @skip('operators')
    def test_operator_invalid(self):
        # TODO: Provide a better error message, allow rules that expand
        # to literals.
        g = """
           %prec = a
           expr = expr 'b' expr -> [$1, 'b', $3]
                | '0'..'9'
        """
        self.check(
            g,
            text='1',
            grammar_err=('Errors were found:\n  Unknown rule "a"\n'),
        )

    @skip('operators')
    def test_operators(self):
        # For now, precedence has no effect but this at least tests
        # that the pragmas get parsed.
        g = """
            %prec = '+' '-'
            %prec = '*' '/'
            %prec = '^'
            %assoc = '^' right
            %assoc = '+' left   // this is unnecessary but gets us coverage.
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
           %prec = '++'
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
            %prec = '+' '-'
            %prec = '*' '/'
            %prec = '^'
            %assoc = '^' right
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
        # self.check('grammar = ?{true} end { true }', text='', out=True)
        self.check('grammar = ?{true} end -> true', text='', out=True)
        self.check(
            """\
            grammar = ?{false} end -> 'a'
                    | end -> 'b'
            """,
            text='',
            out='b',
        )
        self.check(
            'grammar = ?{"foo"} end -> false',
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
            %assoc = 'grammar#1' right
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
        self.check(
            "g = <'a' 'b' 'c'> -> true",
            text='d',
            err='<string>:1 Unexpected "d" at column 1',
        )

    def test_seq(self):
        self.check("grammar = 'foo' 'bar' -> true", text='foobar', out=True)

    def test_set(self):
        g = 'g = [xa-e] -> true'
        self.check(g, text='x', out=True)
        self.check(g, text='a', out=True)
        self.check(g, text='b', out=True)
        self.check(g, text='e', out=True)
        self.check(
            g, text='', err='<string>:1 Unexpected end of input at column 1'
        )
        self.check(g, text='f', err='<string>:1 Unexpected "f" at column 1')

    def test_set_exclude(self):
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

    def test_set_exclude_esc_char(self):
        self.check(
            'g = [^\\n] -> true',
            text='\n',
            err='<string>:1 Unexpected "\\n" at column 1',
        )

    def test_set_escaped_right_bracket(self):
        g = r'g = [xa-e\]] -> true'
        self.check(g, text=']', out=True)

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
            '%tokens = 1234',
            text='',
            grammar_err='<string>:1 Unexpected "1" at column 11',
        )

    def test_token_pragma(self):
        self.check(
            """\
            %tokens = foo
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
            %tokens = quux
            grammar = foo -> true
            foo     = bar
            bar     = 'baz'
            """,
            text='baz',
            grammar_err='Errors were found:\n  Unknown token rule "quux"\n',
        )

    def test_tokens_pragma(self):
        grammar = """\
            %tokens = foo bar
            grammar = (foo bar)+ end -> true
            foo     = 'foo'
            bar     = 'bar'
            """
        self.check(grammar, text='foobar', out=True)

    def test_unknown_pragma(self):
        self.check(
            '%foo = end',
            text='',
            out=None,
            grammar_err=('Errors were found:\n  Unknown pragma "%foo"\n'),
        )

    def test_whitespace_chars(self):
        # self.check('g = \t\n\r { true }', text='', out=True)
        self.check('g = \t\n\r -> true', text='', out=True)

    def test_whitespace_pragma(self):
        grammar = textwrap.dedent("""\
            %tokens = foo
            %whitespace = ' '

            grammar = foo foo end -> true

            foo     = 'foo'
            """)
        self.check(grammar, text='foofoo', out=True)

    def test_whitespace_can_be_referenced(self):
        grammar = textwrap.dedent("""\
            %whitespace = ' '

            %tokens     = foo

            grammar     = foo  -> true

            foo         = '"' %whitespace '"'
            """)
        self.check(grammar, '" "', out=True)


class Interpreter(unittest.TestCase, GrammarTestsMixin):
    max_diff = None

    def compile(self, grammar, path='<string>', memoize=False, externs=None):
        return pyfloyd.compile(
            textwrap.dedent(grammar), path, memoize=memoize, externs=externs
        )


class _GeneratedParserWrapper:
    def __init__(self, cmd, ext, source_code):
        self.cmd = cmd
        self.ext = ext
        self.source_code = source_code
        self.host = pyfloyd.host.Host()
        self.tempdir = self.host.mkdtemp()
        self.source_code = source_code
        self.source = os.path.join(self.tempdir, f'parser{self.ext}')
        self.host.write_text_file(self.source, self.source_code)

    def parse(self, text, path='<string>', externs=None):
        inp = os.path.join(self.tempdir, 'input.txt')
        self.host.write_text_file(inp, text)
        defines = []
        externs = externs or {}
        for k, v in externs.items():
            defines.extend(['-D', f'{k}={json.dumps(v)}'])
        proc = subprocess.run(
            self.cmd + [self.source] + defines + [inp],
            check=False,
            capture_output=True,
        )
        if proc.stderr:
            stderr = proc.stderr.decode('utf8').strip()
            try:
                assert inp in stderr, f'"{inp}" not in "{stderr}"'
            except Exception as e:
                import pdb

                pdb.set_trace()

            stderr = stderr.replace(inp, path)
        else:
            stderr = None
        if proc.returncode == 0:
            try:
                return json.loads(proc.stdout), None, 0
            except Exception as e:
                import pdb

                pdb.set_trace()

        return None, stderr, 0

    def cleanup(self):
        self.host.rmtree(self.tempdir)


class GeneratorMixin:
    def compile(self, grammar, path='<string>', memoize=False, externs=None):
        source_code, err, endpos = pyfloyd.generate(
            textwrap.dedent(grammar),
            path=path,
            options=pyfloyd.GeneratorOptions(
                language=self.language,
                main=True,
                memoize=memoize,
            ),
            externs=externs,
        )
        if err:
            assert source_code is None
            return None, err, endpos

        return (
            _GeneratedParserWrapper(self.cmd, self.ext, source_code),
            None,
            0,
        )


class PythonGenerator(unittest.TestCase, GeneratorMixin, GrammarTestsMixin):
    cmd = [sys.executable]
    language = 'python'
    ext = '.py'


class JavaScriptGenerator(
    unittest.TestCase, GeneratorMixin, GrammarTestsMixin
):
    cmd = [shutil.which('node')]
    language = 'javascript'
    ext = '.js'
    floyd_externs = {'unicode_names': False}

    @skip('integration')
    def test_json5_special_floats(self):
        # TODO: `Infinity` and `NaN` are legal Python values and legal
        # JavaScript values, but they are not legal JSON values, and so
        # we can't read them in from output that is JSON.
        pass
