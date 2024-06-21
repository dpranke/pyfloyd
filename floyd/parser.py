# pylint: disable=too-many-lines


class Parser:
    def __init__(self, msg, fname):
        self.msg = msg
        self.end = len(self.msg)
        self.errpos = 0
        self.failed = False
        self.fname = fname
        self.pos = 0
        self.val = None
        self.scopes = []

    def parse(self):
        self._grammar_()
        if self.failed:
            return None, self._err_str(), self.errpos
        return self.val, None, self.pos

    def _grammar_(self):
        self._push('grammar')
        self._seq([self._grammar_s0_, self._sp_, self._end_, self._grammar_s1_])
        self._pop('grammar')

    def _grammar_s0_(self):
        self._bind(self._grammar_s0_l_, 'vs')

    def _grammar_s0_l_(self):
        self._star(self._grammar_s0_l_p_)

    def _grammar_s0_l_p_(self):
        self._grammar_s0_l_p_g_()

    def _grammar_s0_l_p_g_(self):
        self._seq([self._sp_, self._grammar_s0_l_p_g_s0_])

    def _grammar_s0_l_p_g_s0_(self):
        self._grammar_s0_l_p_g_s0_g_()

    def _grammar_s0_l_p_g_s0_g_(self):
        self._choose(
            [
                lambda: self._seq([self._pragma_]),
                lambda: self._seq([self._rule_]),
            ]
        )

    def _grammar_s1_(self):
        self._succeed(['rules', None, self._get('vs')])

    def _sp_(self):
        self._star(self._ws_)

    def _ws_(self):
        self._choose(
            [
                lambda: self._ch(' '),
                lambda: self._ch('\t'),
                lambda: self._seq([self._eol_]),
                lambda: self._seq([self._comment_]),
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

    def _comment_c0_(self):
        self._seq([lambda: self._str('//'), self._comment_c0_s0_])

    def _comment_c0_s0_(self):
        self._star(self._comment_c0_s0_p_)

    def _comment_c0_s0_p_(self):
        self._comment_c0_s0_p_g_()

    def _comment_c0_s0_p_g_(self):
        self._seq([self._comment_c0_s0_p_g_s0_, self._any_])

    def _comment_c0_s0_p_g_s0_(self):
        self._not(self._comment_c0_s0_p_g_s0_n_)

    def _comment_c0_s0_p_g_s0_n_(self):
        self._eol_()

    def _comment_c1_(self):
        self._seq(
            [
                lambda: self._str('/*'),
                self._comment_c1_s0_,
                lambda: self._str('*/'),
            ]
        )

    def _comment_c1_s0_(self):
        self._star(self._comment_c1_s0_p_)

    def _comment_c1_s0_p_(self):
        self._comment_c1_s0_p_g_()

    def _comment_c1_s0_p_g_(self):
        self._seq([self._comment_c1_s0_p_g_s0_, self._any_])

    def _comment_c1_s0_p_g_s0_(self):
        self._not(self._comment_c1_s0_p_g_s0_n_)

    def _comment_c1_s0_p_g_s0_n_(self):
        self._str('*/')

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
        self._push('pragma_c0')
        self._seq(
            [
                lambda: self._str('%tokens'),
                self._pragma_c0_s0_,
                self._pragma_c0_s1_,
            ]
        )
        self._pop('pragma_c0')

    def _pragma_c0_s0_(self):
        self._bind(self._pragma_c0_s0_l_, 'is')

    def _pragma_c0_s0_l_(self):
        self._ident_list_()

    def _pragma_c0_s1_(self):
        self._succeed(['pragma', 'tokens', self._get('is')])

    def _pragma_c1_(self):
        self._push('pragma_c1')
        self._seq(
            [
                lambda: self._str('%token'),
                self._sp_,
                self._pragma_c1_s0_,
                self._pragma_c1_s1_,
            ]
        )
        self._pop('pragma_c1')

    def _pragma_c1_s0_(self):
        self._bind(self._pragma_c1_s0_l_, 'i')

    def _pragma_c1_s0_l_(self):
        self._ident_()

    def _pragma_c1_s1_(self):
        self._succeed(['pragma', 'token', [self._get('i')]])

    def _pragma_c2_(self):
        self._push('pragma_c2')
        self._seq(
            [
                lambda: self._str('%whitespace_style'),
                self._sp_,
                self._pragma_c2_s0_,
                self._pragma_c2_s1_,
            ]
        )
        self._pop('pragma_c2')

    def _pragma_c2_s0_(self):
        self._bind(self._pragma_c2_s0_l_, 'i')

    def _pragma_c2_s0_l_(self):
        self._ident_()

    def _pragma_c2_s1_(self):
        self._succeed(['pragma', 'whitespace_style', self._get('i')])

    def _pragma_c3_(self):
        self._push('pragma_c3')
        self._seq(
            [
                lambda: self._str('%whitespace'),
                self._sp_,
                lambda: self._ch('='),
                self._sp_,
                self._pragma_c3_s0_,
                self._pragma_c3_s1_,
            ]
        )
        self._pop('pragma_c3')

    def _pragma_c3_s0_(self):
        self._bind(self._pragma_c3_s0_l_, 'cs')

    def _pragma_c3_s0_l_(self):
        self._choice_()

    def _pragma_c3_s1_(self):
        self._succeed(['pragma', 'whitespace', [self._get('cs')]])

    def _pragma_c4_(self):
        self._push('pragma_c4')
        self._seq(
            [
                lambda: self._str('%comment_style'),
                self._sp_,
                self._pragma_c4_s0_,
                self._pragma_c4_s1_,
            ]
        )
        self._pop('pragma_c4')

    def _pragma_c4_s0_(self):
        self._bind(self._pragma_c4_s0_l_, 'c')

    def _pragma_c4_s0_l_(self):
        self._pragma_c4_s0_l_g_()

    def _pragma_c4_s0_l_g_(self):
        self._choose(
            [lambda: self._str('C++'), lambda: self._seq([self._ident_])]
        )

    def _pragma_c4_s1_(self):
        self._succeed(['pragma', 'comment_style', self._get('c')])

    def _pragma_c5_(self):
        self._push('pragma_c5')
        self._seq(
            [
                lambda: self._str('%comment'),
                self._sp_,
                lambda: self._ch('='),
                self._sp_,
                self._pragma_c5_s0_,
                self._pragma_c5_s1_,
            ]
        )
        self._pop('pragma_c5')

    def _pragma_c5_s0_(self):
        self._bind(self._pragma_c5_s0_l_, 'cs')

    def _pragma_c5_s0_l_(self):
        self._choice_()

    def _pragma_c5_s1_(self):
        self._succeed(['pragma', 'comment', [self._get('cs')]])

    def _pragma_c6_(self):
        self._push('pragma_c6')
        self._seq(
            [
                lambda: self._str('%assoc'),
                self._sp_,
                self._pragma_c6_s0_,
                self._sp_,
                self._pragma_c6_s1_,
                self._pragma_c6_s2_,
            ]
        )
        self._pop('pragma_c6')

    def _pragma_c6_s0_(self):
        self._bind(self._pragma_c6_s0_l_, 'o')

    def _pragma_c6_s0_l_(self):
        self._op_()

    def _pragma_c6_s1_(self):
        self._bind(self._pragma_c6_s1_l_, 'd')

    def _pragma_c6_s1_l_(self):
        self._dir_()

    def _pragma_c6_s2_(self):
        self._succeed(['pragma', 'assoc', [self._get('o'), self._get('d')]])

    def _pragma_c7_(self):
        self._push('pragma_c7')
        self._seq(
            [
                lambda: self._str('%prec'),
                self._pragma_c7_s0_,
                self._pragma_c7_s1_,
            ]
        )
        self._pop('pragma_c7')

    def _pragma_c7_s0_(self):
        self._bind(self._pragma_c7_s0_l_, 'os')

    def _pragma_c7_s0_l_(self):
        self._plus(self._pragma_c7_s0_l_p_)

    def _pragma_c7_s0_l_p_(self):
        self._pragma_c7_s0_l_p_g_()

    def _pragma_c7_s0_l_p_g_(self):
        self._push('pragma_c7_s0_l_p_g')
        self._seq(
            [
                self._pragma_c7_s0_l_p_g_s0_,
                self._ws_,
                self._pragma_c7_s0_l_p_g_s1_,
                self._pragma_c7_s0_l_p_g_s2_,
            ]
        )
        self._pop('pragma_c7_s0_l_p_g')

    def _pragma_c7_s0_l_p_g_s0_(self):
        self._not(self._pragma_c7_s0_l_p_g_s0_n_)

    def _pragma_c7_s0_l_p_g_s0_n_(self):
        self._eol_()

    def _pragma_c7_s0_l_p_g_s1_(self):
        self._bind(self._pragma_c7_s0_l_p_g_s1_l_, 'o')

    def _pragma_c7_s0_l_p_g_s1_l_(self):
        self._op_()

    def _pragma_c7_s0_l_p_g_s2_(self):
        self._succeed(self._get('o'))

    def _pragma_c7_s1_(self):
        self._succeed(['pragma', 'prec', self._get('os')])

    def _op_(self):
        self._push('op')
        self._seq([self._op_s0_, self._op_s1_])
        self._pop('op')

    def _op_s0_(self):
        self._bind(self._op_s0_l_, 'op')

    def _op_s0_l_(self):
        self._plus(self._op_s0_l_p_)

    def _op_s0_l_p_(self):
        self._op_s0_l_p_g_()

    def _op_s0_l_p_g_(self):
        self._seq([self._op_s0_l_p_g_s0_, self._any_])

    def _op_s0_l_p_g_s0_(self):
        self._not(self._op_s0_l_p_g_s0_n_)

    def _op_s0_l_p_g_s0_n_(self):
        self._ws_()

    def _op_s1_(self):
        self._succeed(self._join('', self._get('op')))

    def _dir_(self):
        self._push('dir')
        self._seq([self._dir_s0_, self._dir_s1_])
        self._pop('dir')

    def _dir_s0_(self):
        self._bind(self._dir_s0_l_, 'd')

    def _dir_s0_l_(self):
        self._dir_s0_l_g_()

    def _dir_s0_l_g_(self):
        self._choose([lambda: self._str('left'), lambda: self._str('right')])

    def _dir_s1_(self):
        self._succeed(self._get('d'))

    def _ident_list_(self):
        self._push('ident_list')
        self._seq([self._ident_list_s0_, self._ident_list_s1_])
        self._pop('ident_list')

    def _ident_list_s0_(self):
        self._bind(self._ident_list_s0_l_, 'is')

    def _ident_list_s0_l_(self):
        self._plus(self._ident_list_s0_l_p_)

    def _ident_list_s0_l_p_(self):
        self._ident_list_s0_l_p_g_()

    def _ident_list_s0_l_p_g_(self):
        self._push('ident_list_s0_l_p_g')
        self._seq(
            [
                self._sp_,
                self._ident_list_s0_l_p_g_s0_,
                self._sp_,
                self._ident_list_s0_l_p_g_s1_,
                self._ident_list_s0_l_p_g_s2_,
            ]
        )
        self._pop('ident_list_s0_l_p_g')

    def _ident_list_s0_l_p_g_s0_(self):
        self._bind(self._ident_list_s0_l_p_g_s0_l_, 'i')

    def _ident_list_s0_l_p_g_s0_l_(self):
        self._ident_()

    def _ident_list_s0_l_p_g_s1_(self):
        self._not(self._ident_list_s0_l_p_g_s1_n_)

    def _ident_list_s0_l_p_g_s1_n_(self):
        self._ch('=')

    def _ident_list_s0_l_p_g_s2_(self):
        self._succeed(self._get('i'))

    def _ident_list_s1_(self):
        self._succeed(self._get('is'))

    def _rule_(self):
        self._push('rule')
        self._seq(
            [
                self._rule_s0_,
                self._sp_,
                lambda: self._ch('='),
                self._sp_,
                self._rule_s1_,
                self._sp_,
                lambda: self._opt(lambda: self._ch(',')),
                self._rule_s2_,
            ]
        )
        self._pop('rule')

    def _rule_s0_(self):
        self._bind(self._rule_s0_l_, 'i')

    def _rule_s0_l_(self):
        self._ident_()

    def _rule_s1_(self):
        self._bind(self._rule_s1_l_, 'cs')

    def _rule_s1_l_(self):
        self._choice_()

    def _rule_s2_(self):
        self._succeed(['rule', self._get('i'), [self._get('cs')]])

    def _ident_(self):
        self._push('ident')
        self._seq([self._ident_s0_, self._ident_s1_, self._ident_s2_])
        self._pop('ident')

    def _ident_s0_(self):
        self._bind(self._ident_s0_l_, 'hd')

    def _ident_s0_l_(self):
        self._id_start_()

    def _ident_s1_(self):
        self._bind(self._ident_s1_l_, 'tl')

    def _ident_s1_l_(self):
        self._star(self._id_continue_)

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
        self._choose(
            [
                lambda: self._seq([self._id_start_]),
                lambda: self._seq([self._digit_]),
            ]
        )

    def _choice_(self):
        self._push('choice')
        self._seq([self._choice_s0_, self._choice_s1_, self._choice_s2_])
        self._pop('choice')

    def _choice_s0_(self):
        self._bind(self._choice_s0_l_, 's')

    def _choice_s0_l_(self):
        self._seq_()

    def _choice_s1_(self):
        self._bind(self._choice_s1_l_, 'ss')

    def _choice_s1_l_(self):
        self._star(self._choice_s1_l_p_)

    def _choice_s1_l_p_(self):
        self._choice_s1_l_p_g_()

    def _choice_s1_l_p_g_(self):
        self._seq([self._sp_, lambda: self._ch('|'), self._sp_, self._seq_])

    def _choice_s2_(self):
        self._succeed(['choice', None, [self._get('s')] + self._get('ss')])

    def _seq_(self):
        self._choose([self._seq_c0_, self._seq_c1_])

    def _seq_c0_(self):
        self._push('seq_c0')
        self._seq([self._seq_c0_s0_, self._seq_c0_s1_, self._seq_c0_s2_])
        self._pop('seq_c0')

    def _seq_c0_s0_(self):
        self._bind(self._seq_c0_s0_l_, 'e')

    def _seq_c0_s0_l_(self):
        self._expr_()

    def _seq_c0_s1_(self):
        self._bind(self._seq_c0_s1_l_, 'es')

    def _seq_c0_s1_l_(self):
        self._star(self._seq_c0_s1_l_p_)

    def _seq_c0_s1_l_p_(self):
        self._seq_c0_s1_l_p_g_()

    def _seq_c0_s1_l_p_g_(self):
        self._seq([self._ws_, self._sp_, self._expr_])

    def _seq_c0_s2_(self):
        self._succeed(['seq', None, [self._get('e')] + self._get('es')])

    def _seq_c1_(self):
        self._succeed(['empty', None, []])

    def _expr_(self):
        self._choose([self._expr_c0_, lambda: self._seq([self._post_expr_])])

    def _expr_c0_(self):
        self._push('expr_c0')
        self._seq(
            [
                self._expr_c0_s0_,
                lambda: self._ch(':'),
                self._expr_c0_s1_,
                self._expr_c0_s2_,
            ]
        )
        self._pop('expr_c0')

    def _expr_c0_s0_(self):
        self._bind(self._expr_c0_s0_l_, 'e')

    def _expr_c0_s0_l_(self):
        self._post_expr_()

    def _expr_c0_s1_(self):
        self._bind(self._expr_c0_s1_l_, 'l')

    def _expr_c0_s1_l_(self):
        self._ident_()

    def _expr_c0_s2_(self):
        self._succeed(['label', self._get('l'), [self._get('e')]])

    def _post_expr_(self):
        self._choose(
            [self._post_expr_c0_, lambda: self._seq([self._prim_expr_])]
        )

    def _post_expr_c0_(self):
        self._push('post_expr_c0')
        self._seq(
            [
                self._post_expr_c0_s0_,
                self._post_expr_c0_s1_,
                self._post_expr_c0_s2_,
            ]
        )
        self._pop('post_expr_c0')

    def _post_expr_c0_s0_(self):
        self._bind(self._post_expr_c0_s0_l_, 'e')

    def _post_expr_c0_s0_l_(self):
        self._prim_expr_()

    def _post_expr_c0_s1_(self):
        self._bind(self._post_expr_c0_s1_l_, 'op')

    def _post_expr_c0_s1_l_(self):
        self._post_op_()

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
        self._push('prim_expr_c0')
        self._seq(
            [
                self._prim_expr_c0_s0_,
                self._sp_,
                lambda: self._str('..'),
                self._sp_,
                self._prim_expr_c0_s1_,
                self._prim_expr_c0_s2_,
            ]
        )
        self._pop('prim_expr_c0')

    def _prim_expr_c0_s0_(self):
        self._bind(self._prim_expr_c0_s0_l_, 'i')

    def _prim_expr_c0_s0_l_(self):
        self._lit_()

    def _prim_expr_c0_s1_(self):
        self._bind(self._prim_expr_c0_s1_l_, 'j')

    def _prim_expr_c0_s1_l_(self):
        self._lit_()

    def _prim_expr_c0_s2_(self):
        self._succeed(['range', None, [self._get('i'), self._get('j')]])

    def _prim_expr_c1_(self):
        self._push('prim_expr_c1')
        self._seq([self._prim_expr_c1_s0_, self._prim_expr_c1_s1_])
        self._pop('prim_expr_c1')

    def _prim_expr_c1_s0_(self):
        self._bind(self._prim_expr_c1_s0_l_, 'l')

    def _prim_expr_c1_s0_l_(self):
        self._lit_()

    def _prim_expr_c1_s1_(self):
        self._succeed(self._get('l'))

    def _prim_expr_c2_(self):
        self._push('prim_expr_c2')
        self._seq([self._prim_expr_c2_s0_, self._prim_expr_c2_s1_])
        self._pop('prim_expr_c2')

    def _prim_expr_c2_s0_(self):
        self._bind(self._prim_expr_c2_s0_l_, 'e')

    def _prim_expr_c2_s0_l_(self):
        self._escape_()

    def _prim_expr_c2_s1_(self):
        self._succeed(self._get('e'))

    def _prim_expr_c3_(self):
        self._push('prim_expr_c3')
        self._seq(
            [
                self._prim_expr_c3_s0_,
                self._prim_expr_c3_s1_,
                self._prim_expr_c3_s2_,
            ]
        )
        self._pop('prim_expr_c3')

    def _prim_expr_c3_s0_(self):
        self._bind(self._prim_expr_c3_s0_l_, 'i')

    def _prim_expr_c3_s0_l_(self):
        self._ident_()

    def _prim_expr_c3_s1_(self):
        self._not(self._prim_expr_c3_s1_n_)

    def _prim_expr_c3_s1_n_(self):
        self._prim_expr_c3_s1_n_g_()

    def _prim_expr_c3_s1_n_g_(self):
        self._seq([self._sp_, lambda: self._ch('=')])

    def _prim_expr_c3_s2_(self):
        self._succeed(['apply', self._get('i'), []])

    def _prim_expr_c4_(self):
        self._push('prim_expr_c4')
        self._seq(
            [
                lambda: self._str('->'),
                self._sp_,
                self._prim_expr_c4_s0_,
                self._prim_expr_c4_s1_,
            ]
        )
        self._pop('prim_expr_c4')

    def _prim_expr_c4_s0_(self):
        self._bind(self._prim_expr_c4_s0_l_, 'e')

    def _prim_expr_c4_s0_l_(self):
        self._ll_expr_()

    def _prim_expr_c4_s1_(self):
        self._succeed(['action', None, [self._get('e')]])

    def _prim_expr_c5_(self):
        self._push('prim_expr_c5')
        self._seq(
            [
                lambda: self._ch('{'),
                self._sp_,
                self._prim_expr_c5_s0_,
                self._sp_,
                lambda: self._ch('}'),
                self._prim_expr_c5_s1_,
            ]
        )
        self._pop('prim_expr_c5')

    def _prim_expr_c5_s0_(self):
        self._bind(self._prim_expr_c5_s0_l_, 'e')

    def _prim_expr_c5_s0_l_(self):
        self._ll_expr_()

    def _prim_expr_c5_s1_(self):
        self._succeed(['action', None, [self._get('e')]])

    def _prim_expr_c6_(self):
        self._push('prim_expr_c6')
        self._seq(
            [
                lambda: self._ch('~'),
                self._prim_expr_c6_s0_,
                self._prim_expr_c6_s1_,
            ]
        )
        self._pop('prim_expr_c6')

    def _prim_expr_c6_s0_(self):
        self._bind(self._prim_expr_c6_s0_l_, 'e')

    def _prim_expr_c6_s0_l_(self):
        self._prim_expr_()

    def _prim_expr_c6_s1_(self):
        self._succeed(['not', None, [self._get('e')]])

    def _prim_expr_c7_(self):
        self._push('prim_expr_c7')
        self._seq(
            [
                lambda: self._str('?('),
                self._sp_,
                self._prim_expr_c7_s0_,
                self._sp_,
                lambda: self._ch(')'),
                self._prim_expr_c7_s1_,
            ]
        )
        self._pop('prim_expr_c7')

    def _prim_expr_c7_s0_(self):
        self._bind(self._prim_expr_c7_s0_l_, 'e')

    def _prim_expr_c7_s0_l_(self):
        self._ll_expr_()

    def _prim_expr_c7_s1_(self):
        self._succeed(['pred', None, [self._get('e')]])

    def _prim_expr_c8_(self):
        self._push('prim_expr_c8')
        self._seq(
            [
                lambda: self._str('?{'),
                self._sp_,
                self._prim_expr_c8_s0_,
                self._sp_,
                lambda: self._ch('}'),
                self._prim_expr_c8_s1_,
            ]
        )
        self._pop('prim_expr_c8')

    def _prim_expr_c8_s0_(self):
        self._bind(self._prim_expr_c8_s0_l_, 'e')

    def _prim_expr_c8_s0_l_(self):
        self._ll_expr_()

    def _prim_expr_c8_s1_(self):
        self._succeed(['pred', None, [self._get('e')]])

    def _prim_expr_c9_(self):
        self._push('prim_expr_c9')
        self._seq(
            [
                lambda: self._ch('('),
                self._sp_,
                self._prim_expr_c9_s0_,
                self._sp_,
                lambda: self._ch(')'),
                self._prim_expr_c9_s1_,
            ]
        )
        self._pop('prim_expr_c9')

    def _prim_expr_c9_s0_(self):
        self._bind(self._prim_expr_c9_s0_l_, 'e')

    def _prim_expr_c9_s0_l_(self):
        self._choice_()

    def _prim_expr_c9_s1_(self):
        self._succeed(['paren', None, [self._get('e')]])

    def _lit_(self):
        self._choose([self._lit_c0_, self._lit_c1_])

    def _lit_c0_(self):
        self._push('lit_c0')
        self._seq(
            [self._squote_, self._lit_c0_s0_, self._squote_, self._lit_c0_s1_]
        )
        self._pop('lit_c0')

    def _lit_c0_s0_(self):
        self._bind(self._lit_c0_s0_l_, 'cs')

    def _lit_c0_s0_l_(self):
        self._star(self._sqchar_)

    def _lit_c0_s1_(self):
        self._succeed(['lit', self._cat(self._get('cs')), []])

    def _lit_c1_(self):
        self._push('lit_c1')
        self._seq(
            [self._dquote_, self._lit_c1_s0_, self._dquote_, self._lit_c1_s1_]
        )
        self._pop('lit_c1')

    def _lit_c1_s0_(self):
        self._bind(self._lit_c1_s0_l_, 'cs')

    def _lit_c1_s0_l_(self):
        self._star(self._dqchar_)

    def _lit_c1_s1_(self):
        self._succeed(['lit', self._cat(self._get('cs')), []])

    def _sqchar_(self):
        self._choose([self._sqchar_c0_, self._sqchar_c1_])

    def _sqchar_c0_(self):
        self._push('sqchar_c0')
        self._seq([self._bslash_, self._sqchar_c0_s0_, self._sqchar_c0_s1_])
        self._pop('sqchar_c0')

    def _sqchar_c0_s0_(self):
        self._bind(self._sqchar_c0_s0_l_, 'c')

    def _sqchar_c0_s0_l_(self):
        self._esc_char_()

    def _sqchar_c0_s1_(self):
        self._succeed(self._get('c'))

    def _sqchar_c1_(self):
        self._push('sqchar_c1')
        self._seq(
            [self._sqchar_c1_s0_, self._sqchar_c1_s1_, self._sqchar_c1_s2_]
        )
        self._pop('sqchar_c1')

    def _sqchar_c1_s0_(self):
        self._not(self._sqchar_c1_s0_n_)

    def _sqchar_c1_s0_n_(self):
        self._squote_()

    def _sqchar_c1_s1_(self):
        self._bind(self._sqchar_c1_s1_l_, 'c')

    def _sqchar_c1_s1_l_(self):
        self._any_()

    def _sqchar_c1_s2_(self):
        self._succeed(self._get('c'))

    def _dqchar_(self):
        self._choose([self._dqchar_c0_, self._dqchar_c1_])

    def _dqchar_c0_(self):
        self._push('dqchar_c0')
        self._seq([self._bslash_, self._dqchar_c0_s0_, self._dqchar_c0_s1_])
        self._pop('dqchar_c0')

    def _dqchar_c0_s0_(self):
        self._bind(self._dqchar_c0_s0_l_, 'c')

    def _dqchar_c0_s0_l_(self):
        self._esc_char_()

    def _dqchar_c0_s1_(self):
        self._succeed(self._get('c'))

    def _dqchar_c1_(self):
        self._push('dqchar_c1')
        self._seq(
            [self._dqchar_c1_s0_, self._dqchar_c1_s1_, self._dqchar_c1_s2_]
        )
        self._pop('dqchar_c1')

    def _dqchar_c1_s0_(self):
        self._not(self._dqchar_c1_s0_n_)

    def _dqchar_c1_s0_n_(self):
        self._dquote_()

    def _dqchar_c1_s1_(self):
        self._bind(self._dqchar_c1_s1_l_, 'c')

    def _dqchar_c1_s1_l_(self):
        self._any_()

    def _dqchar_c1_s2_(self):
        self._succeed(self._get('c'))

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
        self._seq([lambda: self._ch('b'), self._esc_char_c0_s0_])

    def _esc_char_c0_s0_(self):
        self._succeed('\b')

    def _esc_char_c1_(self):
        self._seq([lambda: self._ch('f'), self._esc_char_c1_s0_])

    def _esc_char_c1_s0_(self):
        self._succeed('\f')

    def _esc_char_c2_(self):
        self._seq([lambda: self._ch('n'), self._esc_char_c2_s0_])

    def _esc_char_c2_s0_(self):
        self._succeed('\n')

    def _esc_char_c3_(self):
        self._seq([lambda: self._ch('r'), self._esc_char_c3_s0_])

    def _esc_char_c3_s0_(self):
        self._succeed('\r')

    def _esc_char_c4_(self):
        self._seq([lambda: self._ch('t'), self._esc_char_c4_s0_])

    def _esc_char_c4_s0_(self):
        self._succeed('\t')

    def _esc_char_c5_(self):
        self._seq([lambda: self._ch('v'), self._esc_char_c5_s0_])

    def _esc_char_c5_s0_(self):
        self._succeed('\v')

    def _esc_char_c6_(self):
        self._seq([self._squote_, self._esc_char_c6_s0_])

    def _esc_char_c6_s0_(self):
        self._succeed("'")

    def _esc_char_c7_(self):
        self._seq([self._dquote_, self._esc_char_c7_s0_])

    def _esc_char_c7_s0_(self):
        self._succeed('"')

    def _esc_char_c8_(self):
        self._seq([self._bslash_, self._esc_char_c8_s0_])

    def _esc_char_c8_s0_(self):
        self._succeed('\\')

    def _esc_char_c9_(self):
        self._push('esc_char_c9')
        self._seq([self._esc_char_c9_s0_, self._esc_char_c9_s1_])
        self._pop('esc_char_c9')

    def _esc_char_c9_s0_(self):
        self._bind(self._esc_char_c9_s0_l_, 'c')

    def _esc_char_c9_s0_l_(self):
        self._hex_esc_()

    def _esc_char_c9_s1_(self):
        self._succeed(self._get('c'))

    def _esc_char_c10_(self):
        self._push('esc_char_c10')
        self._seq([self._esc_char_c10_s0_, self._esc_char_c10_s1_])
        self._pop('esc_char_c10')

    def _esc_char_c10_s0_(self):
        self._bind(self._esc_char_c10_s0_l_, 'c')

    def _esc_char_c10_s0_l_(self):
        self._unicode_esc_()

    def _esc_char_c10_s1_(self):
        self._succeed(self._get('c'))

    def _hex_esc_(self):
        self._push('hex_esc')
        self._seq(
            [
                lambda: self._ch('x'),
                self._hex_esc_s0_,
                self._hex_esc_s1_,
                self._hex_esc_s2_,
            ]
        )
        self._pop('hex_esc')

    def _hex_esc_s0_(self):
        self._bind(self._hex_esc_s0_l_, 'h1')

    def _hex_esc_s0_l_(self):
        self._hex_()

    def _hex_esc_s1_(self):
        self._bind(self._hex_esc_s1_l_, 'h2')

    def _hex_esc_s1_l_(self):
        self._hex_()

    def _hex_esc_s2_(self):
        self._succeed(self._xtou(self._get('h1') + self._get('h2')))

    def _unicode_esc_(self):
        self._choose([self._unicode_esc_c0_, self._unicode_esc_c1_])

    def _unicode_esc_c0_(self):
        self._push('unicode_esc_c0')
        self._seq(
            [
                lambda: self._ch('u'),
                self._unicode_esc_c0_s0_,
                self._unicode_esc_c0_s1_,
                self._unicode_esc_c0_s2_,
                self._unicode_esc_c0_s3_,
                self._unicode_esc_c0_s4_,
            ]
        )
        self._pop('unicode_esc_c0')

    def _unicode_esc_c0_s0_(self):
        self._bind(self._unicode_esc_c0_s0_l_, 'h1')

    def _unicode_esc_c0_s0_l_(self):
        self._hex_()

    def _unicode_esc_c0_s1_(self):
        self._bind(self._unicode_esc_c0_s1_l_, 'h2')

    def _unicode_esc_c0_s1_l_(self):
        self._hex_()

    def _unicode_esc_c0_s2_(self):
        self._bind(self._unicode_esc_c0_s2_l_, 'h3')

    def _unicode_esc_c0_s2_l_(self):
        self._hex_()

    def _unicode_esc_c0_s3_(self):
        self._bind(self._unicode_esc_c0_s3_l_, 'h4')

    def _unicode_esc_c0_s3_l_(self):
        self._hex_()

    def _unicode_esc_c0_s4_(self):
        self._succeed(
            self._xtou(
                self._get('h1')
                + self._get('h2')
                + self._get('h3')
                + self._get('h4'),
            )
        )

    def _unicode_esc_c1_(self):
        self._push('unicode_esc_c1')
        self._seq(
            [
                lambda: self._ch('U'),
                self._unicode_esc_c1_s0_,
                self._unicode_esc_c1_s1_,
                self._unicode_esc_c1_s2_,
                self._unicode_esc_c1_s3_,
                self._unicode_esc_c1_s4_,
                self._unicode_esc_c1_s5_,
                self._unicode_esc_c1_s6_,
                self._unicode_esc_c1_s7_,
                self._unicode_esc_c1_s8_,
            ]
        )
        self._pop('unicode_esc_c1')

    def _unicode_esc_c1_s0_(self):
        self._bind(self._unicode_esc_c1_s0_l_, 'h1')

    def _unicode_esc_c1_s0_l_(self):
        self._hex_()

    def _unicode_esc_c1_s1_(self):
        self._bind(self._unicode_esc_c1_s1_l_, 'h2')

    def _unicode_esc_c1_s1_l_(self):
        self._hex_()

    def _unicode_esc_c1_s2_(self):
        self._bind(self._unicode_esc_c1_s2_l_, 'h3')

    def _unicode_esc_c1_s2_l_(self):
        self._hex_()

    def _unicode_esc_c1_s3_(self):
        self._bind(self._unicode_esc_c1_s3_l_, 'h4')

    def _unicode_esc_c1_s3_l_(self):
        self._hex_()

    def _unicode_esc_c1_s4_(self):
        self._bind(self._unicode_esc_c1_s4_l_, 'h5')

    def _unicode_esc_c1_s4_l_(self):
        self._hex_()

    def _unicode_esc_c1_s5_(self):
        self._bind(self._unicode_esc_c1_s5_l_, 'h6')

    def _unicode_esc_c1_s5_l_(self):
        self._hex_()

    def _unicode_esc_c1_s6_(self):
        self._bind(self._unicode_esc_c1_s6_l_, 'h7')

    def _unicode_esc_c1_s6_l_(self):
        self._hex_()

    def _unicode_esc_c1_s7_(self):
        self._bind(self._unicode_esc_c1_s7_l_, 'h8')

    def _unicode_esc_c1_s7_l_(self):
        self._hex_()

    def _unicode_esc_c1_s8_(self):
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
        self._push('escape')
        self._seq(
            [
                lambda: self._str('\\p{'),
                self._escape_s0_,
                lambda: self._ch('}'),
                self._escape_s1_,
            ]
        )
        self._pop('escape')

    def _escape_s0_(self):
        self._bind(self._escape_s0_l_, 'i')

    def _escape_s0_l_(self):
        self._ident_()

    def _escape_s1_(self):
        self._succeed(['unicat', self._get('i'), []])

    def _ll_exprs_(self):
        self._choose([self._ll_exprs_c0_, self._ll_exprs_c1_])

    def _ll_exprs_c0_(self):
        self._push('ll_exprs_c0')
        self._seq(
            [
                self._ll_exprs_c0_s0_,
                self._ll_exprs_c0_s1_,
                self._ll_exprs_c0_s2_,
            ]
        )
        self._pop('ll_exprs_c0')

    def _ll_exprs_c0_s0_(self):
        self._bind(self._ll_exprs_c0_s0_l_, 'e')

    def _ll_exprs_c0_s0_l_(self):
        self._ll_expr_()

    def _ll_exprs_c0_s1_(self):
        self._bind(self._ll_exprs_c0_s1_l_, 'es')

    def _ll_exprs_c0_s1_l_(self):
        self._star(self._ll_exprs_c0_s1_l_p_)

    def _ll_exprs_c0_s1_l_p_(self):
        self._ll_exprs_c0_s1_l_p_g_()

    def _ll_exprs_c0_s1_l_p_g_(self):
        self._seq([self._sp_, lambda: self._ch(','), self._sp_, self._ll_expr_])

    def _ll_exprs_c0_s2_(self):
        self._succeed([self._get('e')] + self._get('es'))

    def _ll_exprs_c1_(self):
        self._succeed([])

    def _ll_expr_(self):
        self._choose(
            [
                self._ll_expr_c0_,
                self._ll_expr_c1_,
                lambda: self._seq([self._ll_qual_]),
            ]
        )

    def _ll_expr_c0_(self):
        self._push('ll_expr_c0')
        self._seq(
            [
                self._ll_expr_c0_s0_,
                self._sp_,
                lambda: self._ch('+'),
                self._sp_,
                self._ll_expr_c0_s1_,
                self._ll_expr_c0_s2_,
            ]
        )
        self._pop('ll_expr_c0')

    def _ll_expr_c0_s0_(self):
        self._bind(self._ll_expr_c0_s0_l_, 'e1')

    def _ll_expr_c0_s0_l_(self):
        self._ll_qual_()

    def _ll_expr_c0_s1_(self):
        self._bind(self._ll_expr_c0_s1_l_, 'e2')

    def _ll_expr_c0_s1_l_(self):
        self._ll_expr_()

    def _ll_expr_c0_s2_(self):
        self._succeed(['ll_plus', None, [self._get('e1'), self._get('e2')]])

    def _ll_expr_c1_(self):
        self._push('ll_expr_c1')
        self._seq(
            [
                self._ll_expr_c1_s0_,
                self._sp_,
                lambda: self._ch('-'),
                self._sp_,
                self._ll_expr_c1_s1_,
                self._ll_expr_c1_s2_,
            ]
        )
        self._pop('ll_expr_c1')

    def _ll_expr_c1_s0_(self):
        self._bind(self._ll_expr_c1_s0_l_, 'e1')

    def _ll_expr_c1_s0_l_(self):
        self._ll_qual_()

    def _ll_expr_c1_s1_(self):
        self._bind(self._ll_expr_c1_s1_l_, 'e2')

    def _ll_expr_c1_s1_l_(self):
        self._ll_expr_()

    def _ll_expr_c1_s2_(self):
        self._succeed(['ll_minus', None, [self._get('e1'), self._get('e2')]])

    def _ll_qual_(self):
        self._choose([self._ll_qual_c0_, lambda: self._seq([self._ll_prim_])])

    def _ll_qual_c0_(self):
        self._push('ll_qual_c0')
        self._seq(
            [self._ll_qual_c0_s0_, self._ll_qual_c0_s1_, self._ll_qual_c0_s2_]
        )
        self._pop('ll_qual_c0')

    def _ll_qual_c0_s0_(self):
        self._bind(self._ll_qual_c0_s0_l_, 'e')

    def _ll_qual_c0_s0_l_(self):
        self._ll_prim_()

    def _ll_qual_c0_s1_(self):
        self._bind(self._ll_qual_c0_s1_l_, 'ps')

    def _ll_qual_c0_s1_l_(self):
        self._plus(self._ll_post_op_)

    def _ll_qual_c0_s2_(self):
        self._succeed(['ll_qual', None, [self._get('e')] + self._get('ps')])

    def _ll_post_op_(self):
        self._choose([self._ll_post_op_c0_, self._ll_post_op_c1_])

    def _ll_post_op_c0_(self):
        self._push('ll_post_op_c0')
        self._seq(
            [
                lambda: self._ch('['),
                self._sp_,
                self._ll_post_op_c0_s0_,
                self._sp_,
                lambda: self._ch(']'),
                self._ll_post_op_c0_s1_,
            ]
        )
        self._pop('ll_post_op_c0')

    def _ll_post_op_c0_s0_(self):
        self._bind(self._ll_post_op_c0_s0_l_, 'e')

    def _ll_post_op_c0_s0_l_(self):
        self._ll_expr_()

    def _ll_post_op_c0_s1_(self):
        self._succeed(['ll_getitem', None, [self._get('e')]])

    def _ll_post_op_c1_(self):
        self._push('ll_post_op_c1')
        self._seq(
            [
                lambda: self._ch('('),
                self._sp_,
                self._ll_post_op_c1_s0_,
                self._sp_,
                lambda: self._ch(')'),
                self._ll_post_op_c1_s1_,
            ]
        )
        self._pop('ll_post_op_c1')

    def _ll_post_op_c1_s0_(self):
        self._bind(self._ll_post_op_c1_s0_l_, 'es')

    def _ll_post_op_c1_s0_l_(self):
        self._ll_exprs_()

    def _ll_post_op_c1_s1_(self):
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
        self._seq([lambda: self._str('false'), self._ll_prim_c0_s0_])

    def _ll_prim_c0_s0_(self):
        self._succeed(['ll_const', 'false', []])

    def _ll_prim_c1_(self):
        self._seq([lambda: self._str('null'), self._ll_prim_c1_s0_])

    def _ll_prim_c1_s0_(self):
        self._succeed(['ll_const', 'null', []])

    def _ll_prim_c2_(self):
        self._seq([lambda: self._str('true'), self._ll_prim_c2_s0_])

    def _ll_prim_c2_s0_(self):
        self._succeed(['ll_const', 'true', []])

    def _ll_prim_c3_(self):
        self._seq([lambda: self._str('Infinity'), self._ll_prim_c3_s0_])

    def _ll_prim_c3_s0_(self):
        self._succeed(['ll_const', 'Infinity', []])

    def _ll_prim_c4_(self):
        self._seq([lambda: self._str('NaN'), self._ll_prim_c4_s0_])

    def _ll_prim_c4_s0_(self):
        self._succeed(['ll_const', 'NaN', []])

    def _ll_prim_c5_(self):
        self._push('ll_prim_c5')
        self._seq([self._ll_prim_c5_s0_, self._ll_prim_c5_s1_])
        self._pop('ll_prim_c5')

    def _ll_prim_c5_s0_(self):
        self._bind(self._ll_prim_c5_s0_l_, 'i')

    def _ll_prim_c5_s0_l_(self):
        self._ident_()

    def _ll_prim_c5_s1_(self):
        self._succeed(['ll_var', self._get('i'), []])

    def _ll_prim_c6_(self):
        self._push('ll_prim_c6')
        self._seq(
            [
                lambda: self._str('0x'),
                self._ll_prim_c6_s0_,
                self._ll_prim_c6_s1_,
            ]
        )
        self._pop('ll_prim_c6')

    def _ll_prim_c6_s0_(self):
        self._bind(self._ll_prim_c6_s0_l_, 'hs')

    def _ll_prim_c6_s0_l_(self):
        self._hexdigits_()

    def _ll_prim_c6_s1_(self):
        self._succeed(['ll_num', '0x' + self._get('hs'), []])

    def _ll_prim_c7_(self):
        self._push('ll_prim_c7')
        self._seq([self._ll_prim_c7_s0_, self._ll_prim_c7_s1_])
        self._pop('ll_prim_c7')

    def _ll_prim_c7_s0_(self):
        self._bind(self._ll_prim_c7_s0_l_, 'ds')

    def _ll_prim_c7_s0_l_(self):
        self._digits_()

    def _ll_prim_c7_s1_(self):
        self._succeed(['ll_num', self._get('ds'), []])

    def _ll_prim_c8_(self):
        self._push('ll_prim_c8')
        self._seq([self._ll_prim_c8_s0_, self._ll_prim_c8_s1_])
        self._pop('ll_prim_c8')

    def _ll_prim_c8_s0_(self):
        self._bind(self._ll_prim_c8_s0_l_, 'l')

    def _ll_prim_c8_s0_l_(self):
        self._lit_()

    def _ll_prim_c8_s1_(self):
        self._succeed(['ll_lit', self._get('l')[1], []])

    def _ll_prim_c9_(self):
        self._push('ll_prim_c9')
        self._seq(
            [
                lambda: self._ch('('),
                self._sp_,
                self._ll_prim_c9_s0_,
                self._sp_,
                lambda: self._ch(')'),
                self._ll_prim_c9_s1_,
            ]
        )
        self._pop('ll_prim_c9')

    def _ll_prim_c9_s0_(self):
        self._bind(self._ll_prim_c9_s0_l_, 'e')

    def _ll_prim_c9_s0_l_(self):
        self._ll_expr_()

    def _ll_prim_c9_s1_(self):
        self._succeed(['ll_paren', None, [self._get('e')]])

    def _ll_prim_c10_(self):
        self._push('ll_prim_c10')
        self._seq(
            [
                lambda: self._ch('['),
                self._sp_,
                self._ll_prim_c10_s0_,
                self._sp_,
                lambda: self._ch(']'),
                self._ll_prim_c10_s1_,
            ]
        )
        self._pop('ll_prim_c10')

    def _ll_prim_c10_s0_(self):
        self._bind(self._ll_prim_c10_s0_l_, 'es')

    def _ll_prim_c10_s0_l_(self):
        self._ll_exprs_()

    def _ll_prim_c10_s1_(self):
        self._succeed(['ll_arr', None, self._get('es')])

    def _digits_(self):
        self._push('digits')
        self._seq([self._digits_s0_, self._digits_s1_])
        self._pop('digits')

    def _digits_s0_(self):
        self._bind(self._digits_s0_l_, 'ds')

    def _digits_s0_l_(self):
        self._plus(self._digit_)

    def _digits_s1_(self):
        self._succeed(self._cat(self._get('ds')))

    def _hexdigits_(self):
        self._push('hexdigits')
        self._seq([self._hexdigits_s0_, self._hexdigits_s1_])
        self._pop('hexdigits')

    def _hexdigits_s0_(self):
        self._bind(self._hexdigits_s0_l_, 'hs')

    def _hexdigits_s0_l_(self):
        self._plus(self._hex_)

    def _hexdigits_s1_(self):
        self._succeed(self._cat(self._get('hs')))

    def _hex_(self):
        self._choose(
            [lambda: self._seq([self._digit_]), self._hex_c0_, self._hex_c1_]
        )

    def _hex_c0_(self):
        self._range('a', 'f')

    def _hex_c1_(self):
        self._range('A', 'F')

    def _digit_(self):
        self._range('0', '9')

    def _any_(self):
        if self.pos < self.end:
            self._succeed(self.msg[self.pos], self.pos + 1)
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
        if p < self.end and self.msg[p] == ch:
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
            if self.msg[i] == '\n':
                lineno += 1
                colno = 1
            else:
                colno += 1
        return lineno, colno

    def _err_str(self):
        lineno, colno = self._err_offsets()
        if self.errpos == len(self.msg):
            thing = 'end of input'
        else:
            thing = '"%s"' % self.msg[self.errpos]
        return '%s:%d Unexpected %s at column %d' % (
            self.fname,
            lineno,
            thing,
            colno,
        )

    def _fail(self):
        self.val = None
        self.failed = True
        self.errpos = max(self.errpos, self.pos)

    def _get(self, var):
        return self.scopes[-1][1][var]

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

    def _pop(self, name):
        actual_name, _ = self.scopes.pop()
        assert name == actual_name

    def _push(self, name):
        self.scopes.append((name, {}))

    def _range(self, i, j):
        p = self.pos
        if p != self.end and ord(i) <= ord(self.msg[p]) <= ord(j):
            self._succeed(self.msg[p], self.pos + 1)
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
        self.scopes[-1][1][var] = val

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
