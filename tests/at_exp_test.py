# Copyright 2025 Dirk Pranke. All rights reserved.
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

from pyfloyd import at_exp
from pyfloyd import lisp_interpreter
from pyfloyd.formatter import (
    flatten_as_lisplist,
)


class Tests(unittest.TestCase):
    def check_lines(self, s, expected_lines, indent='    '):
        interp = lisp_interpreter.Interpreter()
        at_exp.bind_at_exps(interp, '  ', use_format_objs=True)
        actual_obj = interp.eval([['symbol', 'at_exp'], s])
        actual_lines = flatten_as_lisplist(actual_obj, indent=indent)
        self.assertEqual(expected_lines, actual_lines)

    def check(self, s, expected):
        interp = lisp_interpreter.Interpreter()
        at_exp.bind_at_exps(interp, '  ', use_format_objs=False)
        got = interp.eval([['symbol', 'at_exp'], s])
        self.assertEqual(expected, got)

    def test_basic(self):
        self.check('foo', ['foo'])
        self.check('@list[]', [[]])
        self.check('@list{foo}', [['foo']])
        self.check('@list{foo @list{bar} baz}', [['foo ', ['bar'], ' baz']])

    def test_comment(self):
        self.check('@;foo', [])

    def test_lines(self):
        self.check_lines('hello world', ["[vl 'hello world']"])
        self.check_lines('@strcat["foo" "bar"]', ["[vl 'foobar']"])
