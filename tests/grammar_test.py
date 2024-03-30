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

import io
import math
import pathlib
import textwrap
import unittest
import json

import floyd


THIS_DIR = pathlib.Path(__file__).parent


class GrammarTest(unittest.TestCase):
    maxDiff = None

    def check(self, grammar, input, output=None, error=None):
        assert output or error

        host = floyd.host.Host()
        if host.exists(THIS_DIR / input):
            input = host.read_text_file(THIS_DIR / input)
        if output:
            if host.exists(THIS_DIR / output):
                output = host.read_text_file(THIS_DIR / output)
            expected_obj = json.loads(output)

        actual_obj, actual_err = grammar.parse(input)
        if error:
            self.assertEqual(error, actual_err)
        else:
            self.assertEqual(expected_obj, actual_obj)

    def test_json5(self):
        h = floyd.host.Host()
        g = floyd.compile(
            h.read_text_file(THIS_DIR / '../grammars/json5.g'),
            path=str(THIS_DIR / '../grammars/json5.g'),
        )
        self.check(
            g, 'grammars/json5_sample.inp', 'grammars/json5_sample.outp'
        )
        self.check(g, 'Infinity', 'Infinity')
        self.check(g, 'null', 'null')
        self.check(g, 'true', 'true')
        self.check(g, 'false', 'false')
        self.check(g, '{foo: "bar"}', '{"foo": "bar"}')
        self.check(g, '[1, 2]', '[1, 2]')

        # can't use check for this because NaN != NaN.
        obj, err = g.parse('NaN')
        self.assertTrue(math.isnan(obj))
        self.assertTrue(err is None)

        self.check(
            g, '[1', error='<string>:1 Unexpected end of input at column 3'
        )
