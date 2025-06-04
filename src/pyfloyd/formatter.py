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
from typing import Any, Callable, Optional, Union

from pyfloyd import datafile


El = Union[str, 'FormatObj', None]
_Len = Union[int, None]
_FmtFn = Callable[[El, '_FmtParams'], list[str]]


class _FmtParams:
    cur_len: _Len
    max_len: _Len
    indent: str
    fn: _FmtFn

    def __init__(self, cur_len: _Len, max_len: _Len, indent: str, fn: _FmtFn):
        self.cur_len = cur_len
        self.max_len = max_len
        self.indent = indent
        self.fn = fn

    def shrink(self, ln: int, max_ln: int = 0) -> '_FmtParams':
        return self.adjust(
            _new_l(self.cur_len, ln),
            _new_l(self.max_len, max_ln),
        )

    def adjust(self, new_cur: _Len, new_max: _Len) -> '_FmtParams':
        return _FmtParams(new_cur, new_max, self.indent, self.fn)

    def fmt(self, obj):
        return self.fn(obj, self)


def flatten(
    obj: El,
    length: _Len = 79,
    indent: str = '    ',
) -> list[str]:
    """Returns an object formatted into a list of 1 or more strings.

    Each string must be shorter than `length` characters, if possible. If
    length is None, lines can be arbitrarily long.
    """
    p = _FmtParams(length, length, indent, _fmt)
    return p.fn(obj, p)


def flatten_as_lisplist(
    obj: El, length: _Len = 79, indent: str = '    '
) -> list[str]:
    """Returns an object formatted as a datafile-formatted representation of
    itself."""
    r_obj = to_lisplist(obj)
    p = _FmtParams(length, length, indent, _fmt_quote)
    return p.fmt(r_obj)


def _fmt(obj: El, p: _FmtParams) -> list[str]:
    if obj is None:
        return []
    if isinstance(obj, str):
        return splitlines(obj)
    return obj.fmt(p)


def _fmt_quote(obj: El, p: _FmtParams) -> list[str]:
    if obj is None:
        return []
    if isinstance(obj, str):
        lines = [
            datafile.encode_quoted_string(line, escape_newlines=True)
            for line in splitlines(obj)
        ]
        if len(lines) > 1:
            return ['('] + [p.indent + line for line in lines] + [')']
        return lines
    return obj.fmt(p)


def to_list(obj):
    """Returns a nested list of objects corresponding to the FormatObj."""
    if isinstance(obj, FormatObj):
        return obj.to_list()
    return obj


def to_lisplist(obj):
    """Returns a nested list of objects formatted with tags as bare words."""
    if isinstance(obj, FormatObj):
        return obj.to_lisplist()
    return obj


def from_list(obj: Any) -> Any:
    """Turns a list of objects into a recursively nested FormatObj."""
    if not isinstance(obj, list):
        return obj
    assert len(obj) >= 2, 'lists need at least two elements: {obj!r}'
    tag = obj[0]
    cls_map = _class_map()
    assert tag in cls_map, f'unknown list tag {tag}'
    args = []
    for ob in obj[1:]:
        arg = from_list(ob)
        args.append(arg)
    cls = cls_map[tag]
    return cls(*args)


def split_to_objs(s: str, indent: str) -> 'VList':
    objs = []
    lines = splitlines(s)
    for line in lines:
        level = indent_level(line, indent)
        obj: Union[Indent, str] = line[len(indent) * level :]
        while level > 0:
            obj = Indent(obj)
            level -= 1
        objs.append(obj)
    return VList(objs)


def splitlines(s: str) -> list[str]:
    if s == '':
        return ['']
    if s == '\n':
        return ['']
    lines = []
    spl_lines = s.splitlines()
    for spl_line in spl_lines[:-1]:
        lines.append(spl_line)
    lines.append(spl_lines[-1])
    return lines


def _new_l(l1: _Len, l2: int) -> _Len:
    return l1 if l1 is None else l1 - l2


def _fits(p: _FmtParams, s: str) -> bool:
    return p.cur_len is None or len(s) <= p.cur_len


def _fits_on_one(p, lines) -> bool:
    return not lines or (len(lines) == 1 and _fits(p, lines[0]))


def indent_level(s: str, indent: str) -> int:
    if indent == '':
        return 0
    i = 0
    j = 0
    ln = len(indent)
    while s[j : j + ln] == indent:
        i += 1
        j += ln
    return i


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


def _class_map():
    return {
        'comma': Comma,
        'hang': Hang,
        'hl': HList,
        'ind': Indent,
        'll': LispList,
        'saw': Saw,
        'tree': Tree,
        'tri': Triangle,
        'vl': VList,
        'wrap': Wrap,
    }


class FormatObj:
    tag: str = ''

    def __init__(self, *objs):
        self.objs = list(objs)

    def _optimize(self, objs, cls):
        objs = self._collapse(objs, cls)
        objs = self._simplify_hlists(objs)
        objs = self._merge_indents(objs)
        return objs

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
        return LispList(self.tag, *[to_lisplist(obj) for obj in self.objs])

    def is_empty(self):
        return len(self.objs) == 0

    def fmt(self, p: _FmtParams) -> list[str]:
        """Returns a list of strings, each representing a line."""
        raise NotImplementedError


class Comma(FormatObj):
    """Format a comma-separated list of arguments.

    If we need to format a list of arguments across multiple lines, we
    want each to appear on its own line with a trailing comma, even on
    the last line where the trailing comma is unnecessary.

    [comma]           = ''
    [comma a]         = 'a'
    [comma a b c ...] = 'a, b, c'
                      | '<i>a,'
                        '<i>b,'
                        '<i>c,'
    """

    tag = 'comma'

    def fmt(self, p: _FmtParams) -> list[str]:
        # single line
        if len(self.objs) == 0:
            return []
        if len(self.objs) == 1:
            # Don't want a comma after a single arg.
            return p.fmt(self.objs[0])

        lines = pack(p, self.objs, ', ')
        if _fits_on_one(p, lines):
            return lines
        lines = []
        for obj in self.objs:
            lines.extend(wrap(p, obj, '', '', '', ', '))
        return lines


class Hang(FormatObj):
    """Wrap a list of objects across multiple lines, separating them
    with a given separator.

    The second and subsequent lines will be indented to align with the
    *second* argument, e.g. .[foo bar baz] will format as

    [hang ' ']           = ''
    [hang ' ' a]         = 'a'
    [hang ' ' a b c ...] = 'a b c d'
                           '  d e f'
    """

    tag = 'hang'

    def fmt(self, p: _FmtParams) -> list[str]:
        objs = self.objs[0]
        sep = self.objs[1]
        if len(objs) == 0:
            return []
        first = p.fmt(objs[0])[0]
        if len(objs) == 1:
            return [first]
        first += sep
        prefix = ' ' * len(first)
        new_p = p.adjust(
            _new_l(p.cur_len, len(first)), _new_l(p.max_len, len(first))
        )
        rest = pack(new_p, objs[1:])
        return wrap(p, rest, prefix, '', first, '')


class HList(FormatObj):
    """Takes a list of objects and lays them out horizontally.

    The objects are considered to be atomic concatenated and will not be
    split by subsequent formatting, but any object that can be formatted
    multiple ways itself will be handled. If any object produces multiple
    lines, subsequent objects will be laid out on the same last line, e.g.:

    [hl a b [vl c d] e f]    = 'abc'
                               '  def'
    """

    tag = 'hl'

    def __init__(self, *objs):
        super().__init__()
        new_objs = self._collapse(objs, cls=self.__class__)
        self.objs = self._simplify_hlists(new_objs)

    def fmt(self, p: _FmtParams) -> list[str]:
        return horiz(p, self.objs)


class Indent(FormatObj):
    """Returns a list of objects laid out vertically, each line indented.

    [ind a b c] = '<i>a'
                  '<i>b'
                  '<i>c'
    """

    tag = 'ind'

    def __init__(self, *objs):
        super().__init__([])
        self.objs = self._optimize(objs, VList)

    def fmt(self, p: _FmtParams) -> list[str]:
        return wrap(p, self.objs, p.indent)


class LispList(FormatObj):
    """Format as a list, lisp-style.

    Across multiple lines, the second and subsequent lines will be
    indented to match the second argument to the list, and closing
    brackets will be on the last line:

    [ll a [ll b c d [ll e f] = '[a [b c d] [e f]]'
                             | '[a [b c'
                               '      d]'
                               '   [e f]]'
    """

    # TODO: Should this just be a flag on an existing class or classes,
    # rather than a separate class?

    tag = 'll'

    def __init__(self, *objs):
        super().__init__(*objs)
        if len(self.objs) > 0:
            assert isinstance(self.objs[0], str)

    def fmt(self, p: _FmtParams) -> list[str]:
        if len(self.objs) == 0:
            return ['[]']

        if len(self.objs) == 1:
            return ['[' + self.objs[0] + ']']

        first = '[' + self.objs[0] + ' '
        hang = ' ' * len(first)
        new_p = p.shrink(len(first) + 1)
        sub_lines = pack(new_p, self.objs[1:])
        if _fits_on_one(new_p, sub_lines):
            return [first + sub_lines[0] + ']']
        return wrap(new_p, vert(new_p, self.objs[1:]), hang, '', first, ']')


class Pack(FormatObj):
    """Formats a list of objects into one or more left-aligned rows.

    [pack a b c ..]      = 'a b c d e f'
                         | 'a b c'
                           'd e f'
    [pack a [vl b c] d]  = 'a b'
                           'c d'
    """

    tag = 'pack'

    def fmt(self, p: _FmtParams) -> list[str]:
        return pack(p, self.objs)


class Saw(FormatObj):
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
    ```

    where the unindented parts are all on a single line and the indented
    parts may be on one or more lines. We express this as one Saw object
    with an initial prefix + multiple Triangle objects.

    Note: this ends up formatting the same as `pack()`.
    """

    tag = 'saw'

    def __init__(self, *args):
        super().__init__(*args)
        assert len(args) > 1
        assert isinstance(args[0], (str, HList, Triangle))
        for arg in args[1:]:
            assert isinstance(arg, Triangle)

    def fmt(self, p: _FmtParams) -> list[str]:
        return pack(p, self.objs, '')


class Triangle(FormatObj):
    """Format a series of three objects.

    [tri a b c] = 'abc'
                | 'a'
                  '<ind>b'
                  'c'
    """

    tag = 'tri'

    def __init__(self, left, mid, right):
        super().__init__(left, mid, right)
        assert isinstance(self.objs[0], str)
        assert isinstance(self.objs[2], str)

    def fmt(self, p: _FmtParams) -> list[str]:
        lines = pack(p, self.objs, '')
        if _fits_on_one(p, lines):
            return lines

        new_p = p.adjust(p.max_len, p.max_len)
        return vert(
            p,
            [self.objs[0]]
            + wrap(new_p, self.objs[1], new_p.indent)
            + [self.objs[2]],
        )


class Tree(FormatObj):
    """Formats a call or dereference.

    Given an expression like '(foo)' or '[bar]', where there's a starting
    and ending string and a possibly more complex object in the middle,
    formats these thing over possibly multiple lines.

    tree [a b [tree c d e]]  = 'a b c d e'
                             | 'a'
                               'b c'
                               'd e'

    This gets its own format rule because the trees may be recursive
    and yet need to be formatted as one thing.
    """

    tag = 'tree'

    def __init__(self, left, op, right):
        super().__init__(left, op, right)
        assert left is not None or right is not None
        assert isinstance(op, str)

    def fmt(self, p: _FmtParams) -> list[str]:
        lines = pack(p, self.objs, ' ')
        if _fits_on_one(p, lines):
            return lines
        return vtree(p, self)


class VList(FormatObj):
    """Takes a list of objects and lays them out vertically.

    [vl a b c ...]  = 'a'
                      'b'
                      'c'
    """

    tag = 'vl'

    def __init__(self, *objs):
        super().__init__()
        self.objs = self._optimize(objs, self.__class__)

    def __iadd__(self, obj):
        self.objs.extend(self._optimize([obj], self.__class__))
        return self

    def fmt(self, p: _FmtParams) -> list[str]:
        return vert(p, self.objs)


class Wrap(FormatObj):
    """Wraps an object with text on both sides.

    It takes an object and four parameters: the text to use as a prefix on
    most lines, the text to use as a suffix on most lines, the text to use
    as a prefix on just the first line, and the text to use as the suffix
    on the last line. The two prefix strings must be the same length.
    The two suffix strings may be different lengths. Any trailing whitespace
    will be stripped.

    [wrap a b c d [vl e f g]  = 'ceb'
                                'afb'
                                'agd'
    """

    tag = 'wrap'

    def __init__(self, *objs):
        super().__init__(*objs)
        assert len(objs) == 5

    def fmt(self, p: _FmtParams) -> list[str]:
        obj, prefix, suffix, first, last = self.objs
        return wrap(p, obj, prefix, suffix, first, last)


def flatten_objs(obj: Any, lis: Optional[list[Any]] = None):
    """Returns a single list of objects from a list of objects and lists."""
    lis = [] if lis is None else lis
    if isinstance(obj, list):
        for el in obj:
            flatten_objs(el, lis)
    else:
        lis.append(obj)
    return lis


def horiz(p: _FmtParams, objs: list[El]) -> list[str]:
    """Lay out objects horizontally."""
    lines: list[str] = []
    if len(objs) == 0:
        return ['']

    lines = ['']
    new_p = p.shrink(0)
    for obj in objs:
        if obj is None:
            continue
        if isinstance(obj, str):
            lines[-1] += obj
        else:
            ind = len(lines[-1])
            new_p = p.adjust(
                _new_l(p.cur_len, len(lines[-1])),
                _new_l(p.max_len, len(lines[-1])),
            )
            sublines = new_p.fmt(obj)
            if sublines:
                lines[-1] += sublines[0]
                if len(sublines) > 1:
                    lines.extend((' ' * ind) + line for line in sublines[1:])
    return lines


def vert(p: _FmtParams, objs: list[El]) -> list[str]:
    """Lay out objects vertically"""
    lines = []
    for obj in flatten_objs(objs):
        lines.extend(p.fmt(obj))
    return lines


def pack(p: _FmtParams, objs: list[FormatObj], sep: str = ' ') -> list[str]:
    """Lay out objects packed across multiple lines"""
    if len(objs) == 0:
        return []
    lines = p.fmt(objs[0])
    new_p = p
    for sub_obj in objs[1:]:
        if lines:
            lines[-1] += sep
            new_p = p.shrink(len(lines[-1]))
        sl = new_p.fmt(sub_obj)
        if not sl:
            continue
        if _fits(new_p, sl[0]):
            if lines:
                lines[-1] += sl[0]
                lines.extend(sl[1:])
            else:
                lines = sl
        else:
            lines.extend(sl)
    return lines


def vtree(p: _FmtParams, t: El):
    """Lay out objects as per Tree()."""
    if t is None:
        return []
    if isinstance(t, str):
        return [t]
    assert isinstance(t, Tree)
    left, op, right = t.objs[0], t.objs[1], t.objs[2]
    if left is None:
        lines = []
    else:
        lines = vtree(p, left)
    if right is None:
        lines[-1].append(' ' + op)
        return lines
    sub_lines = vtree(p, right)
    lines.append(op + ' ' + sub_lines[0])
    lines.extend(sub_lines[1:])
    return lines


def wrap(
    p: _FmtParams,
    objs: list[El],
    prefix: str = '',
    suffix: str = '',
    first: Optional[str] = None,
    last: Optional[str] = None,
) -> list[str]:
    """Wraps a list of objects in text."""
    first = first or prefix
    last = last or suffix
    assert len(first) == len(prefix)
    dist = len(prefix) + max(len(suffix), len(last))
    new_p = p.shrink(dist, dist)

    new_objs = flatten_objs(objs)
    sub_lines = []
    for obj in new_objs:
        sub_lines.extend(new_p.fmt(obj))

    lines = []
    if len(sub_lines) == 1:
        lines = [first + sub_lines[0] + last]
    elif len(sub_lines) > 1:
        lines.append(first + sub_lines[0] + suffix)
        for sl in sub_lines[1:-1]:
            lines.append(prefix + sl + suffix)
        lines.append(prefix + sub_lines[-1] + last)
    return [line.rstrip() for line in lines]
