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
        self.check("bar\n  baz", "'bar\\n  baz'")

    def test_str_quote_escapes(self):
        self.check('\'"`', "''''\"`'''")


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
