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

import inspect
from typing import Any, Callable, Optional, Sequence, Union

from pyfloyd import datafile


FormatMethod = Callable[[int, str], list[str]]


El = Union[str, 'FormatObj', None]
ElSeq = Sequence[El]
ElList = list[El]
_FmtFn = Callable[[El, Union[None, int], str], list[str]]


class FormatObj:
    tag: str = ''

    def __init__(self, objs: Optional[ElSeq] = None):
        self.objs: ElList = list(objs) if objs else []

    def __eq__(self, other):
        return (
            (self.__class__ == other.__class__)
            and (len(self.objs) == len(other.objs))
            and all(
                self.objs[i] == other.objs[i] for i in range(len(self.objs))
            )
        )

    def __repr__(self):
        cls_name = self.__class__.__name__
        return f'{cls_name}([{", ".join(repr(obj) for obj in self.objs)}])'

    def to_list(self):
        return [self.tag] + [to_list(obj) for obj in self.objs]

    def to_lisplist(self):
        assert self.tag is not None
        return LispList([self.tag] + [to_lisplist(obj) for obj in self.objs])

    def is_empty(self):
        return len(self.objs) == 0

    def fmt(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        """Returns a list of strings, each representing a line."""
        raise NotImplementedError


class _MultipleObj(FormatObj):
    "An object that can be formatted in multiple non-trivially different ways."

    def fmt(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        """Returns a list of strings, each representing a line."""
        s = self.fmt_single_line(None, indent, fmt_fn)
        if length is None or len(s) < length:
            return [s]
        lines = self.fmt_multiple_lines(None, indent, fmt_fn)
        if all(len(line) < length for line in lines):
            return lines
        return self.fmt_multiple_lines(length, indent, fmt_fn)

    def fmt_single_line(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> str:
        raise NotImplementedError

    def fmt_multiple_lines(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        raise NotImplementedError


# For backward compatibility. TODO: remove this.
ListObj = FormatObj


class Comma(_MultipleObj):
    """Format a comma-separated list of arguments.

    If we need to format a list of arguments across multiple lines, we
    want each to appear on its own line with a trailing comma, even on
    the last line where the trailing comma is unnecessary.
    """

    tag = 'comma'

    def fmt_single_line(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> str:
        if not self.objs:
            return ''

        new_l = None if length is None else length
        s = _fmt_single_line(self.objs[0], new_l, indent, fmt_fn)
        for obj in self.objs[1:]:
            if new_l is not None:
                new_l -= len(s) + 2
            s += ', ' + _fmt_single_line(obj, new_l, indent, fmt_fn)
        return s

    def fmt_multiple_lines(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        if not self.objs:
            return ['']

        new_l = None if length is None else length - 1
        lines = []
        for obj in self.objs:
            lines += fmt_fn(obj, new_l, indent)
            if len(self.objs) > 1:
                lines[-1] += ','
        return lines


class HList(FormatObj):
    tag = 'hl'

    def __init__(self, objs: Optional[ElSeq] = None):
        super().__init__([])
        objs = objs or []
        for obj in objs:
            if isinstance(objs[0], self.__class__):
                assert isinstance(obj, FormatObj)
                self.objs.extend(obj.objs)
            else:
                self.objs.append(obj)

    def fmt(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        lines: list[str] = []
        if len(self.objs) != 0:
            lines.extend(fmt_fn(self.objs[0], length, indent))
            for obj in self.objs[1:]:
                if obj is None:
                    continue
                if isinstance(obj, str):
                    lines[-1] += obj
                else:
                    new_l = None if length is None else length - len(lines[-1])
                    sublines = obj.fmt(new_l, indent, fmt_fn)
                    lines[-1] += sublines[0]
                    if len(sublines) > 1:
                        lines.extend(sublines[1:])
        return lines


class Indent(FormatObj):
    tag = 'ind'

    def __init__(self, objs):
        if isinstance(objs, list):
            super().__init__(objs)
        else:
            super().__init__([objs])

    def fmt(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        new_l = None if length is None else length - len(indent)
        lines = []
        assert len(self.objs) > 0 and isinstance(self.objs[0], FormatObj)
        for line in self.objs[0].fmt(new_l, indent, fmt_fn):
            if line:
                lines.append(indent + line)
            else:
                lines.append(line)
        return lines


class LispList(_MultipleObj):
    """Format as a list, lisp-style.

    Across multiple lines, the second and subsequent lines will be
    indented to match the second argument to the list, and closing
    brackets will be on the last line:

        [foo [bar [baz]
                  [a b c]]
             [quux]]
    """

    # TODO: Should this just be a flag on an existing class or classes,
    # rather than a separate class?

    tag = 'll'

    def fmt_single_line(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> str:
        s = '['
        if self.objs:
            s += _fmt_single_line(self.objs[0], length, indent, fmt_fn)
            if len(self.objs) > 1:
                for obj in self.objs[1:]:
                    if obj is None:
                        continue
                    s += ' '
                    s += _fmt_single_line(obj, length, indent, fmt_fn)
        s += ']'
        return s

    def fmt_multiple_lines(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        lines = ['']
        if len(self.objs) == 0:
            return ['[]']
        if len(self.objs) == 1:
            if isinstance(self.objs[0], str):
                return ['[' + self.objs[0] + ']']
            if self.objs[0] is None:
                return ['[]']
            sl = fmt_fn(self.objs[0], length, indent)
            sl[0] = '[' + sl[0] + ']'
            sl[-1] = sl[-1] + ']'
            return sl

        assert isinstance(self.objs[0], str)
        prefix = '[' + self.objs[0] + ' '
        lines[0] += prefix
        new_l = None if length is None else length - len(prefix)
        for i, obj in enumerate(self.objs[1:]):
            if obj is None:
                continue
            sl = fmt_fn(obj, new_l, indent)
            if i == 0:
                lines[0] += sl[0]
            else:
                lines.append(' ' * len(prefix) + sl[0])
            for sline in sl[1:]:
                lines.append(' ' * len(prefix) + sline)
        lines[-1] += ']'
        return lines


class Lit(FormatObj):
    tag = 'lit'

    def __init__(self, obj: Union[str, ElSeq]):
        if isinstance(obj, str):
            super().__init__([obj])
        else:
            assert len(obj) > 0 and isinstance(obj[0], str)
            super().__init__(obj)

    @property
    def s(self):
        return self.objs[0]

    @s.setter
    def s(self, v):
        self.objs[0] = v

    def fmt(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        assert isinstance(self.objs[0], str)
        return [self.objs[0]]


class Saw(_MultipleObj):
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

    tag = 'saw'

    def __init__(self, *args):
        if len(args) == 3:
            super().__init__(args)
        else:
            super().__init__(*args)

    @property
    def start(self):
        return self.objs[0]

    @start.setter
    def start(self, v):
        self.objs[0] = v

    @property
    def mid(self):
        return self.objs[1]

    @mid.setter
    def mid(self, v):
        self.objs[1] = v

    @property
    def end(self):
        return self.objs[2]

    @end.setter
    def end(self, v):
        self.objs[2] = v

    def fmt_single_line(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> str:
        s = ''
        for obj in self.objs:
            s += _fmt_single_line(obj, length, indent, fmt_fn)
        return s

    def fmt_multiple_lines(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        lines = fmt_fn(self.start, length, indent)
        new_l = None if length is None else length - len(lines[-1])
        for line in fmt_fn(self.mid, length, indent):
            lines.append(indent + line)
        for line in fmt_fn(self.end, new_l, indent):
            lines.append(line)
        return lines


class Tree(_MultipleObj):
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

    tag = 'tree'

    def __init__(self, *args):
        if len(args) == 3:
            super().__init__(args)
        else:
            super().__init__(*args)
        assert self.left is not None or self.right is not None

    @property
    def left(self) -> Optional[El]:
        return self.objs[0]

    @left.setter
    def left(self, v: Optional[El]):
        self.objs[0] = v

    @property
    def op(self) -> str:
        assert isinstance(self.objs[1], str)
        return self.objs[1]

    @op.setter
    def op(self, v: str):
        self.objs[1] = v

    @property
    def right(self) -> Optional[El]:
        return self.objs[2]

    @right.setter
    def right(self, v: Optional[El]):
        self.objs[2] = v

    def fmt_single_line(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> str:
        # pylint: disable=unbalanced-tuple-unpacking
        left, op, right = self.objs
        assert isinstance(op, str)
        if left is None:
            s = op
            assert right is not None
            s += _fmt_single_line(right, length, indent, fmt_fn)
        else:
            s = _fmt_single_line(left, length, indent, fmt_fn)
            if right is None:
                s += op
            else:
                s += ' ' + op + ' '
                new_l = None if length is None else length - len(s)
                s += _fmt_single_line(right, new_l, indent, fmt_fn)
        return s

    def fmt_multiple_lines(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        # pylint: disable=unbalanced-tuple-unpacking
        left, op, right = self.objs
        lines: list[str]
        right_lines: list[str]
        assert isinstance(op, str)

        if left is None:
            assert right is not None
            assert isinstance(op, str)
            new_l = None if length is None else length - len(self.op)
            sublines: list[str] = fmt_fn(right, new_l, indent)
            lines = [op + sublines[0]] + sublines[1:]
            return lines

        lines = fmt_fn(left, length, indent)
        if right is None:
            lines[-1] += self.op
            return lines

        while isinstance(right, Tree):
            new_l = None if length is None else length - len(op) - 1
            if right.left is not None:
                right_lines = fmt_fn(right.left, new_l, indent)
                lines.append(op + ' ' + right_lines[0])
                lines += right_lines[1:]
            op = right.op
            right = right.right
        if right is not None:
            new_l = None if length is None else length - len(op) - 1
            if isinstance(right, FormatObj):
                right_lines = fmt_fn(right, new_l, indent)
                lines.append(op + ' ' + right_lines[0])
                lines += right_lines[1:]
            else:
                lines.append(op + ' ' + right)
        return lines


class VList(FormatObj):
    tag = 'vl'

    def __init__(self, objs: Optional[ElSeq] = None):
        super().__init__([])
        objs = objs or []
        for obj in objs:
            if isinstance(obj, str):
                lines = obj.splitlines()
                if len(lines) < 2:
                    self.objs.append(obj)
                else:
                    self.objs.extend(obj.splitlines())
            else:
                self.objs.append(obj)

    def __iadd__(self, obj):
        if isinstance(obj, str):
            lines = obj.splitlines()
            if len(lines) < 2:
                self.objs.append(obj)
            else:
                self.objs.extend(lines)
        else:
            self.objs.append(obj)
        return self

    def fmt(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        lines = []
        for obj in self.objs:
            if obj is not None:
                lines.extend(fmt_fn(obj, length, indent))
        return lines


def _fmt(obj: El, length: Union[int, None], indent: str) -> list[str]:
    if obj is None:
        return []
    if isinstance(obj, str):
        if obj == '':
            return ['']
        lines = obj.splitlines()
        return lines
    return obj.fmt(length, indent, _fmt)


def flatten(
    obj: El,
    length: Union[None, int] = 79,
    indent: str = '    ',
    fmt_fn: _FmtFn = _fmt,
) -> list[str]:
    """Flatten an object into a list of 1 or more strings.

    Each string must be shorter than `length` characters, if possible. If
    length is None, lines can be arbitrarily long.
    """
    return fmt_fn(obj, length, indent)


def flatten_as_lisplist(
    obj: El, length: Optional[int] = 79, indent: str = '    '
) -> list[str]:
    """Print a datafile-formatted representation of the tree itself."""
    r_obj = to_lisplist(obj)
    return flatten(r_obj, length, indent, _fmt_quote)


def _fmt_quote(obj: El, length: Union[int, None], indent: str) -> list[str]:
    if obj is None:
        return []
    if isinstance(obj, str):
        if obj == '':
            return [datafile.encode_string('')]
        return [datafile.encode_string(line) for line in obj.splitlines()]
    return obj.fmt(length, indent, _fmt_quote)


def _fmt_single_line(
    obj: El, length: Union[int, None], indent: str, fmt_fn: _FmtFn
) -> str:
    lines = fmt_fn(obj, length, indent)
    assert isinstance(lines, list)
    assert len(lines) == 1, (
        f'format unexpectedly returned more than one line: {repr(lines)}'
    )

    return lines[0]


def to_list(obj):
    if isinstance(obj, FormatObj):
        return obj.to_list()
    return obj


def to_lisplist(obj):
    if isinstance(obj, FormatObj):
        return obj.to_lisplist()
    return obj


CLASS_MAP = {}


def _set_class_map():
    for k in list(globals()):
        obj = globals()[k]
        if (
            inspect.isclass(obj)
            and issubclass(obj, FormatObj)
            and obj not in (FormatObj, _MultipleObj)
        ):
            CLASS_MAP[obj.tag] = obj


_set_class_map()


def from_list(obj: Any) -> El:
    if not isinstance(obj, list):
        return obj
    assert len(obj) >= 2, 'lists need at least two elements: {obj!r}'
    tag = obj[0]
    assert tag in CLASS_MAP, f'unknown list tag {tag}'
    cls = CLASS_MAP[tag]
    args = []
    for ob in obj[1:]:
        arg = from_list(ob)
        args.append(arg)
    return cls(args)
