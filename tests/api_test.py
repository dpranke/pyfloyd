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

import floyd


class APITest(unittest.TestCase):
    maxDiff = None

    def test_compile(self):
        parser, err = floyd.compile_parser('grammar = "foo" "bar"')
        self.assertEqual(err, None)

        val, err = parser.parse('baz')
        self.assertEqual(val, None)
        self.assertEqual(err, '<string>:1 Unexpected "b" at column 1')

    def test_compile_bad_grammar(self):
        parser, err = floyd.compile_parser('xyz')
        self.assertEqual(parser, None)
        self.assertEqual(err, '<string>:1 Unexpected end of input at column 4')

    def test_parse(self):
        obj, err = floyd.parse('grammar = "Hello, world" end', 'Hello, world')
        self.assertEqual(obj, None)
        self.assertEqual(err, None)

    def test_parse_grammar_err(self):
        obj, err = floyd.parse('grammar =', '')
        self.assertEqual(obj, None)
        self.assertEqual(err, 'Error compiling grammar.')

    def test_pretty_print(self):
        s, err = floyd.pretty_print('grammar = end')
        self.assertIsNone(err)
        self.assertEqual(s, 'grammar = end\n')

    def test_pretty_print_fails(self):
        s, err = floyd.pretty_print('gram')
        self.assertIsNone(s)
        self.assertEqual(err, '<string>:1 Unexpected end of input at column 5')
