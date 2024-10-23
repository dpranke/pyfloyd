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


def flatten(obj, max_length=67, indent='    '):
    """Flatten an object into a list of 1 or more strings.

    Each string must be shorter than `max_length` characters, if possible.
    """
    depth = 0
    last_num_lines = 0
    while True:
        lines = fmt(obj, 0, depth, indent)
        if all(len(line) <= max_length for line in lines):
            return lines
        num_lines = len(lines)
        if num_lines == last_num_lines:
            return lines
        depth += 1
        last_num_lines = num_lines

    return lines


def fmt(obj, current_depth, max_depth, indent):
    if isinstance(obj, str):
        return [obj]
    return obj.fmt(current_depth, max_depth, indent)


class Formatter:
    def fmt(self, current_depth, max_depth, indent):
        """Returns a list of strings, each representing a line."""
        raise NotImplementedError  # pragma: no cover


class Saw(Formatter):
    """Formats series of calls and lists as a saw-shaped pattern.

    Expressions of the form `foo(x)`, `[4]`, and `foo(x)[4]` can be called
    saw-shaped, as when the arguments are long, the rest can be a series
    of alternating lines and indented regions, e.g.

    ```
    foo(
        x
    )[
        4
    ]

    where the unindented parts are all on a single line and the indented
    parts may be on one or more lines.
    """

    def __init__(self, start, mid, end):
        self.start = start
        self.mid = mid
        self.end = end

    def __repr__(self):
        return f'Saw({repr(self.start)}, {repr(self.mid)}, {repr(self.end)})'

    def fmt(self, current_depth, max_depth, indent):
        if current_depth == max_depth:
            s = (
                fmt(self.start, current_depth, max_depth, indent)[0]
                + fmt(self.mid, current_depth, max_depth, indent)[0]
                + fmt(self.end, current_depth, max_depth, indent)[0]
            )
            return [s]
        lines = [self.start]
        for line in fmt(self.mid, current_depth + 1, max_depth, indent):
            lines.append(indent + line)
        for line in fmt(self.end, current_depth, max_depth, indent):
            lines.append(line)
        return lines


class Comma(Formatter):
    """Format a comma-separated list of arguments.

    If we need to format a list of arguments across multiple lines, we
    want each to appear on its own line with a trailing comma, even on
    the last line where the trailing comma is unnecessary.
    """

    def __init__(self, args):
        # Ensure that if we were passed a generator we can hold onto the values.
        self.args = list(args)

    def __repr__(self):
        return 'Comma(' + repr(self.args) + ')'

    def fmt(self, current_depth, max_depth, indent):
        if current_depth == max_depth:
            s = fmt(self.args[0], current_depth, max_depth, indent)[0]
            for arg in self.args[1:]:
                s += ', ' + fmt(arg, current_depth, max_depth, indent)[0]
            return [s]
        lines = []
        for arg in self.args:
            arg_lines = fmt(arg, current_depth, max_depth, indent)
            lines += arg_lines
            lines[-1] += ','
        return lines


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
        return 'Tree(%s, %s, %s)' % (
            repr(self.left),
            repr(self.op),
            repr(self.right),
        )

    def fmt(self, current_depth, max_depth, indent):
        if current_depth == max_depth:
            s = fmt(self.left, current_depth, max_depth, indent)[0]
            s += ' ' + self.op + ' '
            s += fmt(self.right, current_depth, max_depth, indent)[0]
            return [s]
        lines = fmt(self.left, current_depth, max_depth, indent)
        right = fmt(self.right, current_depth, max_depth, indent)
        lines.append(self.op + ' ' + right[0])
        if right[1:]:
            lines += right[1:]
        return lines
