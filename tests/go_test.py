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


class _Mixin(grammar_test.GeneratorMixin):
    cmd = [shutil.which('go'), 'run']
    generator = 'datafile'
    template = 'go'
    ext = '.go'


class Hello(_Mixin, grammar_test.HelloMixin):
    pass


class Rules(_Mixin, grammar_test.RulesMixin):
    pass


class Values(_Mixin, grammar_test.ValuesMixin):
    pass


class Actions(_Mixin, grammar_test.ActionsMixin):
    @unittest.skip('bignum')
    def test_big_int(self):
        pass

    def test_ll_getitem(self):
        # TODO: make getitem work w/ literals.
        # self.check("grammar = end -> ['a', 'b'][1]", '', out='b')
        pass

    def test_quals(self):
        self.check("g = -> utoi(' ')", '', out=32)
        self.check("g = 'x'*:l -> l[0]", 'xx', out='x')
        # TODO: make getitem work w/ literals.
        # self.check("g = -> ['a', 'b'][1]", '', out='b')
        # self.check("g = -> [['a']][0][0]", '', out='a')


class Functions(_Mixin, grammar_test.FunctionsMixin):
    @unittest.skip('not implemented yet')
    def test_dedent(self):
        pass


class Errors(_Mixin, grammar_test.ErrorsMixin):
    pass


@unittest.skip('unimplemented')
class Operators(_Mixin, grammar_test.OperatorsMixin):
    pass


@unittest.skip('unimplemented')
class Recursion(_Mixin, grammar_test.RecursionMixin):
    pass


@unittest.skip('unimplemented')
class Integration(_Mixin, grammar_test.IntegrationMixin):
    pass
