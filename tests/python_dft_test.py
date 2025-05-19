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

import sys
import unittest

from . import grammar_test

skip = grammar_test.skip


class Tests(
    unittest.TestCase,
    grammar_test.GeneratorMixin,
    grammar_test.GrammarTestsMixin,
):
    maxDiff = None
    cmd = [sys.executable]
    language = 'datafile'
    ext = '.py'

    def test_quals(self):
        pass

    @skip('integration')
    def test_floyd(self):
        pass

    @skip('integration')
    def test_floyd_ws(self):
        pass

    @skip('integration')
    def test_json(self):
        pass

    @skip('integration')
    def test_json5(self):
        pass

    @skip('integration')
    def test_json5_special_floats(self):
        pass

    @skip('integration')
    def test_json5_sample(self):
        pass

    @skip('integration')
    def test_json5_ws(self):
        pass

    @skip('operators')
    def test_not_quite_operators(self):
        pass

    def test_operator_indirect(self):
        pass

    @skip('operators')
    def test_operator_invalid(self):
        pass

    @skip('operators')
    def test_operators(self):
        pass

    @skip('operators')
    def test_operators_multichar_is_valid(self):
        pass

    @skip('operators')
    def test_operators_with_whitespace(self):
        pass

    @skip('leftrec')
    def test_recursion_both(self):
        pass

    @skip('leftrec')
    def test_recursion_direct_left(self):
        pass

    @skip('leftrec')
    def test_recursion_without_a_label(self):
        pass

    @skip('leftrec')
    def test_recursion_indirect_left(self):
        pass

    @skip('leftrec')
    def test_recursion_left_opt(self):
        pass

    @skip('leftrec')
    def test_recursion_repeated(self):
        pass
