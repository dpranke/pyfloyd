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

import collections
import math
import re

from typing import (
    Any,
    Callable,
    IO,
    Iterable,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

from . import parser


_bare_word_re = re.compile(r'^[^\\\s\[\]\(\)\{\}:\'"`]+$')

_long_str_re = re.compile(r"^l'=+'")


def load(
    fp: IO,
    *,
    encoding: Optional[str] = None,
    cls: Any = None,
    object_hook: Optional[Callable[[Mapping[str, Any]], Any]] = None,
    parse_number: Optional[Callable[[str], Any]] = None,
    parse_numword: Optional[Callable[[str], Any]] = None,
    object_pairs_hook: Optional[
        Callable[[Iterable[Tuple[str, Any]]], Any]
    ] = None,
    allow_trailing: bool = False,
    allow_numwords: bool = False,
    start: Optional[int] = None,
) -> Any:
    """Deserialize ``fp`` (a ``.read()``-supporting file-like object
    containing a Floyd datafile) to a Python object.

    Supports almost the same arguments as ``json.load()`` except that:
        - the `cls` keyword is ignored.
        - an extra `allow_trailing` parameter specifies whether parsing
          should stop after a value and any trailing filler has been
          reached. By default, this is `False`, and it is illegal for
          there to be trailing content after a value (i.e., you must
          be at the end of the string). If this is set to `True`, then
          parsing stops without error if trailing content is reached.
        - an extra `start` parameter specifies the zero-based offset into the
          file to start parsing at. If `start` is None, parsing will
          start at the current position in the file, and line number
          and column values will be reported as if starting from the
          beginning of the file; If `start` is not None,
          `load` will seek to zero and then read (and discard) the
          appropriate number of characters before beginning parsing;
          the file must be seekable for this to work correctly.

    You can use `load(..., allow_trailing=True)` to repeatedly read
    values from a file. However, in the current implementation `load` does
    this by reading the entire file into memory before doing anything, so
    it is not very efficient.

    Args:
      fp: A file-like object to read the document from.
      encoding: the encoding to use to decode the bytes from `fp`.
      cls: ignored. Present for compatibility with `json.load()`.

    Raises:
      TypeError: if given an invalid document.
      ValueError: if given an invalid document.
      UnicodeDecodeError: if given a byte string that is not a
          legal UTF-8 document (or the equivalent, if using a different
          `encoding`). This matches the `json` module.
    """

    s = fp.read()
    val, err, _ = parse(
        s,
        encoding=encoding,
        cls=cls,
        object_hook=object_hook,
        parse_number=parse_number,
        parse_numword=parse_numword,
        object_pairs_hook=object_pairs_hook,
        allow_trailing=allow_trailing,
        allow_numwords=allow_numwords,
        start=start,
    )
    if err:
        raise ValueError(err)
    return val


def loads(
    s: str,
    *,
    encoding: Optional[str] = None,
    cls: Any = None,
    object_hook: Optional[Callable[[Mapping[str, Any]], Any]] = None,
    parse_number: Optional[Callable[[str], Any]] = None,
    parse_numword: Optional[Callable[[str], Any]] = None,
    object_pairs_hook: Optional[
        Callable[[Iterable[Tuple[str, Any]]], Any]
    ] = None,
    allow_trailing: bool = False,
    allow_numwords: bool = False,
    start: Optional[int] = None,
):
    """Deserialize ``s`` (a string containing a Floyd datafile) to a Python
    object.

    Supports the same arguments as ``json.load()`` except that:
        - the `cls` keyword is ignored.
        - an extra `allow_trailing` parameter specifies whether parsing
          should stop after a value and any trailing filler has been
          reached. By default, this is `False`, and it is illegal for
          there to be trailing content after a value (i.e., you must
          be at the end of the string). If this is set to `True`, then
          parsing stops without error if trailing content is reached.
          This is not as useful here as it is in `load()` and `parse()`,
          as the stopping point is not returned to the caller. However,
          it can be used just as a form of robustness if desired.
        - an extra `start` parameter specifies the zero-based offset into the
          string to start parsing at.

    Raises
        - `TypeError` if given an invalid document.
        - `ValueError` if given an invalid document.
        - `UnicodeDecodeError` if given a byte string that is not a
          legal UTF-8 document (or the equivalent, if using a different
          `encoding`). This matches the `json` module.
    """

    val, err, _ = parse(
        s=s,
        encoding=encoding,
        cls=cls,
        object_hook=object_hook,
        parse_number=parse_number,
        parse_numword=parse_numword,
        object_pairs_hook=object_pairs_hook,
        allow_trailing=allow_trailing,
        allow_numwords=allow_numwords,
        start=start,
    )
    if err:
        raise ValueError(err)
    return val


def parse(
    s: str,
    *,
    encoding: Optional[str] = None,
    cls: Any = None,
    object_hook: Optional[Callable[[Mapping[str, Any]], Any]] = None,
    parse_number: Optional[Callable[[str], Any]] = None,
    parse_numword: Optional[Callable[[str], Any]] = None,
    object_pairs_hook: Optional[
        Callable[[Iterable[Tuple[str, Any]]], Any]
    ] = None,
    allow_trailing: bool = False,
    allow_numwords: bool = False,
    start: Optional[int] = None,
):
    """Parse ```s``, returning positional information along with a value.

    This works exactly like `loads()`, except that the return value is
    different (see below). `parse()` is useful if you have a string that
    might contain multiple values and you need to extract all of them;
    you can do so by repeatedly calling `parse`, setting `start` to the
    value returned in `position` from the previous call (see the example below).

    Returns:
      A tuple of (value, error_string, position). If the string
      was a legal value, `value` will be the deserialized value,
      `error_string` will be `None`, and `position` will be one
      past the zero-based offset where the parser stopped reading.
      If the string was not a legal value,
      `value` will be `None`, `error_string` will be the string value
      of the exception that would've been raised, and `position` will
      be the zero-based farthest offset into the string where the parser
      hit an error.

    Raises:
      UnicodeDecodeError: if given a byte string that is not a
        legal UTF-8 document (or the equivalent, if using a different
        `encoding`). This matches the `json` module.

    Note that this does *not* raise a `ValueError`; instead any error is
    returned as the second value in the tuple.

    You can use this method to read in a series of values from a string
    `s` as follows:

        >>> import floyd_datafile
        >>> s = '1 2 3 4'
        >>> values = []
        >>> start = 0
        >>> while True:
        ...     v, err, pos = floyd_datafile.parse(s, start=start,
        ...                                        allow_trailing=True)
        ...     if v:
        ...         values.append(v)
        ...         start = pos
        ...         if start == len(s) or s[start:].isspace():
        ...             # Reached the end of the string (ignoring trailing
        ...             # whitespace
        ...             break
        ...         continue
        ...     raise ValueError(err)
        >>> values
        [1, 2, 3, 4]

    """
    assert cls is None, 'Custom decoders are not supported'

    if isinstance(s, bytes):
        encoding = encoding or 'utf-8'
        s = s.decode(encoding)

    if not s:
        raise ValueError('Empty strings are not legal Floyd datafiles')
    start = start or 0
    externs = {
        'allow_trailing': allow_trailing,
        'allow_numwords': allow_numwords,
    }
    ast, err, pos = parser.parse(s, '<string>', externs)
    if err:
        return None, err, pos

    value = _convert(
        ast,
        object_hook=object_hook,
        parse_number=parse_number,
        parse_numword=parse_numword,
        object_pairs_hook=object_pairs_hook,
    )
    return value, None, pos


def _convert(
    ast,
    object_hook,
    parse_number,
    parse_numword,
    object_pairs_hook,
):
    def _dictify(pairs):
        keys = set()
        key_pairs = []
        for key_ast, val in pairs:
            _, tag, s = key_ast
            key = _decode_str(s, 'r' in tag, 'd' in tag)
            if key in keys:
                raise ValueError(f'Duplicate key "{key}" found in object')
            keys.add(key)
            key_pairs.append((key, val))

        if object_pairs_hook:
            return object_pairs_hook(key_pairs)
        if object_hook:
            return object_hook(dict(key_pairs))
        return dict(key_pairs)

    return _walk_ast(
        ast,
        _dictify,
        parse_number or _decode_number,
        parse_numword or _decode_numword,
    )


def _decode_number(v):
    s = v.replace('_', '')
    if s.startswith('0x'):
        return int(s, base=16)
    if s.startswith('0b'):
        return int(s, base=2)
    if s.startswith('0o'):
        return int(s, base=8)
    if '.' in s or 'e' in s or 'E' in s:
        return float(s)
    return int(s)


def _decode_numword(v):
    return v


def _decode_str(s, is_rstr, is_dstr):
    i = 0
    ret = []
    while i < len(s):
        if s[i] == '\\' and not is_rstr:
            i, c = _decode_escape(s, i)
            ret.append(c)
        else:
            ret.append(s[i])
            i += 1
    if is_dstr:
        return dedent(''.join(ret))
    return ''.join(ret)


def _decode_escape(s, i):
    c = s[i + 1]
    if c == 'n':
        return i + 2, '\n'
    if c == 't':
        return i + 2, '\t'
    if c == 'r':
        return i + 2, '\r'
    if c == 'b':
        return i + 2, '\b'
    if c == 'f':
        return i + 2, '\f'
    if c == 'a':
        return i + 2, '\a'
    if c == 'v':
        return i + 2, '\v'
    if c == "'":
        return i + 2, "'"
    if c == '"':
        return i + 2, '"'
    if c == '`':
        return i + 2, '`'
    if c == 'x':
        if _check(s, i + 2, 2, _ishex):
            return i + 4, chr(int(s[i + 2 : i + 4], base=16))
    if c == 'u':
        if _check(s, i + 2, 4, _ishex):
            return i + 6, chr(int(s[i + 2 : i + 6], base=16))
    if c == 'U':
        if _check(s, i + 2, 8, _ishex):
            return i + 10, chr(int(s[i + 2 : i + 10], base=16))
    if len(s) > i + 1 and _isoct(s[i + 1]):
        x = int(s[i + 1], base=8)
        j = 2
        if len(s) > i + 2 and _isoct(s[i + 2]):
            x = x * 8 + int(s[i + 2], base=8)
            j += 1
        if len(s) > i + 3 and _isoct(s[i + 3]):
            x = x * 8 + int(s[i + 2], base=8)
            j += 1
        return j, chr(x)
    raise ValueError(f'Bad escape in str {repr(s)} at pos {i}')


def _check(s, i, n, fn):
    if len(s) < i + n:
        return False
    return all(fn(s[j]) for j in range(i, i + n))


def _ishex(ch):
    return ch in '0123456789abcdefABCDEF'


def _isoct(ch):
    return '0' <= ch <= '7'


def dedent(s):
    # TODO: Figure out what to do with tabs and other non-space whitespace.

    def _indent(s):
        i = 0
        while i < len(s) and s[i] == ' ':
            i += 1
        return i

    lines = s.splitlines()
    if len(lines) < 2:
        return s

    line0 = lines[0]
    min_indent = min(_indent(line) for line in lines[1:])
    if line0.strip():
        r = line0 + '\n'
    else:
        r = ''
    return r + '\n'.join(line[min_indent:] for line in lines[1:]) + '\n'


def _walk_ast(
    el,
    dictify: Callable[[Iterable[Tuple[str, Any]]], Any],
    parse_number,
    parse_numword,
):
    ty, tag, v = el
    if ty == 'true':
        return True
    if ty == 'false':
        return False
    if ty == 'null':
        return None
    if ty == 'number':
        return parse_number(v)
    if ty == 'numword':
        return parse_numword(v)
    if ty == 'string':
        return _decode_str(v, 'r' in tag, 'd' in tag)
    if ty == 'string_list':
        r = [_walk_ast(el, dictify, parse_number, parse_numword) for el in v]
        return ''.join(r)
    if ty == 'object':
        pairs = []
        for key, val_expr in v:
            val = _walk_ast(val_expr, dictify, parse_number, parse_numword)
            pairs.append((key, val))
        return dictify(pairs)
    if ty == 'array':
        return [
            _walk_ast(el, dictify, parse_number, parse_numword) for el in v
        ]
    raise ValueError('unknown el: ' + el)  # pragma: no cover


def dump(
    obj: Any,
    fp: IO,
    *,
    ensure_ascii: bool = True,
    cls: Optional[Type['Encoder']] = None,
    indent: Optional[Union[int, str]] = None,
    separators: Optional[Tuple[str, str]] = None,
    default: Optional[Callable[[Any], Any]] = None,
    sort_keys: bool = False,
    **kw,
):
    """Serialize ``obj`` as datafile to ``fp``,
    a ``.write()``-supporting file-like object.

    Supports the same arguments as ``dumps()``, below.
    """

    fp.write(
        dumps(
            obj=obj,
            ensure_ascii=ensure_ascii,
            cls=cls,
            indent=indent,
            separators=separators,
            default=default,
            sort_keys=sort_keys,
            **kw,
        )
    )


def dumps(
    obj: Any,
    *,
    ensure_ascii: bool = True,
    cls: Optional[Type['Encoder']] = None,
    indent: Optional[Union[int, str]] = None,
    separators: Optional[Tuple[str, str]] = None,
    default: Optional[Callable[[Any], Any]] = None,
    sort_keys: bool = False,
    **kw,
):
    """Serialize ``obj`` as a datafile to a string.

    Other keyword arguments are allowed and will be passed to the
    encoder so custom encoders can get them, but otherwise they will
    be ignored in an attempt to provide some amount of forward-compatibility.

    For example:

    ```
    >>> import floyd_datafile
    >>> from typing import Any, Set
    >>>
    >>> class Hex(int):
    ...    def __repr__(self):
    ...        return hex(self)
    >>>
    >>> class CustomEncoder(floyd_datafile.Encoder):
    ...    def encode(
    ...        self, obj: Any, seen: Set, level: int, *, as_key: bool
    ...    ) -> str:
    ...        if isinstance(obj, Hex):
    ...            return repr(obj)
    ...        return super().encode(obj, seen, level, as_key=as_key)
    ...
    >>> floyd_datafile.dumps([20, Hex(20)], cls=CustomEncoder)
    '[20, 0x14]'

    ```

    """

    cls = cls or Encoder
    enc = cls(
        ensure_ascii=ensure_ascii,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        **kw,
    )
    return enc.encode(obj, seen=set(), level=0, as_key=False)


class Encoder:
    """A class that can customize the behavior of `dumps`."""

    def __init__(
        self,
        *,
        ensure_ascii: bool = True,
        indent: Optional[Union[int, str]] = None,
        separators: Optional[Tuple[str, str]] = None,
        default: Optional[Callable[[Any], Any]] = None,
        sort_keys: bool = False,
        **kw,
    ):
        """Provides a class that may be overridden to customize the behavior
        of `dumps()`. The keyword args are the same as for that function.
        *Added in version 0.10.0"""
        # Ignore unrecognized keyword arguments in the hope of providing
        # some level of backwards- and forwards-compatibility.
        del kw
        self.ensure_ascii = ensure_ascii
        self.indent = indent
        separators = separators or (' ', ': ')
        self.item_separator, self.kv_separator = separators
        self.default_fn = default or _raise_type_error
        self.sort_keys = sort_keys

    def default(self, obj: Any) -> Any:
        """Provides a last-ditch option to encode a value that the encoder
        doesn't otherwise recognize, by converting `obj` to a value that
        *can* (and will) be serialized by the other methods in the class.

        Note: this must not return a serialized value (i.e., string)
        directly, as that'll result in a doubly-encoded value."""
        return self.default_fn(obj)

    def encode(
        self,
        obj: Any,
        seen: Set,
        level: int,
        *,
        as_key: bool,
    ) -> str:
        """Returns a datafile-encoded version of an arbitrary object. This can
        be used to provide customized serialization of objects. Overridden
        methods of this class should handle their custom objects and then
        fall back to super.encode() if they've been passed a normal object.

        `level` represents the current indentation level, which increases
        by one for each recursive invocation of encode (i.e., whenever
        we're encoding the values of a dict or a list).

        May raise `TypeError` if the object is the wrong type to be
        encoded (i.e., your custom routine can't handle it either), and
        `ValueError` if there's something wrong with the value.

        If `as_key` is true, the return value should be something that
        can be used as a key, i.e., either a bare word that isn't a
        boolean, null, or a number, or a quoted string.
        If the object should not be used as a key, `TypeError` should be
        raised.
        """
        seen = seen or set()
        s = self._encode_basic_type(obj, as_key=as_key)
        if s is not None:
            return s

        if as_key:
            raise TypeError(f'Invalid key f{obj}')
        return self._encode_non_basic_type(obj, seen, level)

    def _encode_basic_type(self, obj: Any, *, as_key: bool) -> Optional[str]:
        """Returns None if the object is not a basic type."""

        if isinstance(obj, str):
            return self._encode_str(obj, as_key=as_key)

        # Check for True/False before ints because True and False are
        # also considered ints and so would be represented as 1 and 0
        # if we did ints first.
        if obj is True:
            return '"true"' if as_key else 'true'
        if obj is False:
            return '"false"' if as_key else 'false'
        if obj is None:
            return '"null"' if as_key else 'null'

        if isinstance(obj, int):
            return self._encode_int(obj, as_key=as_key)

        if isinstance(obj, float):
            return self._encode_float(obj, as_key=as_key)

        return None

    def _encode_int(self, obj: int, *, as_key: bool) -> str:
        s = int.__repr__(obj)
        return f'"{s}"' if as_key else s

    def _encode_float(self, obj: float, *, as_key: bool) -> str:
        if obj == float('inf') or obj == float('-inf') or math.isnan(obj):
            raise ValueError('Illegal datafile value: f{obj}')
        return f'"{repr(obj)}"' if as_key else repr(obj)

    def _encode_str(self, obj: str, *, as_key: bool) -> str:
        if as_key:
            return obj

        m = _bare_word_re.match(obj, re.MULTILINE)
        if m:
            return obj
        return self._encode_quoted_str(obj)

    def _encode_quoted_str(self, s: str) -> str:
        """Returns a quoted string with a minimal number of escaped quotes."""
        quote_map = {"'": 0, '"': 0, '`': 0, "'''": 0, '"""': 0, '```': 0}
        lstrs: dict[int, bool] = {}

        i = 0
        while i < len(s):
            if s[i] == '\\' and s[i + 1] in '\'"`':
                i += 2
            for k in quote_map:
                if s[i:].startswith(k):
                    quote_map[k] += 1
                    i += len(k)
                    break
            else:
                m = _long_str_re.match(s[i:])
                if m:
                    lstrs[len(m.group(0)) - 2] = True
                    i += len(m.group(0))
                else:
                    i += 1

        quote = sorted(quote_map.keys(), key=lambda k: quote_map[k])[0]
        if quote_map[quote]:
            i = 1
            while True:
                if i in lstrs:
                    i += 1
                    continue
                quote = "l'" + '=' * i + "'"
                break

        i = 0
        ret = []
        while i < len(s):
            if s.startswith(quote, i):
                ret.append('\\')
                ret.append(quote[0])
                i += len(quote)
                continue

            ch = s[i]
            o = ord(ch)
            if o < 32:
                ret.append(self._escape_ch(ch))
            elif o < 128 or (
                not self.ensure_ascii and ch not in ('\u2028', '\u2029')
            ):
                ret.append(ch)
            else:
                ret.append(self._escape_ch(ch))
            i += 1
        return quote + ''.join(ret) + quote

    def _escape_ch(self, ch: str) -> str:
        """Returns the backslash-escaped representation of the char."""
        if ch == '\\':
            return '\\\\'
        if ch == "'":
            return r'\''
        if ch == '"':
            return r'\"'
        if ch == '\n':
            return r'\n'
        if ch == '\r':
            return r'\r'
        if ch == '\t':
            return r'\t'
        if ch == '\b':
            return r'\b'
        if ch == '\f':
            return r'\f'
        if ch == '\v':
            return r'\v'
        if ch == '\0':
            return r'\0'

        o = ord(ch)
        if o < 65536:
            return rf'\u{o:04x}'

        val = o - 0x10000
        high = 0xD800 + (val >> 10)
        low = 0xDC00 + (val & 0x3FF)
        return rf'\u{high:04x}\u{low:04x}'

    def _encode_non_basic_type(self, obj, seen: Set, level: int) -> str:
        # Basic types can't be recursive so we only check for circularity
        # on non-basic types. If for some reason the caller was using a
        # subclass of a basic type and wanted to check circularity on it,
        # it'd have to do so directly in a subclass of Encoder.
        i = id(obj)
        if i in seen:
            raise ValueError('Circular reference detected.')
        seen.add(i)

        if self.indent:
            if isinstance(self.indent, str):
                max_len = 80 - len(level * self.indent)
            else:
                max_len = 80 - level * self.indent
        else:
            max_len = 80
        if isinstance(obj, collections.abc.Mapping):
            s = self._encode_dict(obj, seen, level + 1, oneline=True)
            if len(s) > max_len or '\n' in s:
                s = self._encode_dict(obj, seen, level + 1, oneline=False)
        elif isinstance(obj, collections.abc.Sequence):
            s = self._encode_array(obj, seen, level + 1, oneline=True)
            if len(s) > max_len or '\n' in s:
                s = self._encode_array(obj, seen, level + 1, oneline=False)

        else:
            s = self.encode(self.default(obj), seen, level + 1, as_key=False)
            assert s is not None

        seen.remove(i)
        return s

    def _encode_dict(
        self, obj: Any, seen: set, level: int, oneline=False
    ) -> str:
        # TODO: Should I be doing something w/ oneline?
        del oneline
        if not obj:
            return '{}'

        indent_str, end_str = self._spacers(level, False)
        item_sep = self.item_separator + indent_str
        kv_sep = self.kv_separator

        if self.sort_keys:
            keys = sorted(obj.keys())
        else:
            keys = obj.keys()

        s = '{' + indent_str

        first_key = True
        new_keys = set()
        for key in keys:
            key_str = self.encode(key, seen, level, as_key=True)

            if key_str in new_keys:
                raise ValueError(f'duplicate key {repr(key)}')
            new_keys.add(key_str)

            if first_key:
                first_key = False
            else:
                s += item_sep

            val_str = self.encode(obj[key], seen, level, as_key=False)
            s += key_str + kv_sep + val_str

        s += end_str + '}'
        return s

    def _encode_array(
        self, obj: Any, seen: Set, level: int, oneline=True
    ) -> str:
        if not obj:
            return '[]'

        indent_str, end_str = self._spacers(level, oneline)
        item_sep = self.item_separator + indent_str
        return (
            '['
            + indent_str
            + item_sep.join(
                self.encode(el, seen, level, as_key=False) for el in obj
            )
            + end_str
            + ']'
        )

    def _spacers(self, level: int, oneline: bool) -> Tuple[str, str]:
        if oneline:
            return '', ''
        if self.indent is not None:
            end_str = ''
            if isinstance(self.indent, int):
                if self.indent > 0:
                    indent_str = '\n' + ' ' * self.indent * level
                    end_str += '\n' + ' ' * self.indent * (level - 1)
                else:
                    indent_str = '\n'
                    end_str += '\n'
            else:
                indent_str = '\n' + self.indent * level
                end_str += '\n' + self.indent * (level - 1)
        else:
            indent_str = ''
            end_str = ''
        return indent_str, end_str


def _raise_type_error(obj) -> Any:
    raise TypeError(f'{repr(obj)} is not serializable as a Floyd datafile')
