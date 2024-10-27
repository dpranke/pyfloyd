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
        self._r_grammar_()
        if self.failed:
            return Result(None, self._err_str(), self.errpos)
        return Result(self.val, None, self.pos)

    def _r_grammar_(self):
        r = self.cache.get(('_r_grammar_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._s_grammar_1_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._r_end_()
        if not self.failed:
            self._succeed(['rules', None, v__1])
        self.cache[('_r_grammar_', pos)] = (self.val, self.failed, self.pos)

    def _s_grammar_1_(self):
        vs = []
        while True:
            p = self.pos
            self._r_rule_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_rule_(self):
        r = self.cache.get(('_r_rule_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._s_rule_1_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch('=')
        if not self.failed:
            self._r_choice_()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._succeed(['rule', v__1, [v__3]])
        self.cache[('_r_rule_', pos)] = (self.val, self.failed, self.pos)

    def _s_rule_1_(self):
        self._r__filler_()
        if not self.failed:
            self._r_ident_()

    def _r_ident_(self):
        r = self.cache.get(('_r_ident_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._r_id_start_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_ident_1_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_cat(_scons(v__1, v__2)))
        self.cache[('_r_ident_', pos)] = (self.val, self.failed, self.pos)

    def _s_ident_1_(self):
        vs = []
        while True:
            p = self.pos
            self._r_id_continue_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_id_start_(self):
        r = self.cache.get(('_r_id_start_', self.pos))
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
        self.cache[('_r_id_start_', pos)] = (self.val, self.failed, self.pos)

    def _r_id_continue_(self):
        r = self.cache.get(('_r_id_continue_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._r_id_start_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_id_continue_1_()
        self.cache[('_r_id_continue_', pos)] = (self.val, self.failed, self.pos)

    def _s_id_continue_1_(self):
        p = '[0-9]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_choice_(self):
        r = self.cache.get(('_r_choice_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._r_seq_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_choice_1_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['choice', None, _cons(v__1, v__2)])
        self.cache[('_r_choice_', pos)] = (self.val, self.failed, self.pos)

    def _s_choice_1_(self):
        vs = []
        while True:
            p = self.pos
            self._s_choice_2_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_choice_2_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('|')
        if not self.failed:
            self._r_seq_()

    def _r_seq_(self):
        r = self.cache.get(('_r_seq_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_seq_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._succeed(['empty', None, []])
        self.cache[('_r_seq_', pos)] = (self.val, self.failed, self.pos)

    def _s_seq_1_(self):
        self._r_expr_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_seq_2_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['seq', None, _cons(v__1, v__2)])

    def _s_seq_2_(self):
        vs = []
        while True:
            p = self.pos
            self._s_seq_3_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_seq_3_(self):
        self._r_expr_()

    def _r_expr_(self):
        r = self.cache.get(('_r_expr_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_expr_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_expr_2_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_expr_3_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_expr_4_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_post_expr_()
        self.cache[('_r_expr_', pos)] = (self.val, self.failed, self.pos)

    def _s_expr_1_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('<')
        if not self.failed:
            self._r_choice_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch('>')
        if not self.failed:
            self._succeed(['run', None, [v__2]])

    def _s_expr_2_(self):
        self._r__filler_()
        if not self.failed:
            self._str('->')
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['action', None, [v__2]])

    def _s_expr_3_(self):
        self._r__filler_()
        if not self.failed:
            self._str('?{')
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed(['pred', None, [v__2]])

    def _s_expr_4_(self):
        self._r_post_expr_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch(':')
        if not self.failed:
            self._s_expr_5_()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._succeed(['label', v__3, [v__1]])

    def _s_expr_5_(self):
        self._r__filler_()
        if not self.failed:
            self._r_ident_()

    def _r_post_expr_(self):
        r = self.cache.get(('_r_post_expr_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_post_expr_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_post_expr_3_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_post_expr_5_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_post_expr_7_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_prim_expr_()
        self.cache[('_r_post_expr_', pos)] = (self.val, self.failed, self.pos)

    def _s_post_expr_1_(self):
        self._r_prim_expr_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_post_expr_2_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['post', v__2, [v__1]])

    def _s_post_expr_2_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('?')

    def _s_post_expr_3_(self):
        self._r_prim_expr_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_post_expr_4_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['post', v__2, [v__1]])

    def _s_post_expr_4_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('*')

    def _s_post_expr_5_(self):
        self._r_prim_expr_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_post_expr_6_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['post', v__2, [v__1]])

    def _s_post_expr_6_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('+')

    def _s_post_expr_7_(self):
        self._r_prim_expr_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r_count_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['count', v__2, [v__1]])

    def _r_count_(self):
        r = self.cache.get(('_r_count_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_count_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_count_4_()
        self.cache[('_r_count_', pos)] = (self.val, self.failed, self.pos)

    def _s_count_1_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('{')
        if not self.failed:
            self._s_count_2_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch(',')
        if not self.failed:
            self._s_count_3_()
            if not self.failed:
                v__4 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed([v__2, v__4])

    def _s_count_2_(self):
        self._r__filler_()
        if not self.failed:
            self._r_zpos_()

    def _s_count_3_(self):
        self._r__filler_()
        if not self.failed:
            self._r_zpos_()

    def _s_count_4_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('{')
        if not self.failed:
            self._s_count_5_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed([v__2, v__2])

    def _s_count_5_(self):
        self._r__filler_()
        if not self.failed:
            self._r_zpos_()

    def _r_prim_expr_(self):
        r = self.cache.get(('_r_prim_expr_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_prim_expr_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_4_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_6_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_8_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_10_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_12_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_13_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_14_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_15_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_19_()
        self.cache[('_r_prim_expr_', pos)] = (self.val, self.failed, self.pos)

    def _s_prim_expr_1_(self):
        self._s_prim_expr_2_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._str('..')
        if not self.failed:
            self._s_prim_expr_3_()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._succeed(['range', [v__1, v__3], []])

    def _s_prim_expr_2_(self):
        self._r__filler_()
        if not self.failed:
            self._r_lit_()

    def _s_prim_expr_3_(self):
        self._r__filler_()
        if not self.failed:
            self._r_lit_()

    def _s_prim_expr_4_(self):
        self._s_prim_expr_5_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['lit', v__1, []])

    def _s_prim_expr_5_(self):
        self._r__filler_()
        if not self.failed:
            self._r_lit_()

    def _s_prim_expr_6_(self):
        self._r__filler_()
        if not self.failed:
            self._str('\\p{')
        if not self.failed:
            self._s_prim_expr_7_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed(['unicat', v__2, []])

    def _s_prim_expr_7_(self):
        self._r__filler_()
        if not self.failed:
            self._r_ident_()

    def _s_prim_expr_8_(self):
        self._s_prim_expr_9_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['set', v__1, []])

    def _s_prim_expr_9_(self):
        self._r__filler_()
        if not self.failed:
            self._r_set_()

    def _s_prim_expr_10_(self):
        self._s_prim_expr_11_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['regexp', v__1, []])

    def _s_prim_expr_11_(self):
        self._r__filler_()
        if not self.failed:
            self._r_regexp_()

    def _s_prim_expr_12_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('\x7e')
        if not self.failed:
            self._r_prim_expr_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['not', None, [v__2]])

    def _s_prim_expr_13_(self):
        self._r__filler_()
        if not self.failed:
            self._str('^.')
        if not self.failed:
            self._r_prim_expr_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['ends_in', None, [v__2]])

    def _s_prim_expr_14_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('^')
        if not self.failed:
            self._r_prim_expr_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['not_one', None, [v__2]])

    def _s_prim_expr_15_(self):
        self._s_prim_expr_16_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_prim_expr_17_()
        if not self.failed:
            self._succeed(['apply', v__1, []])

    def _s_prim_expr_16_(self):
        self._r__filler_()
        if not self.failed:
            self._r_ident_()

    def _s_prim_expr_17_(self):
        p = self.pos
        errpos = self.errpos
        self._s_prim_expr_18_()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _s_prim_expr_18_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('=')

    def _s_prim_expr_19_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('(')
        if not self.failed:
            self._r_choice_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch(')')
        if not self.failed:
            self._succeed(['paren', None, [v__2]])

    def _r_lit_(self):
        r = self.cache.get(('_r_lit_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_lit_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_lit_3_()
        self.cache[('_r_lit_', pos)] = (self.val, self.failed, self.pos)

    def _s_lit_1_(self):
        self._r_squote_()
        if not self.failed:
            self._s_lit_2_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r_squote_()
        if not self.failed:
            self._succeed(_cat(v__2))

    def _s_lit_2_(self):
        vs = []
        while True:
            p = self.pos
            self._r_sqchar_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_lit_3_(self):
        self._r_dquote_()
        if not self.failed:
            self._s_lit_4_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r_dquote_()
        if not self.failed:
            self._succeed(_cat(v__2))

    def _s_lit_4_(self):
        vs = []
        while True:
            p = self.pos
            self._r_dqchar_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_sqchar_(self):
        r = self.cache.get(('_r_sqchar_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._r_escape_()
        if not self.failed:
            return
        self._rewind(p)
        p = self.pos
        errpos = self.errpos
        self._r_squote_()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()
        if not self.failed:
            self._r_any_()
        self.cache[('_r_sqchar_', pos)] = (self.val, self.failed, self.pos)

    def _r_dqchar_(self):
        r = self.cache.get(('_r_dqchar_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._r_escape_()
        if not self.failed:
            return
        self._rewind(p)
        p = self.pos
        errpos = self.errpos
        self._r_dquote_()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()
        if not self.failed:
            self._r_any_()
        self.cache[('_r_dqchar_', pos)] = (self.val, self.failed, self.pos)

    def _r_bslash_(self):
        r = self.cache.get(('_r_bslash_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._ch('\\')
        self.cache[('_r_bslash_', pos)] = (self.val, self.failed, self.pos)

    def _r_squote_(self):
        r = self.cache.get(('_r_squote_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._ch("'")
        self.cache[('_r_squote_', pos)] = (self.val, self.failed, self.pos)

    def _r_dquote_(self):
        r = self.cache.get(('_r_dquote_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._ch('"')
        self.cache[('_r_dquote_', pos)] = (self.val, self.failed, self.pos)

    def _r_escape_(self):
        r = self.cache.get(('_r_escape_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_escape_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_2_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_3_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_4_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_5_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_6_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_7_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_8_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_9_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_hex_esc_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_uni_esc_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_escape_10_()
        self.cache[('_r_escape_', pos)] = (self.val, self.failed, self.pos)

    def _s_escape_1_(self):
        self._str('\\b')
        if not self.failed:
            self._succeed('\b')

    def _s_escape_2_(self):
        self._str('\\f')
        if not self.failed:
            self._succeed('\f')

    def _s_escape_3_(self):
        self._str('\\n')
        if not self.failed:
            self._succeed('\n')

    def _s_escape_4_(self):
        self._str('\\r')
        if not self.failed:
            self._succeed('\r')

    def _s_escape_5_(self):
        self._str('\\t')
        if not self.failed:
            self._succeed('\t')

    def _s_escape_6_(self):
        self._str('\\v')
        if not self.failed:
            self._succeed('\v')

    def _s_escape_7_(self):
        self._ch('\\')
        if not self.failed:
            self._r_squote_()
        if not self.failed:
            self._succeed("'")

    def _s_escape_8_(self):
        self._ch('\\')
        if not self.failed:
            self._r_dquote_()
        if not self.failed:
            self._succeed('"')

    def _s_escape_9_(self):
        self._str('\\\\')
        if not self.failed:
            self._succeed('\\')

    def _s_escape_10_(self):
        self._ch('\\')
        if not self.failed:
            self._r_any_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(v__2)

    def _r_hex_esc_(self):
        r = self.cache.get(('_r_hex_esc_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_hex_esc_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_hex_esc_3_()
        self.cache[('_r_hex_esc_', pos)] = (self.val, self.failed, self.pos)

    def _s_hex_esc_1_(self):
        self._str('\\x')
        if not self.failed:
            self._s_hex_esc_2_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_xtou(_cat(v__2)))

    def _s_hex_esc_2_(self):
        vs = []
        i = 0
        cmin, cmax = [2, 2]
        while i < cmax:
            self._r_hex_char_()
            if self.failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self.val)
            i += 1
        self._succeed(vs)

    def _s_hex_esc_3_(self):
        self._str('\\x{')
        if not self.failed:
            self._s_hex_esc_4_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed(_xtou(_cat(v__2)))

    def _s_hex_esc_4_(self):
        vs = []
        self._r_hex_char_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_hex_char_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_uni_esc_(self):
        r = self.cache.get(('_r_uni_esc_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_uni_esc_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_uni_esc_3_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_uni_esc_5_()
        self.cache[('_r_uni_esc_', pos)] = (self.val, self.failed, self.pos)

    def _s_uni_esc_1_(self):
        self._str('\\u')
        if not self.failed:
            self._s_uni_esc_2_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_xtou(_cat(v__2)))

    def _s_uni_esc_2_(self):
        vs = []
        i = 0
        cmin, cmax = [4, 4]
        while i < cmax:
            self._r_hex_char_()
            if self.failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self.val)
            i += 1
        self._succeed(vs)

    def _s_uni_esc_3_(self):
        self._str('\\u{')
        if not self.failed:
            self._s_uni_esc_4_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed(_xtou(_cat(v__2)))

    def _s_uni_esc_4_(self):
        vs = []
        self._r_hex_char_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_hex_char_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_uni_esc_5_(self):
        self._str('\\U')
        if not self.failed:
            self._s_uni_esc_6_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_xtou(_cat(v__2)))

    def _s_uni_esc_6_(self):
        vs = []
        i = 0
        cmin, cmax = [8, 8]
        while i < cmax:
            self._r_hex_char_()
            if self.failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self.val)
            i += 1
        self._succeed(vs)

    def _r_set_(self):
        r = self.cache.get(('_r_set_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_set_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_set_3_()
        self.cache[('_r_set_', pos)] = (self.val, self.failed, self.pos)

    def _s_set_1_(self):
        self._ch('[')
        if not self.failed:
            self._ch('^')
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._s_set_2_()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._ch(']')
        if not self.failed:
            self._succeed(_cat(_scons(v__2, v__3)))

    def _s_set_2_(self):
        vs = []
        self._r_set_char_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_set_char_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_set_3_(self):
        self._ch('[')
        if not self.failed:
            self._s_set_4_()
        if not self.failed:
            self._s_set_5_()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._ch(']')
        if not self.failed:
            self._succeed(_cat(v__3))

    def _s_set_4_(self):
        p = self.pos
        errpos = self.errpos
        self._ch('^')
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _s_set_5_(self):
        vs = []
        self._r_set_char_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_set_char_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_set_char_(self):
        r = self.cache.get(('_r_set_char_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._r_escape_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_set_char_1_()
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
            self._r_any_()
        self.cache[('_r_set_char_', pos)] = (self.val, self.failed, self.pos)

    def _s_set_char_1_(self):
        self._str('\\]')
        if not self.failed:
            self._succeed(']')

    def _r_regexp_(self):
        r = self.cache.get(('_r_regexp_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        self._ch('/')
        if not self.failed:
            self._s_regexp_1_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._ch('/')
        if not self.failed:
            self._succeed(_cat(v__2))
        self.cache[('_r_regexp_', pos)] = (self.val, self.failed, self.pos)

    def _s_regexp_1_(self):
        vs = []
        self._r_re_char_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_re_char_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_re_char_(self):
        r = self.cache.get(('_r_re_char_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_re_char_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_escape_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_re_char_2_()
        self.cache[('_r_re_char_', pos)] = (self.val, self.failed, self.pos)

    def _s_re_char_1_(self):
        self._r_bslash_()
        if not self.failed:
            self._ch('/')
        if not self.failed:
            self._succeed('/')

    def _s_re_char_2_(self):
        p = '[^/]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_zpos_(self):
        r = self.cache.get(('_r_zpos_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_zpos_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_zpos_2_()
        self.cache[('_r_zpos_', pos)] = (self.val, self.failed, self.pos)

    def _s_zpos_1_(self):
        self._ch('0')
        if not self.failed:
            self._succeed(0)

    def _s_zpos_2_(self):
        start = self.pos
        self._s_zpos_3_()
        if self.failed:
            return
        end = self.pos
        self.val = self.text[start:end]
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(_atoi(v__1))

    def _s_zpos_3_(self):
        self._s_zpos_4_()
        if not self.failed:
            self._s_zpos_5_()

    def _s_zpos_4_(self):
        p = '[1-9]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _s_zpos_5_(self):
        vs = []
        while True:
            p = self.pos
            self._s_zpos_6_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_zpos_6_(self):
        p = '[0-9]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_ll_expr_(self):
        r = self.cache.get(('_r_ll_expr_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_ll_expr_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_expr_2_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_ll_qual_()
        self.cache[('_r_ll_expr_', pos)] = (self.val, self.failed, self.pos)

    def _s_ll_expr_1_(self):
        self._r_ll_qual_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch('+')
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._succeed(['ll_plus', None, [v__1, v__3]])

    def _s_ll_expr_2_(self):
        self._r_ll_qual_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch('-')
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._succeed(['ll_minus', None, [v__1, v__3]])

    def _r_ll_exprs_(self):
        r = self.cache.get(('_r_ll_exprs_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_ll_exprs_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._succeed([])
        self.cache[('_r_ll_exprs_', pos)] = (self.val, self.failed, self.pos)

    def _s_ll_exprs_1_(self):
        self._r_ll_expr_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_ll_exprs_2_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._s_ll_exprs_4_()
        if not self.failed:
            self._succeed(_cons(v__1, v__2))

    def _s_ll_exprs_2_(self):
        vs = []
        while True:
            p = self.pos
            self._s_ll_exprs_3_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_ll_exprs_3_(self):
        self._r__filler_()
        if not self.failed:
            self._ch(',')
        if not self.failed:
            self._r_ll_expr_()

    def _s_ll_exprs_4_(self):
        p = self.pos
        self._s_ll_exprs_5_()
        if self.failed:
            self._succeed([], p)
        else:
            self._succeed([self.val])

    def _s_ll_exprs_5_(self):
        self._r__filler_()
        if not self.failed:
            self._ch(',')

    def _r_ll_qual_(self):
        r = self.cache.get(('_r_ll_qual_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_ll_qual_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_ll_prim_()
        self.cache[('_r_ll_qual_', pos)] = (self.val, self.failed, self.pos)

    def _s_ll_qual_1_(self):
        self._r_ll_prim_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_ll_qual_2_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['ll_qual', None, _cons(v__1, v__2)])

    def _s_ll_qual_2_(self):
        vs = []
        self._r_ll_post_op_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_ll_post_op_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_ll_post_op_(self):
        r = self.cache.get(('_r_ll_post_op_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_ll_post_op_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_post_op_2_()
        self.cache[('_r_ll_post_op_', pos)] = (self.val, self.failed, self.pos)

    def _s_ll_post_op_1_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('[')
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch(']')
        if not self.failed:
            self._succeed(['ll_getitem', None, [v__2]])

    def _s_ll_post_op_2_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('(')
        if not self.failed:
            self._r_ll_exprs_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch(')')
        if not self.failed:
            self._succeed(['ll_call', None, v__2])

    def _r_ll_prim_(self):
        r = self.cache.get(('_r_ll_prim_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s_ll_prim_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_2_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_3_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_4_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_6_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_8_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_10_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_12_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_13_()
        self.cache[('_r_ll_prim_', pos)] = (self.val, self.failed, self.pos)

    def _s_ll_prim_1_(self):
        self._r__filler_()
        if not self.failed:
            self._str('false')
        if not self.failed:
            self._succeed(['ll_const', 'false', []])

    def _s_ll_prim_2_(self):
        self._r__filler_()
        if not self.failed:
            self._str('null')
        if not self.failed:
            self._succeed(['ll_const', 'null', []])

    def _s_ll_prim_3_(self):
        self._r__filler_()
        if not self.failed:
            self._str('true')
        if not self.failed:
            self._succeed(['ll_const', 'true', []])

    def _s_ll_prim_4_(self):
        self._s_ll_prim_5_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['ll_var', v__1, []])

    def _s_ll_prim_5_(self):
        self._r__filler_()
        if not self.failed:
            self._r_ident_()

    def _s_ll_prim_6_(self):
        self._s_ll_prim_7_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['ll_num', v__1, []])

    def _s_ll_prim_7_(self):
        self._r__filler_()
        if not self.failed:
            self._r_hex_()

    def _s_ll_prim_8_(self):
        self._s_ll_prim_9_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['ll_num', v__1, []])

    def _s_ll_prim_9_(self):
        self._r__filler_()
        if not self.failed:
            self._r_int_()

    def _s_ll_prim_10_(self):
        self._s_ll_prim_11_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._succeed(['ll_lit', v__1, []])

    def _s_ll_prim_11_(self):
        self._r__filler_()
        if not self.failed:
            self._r_lit_()

    def _s_ll_prim_12_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('(')
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch(')')
        if not self.failed:
            self._succeed(['ll_paren', None, [v__2]])

    def _s_ll_prim_13_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('[')
        if not self.failed:
            self._r_ll_exprs_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch(']')
        if not self.failed:
            self._succeed(['ll_arr', None, v__2])

    def _r_int_(self):
        r = self.cache.get(('_r_int_', self.pos))
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
        self._s_int_1_()
        if self.failed:
            return
        end = self.pos
        self.val = self.text[start:end]
        self.cache[('_r_int_', pos)] = (self.val, self.failed, self.pos)

    def _s_int_1_(self):
        self._s_int_2_()
        if not self.failed:
            self._s_int_3_()
        if not self.failed:
            self._s_int_4_()

    def _s_int_2_(self):
        p = self.pos
        self._ch('-')
        if self.failed:
            self._succeed([], p)
        else:
            self._succeed([self.val])

    def _s_int_3_(self):
        p = '[1-9]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _s_int_4_(self):
        vs = []
        while True:
            p = self.pos
            self._s_int_5_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_int_5_(self):
        p = '[0-9]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_hex_(self):
        r = self.cache.get(('_r_hex_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        start = self.pos
        self._s_hex_1_()
        if self.failed:
            return
        end = self.pos
        self.val = self.text[start:end]
        self.cache[('_r_hex_', pos)] = (self.val, self.failed, self.pos)

    def _s_hex_1_(self):
        self._str('0x')
        if not self.failed:
            self._s_hex_2_()

    def _s_hex_2_(self):
        vs = []
        self._r_hex_char_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_hex_char_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_hex_char_(self):
        r = self.cache.get(('_r_hex_char_', self.pos))
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
        self.cache[('_r_hex_char_', pos)] = (self.val, self.failed, self.pos)

    def _r__whitespace_(self):
        r = self.cache.get(('_r__whitespace_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        vs = []
        self._s__whitespace_1_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._s__whitespace_1_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)
        self.cache[('_r__whitespace_', pos)] = (self.val, self.failed, self.pos)

    def _s__whitespace_1_(self):
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

    def _r__comment_(self):
        r = self.cache.get(('_r__comment_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        p = self.pos
        self._s__comment_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s__comment_5_()
        self.cache[('_r__comment_', pos)] = (self.val, self.failed, self.pos)

    def _s__comment_1_(self):
        self._s__comment_2_()
        if not self.failed:
            self._s__comment_3_()

    def _s__comment_2_(self):
        p = self.pos
        self._str('//')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('#')

    def _s__comment_3_(self):
        vs = []
        while True:
            p = self.pos
            self._s__comment_4_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s__comment_4_(self):
        p = '[^\r\n]'
        if p not in self.regexps:
            self.regexps[p] = re.compile(p)
        m = self.regexps[p].match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _s__comment_5_(self):
        self._str('/*')
        if not self.failed:
            while True:
                self._str('*/')
                if not self.failed:
                    break
                self._r_any_()
                if self.failed:
                    break

    def _r__filler_(self):
        r = self.cache.get(('_r__filler_', self.pos))
        if r is not None:
            self.val, self.failed, self.pos = r
            return
        pos = self.pos
        vs = []
        while True:
            p = self.pos
            self._s__filler_1_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)
        self.cache[('_r__filler_', pos)] = (self.val, self.failed, self.pos)

    def _s__filler_1_(self):
        p = self.pos
        self._r__whitespace_()
        if not self.failed:
            return
        self._rewind(p)
        self._r__comment_()

    def _r_any_(self):
        if self.pos < self.end:
            self._succeed(self.text[self.pos], self.pos + 1)
        else:
            self._fail()

    def _r_end_(self):
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
