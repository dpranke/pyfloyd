# Functions

## Builtin

The host language has the following built-in functions with the
given types (using Python's type annotation syntax):

* `atob(s: str) -> bool`<br>
    Returns either true or false depending on whether the string
    is "true" or "false".

* `atof(s: str) -> float`<br>
    Returns the numeric equivalent of the string value, where the
    string matches either a floating-point number.

* `atoi(s: str, base: int) -> float`<br>
    Returns the numeric (integer) equivalent of the string value
    where the string is a series of digits in the given base (2, 8,
    10, 16). Strings in bases other than 10 may optionally be
    prefixed with the corresponding prefix. Strings in base 10
    may optionally have a leading '-'.

* `atou(s: str, base: int = 10) -> str`<br>
    Returns the unicode code point value corresponding to the
    int value of s. Equivalent to `itou(atoi(s, base))`.

* `btoa(b: bool) -> str`<br>
    Returns either 'true' or 'false' depending on the value of b.

* `car(lis: list[any]) -> any`<br>
    Returns the first item in the list. Equivalent to `item(l, 0)`.

* `cat(strs: list[str]) -> str`<br>
    Returns the string produced by concatenating all of the
    elements of `strs` together Equivalent to `join('', strs)` or
    `cat(*strs)`.

* `cdr(lis: list[any]) -> list[any]`<br>
    Returns the sublist with everything but the first element.
    Equivalent to `slice(l, 1, 0)`.

* `colno() -> int`<br>
    Returns the current (1-based) column number in the text at the
    point where the function is called. If the text is empty,
    returns 1. If at the end of the text, returns 1 + the colno of
    the last character in the file.

* `concat(xs: list[any], ys: list[any]) -> list[any]`<br>
    Returns an array containing all of the elements of `x` followed
    by all of the elements of `y`.

* `cons(hd: any, tl: list[any]) -> list[any]`<br>
    Returns an array with `hd` as the first element, followed by
    the elements from `tl`. Equivalent to `concat([hd], tl)`.

* `dedent(s: str, colno: int = -1, min_indent: int = -1) -> str`<br>
    Returns a (possibly) unindented version of the given string, as
    follows:
    - A single-line string is returned unchanged.
    - If `min_indent` is `-1`, The minimum indentation of the second
      and subsequent lines of the string is calculated; that number is
      compared to the column number of the first line as well (if
      available). Otherwise, the given column number (1-based) is
      used to determine the indentation to leave (A value of 0 or 1
      means "leave as-is").
    - If colno is not -1, that is used as the (1-based) column number
      to use for the indentation on the first line.
    - That number of leading spaces as determined from the above is
      stripped from each line, and any trailing spaces are stripped
      from each line. If the first line is blank, it is discarded
      altogether. If the last line is blank it is also discarded;
      however, if the string ends in a newline, the newline is
      preserved.

* `dict(pairs: any) -> dict[str, any]`<br>
    Returns a dictionary containing all the key/value pairs.

* `dict_is_empty(d: dict[str, any]) -> bool`<br>
    Returns whether the dictionary contains no entries. Equivalent
    to `length(keys(d)) == 0`.

* `encode_string(s: str) -> str`<br>
    Returns a double-quoted, escaped representation of the string.

* `equal(x: any, y: any) -> bool`<br>
    Returns whether the two values are equal.

* `ftoa(f: float) -> str`<br>
    Returns the string representation of the floating point number.

* `ftoi(f: float) -> int`<br>
    Returns the integer equivalent of the floating point number.
    Values are truncated towards zero (i.e., `int(3.5)` returns
    `3` and `int(-3.5)` returns `-3`).

* `get(d: dict[str, any], attr: any) -> any`<br>
    Returns the given member of the dictionary.

* `has(d: dict[str, any], key: str) -> bool`<br>
    Returns whether the key is in the dictionary.

* `in(lis: list[any], v: any) -> bool`<br>
    Returns whether `lis` contains `v`.

* `is_atom(el: any) -> bool`<br>
    Returns whether the element is a primitive type
    (null/bool/num/str).

* `is_bool(el: any) -> bool`<br>
    Returns whether the element is a boolean value.

* `is_dict(el: any) -> bool`<br>
    Returns whether the element is a dictionary/object/map.

* `is_empty(lis: list[any]) -> bool`<br>
    Returns whether the list has no elements. Equivalent to
    `equal(length(lis), 0)`.

* `is_float(el: any) -> bool`<br>
    Returns whether the element is a floating point number.

* `is_int(el: any) -> bool`<br>
    Returns whether the element is an integer.

* `is_list(el: any) -> bool`<br>
    Returns whether the element is a list.

* `is_number(el: any) -> bool`<br>
    Returns whether the element is some kind of number (int or
    float).

* `is_null(el: any) -> bool`<br>
    Returns whether the element is `null`.

* `is_str(el: any) -> bool`<br>
    Returns whether the element is a string.

* `item(lis: list[any], index: int) -> any`<br>
    Returns the given member of the array. Indexes work as in
    Python, so they are zero-based and negative numbers work
    backwards from the end of the list.

* `itoa(i: int, base: int = 10) -> str`<br>
    Returns the string representation of integer `val` expressed in
    the given base (either 2, 8, 10, or 16). Bases other than
    10 are prefixed with the corresponding prefix ('0b', '0o', or
    '0x').

* `itof(i: int) -> float`<br>
    Returns the floating point equivalent of the integer `i`.

* `itou(i: int) -> str`<br>
    Returns a string containing a single character with the code
    point corresponding to `i`.

* `join(sep: str, strs: list[str]) -> str`<br>
    Returns the result of joining all the strings in `strs` with
    the string in `sep` in between them.

* `keys(d: dict[str, any]) -> list[str]`<br>
    Returns the keys in the dictionary.

* `len(lis: list[any]) -> int`<br>
    Returns the length of the list.

* `list(*args: any) -> list[any]`<br>
    Returns a list of the given arguments.

* `map(fn: func[[any], any], lis: list[any]) -> list[any]`<br>
    Returns a list containing the values returned from calling `fn`
    with every item in `lis`.

* `map_items(fn: func[[str, any], any], lis: list[any]) -> list[any]`<br>
    Returns a list containing the values returned from calling `fn`
    with each `key`, `value` pair in `d`.

* `node(parser: any, *args: any) -> any`<br>
    Hook function that can be used to synthesize custom AST nodes
    in the parser. By default this just returns a list of the args
    passed to it.

* `otou(s: str) -> str`<br>
    Returns a string containing a single character with the code
    point corresponding to the given string of octal digits.
    Equivalent to `itou(atoi(s, base=8))`.

* `pairs(d: dict[str, any]) -> list[any]`<br>
    Returns a list of the [key, value] pairs in the dict `d`.

* `pos() -> int`<br>
    Returns the current position in the parser.

* `replace(s: str, old: str, new: str) -> str`<br>
    Returns a copy of `s` with all the occurrences of `old` replaced
    by `new`.

* `scat(hd: str, tl: list[str]) -> str`<br>
    Returns a string formed by concatenating `hd` with every item
    in `tl`. Equivalent to `strcat(hd, *tl)` or `cat(scons(hd, tl))`.

* `scons(hd: str, tl: list[str]) -> list[str]`<br>
    Returns an array with `hd` as the first element, followed by the
    elements from `tl`. Equivalent to `cons`, but takes strings
    instead of arbitrary values.

* `slice(vs: list[any], start: int, end: int) -> list[any]`<br>
    Returns the sublist of `l` starting at `start` and ending at
    `end`. `start` and `end` have almost the same meanings as in
    Python, i.e., they are zero-based, and negative numbers count
    backwards from the end of the list. Unlike Python, however,
    a value of 0 for `end` means "to the end of the list", i.e.,
    `slice(l, 1, 0)` is equivalent to Python's `l[1:]`.

* `sort(strs: list[str]) -> list[str]`<br>
    Returns a copy of `strs` where the elements have been sorted.

* `split(s: str, sep: str = '') -> list[str]`<br>
    Returns a list of strings obtained by splitting `s` whereever
    `sep` occurs. If sep is the empty string, the string is split
    into a list of individual characters.

* `str2td(s: str) -> dict[str, any]`<br>
    Returns a descriptor containing a language-neutral parsed
    version of a given language-neutral type string. Each descriptor
    contains two fields, a `base` field with the base type (as a
    string), and an `elements` field, for any type parameters.
    For example, `list[str]` would be
    `{base: list, elements[{base: str}]}`. Note: in some languages
    this may return a dict-like object rather than an actual dict.

* `strcat(*args: str) -> str`<br>
    Returns the string concatenation of the args. Equivalent to
    `cat(args)` or `join('', args)`.

* `strin(s: str, sub: str) -> bool`<br>
    Returns whether `sub` is found in `s`.

* `strlen(s: str) -> int`<br>
    Returns the length of the string.

* `substr(s: str, start: int, end: int) -> str`<br>
    Returns the substring of `s` from `start` to `end`. `start` and
    `end` have almost the same meanings as in a Python slice, i.e.
    they are zero-based and negative numbers count backwards from
    the end. Unlike Python, however, a value of `0` for `end` can
    be used for the end of the string.

* `td2str(d: dict[str, any]) -> str`<br>
    Returns a language-neutral string representative of a given
    language-neutral type description. See `str2td` for the
    dictionary structure. For example,
    `td2str({base: list, elements: [{base: str, elements: []}]`
    would return `list[str]`.

* `throw(msg: str) -> str`<br>
    Throws (or raises) an exception with the given `msg` as a
    message. The current `compile`, `parse`, or `generate` operation
    completes immediately and returns the message as the error.

* `ucategory(s: str) -> str`<br>
    Returns a string with the unicode category of the first
    character in the string `s`. This may not be available in every
    environment; if it isn't, a RuntimeError will be raised when
    the runtime detects that you may want to use it (i.e., at parse
    time, not runtime).

* `ulookup(s: str) -> str`<br>
    Returns a string containing the single character with the
    unicode name given in `s`. This may not be available in every
    environment; if it isn't, a RuntimeError will be raised when
    the runtime detects that you may want to use it (i.e., at parse
    time, not runtime).

* `uname(s: str) -> str`<br>
    Returns the unicode name for the first character in `s`. This
    may not be available in every environment; if it isn't, a
    RuntimeError will be raised when the runtime detects that you
    may want to use it (i.e., at parse time, not runtime).

* `utoi(u: str) -> int`<br>
    Returns the unicode code point value of the first character in s.

* `values(d: dict[str, any]) -> list[any]`<br>
    Returns the values in the given dictionary.

* `xtoi(s: str) -> int`<br>
    Returns the integer value of the given hexadecimal string.
    The string may have an optional '0x' at the front. Equivalent
    to `atoi(s, base=16)`.

* `xtou(s: str) -> str`<br>
    Returns the Unicode character with the code point value that is
    the hexadecimal value in `s`. The string may have an optional
    "0x" in front, or it may be just a string of hexadecimal digits.
    Equivalent to `atou(s, base=16)`.

