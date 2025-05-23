# Generated by pyfloyd version 0.20.0.dev0
#    https://github.com/dpranke/pyfloyd
#    `pyfloyd -o src/pyfloyd/lisp_parser.py --memoize -c --python grammars/lisp.g`

import re
from typing import Any, Dict, NamedTuple, Optional


Externs = Optional[Dict[str, Any]]

# pylint: disable=too-many-lines


class _ParsingRuntimeError(Exception):
    pass


class Result(NamedTuple):
    """The result returned from a `parse()` call.

    If the parse is successful, `val` will contain the returned value, if any
    and `pos` will indicate the point in the text where the parser stopped.
    If the parse is unsuccessful, `err` will contain a string describing
    any errors that occurred during the parse and `pos` will indicate
    the location of the farthest error in the text.
    """

    val: Any = None
    err: Optional[str] = None
    pos: Optional[int] = None


def parse(
    text: str, path: str = '<string>', externs: Externs = None, start: int = 0
) -> Result:
    """Parse a given text and return the result.

    If the parse was successful, `result.val` will be the returned value
    from the parse, and `result.pos` will indicate where the parser
    stopped when it was done parsing.

    If the parse is unsuccessful, `result.err` will be a string describing
    any errors found in the text, and `result.pos` will indicate the
    furthest point reached during the parse.

    If the optional `path` is provided it will be used in any error
    messages to indicate the path to the filename containing the given
    text.
    """
    return _Parser(text, path).parse(externs, start)


class _Parser:
    def __init__(self, text, path):
        self._text = text
        self._end = len(self._text)
        self._errpos = 0
        self._failed = False
        self._path = path
        self._pos = 0
        self._val = None
        self._externs = {
            'allow_trailing': False,
        }
        self._cache = {}
        self._regexps = {}

    def parse(self, externs: Externs = None, start: int = 0):
        self._pos = start
        errors = ''
        if externs:
            for k, v in externs.items():
                if k in self._externs:
                    self._externs[k] = v
                else:
                    errors += f'Unexpected extern "{k}"\n'
        if errors:
            return Result(None, errors, 0)
        try:
            self._r_grammar()

            if self._failed:
                return Result(None, self._error(), self._errpos)
            return Result(self._val, None, self._pos)
        except _ParsingRuntimeError as e:  # pragma: no cover
            lineno, _ = self._offsets(self._errpos)
            return Result(
                None,
                self._path + ':' + str(lineno) + ' ' + str(e),
                self._errpos,
            )

    def _r_grammar(self):
        self._s_grammar_1()
        v__1 = self._val
        self._memoize('r_opt_end', self._r_opt_end)
        if self._failed:
            return
        self._succeed(v__1)

    def _s_grammar_1(self):
        vs = []
        while True:
            p = self._pos
            self._s_grammar_2()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _s_grammar_2(self):
        p = self._pos
        self._s_grammar_3()
        if not self._failed:
            return
        self._rewind(p)
        self._memoize('r_list', self._r_list)

    def _s_grammar_3(self):
        self._memoize('r__filler', self._r__filler)
        self._memoize('r_atom', self._r_atom)

    def _r_ws(self):
        self._memoize('r__filler', self._r__filler)
        self._s_ws_1()

    def _s_ws_1(self):
        p = '[ \t\n]+'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_atom(self):
        p = self._pos
        self._s_atom_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_atom_2()
        if not self._failed:
            return
        self._rewind(p)
        self._s_atom_3()
        if not self._failed:
            return
        self._rewind(p)
        self._s_atom_4()
        if not self._failed:
            return
        self._rewind(p)
        self._memoize('r_number', self._r_number)
        if not self._failed:
            return
        self._rewind(p)
        self._memoize('r_string', self._r_string)
        if not self._failed:
            return
        self._rewind(p)
        self._memoize('r_symbol', self._r_symbol)

    def _s_atom_1(self):
        self._str('#t')
        if self._failed:
            return
        self._succeed(True)

    def _s_atom_2(self):
        self._str('true')
        if self._failed:
            return
        self._succeed(True)

    def _s_atom_3(self):
        self._str('#f')
        if self._failed:
            return
        self._succeed(False)

    def _s_atom_4(self):
        self._str('false')
        if self._failed:
            return
        self._succeed(False)

    def _r_number(self):
        p = self._pos
        self._s_number_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_number_2()

    def _s_number_1(self):
        self._ch('0')
        if self._failed:
            return
        self._succeed(0)

    def _s_number_2(self):
        self._s_number_3()
        if self._failed:
            return
        v__1 = self._val
        if self._failed:
            return
        self._succeed(self._fn_atoi(v__1, 10))

    def _s_number_3(self):
        p = '[1-9][0-9]*'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_string(self):
        self._ch('"')
        if self._failed:
            return
        self._s_string_1()
        v__2 = self._val
        self._ch('"')
        if self._failed:
            return
        self._succeed(self._fn_join('', v__2))

    def _s_string_1(self):
        vs = []
        while True:
            p = self._pos
            self._memoize('r_ch', self._r_ch)
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _r_ch(self):
        p = self._pos
        self._s_ch_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_ch_2()
        if not self._failed:
            return
        self._rewind(p)
        p = self._pos
        errpos = self._errpos
        self._ch('"')
        if self._failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self._errpos = errpos
            self._fail()
        if not self._failed:
            self._r_any()

    def _s_ch_1(self):
        self._str('\\\\')
        if self._failed:
            return
        self._succeed('\\')

    def _s_ch_2(self):
        self._str('\\\n')
        if self._failed:
            return
        self._succeed('\n')

    def _r_symbol(self):
        self._s_symbol_1()
        if self._failed:
            return
        v__1 = self._val
        if self._failed:
            return
        self._succeed(['symbol', v__1])

    def _s_symbol_1(self):
        p = '[a-zA-Z][a-zA-Z0-9_]*'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_list(self):
        self._memoize('r__filler', self._r__filler)
        self._ch('(')
        if self._failed:
            return
        self._s_list_1()
        v__2 = self._val
        self._memoize('r__filler', self._r__filler)
        self._ch(')')
        if self._failed:
            return
        self._succeed(v__2)

    def _s_list_1(self):
        vs = []
        while True:
            p = self._pos
            self._s_list_2()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _s_list_2(self):
        p = self._pos
        self._s_list_3()
        if not self._failed:
            return
        self._rewind(p)
        self._memoize('r_list', self._r_list)

    def _s_list_3(self):
        self._memoize('r__filler', self._r__filler)
        self._memoize('r_atom', self._r_atom)

    def _r_opt_end(self):
        p = self._pos
        v = self._externs['allow_trailing']
        if v is True:
            self._succeed(v)
        elif v is False:
            self._fail()
        else:
            raise _ParsingRuntimeError('Bad predicate value')
        if not self._failed:
            return
        self._rewind(p)
        self._s_opt_end_1()

    def _s_opt_end_1(self):
        self._memoize('r__filler', self._r__filler)
        self._memoize('r_end', self._r_end)

    def _r__whitespace(self):
        p = '[ \t\n]+'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r__comment(self):
        self._ch(';')
        if self._failed:
            return
        self._s__comment_1()

    def _s__comment_1(self):
        vs = []
        while True:
            p = self._pos
            p = self._pos
            errpos = self._errpos
            self._ch('\n')
            if self._failed:
                self._succeed(None, p)
            else:
                self._rewind(p)
                self._errpos = errpos
                self._fail()
            if not self._failed:
                self._r_any()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _r__filler(self):
        vs = []
        while True:
            p = self._pos
            self._s__filler_1()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _s__filler_1(self):
        p = self._pos
        self._memoize('r__whitespace', self._r__whitespace)
        if not self._failed:
            return
        self._rewind(p)
        self._memoize('r__comment', self._r__comment)

    def _r_any(self):
        if self._pos < self._end:
            self._succeed(self._text[self._pos], self._pos + 1)
        else:
            self._fail()

    def _r_end(self):
        if self._pos == self._end:
            self._succeed(None)
        else:
            self._fail()

    def _ch(self, ch):
        p = self._pos
        if p < self._end and self._text[p] == ch:
            self._succeed(ch, self._pos + 1)
        else:
            self._fail()

    def _error(self):
        lineno, colno = self._offsets(self._errpos)
        if self._errpos == len(self._text):
            thing = 'end of input'
        else:
            thing = repr(self._text[self._errpos]).replace("'", '"')
        path = self._path
        return f'{path}:{lineno} Unexpected {thing} at column {colno}'

    def _fail(self):
        self._val = None
        self._failed = True
        self._errpos = max(self._errpos, self._pos)

    def _memoize(self, rule_name, fn):
        p = self._pos
        r = self._cache.setdefault(p, {}).get(rule_name)
        if r:
            self._val, self._failed, self._pos = r
            return
        fn()
        self._cache[p][rule_name] = (self._val, self._failed, self._pos)

    def _offsets(self, pos):
        lineno = 1
        colno = 1
        for i in range(pos):
            if self._text[i] == '\n':
                lineno += 1
                colno = 1
            else:
                colno += 1
        return lineno, colno

    def _rewind(self, newpos):
        self._succeed(None, newpos)

    def _str(self, s):
        for ch in s:
            self._ch(ch)
            if self._failed:
                return
        self._val = s

    def _succeed(self, v, newpos=None):
        self._val = v
        self._failed = False
        if newpos is not None:
            self._pos = newpos

    def _fn_atoi(self, a, base):
        return int(a, base)

    def _fn_join(self, s, vs):
        return s.join(vs)
