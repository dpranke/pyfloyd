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

from . import grammar_test


class _Mixin(grammar_test.GeneratorMixin):
    exe = 'node'
    generator = 'javascript'
    floyd_externs = {'unicode_names': False}


class Hello(_Mixin, grammar_test.HelloMixin):
    pass


class Rules(_Mixin, grammar_test.RulesMixin):
    pass


class Actions(_Mixin, grammar_test.ActionsMixin):
    pass


class Functions(_Mixin, grammar_test.FunctionsMixin):
    def test_dedent(self):
        # TODO: `dedent` isn't implemented properly in the hardcoded
        # JS generator yet.
        self.check(
            'g = -> dedent("\n  foo\n     bar\n", -1)',
            text='',
            out='\n  foo\n     bar\n',
        )


class Comments(_Mixin, grammar_test.CommentsMixin):
    pass


class Pragmas(_Mixin, grammar_test.PragmasMixin):
    pass


class Errors(_Mixin, grammar_test.ErrorsMixin):
    pass


class Operators(_Mixin, grammar_test.OperatorsMixin):
    pass


class Recursion(_Mixin, grammar_test.RecursionMixin):
    pass


class Integration(_Mixin, grammar_test.IntegrationMixin):
    @grammar_test.skip('integration')
    def test_json5_special_floats(self):
        # TODO: `Infinity` and `NaN` are legal Python values and legal
        # JavaScript values, but they are not legal JSON values, and so
        # we can't read them in from output that is JSON.
        pass
