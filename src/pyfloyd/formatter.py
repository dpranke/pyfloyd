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

from typing import List, Sequence


class FormatObj:
    def fmt(self, current_depth: int, max_depth: int, indent: str):
        """Returns a list of strings, each representing a line."""
        raise NotImplementedError  # pragma: no cover


def flatten(
    obj: FormatObj, max_length: int = 79, indent: str = '    '
) -> List[str]:
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


def fmt(
    obj: FormatObj, current_depth: int, max_depth: int, indent: str
) -> List[str]:
    if isinstance(obj, str):
        return [obj]
    return obj.fmt(current_depth, max_depth, indent)


class Indent(FormatObj):
    def __init__(self, obj):
        self.obj = obj

    def __repr__(self):
        return 'Indent(' + repr(self.obj) + ')'

    def fmt(self, current_depth: int, max_depth: int, indent: str) -> List[str]:
        return [indent + line for line in self.obj.fmt(current_depth, max_depth, indent)]


class Lit(FormatObj):
    def __init__(self, s):
        self.s = s

    def __repr__(self):
        return f'Lit({repr(self.s)})'

    def fmt(
        self, current_depth: int, max_depth: int, indent: str
    ) -> List[str]:
        return [self.s]


class ListObj(FormatObj):
    pass


class VList(ListObj):
    def __init__(self, objs: Sequence[FormatObj|str]):
        self.objs = objs

    def __repr__(self):
        if self.objs:
            return (
                'VList([\n  ' +
                ',\n  '.join(repr(o) for o in self.objs) +
                '\n])'
            )
        return 'VList([])'

    def append(self, obj: FormatObj|str):
        self.objs.append(obj)

    def fmt(self, current_depth: int, max_depth: int, indent: str) -> List[str]:
        lines = []
        for obj in self.objs:
            if isinstance(obj, str):
                lines.append(obj)
            else:
                assert isinstance(obj, FormatObj)
                lines.extend(obj.fmt(current_depth, max_depth, indent))
        return lines


class HList(ListObj):
    def __init__(self, objs: List[FormatObj|str]):
        self.objs = objs

    def __repr__(self):
        return 'VList([' + ', '.join(repr(o) for o in self.objs) + '])'

    def fmt(self, current_depth: int, max_depth: int, indent: str) -> List[str]:
        lines: List[str] = []
        if len(self.objs):
            if isinstance(self.objs[0], str):
                lines.append(self.objs[0])
            else:
                lines = self.objs[0].fmt(current_depth, max_depth, indent)
            for obj in self.objs[1:]:
                if isinstance(obj, str):
                    lines[-1] += obj
                else:
                    sublines = obj.fmt(current_depth, max_depth, indent)
                    lines[-1] += sublines[0]
                    if len(sublines) > 1:
                        lines.extend(sublines[1:])
        return lines


class Saw(FormatObj):
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

    def fmt(
        self, current_depth: int, max_depth: int, indent: str
    ) -> List[str]:
        try:
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
        except Exception as e:
            import pdb; pdb.set_trace()


class Comma(FormatObj):
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
        if not self.args:
            return ['']

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


class Tree(FormatObj):
    """Format a tree of expressions.

    This formats a tree of expressions, like `1 + 2 - 3`. If the expressions
    need to be split across multiple lines, we want the lines to be split
    before each operator, e.g.:
        1
        + 2
        - 3
    This requires some surgery when walking the tree.

    `left` and `right` may be `None` to handle prefix and postfix operators.
    """

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
            if self.left is None:
                s = self.op
                s += fmt(self.right, current_depth, max_depth, indent)[0]
            else:
                s = fmt(self.left, current_depth, max_depth, indent)[0]
                if self.right is None:
                    s += self.op
                else:
                    s += ' ' + self.op + ' '
                    s += fmt(self.right, current_depth, max_depth, indent)[0]
            return [s]

        #if self.right is None:
        #    right = ['']
        #else:
        #    right = fmt(self.right, current_depth, max_depth, indent)

        if self.left is None:
            s = self.op + fmt(self.right, current_depth, max_depth, indent)[0]
            lines = [s]
            return lines
        else:
            lines = fmt(self.left, current_depth, max_depth, indent)
        if self.right is None:
            lines[-1] += self.op
        else:
            right = fmt(self.right, current_depth, max_depth, indent)
            lines.append(self.op + ' ' + right[0])
            if right[1:]:
                lines += right[1:]
        return lines
