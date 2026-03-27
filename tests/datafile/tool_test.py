# Copyright 2017 Google Inc. All rights reserved.
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

import os

from pyfloyd import support, __version__
from pyfloyd.datafile import tool


class _Tests:
    # pylint: disable=no-member

    def test_help(self):
        self.check(['--help'])

        # Run again and ignore the error code just to get coverage of
        # the test code branches in check().
        self.check(['--help'], returncode=None)

    def test_inline_expression(self):
        self.check(['-c', '{foo: 1}'], out='{\n    foo: 1\n}\n')

    def test_indent(self):
        self.check(['--indent=None', '-c', '[1]'], out='[1]\n')
        self.check(['--indent=2', '-c', '[1]'], out='[1]\n')
        self.check(['--indent=  ', '-c', '[1]'], out='[1]\n')

    def test_as_json(self):
        self.check(
            ['--as-json', '-c', '{foo: 1}'],
            out='{\n    "foo": 1\n}\n',
        )

    def test_error(self):
        self.check(
            ['-c', '[x'],
            returncode=1,
            out='-:1 Unexpected end of input at column 3\n',
        )

    def test_read_command(self):
        self.check(['-c', '"foo"'], out='foo\n')

    def test_read_from_stdin(self):
        self.check([], stdin='"foo"\n', out='foo\n')

    def test_read_from_a_file(self):
        files = {
            'foo.fdf': '"foo"\n',
        }
        self.check(['foo.fdf'], files=files, out='foo\n')

    def test_unknown_switch(self):
        self.check(
            ['--unknown-switch'],
            returncode=2,
            err=(
                'usage: fld [-h] [-V] [-c STR] [--as-json] [--indent INDENT]'
                ' [FILE]\n'
                'error: unrecognized arguments: --unknown-switch\n'
            ),
        )

    def test_version(self):
        self.check(['--version'], out=str(__version__) + '\n')


class Inline(support.InlineTestCase, _Tests):
    main = tool.main


class Module(support.ModuleTestCase, _Tests):
    module = 'pyfloyd.datafile'


class Script(support.ScriptTestCase, _Tests):
    script = 'fld'


class Tool(support.ScriptTestCase, _Tests):
    script = os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        'src',
        'pyfloyd',
        'datafile',
        'tool.py',
    )
    outside_venv = True
