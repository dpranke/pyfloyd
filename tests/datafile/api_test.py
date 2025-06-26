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
import os
import unittest

from pyfloyd import datafile


class Load(unittest.TestCase):
    # pylint: disable=no-member

    def test_custom_array_tag(self):
        def tag_fn(ty, tag, vals):
            self.assertEqual(ty, 'array')
            self.assertEqual(tag, 'c')
            self.assertEqual(vals, [1])
            return [0]
        v = datafile.loads('c[1]', custom_tags={'c': tag_fn})
        self.assertEqual(v, [0])

        # check that it isn't called if there is no tag
        v = datafile.loads('[1]', custom_tags={'c': tag_fn})
        self.assertEqual(v, [1])

        # check that an unknown tag raises an error
        with self.assertRaises(datafile.DatafileError) as cm:
            datafile.loads('c[1]')
        self.assertEqual(str(cm.exception), 'Unsupported array tag "c"')

    def test_custom_object_key_tag(self):
        def tag_fn(ty, tag, val, as_key):
            _, quote, colno, text = val
            self.assertEqual(ty, 'string')
            self.assertEqual(tag, 'c')
            self.assertEqual(as_key, True)
            self.assertEqual(quote, '"')
            self.assertEqual(colno, 4)
            self.assertEqual(text, 'foo')
            return text + '_custom'
        v = datafile.loads('{c"foo": 1}', custom_tags={'c': tag_fn})
        self.assertEqual(v, {'foo_custom': 1})

        # check that it isn't called if there is no tag
        v = datafile.loads('{"foo": 1}', custom_tags={'c': tag_fn})
        self.assertEqual(v, {'foo': 1})

        # check that an unknown tag raises an error
        with self.assertRaises(datafile.DatafileError) as cm:
            datafile.loads('{c"foo": 1}')
        self.assertEqual(str(cm.exception), 'Unsupported string tag "c"')

    def test_custom_object_tag(self):
        def tag_fn(ty, tag, pairs):
            self.assertEqual(ty, 'object')
            self.assertEqual(tag, 'c')
            self.assertEqual(pairs, [('foo', 1)])
            return {'foo_custom': 1}
        v = datafile.loads('c{foo: 1}', custom_tags={'c': tag_fn})
        self.assertEqual(v, {'foo_custom': 1})

        # check that it isn't called if there is no tag
        v = datafile.loads('{foo: 1}', custom_tags={'c': tag_fn})
        self.assertEqual(v, {'foo': 1})

        # check that an unknown tag raises an error
        with self.assertRaises(datafile.DatafileError) as cm:
            datafile.loads('c{foo: 1}')
        self.assertEqual(str(cm.exception), 'Unsupported object tag "c"')

    def test_custom_string_tag(self):
        def tag_fn(ty, tag, val, as_key):
            _, quote, colno, text = val
            self.assertEqual(ty, 'string')
            self.assertEqual(tag, 'c')
            self.assertEqual(as_key, False)
            self.assertEqual(quote, '"')
            self.assertEqual(colno, 3)
            self.assertEqual(text, 'foo')
            return text + '_custom'
        v = datafile.loads('c"foo"', custom_tags={'c': tag_fn})
        self.assertEqual(v, 'foo_custom')

        # check that it isn't called if there is no tag
        v = datafile.loads('"foo"', custom_tags={'c': tag_fn})
        self.assertEqual(v, 'foo')

        # check that an unknown tag raises an error
        with self.assertRaises(datafile.DatafileError) as cm:
            datafile.loads('c"foo"')
        self.assertEqual(str(cm.exception), 'Unsupported string tag "c"')


    def test_load(self):
        fp = io.StringIO('4')
        doc = datafile.load(fp)
        self.assertEqual(doc, 4)

    def test_empty_is_error(self):
        with self.assertRaises(datafile.DatafileError) as cm:
            datafile.loads('')
        self.assertEqual(
            str(cm.exception),
            'Empty strings are not legal datafiles'
        )


class Dump(unittest.TestCase):
    def test_dump(self):
        fp = io.StringIO()
        datafile.dump('foo', fp)
        self.assertEqual(fp.getvalue(), 'foo')
