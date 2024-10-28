import re
from typing import Any, NamedTuple, Optional


# pylint: disable=too-many-lines


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


def parse(text: str, path: str = '<string>') -> Result:
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
    return _Parser(text, path).parse()


class _Parser:
    def __init__(self, text, path):
        self._text = text
        self._end = len(self._text)
        self._errpos = 0
        self._failed = False
        self._path = path
        self._pos = 0
        self._val = None
        self._cache = {}
        self._regexps = {}

    def parse(self):
        self._r_grammar()
        if self._failed:
            return Result(None, self._err_str(), self._errpos)
        return Result(self._val, None, self._pos)

    def _r_grammar(self):
        r = self._cache.get(('r_grammar', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        self._s_grammar_1()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._r_end()
        if not self._failed:
            self._succeed(['rules', None, v__1])
        self._cache[('r_grammar', pos)] = (self._val, self._failed, self._pos)

    def _s_grammar_1(self):
        vs = []
        while True:
            p = self._pos
            self._r_rule()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _r_rule(self):
        r = self._cache.get(('r_rule', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        self._s_rule_1()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch('=')
        if not self._failed:
            self._r_choice()
            if not self._failed:
                v__3 = self._val
        if not self._failed:
            self._succeed(['rule', v__1, [v__3]])
        self._cache[('r_rule', pos)] = (self._val, self._failed, self._pos)

    def _s_rule_1(self):
        self._r__filler()
        if not self._failed:
            self._r_ident()

    def _r_ident(self):
        r = self._cache.get(('r_ident', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        self._r_id_start()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._s_ident_1()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(self._fn_cat(self._fn_scons(v__1, v__2)))
        self._cache[('r_ident', pos)] = (self._val, self._failed, self._pos)

    def _s_ident_1(self):
        vs = []
        while True:
            p = self._pos
            self._r_id_continue()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _r_id_start(self):
        r = self._cache.get(('r_id_start', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = '[a-zA-Z$_%]'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()
        self._cache[('r_id_start', pos)] = (self._val, self._failed, self._pos)

    def _r_id_continue(self):
        r = self._cache.get(('r_id_continue', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._r_id_start()
        if not self._failed:
            return
        self._rewind(p)
        self._s_id_continue_1()
        self._cache[('r_id_continue', pos)] = (self._val, self._failed, self._pos)

    def _s_id_continue_1(self):
        p = '[0-9]'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_choice(self):
        r = self._cache.get(('r_choice', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        self._r_seq()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._s_choice_1()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(['choice', None, self._fn_cons(v__1, v__2)])
        self._cache[('r_choice', pos)] = (self._val, self._failed, self._pos)

    def _s_choice_1(self):
        vs = []
        while True:
            p = self._pos
            self._s_choice_2()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _s_choice_2(self):
        self._r__filler()
        if not self._failed:
            self._ch('|')
        if not self._failed:
            self._r_seq()

    def _r_seq(self):
        r = self._cache.get(('r_seq', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_seq_1()
        if not self._failed:
            return
        self._rewind(p)
        self._succeed(['empty', None, []])
        self._cache[('r_seq', pos)] = (self._val, self._failed, self._pos)

    def _s_seq_1(self):
        self._r_expr()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._s_seq_2()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(['seq', None, self._fn_cons(v__1, v__2)])

    def _s_seq_2(self):
        vs = []
        while True:
            p = self._pos
            self._s_seq_3()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _s_seq_3(self):
        self._r_expr()

    def _r_expr(self):
        r = self._cache.get(('r_expr', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_expr_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_expr_2()
        if not self._failed:
            return
        self._rewind(p)
        self._s_expr_3()
        if not self._failed:
            return
        self._rewind(p)
        self._r_post_expr()
        self._cache[('r_expr', pos)] = (self._val, self._failed, self._pos)

    def _s_expr_1(self):
        self._r__filler()
        if not self._failed:
            self._str('->')
        if not self._failed:
            self._r_ll_expr()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(['action', None, [v__2]])

    def _s_expr_2(self):
        self._r__filler()
        if not self._failed:
            self._str('?{')
        if not self._failed:
            self._r_ll_expr()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch('}')
        if not self._failed:
            self._succeed(['pred', None, [v__2]])

    def _s_expr_3(self):
        self._r_post_expr()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch(':')
        if not self._failed:
            self._s_expr_4()
            if not self._failed:
                v__3 = self._val
        if not self._failed:
            self._succeed(['label', v__3, [v__1]])

    def _s_expr_4(self):
        self._r__filler()
        if not self._failed:
            self._r_ident()

    def _r_post_expr(self):
        r = self._cache.get(('r_post_expr', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_post_expr_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_post_expr_2()
        if not self._failed:
            return
        self._rewind(p)
        self._s_post_expr_3()
        if not self._failed:
            return
        self._rewind(p)
        self._s_post_expr_4()
        if not self._failed:
            return
        self._rewind(p)
        self._r_prim_expr()
        self._cache[('r_post_expr', pos)] = (self._val, self._failed, self._pos)

    def _s_post_expr_1(self):
        self._r_prim_expr()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch('?')
        if not self._failed:
            self._succeed(['opt', None, [v__1]])

    def _s_post_expr_2(self):
        self._r_prim_expr()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch('*')
        if not self._failed:
            self._succeed(['star', None, [v__1]])

    def _s_post_expr_3(self):
        self._r_prim_expr()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch('+')
        if not self._failed:
            self._succeed(['plus', None, [v__1]])

    def _s_post_expr_4(self):
        self._r_prim_expr()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._r_count()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(['count', v__2, [v__1]])

    def _r_count(self):
        r = self._cache.get(('r_count', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_count_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_count_4()
        self._cache[('r_count', pos)] = (self._val, self._failed, self._pos)

    def _s_count_1(self):
        self._r__filler()
        if not self._failed:
            self._ch('{')
        if not self._failed:
            self._s_count_2()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch(',')
        if not self._failed:
            self._s_count_3()
            if not self._failed:
                v__4 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch('}')
        if not self._failed:
            self._succeed([v__2, v__4])

    def _s_count_2(self):
        self._r__filler()
        if not self._failed:
            self._r_zpos()

    def _s_count_3(self):
        self._r__filler()
        if not self._failed:
            self._r_zpos()

    def _s_count_4(self):
        self._r__filler()
        if not self._failed:
            self._ch('{')
        if not self._failed:
            self._s_count_5()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch('}')
        if not self._failed:
            self._succeed([v__2, v__2])

    def _s_count_5(self):
        self._r__filler()
        if not self._failed:
            self._r_zpos()

    def _r_prim_expr(self):
        r = self._cache.get(('r_prim_expr', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_prim_expr_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_prim_expr_4()
        if not self._failed:
            return
        self._rewind(p)
        self._s_prim_expr_6()
        if not self._failed:
            return
        self._rewind(p)
        self._s_prim_expr_8()
        if not self._failed:
            return
        self._rewind(p)
        self._s_prim_expr_10()
        if not self._failed:
            return
        self._rewind(p)
        self._s_prim_expr_12()
        if not self._failed:
            return
        self._rewind(p)
        self._s_prim_expr_13()
        if not self._failed:
            return
        self._rewind(p)
        self._s_prim_expr_14()
        if not self._failed:
            return
        self._rewind(p)
        self._s_prim_expr_15()
        if not self._failed:
            return
        self._rewind(p)
        self._s_prim_expr_19()
        if not self._failed:
            return
        self._rewind(p)
        self._s_prim_expr_20()
        self._cache[('r_prim_expr', pos)] = (self._val, self._failed, self._pos)

    def _s_prim_expr_1(self):
        self._s_prim_expr_2()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._str('..')
        if not self._failed:
            self._s_prim_expr_3()
            if not self._failed:
                v__3 = self._val
        if not self._failed:
            self._succeed(['range', [v__1, v__3], []])

    def _s_prim_expr_2(self):
        self._r__filler()
        if not self._failed:
            self._r_lit()

    def _s_prim_expr_3(self):
        self._r__filler()
        if not self._failed:
            self._r_lit()

    def _s_prim_expr_4(self):
        self._s_prim_expr_5()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._succeed(['lit', v__1, []])

    def _s_prim_expr_5(self):
        self._r__filler()
        if not self._failed:
            self._r_lit()

    def _s_prim_expr_6(self):
        self._r__filler()
        if not self._failed:
            self._str('\\p{')
        if not self._failed:
            self._s_prim_expr_7()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch('}')
        if not self._failed:
            self._succeed(['unicat', v__2, []])

    def _s_prim_expr_7(self):
        self._r__filler()
        if not self._failed:
            self._r_ident()

    def _s_prim_expr_8(self):
        self._s_prim_expr_9()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._succeed(['set', v__1, []])

    def _s_prim_expr_9(self):
        self._r__filler()
        if not self._failed:
            self._r_set()

    def _s_prim_expr_10(self):
        self._s_prim_expr_11()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._succeed(['regexp', v__1, []])

    def _s_prim_expr_11(self):
        self._r__filler()
        if not self._failed:
            self._r_regexp()

    def _s_prim_expr_12(self):
        self._r__filler()
        if not self._failed:
            self._ch('\x7e')
        if not self._failed:
            self._r_prim_expr()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(['not', None, [v__2]])

    def _s_prim_expr_13(self):
        self._r__filler()
        if not self._failed:
            self._str('^.')
        if not self._failed:
            self._r_prim_expr()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(['ends_in', None, [v__2]])

    def _s_prim_expr_14(self):
        self._r__filler()
        if not self._failed:
            self._ch('^')
        if not self._failed:
            self._r_prim_expr()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(['not_one', None, [v__2]])

    def _s_prim_expr_15(self):
        self._s_prim_expr_16()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._s_prim_expr_17()
        if not self._failed:
            self._succeed(['apply', v__1, []])

    def _s_prim_expr_16(self):
        self._r__filler()
        if not self._failed:
            self._r_ident()

    def _s_prim_expr_17(self):
        p = self._pos
        errpos = self._errpos
        self._s_prim_expr_18()
        if self._failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self._errpos = errpos
            self._fail()

    def _s_prim_expr_18(self):
        self._r__filler()
        if not self._failed:
            self._ch('=')

    def _s_prim_expr_19(self):
        self._r__filler()
        if not self._failed:
            self._ch('(')
        if not self._failed:
            self._r_choice()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch(')')
        if not self._failed:
            self._succeed(['paren', None, [v__2]])

    def _s_prim_expr_20(self):
        self._r__filler()
        if not self._failed:
            self._ch('<')
        if not self._failed:
            self._r_choice()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch('>')
        if not self._failed:
            self._succeed(['run', None, [v__2]])

    def _r_lit(self):
        r = self._cache.get(('r_lit', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_lit_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_lit_3()
        self._cache[('r_lit', pos)] = (self._val, self._failed, self._pos)

    def _s_lit_1(self):
        self._r_squote()
        if not self._failed:
            self._s_lit_2()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._r_squote()
        if not self._failed:
            self._succeed(self._fn_cat(v__2))

    def _s_lit_2(self):
        vs = []
        while True:
            p = self._pos
            self._r_sqchar()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _s_lit_3(self):
        self._r_dquote()
        if not self._failed:
            self._s_lit_4()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._r_dquote()
        if not self._failed:
            self._succeed(self._fn_cat(v__2))

    def _s_lit_4(self):
        vs = []
        while True:
            p = self._pos
            self._r_dqchar()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _r_sqchar(self):
        r = self._cache.get(('r_sqchar', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._r_escape()
        if not self._failed:
            return
        self._rewind(p)
        p = self._pos
        errpos = self._errpos
        self._r_squote()
        if self._failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self._errpos = errpos
            self._fail()
        if not self._failed:
            self._r_any()
        self._cache[('r_sqchar', pos)] = (self._val, self._failed, self._pos)

    def _r_dqchar(self):
        r = self._cache.get(('r_dqchar', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._r_escape()
        if not self._failed:
            return
        self._rewind(p)
        p = self._pos
        errpos = self._errpos
        self._r_dquote()
        if self._failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self._errpos = errpos
            self._fail()
        if not self._failed:
            self._r_any()
        self._cache[('r_dqchar', pos)] = (self._val, self._failed, self._pos)

    def _r_bslash(self):
        r = self._cache.get(('r_bslash', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        self._ch('\\')
        self._cache[('r_bslash', pos)] = (self._val, self._failed, self._pos)

    def _r_squote(self):
        r = self._cache.get(('r_squote', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        self._ch("'")
        self._cache[('r_squote', pos)] = (self._val, self._failed, self._pos)

    def _r_dquote(self):
        r = self._cache.get(('r_dquote', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        self._ch('"')
        self._cache[('r_dquote', pos)] = (self._val, self._failed, self._pos)

    def _r_escape(self):
        r = self._cache.get(('r_escape', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_escape_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_escape_2()
        if not self._failed:
            return
        self._rewind(p)
        self._s_escape_3()
        if not self._failed:
            return
        self._rewind(p)
        self._s_escape_4()
        if not self._failed:
            return
        self._rewind(p)
        self._s_escape_5()
        if not self._failed:
            return
        self._rewind(p)
        self._s_escape_6()
        if not self._failed:
            return
        self._rewind(p)
        self._s_escape_7()
        if not self._failed:
            return
        self._rewind(p)
        self._s_escape_8()
        if not self._failed:
            return
        self._rewind(p)
        self._s_escape_9()
        if not self._failed:
            return
        self._rewind(p)
        self._r_hex_esc()
        if not self._failed:
            return
        self._rewind(p)
        self._r_uni_esc()
        if not self._failed:
            return
        self._rewind(p)
        self._s_escape_10()
        self._cache[('r_escape', pos)] = (self._val, self._failed, self._pos)

    def _s_escape_1(self):
        self._str('\\b')
        if not self._failed:
            self._succeed('\b')

    def _s_escape_2(self):
        self._str('\\f')
        if not self._failed:
            self._succeed('\f')

    def _s_escape_3(self):
        self._str('\\n')
        if not self._failed:
            self._succeed('\n')

    def _s_escape_4(self):
        self._str('\\r')
        if not self._failed:
            self._succeed('\r')

    def _s_escape_5(self):
        self._str('\\t')
        if not self._failed:
            self._succeed('\t')

    def _s_escape_6(self):
        self._str('\\v')
        if not self._failed:
            self._succeed('\v')

    def _s_escape_7(self):
        self._ch('\\')
        if not self._failed:
            self._r_squote()
        if not self._failed:
            self._succeed("'")

    def _s_escape_8(self):
        self._ch('\\')
        if not self._failed:
            self._r_dquote()
        if not self._failed:
            self._succeed('"')

    def _s_escape_9(self):
        self._str('\\\\')
        if not self._failed:
            self._succeed('\\')

    def _s_escape_10(self):
        self._ch('\\')
        if not self._failed:
            self._r_any()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(v__2)

    def _r_hex_esc(self):
        r = self._cache.get(('r_hex_esc', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_hex_esc_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_hex_esc_3()
        self._cache[('r_hex_esc', pos)] = (self._val, self._failed, self._pos)

    def _s_hex_esc_1(self):
        self._str('\\x')
        if not self._failed:
            self._s_hex_esc_2()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(self._fn_xtou(self._fn_cat(v__2)))

    def _s_hex_esc_2(self):
        vs = []
        i = 0
        cmin, cmax = [2, 2]
        while i < cmax:
            self._r_hex_char()
            if self._failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self._val)
            i += 1
        self._succeed(vs)

    def _s_hex_esc_3(self):
        self._str('\\x{')
        if not self._failed:
            self._s_hex_esc_4()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._ch('}')
        if not self._failed:
            self._succeed(self._fn_xtou(self._fn_cat(v__2)))

    def _s_hex_esc_4(self):
        vs = []
        self._r_hex_char()
        vs.append(self._val)
        if self._failed:
            return
        while True:
            p = self._pos
            self._r_hex_char()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _r_uni_esc(self):
        r = self._cache.get(('r_uni_esc', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_uni_esc_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_uni_esc_3()
        if not self._failed:
            return
        self._rewind(p)
        self._s_uni_esc_5()
        self._cache[('r_uni_esc', pos)] = (self._val, self._failed, self._pos)

    def _s_uni_esc_1(self):
        self._str('\\u')
        if not self._failed:
            self._s_uni_esc_2()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(self._fn_xtou(self._fn_cat(v__2)))

    def _s_uni_esc_2(self):
        vs = []
        i = 0
        cmin, cmax = [4, 4]
        while i < cmax:
            self._r_hex_char()
            if self._failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self._val)
            i += 1
        self._succeed(vs)

    def _s_uni_esc_3(self):
        self._str('\\u{')
        if not self._failed:
            self._s_uni_esc_4()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._ch('}')
        if not self._failed:
            self._succeed(self._fn_xtou(self._fn_cat(v__2)))

    def _s_uni_esc_4(self):
        vs = []
        self._r_hex_char()
        vs.append(self._val)
        if self._failed:
            return
        while True:
            p = self._pos
            self._r_hex_char()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _s_uni_esc_5(self):
        self._str('\\U')
        if not self._failed:
            self._s_uni_esc_6()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(self._fn_xtou(self._fn_cat(v__2)))

    def _s_uni_esc_6(self):
        vs = []
        i = 0
        cmin, cmax = [8, 8]
        while i < cmax:
            self._r_hex_char()
            if self._failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self._val)
            i += 1
        self._succeed(vs)

    def _r_set(self):
        r = self._cache.get(('r_set', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_set_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_set_3()
        self._cache[('r_set', pos)] = (self._val, self._failed, self._pos)

    def _s_set_1(self):
        self._ch('[')
        if not self._failed:
            self._ch('^')
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._s_set_2()
            if not self._failed:
                v__3 = self._val
        if not self._failed:
            self._ch(']')
        if not self._failed:
            self._succeed(self._fn_cat(self._fn_scons(v__2, v__3)))

    def _s_set_2(self):
        vs = []
        self._r_set_char()
        vs.append(self._val)
        if self._failed:
            return
        while True:
            p = self._pos
            self._r_set_char()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _s_set_3(self):
        self._ch('[')
        if not self._failed:
            self._s_set_4()
        if not self._failed:
            self._s_set_5()
            if not self._failed:
                v__3 = self._val
        if not self._failed:
            self._ch(']')
        if not self._failed:
            self._succeed(self._fn_cat(v__3))

    def _s_set_4(self):
        p = self._pos
        errpos = self._errpos
        self._ch('^')
        if self._failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self._errpos = errpos
            self._fail()

    def _s_set_5(self):
        vs = []
        self._r_set_char()
        vs.append(self._val)
        if self._failed:
            return
        while True:
            p = self._pos
            self._r_set_char()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _r_set_char(self):
        r = self._cache.get(('r_set_char', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._r_escape()
        if not self._failed:
            return
        self._rewind(p)
        self._s_set_char_1()
        if not self._failed:
            return
        self._rewind(p)
        p = self._pos
        errpos = self._errpos
        self._ch(']')
        if self._failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self._errpos = errpos
            self._fail()
        if not self._failed:
            self._r_any()
        self._cache[('r_set_char', pos)] = (self._val, self._failed, self._pos)

    def _s_set_char_1(self):
        self._str('\\]')
        if not self._failed:
            self._succeed(']')

    def _r_regexp(self):
        r = self._cache.get(('r_regexp', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        self._ch('/')
        if not self._failed:
            self._s_regexp_1()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._ch('/')
        if not self._failed:
            self._succeed(self._fn_cat(v__2))
        self._cache[('r_regexp', pos)] = (self._val, self._failed, self._pos)

    def _s_regexp_1(self):
        vs = []
        self._r_re_char()
        vs.append(self._val)
        if self._failed:
            return
        while True:
            p = self._pos
            self._r_re_char()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _r_re_char(self):
        r = self._cache.get(('r_re_char', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_re_char_1()
        if not self._failed:
            return
        self._rewind(p)
        self._r_escape()
        if not self._failed:
            return
        self._rewind(p)
        self._s_re_char_2()
        self._cache[('r_re_char', pos)] = (self._val, self._failed, self._pos)

    def _s_re_char_1(self):
        self._r_bslash()
        if not self._failed:
            self._ch('/')
        if not self._failed:
            self._succeed('/')

    def _s_re_char_2(self):
        p = '[^/]'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_zpos(self):
        r = self._cache.get(('r_zpos', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_zpos_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_zpos_2()
        self._cache[('r_zpos', pos)] = (self._val, self._failed, self._pos)

    def _s_zpos_1(self):
        self._ch('0')
        if not self._failed:
            self._succeed(0)

    def _s_zpos_2(self):
        start = self._pos
        self._s_zpos_3()
        if self._failed:
            return
        end = self._pos
        self._val = self._text[start:end]
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._succeed(self._fn_atoi(v__1))

    def _s_zpos_3(self):
        self._s_zpos_4()
        if not self._failed:
            self._s_zpos_5()

    def _s_zpos_4(self):
        p = '[1-9]'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _s_zpos_5(self):
        vs = []
        while True:
            p = self._pos
            self._s_zpos_6()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _s_zpos_6(self):
        p = '[0-9]'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_ll_expr(self):
        r = self._cache.get(('r_ll_expr', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_ll_expr_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_ll_expr_2()
        if not self._failed:
            return
        self._rewind(p)
        self._r_ll_qual()
        self._cache[('r_ll_expr', pos)] = (self._val, self._failed, self._pos)

    def _s_ll_expr_1(self):
        self._r_ll_qual()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch('+')
        if not self._failed:
            self._r_ll_expr()
            if not self._failed:
                v__3 = self._val
        if not self._failed:
            self._succeed(['ll_plus', None, [v__1, v__3]])

    def _s_ll_expr_2(self):
        self._r_ll_qual()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch('-')
        if not self._failed:
            self._r_ll_expr()
            if not self._failed:
                v__3 = self._val
        if not self._failed:
            self._succeed(['ll_minus', None, [v__1, v__3]])

    def _r_ll_exprs(self):
        r = self._cache.get(('r_ll_exprs', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_ll_exprs_1()
        if not self._failed:
            return
        self._rewind(p)
        self._succeed([])
        self._cache[('r_ll_exprs', pos)] = (self._val, self._failed, self._pos)

    def _s_ll_exprs_1(self):
        self._r_ll_expr()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._s_ll_exprs_2()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._s_ll_exprs_4()
        if not self._failed:
            self._succeed(self._fn_cons(v__1, v__2))

    def _s_ll_exprs_2(self):
        vs = []
        while True:
            p = self._pos
            self._s_ll_exprs_3()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _s_ll_exprs_3(self):
        self._r__filler()
        if not self._failed:
            self._ch(',')
        if not self._failed:
            self._r_ll_expr()

    def _s_ll_exprs_4(self):
        p = self._pos
        self._s_ll_exprs_5()
        if self._failed:
            self._succeed([], p)
        else:
            self._succeed([self._val])

    def _s_ll_exprs_5(self):
        self._r__filler()
        if not self._failed:
            self._ch(',')

    def _r_ll_qual(self):
        r = self._cache.get(('r_ll_qual', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_ll_qual_1()
        if not self._failed:
            return
        self._rewind(p)
        self._r_ll_prim()
        self._cache[('r_ll_qual', pos)] = (self._val, self._failed, self._pos)

    def _s_ll_qual_1(self):
        self._r_ll_prim()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._s_ll_qual_2()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._succeed(['ll_qual', None, self._fn_cons(v__1, v__2)])

    def _s_ll_qual_2(self):
        vs = []
        self._r_ll_post_op()
        vs.append(self._val)
        if self._failed:
            return
        while True:
            p = self._pos
            self._r_ll_post_op()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _r_ll_post_op(self):
        r = self._cache.get(('r_ll_post_op', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_ll_post_op_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_ll_post_op_2()
        self._cache[('r_ll_post_op', pos)] = (self._val, self._failed, self._pos)

    def _s_ll_post_op_1(self):
        self._r__filler()
        if not self._failed:
            self._ch('[')
        if not self._failed:
            self._r_ll_expr()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch(']')
        if not self._failed:
            self._succeed(['ll_getitem', None, [v__2]])

    def _s_ll_post_op_2(self):
        self._r__filler()
        if not self._failed:
            self._ch('(')
        if not self._failed:
            self._r_ll_exprs()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch(')')
        if not self._failed:
            self._succeed(['ll_call', None, v__2])

    def _r_ll_prim(self):
        r = self._cache.get(('r_ll_prim', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s_ll_prim_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s_ll_prim_2()
        if not self._failed:
            return
        self._rewind(p)
        self._s_ll_prim_3()
        if not self._failed:
            return
        self._rewind(p)
        self._s_ll_prim_4()
        if not self._failed:
            return
        self._rewind(p)
        self._s_ll_prim_6()
        if not self._failed:
            return
        self._rewind(p)
        self._s_ll_prim_8()
        if not self._failed:
            return
        self._rewind(p)
        self._s_ll_prim_10()
        if not self._failed:
            return
        self._rewind(p)
        self._s_ll_prim_12()
        if not self._failed:
            return
        self._rewind(p)
        self._s_ll_prim_13()
        self._cache[('r_ll_prim', pos)] = (self._val, self._failed, self._pos)

    def _s_ll_prim_1(self):
        self._r__filler()
        if not self._failed:
            self._str('false')
        if not self._failed:
            self._succeed(['ll_const', 'false', []])

    def _s_ll_prim_2(self):
        self._r__filler()
        if not self._failed:
            self._str('null')
        if not self._failed:
            self._succeed(['ll_const', 'null', []])

    def _s_ll_prim_3(self):
        self._r__filler()
        if not self._failed:
            self._str('true')
        if not self._failed:
            self._succeed(['ll_const', 'true', []])

    def _s_ll_prim_4(self):
        self._s_ll_prim_5()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._succeed(['ll_var', v__1, []])

    def _s_ll_prim_5(self):
        self._r__filler()
        if not self._failed:
            self._r_ident()

    def _s_ll_prim_6(self):
        self._s_ll_prim_7()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._succeed(['ll_num', v__1, []])

    def _s_ll_prim_7(self):
        self._r__filler()
        if not self._failed:
            self._r_hex()

    def _s_ll_prim_8(self):
        self._s_ll_prim_9()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._succeed(['ll_num', v__1, []])

    def _s_ll_prim_9(self):
        self._r__filler()
        if not self._failed:
            self._r_int()

    def _s_ll_prim_10(self):
        self._s_ll_prim_11()
        if not self._failed:
            v__1 = self._val
        if not self._failed:
            self._succeed(['ll_lit', v__1, []])

    def _s_ll_prim_11(self):
        self._r__filler()
        if not self._failed:
            self._r_lit()

    def _s_ll_prim_12(self):
        self._r__filler()
        if not self._failed:
            self._ch('(')
        if not self._failed:
            self._r_ll_expr()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch(')')
        if not self._failed:
            self._succeed(['ll_paren', None, [v__2]])

    def _s_ll_prim_13(self):
        self._r__filler()
        if not self._failed:
            self._ch('[')
        if not self._failed:
            self._r_ll_exprs()
            if not self._failed:
                v__2 = self._val
        if not self._failed:
            self._r__filler()
        if not self._failed:
            self._ch(']')
        if not self._failed:
            self._succeed(['ll_arr', None, v__2])

    def _r_int(self):
        r = self._cache.get(('r_int', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._ch('0')
        if not self._failed:
            return
        self._rewind(p)
        start = self._pos
        self._s_int_1()
        if self._failed:
            return
        end = self._pos
        self._val = self._text[start:end]
        self._cache[('r_int', pos)] = (self._val, self._failed, self._pos)

    def _s_int_1(self):
        self._s_int_2()
        if not self._failed:
            self._s_int_3()
        if not self._failed:
            self._s_int_4()

    def _s_int_2(self):
        p = self._pos
        self._ch('-')
        if self._failed:
            self._succeed([], p)
        else:
            self._succeed([self._val])

    def _s_int_3(self):
        p = '[1-9]'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _s_int_4(self):
        vs = []
        while True:
            p = self._pos
            self._s_int_5()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _s_int_5(self):
        p = '[0-9]'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_hex(self):
        r = self._cache.get(('r_hex', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        start = self._pos
        self._s_hex_1()
        if self._failed:
            return
        end = self._pos
        self._val = self._text[start:end]
        self._cache[('r_hex', pos)] = (self._val, self._failed, self._pos)

    def _s_hex_1(self):
        self._str('0x')
        if not self._failed:
            self._s_hex_2()

    def _s_hex_2(self):
        vs = []
        self._r_hex_char()
        vs.append(self._val)
        if self._failed:
            return
        while True:
            p = self._pos
            self._r_hex_char()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _r_hex_char(self):
        r = self._cache.get(('r_hex_char', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = '[0-9a-fA-F]'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()
        self._cache[('r_hex_char', pos)] = (self._val, self._failed, self._pos)

    def _r__whitespace(self):
        r = self._cache.get(('r__whitespace', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        vs = []
        self._s__whitespace_1()
        vs.append(self._val)
        if self._failed:
            return
        while True:
            p = self._pos
            self._s__whitespace_1()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)
        self._cache[('r__whitespace', pos)] = (self._val, self._failed, self._pos)

    def _s__whitespace_1(self):
        p = self._pos
        self._ch(' ')
        if not self._failed:
            return
        self._rewind(p)
        self._ch('\f')
        if not self._failed:
            return
        self._rewind(p)
        self._ch('\n')
        if not self._failed:
            return
        self._rewind(p)
        self._ch('\r')
        if not self._failed:
            return
        self._rewind(p)
        self._ch('\t')
        if not self._failed:
            return
        self._rewind(p)
        self._ch('\v')

    def _r__comment(self):
        r = self._cache.get(('r__comment', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        p = self._pos
        self._s__comment_1()
        if not self._failed:
            return
        self._rewind(p)
        self._s__comment_5()
        self._cache[('r__comment', pos)] = (self._val, self._failed, self._pos)

    def _s__comment_1(self):
        self._s__comment_2()
        if not self._failed:
            self._s__comment_3()

    def _s__comment_2(self):
        p = self._pos
        self._str('//')
        if not self._failed:
            return
        self._rewind(p)
        self._ch('#')

    def _s__comment_3(self):
        vs = []
        while True:
            p = self._pos
            self._s__comment_4()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)

    def _s__comment_4(self):
        p = '[^\r\n]'
        if p not in self._regexps:
            self._regexps[p] = re.compile(p)
        m = self._regexps[p].match(self._text, self._pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _s__comment_5(self):
        self._str('/*')
        if not self._failed:
            while True:
                self._str('*/')
                if not self._failed:
                    break
                self._r_any()
                if self._failed:
                    break

    def _r__filler(self):
        r = self._cache.get(('r__filler', self._pos))
        if r is not None:
            self._val, self._failed, self._pos = r
            return
        pos = self._pos
        vs = []
        while True:
            p = self._pos
            self._s__filler_1()
            if self._failed or self._pos == p:
                self._rewind(p)
                break
            vs.append(self._val)
        self._succeed(vs)
        self._cache[('r__filler', pos)] = (self._val, self._failed, self._pos)

    def _s__filler_1(self):
        p = self._pos
        self._r__whitespace()
        if not self._failed:
            return
        self._rewind(p)
        self._r__comment()

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

    def _err_offsets(self):
        lineno = 1
        colno = 1
        for i in range(self._errpos):
            if self._text[i] == '\n':
                lineno += 1
                colno = 1
            else:
                colno += 1
        return lineno, colno

    def _err_str(self):
        lineno, colno = self._err_offsets()
        if self._errpos == len(self._text):
            thing = 'end of input'
        else:
            thing = repr(self._text[self._errpos]).replace("'", '"')
        return '%s:%d Unexpected %s at column %d' % (
            self._path,
            lineno,
            thing,
            colno,
        )

    def _fail(self):
        self._val = None
        self._failed = True
        self._errpos = max(self._errpos, self._pos)

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

    def _fn_atoi(self, a):
        return int(a, base=10)

    def _fn_cat(self, strs):
        return ''.join(strs)

    def _fn_cons(self, hd, tl):
        return [hd] + tl

    def _fn_scons(self, hd, tl):
        return [hd] + tl

    def _fn_xtou(self, s):
        return chr(int(s, base=16))
