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

from floyd.formatter import flatten, Comma, Saw, Tree


class FormatterTests(unittest.TestCase):
    def test_str(self):
        self.assertEqual(['foo'], flatten('foo'))

    def test_comma(self):
        t = Comma(['1', '2', '3'])
        self.assertEqual(['1, 2, 3'], flatten(t))

        t = Comma(['1', Saw('[', Comma(['2']), ']')])
        self.assertEqual(['1, [2]'], flatten(t))

        # This tests an array that needs to span multiple lines.
        t = Comma(
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
                'self._long_rule_1,',
                'self._long_rule_2,',
                'self._long_rule_3,',
                'self._long_rule_4,',
                'self._long_rule_5,',
            ],
            flatten(t),
        )

    def test_comma_repr(self):
        self.assertEqual("Comma(['1', '2'])", repr(Comma(['1', '2'])))
        self.assertEqual(
            "Comma(['1', Saw('[', Comma(['2']), ']')])",
            repr(Comma(['1', Saw('[', Comma(['2']), ']')])),
        )

    def test_line_too_long(self):
        long_str = (
            'this is a string line that stretches out for a'
            'really long time and will not fit on one line'
        )
        self.assertEqual([long_str], flatten(long_str))

    def test_mix(self):
        lines = flatten(
            Saw(
                'self._succeed(',
                Saw(
                    'self.xtou(',
                    Comma(
                        [
                            Tree(
                                "self._get('long_variable_1')",
                                '+',
                                Tree(
                                    "self._get('long_variable_2')",
                                    '+',
                                    "self._get('long_variable_3')",
                                ),
                            )
                        ]
                    ),
                    ')',
                ),
                ')',
            )
        )
        self.assertEqual(
            [
                'self._succeed(',
                '    self.xtou(',
                "        self._get('long_variable_1')",
                "        + self._get('long_variable_2')",
                "        + self._get('long_variable_3'),",
                '    )',
                ')',
            ],
            lines,
        )

    def test_saw(self):
        t = Saw('foo(', "'bar'", ')')
        self.assertEqual(["foo('bar')"], flatten(t))

        t = Saw('foo(', "'bar'", Saw(')(', "'baz'", ')'))
        self.assertEqual(["foo('bar')('baz')"], flatten(t))

        # test that the right length of args can fit on a line by itself.
        t = Saw(
            'foo(',
            Comma(
                [
                    'self._long_rule_1',
                    'self._long_rule_2',
                    'self._long_rule_3',
                    'self._long_',
                ]
            ),
            ')',
        )
        self.assertEqual(
            [
                'foo(',
                '    self._long_rule_1, self._long_rule_2, self._long_rule_3, '
                'self._long_',
                ')',
            ],
            flatten(t),
        )
        t = Saw(
            'foo(',
            Comma(
                [
                    'self._long_rule_1',
                    'self._long_rule_2',
                    'self._long_rule_3',
                    'self._long_rule_4',
                    'self._long_rule_5',
                    'self._long_rule_6',
                ]
            ),
            ')',
        )
        self.assertEqual(
            [
                'foo(',
                '    self._long_rule_1,',
                '    self._long_rule_2,',
                '    self._long_rule_3,',
                '    self._long_rule_4,',
                '    self._long_rule_5,',
                '    self._long_rule_6,',
                ')',
            ],
            flatten(t),
        )

        t2 = Saw(')[', '4', ']')
        t.end = t2
        self.assertEqual(
            [
                'foo(',
                '    self._long_rule_1,',
                '    self._long_rule_2,',
                '    self._long_rule_3,',
                '    self._long_rule_4,',
                '    self._long_rule_5,',
                '    self._long_rule_6,',
                ')[',
                '    4',
                ']',
            ],
            flatten(t),
        )

    def test_tree(self):
        t = Tree('1', '+', '2')
        self.assertEqual(['1 + 2'], flatten(t))
        t = Tree(
            "'long string 1'",
            '+',
            Tree(
                "'long string 2'",
                '+',
                Tree(
                    "'long string 3'",
                    '+',
                    Tree("'long string 4'", '+', "'long string5'"),
                ),
            ),
        )
        self.assertEqual(
            [
                "'long string 1'",
                "+ 'long string 2'",
                "+ 'long string 3'",
                "+ 'long string 4'",
                "+ 'long string5'",
            ],
            flatten(t),
        )

    def test_tree_repr(self):
        self.assertEqual("Tree('1', '+', '2')", repr(Tree('1', '+', '2')))
        self.assertEqual(
            "Tree('1', '+', Tree('2', '+', '3'))",
            repr(Tree('1', '+', Tree('2', '+', '3'))),
        )
