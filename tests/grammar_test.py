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

# pylint: disable=too-many-lines, too-many-positional-arguments

import json
import os
import shlex
import shutil
import subprocess
import sys
import textwrap
from typing import Optional, Dict
import unittest

import pyfloyd


THIS_DIR = os.path.dirname(__file__)

SKIP = os.environ.get('SKIP', '')


class _JSONDecodeError(Exception):
    def __init__(self, stdout, *args):
        super().__init__(*args)
        self.stdout = stdout


def skip(kind):
    def decorator(fn):
        def wrapper(obj):
            if kind in SKIP:  # pragma: no cover
                obj.skipTest(kind)
            else:
                fn(obj)

        return wrapper

    return decorator


class Mixin(unittest.TestCase):
    max_diff = None
    floyd_externs: Optional[Dict[str, bool]] = None

    def read_grammar(self, grammar):
        path = os.path.join(THIS_DIR, '..', 'grammars', grammar)
        with open(path, 'r', encoding='utf8') as fp:
            return fp.read()

    def compile_grammar(self, grammar, **kwargs):
        contents = self.read_grammar(grammar)
        return self.compile(contents, grammar, **kwargs)

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
        ex = None
        try:
            actual_out, actual_err, _ = parser.parse(
                text, path='<string>', externs=externs
            )
        except _JSONDecodeError as e:
            ex = e

        if ex:
            if ex.stdout == b'':
                self.fail('Failed to decode JSON object from empty stdout')
            else:
                self.fail(
                    'Failed to decode JSON object from stdout'
                    + str(ex.stdout)
                    + ': `'
                    + str(ex)
                )

        # Test err before out because it's probably more helpful to display
        # an unexpected error than it is to display an unexpected output.
        if err is None and actual_err:
            print(
                'Got Unexpected stderr:\n  '
                + '\n  '.join(actual_err.splitlines())
                + '\n'
            )
            # self.fail('Unexpected stderr, see above')
            # return

        err = err or ''
        actual_err = actual_err or ''
        if err is not None:
            self.assertMultiLineEqual(err, actual_err)
        if out is not None:
            self.assertEqual(out, actual_out)

    def check_grammar_error(self, grammar, err):
        p, p_err, _ = self.compile(grammar)
        self.assertIsNone(p)
        self.assertMultiLineEqual(err, p_err)


class GeneratorMixin(Mixin):
    cmd: Optional[list] = None
    template: Optional[str] = None

    def compile(self, grammar, path='<string>', memoize=False, externs=None):
        if self.cmd is None:
            if os.path.sep in self.exe:
                cmd = [self.exe]
            elif self.exe == 'python':
                cmd = [sys.executable]
            else:
                cmd = [shutil.which(self.exe)]
        else:
            cmd = self.cmd

        generate_cmd = f'flc -g {self.generator} -T {self.template} --main'
        if memoize:
            generate_cmd += ' -G "memoize = true"'
        if externs:
            generate_cmd += ' -E {externs!r}'

        v, err, endpos = pyfloyd.generate(
            textwrap.dedent(grammar),
            path=path,
            options=pyfloyd.GeneratorOptions(
                generator=self.generator,
                template=self.template,
                main=True,
                memoize=memoize,
            ),
            externs=externs,
        )
        if err:
            assert v is None
            return None, err, endpos

        source_code, ext = v
        return (
            _GeneratedParserWrapper(
                cmd, ext, grammar, source_code, generate_cmd
            ),
            None,
            0,
        )


class _GeneratedParserWrapper:
    def __init__(self, cmd, ext, grammar, source_code, generate_cmd):
        self.cmd = cmd
        self.grammar = grammar
        self.source_code = source_code
        self.generate_cmd = generate_cmd
        self.host = pyfloyd.support.Host()
        self.tempdir = self.host.mkdtemp()
        self.source = os.path.join(self.tempdir, f'parser{ext}')
        self.host.write_text_file(self.source, self.source_code)

    def parse(self, text, path='<string>', externs=None):
        inp = os.path.join(self.tempdir, 'input.txt')
        self.host.write_text_file(inp, text)
        defines = []
        externs = externs or {}
        for k, v in externs.items():
            defines.extend(['-D', f'{k}={json.dumps(v)}'])

        cmd = self.cmd + [self.source] + defines + [inp]

        print()
        print('# Repro steps:')

        def _echo(text, file):
            lines = text.splitlines()
            if len(lines) > 1:
                print(f'echo {shlex.quote(lines[0])}  > {file} && \\')
                for line in lines[1:-1]:
                    print(f'echo {shlex.quote(line)}  >> {file} && \\')
                if text.endswith('\n'):
                    print(f'echo {shlex.quote(lines[-1])} >> {file} && \\')
                else:
                    print(f'echo -n {shlex.quote(lines[-1])} >> {file} && \\')
            elif text.endswith('\n'):
                print(f'echo {shlex.quote(text)}  > {file} && \\')
            else:
                print(f'echo -n {shlex.quote(text)}  > {file} && \\')

        _echo(self.grammar, 'parser.g')
        _echo(text, 'input.txt')
        print(f'{self.generate_cmd} parser.g && \\')
        print(shlex.join(arg.replace(self.tempdir, '.') for arg in cmd))
        print()

        proc = subprocess.run(cmd, check=False, capture_output=True)
        if proc.stderr:
            stderr = proc.stderr.decode('utf8').strip()
            stderr = stderr.replace(self.tempdir, '.')
            stderr = stderr.replace('./input.txt', path)
            if stderr.endswith('\nexit status 1'):
                stderr = stderr[: -len('\nexit status 1')]
        else:
            stderr = None

        if proc.returncode == 0:
            try:
                return json.loads(proc.stdout), None, 0
            except json.decoder.JSONDecodeError as e:
                raise _JSONDecodeError(proc.stdout, *e.args) from e

        return None, stderr, 0

    def cleanup(self):
        self.host.rmtree(self.tempdir)


class HelloMixin:
    def test_in(self):
        self.check(
            'grammar = "hello, world" -> true', 'hello, world', out=True
        )

    def test_out(self):
        self.check('grammar = -> "hello, world"', '', out='hello, world')

    def test_both(self):
        self.check(
            "grammar = any+ -> strcat('hello, ', join('', $1))",
            'world',
            out='hello, world',
        )


class RulesMixin:
    def test_action(self):
        self.check('grammar = -> true', '')

    def test_basic(self):
        self.check('grammar = end', '')

    def test_c_style_comment(self):
        self.check('grammar = /* foo */ end', '')

    def test_choice(self):
        self.check("grammar = 'foo' | 'bar'", 'foo')

        self.check("grammar = 'foo' | 'bar'", 'bar')

    def test_choice_with_rewind(self):
        self.check("grammar = 'a' 'b' | 'a' 'c'", 'ac')

    def test_count(self):
        grammar = "grammar = 'a'{3} 'b'{1,4} end"
        self.check(
            grammar,
            'a',
            err='<string>:1 Unexpected end of input at column 2',
        )
        self.check(
            grammar,
            'aaa',
            err='<string>:1 Unexpected end of input at column 4',
        )
        self.check(grammar, 'aaab')
        self.check(
            grammar,
            'aaabbbbb',
            err='<string>:1 Unexpected "b" at column 8',
        )

    def test_empty(self):
        self.check('grammar = ', '')

    def test_end(self):
        self.check(
            'grammar = end', 'foo', err='<string>:1 Unexpected "f" at column 1'
        )

    def test_ends_in(self):
        g = "g = ^.'a'"
        self.check(g, '', err='<string>:1 Unexpected end of input at column 1')
        self.check(
            g, 'b', err='<string>:1 Unexpected end of input at column 2'
        )
        self.check(g, 'ba')

    def test_equals(self):
        g = "g = ={'foo'}"
        self.check(g, 'foo', out='foo')
        self.check(g, 'bar', err='<string>:1 Unexpected "b" at column 1')

    def test_escape_unicat(self):
        self.check('grammar = \\p{Nd}', '1')

    def test_escapes_in_string(self):
        self.check('grammar = "\\n\\"foo"', '\n"foo')
        self.check("grammar = '\\'foo'", "'foo")

    def test_inline_seq(self):
        # This checks that we correctly include the builtin `end` rule
        # when it is part of a parenthesized choice.
        self.check("g = ('foo'|end)", '')

    def test_inline_parens(self):
        # This is a regression test for a subtle bug found when working
        # on the inlining code in the generator; the method for the second
        # choice was overwriting the method for the first choice.
        self.check(
            """
            g  = (sp '*') | (sp '+')
            sp = ' '
            """,
            ' *',
        )

    def test_lit_str(self):
        self.check("grammar = ('foo')*", 'foofoo')

    def test_long_unicode_literals(self):
        self.check("grammar = '\\U00000020'", ' ')

    def test_not_one(self):
        self.check("grammar = ^'a' 'b'", 'cb')
        self.check(
            "grammar = ^'a' 'b'",
            'a',
            err='<string>:1 Unexpected "a" at column 1',
        )
        self.check(
            "grammar = ^'a' 'b'",
            '',
            err='<string>:1 Unexpected end of input at column 1',
        )

    def test_not_not(self):
        self.check("grammar = ~~('a') 'a'", 'a')

    def test_opt(self):
        self.check("grammar = 'a' 'b'?", 'a')

    def test_plus(self):
        g = "grammar = 'a'+"
        self.check(
            g,
            '',
            err='<string>:1 Unexpected end of input at column 1',
        )
        self.check(g, 'a')
        self.check(g, 'aa')

    def test_pred(self):
        # self.check('grammar = ?{true} end { true }', '', out=True)
        self.check('grammar = ?{true} end', '')
        self.check(
            """\
            grammar = ?{false} end
                    | end
            """,
            '',
        )

    def test_pred_bad_value(self):
        self.check(
            'grammar = ?{"foo"} end',
            '',
            err='<string>:1 Bad predicate value',
        )

    def test_range(self):
        grammar = "g = '0'..'9'"
        self.check(grammar, '5')
        self.check(grammar, 'a', err='<string>:1 Unexpected "a" at column 1')

    def test_regexp(self):
        self.check('g = /.+/', 'abc')

    def test_rule_with_lit_str(self):
        self.check(
            """\
            grammar = foo*
            foo     = 'foo'
            """,
            'foofoo',
        )

    def test_run(self):
        self.check("g = <'a' 'b' 'c'>", 'abc')
        self.check(
            "g = <'a' 'b' 'c'>",
            'd',
            err='<string>:1 Unexpected "d" at column 1',
        )

    def test_seq(self):
        self.check("grammar = 'foo' 'bar'", 'foobar')

    def test_set(self):
        g = 'g = [xa-e]'
        self.check(g, 'x')
        self.check(g, 'a')
        self.check(g, 'b')
        self.check(g, 'e')
        self.check(g, '', err='<string>:1 Unexpected end of input at column 1')
        self.check(g, 'f', err='<string>:1 Unexpected "f" at column 1')

    def test_set_exclude(self):
        self.check('g = [^ab]', 'c')
        self.check(
            'g = [^a]',
            'a',
            err='<string>:1 Unexpected "a" at column 1',
        )
        self.check(
            'g = [^a]',
            '',
            err='<string>:1 Unexpected end of input at column 1',
        )
        self.check(
            'g = [^]',
            '',
            grammar_err='<string>:1 Unexpected "]" at column 7',
        )
        self.check(
            'g = [^',
            '',
            grammar_err='<string>:1 Unexpected end of input at column 7',
        )
        self.check('g = [^\\ta\\n]', 'e')

    def test_set_exclude_esc_char(self):
        self.check(
            'g = [^\\n]',
            '\n',
            err='<string>:1 Unexpected "\\n" at column 1',
        )

    def test_set_escaped_right_bracket(self):
        g = r'g = [xa-e\]]'
        self.check(g, ']')

    def test_set_exclude_escaped_right_bracket(self):
        self.check(
            'g = [^\\]]',
            ']',
            err='<string>:1 Unexpected "]" at column 1',
        )

    def test_star(self):
        self.check("grammar = 'a'*", '')
        self.check("grammar = 'a'*", 'a')
        self.check("grammar = 'a'*", 'aa')

    def test_star_nested(self):
        # This checks to make sure we don't get stuck in an infinite
        # loop where the inner star always succeeds so the outer star
        # keeps looping. The implementation should break out if it
        # doesn't actually consume anything.
        self.check("grammar = ('a'*)* 'b'", 'b')


class ValuesMixin:
    def test_basic(self):
        self.check('grammar = end', '', out=None)

    def test_bind(self):
        self.check("grammar = 'a'*", 'aa', out=['a', 'a'])

    def test_c_style_comment(self):
        self.check('grammar = /* foo */ end', '')

    def test_choice(self):
        self.check("grammar = 'foo' | 'bar'", 'foo', out='foo')

        self.check(
            """\
            grammar = 'foo' -> true
                    | 'bar' -> false
            """,
            'bar',
            out=False,
        )

    def test_choice_with_rewind(self):
        self.check(
            """\
            grammar = 'a' 'b' -> false
                    | 'a' 'c' -> true
            """,
            'ac',
            out=True,
        )

    def test_count(self):
        grammar = "grammar = 'a'{3} 'b'{1,4} end"
        self.check(
            grammar,
            'a',
            err='<string>:1 Unexpected end of input at column 2',
        )
        self.check(
            grammar,
            'aaa',
            err='<string>:1 Unexpected end of input at column 4',
        )
        self.check(grammar, 'aaab', out=None)
        self.check(
            grammar,
            'aaabbbbb',
            err='<string>:1 Unexpected "b" at column 8',
        )

    def test_empty(self):
        self.check('grammar = ', '', out=None, err=None)

    def test_end(self):
        self.check(
            'grammar = end',
            'foo',
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

    def test_escape_unicat(self):
        self.check('grammar = \\p{Nd} -> true', '1', out=True)

    def test_escapes_in_string(self):
        self.check('grammar = "\\n\\"foo" -> true', '\n"foo', out=True)
        self.check("grammar = '\\'foo' -> true", "'foo", out=True)

    def test_inline_seq(self):
        # This checks that we correctly include the builtin `end` rule
        # when it is part of a parenthesized choice.
        self.check("g = ('foo'|end) -> true", '', out=True)

    def test_inline_parens(self):
        # This is a regression test for a subtle bug found when working
        # on the inlining code in the generator; the method for the second
        # choice was overwriting the method for the first choice.
        self.check(
            """
            g  = (sp '*') | (sp '+')
            sp = ' '
            """,
            ' *',
            out='*',
        )

    def test_label(self):
        self.check("grammar = 'foobar':v -> v", 'foobar', out='foobar')
        self.check("grammar = 'foobar' -> $1", 'foobar', out='foobar')
        self.check(
            "grammar = 'foobar':$1 -> $1",
            'foobar',
            grammar_err=(
                'Errors were found:\n'
                '  "$1" is a reserved variable name '
                'and cannot be explicitly defined\n'
            ),
        )
        self.check(
            "grammar = 'foobar' -> $2",
            'foobar',
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
        self.check(g, 'fooxfoo', out=True)

    def test_label_inner_not_in_outer(self):
        # Named variables defined in an inner sequence should *not* be
        # visible in an outer sequence. This shows that there are different
        # scopes for inner and outer sequences.
        # TODO: Can we provide a better error here?
        self.check(
            "g = 'foo' ('x'+:x) -> cat(x)",
            'fooxxx',
            grammar_err=(
                'Errors were found:\n'
                '  Variable "x" never used\n'
                '  Unknown identifier "x" referenced\n'
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
            'fooxfoo',
            grammar_err=(
                'Errors were found:\n'
                '  Variable "f" never used\n'
                '  Unknown identifier "f" referenced\n'
            ),
        )

    def test_lit_str(self):
        self.check("grammar = ('foo')* -> true", 'foofoo', out=True)

    def test_long_unicode_literals(self):
        self.check("grammar = '\\U00000020' -> true", ' ', out=True)

    def test_not_one(self):
        self.check("grammar = ^'a' 'b'-> true", 'cb', out=True)
        self.check(
            "grammar = ^'a' 'b'-> true",
            'a',
            err='<string>:1 Unexpected "a" at column 1',
        )
        self.check(
            "grammar = ^'a' 'b'-> true",
            '',
            err='<string>:1 Unexpected end of input at column 1',
        )

    def test_not_not(self):
        self.check("grammar = ~~('a') 'a' -> true", 'a', out=True)

    def test_opt(self):
        self.check("grammar = 'a' 'b'? -> true", 'a', out=True)

    def test_paren_in_value(self):
        self.check('grammar = -> (true)', '', out=True)

    def test_plus(self):
        g = "grammar = 'a'+ -> true"
        self.check(
            g,
            '',
            err='<string>:1 Unexpected end of input at column 1',
        )

        self.check(g, 'a', out=True)
        self.check(g, 'aa', out=True)

    def test_pred(self):
        # self.check('grammar = ?{true} end { true }', '', out=True)
        self.check('grammar = ?{true} end -> true', '', out=True)
        self.check(
            """\
            grammar = ?{false} end -> 'a'
                    | end -> 'b'
            """,
            '',
            out='b',
        )

    def test_pred_bad_value(self):
        self.check(
            'grammar = ?{"foo"} end -> false',
            '',
            out=None,
            err='<string>:1 Bad predicate value',
        )

    def test_range(self):
        grammar = "g = '0'..'9':d -> d"
        self.check(grammar, '5', out='5')
        self.check(grammar, 'a', err='<string>:1 Unexpected "a" at column 1')

    def test_regexp(self):
        self.check('g = /.+/', 'abc', out='abc')

    def test_rule_with_lit_str(self):
        self.check(
            """\
            grammar = foo* -> true
            foo     = 'foo'
            """,
            'foofoo',
            out=True,
        )

    def test_run(self):
        self.check("g = <'a' 'b' 'c'> -> true", 'abc', out=True)
        self.check(
            "g = <'a' 'b' 'c'> -> true",
            'd',
            err='<string>:1 Unexpected "d" at column 1',
        )

    def test_seq(self):
        self.check("grammar = 'foo' 'bar' -> true", 'foobar', out=True)

    def test_set(self):
        g = 'g = [xa-e] -> true'
        self.check(g, 'x', out=True)
        self.check(g, 'a', out=True)
        self.check(g, 'b', out=True)
        self.check(g, 'e', out=True)
        self.check(g, '', err='<string>:1 Unexpected end of input at column 1')
        self.check(g, 'f', err='<string>:1 Unexpected "f" at column 1')

    def test_set_exclude(self):
        self.check('g = [^ab] -> true', 'c', out=True)
        self.check(
            'g = [^a] -> true',
            'a',
            err='<string>:1 Unexpected "a" at column 1',
        )
        self.check(
            'g = [^a] -> true',
            '',
            err='<string>:1 Unexpected end of input at column 1',
        )
        self.check(
            'g = [^\\]] -> true',
            ']',
            err='<string>:1 Unexpected "]" at column 1',
        )
        self.check(
            'g = [^] -> true',
            '',
            grammar_err='<string>:1 Unexpected "]" at column 7',
        )
        self.check(
            'g = [^',
            '',
            grammar_err='<string>:1 Unexpected end of input at column 7',
        )
        self.check('g = [^\\ta\\n] -> true', 'e', out=True)

    def test_set_exclude_esc_char(self):
        self.check(
            'g = [^\\n] -> true',
            '\n',
            err='<string>:1 Unexpected "\\n" at column 1',
        )

    def test_set_escaped_right_bracket(self):
        g = r'g = [xa-e\]] -> true'
        self.check(g, ']', out=True)

    def test_star(self):
        self.check("grammar = 'a'* -> true", '', out=True)
        self.check("grammar = 'a'* -> true", 'a', out=True)
        self.check("grammar = 'a'* -> true", 'aa', out=True)

    def test_star_nested(self):
        # This checks to make sure we don't get stuck in an infinite
        # loop where the inner star always succeeds so the outer star
        # keeps looping. The implementation should break out if it
        # doesn't actually consume anything.
        self.check("grammar = ('a'*)* 'b' -> true", 'b', out=True)


class ActionsMixin:
    def test_action(self):
        self.check('grammar = end -> true', '', out=True)

    def test_array(self):
        self.check(
            """\
            grammar = '[' value:v (',' value)*:vs ','? ']' -> concat([v], vs)
            value   = '2':v                                -> atof(v)
            """,
            '[2]',
            out=[2],
        )

    def test_big_int(self):
        self.check(
            # 'grammar = { ftoi("505874924095815700") }',
            'grammar = -> atoi("505874924095815700", 10)',
            '',
            out=505874924095815700,
        )
        self.check(
            # 'grammar = { 505874924095815700 }', '',
            # out=505874924095815700
            'grammar = -> 505874924095815700',
            '',
            out=505874924095815700,
        )

    def test_e_not(self):
        self.check('g = -> !false', '', out=True)
        self.check('g = -> !true', '', out=False)
        self.check('g = (?{true}):x -> !x', '', out=False)

    def test_hex_digits_in_value(self):
        self.check('grammar = -> 0x20', '', out=32)

    def test_hex_digits_invalid(self):
        self.check(
            'grammar = -> 0xtt',
            '',
            grammar_err='<string>:1 Unexpected "t" at column 16',
        )

    def test_ll_arr(self):
        self.check("grammar = -> ['a', 'b']", '', out=['a', 'b'])

    def test_ll_getitem(self):
        self.check("grammar = end -> ['a', 'b'][1]", '', out='b')

    def test_ll_minus(self):
        self.check('grammar = end -> 1 - 4', '', out=-3)

    def test_ll_num(self):
        self.check('grammar = end -> 1', '', out=1)
        self.check('grammar = end -> 0x20', '', out=32)

    def test_ll_plus(self):
        self.check(
            "grammar = 'a':a 'b'*:bs -> a + join('', bs)",
            'abb',
            out='abb',
        )

    def test_quals(self):
        self.check("g = -> utoi(' ')", '', out=32)
        self.check("g = 'x'*:l -> l[0]", 'xx', out='x')
        self.check("g = -> ['a', 'b'][1]", '', out='b')
        self.check("g = -> [['a']][0][0]", '', out='a')


class FunctionsMixin:
    def test_atof(self):
        self.check("g = -> atof('1.3')", '', out=1.3)

    def test_atoi(self):
        self.check("g = -> atoi('0x41', 16)", '', out=65)

    def test_atou(self):
        self.check("g = -> atou('65', 10)", '', out='A')
        self.check("g = -> atou('0x41', 16)", '', out='A')

    def test_cat(self):
        self.check("g = -> cat(['1', '2'])", '', out='12')

    def test_colno(self):
        g = "g = ('a' | '\n')* -> colno()"
        self.check(g, '', out=1)
        self.check(g, 'a', out=2)
        self.check(g, 'aaa', out=4)
        self.check(g, 'aa\n', out=1)
        self.check(g, 'aa\nb', out=1)
        self.check(g, 'aa\nab', out=2)

    def test_concat(self):
        self.check('g = -> concat([1], [2])', '', out=[1, 2])

    def test_cons(self):
        self.check('g = -> cons(1, [2, 3])', '', out=[1, 2, 3])

    def test_dedent(self):
        self.check(
            'g = -> dedent("\n  foo\n    bar\n", -1)',
            '',
            out='foo\n  bar\n',
        )

    def test_dict(self):
        self.check(
            "g = -> dict([['a', 1], ['b', 2]])", '', out={'a': 1, 'b': 2}
        )

    def disabled_test_int(self):
        self.check('g = int(4.0)', '', out=4)

    def test_itou(self):
        self.check('grammar = -> itou(97)', '', out='a')

    def test_join(self):
        self.check("g = -> join('x', ['1', '2', '3'])", '', out='1x2x3')

    def test_scons(self):
        self.check("g = -> scons('a', ['b', 'c'])", '', out=['a', 'b', 'c'])

    def test_strcat(self):
        self.check("g = -> strcat('foo', 'bar')", '', out='foobar')

    def test_utoi(self):
        self.check('grammar = -> utoi("a")', '', out=97)

    def test_xtou(self):
        self.check("g = -> xtou('0x41')", '', out='A')


class CommentsMixin:
    def test_cpp_style(self):
        self.check(
            """\
            grammar = // ignore this line
                      end -> true
            """,
            '',
            out=True,
        )

    def test_cpp_style_eol(self):
        self.check('grammar = //\r\nend -> true', '', out=True)
        self.check('grammar = //\nend -> true', '', out=True)

    def test_tabs_are_whitespace(self):
        self.check("grammar\t=\t'a'\t->\ttrue", 'a', out=True)


class PragmasMixin:
    def test_comment(self):
        grammar = """\
            %tokens = foo
            %comment = '//' (~'\n' any)*
            grammar = (foo ' '* '\n')+  end -> true

            foo     = 'foo'
            """
        self.check(grammar, 'foo\nfoo\n', out=True)

    def test_token(self):
        self.check(
            """\
            %tokens = foo
            grammar = foo -> true
            foo     = bar
            bar     = 'baz'
            """,
            'baz',
            out=True,
        )

    def test_token_is_unknown(self):
        self.check(
            """\
            %tokens = quux
            grammar = foo -> true
            foo     = bar
            bar     = 'baz'
            """,
            'baz',
            grammar_err='Errors were found:\n  Unknown token rule "quux"\n',
        )

    def test_tokens(self):
        grammar = """\
            %tokens = foo bar
            grammar = (foo bar)+ end -> true
            foo     = 'foo'
            bar     = 'bar'
            """
        self.check(grammar, 'foobar', out=True)

    def test_token_is_invalid(self):
        self.check(
            '%tokens = 1234',
            '',
            grammar_err='<string>:1 Unexpected "1" at column 11',
        )

    def test_unknown(self):
        self.check(
            '%foo = end',
            '',
            out=None,
            grammar_err=('Errors were found:\n  Unknown pragma "%foo"\n'),
        )

    def test_whitespace_chars(self):
        # self.check('g = \t\n\r { true }', '', out=True)
        self.check('g = \t\n\r -> true', '', out=True)

    def test_whitespace(self):
        grammar = textwrap.dedent("""\
            %tokens = foo
            %whitespace = ' '

            grammar = foo foo end -> true

            foo     = 'foo'
            """)
        self.check(grammar, 'foofoo', out=True)

    def test_whitespace_can_be_referenced(self):
        grammar = textwrap.dedent("""\
            %whitespace = ' '

            %tokens     = foo

            grammar     = foo  -> true

            foo         = '"' %whitespace '"'
            """)
        self.check(grammar, '" "', out=True)

    def test_externs(self):
        g = """
        %externs = foo -> true
                 | bar -> false

        g = ?{foo} -> 'foo is true'
          | ?{bar} -> 'bar is true'
        """
        self.check(g, '', out='foo is true')


class OperatorsMixin:
    @skip('operators')
    def test_not_quite(self):
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

    @skip('operators')
    def test_indirect(self):
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
    def test_invalid(self):
        # TODO: Provide a better error message, allow rules that expand
        # to literals.
        g = """
           %prec = a
           expr = expr 'b' expr -> [$1, 'b', $3]
                | '0'..'9'
        """
        self.check(
            g,
            '1',
            grammar_err=('Errors were found:\n  Unknown rule "a"\n'),
        )

    @skip('operators')
    def test_basic(self):
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
        self.check(g, '1', out='1')
        self.check(g, '1+2', out=['1', '+', '2'])
        self.check(g, '1+2*3', out=['1', '+', ['2', '*', '3']])
        self.check(g, '1+2-3', out=[['1', '+', '2'], '-', '3'])

        self.check(
            g,
            '1^2^3+4*5/6',
            out=[
                ['1', '^', ['2', '^', '3']],
                '+',
                [['4', '*', '5'], '/', '6'],
            ],
        )

    @skip('operators')
    def test_multichar_is_valid(self):
        # This tests that operators do not have to be just a single character.
        g = """
           %prec = '++'
           expr = expr '++' expr -> [$1, '++', $3]
                | '0'..'9'
        """
        self.check(g, '1++2', out=['1', '++', '2'])

    @skip('operators')
    def test_whitespace(self):
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
        self.check(g, '1', out='1')
        self.check(g, '1 + 2', out=['1', '+', '2'])
        self.check(
            g,
            '1^2^3 + 4 * 5 / 6',
            out=[
                ['1', '^', ['2', '^', '3']],
                '+',
                [['4', '*', '5'], '/', '6'],
            ],
        )


class RecursionMixin:
    @skip('leftrec')
    def test_both(self):
        grammar = """\
            expr = expr:l '+' expr:r -> [l, '+', r]
                 | '0'..'9':d        -> d
            """
        # Note that a grammar that is both left- and right-recursive
        # is left-associative by default.
        self.check(grammar, '1+2+3', [['1', '+', '2'], '+', '3'])

    @skip('leftrec')
    def test_direct_left(self):
        self.check(
            """\
            grammar = grammar:g '+' 'a' -> [g, '+', 'a']
                    | 'a'               -> 'a'
            """,
            'a+a+a',
            [['a', '+', 'a'], '+', 'a'],
        )

    @skip('leftrec')
    def test_without_a_label(self):
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

    def test_direct_right(self):
        self.check(
            """\
            grammar = 'a' '+' grammar:g -> ['a', '+', g]
                    | 'a'               -> 'a'
            """,
            'a+a+a',
            ['a', '+', ['a', '+', 'a']],
        )

    @skip('leftrec')
    def test_indirect_left(self):
        self.check(
            """\
            grammar = b:b '+' 'a'   -> [b, '+', 'a']
                    | 'a'           -> 'a'
            b       = grammar:g     -> g
            """,
            'a+a+a',
            [['a', '+', 'a'], '+', 'a'],
        )

    def test_indirect_right(self):
        self.check(
            """\
            grammar = 'a' '+' b:b   -> ['a', '+', b]
                    | 'a'           -> 'a'
            b       = grammar:g     -> g
            """,
            'a+a+a',
            ['a', '+', ['a', '+', 'a']],
        )

    def test_interior(self):
        self.check(
            """\
            grammar = 'a' grammar:g 'b' -> 'a' + g + 'b'| 'ab' -> 'ab'
            """,
            'aabb',
            'aabb',
        )

    @skip('leftrec')
    def test_left_opt(self):
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
    def test_repeated(self):
        self.check(
            """
            grammar = grammar:x grammar:y 'a' -> [x, y, 'a']
                    | 'a'                     -> 'a'
            """,
            'aaa',
            ['a', 'a', 'a'],
        )


class ErrorsMixin:
    def test_any(self):
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

    def test_second_line_of_grammar(self):
        self.check_grammar_error(
            """\
            grammar = 'foo'
                      4
            """,
            err='<string>:2 Unexpected "4" at column 11',
        )

    def test_unknown_function(self):
        self.check(
            'grammar = -> foo()',
            '',
            grammar_err=(
                'Errors were found:\n'
                '  Unknown function "foo" called\n'
                '  Unknown identifier "foo" referenced\n'
            ),
        )

    def test_unknown_var(self):
        self.check(
            'grammar = -> v',
            '',
            grammar_err=(
                'Errors were found:\n  Unknown identifier "v" referenced\n'
            ),
        )

    def test_unknown_rule(self):
        self.check(
            'grammar = foo',
            '',
            grammar_err=('Errors were found:\n  Unknown rule "foo"\n'),
        )

        # Check that referring to a reserved rule is caught when the rule
        # isn't defined.
        self.check(
            textwrap.dedent("""\
            grammar = _whitespace
            """),
            '',
            grammar_err=('Errors were found:\n  Unknown rule "_whitespace"\n'),
        )

        # Check that referring to a reserved rule is caught when the rule
        # is defined.
        self.check(
            textwrap.dedent("""\
            %whitespace = ' '
            grammar = _whitespace
            """),
            '',
            grammar_err=('Errors were found:\n  Unknown rule "_whitespace"\n'),
        )

    def test_unexpected_thing(self):
        self.check_grammar_error(
            'grammar = 1 2 3', err='<string>:1 Unexpected "1" at column 11'
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


class IntegrationMixin:
    @skip('integration')
    def test_floyd(self):
        contents = self.read_grammar('floyd.g')
        p, err, _ = self.compile(
            contents, 'floyd.g', memoize=True, externs=self.floyd_externs
        )
        self.assertIsNone(err)
        out, err, _ = p.parse(contents, 'floyd.g')
        # We don't check the actual output here because it is too long
        # and we don't want the test to be so sensitive to the AST for
        # the floyd grammar.
        self.assertIsNone(err)
        self.assertEqual(out[0], 'rules')

    @skip('integration')
    def test_floyd_ws(self):
        contents = self.read_grammar('floyd_ws.g')
        p, err, _ = self.compile(
            contents, 'floyd_ws.g', externs=self.floyd_externs
        )
        self.assertIsNone(err)
        out, err, _ = p.parse(contents, 'floyd_ws.g')
        # We don't check the actual output here because it is too long
        # and we don't want the test to be so sensitive to the AST for
        # the floyd grammar.
        self.assertIsNone(err)
        self.assertEqual(out[0], 'rules')

    @skip('integration')
    def test_json(self):
        p, err, _ = self.compile_grammar('json.g')
        self.assertIsNone(err)
        self._common_json_checks(p, {})

        self.checkp(p, '"foo"', out='"foo"', externs={})

        if hasattr(p, 'cleanup'):
            p.cleanup()

    @skip('integration')
    def test_json5(self):
        externs = {'strict': True}
        p, err, _ = self.compile_grammar('json5.g')
        self.assertIsNone(err)
        self._common_json_checks(p, externs=externs)
        self._common_json5_checks(p, externs=externs)

    @skip('integration')
    def test_json5_special_floats(self):
        externs = {'strict': True}
        p, err, _ = self.compile_grammar('json5.g')
        self.assertIsNone(err)

        # TODO: Figure out what to do with 'Infinity' and 'NaN'.
        # self.checkp(p, 'Infinity', out=float('inf'))
        self.checkp(p, 'Infinity', out='Infinity', externs=externs)

        # Can't use check() for this because NaN != NaN.
        # obj, err, _ = p.parse('NaN')
        # self.assertTrue(math.isnan(obj))
        # self.assertTrue(err is None)
        self.checkp(p, 'NaN', out='NaN', externs=externs)

        if hasattr(p, 'cleanup'):
            p.cleanup()

    def _common_json_checks(self, p, externs):
        self.checkp(p, '123', out=123, externs=externs)
        self.checkp(p, '1.5', out=1.5, externs=externs)
        self.checkp(p, '-1.5', out=-1.5, externs=externs)
        self.checkp(p, '1.5e2', out=150, externs=externs)
        self.checkp(p, 'null', out=None, externs=externs)
        self.checkp(p, 'true', out=True, externs=externs)
        self.checkp(p, 'false', out=False, externs=externs)

        self.checkp(p, '[]', out=[], externs=externs)
        self.checkp(p, '[2]', out=[2], externs=externs)
        self.checkp(p, '{}', out={}, externs=externs)

        self.checkp(
            p,
            '[1',
            err='<string>:1 Unexpected end of input at column 3',
            externs=externs,
        )

        # Check that leading whitespace is allowed.
        self.checkp(p, '  {}', {}, externs=externs)

    def _common_json5_checks(self, p, externs):
        self.checkp(p, '+1.5', out=1.5, externs=externs)
        self.checkp(p, '.5e-2', out=0.005, externs=externs)
        self.checkp(p, '"foo"', out='foo', externs=externs)
        self.checkp(
            p,
            '{foo: "bar", a: "b"}',
            out={'foo': 'bar', 'a': 'b'},
            externs=externs,
        )

    @skip('integration')
    def test_json5_sample(self):
        # Check the sample file from pyjson5.
        # this skips the `'to': Infinity` pair because that can't
        # be marshalled in and out of JSON.
        p, err, _ = self.compile_grammar('json5.g')
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
        p, err, _ = self.compile_grammar('json5_ws.g')
        self.assertIsNone(err)
        self._common_json_checks(p, externs=externs)
        self._common_json5_checks(p, externs=externs)
