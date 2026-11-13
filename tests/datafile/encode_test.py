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

import io
import unittest

from pyfloyd import datafile


class T(unittest.TestCase):
    def check(self, s, obj, **kwargs):
        self.assertEqual(obj, datafile.dumps(s, **kwargs))

    def test_dump(self):
        fp = io.StringIO()
        datafile.dump(True, fp)
        self.assertEqual('true', fp.getvalue())

    def test_true(self):
        self.check(True, 'true')

    def test_false(self):
        self.check(False, 'false')

    def test_null(self):
        self.check(None, 'null')

    def test_number(self):
        self.check(4, '4')
        self.check(4.1, '4.1')
        self.check(-4, '-4')

    def test_array(self):
        self.check([], '[]')
        self.check([1], '[1]')
        self.check(['foo'], '[foo]')
        self.check([1, 2], '[1 2]')

    def test_numword(self):
        self.check('123foo', '123foo', allow_numwords=True)

    def test_object(self):
        self.check({}, '{}')
        self.check({'foo': 'bar'}, '{foo: bar}')
        self.check({'foo': 'bar', 'baz': 'quux'}, '{foo: bar baz: quux}')
        self.check({'f': 1, 'g': 2}, '{f: 1 g: 2}')

    def test_str(self):
        self.check('foo', 'foo')
        self.check('bar\n  baz', "'bar\\n  baz'")

    def test_str_quote_escapes(self):
        self.check('\'"`', "''''\"`'''")

    def test_str_backslash_is_escaped(self):
        # A backslash must be escaped on the way out, or the output
        # re-parses to a different string (e.g., 'a\\b' would come back
        # as 'a\x08b' once \b is interpreted as an escape).
        self.check('a\\b', "'a\\\\b'")
        self.check('\\1', "'\\\\1'")

    def test_barewords_that_reparse_as_other_types_are_quoted(self):
        # The datafile spec only allows a string to be written unquoted if
        # it cannot be interpreted as a boolean, null, or a number.
        self.check('true', "'true'")
        self.check('false', "'false'")
        self.check('null', "'null'")
        self.check('2', "'2'")
        self.check('-3', "'-3'")
        self.check('2.5', "'2.5'")
        self.check('2.5e', "'2.5e'")
        # A numword stays unquoted when numwords are allowed ...
        self.check('123foo', '123foo', allow_numwords=True)
        # ... but is quoted otherwise, so that it still parses back to the
        # same string.
        self.check('123foo', "'123foo'")

    def test_barewords_with_punctuation_are_quoted(self):
        # ',' separates values, '#' starts a comment, and '/', '=', quotes,
        # brackets and so on are punctuation per the grammar's `punct` rule,
        # so words containing them cannot be written unquoted.
        self.check('1,2', "'1,2'")
        self.check('#c', "'#c'")
        self.check('a=b', "'a=b'")
        self.check('a/b', "'a/b'")
        self.check('a b', "'a b'")

    def test_keys_that_are_not_barewords_are_quoted(self):
        self.check({' b': 1}, "{' b': 1}")
        self.check({'a b': 1}, "{'a b': 1}")
        self.check({'"q"': 1}, "{'\"q\"': 1}")
        self.check({'1': 1}, "{'1': 1}")
        self.check({'': 1}, "{'': 1}")
        self.check({'true': 1}, "{'true': 1}")
        self.check({'#c': 1}, "{'#c': 1}")

    def test_roundtrip(self):
        # Anything dumps() emits should load back to the same object.
        objs = [
            'foo', 'true', 'false', 'null', '2', '2.5', '-3', '2.5e',
            '1,2', '#c', 'a b', ' b', 'v ', 'a=b', 'a/b', 'a\\b', '\\1',
            'a"b', "'x'", '+', '-abc', '.5', '1abc',
            {' b': 1}, {'a b': 1}, {'"q"': 1}, {'a"b': 1}, {'1': 1},
            {'': 1}, {'true': 1}, {'null': 1}, {'#c': 1}, {'1,2': 1},
            {'a=b': 1}, {'a/b': 1}, {'a\\b': 1},
            {'k': ['true', '2', 'a\\b']},
            [{' b': 1}, {"'q'": [1, 'null']}],
        ]
        for obj in objs:
            s = datafile.dumps(obj)
            self.assertEqual(obj, datafile.loads(s), msg=f'{obj!r} -> {s!r}')

        for obj in ('123foo', '2.5ex'):
            s = datafile.dumps(obj, allow_numwords=True)
            self.assertEqual(
                obj, datafile.loads(s, allow_numwords=True), msg=s
            )

    def test_invalid_key_error_message(self):
        with self.assertRaises(TypeError) as cm:
            datafile.dumps({(1, 2): 3})
        self.assertEqual(str(cm.exception), 'Invalid key: (1, 2)')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
