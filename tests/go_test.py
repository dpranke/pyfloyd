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

from tests import grammar_test


class _Mixin(grammar_test.GeneratorMixin):
    cmd = ['go', 'run']
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
    pass


class Functions(_Mixin, grammar_test.FunctionsMixin):
    def test_dedent(self):
        # TODO: `dedent` isn't implemented properly in Go yet.
        self.check(
            'g = -> dedent("\n  foo\n     bar\n", -1)',
            text='',
            out='\n  foo\n     bar\n',
        )


class Errors(_Mixin, grammar_test.ErrorsMixin):
    pass


class Pragmas(_Mixin, grammar_test.PragmasMixin):
    pass


class Operators(_Mixin, grammar_test.OperatorsMixin):
    pass


class Recursion(_Mixin, grammar_test.RecursionMixin):
    pass


class Integration(_Mixin, grammar_test.IntegrationMixin):
    pass
