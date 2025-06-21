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

import abc
import copy
from typing import Any, Callable, Optional, Sequence, Tuple, Union

from pyfloyd import datafile


El = Union[str, 'FormatObj', None]
_FmtFn = Callable[[El, '_FmtParams'], list[str]]


class _FmtParams:
    cur_len: int  # Amount remaining on current line
    max_len: int  # Max amount remaining for any line
    indent: str
    fn: _FmtFn

    def __init__(self, cur_len: int, max_len: int, indent: str, fn: _FmtFn):
        self.cur_len = cur_len
        self.max_len = max_len
        self.indent = indent
        self.fn = fn

    def shrink(self, ln: int, max_ln: int = 0) -> '_FmtParams':
        return self.adjust(self.cur_len - ln, self.max_len - max_ln)

    def adjust(self, new_cur: int, new_max: int) -> '_FmtParams':
        return _FmtParams(new_cur, new_max, self.indent, self.fn)

    def fmt(self, obj):
        return self.fn(obj, self)


def flatten(
    obj: El,
    length: Optional[int] = 79,
    indent: str = '    ',
) -> list[str]:
    """Returns an object formatted into a list of 1 or more strings.

    Each string must be shorter than `length` characters, if possible. If
    length is None, lines can be arbitrarily long.
    """
    if length is None:
        length = 2**32 - 1
    p = _FmtParams(length, length, indent, _fmt)
    lines = p.fn(obj, p)
    return lines


def flatten_as_lisplist(
    obj: El, length: Optional[int] = 79, indent: str = '    '
) -> list[str]:
    """Returns an object formatted as a datafile-formatted representation of
    itself."""
    if length is None:
        length = 2**32 - 1

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


def _fits(el: El, remaining: int, indent: str) -> Tuple[bool, int]:
    if el is None:
        return True, remaining
    if isinstance(el, str):
        ln = len(el)
        if ln <= remaining:
            return True, remaining - ln
        return False, -1
    return el.fits(remaining, indent)


def _objs_fit_on_one(
    objs: list[El], sep: str, remaining: int, indent: str
) -> Tuple[bool, int]:
    if not objs:
        return True, remaining
    for obj in objs[:-1]:
        fit, remaining = _fits(obj, remaining, indent)
        if not fit:
            return False, -1
        remaining -= len(sep)
        if remaining is not None and remaining < 0:
            return False, -1
    return _fits(objs[-1], remaining, indent)


def _lines_fit_on_one(lines, remaining: int) -> bool:
    if lines is None or len(lines) > 1:
        return False
    if lines == []:
        return True
    return _fits(lines[0], remaining, '')[0]


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
        'tree': Tree,
        'tri': Triangle,
        'vl': VList,
        'wrap': Wrap,
    }


objects = []

func_stats = {
    'horiz': 0,
    'vert': 0,
    'pack': 0,
    'vtree': 0,
    'wrap': 0,
}


class FormatObj(abc.ABC):
    tag: str = ''
    maybe_has_single_format = False

    def __init__(self, *objs):
        self.objs = list(objs)
        self.cache = {}  # dict[cur_len, lines]
        self.results: list[list[str]] = []
        self._single_format: Optional[bool] = None

        # Note that while we track if some objects might have multiple
        # results even if all of their children don't, we don't attempt
        # to optimize cachng for that case; at least some stats
        # gathering suggests that nearly all such objects are only
        # ever formatted once, and it doesn't happen w/ Floyd's own grammars
        # (although it does in formatter_test*test_hang).
        self._objs_all_single_format = all(
            _has_single_format(obj) for obj in self.objs
        )

        # Performance statistics
        objects.append(self)
        self.index = len(objects) - 1
        self.n_fmts = 0
        self.n_calcs = 0
        self.n_fmts_by_len = {}
        self.n_calcs_by_len = {}

    def has_single_format(self):
        if self._single_format is not None:
            return self._single_format

        if len(self.objs) in (0, 1) or self.maybe_has_single_format:
            self._single_format = self._objs_all_single_format
        else:
            self._single_format = False

        return self._single_format

    def fmt(self, p: _FmtParams) -> list[str]:
        """Returns a list of strings, each representing a line."""

        # This routine is a place for logic common to all format objects;
        # currently it just manages performance statistics and a cache
        # of results. The actual formatting is done in _fmt().
        p_key = (p.cur_len, p.max_len)
        self.n_fmts += 1
        self.n_fmts_by_len.setdefault(p_key, 0)
        self.n_fmts_by_len[p_key] += 1
        if self.has_single_format() and self.results:
            return self.results[0]

        for cache_key in sorted(self.cache.keys(), reverse=True):
            result = self.results[self.cache[cache_key]]
            if len(result) == 1 and len(result[0]) < p.cur_len:
                return result
            if cache_key == p_key:
                return result
        self.n_calcs += 1
        self.n_calcs_by_len.setdefault(p_key, 0)
        self.n_calcs_by_len[p_key] += 1
        lines = self._fmt(p)
        for i, result in enumerate(self.results):
            if lines == result:
                self.cache[p_key] = i
                return lines
        self.results.append(lines)
        self.cache[p_key] = len(self.results) - 1
        return lines

    @abc.abstractmethod
    def _fmt(self, p: _FmtParams) -> list[str]:
        # Put the actual format implementation here.
        raise NotImplementedError

    def fits(self, remaining: int, indent: str) -> Tuple[bool, int]:
        """Returns whether the object will fit on one line with the
        remaining space and, if so, how much space will remain."""
        raise NotImplementedError

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

    def _fmt(self, p: _FmtParams) -> list[str]:
        if len(self.objs) == 0:
            return []

        if len(self.objs) == 1:
            # Don't want a comma after a single arg.
            return p.fmt(self.objs[0])

        if _objs_fit_on_one(self.objs, ', ', p.cur_len, p.indent)[0]:
            return pack(p, self.objs, ', ')

        lines: list[str] = []
        for obj in self.objs:
            lines = lines + wrap(p, obj, '', '', '', ', ')
        return lines

    def fits(self, remaining: int, indent: str) -> Tuple[bool, int]:
        return _objs_fit_on_one(self.objs, ', ', remaining, indent)


class Hang(FormatObj):
    """Wrap a list of objects across multiple lines, separating them
    with a given separator.

    The second and subsequent lines will be indented to align with the
    *second* argument, e.g. .[foo bar baz] will format as

    [hang [] ' ']           = ''
    [hang [a] ' ']          = 'a'
    [hang [a b c ...] ' ' ] = 'a b c d'
                              '  d e f'
    """

    tag = 'hang'

    def __init__(self, objs, sep):
        super().__init__(*objs)
        self.sep = sep

    def _fmt(self, p: _FmtParams) -> list[str]:
        objs = self.objs
        sep = self.sep

        if len(objs) == 0:
            return []

        first = p.fmt(objs[0])[0]
        if len(objs) == 1:
            return [first]

        if _objs_fit_on_one(objs, sep, p.cur_len, p.indent)[0]:
            return pack(p, objs, sep)

        first += sep
        prefix = ' ' * len(first)
        new_p = p.adjust(p.cur_len - len(first), p.max_len - len(first))
        return wrap(p, pack(new_p, objs[1:]), prefix, '', first, '')

    def fits(self, remaining: int, indent: str) -> Tuple[bool, int]:
        return _objs_fit_on_one(self.objs, self.sep, remaining, indent)


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
    maybe_has_single_format = True

    def __init__(self, *objs):
        super().__init__(*_simplify_hlists(_collapse(objs, self.__class__)))

    def _fmt(self, p: _FmtParams) -> list[str]:
        return horiz(p, self.objs)

    def fits(self, remaining: int, indent: str) -> Tuple[bool, int]:
        return _objs_fit_on_one(self.objs, '', remaining, indent)


class Indent(FormatObj):
    """Returns a list of objects laid out vertically, each line indented.

    [ind a b c] = '<i>a'
                  '<i>b'
                  '<i>c'
    """

    tag = 'ind'
    maybe_has_single_format = True

    def __init__(self, *objs):
        super().__init__(*_optimize(objs, VList))

    def _fmt(self, p: _FmtParams) -> list[str]:
        return wrap(p, self.objs, p.indent)

    def fits(self, remaining: int, indent: str) -> Tuple[bool, int]:
        remaining -= len(indent)
        remains = []
        for obj in self.objs:
            fit, new_remaining = _fits(obj, remaining, indent)
            if not fit:
                return False, -1
            remains.append(new_remaining)
        return True, min(remains)


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

    def _fmt(self, p: _FmtParams) -> list[str]:
        if len(self.objs) == 0:
            return ['[]']

        if len(self.objs) == 1:
            return ['[' + self.objs[0] + ']']

        first = '[' + self.objs[0] + ' '
        hang = ' ' * len(first)
        new_p = p.shrink(len(first) + 1)
        sub_lines = pack(new_p, self.objs[1:])
        if _lines_fit_on_one(sub_lines, new_p.cur_len):
            return [first + sub_lines[0] + ']']
        return wrap(new_p, vert(new_p, self.objs[1:]), hang, '', first, ']')

    def fits(self, remaining: int, indent: str) -> Tuple[bool, int]:
        remaining -= 2  # account for '[' and ']'
        if remaining < 0:
            return False, -1
        return _objs_fit_on_one(self.objs, ' ', remaining, indent)


class Pack(FormatObj):
    """Formats a list of objects into one or more left-aligned rows.

    [pack a b c ..]      = 'abcdef'
                         | 'abc'
                           'def'
    [pack a [vl b c] d]  = 'ab'
                           'cd'
    """

    tag = 'pack'

    def _fmt(self, p: _FmtParams) -> list[str]:
        return pack(p, self.objs, sep='')

    def fits(self, remaining: int, indent: str) -> Tuple[bool, int]:
        return _objs_fit_on_one(self.objs, '', remaining, indent)


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

    def _fmt(self, p: _FmtParams) -> list[str]:
        lines = pack(p, self.objs, '')
        if _lines_fit_on_one(lines, p.cur_len):
            return lines

        new_p = p.adjust(p.max_len, p.max_len)
        return vert(
            p,
            [self.objs[0]]
            + wrap(new_p, self.objs[1], new_p.indent)
            + [self.objs[2]],
        )

    def fits(self, remaining: int, indent: str) -> Tuple[bool, int]:
        return _objs_fit_on_one(self.objs, '', remaining, indent)


class Tree(FormatObj):
    """Formats a call or dereference.

    Given an expression like '(foo)' or '[bar]', where there's a starting
    and ending string and a possibly more complex object in the middle,
    formats these thing over possibly multiple lines.

    tree [a b [tree c d e]]  = 'abcde'
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

    def _fmt(self, p: _FmtParams) -> list[str]:
        if self.objs[0] is None:
            lines = pack(p, self.objs, '')
        else:
            lines = pack(p, self.objs, ' ')
        if _lines_fit_on_one(lines, p.cur_len):
            return lines
        return vtree(p, self)

    def fits(self, remaining: int, indent: str) -> Tuple[bool, int]:
        return _objs_fit_on_one(self.objs, '', remaining, indent)


class VList(FormatObj):
    """Takes a list of objects and lays them out vertically.

    [vl a b c ...]  = 'a'
                      'b'
                      'c'
    """

    tag = 'vl'
    maybe_has_single_format = True

    def __init__(self, *objs):
        super().__init__(*_optimize(objs, self.__class__))

    def __iadd__(self, obj):
        self.objs.extend(_optimize([obj], self.__class__))
        self._single_format = None
        self.results = []
        self.cache = {}
        return self

    def _fmt(self, p: _FmtParams) -> list[str]:
        return vert(p, self.objs)

    def fits(self, remaining: int, indent: str) -> Tuple[bool, int]:
        remains = []
        for obj in self.objs:
            fits, new_remaining = _fits(obj, remaining, indent)
            if not fits:
                return False, -1
            remains.append(new_remaining)
        return True, min(remains)


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

    def _fmt(self, p: _FmtParams) -> list[str]:
        obj, prefix, suffix, first, last = self.objs
        return wrap(p, obj, prefix, suffix, first, last)

    def fits(self, remaining: int, indent: str) -> Tuple[bool, int]:
        objs, prefix, suffix, first, last = self.objs
        remains = []
        if objs is None or len(objs) == 0:
            return True, remaining
        if len(objs) == 1:
            remaining -= len(first) + len(last)
            if remaining < 0:
                return False, -1
            return True, remaining
        fit, new_remaining = _fits(
            objs[0], remaining - len(first) - len(suffix), indent
        )
        if not fit:
            return False, -1
        remains.append(new_remaining)
        for obj in objs[1:-1]:
            fit, new_remaining = _fits(
                obj, remaining - len(prefix) - len(suffix), indent
            )
            if not fit:
                return False, -1
            remains.append(new_remaining)
        fit, new_remaining = _fits(
            objs[-1], remaining - len(prefix) - len(last), indent
        )
        if not fit:
            return False, -1
        remains.append(new_remaining)
        return True, min(remains)


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
    func_stats['horiz'] += 1

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
            new_p = p.shrink(ind, ind)
            sublines = new_p.fmt(obj)
            if sublines:
                lines[-1] += sublines[0]
                if len(sublines) > 1:
                    lines = lines + [
                        (' ' * ind) + line for line in sublines[1:]
                    ]
    return lines


def vert(p: _FmtParams, objs: list[El]) -> list[str]:
    """Lay out objects vertically"""
    func_stats['vert'] += 1

    lines: list[str] = []
    for obj in flatten_objs(objs):
        lines = lines + p.fmt(obj)
    return lines


def pack(p: _FmtParams, objs: list[FormatObj], sep: str = ' ') -> list[str]:
    """Lay out objects packed across multiple lines"""
    func_stats['pack'] += 1

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
        fit, remaining = _fits(sl[0], new_p.cur_len, new_p.indent)
        if fit:
            if lines:
                lines[-1] += sl[0]
                lines = lines + sl[1:]
            else:
                lines = sl
        else:
            lines = lines + sl
    return lines


def vtree(p: _FmtParams, t: El):
    """Lay out objects as per Tree()."""
    func_stats['vtree'] += 1

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
    if left is None:
        lines.append(op + sub_lines[0])
    else:
        lines.append(op + ' ' + sub_lines[0])
    lines.extend(sub_lines[1:])
    return lines


def wrap(
    p: _FmtParams,
    objs: Sequence[El],
    prefix: str = '',
    suffix: str = '',
    first: Optional[str] = None,
    last: Optional[str] = None,
) -> list[str]:
    """Wraps a list of objects in text."""
    func_stats['wrap'] += 1

    first = first or prefix
    last = last or suffix
    assert len(first) == len(prefix)
    dist = len(prefix) + max(len(suffix), len(last))
    new_p = p.shrink(dist, dist)

    new_objs = flatten_objs(objs)
    sub_lines: list[str] = []
    for obj in new_objs:
        sub_lines = sub_lines + new_p.fmt(obj)

    lines = []
    if len(sub_lines) == 1:
        lines = [first + sub_lines[0] + last]
    elif len(sub_lines) > 1:
        lines.append(first + sub_lines[0] + suffix)
        for sl in sub_lines[1:-1]:
            lines.append(prefix + sl + suffix)
        lines.append(prefix + sub_lines[-1] + last)
    return [line.rstrip() for line in lines]


def _optimize(objs, cls):
    objs = _collapse(objs, cls)
    objs = _simplify_hlists(objs)
    objs = _merge_indents(objs)
    return objs


def _collapse(objs, cls):
    if objs is None:
        return []
    new_objs = []
    for obj in objs:
        if obj is None:
            continue
        if obj.__class__ == cls:
            new_objs.extend(_collapse(obj.objs, cls))
        elif isinstance(obj, list):
            new_objs.extend(_collapse(obj, cls))
        else:
            new_objs.append(obj)
    return new_objs


def _simplify_hlists(objs):
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


def _merge_indents(objs):
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


def _has_single_format(obj):
    if obj is None or isinstance(obj, str):
        return True
    return obj.has_single_format()
