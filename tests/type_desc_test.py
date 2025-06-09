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

from pyfloyd import type_desc

TD = type_desc.TypeDesc


class Tests(unittest.TestCase):
    def check(self, s, td):
        got_td = TD.from_str(s)
        self.assertEqual(td, got_td)
        self.assertEqual(got_td.to_str(), s)

    def test_basic_types(self):
        self.check('any', TD('any'))
        self.check('bool', TD('bool'))
        self.check('float', TD('float'))
        self.check('int', TD('int'))
        self.check('null', TD('null'))

    def test_dict(self):
        self.check('dict[str, any]', TD('dict', [TD('str'), TD('any')]))

    def test_list(self):
        self.check('list[str]', TD('list[str]'))
        self.check('list[str]', TD('list', [TD('str')]))

    def test_tuple(self):
        self.check('tuple[str, any]', TD('tuple', [TD('str'), TD('any')]))

    def test_bad_type_desc(self):
        self.assertRaises(ValueError, TD.from_str, 'foo')
        self.assertRaises(ValueError, TD.from_str, 'list[')
        self.assertRaises(ValueError, TD.from_str, 'list[]')
        self.assertRaises(ValueError, TD.from_str, 'list[]foo')
        self.assertRaises(ValueError, TD.from_str, 'list[]]')
        self.assertRaises(ValueError, TD.from_str, 'list[str]foo')
        self.assertRaises(ValueError, TD.from_str, 'list[str, any]')
        self.assertRaises(ValueError, TD.from_str, 'dict[]')
        self.assertRaises(ValueError, TD.from_str, 'dict[str]')

    def test_to_dict(self):
        self.assertEqual({'base': 'str', 'elements': []}, TD('str').to_dict())
        self.assertEqual(
            {'base': 'list', 'elements': [{'base': 'str', 'elements': []}]},
            TD('list[str]').to_dict(),
        )

    def test_d2str(self):
        self.assertEqual(
            'str', type_desc.d2str({'base': 'str', 'elements': []})
        )

        self.assertEqual(
            'list[str]',
            type_desc.d2str(
                {'base': 'list', 'elements': [{'base': 'str', 'elements': []}]}
            ),
        )
