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

import copy
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

    def __init__(self, *objs):
        self.objs = list(objs)

    def _optimize(self, objs, cls, indent):
        objs = self._collapse(objs, cls)
        objs = self._split_objs(objs, indent)
        objs = self._collapse(objs, cls)
        objs = self._simplify_hlists(objs)
        objs = self._merge_indents(objs)
        return objs

    def _split_objs(self, objs, indent):
        split_objs = []
        for obj in objs:
            if (
                isinstance(obj, str)
                and (obj.startswith(' ') or '\n' in obj)
                and indent is not None
            ):
                split_objs.append(split_to_objs(obj, indent))
            else:
                split_objs.append(obj)
        return split_objs

    def _collapse(self, objs, cls):
        if objs is None:
            return []
        new_objs = []
        for obj in objs:
            if obj is None:
                continue
            if obj.__class__ == cls:
                new_objs.extend(self._collapse(obj.objs, cls))
            elif isinstance(obj, list):
                new_objs.extend(self._collapse(obj, cls))
            else:
                new_objs.append(obj)
        return new_objs

    def _simplify_hlists(self, objs):
        new_objs = []
        for obj in objs:
            if isinstance(obj, HList):
                if len(obj.objs) == 0:
                    obj = ''
                elif len(obj.objs) == 1 and isinstance(obj.objs[0], str):
                    obj = obj.objs[0]
                elif all(isinstance(o, str) for o in obj.objs):
                    obj = ''.join(obj.objs)
            new_objs.append(obj)
        return new_objs

    def _merge_indents(self, objs):
        if not objs:
            return []
        new_objs = [objs[0]]
        for obj in objs[1:]:
            if isinstance(new_objs[-1], Indent):
                if isinstance(obj, Indent):
                    x = new_objs[-1]
                    y = obj
                    # Append the objs to the innermost common indent.
                    while isinstance(x.objs[-1], Indent) and isinstance(
                        y.objs[-1], Indent
                    ):
                        x = x.objs[-1]
                        y = y.objs[-1]
                    # Make a copy to keep from modifying the original
                    # the next time through the loop.
                    x.objs = x.objs + copy.deepcopy(y.objs)
                    continue
                if isinstance(obj, str) and obj == '':
                    new_objs[-1].objs.append(obj)
                    continue
            if isinstance(obj, Indent):
                new_objs.append(copy.deepcopy(obj))
            else:
                new_objs.append(obj)
        assert _lines(objs) == _lines(new_objs)
        return new_objs

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
        return f'{cls_name}({", ".join(repr(obj) for obj in self.objs)})'

    def to_list(self):
        return [self.tag] + [to_list(obj) for obj in self.objs]

    def to_lisplist(self):
        assert self.tag is not None
        return LispList(self.tag, *[to_lisplist(obj) for obj in self.objs])

    def is_empty(self):
        return len(self.objs) == 0

    def fmt(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        """Returns a list of strings, each representing a line."""
        raise NotImplementedError


# For backward compatibility. TODO: remove this.
ListObj = FormatObj


class HList(FormatObj):
    tag = 'hl'

    def __init__(self, *objs):
        super().__init__()
        new_objs = self._collapse(objs, cls=self.__class__)
        self.objs = self._simplify_hlists(new_objs)

    def fmt(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        lines: list[str] = []
        if len(self.objs) == 0:
            return ['']

        lines.extend(fmt_fn(self.objs[0], length, indent))
        for obj in self.objs[1:]:
            if obj is None:
                continue
            if isinstance(obj, str):
                lines[-1] += obj
            else:
                new_l = None if length is None else length - len(lines[-1])
                sublines = obj.fmt(new_l, indent, fmt_fn)
                if sublines:
                    lines[-1] += sublines[0]
                    if len(sublines) > 1:
                        lines.extend(sublines[1:])
        return lines


class VList(FormatObj):
    tag = 'vl'

    def __init__(self, *objs, indent=None):
        super().__init__()
        self.indent = indent
        self.objs = self._optimize(objs, self.__class__, indent)

    def __iadd__(self, obj):
        self.objs.extend(self._optimize([obj], self.__class__, self.indent))
        return self

    def fmt(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        lines = []
        for obj in self.objs:
            if obj is not None:
                lines.extend(fmt_fn(obj, length, indent))
        return lines


class Indent(VList):
    tag = 'ind'

    def __init__(self, *objs, indent=None):
        super().__init__([], indent=indent)
        new_objs = self._optimize(objs, VList, indent)
        self.objs = new_objs

    def fmt(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        new_l = _new_length(length, len(indent))
        lines = super().fmt(new_l, indent, fmt_fn)
        new_lines = ['' if line == '' else indent + line for line in lines]
        return new_lines


class _MultipleObj(FormatObj):
    "An object that can be formatted in multiple non-trivially different ways."

    def fmt(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        """Returns a list of strings, each representing a line."""
        s = self.fmt_single_line(None, indent, fmt_fn)
        if s is not None and (length is None or len(s) <= length):
            return [s]
        lines = self.fmt_multiple_lines(None, indent, fmt_fn)
        if length is None:
            return lines
        if all((line is not None and len(line) <= length) for line in lines):
            return lines
        return self.fmt_multiple_lines(length, indent, fmt_fn)

    def fmt_single_line(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> Optional[str]:
        raise NotImplementedError

    def fmt_multiple_lines(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        raise NotImplementedError


class Comma(_MultipleObj):
    """Format a comma-separated list of arguments.

    If we need to format a list of arguments across multiple lines, we
    want each to appear on its own line with a trailing comma, even on
    the last line where the trailing comma is unnecessary.
    """

    tag = 'comma'

    def fmt_single_line(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> Optional[str]:
        if not self.objs:
            return ''

        new_l = None if length is None else length
        s = _fmt_single_line(self.objs[0], new_l, indent, fmt_fn)
        if s is None:
            return s

        for obj in self.objs[1:]:
            if new_l is not None:
                new_l -= len(s) + 2
            r = _fmt_single_line(obj, new_l, indent, fmt_fn)
            if r is None:
                return r
            s += ', ' + r
        return s

    def fmt_multiple_lines(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        if not self.objs:
            return ['']

        new_l = None if length is None else length
        lines = []
        for obj in self.objs:
            lines += fmt_fn(obj, new_l, indent)
            if len(self.objs) > 1:
                lines[-1] += ','
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
    ) -> Optional[str]:
        s = '['
        if self.objs:
            # r = _fmt_single_line(self.objs[0], length, indent, fmt_fn)
            s += self.objs[0]
            if len(self.objs) > 1:
                for obj in self.objs[1:]:
                    if obj is None:
                        continue
                    s += ' '
                    r = _fmt_single_line(obj, length, indent, fmt_fn)
                    if r is None:
                        return r
                    s += r
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


class Saw(_MultipleObj):
    """Formats values in a saw-shaped pattern.

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
    parts may be on one or more lines. We express this as one Saw object
    with an initial prefix + multiple Triangle objects.
    """

    tag = 'saw'

    def __init__(self, s, *args):
        super().__init__()
        assert isinstance(s, (str, Triangle))
        for arg in args:
            assert isinstance(arg, Triangle)

        if isinstance(s, str):
            objs = [s]
        else:
            objs = list(s.objs)
        for arg in args:
            objs[-1] += arg.objs[0]
            objs.append(arg.objs[1])
            objs.append(arg.objs[2])
        self.objs = objs

    def fmt_single_line(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> Optional[str]:
        s = ''
        for obj in self.objs:
            r = _fmt_single_line(obj, length, indent, fmt_fn)
            if r is None:
                return r
            s += r
        return s

    def fmt_multiple_lines(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        lines = fmt_fn(self.objs[0], length, indent)
        i = 1
        while i < len(self.objs) - 1:
            offset = len(lines[-1]) + len(self.objs[i + 1])
            new_l = _new_length(length, offset)
            sub_lines = fmt_fn(self.objs[i], new_l, indent)
            if (
                length
                and len(sub_lines) == 1
                and len(lines[-1]) + offset <= length
            ):
                lines[-1] += sub_lines[0] + self.objs[i + 1]
                i += 2
                continue
            assert indent is not None
            new_l = _new_length(length, len(indent))
            lines.extend(
                indent + line for line in fmt_fn(self.objs[i], new_l, indent)
            )
            lines.append(self.objs[i + 1])
            i += 2
        return lines


class Triangle(_MultipleObj):
    tag = 'tri'

    def __init__(self, left, mid, right):
        super().__init__(left, mid, right)
        self.left, self.mid, self.right = left, mid, right
        assert isinstance(self.objs[0], str)
        assert isinstance(self.objs[2], str)

    def fmt_single_line(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> Optional[str]:
        s = ''
        for obj in self.objs:
            r = _fmt_single_line(obj, length, indent, fmt_fn)
            if r is None:
                return r
            s += r
        return s

    def fmt_multiple_lines(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        lines = fmt_fn(self.objs[0], length, indent)
        new_l = _new_length(length, len(indent))
        lines.extend(
            indent + line for line in fmt_fn(self.objs[1], new_l, indent)
        )
        lines.extend(fmt_fn(self.objs[2], length, indent))
        return lines


class Tree(_MultipleObj):
    """Formats a call or dereference.

    Given an expression like '(foo)' or '[bar]', where there's a starting
    and ending string and a possibly more complex object in the middle,
    formats these thing over possibly multiple lines.
    """

    tag = 'tree'

    def __init__(self, left, op, right):
        super().__init__(left, op, right)
        self.left, self.op, self.right = left, op, right

    def fmt_single_line(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> Optional[str]:
        # pylint: disable=unbalanced-tuple-unpacking
        left, op, right = self.left, self.op, self.right
        assert isinstance(op, str)
        if left is None:
            s = op
            assert right is not None
            r = _fmt_single_line(right, length, indent, fmt_fn)
            if r is None:
                return r
            s += r
        else:
            r = _fmt_single_line(left, length, indent, fmt_fn)
            if r is None:
                return r
            s = r
            if right is None:
                s += op
            else:
                s += ' ' + op + ' '
                new_l = None if length is None else length - len(s)
                r = _fmt_single_line(right, new_l, indent, fmt_fn)
                if r is None:
                    return r
                s += r
        return s

    def fmt_multiple_lines(
        self, length: Union[int, None], indent: str, fmt_fn: _FmtFn
    ) -> list[str]:
        left, op, right = self.left, self.op, self.right
        lines: list[str]
        right_lines: list[str]
        assert isinstance(op, str)

        if left is None:
            assert right is not None
            assert isinstance(op, str)
            new_l = None if length is None else length - len(op)
            sublines: list[str] = fmt_fn(right, new_l, indent)
            if sublines:
                lines = [op + sublines[0]] + sublines[1:]
            return lines

        lines = fmt_fn(left, length, indent)
        if right is None:
            lines[-1] += op
            return lines

        while isinstance(right, Tree):
            new_l = None if length is None else length - len(op) - 1
            if right.objs[0] is not None:
                right_lines = fmt_fn(right.objs[0], new_l, indent)
                lines.append(op + ' ' + right_lines[0])
                lines += right_lines[1:]
            op = right.objs[1]
            right = right.objs[2]
        if right is not None:
            new_l = None if length is None else length - len(op) - 1
            if isinstance(right, FormatObj):
                right_lines = fmt_fn(right, new_l, indent)
                lines.append(op + ' ' + right_lines[0])
                lines += right_lines[1:]
            else:
                lines.append(op + ' ' + right)
        return lines


def _fmt(obj: El, length: Union[int, None], indent: str) -> list[str]:
    if obj is None:
        return []
    if isinstance(obj, str):
        return splitlines(obj)
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
        lines = [
            datafile.encode_quoted_string(line, escape_newlines=True)
            for line in splitlines(obj)
        ]
        if len(lines) > 1:
            return ['('] + [indent + line for line in lines] + [')']
        return lines
    return obj.fmt(length, indent, _fmt_quote)


def _fmt_single_line(
    obj: El, length: Union[int, None], indent: str, fmt_fn: _FmtFn
) -> Optional[str]:
    lines = fmt_fn(obj, length, indent)
    assert isinstance(lines, list)
    if len(lines) > 2 or (len(lines) == 2 and lines[1] != '\n'):
        return None

    assert (len(lines) == 1) or (len(lines) == 2 and lines[1] == "'\n'"), (
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
    return cls(*args)


def split_to_objs(s, indent):
    objs = []
    lines = splitlines(s)
    for line in lines:
        level = indent_level(line, indent)
        obj = line[len(indent) * level :]
        while level > 0:
            obj = Indent(obj)
            level -= 1
        objs.append(obj)
    return VList(objs)


def splitlines(s, skip_empty=False):
    if s == '':
        if skip_empty:
            return []
        return ['']
    if s == '\n':
        return ['']
    lines = []
    spl_lines = s.splitlines()
    for spl_line in spl_lines[:-1]:
        lines.append(spl_line)
    lines.append(spl_lines[-1])
    return lines


def _new_length(l1: Union[int, None], l2: int) -> Union[int, None]:
    return l1 if l1 is None else l1 - l2


def indent_level(obj, indent: str) -> int:
    if isinstance(obj, str):
        while obj.startswith(indent):
            return 1 + indent_level(obj[len(indent) :], indent)
    elif isinstance(obj, HList):
        return indent_level(obj.objs[0], indent)
    return 0


def _lines(objs):
    i = 0
    for obj in objs:
        if isinstance(obj, list):
            i += _lines(obj)
        elif isinstance(obj, FormatObj):
            i += _lines(obj.objs)
        else:
            i += 1
    return i
