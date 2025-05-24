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

import textwrap
import unittest

import pyfloyd


from . import grammar_test


class Tests(unittest.TestCase, grammar_test.GrammarTestsMixin):
    max_diff = None

    def compile(self, grammar, path='<string>', memoize=False, externs=None):
        return pyfloyd.compile_to_parser(
            textwrap.dedent(grammar), path, memoize=memoize, externs=externs
        )
