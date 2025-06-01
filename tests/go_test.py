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


@unittest.skip('unimplemented')
class Rules(_Mixin, grammar_test.RulesMixin):
    pass


@unittest.skip('unimplemented')
class Actions(_Mixin, grammar_test.ActionsMixin):
    pass


@unittest.skip('unimplemented')
class Functions(_Mixin, grammar_test.FunctionsMixin):
    pass


@unittest.skip('unimplemented')
class Comments(_Mixin, grammar_test.CommentsMixin):
    pass


@unittest.skip('unimplemented')
class Pragmas(_Mixin, grammar_test.PragmasMixin):
    pass


@unittest.skip('unimplemented')
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
