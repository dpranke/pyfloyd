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

from typing import Callable, Optional, Sequence


FormatMethod = Callable[[int, str], list[str]]

# Pick a line length way over anything practical in order to force
# things to be formatted on one line where possible.
MAX_LENGTH = 1000000


class FormatObj:
    def fmt(self, length: int, indent: str) -> list[str]:
        """Returns a list of strings, each representing a line."""
        raise NotImplementedError


El = str | FormatObj
ElSeq = Sequence[El]
ElList = list[El]


def flatten(obj: El, length: int = 79, indent: str = '    ') -> list[str]:
    """Flatten an object into a list of 1 or more strings.

    Each string must be shorter than `max_length` characters, if possible.
    """
    return _fmt(obj, length, indent)


def _fmt(obj: El, length: int, indent: str) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    return obj.fmt(length, indent)


def _fmt_one(obj: El, length: int, indent: str) -> str:
    lines = _fmt(obj, length, indent)
    assert len(lines) == 1, (
        f'format unexpectedly returned more than one line: {repr(lines)}'
    )
    return lines[0]


class Indent(FormatObj):
    def __init__(self, obj: FormatObj):
        super().__init__()
        self.obj = obj

    def __repr__(self):
        return 'Indent(' + repr(self.obj) + ')'

    def fmt(self, length: int, indent: str) -> list[str]:
        new_length = length - len(indent)
        lines = []
        for line in self.obj.fmt(new_length, indent):
            if line:
                lines.append(indent + line)
            else:
                lines.append(line)
        return lines


class Lit(FormatObj):
    def __init__(self, s: str):
        self.s = s

    def __repr__(self):
        return f'Lit({repr(self.s)})'

    def fmt(self, length: int, indent: str) -> list[str]:
        return [self.s]


class MultipleObj(FormatObj):
    def fmt(self, length: int, indent: str) -> list[str]:
        """Returns a list of strings, each representing a line."""
        lines = self.fmt_one(MAX_LENGTH, indent)
        if all(len(line) < length for line in lines):
            return lines
        lines = self.fmt_multiple(MAX_LENGTH, indent)
        if all(len(line) < length for line in lines):
            return lines
        return self.fmt_multiple(length, indent)

    def fmt_one(self, length: int, indent: str) -> list[str]:
        raise NotImplementedError

    def fmt_multiple(self, length: int, indent: str) -> list[str]:
        raise NotImplementedError


class ListObj(FormatObj):
    def __init__(self, objs: Optional[ElSeq] = None):
        self.objs: ElList
        if not objs:
            self.objs = []
        elif len(objs) == 1 and isinstance(objs[0], self.__class__):
            self.objs = objs[0].objs
        else:
            self.objs = list(objs)

    def fmt(self, length: int, indent: str) -> list[str]:
        raise NotImplementedError


class VList(ListObj):
    def __repr__(self):
        if self.objs:
            return (
                'VList([\n  '
                + ',\n  '.join(repr(o) for o in self.objs)
                + '\n])'
            )
        return 'VList()'

    def __iadd__(self, obj):
        if isinstance(obj, VList):
            self.objs.extend(obj.objs)
        else:
            self.objs.append(obj)
        return self

    def fmt(self, length: int, indent: str) -> list[str]:
        lines = []
        for obj in self.objs:
            lines.extend(_fmt(obj, length, indent))
        return lines


class HList(ListObj):
    def __repr__(self):
        return 'HList([' + ', '.join(repr(o) for o in self.objs) + '])'

    def fmt(self, length: int, indent: str) -> list[str]:
        lines: list[str] = []
        if len(self.objs):
            lines.extend(_fmt(self.objs[0], length, indent))
            for obj in self.objs[1:]:
                if isinstance(obj, str):
                    lines[-1] += obj
                else:
                    new_length = length - len(lines[-1])
                    sublines = obj.fmt(new_length, indent)
                    lines[-1] += sublines[0]
                    if len(sublines) > 1:
                        lines.extend(sublines[1:])
        return lines


class Saw(MultipleObj):
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

    def __init__(self, start: str, mid: El, end: El):
        super().__init__()
        self.start: str = start
        self.mid: El = mid
        self.end: El = end

    def __repr__(self):
        return f'Saw({repr(self.start)}, {repr(self.mid)}, {repr(self.end)})'

    def fmt_one(self, length: int, indent: str) -> list[str]:
        s = (
            self.start
            + _fmt_one(self.mid, length, indent)
            + _fmt_one(self.end, length, indent)
        )
        return [s]

    def fmt_multiple(self, length: int, indent: str) -> list[str]:
        lines = [self.start]
        new_length = length - len(indent)
        for line in _fmt(self.mid, length, indent):
            lines.append(indent + line)
        for line in _fmt(self.end, new_length, indent):
            lines.append(line)
        return lines


class Comma(MultipleObj):
    """Format a comma-separated list of arguments.

    If we need to format a list of arguments across multiple lines, we
    want each to appear on its own line with a trailing comma, even on
    the last line where the trailing comma is unnecessary.
    """

    def __init__(self, objs: Optional[ElSeq] = None):
        self.objs: ElList
        if not objs:
            self.objs = []
        else:
            self.objs = list(objs)

    def __repr__(self):
        return 'Comma(' + repr(self.objs) + ')'

    def fmt_one(self, length: int, indent: str) -> list[str]:
        if not self.objs:
            return ['']

        new_length = length
        s = _fmt_one(self.objs[0], new_length, indent)
        for obj in self.objs[1:]:
            new_length -= len(s) + 2
            s += ', ' + _fmt_one(obj, new_length, indent)
        return [s]

    def fmt_multiple(self, length: int, indent: str) -> list[str]:
        if not self.objs:
            return ['']

        new_length = length - 1
        lines = []
        for obj in self.objs:
            lines += _fmt(obj, new_length, indent)
            if len(self.objs) > 1:
                lines[-1] += ','
        return lines


class Tree(MultipleObj):
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

    def __init__(self, left: Optional[El], op: str, right: Optional[El]):
        self.left = left
        self.op = op
        self.right = right
        assert self.left is not None or self.right is not None

    def __repr__(self):
        return 'Tree(%s, %s, %s)' % (
            repr(self.left),
            repr(self.op),
            repr(self.right),
        )

    def fmt_one(self, length: int, indent: str) -> list[str]:
        if self.left is None:
            s = self.op
            assert self.right is not None
            s += _fmt_one(self.right, length, indent)
        else:
            s = _fmt_one(self.left, length, indent)
            if self.right is None:
                s += self.op
            else:
                s += ' ' + self.op + ' '
                new_length = length - len(s)
                s += _fmt_one(self.right, new_length, indent)
        return [s]

    def fmt_multiple(self, length: int, indent: str) -> list[str]:
        if self.left is None:
            assert self.right is not None
            new_length = length - len(self.op)
            sublines = _fmt(self.right, new_length, indent)
            lines = [self.op + sublines[0]] + sublines[1:]
            return lines

        lines = _fmt(self.left, length, indent)
        if self.right is None:
            lines[-1] += self.op
            return lines

        op = self.op
        right: Optional[El] = self.right
        while isinstance(right, Tree):
            new_length = length - len(op) - 1
            if right.left is not None:
                right_lines = _fmt(right.left, new_length, indent)
                lines.append(op + ' ' + right_lines[0])
                lines += right_lines[1:]
            op = right.op
            right = right.right
        if right is not None:
            new_length = length - len(op) - 1
            if isinstance(right, FormatObj):
                right_lines = _fmt(right, new_length, indent)
                lines.append(op + ' ' + right_lines[0])
                lines += right_lines[1:]
            else:
                lines.append(op + ' ' + right)
        return lines
