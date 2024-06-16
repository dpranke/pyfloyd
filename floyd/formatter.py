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

def flatten(obj):
    "Flatten an object into a list of 1 or more strings"
    depth = 0
    last_num_lines = 0
    while True:
        lines = fmt(obj, 0, depth)
        if all(len(line) <= 72 for line in lines):
            return lines
        num_lines = len(lines)
        if num_lines == last_num_lines:
            return lines
        depth += 1
        last_num_lines = num_lines

    return lines


def fmt(obj, current_depth, max_depth):
    if isinstance(obj, Formatter):
        return obj.fmt(current_depth, max_depth)
    assert isinstance(obj, list)
    if current_depth == max_depth:
        return _fmt_on_one_line(obj, current_depth, max_depth)
    return _fmt_on_multiple_lines(obj, current_depth, max_depth)



def _fmt_on_one_line(obj, current_depth, max_depth):
    s = ''
    for el in obj:
        if isinstance(el, str):
            s += el
        elif isinstance(el, Formatter):
            s += el.fmt(current_depth, max_depth)[0]
        else:
            s += fmt(el, current_depth, max_depth)[0]
    return [s]


def _fmt_on_multiple_lines(obj, current_depth, max_depth):
    lines = []
    for el in obj:
        if isinstance(el, str):
            lines.append(el)
        elif isinstance(el, Formatter) or isinstance(el, list):
            for l in fmt(el, current_depth + 1, max_depth):
                lines.append('    ' + l)
    return lines


class Formatter:
    def fmt(self, current_depth, max_depth):
        """Returns a list of strings, each representing a line."""
        raise NotImplementedError  # pragma: no cover


class CommaList(Formatter):
    """Format a comma-separated list of arguments.

    If we need to format a list of arguments across multiple lines, we
    want each to appear on its own line with a trailing comma, even on
    the last line where the trailing comma is unnecessary. Each line
    must also be indented.
    """
    def __init__(self, args):
        self.args = args

    def __repr__(self):
        return 'CommaList(' + self.fmt(0, 0)[0] + ')'

    def fmt(self, current_depth, max_depth):
        if current_depth == max_depth:
            return [', '.join(self.args)]
        return [arg + ',' for arg in self.args]


class Tree(Formatter):
    """Format a tree of expressions.

    This formats a tree of expressions, like `1 + 2 - 3`. If the expressions
    need to be split across multiple lines, we want the lines to be split
    before each operator, e.g.:
        1
        + 2
        - 3
    This requires some surgery when walking the tree."""

    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return 'Tree(' + self.fmt(0, 0)[0] + ')'

    def fmt(self, current_depth, max_depth):
        if current_depth == max_depth:
            s = fmt(self.left, current_depth, max_depth)[0]
            s += ' ' + self.op + ' '
            s += fmt(self.right, current_depth, max_depth)[0]
            return [s]
        lines = fmt(self.left, current_depth, max_depth)
        right = fmt(self.right, current_depth, max_depth)
        lines.append(self.op + ' ' + right[0])
        if right[1:]:
            lines += right[1:]
        return lines
