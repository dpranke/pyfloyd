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
        self.text = text
        self.end = len(self.text)
        self.errpos = 0
        self.failed = False
        self.path = path
        self.pos = 0
        self.val = None
        self.cache = {}
        self.regexps = {}

    def parse(self):
        self._r_grammar()
        if self.failed:
            return Result(None, self._err_str(), self.errpos)
        return Result(self.val, None, self.pos)

    def _r_grammar(self):
        r = self.cache.get(('_r_grammar', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._s_grammar_1()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._r_end()
        if not self.failed:
            self._succeed(['rules', None, v__1])
        self.cache[('_r_grammar', pos)] = (self.val, self.failed, self.pos)

    def _s_grammar_1(self):
        vs = []
        while True:
            p = self.pos
            self._r_rule()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_rule(self):
        r = self.cache.get(('_r_rule', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._s_rule_1()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch('=')
        if not self.failed:
            self._r_choice()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._succeed(['rule', v__1, [v__3]])
        self.cache[('_r_rule', pos)] = (self.val, self.failed, self.pos)

    def _s_rule_1(self):
        self._r__filler()
        if not self.failed:
            self._r_ident()

    def _r_ident(self):
        r = self.cache.get(('_r_ident', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._r_id_start()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_ident_1()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_cat(_scons(v__1, v__2)))
        self.cache[('_r_ident', pos)] = (self.val, self.failed, self.pos)

    def _s_ident_1(self):
        vs = []
        while True:
            p = self.pos
            self._r_id_continue()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_id_start(self):
        r = self.cache.get(('_r_id_start', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = '[a-zA-Z$_%]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()
        self.cache[('_r_id_start', pos)] = (self.val, self.failed, self.pos)

    def _r_id_continue(self):
        r = self.cache.get(('_r_id_continue', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._r_id_start()
        if not self.failed:
            return
        self._rewind(p)
        self._s_id_continue_1()
        self.cache[('_r_id_continue', pos)] = (self.val, self.failed, self.pos)

    def _s_id_continue_1(self):
        p = '[0-9]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_choice(self):
        r = self.cache.get(('_r_choice', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._r_seq()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_choice_1()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['choice', None, _cons(v__1, v__2)])
        self.cache[('_r_choice', pos)] = (self.val, self.failed, self.pos)

    def _s_choice_1(self):
        vs = []
        while True:
            p = self.pos
            self._s_choice_2()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_choice_2(self):
        self._r__filler()
        if not self.failed:
            self._ch('|')
        if not self.failed:
            self._r_seq()

    def _r_seq(self):
        r = self.cache.get(('_r_seq', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_seq_1()
        if not self.failed:
            return
        self._rewind(p)
        self._succeed(['empty', None, []])
        self.cache[('_r_seq', pos)] = (self.val, self.failed, self.pos)

    def _s_seq_1(self):
        self._r_expr()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_seq_2()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['seq', None, _cons(v__1, v__2)])

    def _s_seq_2(self):
        vs = []
        while True:
            p = self.pos
            self._s_seq_3()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_seq_3(self):
        self._r_expr()

    def _r_expr(self):
        r = self.cache.get(('_r_expr', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_expr_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_expr_2()
        if not self.failed:
            return
        self._rewind(p)
        self._s_expr_3()
        if not self.failed:
            return
        self._rewind(p)
        self._r_post_expr()
        self.cache[('_r_expr', pos)] = (self.val, self.failed, self.pos)

    def _s_expr_1(self):
        self._r__filler()
        if not self.failed:
            self._str('->')
        if not self.failed:
            self._r_ll_expr()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['action', None, [v__2]])

    def _s_expr_2(self):
        self._r__filler()
        if not self.failed:
            self._str('?{')
        if not self.failed:
            self._r_ll_expr()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed(['pred', None, [v__2]])

    def _s_expr_3(self):
        self._r_post_expr()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch(':')
        if not self.failed:
            self._s_expr_4()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._succeed(['label', v__3, [v__1]])

    def _s_expr_4(self):
        self._r__filler()
        if not self.failed:
            self._r_ident()

    def _r_post_expr(self):
        r = self.cache.get(('_r_post_expr', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_post_expr_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_post_expr_2()
        if not self.failed:
            return
        self._rewind(p)
        self._s_post_expr_3()
        if not self.failed:
            return
        self._rewind(p)
        self._s_post_expr_4()
        if not self.failed:
            return
        self._rewind(p)
        self._r_prim_expr()
        self.cache[('_r_post_expr', pos)] = (self.val, self.failed, self.pos)

    def _s_post_expr_1(self):
        self._r_prim_expr()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch('?')
        if not self.failed:
            self._succeed(['opt', None, [v__1]])

    def _s_post_expr_2(self):
        self._r_prim_expr()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch('*')
        if not self.failed:
            self._succeed(['star', None, [v__1]])

    def _s_post_expr_3(self):
        self._r_prim_expr()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch('+')
        if not self.failed:
            self._succeed(['plus', None, [v__1]])

    def _s_post_expr_4(self):
        self._r_prim_expr()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r_count()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['count', v__2, [v__1]])

    def _r_count(self):
        r = self.cache.get(('_r_count', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_count_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_count_4()
        self.cache[('_r_count', pos)] = (self.val, self.failed, self.pos)

    def _s_count_1(self):
        self._r__filler()
        if not self.failed:
            self._ch('{')
        if not self.failed:
            self._s_count_2()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch(',')
        if not self.failed:
            self._s_count_3()
            if not self.failed:
                v__4 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed([v__2, v__4])

    def _s_count_2(self):
        self._r__filler()
        if not self.failed:
            self._r_zpos()

    def _s_count_3(self):
        self._r__filler()
        if not self.failed:
            self._r_zpos()

    def _s_count_4(self):
        self._r__filler()
        if not self.failed:
            self._ch('{')
        if not self.failed:
            self._s_count_5()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed([v__2, v__2])

    def _s_count_5(self):
        self._r__filler()
        if not self.failed:
            self._r_zpos()

    def _r_prim_expr(self):
        r = self.cache.get(('_r_prim_expr', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_prim_expr_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_4()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_6()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_8()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_10()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_12()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_13()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_14()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_15()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_19()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_20()
        self.cache[('_r_prim_expr', pos)] = (self.val, self.failed, self.pos)

    def _s_prim_expr_1(self):
        self._s_prim_expr_2()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._str('..')
        if not self.failed:
            self._s_prim_expr_3()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._succeed(['range', [v__1, v__3], []])

    def _s_prim_expr_2(self):
        self._r__filler()
        if not self.failed:
            self._r_lit()

    def _s_prim_expr_3(self):
        self._r__filler()
        if not self.failed:
            self._r_lit()

    def _s_prim_expr_4(self):
        self._s_prim_expr_5()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['lit', v__1, []])

    def _s_prim_expr_5(self):
        self._r__filler()
        if not self.failed:
            self._r_lit()

    def _s_prim_expr_6(self):
        self._r__filler()
        if not self.failed:
            self._str('\\p{')
        if not self.failed:
            self._s_prim_expr_7()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed(['unicat', v__2, []])

    def _s_prim_expr_7(self):
        self._r__filler()
        if not self.failed:
            self._r_ident()

    def _s_prim_expr_8(self):
        self._s_prim_expr_9()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['set', v__1, []])

    def _s_prim_expr_9(self):
        self._r__filler()
        if not self.failed:
            self._r_set()

    def _s_prim_expr_10(self):
        self._s_prim_expr_11()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['regexp', v__1, []])

    def _s_prim_expr_11(self):
        self._r__filler()
        if not self.failed:
            self._r_regexp()

    def _s_prim_expr_12(self):
        self._r__filler()
        if not self.failed:
            self._ch('\x7e')
        if not self.failed:
            self._r_prim_expr()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['not', None, [v__2]])

    def _s_prim_expr_13(self):
        self._r__filler()
        if not self.failed:
            self._str('^.')
        if not self.failed:
            self._r_prim_expr()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['ends_in', None, [v__2]])

    def _s_prim_expr_14(self):
        self._r__filler()
        if not self.failed:
            self._ch('^')
        if not self.failed:
            self._r_prim_expr()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['not_one', None, [v__2]])

    def _s_prim_expr_15(self):
        self._s_prim_expr_16()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_prim_expr_17()
        if not self.failed:
            self._succeed(['apply', v__1, []])

    def _s_prim_expr_16(self):
        self._r__filler()
        if not self.failed:
            self._r_ident()

    def _s_prim_expr_17(self):
        p = self.pos
        errpos = self.errpos
        self._s_prim_expr_18()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _s_prim_expr_18(self):
        self._r__filler()
        if not self.failed:
            self._ch('=')

    def _s_prim_expr_19(self):
        self._r__filler()
        if not self.failed:
            self._ch('(')
        if not self.failed:
            self._r_choice()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch(')')
        if not self.failed:
            self._succeed(['paren', None, [v__2]])

    def _s_prim_expr_20(self):
        self._r__filler()
        if not self.failed:
            self._ch('<')
        if not self.failed:
            self._r_choice()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch('>')
        if not self.failed:
            self._succeed(['run', None, [v__2]])

    def _r_lit(self):
        r = self.cache.get(('_r_lit', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_lit_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_lit_3()
        self.cache[('_r_lit', pos)] = (self.val, self.failed, self.pos)

    def _s_lit_1(self):
        self._r_squote()
        if not self.failed:
            self._s_lit_2()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r_squote()
        if not self.failed:
            self._succeed(_cat(v__2))

    def _s_lit_2(self):
        vs = []
        while True:
            p = self.pos
            self._r_sqchar()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_lit_3(self):
        self._r_dquote()
        if not self.failed:
            self._s_lit_4()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r_dquote()
        if not self.failed:
            self._succeed(_cat(v__2))

    def _s_lit_4(self):
        vs = []
        while True:
            p = self.pos
            self._r_dqchar()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_sqchar(self):
        r = self.cache.get(('_r_sqchar', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._r_escape()
        if not self.failed:
            return
        self._rewind(p)
        p = self.pos
        errpos = self.errpos
        self._r_squote()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()
        if not self.failed:
            self._r_any()
        self.cache[('_r_sqchar', pos)] = (self.val, self.failed, self.pos)

    def _r_dqchar(self):
        r = self.cache.get(('_r_dqchar', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._r_escape()
        if not self.failed:
            return
        self._rewind(p)
        p = self.pos
        errpos = self.errpos
        self._r_dquote()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()
        if not self.failed:
            self._r_any()
        self.cache[('_r_dqchar', pos)] = (self.val, self.failed, self.pos)

    def _r_bslash(self):
        r = self.cache.get(('_r_bslash', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._ch('\\')
        self.cache[('_r_bslash', pos)] = (self.val, self.failed, self.pos)

    def _r_squote(self):
        r = self.cache.get(('_r_squote', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._ch("'")
        self.cache[('_r_squote', pos)] = (self.val, self.failed, self.pos)

    def _r_dquote(self):
        r = self.cache.get(('_r_dquote', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._ch('"')
        self.cache[('_r_dquote', pos)] = (self.val, self.failed, self.pos)

    def _r_escape(self):
        r = self.cache.get(('_r_escape', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_escape_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_2()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_3()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_4()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_5()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_6()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_7()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_8()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_9()
        if not self.failed:
            return
        self._rewind(p)
        self._r_hex_esc()
        if not self.failed:
            return
        self._rewind(p)
        self._r_uni_esc()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_10()
        self.cache[('_r_escape', pos)] = (self.val, self.failed, self.pos)

    def _s_escape_1(self):
        self._str('\\b')
        if not self.failed:
            self._succeed('\b')

    def _s_escape_2(self):
        self._str('\\f')
        if not self.failed:
            self._succeed('\f')

    def _s_escape_3(self):
        self._str('\\n')
        if not self.failed:
            self._succeed('\n')

    def _s_escape_4(self):
        self._str('\\r')
        if not self.failed:
            self._succeed('\r')

    def _s_escape_5(self):
        self._str('\\t')
        if not self.failed:
            self._succeed('\t')

    def _s_escape_6(self):
        self._str('\\v')
        if not self.failed:
            self._succeed('\v')

    def _s_escape_7(self):
        self._ch('\\')
        if not self.failed:
            self._r_squote()
        if not self.failed:
            self._succeed("'")

    def _s_escape_8(self):
        self._ch('\\')
        if not self.failed:
            self._r_dquote()
        if not self.failed:
            self._succeed('"')

    def _s_escape_9(self):
        self._str('\\\\')
        if not self.failed:
            self._succeed('\\')

    def _s_escape_10(self):
        self._ch('\\')
        if not self.failed:
            self._r_any()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(v__2)

    def _r_hex_esc(self):
        r = self.cache.get(('_r_hex_esc', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_hex_esc_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_hex_esc_3()
        self.cache[('_r_hex_esc', pos)] = (self.val, self.failed, self.pos)

    def _s_hex_esc_1(self):
        self._str('\\x')
        if not self.failed:
            self._s_hex_esc_2()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_xtou(_cat(v__2)))

    def _s_hex_esc_2(self):
        vs = []
        i = 0
        cmin, cmax = [2, 2]
        while i < cmax:
            self._r_hex_char()
            if self.failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self.val)
            i += 1
        self._succeed(vs)

    def _s_hex_esc_3(self):
        self._str('\\x{')
        if not self.failed:
            self._s_hex_esc_4()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed(_xtou(_cat(v__2)))

    def _s_hex_esc_4(self):
        vs = []
        self._r_hex_char()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_hex_char()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_uni_esc(self):
        r = self.cache.get(('_r_uni_esc', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_uni_esc_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_uni_esc_3()
        if not self.failed:
            return
        self._rewind(p)
        self._s_uni_esc_5()
        self.cache[('_r_uni_esc', pos)] = (self.val, self.failed, self.pos)

    def _s_uni_esc_1(self):
        self._str('\\u')
        if not self.failed:
            self._s_uni_esc_2()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_xtou(_cat(v__2)))

    def _s_uni_esc_2(self):
        vs = []
        i = 0
        cmin, cmax = [4, 4]
        while i < cmax:
            self._r_hex_char()
            if self.failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self.val)
            i += 1
        self._succeed(vs)

    def _s_uni_esc_3(self):
        self._str('\\u{')
        if not self.failed:
            self._s_uni_esc_4()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed(_xtou(_cat(v__2)))

    def _s_uni_esc_4(self):
        vs = []
        self._r_hex_char()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_hex_char()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_uni_esc_5(self):
        self._str('\\U')
        if not self.failed:
            self._s_uni_esc_6()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_xtou(_cat(v__2)))

    def _s_uni_esc_6(self):
        vs = []
        i = 0
        cmin, cmax = [8, 8]
        while i < cmax:
            self._r_hex_char()
            if self.failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self.val)
            i += 1
        self._succeed(vs)

    def _r_set(self):
        r = self.cache.get(('_r_set', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_set_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_set_3()
        self.cache[('_r_set', pos)] = (self.val, self.failed, self.pos)

    def _s_set_1(self):
        self._ch('[')
        if not self.failed:
            self._ch('^')
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._s_set_2()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._ch(']')
        if not self.failed:
            self._succeed(_cat(_scons(v__2, v__3)))

    def _s_set_2(self):
        vs = []
        self._r_set_char()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_set_char()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_set_3(self):
        self._ch('[')
        if not self.failed:
            self._s_set_4()
        if not self.failed:
            self._s_set_5()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._ch(']')
        if not self.failed:
            self._succeed(_cat(v__3))

    def _s_set_4(self):
        p = self.pos
        errpos = self.errpos
        self._ch('^')
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _s_set_5(self):
        vs = []
        self._r_set_char()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_set_char()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_set_char(self):
        r = self.cache.get(('_r_set_char', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._r_escape()
        if not self.failed:
            return
        self._rewind(p)
        self._s_set_char_1()
        if not self.failed:
            return
        self._rewind(p)
        p = self.pos
        errpos = self.errpos
        self._ch(']')
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()
        if not self.failed:
            self._r_any()
        self.cache[('_r_set_char', pos)] = (self.val, self.failed, self.pos)

    def _s_set_char_1(self):
        self._str('\\]')
        if not self.failed:
            self._succeed(']')

    def _r_regexp(self):
        r = self.cache.get(('_r_regexp', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._ch('/')
        if not self.failed:
            self._s_regexp_1()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._ch('/')
        if not self.failed:
            self._succeed(_cat(v__2))
        self.cache[('_r_regexp', pos)] = (self.val, self.failed, self.pos)

    def _s_regexp_1(self):
        vs = []
        self._r_re_char()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_re_char()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_re_char(self):
        r = self.cache.get(('_r_re_char', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_re_char_1()
        if not self.failed:
            return
        self._rewind(p)
        self._r_escape()
        if not self.failed:
            return
        self._rewind(p)
        self._s_re_char_2()
        self.cache[('_r_re_char', pos)] = (self.val, self.failed, self.pos)

    def _s_re_char_1(self):
        self._r_bslash()
        if not self.failed:
            self._ch('/')
        if not self.failed:
            self._succeed('/')

    def _s_re_char_2(self):
        p = '[^/]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_zpos(self):
        r = self.cache.get(('_r_zpos', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_zpos_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_zpos_2()
        self.cache[('_r_zpos', pos)] = (self.val, self.failed, self.pos)

    def _s_zpos_1(self):
        self._ch('0')
        if not self.failed:
            self._succeed(0)

    def _s_zpos_2(self):
        start = self.pos
        self._s_zpos_3()
        if self.failed:
            return
        end = self.pos
        self.val = self.text[start:end]
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(_atoi(v__1))

    def _s_zpos_3(self):
        self._s_zpos_4()
        if not self.failed:
            self._s_zpos_5()

    def _s_zpos_4(self):
        p = '[1-9]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _s_zpos_5(self):
        vs = []
        while True:
            p = self.pos
            self._s_zpos_6()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_zpos_6(self):
        p = '[0-9]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_ll_expr(self):
        r = self.cache.get(('_r_ll_expr', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_ll_expr_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_expr_2()
        if not self.failed:
            return
        self._rewind(p)
        self._r_ll_qual()
        self.cache[('_r_ll_expr', pos)] = (self.val, self.failed, self.pos)

    def _s_ll_expr_1(self):
        self._r_ll_qual()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch('+')
        if not self.failed:
            self._r_ll_expr()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._succeed(['ll_plus', None, [v__1, v__3]])

    def _s_ll_expr_2(self):
        self._r_ll_qual()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch('-')
        if not self.failed:
            self._r_ll_expr()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._succeed(['ll_minus', None, [v__1, v__3]])

    def _r_ll_exprs(self):
        r = self.cache.get(('_r_ll_exprs', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_ll_exprs_1()
        if not self.failed:
            return
        self._rewind(p)
        self._succeed([])
        self.cache[('_r_ll_exprs', pos)] = (self.val, self.failed, self.pos)

    def _s_ll_exprs_1(self):
        self._r_ll_expr()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_ll_exprs_2()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._s_ll_exprs_4()
        if not self.failed:
            self._succeed(_cons(v__1, v__2))

    def _s_ll_exprs_2(self):
        vs = []
        while True:
            p = self.pos
            self._s_ll_exprs_3()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_ll_exprs_3(self):
        self._r__filler()
        if not self.failed:
            self._ch(',')
        if not self.failed:
            self._r_ll_expr()

    def _s_ll_exprs_4(self):
        p = self.pos
        self._s_ll_exprs_5()
        if self.failed:
            self._succeed([], p)
        else:
            self._succeed([self.val])

    def _s_ll_exprs_5(self):
        self._r__filler()
        if not self.failed:
            self._ch(',')

    def _r_ll_qual(self):
        r = self.cache.get(('_r_ll_qual', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_ll_qual_1()
        if not self.failed:
            return
        self._rewind(p)
        self._r_ll_prim()
        self.cache[('_r_ll_qual', pos)] = (self.val, self.failed, self.pos)

    def _s_ll_qual_1(self):
        self._r_ll_prim()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_ll_qual_2()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['ll_qual', None, _cons(v__1, v__2)])

    def _s_ll_qual_2(self):
        vs = []
        self._r_ll_post_op()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_ll_post_op()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_ll_post_op(self):
        r = self.cache.get(('_r_ll_post_op', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_ll_post_op_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_post_op_2()
        self.cache[('_r_ll_post_op', pos)] = (self.val, self.failed, self.pos)

    def _s_ll_post_op_1(self):
        self._r__filler()
        if not self.failed:
            self._ch('[')
        if not self.failed:
            self._r_ll_expr()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch(']')
        if not self.failed:
            self._succeed(['ll_getitem', None, [v__2]])

    def _s_ll_post_op_2(self):
        self._r__filler()
        if not self.failed:
            self._ch('(')
        if not self.failed:
            self._r_ll_exprs()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch(')')
        if not self.failed:
            self._succeed(['ll_call', None, v__2])

    def _r_ll_prim(self):
        r = self.cache.get(('_r_ll_prim', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_ll_prim_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_2()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_3()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_4()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_6()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_8()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_10()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_12()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_13()
        self.cache[('_r_ll_prim', pos)] = (self.val, self.failed, self.pos)

    def _s_ll_prim_1(self):
        self._r__filler()
        if not self.failed:
            self._str('false')
        if not self.failed:
            self._succeed(['ll_const', 'false', []])

    def _s_ll_prim_2(self):
        self._r__filler()
        if not self.failed:
            self._str('null')
        if not self.failed:
            self._succeed(['ll_const', 'null', []])

    def _s_ll_prim_3(self):
        self._r__filler()
        if not self.failed:
            self._str('true')
        if not self.failed:
            self._succeed(['ll_const', 'true', []])

    def _s_ll_prim_4(self):
        self._s_ll_prim_5()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['ll_var', v__1, []])

    def _s_ll_prim_5(self):
        self._r__filler()
        if not self.failed:
            self._r_ident()

    def _s_ll_prim_6(self):
        self._s_ll_prim_7()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['ll_num', v__1, []])

    def _s_ll_prim_7(self):
        self._r__filler()
        if not self.failed:
            self._r_hex()

    def _s_ll_prim_8(self):
        self._s_ll_prim_9()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['ll_num', v__1, []])

    def _s_ll_prim_9(self):
        self._r__filler()
        if not self.failed:
            self._r_int()

    def _s_ll_prim_10(self):
        self._s_ll_prim_11()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['ll_lit', v__1, []])

    def _s_ll_prim_11(self):
        self._r__filler()
        if not self.failed:
            self._r_lit()

    def _s_ll_prim_12(self):
        self._r__filler()
        if not self.failed:
            self._ch('(')
        if not self.failed:
            self._r_ll_expr()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch(')')
        if not self.failed:
            self._succeed(['ll_paren', None, [v__2]])

    def _s_ll_prim_13(self):
        self._r__filler()
        if not self.failed:
            self._ch('[')
        if not self.failed:
            self._r_ll_exprs()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler()
        if not self.failed:
            self._ch(']')
        if not self.failed:
            self._succeed(['ll_arr', None, v__2])

    def _r_int(self):
        r = self.cache.get(('_r_int', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._ch('0')
        if not self.failed:
            return
        self._rewind(p)
        start = self.pos
        self._s_int_1()
        if self.failed:
            return
        end = self.pos
        self.val = self.text[start:end]
        self.cache[('_r_int', pos)] = (self.val, self.failed, self.pos)

    def _s_int_1(self):
        self._s_int_2()
        if not self.failed:
            self._s_int_3()
        if not self.failed:
            self._s_int_4()

    def _s_int_2(self):
        p = self.pos
        self._ch('-')
        if self.failed:
            self._succeed([], p)
        else:
            self._succeed([self.val])

    def _s_int_3(self):
        p = '[1-9]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _s_int_4(self):
        vs = []
        while True:
            p = self.pos
            self._s_int_5()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_int_5(self):
        p = '[0-9]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_hex(self):
        r = self.cache.get(('_r_hex', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        start = self.pos
        self._s_hex_1()
        if self.failed:
            return
        end = self.pos
        self.val = self.text[start:end]
        self.cache[('_r_hex', pos)] = (self.val, self.failed, self.pos)

    def _s_hex_1(self):
        self._str('0x')
        if not self.failed:
            self._s_hex_2()

    def _s_hex_2(self):
        vs = []
        self._r_hex_char()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_hex_char()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_hex_char(self):
        r = self.cache.get(('_r_hex_char', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = '[0-9a-fA-F]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()
        self.cache[('_r_hex_char', pos)] = (self.val, self.failed, self.pos)

    def _r__whitespace(self):
        r = self.cache.get(('_r__whitespace', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        vs = []
        self._s__whitespace_1()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._s__whitespace_1()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)
        self.cache[('_r__whitespace', pos)] = (self.val, self.failed, self.pos)

    def _s__whitespace_1(self):
        p = self.pos
        self._ch(' ')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('\f')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('\n')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('\r')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('\t')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('\v')

    def _r__comment(self):
        r = self.cache.get(('_r__comment', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s__comment_1()
        if not self.failed:
            return
        self._rewind(p)
        self._s__comment_5()
        self.cache[('_r__comment', pos)] = (self.val, self.failed, self.pos)

    def _s__comment_1(self):
        self._s__comment_2()
        if not self.failed:
            self._s__comment_3()

    def _s__comment_2(self):
        p = self.pos
        self._str('//')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('#')

    def _s__comment_3(self):
        vs = []
        while True:
            p = self.pos
            self._s__comment_4()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s__comment_4(self):
        p = '[^\r\n]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _s__comment_5(self):
        self._str('/*')
        if not self.failed:
            while True:
                self._str('*/')
                if not self.failed:
                    break
                self._r_any()
                if self.failed:
                    break

    def _r__filler(self):
        r = self.cache.get(('_r__filler', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        vs = []
        while True:
            p = self.pos
            self._s__filler_1()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)
        self.cache[('_r__filler', pos)] = (self.val, self.failed, self.pos)

    def _s__filler_1(self):
        p = self.pos
        self._r__whitespace()
        if not self.failed:
            return
        self._rewind(p)
        self._r__comment()

    def _r_any(self):
        if self.pos < self.end:
            self._succeed(self.text[self.pos], self.pos + 1)
        else:
            self._fail()

    def _r_end(self):
        if self.pos == self.end:
            self._succeed(None)
        else:
            self._fail()

    def _ch(self, ch):
        p = self.pos
        if p < self.end and self.text[p] == ch:
            self._succeed(ch, self.pos + 1)
        else:
            self._fail()

    def _err_offsets(self):
        lineno = 1
        colno = 1
        for i in range(self.errpos):
            if self.text[i] == '\n':
                lineno += 1
                colno = 1
            else:
                colno += 1
        return lineno, colno

    def _err_str(self):
        lineno, colno = self._err_offsets()
        if self.errpos == len(self.text):
            thing = 'end of input'
        else:
            thing = repr(self.text[self.errpos]).replace("'", '"')
        return '%s:%d Unexpected %s at column %d' % (
            self.path,
            lineno,
            thing,
            colno,
        )

    def _fail(self):
        self.val = None
        self.failed = True
        self.errpos = max(self.errpos, self.pos)

    def _rewind(self, newpos):
        self._succeed(None, newpos)

    def _str(self, s):
        for ch in s:
            self._ch(ch)
            if self.failed:
                return
        self.val = s

    def _succeed(self, v, newpos=None):
        self.val = v
        self.failed = False
        if newpos is not None:
            self.pos = newpos


def _atoi(a):
    return int(a, base=10)


def _cat(strs):
    return ''.join(strs)


def _cons(hd, tl):
    return [hd] + tl


def _scons(hd, tl):
    return [hd] + tl


def _xtou(s):
    return chr(int(s, base=16))
