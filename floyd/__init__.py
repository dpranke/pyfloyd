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

"""A parsing framework and parser generator for Python."""

from floyd.api import parse, compile_parser, generate_parser, pretty_print
from floyd.version import __version__

__all__ = [
    '__version__',
    'compile_parser',
    'generate_parser',
    'parse',
    'pretty_print',
]
