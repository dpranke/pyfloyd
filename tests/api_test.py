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

import pyfloyd


class APITest(unittest.TestCase):
    maxDiff = None

    def test_compile(self):
        parser, err, _ = pyfloyd.compile('grammar = "foo" "bar"')
        self.assertIsNone(err)

        val, err, _ = parser.parse('baz')
        self.assertIsNone(val)
        self.assertEqual(err, '<string>:1 Unexpected "b" at column 1')

    def test_compile_bad_grammar(self):
        parser, err, _ = pyfloyd.compile('xyz')
        self.assertIsNone(parser)
        self.assertEqual(err, '<string>:1 Unexpected end of input at column 4')

    def test_generate(self):
        txt, err, _ = pyfloyd.generate('grammar = "Hello" end -> true')
        self.assertIsNone(err)
        scope = {}
        exec(txt, scope)
        parse_fn = scope['parse']
        result = parse_fn('Hello', '<string>')
        self.assertIsNone(result.err)
        self.assertEqual(result.val, True)

    def test_generate_fails(self):
        txt, err, _ = pyfloyd.generate('xyz')
        self.assertIsNone(txt)
        self.assertEqual(err, '<string>:1 Unexpected end of input at column 4')

    def test_generate_unsupported_language(self):
        txt, err, _ = pyfloyd.generate(
            'g =', options=pyfloyd.GeneratorOptions(language='q')
        )
        self.assertIsNone(txt)
        self.assertEqual(
            err,
            (
                'Unsupported language "q"\n'
                'Only "datafile" and "javascript" and "python" are supported.\n'
            ),
        )

    def test_parse(self):
        result = pyfloyd.parse('grammar = "Hello, world" end', 'Hello, world')
        self.assertEqual(result.val, None)
        self.assertEqual(result.err, None)

    def test_parse_grammar_err(self):
        result = pyfloyd.parse('grammar', '')
        self.assertEqual(result.val, None)
        self.assertEqual(
            result.err,
            'Error in grammar: <string>:1 Unexpected end of input at column 8',
        )

    def test_pretty_print(self):
        s, err = pyfloyd.pretty_print('grammar = end')
        self.assertIsNone(err)
        self.assertEqual(s, 'grammar = end\n')

    def test_pretty_print_fails(self):
        s, err = pyfloyd.pretty_print('gram')
        self.assertIsNone(s)
        self.assertEqual(err, '<string>:1 Unexpected end of input at column 5')
