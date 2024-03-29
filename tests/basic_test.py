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
import pathlib
import textwrap
import unittest

import floyd


THIS_DIR = pathlib.Path(__file__).parent


class BasicTest(unittest.TestCase):
    maxDiff = None

    def test_json5_grammar(self):
        host = floyd.host.Host()
        json5_grammar_path = str(THIS_DIR.parent / 'grammars' / 'json5.g')
        host.stdin = io.StringIO()
        host.stdin.write('{foo: "bar"}')
        host.stdin.seek(0)
        host.stdout = io.StringIO()
        ret = floyd.tool.main([json5_grammar_path], host)
        self.assertEqual(ret, 0)
        self.assertEqual(
            host.stdout.getvalue(),
            textwrap.dedent('''\
                [
                  "object",
                  [
                    [
                      "foo",
                      [
                        "string",
                        "bar"
                      ]
                    ]
                  ]
                ]'''))
