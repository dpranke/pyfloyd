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

import shutil
import unittest

from . import grammar_test


class Tests(
    unittest.TestCase,
    grammar_test.GeneratorMixin,
    grammar_test.GrammarTestsMixin,
):
    cmd = [shutil.which('node')]
    generator = 'javascript'
    floyd_externs = {'unicode_names': False}

    def test_fn_dedent(self):
        # TODO: `dedent` isn't implemented properly in the hardcoded
        # JS generator yet.
        self.check(
            'g = -> dedent("\n  foo\n     bar\n", -1)',
            text='',
            out='\n  foo\n     bar\n',
        )

    @grammar_test.skip('integration')
    def test_json5_special_floats(self):
        # TODO: `Infinity` and `NaN` are legal Python values and legal
        # JavaScript values, but they are not legal JSON values, and so
        # we can't read them in from output that is JSON.
        pass
