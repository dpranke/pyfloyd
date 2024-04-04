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
        parser, err, _ = floyd.compile_parser('grammar = "foo" "bar"')
        self.assertIsNone(err)

        val, err, _ = parser.parse('baz')
        self.assertIsNone(val)
        self.assertEqual(err, '<string>:1 Unexpected "b" at column 1')

    def test_compile_bad_grammar(self):
        parser, err, _ = floyd.compile_parser('xyz')
        self.assertIsNone(parser)
        self.assertEqual(err, '<string>:1 Unexpected end of input at column 4')

    def test_generate_parser(self):
        txt, err, _ = floyd.generate_parser('grammar = "Hello" end -> true')
        self.assertIsNone(err)
        scope = {}
        exec(txt, scope)
        parser_cls = scope['Parser']
        obj, err, _ = parser_cls('Hello', '<string>').parse()
        self.assertIsNone(err)
        self.assertEqual(obj, True)

    def test_generate_parser_fails(self):
        txt, err, _ = floyd.generate_parser('xyz')
        self.assertIsNone(txt)
        self.assertEqual(err, '<string>:1 Unexpected end of input at column 4')

    def test_parse(self):
        obj, err, _ = floyd.parse(
            'grammar = "Hello, world" end', 'Hello, world'
        )
        self.assertEqual(obj, None)
        self.assertEqual(err, None)

    def test_parse_grammar_err(self):
        obj, err, _ = floyd.parse('grammar', '')
        self.assertEqual(obj, None)
        self.assertEqual(
            err,
            'Error in grammar: <string>:1 Unexpected end of input at column 8',
        )

    def test_pretty_print(self):
        s, err = floyd.pretty_print('grammar = end')
        self.assertIsNone(err)
        self.assertEqual(s, 'grammar = end\n')

    def test_pretty_print_fails(self):
        s, err = floyd.pretty_print('gram')
        self.assertIsNone(s)
        self.assertEqual(err, '<string>:1 Unexpected end of input at column 5')
