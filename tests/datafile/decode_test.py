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

import unittest

from pyfloyd import datafile


class Tests(unittest.TestCase):
    def check(self, s, obj, **kwargs):
        self.assertEqual(obj, datafile.loads(s, **kwargs))

    def test_true(self):
        self.check('true', True)

    def test_false(self):
        self.check('false', False)

    def test_null(self):
        self.check('null', None)

    def test_number(self):
        self.check('4', 4)
        self.check('4_1', 41)
        self.check('4.1', 4.1)
        self.check('4e2', 400)
        self.check('4.1e2', 410)
        self.check('0b11', 3)
        self.check('0xa0', 160)
        self.check('0xa0_b0', 41136)
        self.check('0o12', 10)
        self.check('-4', -4)
        self.check('+4', +4)

    def test_array(self):
        self.check('[]', [])
        self.check('  []', [])
        self.check('[1]', [1])
        self.check('[foo]', ['foo'])
        self.check('["foo"]', ['foo'])
        self.check('[1 2]', [1, 2])
        self.check('[1, 2]', [1, 2])
        self.check('[1, 2,]', [1, 2])

    def test_numword(self):
        # Test that numwords are not allowed by default.
        with self.assertRaises(datafile.DatafileError) as cm:
            datafile.loads('4foo')
        self.assertEqual(
            str(cm.exception), '<string>:1 Unexpected "f" at column 2'
        )

        # Test that they do work if you enable them.
        self.check('123foo', '123foo', allow_numwords=True)

    def test_object(self):
        self.check('{}', {})
        self.check('  {}', {})
        self.check('{foo: bar}', {'foo': 'bar'})
        self.check('{foo: "bar"}', {'foo': 'bar'})
        self.check("{foo: 'bar'}", {'foo': 'bar'})
        self.check('{foo: bar baz: quux}', {'foo': 'bar', 'baz': 'quux'})
        self.check('{f: 1, g: 2}', {'f': 1, 'g': 2})
        self.check('{"foo": 1}', {'foo': 1})

    def test_top_level_object(self):
        self.check('foo: bar', {'foo': 'bar'})

    def test_raw_str(self):
        self.check(r'r"foo\x"', r'foo\x')

    def test_i_str(self):
        self.check("i'\n  bar\n    baz'", '  bar\n    baz')
        self.check("i'\n  bar\n    baz\n  '", '  bar\n    baz\n')
        self.check("i'\n  \n    baz\n'", '\n    baz\n')
        self.check("i'\n  bar\n\n    baz\n'", '  bar\n\n    baz\n')
        self.check("i'foo'", 'foo')
        self.check("i'  foo  '", '  foo  ')
        self.check("i'  foo\n'", '  foo\n')
        self.check("i'  foo  \nbar'", '    foo\nbar')

    def test_str_dedented_by_default(self):
        self.check("'\n  bar\n    baz'", 'bar\n  baz')
        self.check("'\n  bar\n    baz\n  '", 'bar\n  baz\n')
        self.check("'\n  \n    baz\n'", '\n  baz\n')
        self.check("'\n  bar\n\n    baz\n'", 'bar\n\n  baz\n')
        self.check("'foo'", 'foo')
        self.check("'  foo  '", '  foo  ')
        self.check("'foo\n  bar'", 'foo\n bar')
        self.check("'  foo  \n  bar'", ' foo\nbar')
        self.check("'foo\n  bar \n    baz'", 'foo\n bar\n   baz')
        self.check("  'foo\n bar'", '  foo\nbar')

    def test_str(self):
        self.check('"foo"', 'foo')
        self.check("'foo'", 'foo')
        self.check('`foo`', 'foo')
        self.check('"""foo"""', 'foo')
        self.check("'''foo'''", 'foo')
        self.check('```foo```', 'foo')

    def test_str_quote_escapes(self):
        self.check('"\\\'\\"\\`"', '\'"`')

    def test_str_oct_escapes(self):
        self.check(r"'\0'", chr(0))
        self.check(r"'\00'", chr(0))
        self.check(r"'\000'", chr(0))
        self.check(r"'\0000'", chr(0) + '0')
        self.check(r"'\12'", chr(10))

    def test_string_list(self):
        self.check('s["foo" bar]', 'foobar')

    def test_long_str(self):
        self.check("L'='foo'='", 'foo')
        self.check("L'=='foo'=='", 'foo')
        self.check("L'=='f'='o'=='", "f'='o")

    def test_bare_word(self):
        self.check('foo', 'foo')
        self.check('@foo', '@foo')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
