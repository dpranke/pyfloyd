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

import pyfloyd
from pyfloyd.support import FakeHost, Host
import pyfloyd.tool



class ToolTest(unittest.TestCase):
    maxDiff = None

    def test_compile(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'grammar = "Hello" end -> true')
        ret = pyfloyd.tool.main(['-c', 'grammar.g'], host=host)
        self.assertEqual(ret, 0)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(host.stderr.getvalue(), '')
        parser = host.files['grammar.py']
        scope = {}
        exec(parser, scope)
        parse_fn = scope['parse']
        result = parse_fn('Hello', 'grammar.g')
        self.assertEqual(result.val, True)
        self.assertIsNone(result.err)
        self.assertEqual(result.pos, 5)

    def test_compile_error(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'xyz')
        ret = pyfloyd.tool.main(['-c', 'grammar.g'], host=host)
        self.assertEqual(ret, 1)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(
            host.stderr.getvalue(),
            'grammar.g:1 Unexpected end of input at column 4\n',
        )

    def test_help(self):
        proc = subprocess.run(
            [sys.executable, '-m', 'pyfloyd', '--version'],
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertNotEqual(proc.stdout, '')

    def test_integration(self):
        # This does a full end-to-end test with pyfloyd writing the
        # compiled parser to the filesystem, loading the file from
        # filesystem, and using it to parse something.
        host = Host()
        d = host.mkdtemp()
        try:
            path = d + '/grammar.g'
            host.write_text_file(path, "grammar = 'foo'* -> true\n")
            ret = pyfloyd.tool.main(['-c', path], host)
            f = host.read_text_file(d + '/grammar.py')
            scope = {}
            exec(f, scope)
            parse_fn = scope['parse']
            result = parse_fn('foofoo', '<string>')
            self.assertEqual(ret, 0)
            self.assertEqual(result.val, True)
            self.assertIsNone(result.err)
            self.assertEqual(result.pos, 6)
        finally:
            host.rmtree(d)

    def test_integration_main(self):
        # This does a full end-to-end test with pyfloyd writing the
        # compiled parser to the filesystem, loading the file from
        # filesystem, and using it to parse something.
        host = Host()
        d = host.mkdtemp()
        try:
            path = d + '/grammar.g'
            host.write_text_file(path, "grammar = 'foo'* -> true\n")

            # This specifies a filename for `-o`; the other integration
            # test takes the default filename to cover both code paths.
            pyfloyd.tool.main(['-c', '--main', '-o', d + '/foo.py', path])

            host.write_text_file(d + '/foo.inp', 'foofoo')
            proc = subprocess.run(
                [sys.executable, d + '/foo.py', d + '/foo.inp'],
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout, 'true\n')
        finally:
            host.rmtree(d)

    def test_integration_memoizing_javascript(self):
        # This does a full end-to-end test with pyfloyd writing the
        # compiled parser to the filesystem, loading the file from
        # filesystem, and using it to parse something.
        host = Host()
        d = host.mkdtemp()
        try:
            path = d + '/grammar.g'
            host.write_text_file(path, "grammar = 'foo'* -> true\n")

            # This intentionally generates a JS file w/o a `main()` to
            # get coverage of the code path where the generated file
            # doesn't have a main. It also omits the `-o` flag
            # to get coverage of the code path where we use the default
            # output path and extension.
            pyfloyd.tool.main(
                ['-c', '--memoize', '--language=javascript', path]
            )

            host.write_text_file(d + '/foo.inp', 'foofoo')

            # This runs the file but doesn't do much of anything, because
            # the JS file doesn't have a `main()`. It at least ensures that
            # the file can be parsed, though.
            proc = subprocess.run(
                ['node', d + '/grammar.js', d + '/foo.inp'],
                capture_output=True,
                check=False,
                text=True,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout, '')
            self.assertEqual(proc.stderr, '')
        finally:
            host.rmtree(d)

    def test_interpret_file(self):
        host = FakeHost()
        host.files['grammar.g'] = 'grammar = "Hello" end -> true'
        host.files['input.txt'] = 'Hello'
        self.assertEqual(
            pyfloyd.tool.main(['grammar.g', 'input.txt'], host), 0
        )
        self.assertEqual(host.stdout.getvalue(), 'true\n')
        self.assertEqual(host.stderr.getvalue(), '')

    def test_interpret(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'grammar = "Hello" end -> true')
        host.stdin.write('Hello')
        host.stdin.seek(0)
        ret = pyfloyd.tool.main(['grammar.g'], host=host)
        self.assertEqual(ret, 0)
        self.assertEqual(host.stderr.getvalue(), '')
        self.assertEqual(host.stdout.getvalue(), 'true\n')

    def test_interpret_grammar_error(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'xyz')
        ret = pyfloyd.tool.main(['grammar.g'], host=host)
        self.assertEqual(ret, 1)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(
            host.stderr.getvalue(),
            'Error in grammar: grammar.g:1 Unexpected end of '
            'input at column 4\n',
        )

    def test_interpret_input_error(self):
        host = FakeHost()
        host.files['grammar.g'] = 'grammar = "Hello" end -> true'
        host.stdin.write('Hell')
        host.stdin.seek(0)
        self.assertEqual(pyfloyd.tool.main(['grammar.g'], host), 1)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(
            host.stderr.getvalue(),
            '<stdin>:1 Unexpected end of input at column 5\n',
        )

    def test_keyboard_interrupt(self):
        host = FakeHost()
        host.files['grammar.g'] = ''

        def _error_on_read(path):
            raise KeyboardInterrupt

        host.read_text_file = _error_on_read
        self.assertEqual(pyfloyd.tool.main(['grammar.g'], host), 130)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(host.stderr.getvalue(), 'Interrupted, exiting.\n')

    def test_main(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'grammar = "Hello" end -> true')
        ret = pyfloyd.tool.main(['-c', '--main', 'grammar.g'], host=host)
        self.assertEqual(ret, 0)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(host.stderr.getvalue(), '')
        parser = host.files['grammar.py']
        scope = {}
        exec(parser, scope)
        main_fn = scope['main']
        self.assertIsNotNone(main_fn)

    def test_memoize(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'grammar = "Hello" end -> true')
        ret = pyfloyd.tool.main(['-c', '--memoize', 'grammar.g'], host=host)
        self.assertEqual(ret, 0)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(host.stderr.getvalue(), '')
        parser = host.files['grammar.py']
        scope = {}
        exec(parser, scope)
        parse_fn = scope['parse']
        result = parse_fn('Hello', 'grammar.g')
        self.assertEqual(result.val, True)
        self.assertIsNone(result.err)
        self.assertEqual(result.pos, 5)

    def test_missing_grammar(self):
        host = FakeHost()
        self.assertEqual(pyfloyd.tool.main(['grammar.g'], host), 1)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(
            host.stderr.getvalue(), 'Error: no such file: "grammar.g"\n'
        )

    def test_read_error(self):
        host = FakeHost()
        host.files['grammar.g'] = ''

        def _error_on_read(path):
            raise IOError('read error')

        host.read_text_file = _error_on_read
        self.assertEqual(pyfloyd.tool.main(['grammar.g'], host), 1)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(
            host.stderr.getvalue(), 'Error reading "grammar.g": read error\n'
        )

    def test_pretty_print(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'grammar = "Hello"    end -> true')
        ret = pyfloyd.tool.main(['-p', 'grammar.g'], host=host)
        self.assertEqual(ret, 0)
        self.assertEqual(
            host.stdout.getvalue(), "grammar = 'Hello' end -> true\n"
        )

    def test_pretty_print_error(self):
        host = FakeHost()
        host.write_text_file('grammar.g', 'xyz')
        ret = pyfloyd.tool.main(['-p', 'grammar.g'], host=host)
        self.assertEqual(ret, 1)
        self.assertEqual(host.stdout.getvalue(), '')
        self.assertEqual(
            host.stderr.getvalue(),
            'grammar.g:1 Unexpected end of input at column 4\n',
        )

    def test_usage(self):
        host = FakeHost()
        # This should fail because we're not specifying a grammar.
        self.assertEqual(pyfloyd.tool.main([], host=host), 2)

    def test_version(self):
        host = FakeHost()
        self.assertEqual(pyfloyd.tool.main(['--version'], host=host), 0)
        self.assertEqual(host.stdout.getvalue(), pyfloyd.__version__ + '\n')
