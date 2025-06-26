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

# pylint: disable=too-many-lines

import collections
import math
import re
import unicodedata

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

from pyfloyd import functions

from . import parser


class DatafileError(ValueError):
    """Exception raised when a datafile is semantically invalid.

    This is a subclass of ValueError, and so can be caught by code
    that catches ValueError.
    """


class DatafileParseError(DatafileError):
    """Exception raised when a datafile is syntactically invalid.

    This is a subclass of ValueError, and so can be caught by code
    that catches ValueError.
    """


quote_tokens = ('```', '"""', "'''", '`', '"', "'")

_bare_word_re = re.compile(r'^[^\\\s\[\]\(\)\{\}:\'"`]+$')

_long_str_re = re.compile(r"^l'=+'")

# pylint: disable=too-many-arguments


def load(
    fp: IO,
    *,
    encoding: Optional[str] = None,
    cls: Any = None,
    object_hook: Optional[Callable[[Mapping[str, Any]], Any]] = None,
    parse_number: Optional[Callable[[str], Any]] = None,
    parse_numword: Optional[Callable[[str], Any]] = None,
    parse_bareword: Optional[Callable[[str, bool], Any]] = None,
    object_pairs_hook: Optional[
        Callable[[Iterable[Tuple[str, Any]]], Any]
    ] = None,
    allow_trailing: bool = False,
    allow_numwords: bool = False,
    start: Optional[int] = None,
    custom_tags: Optional[dict[str, Any]] = None,
    filename: Optional[str] = None,
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
      DatafileParseError: if given an invalid document.
      UnicodeDecodeError: if given a byte string that is not a
          legal UTF-8 document (or the equivalent, if using a different
          `encoding`). This matches the `json` module.
    """

    s = fp.read()
    return loads(
        s,
        encoding=encoding,
        cls=cls,
        object_hook=object_hook,
        parse_number=parse_number,
        parse_numword=parse_numword,
        parse_bareword=parse_bareword,
        object_pairs_hook=object_pairs_hook,
        allow_trailing=allow_trailing,
        allow_numwords=allow_numwords,
        start=start,
        custom_tags=custom_tags,
        filename=filename,
    )


def loads(
    s: str,
    *,
    encoding: Optional[str] = None,
    cls: Any = None,
    object_hook: Optional[Callable[[Mapping[str, Any]], Any]] = None,
    parse_number: Optional[Callable[[str], Any]] = None,
    parse_numword: Optional[Callable[[str], Any]] = None,
    parse_bareword: Optional[Callable[[str, bool], Any]] = None,
    object_pairs_hook: Optional[
        Callable[[Iterable[Tuple[str, Any]]], Any]
    ] = None,
    allow_trailing: bool = False,
    allow_numwords: bool = False,
    start: Optional[int] = None,
    custom_tags: Optional[dict[str, Any]] = None,
    filename: Optional[str] = None,
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
        - `DatafileParseError` if given a syntactically invalid document.
        - `DatafileError` if given a semantically invalid document.
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
        parse_bareword=parse_bareword,
        object_pairs_hook=object_pairs_hook,
        allow_trailing=allow_trailing,
        allow_numwords=allow_numwords,
        start=start,
        custom_tags=custom_tags,
        filename=filename,
    )
    if err:
        raise DatafileError(err)
    return val


def parse(
    s: str,
    *,
    allow_trailing: bool = False,
    allow_numwords: bool = False,
    encoding: Optional[str] = None,
    cls: Any = None,
    object_hook: Optional[Callable[[Mapping[str, Any]], Any]] = None,
    object_pairs_hook: Optional[
        Callable[[Iterable[Tuple[str, Any]]], Any]
    ] = None,
    parse_number: Optional[Callable[[str], Any]] = None,
    parse_numword: Optional[Callable[[str], Any]] = None,
    parse_bareword: Optional[Callable[[str, bool], Any]] = None,
    start: Optional[int] = None,
    custom_tags: Optional[dict[str, Any]] = None,
    filename: Optional[str] = None,
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

    Note that this does *not* raise a `DatafileError`; instead any error is
    returned as the second value in the tuple.

    You can use this method to read in a series of values from a string
    `s` as follows:

        >>> from pyfloyd import datafile
        >>> s = '1 2 3 4'
        >>> values = []
        >>> start = 0
        >>> while True:
        ...     v, err, pos = datafile.parse(s, start=start,
        ...                                  allow_trailing=True)
        ...     if v:
        ...         values.append(v)
        ...         start = pos
        ...         if start == len(s) or s[start:].isspace():
        ...             # Reached the end of the string (ignoring trailing
        ...             # whitespace
        ...             break
        ...         continue
        ...     raise datafile.DatafileParseError(err)
        >>> values
        [1, 2, 3, 4]

    """
    cls = cls or Decoder
    obj = cls()
    return obj.parse(
        s,
        allow_numwords=allow_numwords,
        allow_trailing=allow_trailing,
        encoding=encoding,
        object_hook=object_hook,
        object_pairs_hook=object_pairs_hook,
        parse_number=parse_number,
        parse_numword=parse_numword,
        parse_bareword=parse_bareword,
        start=start,
        custom_tags=custom_tags,
        filename=filename,
    )


class Decoder:
    def __init__(self):
        self._allow_trailing = False
        self._allow_numwords = False
        self._parse_number = None
        self._parse_numword = None
        self._parse_bareword = None
        self._parse_object = None
        self._parse_object_pairs = None
        self._custom_tags = None

    def parse(
        self,
        s: str,
        *,
        encoding: Optional[str] = None,
        object_hook: Optional[Callable[[Mapping[str, Any]], Any]] = None,
        object_pairs_hook: Optional[
            Callable[[Iterable[Tuple[str, Any]]], Any]
        ] = None,
        parse_number: Optional[Callable[[str], Any]] = None,
        parse_numword: Optional[Callable[[str], Any]] = None,
        parse_bareword: Optional[Callable[[str, bool], Any]] = None,
        allow_trailing=False,
        allow_numwords=False,
        start=0,
        custom_tags: Optional[dict[str, Any]] = None,
        filename: Optional[str] = None,
    ) -> Tuple[Any, Optional[str], Optional[int]]:
        self._allow_trailing = allow_trailing
        self._allow_numwords = allow_numwords
        self._parse_object = object_hook
        self._parse_object_pairs = object_pairs_hook
        self._parse_number = parse_number or self.parse_number
        self._parse_numword = parse_numword or self.parse_numword
        self._parse_bareword = parse_bareword or self.parse_bareword
        self._custom_tags = custom_tags or {}

        filename = filename or '<string>'

        if isinstance(s, bytes):
            encoding = encoding or 'utf-8'
            s = s.decode(encoding)

        if not s:
            raise DatafileError('Empty strings are not legal Floyd datafiles')
        start = start or 0
        externs = {
            'allow_trailing': self._allow_trailing,
            'allow_numwords': self._allow_numwords,
        }
        ast, err, pos = parser.parse(s, filename, externs)
        if err:
            return None, err, pos

        value = self._walk_ast(ast)
        return value, None, pos

    def _walk_ast(self, el: Tuple[str, Any, list[Any]]) -> Any:
        ty, val, ch = el
        if ty in ('true', 'false', 'null'):
            return val
        if ty == 'number':
            return self.parse_number(val)
        if ty == 'numword':
            return self.parse_numword(val, as_key=False)
        if ty == 'bareword':
            return self.parse_bareword(val, as_key=False)
        if ty == 'string':
            tag = val[0]
            if tag in self._custom_tags:
                return self._custom_tags[tag](ty, val, as_key=False)
            return self.parse_string(val, as_key=False)
        if ty == 'object':
            tag = val
            pairs = []
            for key_ast, value_obj in ch:
                key = self.parse_key(key_ast)
                v = self._walk_ast(value_obj)
                pairs.append((key, v))
            if tag in self._custom_tags:
                return self._custom_tags[tag](ty, tag, pairs)
            return self.parse_object_pairs(tag, pairs)
        if ty == 'array':
            tag = val
            vals = [self._walk_ast(c) for c in ch]
            if tag in self._custom_tags:
                return self._custom_tags[tag](ty, tag, vals)
            return self.parse_array(tag, vals)
        raise DatafileError(f'unknown element type "{ty}"')  # pragma: no cover

    def parse_array(self, tag: str, vals: list[Any]) -> Any:
        if tag == 's':
            return ''.join(vals)
        if tag:
            raise DatafileError(f'Unsupported array tag {tag}')
        return vals

    def parse_number(self, val: str) -> Any:
        s = val.replace('_', '')
        if s.startswith('0x'):
            return int(s, base=16)
        if s.startswith('0b'):
            return int(s, base=2)
        if s.startswith('0o'):
            return int(s, base=8)
        if '.' in s or 'e' in s or 'E' in s:
            return float(s)
        return int(s)

    def parse_numword(self, val: str, as_key: bool) -> Any:
        del as_key
        return val

    def parse_bareword(self, val: str, as_key: bool) -> Any:
        del as_key
        return val

    def parse_string(self, val: Tuple[str, str, int, str], as_key: bool) -> Any:
        del as_key
        tag, quote, colno, text = val
        is_raw_str = 'r' in tag
        is_indented_str = 'i' in tag
        if tag and tag not in ('i', 'r', 'ir', 'ri'):
            raise DatafileError(f'Unsupported string tag `{tag}`')

        if is_raw_str:
            s = text
        else:
            s = decode_string(text, quote)
        if '\n' in text:
            # Note: text, not s. We want to see if the original string had
            # newlines.
            return dedent(
                s, colno=colno, min_indent=1 if is_indented_str else -1
            )
        return s

    def parse_key(self, key_ast: Any) -> str:
        ty, val, _ = key_ast
        tag = val[0]
        if ty == 'string':
            if tag in self._custom_tags:
                return self._custom_tags[tag](ty, val, as_key=True)
            return self.parse_string(val, as_key=True)
        if ty == 'bareword':
            return self.parse_bareword(val, as_key=True)
        assert ty == 'numword'
        return self.parse_numword(val, as_key=True)

    def parse_object_pairs(self, tag: str, pairs: list[Tuple[str, Any]]) -> Any:
        if tag:
            raise DatafileError(f'Unsupported object tag {tag}')
        keys = set()
        key_pairs = []
        for key, val in pairs:
            if key in keys:
                raise DatafileError(f'Duplicate key "{key}" found in object')
            keys.add(key)
            key_pairs.append((key, val))
        if self._parse_object_pairs:
            return self._parse_object_pairs(key_pairs)
        if self._parse_object:
            return self._parse_object(dict(key_pairs))
        return dict(key_pairs)


def decode_string(s: str, quote: Optional[str] = None) -> str:
    """Unescapes a string possibly containing escaped chars.

    `quote` should be the quote string that was used to enclose the
    string in the datafile, if possible. If that's unavailable, best
    effort should be made to provide a quote string that will not
    conflict with the undecoded string. This is used when raising an error.
    You can call `find_quote_for()` to find an appropriate quote string.

    Raises DatafileError if the string contains a bad escaped sequence
    or if it refers to an unrecognized unicode name. `quote` will be
    used during this, and if possible should be the quote character
    sequence that wrapped the original string in the datafile.
    """

    if quote is None:
        quote = find_quote_for(s)

    i = 0
    ret = []
    end = len(s)
    while i < end:
        c = s[i]
        if c != '\\':
            i += 1
        else:
            i, c = decode_escape(s, i, end, quote)
        ret.append(c)
    return ''.join(ret)


def decode_escape(s: str, i: int, end: int, quote: str) -> Tuple[int, str]:
    """Decodes a character escape sequence.

    Returns the number of characters to advance and the decoded character.
    Raises DatafileError if the escape sequence is invalid (including if
    a unicode name isn't recognized).
    """

    if i + 1 >= end:
        raise DatafileError(
            f'Bad escape sequence at end of string {quote}{s}{quote}'
        )

    c = s[i + 1]
    # Check escape sequences in (rough) order of likelihood.
    if c == 'n':
        return i + 2, '\n'
    if c == 't':
        return i + 2, '\t'
    if c == '\\':
        return i + 2, '\\'
    if c == "'":
        return i + 2, "'"
    if c == '"':
        return i + 2, '"'
    if c == '`':
        return i + 2, '`'
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
    if c == 'x':
        return decode_numeric_escape(s, i + 2, end, 1, 2, ishex, 16, quote)
    if c == 'u':
        return decode_numeric_escape(s, i + 2, end, 1, 8, ishex, 16, quote)
    if c == 'N':
        rbrace = s.find( '}', i + 3)
        try:
            ch = unicodedata.lookup(s[i+3: rbrace])
            i = rbrace + 1
            return i, ch
        except KeyError as exc:
            raise DatafileError(
                f'Unrecognized unicode name "{s[i+3: rbrace]}" at offset {i} '
                f'in string {quote}{s}{quote}'
            ) from exc

    return decode_numeric_escape(s, i + 1, end, 1, 3, isoct, 8, quote)


def decode_numeric_escape(
    s: str,
    start: int,
    end: int,
    min_num: int,
    max_num: int,
    fn: Callable[[str], bool],
    base: int,
    quote: str
):
    """Decodes a numeric escape sequence in a string.

    `start` is the offset into the string to start at.
    `end` is the length of the string.
    `min_num` is the minimum legal number of characters in the sequence.
    `max_num` is the maximum legal number of characters in the sequence.
    `fn` is a function that verifies if each character is legal.
    `base` is the numeric base to use in the conversion. Legal values
         are 8 and 16.
    `quote` is the quote string to wrap the string with when reporting an
        error.

    Returns the corresponding character.

    Raises DatafileError if the numeric escape is invalid.
    """
    i = 0

    assert base in (8, 16), (
        f'Unsupported base {base} passed to decode_numeric_escape()'
    )

    def _raise(offset):
        raise DatafileError(
            f'Bad escape sequence in string {quote}{s}{quote} at '
            f'offset {i}'
        )

    i = start
    while i < min(end, start + max_num):
        if not fn(s[i]):
            _raise(i)
        i += 1
    if i - start < min_num:
        _raise(i)
    return i, chr(int(s[start:i], base))


def ishex(ch: str) -> bool:
    return ch in '0123456789abcdefABCDEF'


def isoct(ch: str) -> bool:
    return '0' <= ch <= '7'


def dedent(s: str, colno: int = -1, min_indent = -1) -> str:
    """Returns a dedented version of a string."""
    return functions.f_dedent(s, colno, min_indent)


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
        `DatafileError` if there's something wrong with the value.

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
            raise DatafileError('Illegal datafile value: f{obj}')
        return f'"{repr(obj)}"' if as_key else repr(obj)

    def _encode_str(self, obj: str, *, as_key: bool) -> str:
        if as_key:
            return obj
        return encode_string(obj, self.ensure_ascii)

    def _encode_non_basic_type(self, obj, seen: Set, level: int) -> str:
        # Basic types can't be recursive so we only check for circularity
        # on non-basic types. If for some reason the caller was using a
        # subclass of a basic type and wanted to check circularity on it,
        # it'd have to do so directly in a subclass of Encoder.
        i = id(obj)
        if i in seen:
            raise DatafileError('Circular reference detected.')
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
            if len(s) > max_len and ('\n' not in s):
                s = self._encode_dict(obj, seen, level + 1, oneline=False)
        elif isinstance(obj, collections.abc.Sequence):
            s = self._encode_array(obj, seen, level + 1, oneline=True)
            if len(s) > max_len and ('\n' not in s):
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
        if '\n' in indent_str:
            item_sep = self.item_separator.strip() + indent_str
        else:
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
                raise DatafileError(f'duplicate key {repr(key)}')
            new_keys.add(key_str)

            if first_key:
                first_key = False
            else:
                s += item_sep

            val_str = self.encode(obj[key], seen, level, as_key=False)
            if (
                isinstance(obj[key], str)
                and '\n' in obj[key]
                and self.indent is not None
            ):
                if isinstance(self.indent, int):
                    d_indent_str = indent_str + ' ' * self.indent
                else:
                    d_indent_str = indent_str + self.indent
                lines = val_str.splitlines()
                leading_quote = _get_leading_quote(lines[0])
                if len(lines) > 1:
                    val_str = 'd' + leading_quote
                    val_str += d_indent_str + lines[0][len(leading_quote) :]
                    for line in lines[1:-1]:
                        val_str += d_indent_str + line
                    val_str += d_indent_str + lines[-1]
                else:
                    val_str = lines[0]
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


def encode_string(
    obj: str, ensure_ascii: bool = True, escape_newlines=False
) -> str:
    m = _bare_word_re.match(obj)
    if m:
        return obj
    return encode_quoted_string(obj, ensure_ascii, escape_newlines)


def encode_quoted_string(
        s: str,
        ensure_ascii: bool = True,
        escape_newlines: bool = False,
        quote: Optional[str]=None
) -> str:
    """Returns a safely escaped, quoted version of the string.

    The returned value will have a minimal number of escaped quotes.
    """

    if quote is None:
        quote = find_quote_for(s)

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
            ret.append(escape_char(ch))
        elif o < 128 or (not ensure_ascii and ch not in ('\u2028', '\u2029')):
            ret.append(ch)
        else:
            ret.append(escape_char(ch))
        i += 1

    if len(ret) > 10:
        # Only allow "long" strings to span multiple lines. The number 10
        # is pulled out of the air here as a heuristic for "long".
        ret = [
            '\n' if (r == '\\n' and not escape_newlines) else r for r in ret
        ]

    return quote + ''.join(ret) + quote


def find_quote_for(s: str) -> str:
    """Returns a quote string that can be used to safely enclose the string."""
    quote_map: dict[str, int] = {}
    for token in quote_tokens:
        quote_map[token] = 0
    lstrs: dict[int, bool] = {}

    i = 0
    while i < len(s):
        if s[i] == '\\' and (i + 1 < len(s)) and s[i + 1] in '\'"`':
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

    min_quote_count = min(quote_map.values())
    for tok in reversed(quote_tokens):
        if quote_map[tok] == min_quote_count:
            quote = tok
            break
    if quote_map[quote]:
        i = 1
        while True:
            if i in lstrs:
                i += 1
                continue
            quote = "L'" + '=' * i + "'"
            break
    return quote



def escape_char(ch: str) -> str:
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


def _get_leading_quote(s):
    for q in quote_tokens:
        if s.startswith(q):
            return q
    m = _long_str_re.match(s)
    return m.group(0)


def _raise_type_error(obj) -> Any:
    raise TypeError(f'{repr(obj)} is not serializable as a Floyd datafile')
