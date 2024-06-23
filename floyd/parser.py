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
        self.ok = True
        self.path = path
        self.pos = 0
        self.val = None
        self.scopes = []

    def parse(self):
        self._grammar_()
        if not self.ok:
            return Result(None, self._err_str(), self.errpos)
        return Result(self.val, None, self.pos)

    def _grammar_(self):
        self.scopes.append({})
        self._grammar_s0_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._end_()
        if self.ok:
            self._succeed(['rules', None, self._get('vs')])
        self.scopes.pop()

    def _grammar_s0_(self):
        self._grammar_s0_l_()
        if self.ok:
            self._set('vs', self.val)

    def _grammar_s0_l_p_g_s1_g_(self):
        p = self.pos
        self._pragma_()
        if self.ok:
            return
        self._rewind(p)
        self._rule_()

    def _grammar_s0_l_p_g_(self):
        self._sp_()
        if self.ok:
            self._grammar_s0_l_p_g_s1_g_()

    def _grammar_s0_l_(self):
        vs = []
        while True:
            p = self.pos
            self._grammar_s0_l_p_g_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _sp_(self):
        vs = []
        while True:
            p = self.pos
            self._ws_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _ws_(self):
        p = self.pos
        self._ch(' ')
        if self.ok:
            return
        self._rewind(p)
        self._ch('\t')
        if self.ok:
            return
        self._rewind(p)
        self._eol_()
        if self.ok:
            return
        self._rewind(p)
        self._comment_()

    def _eol_(self):
        p = self.pos
        self._eol_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._ch('\r')
        if self.ok:
            return
        self._rewind(p)
        self._ch('\n')

    def _eol_c0_(self):
        self._ch('\r')
        if self.ok:
            self._ch('\n')

    def _comment_(self):
        p = self.pos
        self._comment_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._comment_c1_()

    def _comment_c0_(self):
        self._str('//')
        if self.ok:
            self._comment_c0_s1_()

    def _comment_c0_s1_p_g_(self):
        self._comment_c0_s1_p_g_s0_()
        if self.ok:
            self._any_()

    def _comment_c0_s1_p_g_s0_(self):
        p = self.pos
        errpos = self.errpos
        self._eol_()
        if not self.ok:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _comment_c0_s1_(self):
        vs = []
        while True:
            p = self.pos
            self._comment_c0_s1_p_g_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _comment_c1_(self):
        self._str('/*')
        if self.ok:
            self._comment_c1_s1_()
        if self.ok:
            self._str('*/')

    def _comment_c1_s1_p_g_(self):
        self._comment_c1_s1_p_g_s0_()
        if self.ok:
            self._any_()

    def _comment_c1_s1_p_g_s0_(self):
        p = self.pos
        errpos = self.errpos
        self._str('*/')
        if not self.ok:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _comment_c1_s1_(self):
        vs = []
        while True:
            p = self.pos
            self._comment_c1_s1_p_g_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _pragma_(self):
        p = self.pos
        self._pragma_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._pragma_c1_()
        if self.ok:
            return
        self._rewind(p)
        self._pragma_c2_()
        if self.ok:
            return
        self._rewind(p)
        self._pragma_c3_()
        if self.ok:
            return
        self._rewind(p)
        self._pragma_c4_()
        if self.ok:
            return
        self._rewind(p)
        self._pragma_c5_()
        if self.ok:
            return
        self._rewind(p)
        self._pragma_c6_()
        if self.ok:
            return
        self._rewind(p)
        self._pragma_c7_()

    def _pragma_c0_(self):
        self.scopes.append({})
        self._str('%tokens')
        if self.ok:
            self._pragma_c0_s1_()
        if self.ok:
            self._succeed(['pragma', 'tokens', self._get('is')])
        self.scopes.pop()

    def _pragma_c0_s1_(self):
        self._ident_list_()
        if self.ok:
            self._set('is', self.val)

    def _pragma_c1_(self):
        self.scopes.append({})
        self._str('%token')
        if self.ok:
            self._sp_()
        if self.ok:
            self._pragma_c1_s2_()
        if self.ok:
            self._succeed(['pragma', 'token', [self._get('i')]])
        self.scopes.pop()

    def _pragma_c1_s2_(self):
        self._ident_()
        if self.ok:
            self._set('i', self.val)

    def _pragma_c2_(self):
        self.scopes.append({})
        self._str('%whitespace_style')
        if self.ok:
            self._sp_()
        if self.ok:
            self._pragma_c2_s2_()
        if self.ok:
            self._succeed(['pragma', 'whitespace_style', self._get('i')])
        self.scopes.pop()

    def _pragma_c2_s2_(self):
        self._ident_()
        if self.ok:
            self._set('i', self.val)

    def _pragma_c3_(self):
        self.scopes.append({})
        self._str('%whitespace')
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch('=')
        if self.ok:
            self._sp_()
        if self.ok:
            self._pragma_c3_s4_()
        if self.ok:
            self._succeed(['pragma', 'whitespace', [self._get('cs')]])
        self.scopes.pop()

    def _pragma_c3_s4_(self):
        self._choice_()
        if self.ok:
            self._set('cs', self.val)

    def _pragma_c4_(self):
        self.scopes.append({})
        self._str('%comment_style')
        if self.ok:
            self._sp_()
        if self.ok:
            self._pragma_c4_s2_()
        if self.ok:
            self._succeed(['pragma', 'comment_style', self._get('c')])
        self.scopes.pop()

    def _pragma_c4_s2_l_g_(self):
        p = self.pos
        self._str('C++')
        if self.ok:
            return
        self._rewind(p)
        self._ident_()

    def _pragma_c4_s2_(self):
        self._pragma_c4_s2_l_g_()
        if self.ok:
            self._set('c', self.val)

    def _pragma_c5_(self):
        self.scopes.append({})
        self._str('%comment')
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch('=')
        if self.ok:
            self._sp_()
        if self.ok:
            self._pragma_c5_s4_()
        if self.ok:
            self._succeed(['pragma', 'comment', [self._get('cs')]])
        self.scopes.pop()

    def _pragma_c5_s4_(self):
        self._choice_()
        if self.ok:
            self._set('cs', self.val)

    def _pragma_c6_(self):
        self.scopes.append({})
        self._str('%assoc')
        if self.ok:
            self._sp_()
        if self.ok:
            self._pragma_c6_s2_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._pragma_c6_s4_()
        if self.ok:
            self._succeed(
                ['pragma', 'assoc', [self._get('a'), self._get('d')]]
            )
        self.scopes.pop()

    def _pragma_c6_s2_l_g_(self):
        p = self.pos
        self._op_()
        if self.ok:
            return
        self._rewind(p)
        self._arm_()

    def _pragma_c6_s2_(self):
        self._pragma_c6_s2_l_g_()
        if self.ok:
            self._set('a', self.val)

    def _pragma_c6_s4_(self):
        self._dir_()
        if self.ok:
            self._set('d', self.val)

    def _pragma_c7_(self):
        self.scopes.append({})
        self._str('%prec')
        if self.ok:
            self._pragma_c7_s1_()
        if self.ok:
            self._succeed(['pragma', 'prec', self._get('os')])
        self.scopes.pop()

    def _pragma_c7_s1_(self):
        self._pragma_c7_s1_l_()
        if self.ok:
            self._set('os', self.val)

    def _pragma_c7_s1_l_p_g_(self):
        self.scopes.append({})
        self._pragma_c7_s1_l_p_g_s0_()
        if self.ok:
            self._ws_()
        if self.ok:
            self._pragma_c7_s1_l_p_g_s2_()
        if self.ok:
            self._succeed(self._get('o'))
        self.scopes.pop()

    def _pragma_c7_s1_l_p_g_s0_(self):
        p = self.pos
        errpos = self.errpos
        self._eol_()
        if not self.ok:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _pragma_c7_s1_l_p_g_s2_(self):
        self._op_()
        if self.ok:
            self._set('o', self.val)

    def _pragma_c7_s1_l_(self):
        vs = []
        self._pragma_c7_s1_l_p_g_()
        vs.append(self.val)
        if not self.ok:
            return
        while True:
            p = self.pos
            self._pragma_c7_s1_l_p_g_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _op_(self):
        self.scopes.append({})
        self._op_s0_()
        if self.ok:
            self._succeed(self._join('', self._get('op')))
        self.scopes.pop()

    def _op_s0_(self):
        self._op_s0_l_()
        if self.ok:
            self._set('op', self.val)

    def _op_s0_l_p_g_(self):
        self._op_s0_l_p_g_s0_()
        if self.ok:
            self._any_()

    def _op_s0_l_p_g_s0_n_g_(self):
        p = self.pos
        self._ws_()
        if self.ok:
            return
        self._rewind(p)
        self._id_continue_()

    def _op_s0_l_p_g_s0_(self):
        p = self.pos
        errpos = self.errpos
        self._op_s0_l_p_g_s0_n_g_()
        if not self.ok:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _op_s0_l_(self):
        vs = []
        self._op_s0_l_p_g_()
        vs.append(self.val)
        if not self.ok:
            return
        while True:
            p = self.pos
            self._op_s0_l_p_g_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _arm_(self):
        self.scopes.append({})
        self._arm_s0_()
        if self.ok:
            self._ch('#')
        if self.ok:
            self._arm_s2_()
        if self.ok:
            self._succeed(
                self._get('i') + '#' + self._join('', self._get('ds'))
            )
        self.scopes.pop()

    def _arm_s0_(self):
        self._ident_()
        if self.ok:
            self._set('i', self.val)

    def _arm_s2_(self):
        self._digits_()
        if self.ok:
            self._set('ds', self.val)

    def _dir_(self):
        self.scopes.append({})
        self._dir_s0_()
        if self.ok:
            self._succeed(self._get('d'))
        self.scopes.pop()

    def _dir_s0_l_g_(self):
        p = self.pos
        self._str('left')
        if self.ok:
            return
        self._rewind(p)
        self._str('right')

    def _dir_s0_(self):
        self._dir_s0_l_g_()
        if self.ok:
            self._set('d', self.val)

    def _ident_list_(self):
        self.scopes.append({})
        self._ident_list_s0_()
        if self.ok:
            self._succeed(self._get('is'))
        self.scopes.pop()

    def _ident_list_s0_(self):
        self._ident_list_s0_l_()
        if self.ok:
            self._set('is', self.val)

    def _ident_list_s0_l_p_g_(self):
        self.scopes.append({})
        self._sp_()
        if self.ok:
            self._ident_list_s0_l_p_g_s1_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._ident_list_s0_l_p_g_s3_()
        if self.ok:
            self._succeed(self._get('i'))
        self.scopes.pop()

    def _ident_list_s0_l_p_g_s1_(self):
        self._ident_()
        if self.ok:
            self._set('i', self.val)

    def _ident_list_s0_l_p_g_s3_(self):
        p = self.pos
        errpos = self.errpos
        self._ch('=')
        if not self.ok:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _ident_list_s0_l_(self):
        vs = []
        self._ident_list_s0_l_p_g_()
        vs.append(self.val)
        if not self.ok:
            return
        while True:
            p = self.pos
            self._ident_list_s0_l_p_g_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _rule_(self):
        self.scopes.append({})
        self._rule_s0_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch('=')
        if self.ok:
            self._sp_()
        if self.ok:
            self._rule_s4_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._rule_s6_()
        if self.ok:
            self._succeed(['rule', self._get('i'), [self._get('cs')]])
        self.scopes.pop()

    def _rule_s0_(self):
        self._ident_()
        if self.ok:
            self._set('i', self.val)

    def _rule_s4_(self):
        self._choice_()
        if self.ok:
            self._set('cs', self.val)

    def _rule_s6_(self):
        p = self.pos
        self._ch(',')
        if not self.ok:
            self._succeed([], p)
        else:
            self._succeed([self.val])

    def _ident_(self):
        self.scopes.append({})
        self._ident_s0_()
        if self.ok:
            self._ident_s1_()
        if self.ok:
            self._succeed(self._cat([self._get('hd')] + self._get('tl')))
        self.scopes.pop()

    def _ident_s0_(self):
        self._id_start_()
        if self.ok:
            self._set('hd', self.val)

    def _ident_s1_(self):
        self._ident_s1_l_()
        if self.ok:
            self._set('tl', self.val)

    def _ident_s1_l_(self):
        vs = []
        while True:
            p = self.pos
            self._id_continue_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _id_start_(self):
        p = self.pos
        self._id_start_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._id_start_c1_()
        if self.ok:
            return
        self._rewind(p)
        self._ch('_')
        if self.ok:
            return
        self._rewind(p)
        self._ch('$')

    def _id_start_c0_(self):
        self._range('a', 'z')

    def _id_start_c1_(self):
        self._range('A', 'Z')

    def _id_continue_(self):
        p = self.pos
        self._id_start_()
        if self.ok:
            return
        self._rewind(p)
        self._digit_()

    def _choice_(self):
        self.scopes.append({})
        self._choice_s0_()
        if self.ok:
            self._choice_s1_()
        if self.ok:
            self._succeed(['choice', None, [self._get('s')] + self._get('ss')])
        self.scopes.pop()

    def _choice_s0_(self):
        self._seq_()
        if self.ok:
            self._set('s', self.val)

    def _choice_s1_(self):
        self._choice_s1_l_()
        if self.ok:
            self._set('ss', self.val)

    def _choice_s1_l_p_g_(self):
        self._sp_()
        if self.ok:
            self._ch('|')
        if self.ok:
            self._sp_()
        if self.ok:
            self._seq_()

    def _choice_s1_l_(self):
        vs = []
        while True:
            p = self.pos
            self._choice_s1_l_p_g_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _seq_(self):
        p = self.pos
        self._seq_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._succeed(['empty', None, []])

    def _seq_c0_(self):
        self.scopes.append({})
        self._seq_c0_s0_()
        if self.ok:
            self._seq_c0_s1_()
        if self.ok:
            self._succeed(['seq', None, [self._get('e')] + self._get('es')])
        self.scopes.pop()

    def _seq_c0_s0_(self):
        self._expr_()
        if self.ok:
            self._set('e', self.val)

    def _seq_c0_s1_(self):
        self._seq_c0_s1_l_()
        if self.ok:
            self._set('es', self.val)

    def _seq_c0_s1_l_p_g_(self):
        self._ws_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._expr_()

    def _seq_c0_s1_l_(self):
        vs = []
        while True:
            p = self.pos
            self._seq_c0_s1_l_p_g_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _expr_(self):
        p = self.pos
        self._expr_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._post_expr_()

    def _expr_c0_(self):
        self.scopes.append({})
        self._expr_c0_s0_()
        if self.ok:
            self._ch(':')
        if self.ok:
            self._expr_c0_s2_()
        if self.ok:
            self._succeed(['label', self._get('l'), [self._get('e')]])
        self.scopes.pop()

    def _expr_c0_s0_(self):
        self._post_expr_()
        if self.ok:
            self._set('e', self.val)

    def _expr_c0_s2_(self):
        self._ident_()
        if self.ok:
            self._set('l', self.val)

    def _post_expr_(self):
        p = self.pos
        self._post_expr_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._prim_expr_()

    def _post_expr_c0_(self):
        self.scopes.append({})
        self._post_expr_c0_s0_()
        if self.ok:
            self._post_expr_c0_s1_()
        if self.ok:
            self._succeed(['post', self._get('op'), [self._get('e')]])
        self.scopes.pop()

    def _post_expr_c0_s0_(self):
        self._prim_expr_()
        if self.ok:
            self._set('e', self.val)

    def _post_expr_c0_s1_(self):
        self._post_op_()
        if self.ok:
            self._set('op', self.val)

    def _post_op_(self):
        p = self.pos
        self._ch('?')
        if self.ok:
            return
        self._rewind(p)
        self._ch('*')
        if self.ok:
            return
        self._rewind(p)
        self._ch('+')

    def _prim_expr_(self):
        p = self.pos
        self._prim_expr_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._prim_expr_c1_()
        if self.ok:
            return
        self._rewind(p)
        self._prim_expr_c2_()
        if self.ok:
            return
        self._rewind(p)
        self._prim_expr_c3_()
        if self.ok:
            return
        self._rewind(p)
        self._prim_expr_c4_()
        if self.ok:
            return
        self._rewind(p)
        self._prim_expr_c5_()
        if self.ok:
            return
        self._rewind(p)
        self._prim_expr_c6_()
        if self.ok:
            return
        self._rewind(p)
        self._prim_expr_c7_()
        if self.ok:
            return
        self._rewind(p)
        self._prim_expr_c8_()
        if self.ok:
            return
        self._rewind(p)
        self._prim_expr_c9_()

    def _prim_expr_c0_(self):
        self.scopes.append({})
        self._prim_expr_c0_s0_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._str('..')
        if self.ok:
            self._sp_()
        if self.ok:
            self._prim_expr_c0_s4_()
        if self.ok:
            self._succeed(['range', None, [self._get('i'), self._get('j')]])
        self.scopes.pop()

    def _prim_expr_c0_s0_(self):
        self._lit_()
        if self.ok:
            self._set('i', self.val)

    def _prim_expr_c0_s4_(self):
        self._lit_()
        if self.ok:
            self._set('j', self.val)

    def _prim_expr_c1_(self):
        self.scopes.append({})
        self._prim_expr_c1_s0_()
        if self.ok:
            self._succeed(self._get('l'))
        self.scopes.pop()

    def _prim_expr_c1_s0_(self):
        self._lit_()
        if self.ok:
            self._set('l', self.val)

    def _prim_expr_c2_(self):
        self.scopes.append({})
        self._prim_expr_c2_s0_()
        if self.ok:
            self._succeed(self._get('e'))
        self.scopes.pop()

    def _prim_expr_c2_s0_(self):
        self._escape_()
        if self.ok:
            self._set('e', self.val)

    def _prim_expr_c3_(self):
        self.scopes.append({})
        self._prim_expr_c3_s0_()
        if self.ok:
            self._prim_expr_c3_s1_()
        if self.ok:
            self._succeed(['apply', self._get('i'), []])
        self.scopes.pop()

    def _prim_expr_c3_s0_(self):
        self._ident_()
        if self.ok:
            self._set('i', self.val)

    def _prim_expr_c3_s1_n_g_(self):
        self._sp_()
        if self.ok:
            self._ch('=')

    def _prim_expr_c3_s1_(self):
        p = self.pos
        errpos = self.errpos
        self._prim_expr_c3_s1_n_g_()
        if not self.ok:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _prim_expr_c4_(self):
        self.scopes.append({})
        self._str('->')
        if self.ok:
            self._sp_()
        if self.ok:
            self._prim_expr_c4_s2_()
        if self.ok:
            self._succeed(['action', None, [self._get('e')]])
        self.scopes.pop()

    def _prim_expr_c4_s2_(self):
        self._ll_expr_()
        if self.ok:
            self._set('e', self.val)

    def _prim_expr_c5_(self):
        self.scopes.append({})
        self._ch('{')
        if self.ok:
            self._sp_()
        if self.ok:
            self._prim_expr_c5_s2_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch('}')
        if self.ok:
            self._succeed(['action', None, [self._get('e')]])
        self.scopes.pop()

    def _prim_expr_c5_s2_(self):
        self._ll_expr_()
        if self.ok:
            self._set('e', self.val)

    def _prim_expr_c6_(self):
        self.scopes.append({})
        self._ch('~')
        if self.ok:
            self._prim_expr_c6_s1_()
        if self.ok:
            self._succeed(['not', None, [self._get('e')]])
        self.scopes.pop()

    def _prim_expr_c6_s1_(self):
        self._prim_expr_()
        if self.ok:
            self._set('e', self.val)

    def _prim_expr_c7_(self):
        self.scopes.append({})
        self._str('?(')
        if self.ok:
            self._sp_()
        if self.ok:
            self._prim_expr_c7_s2_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch(')')
        if self.ok:
            self._succeed(['pred', None, [self._get('e')]])
        self.scopes.pop()

    def _prim_expr_c7_s2_(self):
        self._ll_expr_()
        if self.ok:
            self._set('e', self.val)

    def _prim_expr_c8_(self):
        self.scopes.append({})
        self._str('?{')
        if self.ok:
            self._sp_()
        if self.ok:
            self._prim_expr_c8_s2_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch('}')
        if self.ok:
            self._succeed(['pred', None, [self._get('e')]])
        self.scopes.pop()

    def _prim_expr_c8_s2_(self):
        self._ll_expr_()
        if self.ok:
            self._set('e', self.val)

    def _prim_expr_c9_(self):
        self.scopes.append({})
        self._ch('(')
        if self.ok:
            self._sp_()
        if self.ok:
            self._prim_expr_c9_s2_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch(')')
        if self.ok:
            self._succeed(['paren', None, [self._get('e')]])
        self.scopes.pop()

    def _prim_expr_c9_s2_(self):
        self._choice_()
        if self.ok:
            self._set('e', self.val)

    def _lit_(self):
        p = self.pos
        self._lit_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._lit_c1_()

    def _lit_c0_(self):
        self.scopes.append({})
        self._squote_()
        if self.ok:
            self._lit_c0_s1_()
        if self.ok:
            self._squote_()
        if self.ok:
            self._succeed(['lit', self._cat(self._get('cs')), []])
        self.scopes.pop()

    def _lit_c0_s1_(self):
        self._lit_c0_s1_l_()
        if self.ok:
            self._set('cs', self.val)

    def _lit_c0_s1_l_(self):
        vs = []
        while True:
            p = self.pos
            self._sqchar_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _lit_c1_(self):
        self.scopes.append({})
        self._dquote_()
        if self.ok:
            self._lit_c1_s1_()
        if self.ok:
            self._dquote_()
        if self.ok:
            self._succeed(['lit', self._cat(self._get('cs')), []])
        self.scopes.pop()

    def _lit_c1_s1_(self):
        self._lit_c1_s1_l_()
        if self.ok:
            self._set('cs', self.val)

    def _lit_c1_s1_l_(self):
        vs = []
        while True:
            p = self.pos
            self._dqchar_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _sqchar_(self):
        p = self.pos
        self._sqchar_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._sqchar_c1_()

    def _sqchar_c0_(self):
        self.scopes.append({})
        self._bslash_()
        if self.ok:
            self._sqchar_c0_s1_()
        if self.ok:
            self._succeed(self._get('c'))
        self.scopes.pop()

    def _sqchar_c0_s1_(self):
        self._esc_char_()
        if self.ok:
            self._set('c', self.val)

    def _sqchar_c1_(self):
        self.scopes.append({})
        self._sqchar_c1_s0_()
        if self.ok:
            self._sqchar_c1_s1_()
        if self.ok:
            self._succeed(self._get('c'))
        self.scopes.pop()

    def _sqchar_c1_s0_(self):
        p = self.pos
        errpos = self.errpos
        self._squote_()
        if not self.ok:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _sqchar_c1_s1_(self):
        self._any_()
        if self.ok:
            self._set('c', self.val)

    def _dqchar_(self):
        p = self.pos
        self._dqchar_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._dqchar_c1_()

    def _dqchar_c0_(self):
        self.scopes.append({})
        self._bslash_()
        if self.ok:
            self._dqchar_c0_s1_()
        if self.ok:
            self._succeed(self._get('c'))
        self.scopes.pop()

    def _dqchar_c0_s1_(self):
        self._esc_char_()
        if self.ok:
            self._set('c', self.val)

    def _dqchar_c1_(self):
        self.scopes.append({})
        self._dqchar_c1_s0_()
        if self.ok:
            self._dqchar_c1_s1_()
        if self.ok:
            self._succeed(self._get('c'))
        self.scopes.pop()

    def _dqchar_c1_s0_(self):
        p = self.pos
        errpos = self.errpos
        self._dquote_()
        if not self.ok:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _dqchar_c1_s1_(self):
        self._any_()
        if self.ok:
            self._set('c', self.val)

    def _bslash_(self):
        self._ch('\\')

    def _squote_(self):
        self._ch("'")

    def _dquote_(self):
        self._ch('"')

    def _esc_char_(self):
        p = self.pos
        self._esc_char_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._esc_char_c1_()
        if self.ok:
            return
        self._rewind(p)
        self._esc_char_c2_()
        if self.ok:
            return
        self._rewind(p)
        self._esc_char_c3_()
        if self.ok:
            return
        self._rewind(p)
        self._esc_char_c4_()
        if self.ok:
            return
        self._rewind(p)
        self._esc_char_c5_()
        if self.ok:
            return
        self._rewind(p)
        self._esc_char_c6_()
        if self.ok:
            return
        self._rewind(p)
        self._esc_char_c7_()
        if self.ok:
            return
        self._rewind(p)
        self._esc_char_c8_()
        if self.ok:
            return
        self._rewind(p)
        self._esc_char_c9_()
        if self.ok:
            return
        self._rewind(p)
        self._esc_char_c10_()

    def _esc_char_c0_(self):
        self._ch('b')
        if self.ok:
            self._succeed('\b')

    def _esc_char_c1_(self):
        self._ch('f')
        if self.ok:
            self._succeed('\f')

    def _esc_char_c2_(self):
        self._ch('n')
        if self.ok:
            self._succeed('\n')

    def _esc_char_c3_(self):
        self._ch('r')
        if self.ok:
            self._succeed('\r')

    def _esc_char_c4_(self):
        self._ch('t')
        if self.ok:
            self._succeed('\t')

    def _esc_char_c5_(self):
        self._ch('v')
        if self.ok:
            self._succeed('\v')

    def _esc_char_c6_(self):
        self._squote_()
        if self.ok:
            self._succeed("'")

    def _esc_char_c7_(self):
        self._dquote_()
        if self.ok:
            self._succeed('"')

    def _esc_char_c8_(self):
        self._bslash_()
        if self.ok:
            self._succeed('\\')

    def _esc_char_c9_(self):
        self.scopes.append({})
        self._esc_char_c9_s0_()
        if self.ok:
            self._succeed(self._get('c'))
        self.scopes.pop()

    def _esc_char_c9_s0_(self):
        self._hex_esc_()
        if self.ok:
            self._set('c', self.val)

    def _esc_char_c10_(self):
        self.scopes.append({})
        self._esc_char_c10_s0_()
        if self.ok:
            self._succeed(self._get('c'))
        self.scopes.pop()

    def _esc_char_c10_s0_(self):
        self._unicode_esc_()
        if self.ok:
            self._set('c', self.val)

    def _hex_esc_(self):
        self.scopes.append({})
        self._ch('x')
        if self.ok:
            self._hex_esc_s1_()
        if self.ok:
            self._hex_esc_s2_()
        if self.ok:
            self._succeed(self._xtou(self._get('h1') + self._get('h2')))
        self.scopes.pop()

    def _hex_esc_s1_(self):
        self._hex_()
        if self.ok:
            self._set('h1', self.val)

    def _hex_esc_s2_(self):
        self._hex_()
        if self.ok:
            self._set('h2', self.val)

    def _unicode_esc_(self):
        p = self.pos
        self._unicode_esc_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._unicode_esc_c1_()

    def _unicode_esc_c0_(self):
        self.scopes.append({})
        self._ch('u')
        if self.ok:
            self._unicode_esc_c0_s1_()
        if self.ok:
            self._unicode_esc_c0_s2_()
        if self.ok:
            self._unicode_esc_c0_s3_()
        if self.ok:
            self._unicode_esc_c0_s4_()
        if self.ok:
            self._succeed(
                self._xtou(
                    self._get('h1')
                    + self._get('h2')
                    + self._get('h3')
                    + self._get('h4'),
                )
            )
        self.scopes.pop()

    def _unicode_esc_c0_s1_(self):
        self._hex_()
        if self.ok:
            self._set('h1', self.val)

    def _unicode_esc_c0_s2_(self):
        self._hex_()
        if self.ok:
            self._set('h2', self.val)

    def _unicode_esc_c0_s3_(self):
        self._hex_()
        if self.ok:
            self._set('h3', self.val)

    def _unicode_esc_c0_s4_(self):
        self._hex_()
        if self.ok:
            self._set('h4', self.val)

    def _unicode_esc_c1_(self):
        self.scopes.append({})
        self._ch('U')
        if self.ok:
            self._unicode_esc_c1_s1_()
        if self.ok:
            self._unicode_esc_c1_s2_()
        if self.ok:
            self._unicode_esc_c1_s3_()
        if self.ok:
            self._unicode_esc_c1_s4_()
        if self.ok:
            self._unicode_esc_c1_s5_()
        if self.ok:
            self._unicode_esc_c1_s6_()
        if self.ok:
            self._unicode_esc_c1_s7_()
        if self.ok:
            self._unicode_esc_c1_s8_()
        if self.ok:
            self._succeed(
                self._xtou(
                    self._get('h1')
                    + self._get('h2')
                    + self._get('h3')
                    + self._get('h4')
                    + self._get('h5')
                    + self._get('h6')
                    + self._get('h7')
                    + self._get('h8'),
                )
            )
        self.scopes.pop()

    def _unicode_esc_c1_s1_(self):
        self._hex_()
        if self.ok:
            self._set('h1', self.val)

    def _unicode_esc_c1_s2_(self):
        self._hex_()
        if self.ok:
            self._set('h2', self.val)

    def _unicode_esc_c1_s3_(self):
        self._hex_()
        if self.ok:
            self._set('h3', self.val)

    def _unicode_esc_c1_s4_(self):
        self._hex_()
        if self.ok:
            self._set('h4', self.val)

    def _unicode_esc_c1_s5_(self):
        self._hex_()
        if self.ok:
            self._set('h5', self.val)

    def _unicode_esc_c1_s6_(self):
        self._hex_()
        if self.ok:
            self._set('h6', self.val)

    def _unicode_esc_c1_s7_(self):
        self._hex_()
        if self.ok:
            self._set('h7', self.val)

    def _unicode_esc_c1_s8_(self):
        self._hex_()
        if self.ok:
            self._set('h8', self.val)

    def _escape_(self):
        self.scopes.append({})
        self._str('\\p{')
        if self.ok:
            self._escape_s1_()
        if self.ok:
            self._ch('}')
        if self.ok:
            self._succeed(['unicat', self._get('i'), []])
        self.scopes.pop()

    def _escape_s1_(self):
        self._ident_()
        if self.ok:
            self._set('i', self.val)

    def _ll_exprs_(self):
        p = self.pos
        self._ll_exprs_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._succeed([])

    def _ll_exprs_c0_(self):
        self.scopes.append({})
        self._ll_exprs_c0_s0_()
        if self.ok:
            self._ll_exprs_c0_s1_()
        if self.ok:
            self._succeed([self._get('e')] + self._get('es'))
        self.scopes.pop()

    def _ll_exprs_c0_s0_(self):
        self._ll_expr_()
        if self.ok:
            self._set('e', self.val)

    def _ll_exprs_c0_s1_(self):
        self._ll_exprs_c0_s1_l_()
        if self.ok:
            self._set('es', self.val)

    def _ll_exprs_c0_s1_l_p_g_(self):
        self._sp_()
        if self.ok:
            self._ch(',')
        if self.ok:
            self._sp_()
        if self.ok:
            self._ll_expr_()

    def _ll_exprs_c0_s1_l_(self):
        vs = []
        while True:
            p = self.pos
            self._ll_exprs_c0_s1_l_p_g_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _ll_expr_(self):
        p = self.pos
        self._ll_expr_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_expr_c1_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_qual_()

    def _ll_expr_c0_(self):
        self.scopes.append({})
        self._ll_expr_c0_s0_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch('+')
        if self.ok:
            self._sp_()
        if self.ok:
            self._ll_expr_c0_s4_()
        if self.ok:
            self._succeed(
                ['ll_plus', None, [self._get('e1'), self._get('e2')]]
            )
        self.scopes.pop()

    def _ll_expr_c0_s0_(self):
        self._ll_qual_()
        if self.ok:
            self._set('e1', self.val)

    def _ll_expr_c0_s4_(self):
        self._ll_expr_()
        if self.ok:
            self._set('e2', self.val)

    def _ll_expr_c1_(self):
        self.scopes.append({})
        self._ll_expr_c1_s0_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch('-')
        if self.ok:
            self._sp_()
        if self.ok:
            self._ll_expr_c1_s4_()
        if self.ok:
            self._succeed(
                ['ll_minus', None, [self._get('e1'), self._get('e2')]]
            )
        self.scopes.pop()

    def _ll_expr_c1_s0_(self):
        self._ll_qual_()
        if self.ok:
            self._set('e1', self.val)

    def _ll_expr_c1_s4_(self):
        self._ll_expr_()
        if self.ok:
            self._set('e2', self.val)

    def _ll_qual_(self):
        p = self.pos
        self._ll_qual_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_prim_()

    def _ll_qual_c0_(self):
        self.scopes.append({})
        self._ll_qual_c0_s0_()
        if self.ok:
            self._ll_qual_c0_s1_()
        if self.ok:
            self._succeed(
                ['ll_qual', None, [self._get('e')] + self._get('ps')]
            )
        self.scopes.pop()

    def _ll_qual_c0_s0_(self):
        self._ll_prim_()
        if self.ok:
            self._set('e', self.val)

    def _ll_qual_c0_s1_(self):
        self._ll_qual_c0_s1_l_()
        if self.ok:
            self._set('ps', self.val)

    def _ll_qual_c0_s1_l_(self):
        vs = []
        self._ll_post_op_()
        vs.append(self.val)
        if not self.ok:
            return
        while True:
            p = self.pos
            self._ll_post_op_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _ll_post_op_(self):
        p = self.pos
        self._ll_post_op_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_post_op_c1_()

    def _ll_post_op_c0_(self):
        self.scopes.append({})
        self._ch('[')
        if self.ok:
            self._sp_()
        if self.ok:
            self._ll_post_op_c0_s2_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch(']')
        if self.ok:
            self._succeed(['ll_getitem', None, [self._get('e')]])
        self.scopes.pop()

    def _ll_post_op_c0_s2_(self):
        self._ll_expr_()
        if self.ok:
            self._set('e', self.val)

    def _ll_post_op_c1_(self):
        self.scopes.append({})
        self._ch('(')
        if self.ok:
            self._sp_()
        if self.ok:
            self._ll_post_op_c1_s2_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch(')')
        if self.ok:
            self._succeed(['ll_call', None, self._get('es')])
        self.scopes.pop()

    def _ll_post_op_c1_s2_(self):
        self._ll_exprs_()
        if self.ok:
            self._set('es', self.val)

    def _ll_prim_(self):
        p = self.pos
        self._ll_prim_c0_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_prim_c1_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_prim_c2_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_prim_c3_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_prim_c4_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_prim_c5_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_prim_c6_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_prim_c7_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_prim_c8_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_prim_c9_()
        if self.ok:
            return
        self._rewind(p)
        self._ll_prim_c10_()

    def _ll_prim_c0_(self):
        self._str('false')
        if self.ok:
            self._succeed(['ll_const', 'false', []])

    def _ll_prim_c1_(self):
        self._str('null')
        if self.ok:
            self._succeed(['ll_const', 'null', []])

    def _ll_prim_c2_(self):
        self._str('true')
        if self.ok:
            self._succeed(['ll_const', 'true', []])

    def _ll_prim_c3_(self):
        self._str('Infinity')
        if self.ok:
            self._succeed(['ll_const', 'Infinity', []])

    def _ll_prim_c4_(self):
        self._str('NaN')
        if self.ok:
            self._succeed(['ll_const', 'NaN', []])

    def _ll_prim_c5_(self):
        self.scopes.append({})
        self._ll_prim_c5_s0_()
        if self.ok:
            self._succeed(['ll_var', self._get('i'), []])
        self.scopes.pop()

    def _ll_prim_c5_s0_(self):
        self._ident_()
        if self.ok:
            self._set('i', self.val)

    def _ll_prim_c6_(self):
        self.scopes.append({})
        self._str('0x')
        if self.ok:
            self._ll_prim_c6_s1_()
        if self.ok:
            self._succeed(['ll_num', '0x' + self._get('hs'), []])
        self.scopes.pop()

    def _ll_prim_c6_s1_(self):
        self._hexdigits_()
        if self.ok:
            self._set('hs', self.val)

    def _ll_prim_c7_(self):
        self.scopes.append({})
        self._ll_prim_c7_s0_()
        if self.ok:
            self._succeed(['ll_num', self._get('ds'), []])
        self.scopes.pop()

    def _ll_prim_c7_s0_(self):
        self._digits_()
        if self.ok:
            self._set('ds', self.val)

    def _ll_prim_c8_(self):
        self.scopes.append({})
        self._ll_prim_c8_s0_()
        if self.ok:
            self._succeed(['ll_lit', self._get('l')[1], []])
        self.scopes.pop()

    def _ll_prim_c8_s0_(self):
        self._lit_()
        if self.ok:
            self._set('l', self.val)

    def _ll_prim_c9_(self):
        self.scopes.append({})
        self._ch('(')
        if self.ok:
            self._sp_()
        if self.ok:
            self._ll_prim_c9_s2_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch(')')
        if self.ok:
            self._succeed(['ll_paren', None, [self._get('e')]])
        self.scopes.pop()

    def _ll_prim_c9_s2_(self):
        self._ll_expr_()
        if self.ok:
            self._set('e', self.val)

    def _ll_prim_c10_(self):
        self.scopes.append({})
        self._ch('[')
        if self.ok:
            self._sp_()
        if self.ok:
            self._ll_prim_c10_s2_()
        if self.ok:
            self._sp_()
        if self.ok:
            self._ch(']')
        if self.ok:
            self._succeed(['ll_arr', None, self._get('es')])
        self.scopes.pop()

    def _ll_prim_c10_s2_(self):
        self._ll_exprs_()
        if self.ok:
            self._set('es', self.val)

    def _digits_(self):
        self.scopes.append({})
        self._digits_s0_()
        if self.ok:
            self._succeed(self._cat(self._get('ds')))
        self.scopes.pop()

    def _digits_s0_(self):
        self._digits_s0_l_()
        if self.ok:
            self._set('ds', self.val)

    def _digits_s0_l_(self):
        vs = []
        self._digit_()
        vs.append(self.val)
        if not self.ok:
            return
        while True:
            p = self.pos
            self._digit_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _hexdigits_(self):
        self.scopes.append({})
        self._hexdigits_s0_()
        if self.ok:
            self._succeed(self._cat(self._get('hs')))
        self.scopes.pop()

    def _hexdigits_s0_(self):
        self._hexdigits_s0_l_()
        if self.ok:
            self._set('hs', self.val)

    def _hexdigits_s0_l_(self):
        vs = []
        self._hex_()
        vs.append(self.val)
        if not self.ok:
            return
        while True:
            p = self.pos
            self._hex_()
            if not self.ok:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _hex_(self):
        p = self.pos
        self._digit_()
        if self.ok:
            return
        self._rewind(p)
        self._hex_c1_()
        if self.ok:
            return
        self._rewind(p)
        self._hex_c2_()

    def _hex_c1_(self):
        self._range('a', 'f')

    def _hex_c2_(self):
        self._range('A', 'F')

    def _digit_(self):
        self._range('0', '9')

    def _any_(self):
        if self.pos < self.end:
            self._succeed(self.text[self.pos], self.pos + 1)
        else:
            self._fail()

    def _cat(self, strs):
        return ''.join(strs)

    def _ch(self, ch):
        p = self.pos
        if p < self.end and self.text[p] == ch:
            self._succeed(ch, self.pos + 1)
        else:
            self._fail()

    def _end_(self):
        if self.pos == self.end:
            self._succeed(None)
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
            thing = '"%s"' % self.text[self.errpos]
        return '%s:%d Unexpected %s at column %d' % (
            self.path,
            lineno,
            thing,
            colno,
        )

    def _fail(self):
        self.val = None
        self.ok = False
        self.errpos = max(self.errpos, self.pos)

    def _get(self, var):
        return self.scopes[-1][var]

    def _join(self, s, vs):
        return s.join(vs)

    def _range(self, i, j):
        p = self.pos
        if p != self.end and ord(i) <= ord(self.text[p]) <= ord(j):
            self._succeed(self.text[p], self.pos + 1)
        else:
            self._fail()

    def _rewind(self, newpos):
        self._succeed(None, newpos)

    def _set(self, var, val):
        self.scopes[-1][var] = val

    def _str(self, s):
        for ch in s:
            self._ch(ch)
            if not self.ok:
                return
        self.val = s

    def _succeed(self, v, newpos=None):
        self.val = v
        self.ok = True
        if newpos is not None:
            self.pos = newpos

    def _xtou(self, s):
        return chr(int(s, base=16))
