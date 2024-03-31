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

import math
import pathlib
import textwrap
import unittest
import json

import floyd
import floyd.host


THIS_DIR = pathlib.Path(__file__).parent


class GrammarTest(unittest.TestCase):
    maxDiff = None

    def check(self, host, grammar, text, output=None, error=None):
        if host.exists(THIS_DIR / text):
            text = host.read_text_file(THIS_DIR / text)
        if output:
            if host.exists(THIS_DIR / output):
                output = host.read_text_file(THIS_DIR / output)
            expected_obj = json.loads(output)

        actual_obj, actual_err = grammar.parse(text)
        if output:
            self.assertEqual(expected_obj, actual_obj)
        if error:
            self.assertEqual(error, actual_err)
        return actual_obj, actual_err

    def test_floyd(self):
        h = floyd.host.Host()
        # We compile the parser outside of check so that we can reuse it
        # for multiple tests.
        g, _ = floyd.compile_parser(
            h.read_text_file(THIS_DIR / '../grammars/floyd.g'),
            path=str(THIS_DIR / '../grammars/floyd.g'),
        )

        out, err = self.check(h, g, '../grammars/floyd.g')
        # We don't check the actual output here because it is too long
        # and we don't want the test to be so sensitive to the AST for
        # the floyd grammar. 
        self.assertEqual(out[0][:2], ['rule', 'grammar'])
        self.assertIsNone(err)

    def test_json5(self):
        h = floyd.host.Host()
        # We compile the parser outside of check so that we can reuse it
        # for multiple tests.
        g, _ = floyd.compile_parser(
            h.read_text_file(THIS_DIR / '../grammars/json5.g'),
            path=str(THIS_DIR / '../grammars/json5.g'),
        )
        self.check(
            h, g, 'grammars/json5_sample.inp', 'grammars/json5_sample.outp'
        )
        self.check(h, g, 'Infinity', 'Infinity')
        self.check(h, g, 'null', 'null')
        self.check(h, g, 'true', 'true')
        self.check(h, g, 'false', 'false')
        self.check(h, g, '{foo: "bar"}', '{"foo": "bar"}')
        self.check(h, g, '[1, 2]', '[1, 2]')

        # can't use check for this because NaN != NaN.
        obj, err = g.parse('NaN')
        self.assertTrue(math.isnan(obj))
        self.assertTrue(err is None)

        self.check(
            h, g, '[1', error='<string>:1 Unexpected end of input at column 3'
        )

    def test_rule_with_lit_str(self):
        p, err = floyd.compile_parser(textwrap.dedent("""\
            grammar = foo* -> true
            foo     = 'foo'
            """))
        out, err = p.parse('foofoo')
        self.assertEqual(out, True)
        self.assertIsNone(err)
        
    def test_lit_str(self):
        p, err = floyd.compile_parser(textwrap.dedent("""\
            grammar = ('foo')* -> true
            """))
        out, err = p.parse('foofoo')
        self.assertEqual(out, True)
        self.assertIsNone(err)
        
