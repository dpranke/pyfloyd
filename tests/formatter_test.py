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

import unittest

from floyd.formatter import flatten, CommaList, Tree


class FormatterTests(unittest.TestCase):
    def test_str(self):
        self.assertEqual(['foo'], flatten(['foo']))

    def test_commalist(self):
        t = CommaList(['1', '2', '3'])
        self.assertEqual(['foo(1, 2, 3)'], flatten(['foo(', t, ')']))

        t = CommaList(
            [
                "'long string 1'",
                "'long string 2'",
                "'long string 3'",
                "'long string 4'",
            ]
        )
        self.assertEqual(
            [
                'self._succeed(',
                "    ['long string 1', 'long string 2', "
                "'long string 3', 'long string 4']",
             ')'
            ],
            flatten(['self._succeed(', ['[', t, ']'], ')'])
        )

        t = CommaList(
            [
                'self._long_rule_1',
                'self._long_rule_2',
                'self._long_rule_3',
                'self._long_rule_4',
                'self._long_rule_5',
            ]
        )
        self.assertEqual(
            [
                'foo(',
                '    self._long_rule_1,',
                '    self._long_rule_2,',
                '    self._long_rule_3,',
                '    self._long_rule_4,',
                '    self._long_rule_5,',
                ')',
            ],
            flatten(['foo(', t, ')'])
        ) 

    def test_commalist_repr(self):
        self.assertEqual('CommaList(1, 2)',
                         repr(CommaList(['1', '2'])))

    def test_line_too_long(self):
        long_str = (
            'this is a string line that stretches out for a'
            'really long time and will not fit on one line'
        )
        self.assertEqual([long_str], flatten([long_str]))

    def test_tree(self):
        t = Tree(['1'], '+', ['2'])
        self.assertEqual(['foo(1 + 2)'], flatten(['foo(', t, ')']))
        t = Tree(
            ["'long string 1'"], 
            '+',
            Tree(
                ["'long string 2'"],
                '+',
                Tree(
                    ["'long string 3'"],
                    '+',
                    Tree(
                        ["'long string 4'"], '+', ["'long string5'"]
                    )
                )
            )
        )
        self.assertEqual(
            [
                'foo(',
                "    'long string 1'",
                "    + 'long string 2'",
                "    + 'long string 3'",
                "    + 'long string 4'",
                "    + 'long string5'",
                ')'
            ],
            flatten(['foo(', t, ')'])
        )

    def test_tree_repr(self):
        self.assertEqual('Tree(1 + 2)',
                         repr(Tree(['1'], '+', ['2'])))

