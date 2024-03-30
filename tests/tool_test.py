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

import subprocess
import sys
import unittest

import floyd
import floyd.tool

from .host_fake import FakeHost


class ToolTest(unittest.TestCase):
    maxDiff = None

    def test_compile(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'grammar = "Hello" end -> true')
        ret = floyd.tool.main(['-c', 'grammar.g'], host=host)
        self.assertEqual(ret, 0)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(host.stderr.getvalue(), '')
        parser = host.files['grammar.py']
        scope = {}
        exec(parser, scope)
        parser_cls = scope['Parser']
        obj, err, endpos = parser_cls('Hello', 'grammar.g').parse()
        self.assertEqual(obj, True)
        self.assertIsNone(err)
        self.assertEqual(endpos, 5)

    def test_compile_error(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'xyz')
        ret = floyd.tool.main(['-c', 'grammar.g'], host=host)
        self.assertEqual(ret, 1)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(
            host.stderr.getvalue(), 
            'grammar.g:1 Unexpected end of input at column 4\n')

    def test_help(self):
        proc = subprocess.run(
            [sys.executable, '-m', 'floyd', '--version'],
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertNotEqual(proc.stdout, '')

    def test_usage(self):
        host = FakeHost()
        # This should fail because we're not specifying a grammar.
        self.assertEqual(floyd.tool.main([], host=host), 2)

    def test_version(self):
        host = FakeHost()
        self.assertEqual(floyd.tool.main(['--version'], host=host), 0)
        self.assertEqual(host.stdout.getvalue(), floyd.__version__ + '\n')

    def test_interpret(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'grammar = "Hello" end -> true')
        host.stdin.write('Hello')
        host.stdin.seek(0)
        ret = floyd.tool.main(['-i', '-', 'grammar.g'], host=host)
        self.assertEqual(ret, 0)
        self.assertEqual(host.stderr.getvalue(), '')
        self.assertEqual(host.stdout.getvalue(), 'true\n')

    def test_interpret_error(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'xyz')
        ret = floyd.tool.main(['-p', 'grammar.g'], host=host)
        self.assertEqual(ret, 1)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(
            host.stderr.getvalue(), 
            'grammar.g:1 Unexpected end of input at column 4\n')

    def test_pretty_print(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'grammar = "Hello"    end -> true')
        ret = floyd.tool.main(['-p', 'grammar.g'], host=host)
        self.assertEqual(ret, 0)
        self.assertEqual(host.stdout.getvalue(),
                         "grammar = 'Hello' end -> true\n")

    def test_pretty_print_error(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'xyz')
        ret = floyd.tool.main(['-p', 'grammar.g'], host=host)
        self.assertEqual(ret, 1)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(
            host.stderr.getvalue(), 
            'grammar.g:1 Unexpected end of input at column 4\n')
