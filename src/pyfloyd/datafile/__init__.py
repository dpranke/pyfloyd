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

"""A pure Python implementation of the Floyd datafile format.

This module follows the API of the standard `json` module as much as
possible. It provides the following functions:

- `load()`  - Load an object from a file
- `loads()` - Load an object from a string
- `dump()`  - Dump an object to a file
- `dumps()` - Dump an object to a string
- `parse()` - Parse an object from a string, returning positional information.
"""

from .api import (
    decode_escape,
    dedent,
    dump,
    dumps,
    ishex,
    isoct,
    load,
    loads,
    parse,
    ArgparseAppendAction,
    ArgparseStoreAction,
    Decoder,
)
from .tool import main


__version__ = '0.1.0.dev0'


__all__ = [
    '__version__',
    'decode_escape',
    'dedent',
    'dump',
    'dumps',
    'ishex',
    'isoct',
    'load',
    'loads',
    'main',
    'parse',
    'ArgparseAppendAction',
    'ArgparseStoreAction',
    'Decoder',
]
