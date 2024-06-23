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
        self.scopes = []

    def parse(self):
        self._grammar_()
        if self.failed:
            return Result(None, self._err_str(), self.errpos)
        return Result(self.val, None, self.pos)

    def _grammar_(self):
        self.scopes.append({})
        self._seq(
            [self._grammar_s0_, self._sp_, self._end_, self._grammar_s3_]
        )
        self.scopes.pop()

    def _grammar_s0_l_p_g_s1_g_(self):
        self._choose([self._pragma_, self._rule_])

    def _grammar_s0_l_p_g_(self):
        self._seq([self._sp_, self._grammar_s0_l_p_g_s1_g_])

    def _grammar_s0_(self):
        self._bind(lambda: self._star(self._grammar_s0_l_p_g_), 'vs')

    def _grammar_s3_(self):
        self._succeed(['rules', None, self._get('vs')])

    def _sp_(self):
        self._star(self._ws_)

    def _ws_(self):
        self._choose(
            [
                lambda: self._ch(' '),
                lambda: self._ch('\t'),
                self._eol_,
                self._comment_,
            ]
        )

    def _eol_(self):
        self._choose(
            [self._eol_c0_, lambda: self._ch('\r'), lambda: self._ch('\n')]
        )

    def _eol_c0_(self):
        self._seq([lambda: self._ch('\r'), lambda: self._ch('\n')])

    def _comment_(self):
        self._choose([self._comment_c0_, self._comment_c1_])

    def _comment_c0_s1_p_g_(self):
        self._seq([lambda: self._not(self._eol_), self._any_])

    def _comment_c0_(self):
        self._seq(
            [
                lambda: self._str('//'),
                lambda: self._star(self._comment_c0_s1_p_g_),
            ]
        )

    def _comment_c1_s1_p_g_(self):
        self._seq([lambda: self._not(lambda: self._str('*/')), self._any_])

    def _comment_c1_(self):
        self._seq(
            [
                lambda: self._str('/*'),
                lambda: self._star(self._comment_c1_s1_p_g_),
                lambda: self._str('*/'),
            ]
        )

    def _pragma_(self):
        self._choose(
            [
                self._pragma_c0_,
                self._pragma_c1_,
                self._pragma_c2_,
                self._pragma_c3_,
                self._pragma_c4_,
                self._pragma_c5_,
                self._pragma_c6_,
                self._pragma_c7_,
            ]
        )

    def _pragma_c0_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('%tokens'),
                lambda: self._bind(self._ident_list_, 'is'),
                self._pragma_c0_s2_,
            ]
        )
        self.scopes.pop()

    def _pragma_c0_s2_(self):
        self._succeed(['pragma', 'tokens', self._get('is')])

    def _pragma_c1_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('%token'),
                self._sp_,
                lambda: self._bind(self._ident_, 'i'),
                self._pragma_c1_s3_,
            ]
        )
        self.scopes.pop()

    def _pragma_c1_s3_(self):
        self._succeed(['pragma', 'token', [self._get('i')]])

    def _pragma_c2_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('%whitespace_style'),
                self._sp_,
                lambda: self._bind(self._ident_, 'i'),
                self._pragma_c2_s3_,
            ]
        )
        self.scopes.pop()

    def _pragma_c2_s3_(self):
        self._succeed(['pragma', 'whitespace_style', self._get('i')])

    def _pragma_c3_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('%whitespace'),
                self._sp_,
                lambda: self._ch('='),
                self._sp_,
                lambda: self._bind(self._choice_, 'cs'),
                self._pragma_c3_s5_,
            ]
        )
        self.scopes.pop()

    def _pragma_c3_s5_(self):
        self._succeed(['pragma', 'whitespace', [self._get('cs')]])

    def _pragma_c4_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('%comment_style'),
                self._sp_,
                self._pragma_c4_s2_,
                self._pragma_c4_s3_,
            ]
        )
        self.scopes.pop()

    def _pragma_c4_s2_l_g_(self):
        self._choose([lambda: self._str('C++'), self._ident_])

    def _pragma_c4_s2_(self):
        self._bind(self._pragma_c4_s2_l_g_, 'c')

    def _pragma_c4_s3_(self):
        self._succeed(['pragma', 'comment_style', self._get('c')])

    def _pragma_c5_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('%comment'),
                self._sp_,
                lambda: self._ch('='),
                self._sp_,
                lambda: self._bind(self._choice_, 'cs'),
                self._pragma_c5_s5_,
            ]
        )
        self.scopes.pop()

    def _pragma_c5_s5_(self):
        self._succeed(['pragma', 'comment', [self._get('cs')]])

    def _pragma_c6_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('%assoc'),
                self._sp_,
                lambda: self._bind(self._op_, 'o'),
                self._sp_,
                lambda: self._bind(self._dir_, 'd'),
                self._pragma_c6_s5_,
            ]
        )
        self.scopes.pop()

    def _pragma_c6_s5_(self):
        self._succeed(['pragma', 'assoc', [self._get('o'), self._get('d')]])

    def _pragma_c7_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('%prec'),
                self._pragma_c7_s1_,
                self._pragma_c7_s2_,
            ]
        )
        self.scopes.pop()

    def _pragma_c7_s1_l_p_g_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._not(self._eol_),
                self._ws_,
                lambda: self._bind(self._op_, 'o'),
                lambda: self._succeed(self._get('o')),
            ]
        )
        self.scopes.pop()

    def _pragma_c7_s1_(self):
        self._bind(lambda: self._plus(self._pragma_c7_s1_l_p_g_), 'os')

    def _pragma_c7_s2_(self):
        self._succeed(['pragma', 'prec', self._get('os')])

    def _op_(self):
        self.scopes.append({})
        self._seq([self._op_s0_, self._op_s1_])
        self.scopes.pop()

    def _op_s0_l_p_g_(self):
        self._seq([lambda: self._not(self._ws_), self._any_])

    def _op_s0_(self):
        self._bind(lambda: self._plus(self._op_s0_l_p_g_), 'op')

    def _op_s1_(self):
        self._succeed(self._join('', self._get('op')))

    def _dir_(self):
        self.scopes.append({})
        self._seq([self._dir_s0_, lambda: self._succeed(self._get('d'))])
        self.scopes.pop()

    def _dir_s0_l_g_(self):
        self._choose([lambda: self._str('left'), lambda: self._str('right')])

    def _dir_s0_(self):
        self._bind(self._dir_s0_l_g_, 'd')

    def _ident_list_(self):
        self.scopes.append({})
        self._seq(
            [self._ident_list_s0_, lambda: self._succeed(self._get('is'))]
        )
        self.scopes.pop()

    def _ident_list_s0_l_p_g_(self):
        self.scopes.append({})
        self._seq(
            [
                self._sp_,
                lambda: self._bind(self._ident_, 'i'),
                self._sp_,
                lambda: self._not(lambda: self._ch('=')),
                lambda: self._succeed(self._get('i')),
            ]
        )
        self.scopes.pop()

    def _ident_list_s0_(self):
        self._bind(lambda: self._plus(self._ident_list_s0_l_p_g_), 'is')

    def _rule_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._ident_, 'i'),
                self._sp_,
                lambda: self._ch('='),
                self._sp_,
                lambda: self._bind(self._choice_, 'cs'),
                self._sp_,
                lambda: self._opt(lambda: self._ch(',')),
                self._rule_s7_,
            ]
        )
        self.scopes.pop()

    def _rule_s7_(self):
        self._succeed(['rule', self._get('i'), [self._get('cs')]])

    def _ident_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._id_start_, 'hd'),
                self._ident_s1_,
                self._ident_s2_,
            ]
        )
        self.scopes.pop()

    def _ident_s1_(self):
        self._bind(lambda: self._star(self._id_continue_), 'tl')

    def _ident_s2_(self):
        self._succeed(self._cat([self._get('hd')] + self._get('tl')))

    def _id_start_(self):
        self._choose(
            [
                self._id_start_c0_,
                self._id_start_c1_,
                lambda: self._ch('_'),
                lambda: self._ch('$'),
            ]
        )

    def _id_start_c0_(self):
        self._range('a', 'z')

    def _id_start_c1_(self):
        self._range('A', 'Z')

    def _id_continue_(self):
        self._choose([self._id_start_, self._digit_])

    def _choice_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._seq_, 's'),
                self._choice_s1_,
                self._choice_s2_,
            ]
        )
        self.scopes.pop()

    def _choice_s1_l_p_g_(self):
        self._seq([self._sp_, lambda: self._ch('|'), self._sp_, self._seq_])

    def _choice_s1_(self):
        self._bind(lambda: self._star(self._choice_s1_l_p_g_), 'ss')

    def _choice_s2_(self):
        self._succeed(['choice', None, [self._get('s')] + self._get('ss')])

    def _seq_(self):
        self._choose([self._seq_c0_, self._seq_c1_])

    def _seq_c0_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._expr_, 'e'),
                self._seq_c0_s1_,
                self._seq_c0_s2_,
            ]
        )
        self.scopes.pop()

    def _seq_c0_s1_l_p_g_(self):
        self._seq([self._ws_, self._sp_, self._expr_])

    def _seq_c0_s1_(self):
        self._bind(lambda: self._star(self._seq_c0_s1_l_p_g_), 'es')

    def _seq_c0_s2_(self):
        self._succeed(['seq', None, [self._get('e')] + self._get('es')])

    def _seq_c1_(self):
        self._succeed(['empty', None, []])

    def _expr_(self):
        self._choose([self._expr_c0_, self._post_expr_])

    def _expr_c0_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._post_expr_, 'e'),
                lambda: self._ch(':'),
                lambda: self._bind(self._ident_, 'l'),
                self._expr_c0_s3_,
            ]
        )
        self.scopes.pop()

    def _expr_c0_s3_(self):
        self._succeed(['label', self._get('l'), [self._get('e')]])

    def _post_expr_(self):
        self._choose([self._post_expr_c0_, self._prim_expr_])

    def _post_expr_c0_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._prim_expr_, 'e'),
                lambda: self._bind(self._post_op_, 'op'),
                self._post_expr_c0_s2_,
            ]
        )
        self.scopes.pop()

    def _post_expr_c0_s2_(self):
        self._succeed(['post', self._get('op'), [self._get('e')]])

    def _post_op_(self):
        self._choose(
            [
                lambda: self._ch('?'),
                lambda: self._ch('*'),
                lambda: self._ch('+'),
            ]
        )

    def _prim_expr_(self):
        self._choose(
            [
                self._prim_expr_c0_,
                self._prim_expr_c1_,
                self._prim_expr_c2_,
                self._prim_expr_c3_,
                self._prim_expr_c4_,
                self._prim_expr_c5_,
                self._prim_expr_c6_,
                self._prim_expr_c7_,
                self._prim_expr_c8_,
                self._prim_expr_c9_,
            ]
        )

    def _prim_expr_c0_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._lit_, 'i'),
                self._sp_,
                lambda: self._str('..'),
                self._sp_,
                lambda: self._bind(self._lit_, 'j'),
                self._prim_expr_c0_s5_,
            ]
        )
        self.scopes.pop()

    def _prim_expr_c0_s5_(self):
        self._succeed(['range', None, [self._get('i'), self._get('j')]])

    def _prim_expr_c1_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._lit_, 'l'),
                lambda: self._succeed(self._get('l')),
            ]
        )
        self.scopes.pop()

    def _prim_expr_c2_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._escape_, 'e'),
                lambda: self._succeed(self._get('e')),
            ]
        )
        self.scopes.pop()

    def _prim_expr_c3_s1_n_g_(self):
        self._seq([self._sp_, lambda: self._ch('=')])

    def _prim_expr_c3_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._ident_, 'i'),
                lambda: self._not(self._prim_expr_c3_s1_n_g_),
                self._prim_expr_c3_s2_,
            ]
        )
        self.scopes.pop()

    def _prim_expr_c3_s2_(self):
        self._succeed(['apply', self._get('i'), []])

    def _prim_expr_c4_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('->'),
                self._sp_,
                lambda: self._bind(self._ll_expr_, 'e'),
                self._prim_expr_c4_s3_,
            ]
        )
        self.scopes.pop()

    def _prim_expr_c4_s3_(self):
        self._succeed(['action', None, [self._get('e')]])

    def _prim_expr_c5_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._ch('{'),
                self._sp_,
                lambda: self._bind(self._ll_expr_, 'e'),
                self._sp_,
                lambda: self._ch('}'),
                self._prim_expr_c5_s5_,
            ]
        )
        self.scopes.pop()

    def _prim_expr_c5_s5_(self):
        self._succeed(['action', None, [self._get('e')]])

    def _prim_expr_c6_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._ch('~'),
                lambda: self._bind(self._prim_expr_, 'e'),
                self._prim_expr_c6_s2_,
            ]
        )
        self.scopes.pop()

    def _prim_expr_c6_s2_(self):
        self._succeed(['not', None, [self._get('e')]])

    def _prim_expr_c7_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('?('),
                self._sp_,
                lambda: self._bind(self._ll_expr_, 'e'),
                self._sp_,
                lambda: self._ch(')'),
                self._prim_expr_c7_s5_,
            ]
        )
        self.scopes.pop()

    def _prim_expr_c7_s5_(self):
        self._succeed(['pred', None, [self._get('e')]])

    def _prim_expr_c8_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('?{'),
                self._sp_,
                lambda: self._bind(self._ll_expr_, 'e'),
                self._sp_,
                lambda: self._ch('}'),
                self._prim_expr_c8_s5_,
            ]
        )
        self.scopes.pop()

    def _prim_expr_c8_s5_(self):
        self._succeed(['pred', None, [self._get('e')]])

    def _prim_expr_c9_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._ch('('),
                self._sp_,
                lambda: self._bind(self._choice_, 'e'),
                self._sp_,
                lambda: self._ch(')'),
                self._prim_expr_c9_s5_,
            ]
        )
        self.scopes.pop()

    def _prim_expr_c9_s5_(self):
        self._succeed(['paren', None, [self._get('e')]])

    def _lit_(self):
        self._choose([self._lit_c0_, self._lit_c1_])

    def _lit_c0_(self):
        self.scopes.append({})
        self._seq(
            [self._squote_, self._lit_c0_s1_, self._squote_, self._lit_c0_s3_]
        )
        self.scopes.pop()

    def _lit_c0_s1_(self):
        self._bind(lambda: self._star(self._sqchar_), 'cs')

    def _lit_c0_s3_(self):
        self._succeed(['lit', self._cat(self._get('cs')), []])

    def _lit_c1_(self):
        self.scopes.append({})
        self._seq(
            [self._dquote_, self._lit_c1_s1_, self._dquote_, self._lit_c1_s3_]
        )
        self.scopes.pop()

    def _lit_c1_s1_(self):
        self._bind(lambda: self._star(self._dqchar_), 'cs')

    def _lit_c1_s3_(self):
        self._succeed(['lit', self._cat(self._get('cs')), []])

    def _sqchar_(self):
        self._choose([self._sqchar_c0_, self._sqchar_c1_])

    def _sqchar_c0_(self):
        self.scopes.append({})
        self._seq(
            [
                self._bslash_,
                lambda: self._bind(self._esc_char_, 'c'),
                lambda: self._succeed(self._get('c')),
            ]
        )
        self.scopes.pop()

    def _sqchar_c1_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._not(self._squote_),
                lambda: self._bind(self._any_, 'c'),
                lambda: self._succeed(self._get('c')),
            ]
        )
        self.scopes.pop()

    def _dqchar_(self):
        self._choose([self._dqchar_c0_, self._dqchar_c1_])

    def _dqchar_c0_(self):
        self.scopes.append({})
        self._seq(
            [
                self._bslash_,
                lambda: self._bind(self._esc_char_, 'c'),
                lambda: self._succeed(self._get('c')),
            ]
        )
        self.scopes.pop()

    def _dqchar_c1_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._not(self._dquote_),
                lambda: self._bind(self._any_, 'c'),
                lambda: self._succeed(self._get('c')),
            ]
        )
        self.scopes.pop()

    def _bslash_(self):
        self._ch('\\')

    def _squote_(self):
        self._ch("'")

    def _dquote_(self):
        self._ch('"')

    def _esc_char_(self):
        self._choose(
            [
                self._esc_char_c0_,
                self._esc_char_c1_,
                self._esc_char_c2_,
                self._esc_char_c3_,
                self._esc_char_c4_,
                self._esc_char_c5_,
                self._esc_char_c6_,
                self._esc_char_c7_,
                self._esc_char_c8_,
                self._esc_char_c9_,
                self._esc_char_c10_,
            ]
        )

    def _esc_char_c0_(self):
        self._seq([lambda: self._ch('b'), lambda: self._succeed('\b')])

    def _esc_char_c1_(self):
        self._seq([lambda: self._ch('f'), lambda: self._succeed('\f')])

    def _esc_char_c2_(self):
        self._seq([lambda: self._ch('n'), lambda: self._succeed('\n')])

    def _esc_char_c3_(self):
        self._seq([lambda: self._ch('r'), lambda: self._succeed('\r')])

    def _esc_char_c4_(self):
        self._seq([lambda: self._ch('t'), lambda: self._succeed('\t')])

    def _esc_char_c5_(self):
        self._seq([lambda: self._ch('v'), lambda: self._succeed('\v')])

    def _esc_char_c6_(self):
        self._seq([self._squote_, lambda: self._succeed("'")])

    def _esc_char_c7_(self):
        self._seq([self._dquote_, lambda: self._succeed('"')])

    def _esc_char_c8_(self):
        self._seq([self._bslash_, lambda: self._succeed('\\')])

    def _esc_char_c9_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._hex_esc_, 'c'),
                lambda: self._succeed(self._get('c')),
            ]
        )
        self.scopes.pop()

    def _esc_char_c10_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._unicode_esc_, 'c'),
                lambda: self._succeed(self._get('c')),
            ]
        )
        self.scopes.pop()

    def _hex_esc_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._ch('x'),
                lambda: self._bind(self._hex_, 'h1'),
                lambda: self._bind(self._hex_, 'h2'),
                self._hex_esc_s3_,
            ]
        )
        self.scopes.pop()

    def _hex_esc_s3_(self):
        self._succeed(self._xtou(self._get('h1') + self._get('h2')))

    def _unicode_esc_(self):
        self._choose([self._unicode_esc_c0_, self._unicode_esc_c1_])

    def _unicode_esc_c0_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._ch('u'),
                lambda: self._bind(self._hex_, 'h1'),
                lambda: self._bind(self._hex_, 'h2'),
                lambda: self._bind(self._hex_, 'h3'),
                lambda: self._bind(self._hex_, 'h4'),
                self._unicode_esc_c0_s5_,
            ]
        )
        self.scopes.pop()

    def _unicode_esc_c0_s5_(self):
        self._succeed(
            self._xtou(
                self._get('h1')
                + self._get('h2')
                + self._get('h3')
                + self._get('h4'),
            )
        )

    def _unicode_esc_c1_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._ch('U'),
                lambda: self._bind(self._hex_, 'h1'),
                lambda: self._bind(self._hex_, 'h2'),
                lambda: self._bind(self._hex_, 'h3'),
                lambda: self._bind(self._hex_, 'h4'),
                lambda: self._bind(self._hex_, 'h5'),
                lambda: self._bind(self._hex_, 'h6'),
                lambda: self._bind(self._hex_, 'h7'),
                lambda: self._bind(self._hex_, 'h8'),
                self._unicode_esc_c1_s9_,
            ]
        )
        self.scopes.pop()

    def _unicode_esc_c1_s9_(self):
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

    def _escape_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('\\p{'),
                lambda: self._bind(self._ident_, 'i'),
                lambda: self._ch('}'),
                self._escape_s3_,
            ]
        )
        self.scopes.pop()

    def _escape_s3_(self):
        self._succeed(['unicat', self._get('i'), []])

    def _ll_exprs_(self):
        self._choose([self._ll_exprs_c0_, self._ll_exprs_c1_])

    def _ll_exprs_c0_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._ll_expr_, 'e'),
                self._ll_exprs_c0_s1_,
                self._ll_exprs_c0_s2_,
            ]
        )
        self.scopes.pop()

    def _ll_exprs_c0_s1_l_p_g_(self):
        self._seq(
            [self._sp_, lambda: self._ch(','), self._sp_, self._ll_expr_]
        )

    def _ll_exprs_c0_s1_(self):
        self._bind(lambda: self._star(self._ll_exprs_c0_s1_l_p_g_), 'es')

    def _ll_exprs_c0_s2_(self):
        self._succeed([self._get('e')] + self._get('es'))

    def _ll_exprs_c1_(self):
        self._succeed([])

    def _ll_expr_(self):
        self._choose([self._ll_expr_c0_, self._ll_expr_c1_, self._ll_qual_])

    def _ll_expr_c0_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._ll_qual_, 'e1'),
                self._sp_,
                lambda: self._ch('+'),
                self._sp_,
                lambda: self._bind(self._ll_expr_, 'e2'),
                self._ll_expr_c0_s5_,
            ]
        )
        self.scopes.pop()

    def _ll_expr_c0_s5_(self):
        self._succeed(['ll_plus', None, [self._get('e1'), self._get('e2')]])

    def _ll_expr_c1_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._ll_qual_, 'e1'),
                self._sp_,
                lambda: self._ch('-'),
                self._sp_,
                lambda: self._bind(self._ll_expr_, 'e2'),
                self._ll_expr_c1_s5_,
            ]
        )
        self.scopes.pop()

    def _ll_expr_c1_s5_(self):
        self._succeed(['ll_minus', None, [self._get('e1'), self._get('e2')]])

    def _ll_qual_(self):
        self._choose([self._ll_qual_c0_, self._ll_prim_])

    def _ll_qual_c0_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._bind(self._ll_prim_, 'e'),
                self._ll_qual_c0_s1_,
                self._ll_qual_c0_s2_,
            ]
        )
        self.scopes.pop()

    def _ll_qual_c0_s1_(self):
        self._bind(lambda: self._plus(self._ll_post_op_), 'ps')

    def _ll_qual_c0_s2_(self):
        self._succeed(['ll_qual', None, [self._get('e')] + self._get('ps')])

    def _ll_post_op_(self):
        self._choose([self._ll_post_op_c0_, self._ll_post_op_c1_])

    def _ll_post_op_c0_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._ch('['),
                self._sp_,
                lambda: self._bind(self._ll_expr_, 'e'),
                self._sp_,
                lambda: self._ch(']'),
                self._ll_post_op_c0_s5_,
            ]
        )
        self.scopes.pop()

    def _ll_post_op_c0_s5_(self):
        self._succeed(['ll_getitem', None, [self._get('e')]])

    def _ll_post_op_c1_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._ch('('),
                self._sp_,
                lambda: self._bind(self._ll_exprs_, 'es'),
                self._sp_,
                lambda: self._ch(')'),
                self._ll_post_op_c1_s5_,
            ]
        )
        self.scopes.pop()

    def _ll_post_op_c1_s5_(self):
        self._succeed(['ll_call', None, self._get('es')])

    def _ll_prim_(self):
        self._choose(
            [
                self._ll_prim_c0_,
                self._ll_prim_c1_,
                self._ll_prim_c2_,
                self._ll_prim_c3_,
                self._ll_prim_c4_,
                self._ll_prim_c5_,
                self._ll_prim_c6_,
                self._ll_prim_c7_,
                self._ll_prim_c8_,
                self._ll_prim_c9_,
                self._ll_prim_c10_,
            ]
        )

    def _ll_prim_c0_(self):
        self._seq([lambda: self._str('false'), self._ll_prim_c0_s1_])

    def _ll_prim_c0_s1_(self):
        self._succeed(['ll_const', 'false', []])

    def _ll_prim_c1_(self):
        self._seq([lambda: self._str('null'), self._ll_prim_c1_s1_])

    def _ll_prim_c1_s1_(self):
        self._succeed(['ll_const', 'null', []])

    def _ll_prim_c2_(self):
        self._seq([lambda: self._str('true'), self._ll_prim_c2_s1_])

    def _ll_prim_c2_s1_(self):
        self._succeed(['ll_const', 'true', []])

    def _ll_prim_c3_(self):
        self._seq([lambda: self._str('Infinity'), self._ll_prim_c3_s1_])

    def _ll_prim_c3_s1_(self):
        self._succeed(['ll_const', 'Infinity', []])

    def _ll_prim_c4_(self):
        self._seq([lambda: self._str('NaN'), self._ll_prim_c4_s1_])

    def _ll_prim_c4_s1_(self):
        self._succeed(['ll_const', 'NaN', []])

    def _ll_prim_c5_(self):
        self.scopes.append({})
        self._seq(
            [lambda: self._bind(self._ident_, 'i'), self._ll_prim_c5_s1_]
        )
        self.scopes.pop()

    def _ll_prim_c5_s1_(self):
        self._succeed(['ll_var', self._get('i'), []])

    def _ll_prim_c6_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._str('0x'),
                lambda: self._bind(self._hexdigits_, 'hs'),
                self._ll_prim_c6_s2_,
            ]
        )
        self.scopes.pop()

    def _ll_prim_c6_s2_(self):
        self._succeed(['ll_num', '0x' + self._get('hs'), []])

    def _ll_prim_c7_(self):
        self.scopes.append({})
        self._seq(
            [lambda: self._bind(self._digits_, 'ds'), self._ll_prim_c7_s1_]
        )
        self.scopes.pop()

    def _ll_prim_c7_s1_(self):
        self._succeed(['ll_num', self._get('ds'), []])

    def _ll_prim_c8_(self):
        self.scopes.append({})
        self._seq([lambda: self._bind(self._lit_, 'l'), self._ll_prim_c8_s1_])
        self.scopes.pop()

    def _ll_prim_c8_s1_(self):
        self._succeed(['ll_lit', self._get('l')[1], []])

    def _ll_prim_c9_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._ch('('),
                self._sp_,
                lambda: self._bind(self._ll_expr_, 'e'),
                self._sp_,
                lambda: self._ch(')'),
                self._ll_prim_c9_s5_,
            ]
        )
        self.scopes.pop()

    def _ll_prim_c9_s5_(self):
        self._succeed(['ll_paren', None, [self._get('e')]])

    def _ll_prim_c10_(self):
        self.scopes.append({})
        self._seq(
            [
                lambda: self._ch('['),
                self._sp_,
                lambda: self._bind(self._ll_exprs_, 'es'),
                self._sp_,
                lambda: self._ch(']'),
                self._ll_prim_c10_s5_,
            ]
        )
        self.scopes.pop()

    def _ll_prim_c10_s5_(self):
        self._succeed(['ll_arr', None, self._get('es')])

    def _digits_(self):
        self.scopes.append({})
        self._seq([self._digits_s0_, self._digits_s1_])
        self.scopes.pop()

    def _digits_s0_(self):
        self._bind(lambda: self._plus(self._digit_), 'ds')

    def _digits_s1_(self):
        self._succeed(self._cat(self._get('ds')))

    def _hexdigits_(self):
        self.scopes.append({})
        self._seq([self._hexdigits_s0_, self._hexdigits_s1_])
        self.scopes.pop()

    def _hexdigits_s0_(self):
        self._bind(lambda: self._plus(self._hex_), 'hs')

    def _hexdigits_s1_(self):
        self._succeed(self._cat(self._get('hs')))

    def _hex_(self):
        self._choose([self._digit_, self._hex_c1_, self._hex_c2_])

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

    def _bind(self, rule, var):
        rule()
        if not self.failed:
            self._set(var, self.val)

    def _cat(self, strs):
        return ''.join(strs)

    def _ch(self, ch):
        p = self.pos
        if p < self.end and self.text[p] == ch:
            self._succeed(ch, self.pos + 1)
        else:
            self._fail()

    def _choose(self, rules):
        p = self.pos
        for rule in rules[:-1]:
            rule()
            if not self.failed:
                return
            self._rewind(p)
        rules[-1]()

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
        self.failed = True
        self.errpos = max(self.errpos, self.pos)

    def _get(self, var):
        return self.scopes[-1][var]

    def _join(self, s, vs):
        return s.join(vs)

    def _not(self, rule):
        p = self.pos
        errpos = self.errpos
        rule()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _opt(self, rule):
        p = self.pos
        rule()
        if self.failed:
            self._succeed([], p)
        else:
            self._succeed([self.val])

    def _plus(self, rule):
        vs = []
        rule()
        vs.append(self.val)
        if self.failed:
            return
        self._star(rule, vs)

    def _range(self, i, j):
        p = self.pos
        if p != self.end and ord(i) <= ord(self.text[p]) <= ord(j):
            self._succeed(self.text[p], self.pos + 1)
        else:
            self._fail()

    def _rewind(self, newpos):
        self._succeed(None, newpos)

    def _seq(self, rules):
        for rule in rules:
            rule()
            if self.failed:
                return

    def _set(self, var, val):
        self.scopes[-1][var] = val

    def _star(self, rule, vs=None):
        vs = vs or []
        while True:
            p = self.pos
            rule()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

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

    def _xtou(self, s):
        return chr(int(s, base=16))
