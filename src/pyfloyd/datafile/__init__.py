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

This module follows the API of the standard `json` module where possible.
As such, it provides the following functions:

- load   - Load an object from a file
- loads  - Load an object from a string
- dump   - Dump an object to a file
- dumps  - Dump an object to a string

It also provides a number of other utility functions:

- parse         - Parse an object from a string, returning positional
                  and error information (does not raise exceptions).
- dedent        - Remove leading whitespace from a multiline string per the
                  datafile specification
- decode_string - Returns a (potentially) unescaped, dedented version of a
                  string.
- decode_escape - Returns the unicode character for a given datafile
                  escape sequence.
- encode_string - Returns an encoded (quoted and escaped as appropriate)
                  string matching the datafile specification. This will
                  return a string as an unquoted bareword if possible.
- encode_escape - Returns the matching datafile escape sequence for
                  a unicode characer.
- encode_quoted_string - Returns an quoted (and escaped) string (no
                         barewords).
- ishex         - Returns whether a character is a hex digit.
- isoct         - Returns whether a character is an octal digit.

Decoding (the process of turning a string into a data structure, i.e.,
the load/loads/parse functions) is implemented in terms of a `Decoder`
class that can be subclassed to provide fine-grained customization
of behavior.
"""

import types

from .api import (  # noqa: F401 (unused-import)
    decode_escape,
    dedent,
    dump,
    dumps,
    encode_string,
    encode_quoted_string,
    escape_char,
    ishex,
    isoct,
    load,
    loads,
    parse,
    DatafileError,
    DatafileParseError,
    Decoder,
)


__version__ = '0.1.0.dev0'


__all__ = []
for _k in list(globals()):
    if not isinstance(globals()[_k], types.ModuleType):
        __all__.append(_k)
