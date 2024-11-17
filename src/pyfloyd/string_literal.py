# Copyright 2024 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 as found in the LICENSE file.
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


def _enc(ch, esc_ch):
    bslash = '\\'
    if ch == esc_ch:
        return bslash + esc_ch
    if ch == bslash:
        return bslash + bslash
    if ch == '\b':
        return bslash + 'b'
    if ch == '\f':
        return bslash + 'f'
    if ch == '\n':
        return bslash + 'n'
    if ch == '\r':
        return bslash + 'r'
    if ch == '\t':
        return bslash + 't'
    if ch == '\v':
        return bslash + 'v'
    if 32 <= ord(ch) < 126:
        return ch
    if ord(ch) < 256:
        return '\\x%02x' % ord(ch)
    return '\\u%04x' % ord(ch)


def escape(s, ch):
    """Returns a safely-escaped string of characters."""
    return ''.join(_enc(c, ch) for c in s)


def encode(s):
    """Return a string literal containing a safely-escaped string of chars."""
    squote = "'"
    dquote = '"'
    if squote in s:
        return dquote + escape(s, dquote) + dquote
    return squote + escape(s, squote) + squote
