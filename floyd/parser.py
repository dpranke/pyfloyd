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

    def parse(self):
        self._r_grammar_()
        if self.failed:
            return Result(None, self._err_str(), self.errpos)
        return Result(self.val, None, self.pos)

    def _r_grammar_(self):
        self._s_grammar_1_()
        if not self.failed:
            v_vs = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_end_()
        if not self.failed:
            self._succeed(['rules', None, v_vs])

    def _s_grammar_1_(self):
        vs = []
        while True:
            p = self.pos
            self._s_grammar_2_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_grammar_2_(self):
        self._r_sp_()
        if not self.failed:
            self._s_grammar_3_()

    def _s_grammar_3_(self):
        p = self.pos
        self._r_pragma_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_rule_()

    def _r_sp_(self):
        vs = []
        while True:
            p = self.pos
            self._r_ws_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_ws_(self):
        p = self.pos
        self._ch(' ')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('\t')
        if not self.failed:
            return
        self._rewind(p)
        self._r_eol_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_comment_()

    def _r_eol_(self):
        p = self.pos
        self._s_eol_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._ch('\r')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('\n')

    def _s_eol_1_(self):
        self._ch('\r')
        if not self.failed:
            self._ch('\n')

    def _r_comment_(self):
        p = self.pos
        self._s_comment_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_comment_5_()

    def _s_comment_1_(self):
        self._str('//')
        if not self.failed:
            self._s_comment_2_()

    def _s_comment_2_(self):
        vs = []
        while True:
            p = self.pos
            self._s_comment_3_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_comment_3_(self):
        self._s_comment_4_()
        if not self.failed:
            self._r_any_()

    def _s_comment_4_(self):
        p = self.pos
        errpos = self.errpos
        self._r_eol_()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _s_comment_5_(self):
        self._str('/*')
        if not self.failed:
            self._s_comment_6_()
        if not self.failed:
            self._str('*/')

    def _s_comment_6_(self):
        vs = []
        while True:
            p = self.pos
            self._s_comment_7_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_comment_7_(self):
        self._s_comment_8_()
        if not self.failed:
            self._r_any_()

    def _s_comment_8_(self):
        p = self.pos
        errpos = self.errpos
        self._str('*/')
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _r_pragma_(self):
        p = self.pos
        self._s_pragma_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_pragma_2_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_pragma_3_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_pragma_4_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_pragma_5_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_pragma_7_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_pragma_8_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_pragma_10_()

    def _s_pragma_1_(self):
        self._str('%tokens')
        if not self.failed:
            self._r_ident_list_()
            if not self.failed:
                v_is = self.val
        if not self.failed:
            self._succeed(['pragma', 'tokens', v_is])

    def _s_pragma_2_(self):
        self._str('%token')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ident_()
            if not self.failed:
                v_i = self.val
        if not self.failed:
            self._succeed(['pragma', 'token', [v_i]])

    def _s_pragma_3_(self):
        self._str('%whitespace_style')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ident_()
            if not self.failed:
                v_i = self.val
        if not self.failed:
            self._succeed(['pragma', 'whitespace_style', v_i])

    def _s_pragma_4_(self):
        self._str('%whitespace')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch('=')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_choice_()
            if not self.failed:
                v_cs = self.val
        if not self.failed:
            self._succeed(['pragma', 'whitespace', [v_cs]])

    def _s_pragma_5_(self):
        self._str('%comment_style')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._s_pragma_6_()
            if not self.failed:
                v_c = self.val
        if not self.failed:
            self._succeed(['pragma', 'comment_style', v_c])

    def _s_pragma_6_(self):
        p = self.pos
        self._str('C++')
        if not self.failed:
            return
        self._rewind(p)
        self._r_ident_()

    def _s_pragma_7_(self):
        self._str('%comment')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch('=')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_choice_()
            if not self.failed:
                v_cs = self.val
        if not self.failed:
            self._succeed(['pragma', 'comment', [v_cs]])

    def _s_pragma_8_(self):
        self._str('%assoc')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._s_pragma_9_()
            if not self.failed:
                v_a = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_dir_()
            if not self.failed:
                v_d = self.val
        if not self.failed:
            self._succeed(['pragma', 'assoc', [v_a, v_d]])

    def _s_pragma_9_(self):
        p = self.pos
        self._r_op_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_arm_()

    def _s_pragma_10_(self):
        self._str('%prec')
        if not self.failed:
            self._s_pragma_11_()
            if not self.failed:
                v_os = self.val
        if not self.failed:
            self._succeed(['pragma', 'prec', v_os])

    def _s_pragma_11_(self):
        vs = []
        self._s_pragma_12_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._s_pragma_12_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_pragma_12_(self):
        self._s_pragma_13_()
        if not self.failed:
            self._r_ws_()
        if not self.failed:
            self._r_op_()
            if not self.failed:
                v_o = self.val
        if not self.failed:
            self._succeed(v_o)

    def _s_pragma_13_(self):
        p = self.pos
        errpos = self.errpos
        self._r_eol_()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _r_op_(self):
        self._s_op_1_()
        if not self.failed:
            v_op = self.val
        if not self.failed:
            self._succeed(_join('', v_op))

    def _s_op_1_(self):
        vs = []
        self._s_op_2_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._s_op_2_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_op_2_(self):
        self._s_op_3_()
        if not self.failed:
            self._r_any_()

    def _s_op_3_(self):
        p = self.pos
        errpos = self.errpos
        self._s_op_4_()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _s_op_4_(self):
        p = self.pos
        self._r_ws_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_id_continue_()

    def _r_arm_(self):
        self._r_ident_()
        if not self.failed:
            v_i = self.val
        if not self.failed:
            self._ch('#')
        if not self.failed:
            self._r_digits_()
            if not self.failed:
                v_ds = self.val
        if not self.failed:
            self._succeed(v_i + '#' + _join('', v_ds))

    def _r_dir_(self):
        self._s_dir_1_()
        if not self.failed:
            v_d = self.val
        if not self.failed:
            self._succeed(v_d)

    def _s_dir_1_(self):
        p = self.pos
        self._str('left')
        if not self.failed:
            return
        self._rewind(p)
        self._str('right')

    def _r_ident_list_(self):
        self._s_ident_list_1_()
        if not self.failed:
            v_is = self.val
        if not self.failed:
            self._succeed(v_is)

    def _s_ident_list_1_(self):
        vs = []
        self._s_ident_list_2_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._s_ident_list_2_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_ident_list_2_(self):
        self._r_sp_()
        if not self.failed:
            self._r_ident_()
            if not self.failed:
                v_i = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._s_ident_list_3_()
        if not self.failed:
            self._succeed(v_i)

    def _s_ident_list_3_(self):
        p = self.pos
        errpos = self.errpos
        self._ch('=')
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _r_rule_(self):
        self._r_ident_()
        if not self.failed:
            v_i = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch('=')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_choice_()
            if not self.failed:
                v_cs = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._s_rule_1_()
        if not self.failed:
            self._succeed(['rule', v_i, [v_cs]])

    def _s_rule_1_(self):
        p = self.pos
        self._ch(',')
        if self.failed:
            self._succeed([], p)
        else:
            self._succeed([self.val])

    def _r_ident_(self):
        self._r_id_start_()
        if not self.failed:
            v_hd = self.val
        if not self.failed:
            self._s_ident_1_()
            if not self.failed:
                v_tl = self.val
        if not self.failed:
            self._succeed(_strcat(v_hd, _join('', v_tl)))

    def _s_ident_1_(self):
        vs = []
        while True:
            p = self.pos
            self._r_id_continue_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_id_start_(self):
        p = self.pos
        self._range('a', 'z')
        if not self.failed:
            return
        self._rewind(p)
        self._range('A', 'Z')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('_')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('$')

    def _r_id_continue_(self):
        p = self.pos
        self._r_id_start_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_digit_()

    def _r_choice_(self):
        self._r_seq_()
        if not self.failed:
            v_s = self.val
        if not self.failed:
            self._s_choice_1_()
            if not self.failed:
                v_ss = self.val
        if not self.failed:
            self._succeed(['choice', None, [v_s] + v_ss])

    def _s_choice_1_(self):
        vs = []
        while True:
            p = self.pos
            self._s_choice_2_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_choice_2_(self):
        self._r_sp_()
        if not self.failed:
            self._ch('|')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_seq_()

    def _r_seq_(self):
        p = self.pos
        self._s_seq_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._succeed(['empty', None, []])

    def _s_seq_1_(self):
        self._r_expr_()
        if not self.failed:
            v_e = self.val
        if not self.failed:
            self._s_seq_2_()
            if not self.failed:
                v_es = self.val
        if not self.failed:
            self._succeed(['seq', None, [v_e] + v_es])

    def _s_seq_2_(self):
        vs = []
        while True:
            p = self.pos
            self._s_seq_3_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_seq_3_(self):
        self._r_ws_()
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_expr_()

    def _r_expr_(self):
        p = self.pos
        self._s_expr_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_post_expr_()

    def _s_expr_1_(self):
        self._r_post_expr_()
        if not self.failed:
            v_e = self.val
        if not self.failed:
            self._ch(':')
        if not self.failed:
            self._r_ident_()
            if not self.failed:
                v_l = self.val
        if not self.failed:
            self._succeed(['label', v_l, [v_e]])

    def _r_post_expr_(self):
        p = self.pos
        self._s_post_expr_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_prim_expr_()

    def _s_post_expr_1_(self):
        self._r_prim_expr_()
        if not self.failed:
            v_e = self.val
        if not self.failed:
            self._r_post_op_()
            if not self.failed:
                v_op = self.val
        if not self.failed:
            self._succeed(['post', v_op, [v_e]])

    def _r_post_op_(self):
        p = self.pos
        self._ch('?')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('*')
        if not self.failed:
            return
        self._rewind(p)
        self._ch('+')

    def _r_prim_expr_(self):
        p = self.pos
        self._s_prim_expr_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_2_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_3_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_4_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_7_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_8_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_9_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_10_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_11_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_prim_expr_12_()

    def _s_prim_expr_1_(self):
        self._r_lit_()
        if not self.failed:
            v_i = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._str('..')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_lit_()
            if not self.failed:
                v_j = self.val
        if not self.failed:
            self._succeed(['range', None, [v_i, v_j]])

    def _s_prim_expr_2_(self):
        self._r_lit_()
        if not self.failed:
            v_l = self.val
        if not self.failed:
            self._succeed(v_l)

    def _s_prim_expr_3_(self):
        self._r_escape_()
        if not self.failed:
            v_e = self.val
        if not self.failed:
            self._succeed(v_e)

    def _s_prim_expr_4_(self):
        self._r_ident_()
        if not self.failed:
            v_i = self.val
        if not self.failed:
            self._s_prim_expr_5_()
        if not self.failed:
            self._succeed(['apply', v_i, []])

    def _s_prim_expr_5_(self):
        p = self.pos
        errpos = self.errpos
        self._s_prim_expr_6_()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _s_prim_expr_6_(self):
        self._r_sp_()
        if not self.failed:
            self._ch('=')

    def _s_prim_expr_7_(self):
        self._str('->')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v_e = self.val
        if not self.failed:
            self._succeed(['action', None, [v_e]])

    def _s_prim_expr_8_(self):
        self._ch('{')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v_e = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed(['action', None, [v_e]])

    def _s_prim_expr_9_(self):
        self._ch('~')
        if not self.failed:
            self._r_prim_expr_()
            if not self.failed:
                v_e = self.val
        if not self.failed:
            self._succeed(['not', None, [v_e]])

    def _s_prim_expr_10_(self):
        self._str('?(')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v_e = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch(')')
        if not self.failed:
            self._succeed(['pred', None, [v_e]])

    def _s_prim_expr_11_(self):
        self._str('?{')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v_e = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed(['pred', None, [v_e]])

    def _s_prim_expr_12_(self):
        self._ch('(')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_choice_()
            if not self.failed:
                v_e = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch(')')
        if not self.failed:
            self._succeed(['paren', None, [v_e]])

    def _r_lit_(self):
        p = self.pos
        self._s_lit_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_lit_3_()

    def _s_lit_1_(self):
        self._r_squote_()
        if not self.failed:
            self._s_lit_2_()
            if not self.failed:
                v_cs = self.val
        if not self.failed:
            self._r_squote_()
        if not self.failed:
            self._succeed(['lit', _join('', v_cs), []])

    def _s_lit_2_(self):
        vs = []
        while True:
            p = self.pos
            self._r_sqchar_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_lit_3_(self):
        self._r_dquote_()
        if not self.failed:
            self._s_lit_4_()
            if not self.failed:
                v_cs = self.val
        if not self.failed:
            self._r_dquote_()
        if not self.failed:
            self._succeed(['lit', _join('', v_cs), []])

    def _s_lit_4_(self):
        vs = []
        while True:
            p = self.pos
            self._r_dqchar_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_sqchar_(self):
        p = self.pos
        self._s_sqchar_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_sqchar_2_()

    def _s_sqchar_1_(self):
        self._r_bslash_()
        if not self.failed:
            self._r_esc_char_()
            if not self.failed:
                v_c = self.val
        if not self.failed:
            self._succeed(v_c)

    def _s_sqchar_2_(self):
        self._s_sqchar_3_()
        if not self.failed:
            self._r_any_()
            if not self.failed:
                v_c = self.val
        if not self.failed:
            self._succeed(v_c)

    def _s_sqchar_3_(self):
        p = self.pos
        errpos = self.errpos
        self._r_squote_()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _r_dqchar_(self):
        p = self.pos
        self._s_dqchar_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_dqchar_2_()

    def _s_dqchar_1_(self):
        self._r_bslash_()
        if not self.failed:
            self._r_esc_char_()
            if not self.failed:
                v_c = self.val
        if not self.failed:
            self._succeed(v_c)

    def _s_dqchar_2_(self):
        self._s_dqchar_3_()
        if not self.failed:
            self._r_any_()
            if not self.failed:
                v_c = self.val
        if not self.failed:
            self._succeed(v_c)

    def _s_dqchar_3_(self):
        p = self.pos
        errpos = self.errpos
        self._r_dquote_()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()

    def _r_bslash_(self):
        self._ch('\\')

    def _r_squote_(self):
        self._ch("'")

    def _r_dquote_(self):
        self._ch('"')

    def _r_esc_char_(self):
        p = self.pos
        self._s_esc_char_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_esc_char_2_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_esc_char_3_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_esc_char_4_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_esc_char_5_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_esc_char_6_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_esc_char_7_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_esc_char_8_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_esc_char_9_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_esc_char_10_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_esc_char_11_()

    def _s_esc_char_1_(self):
        self._ch('b')
        if not self.failed:
            self._succeed('\b')

    def _s_esc_char_2_(self):
        self._ch('f')
        if not self.failed:
            self._succeed('\f')

    def _s_esc_char_3_(self):
        self._ch('n')
        if not self.failed:
            self._succeed('\n')

    def _s_esc_char_4_(self):
        self._ch('r')
        if not self.failed:
            self._succeed('\r')

    def _s_esc_char_5_(self):
        self._ch('t')
        if not self.failed:
            self._succeed('\t')

    def _s_esc_char_6_(self):
        self._ch('v')
        if not self.failed:
            self._succeed('\v')

    def _s_esc_char_7_(self):
        self._r_squote_()
        if not self.failed:
            self._succeed("'")

    def _s_esc_char_8_(self):
        self._r_dquote_()
        if not self.failed:
            self._succeed('"')

    def _s_esc_char_9_(self):
        self._r_bslash_()
        if not self.failed:
            self._succeed('\\')

    def _s_esc_char_10_(self):
        self._r_hex_esc_()
        if not self.failed:
            v_c = self.val
        if not self.failed:
            self._succeed(v_c)

    def _s_esc_char_11_(self):
        self._r_unicode_esc_()
        if not self.failed:
            v_c = self.val
        if not self.failed:
            self._succeed(v_c)

    def _r_hex_esc_(self):
        self._ch('x')
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h1 = self.val
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h2 = self.val
        if not self.failed:
            self._succeed(_xtou(v_h1 + v_h2))

    def _r_unicode_esc_(self):
        p = self.pos
        self._s_unicode_esc_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_unicode_esc_2_()

    def _s_unicode_esc_1_(self):
        self._ch('u')
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h1 = self.val
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h2 = self.val
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h3 = self.val
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h4 = self.val
        if not self.failed:
            self._succeed(_xtou(v_h1 + v_h2 + v_h3 + v_h4))

    def _s_unicode_esc_2_(self):
        self._ch('U')
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h1 = self.val
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h2 = self.val
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h3 = self.val
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h4 = self.val
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h5 = self.val
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h6 = self.val
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h7 = self.val
        if not self.failed:
            self._r_hex_()
            if not self.failed:
                v_h8 = self.val
        if not self.failed:
            self._succeed(
                _xtou(v_h1 + v_h2 + v_h3 + v_h4 + v_h5 + v_h6 + v_h7 + v_h8)
            )

    def _r_escape_(self):
        self._str('\\p{')
        if not self.failed:
            self._r_ident_()
            if not self.failed:
                v_i = self.val
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed(['unicat', v_i, []])

    def _r_ll_exprs_(self):
        p = self.pos
        self._s_ll_exprs_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._succeed([])

    def _s_ll_exprs_1_(self):
        self._r_ll_expr_()
        if not self.failed:
            v_e = self.val
        if not self.failed:
            self._s_ll_exprs_2_()
            if not self.failed:
                v_es = self.val
        if not self.failed:
            self._succeed([v_e] + v_es)

    def _s_ll_exprs_2_(self):
        vs = []
        while True:
            p = self.pos
            self._s_ll_exprs_3_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_ll_exprs_3_(self):
        self._r_sp_()
        if not self.failed:
            self._ch(',')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ll_expr_()

    def _r_ll_expr_(self):
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

    def _s_ll_expr_1_(self):
        self._r_ll_qual_()
        if not self.failed:
            v_e1 = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch('+')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v_e2 = self.val
        if not self.failed:
            self._succeed(['ll_plus', None, [v_e1, v_e2]])

    def _s_ll_expr_2_(self):
        self._r_ll_qual_()
        if not self.failed:
            v_e1 = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch('-')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v_e2 = self.val
        if not self.failed:
            self._succeed(['ll_minus', None, [v_e1, v_e2]])

    def _r_ll_qual_(self):
        p = self.pos
        self._s_ll_qual_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_ll_prim_()

    def _s_ll_qual_1_(self):
        self._r_ll_prim_()
        if not self.failed:
            v_e = self.val
        if not self.failed:
            self._s_ll_qual_2_()
            if not self.failed:
                v_ps = self.val
        if not self.failed:
            self._succeed(['ll_qual', None, [v_e] + v_ps])

    def _s_ll_qual_2_(self):
        vs = []
        self._r_ll_post_op_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_ll_post_op_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_ll_post_op_(self):
        p = self.pos
        self._s_ll_post_op_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_post_op_2_()

    def _s_ll_post_op_1_(self):
        self._ch('[')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v_e = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch(']')
        if not self.failed:
            self._succeed(['ll_getitem', None, [v_e]])

    def _s_ll_post_op_2_(self):
        self._ch('(')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ll_exprs_()
            if not self.failed:
                v_es = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch(')')
        if not self.failed:
            self._succeed(['ll_call', None, v_es])

    def _r_ll_prim_(self):
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
        self._s_ll_prim_5_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_6_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_7_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_8_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_9_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_10_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_prim_11_()

    def _s_ll_prim_1_(self):
        self._str('false')
        if not self.failed:
            self._succeed(['ll_const', 'false', []])

    def _s_ll_prim_2_(self):
        self._str('null')
        if not self.failed:
            self._succeed(['ll_const', 'null', []])

    def _s_ll_prim_3_(self):
        self._str('true')
        if not self.failed:
            self._succeed(['ll_const', 'true', []])

    def _s_ll_prim_4_(self):
        self._str('Infinity')
        if not self.failed:
            self._succeed(['ll_const', 'Infinity', []])

    def _s_ll_prim_5_(self):
        self._str('NaN')
        if not self.failed:
            self._succeed(['ll_const', 'NaN', []])

    def _s_ll_prim_6_(self):
        self._r_ident_()
        if not self.failed:
            v_i = self.val
        if not self.failed:
            self._succeed(['ll_var', v_i, []])

    def _s_ll_prim_7_(self):
        self._str('0x')
        if not self.failed:
            self._r_hexdigits_()
            if not self.failed:
                v_hs = self.val
        if not self.failed:
            self._succeed(['ll_num', '0x' + v_hs, []])

    def _s_ll_prim_8_(self):
        self._r_digits_()
        if not self.failed:
            v_ds = self.val
        if not self.failed:
            self._succeed(['ll_num', v_ds, []])

    def _s_ll_prim_9_(self):
        self._r_lit_()
        if not self.failed:
            v_l = self.val
        if not self.failed:
            self._succeed(['ll_lit', v_l[1], []])

    def _s_ll_prim_10_(self):
        self._ch('(')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v_e = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch(')')
        if not self.failed:
            self._succeed(['ll_paren', None, [v_e]])

    def _s_ll_prim_11_(self):
        self._ch('[')
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._r_ll_exprs_()
            if not self.failed:
                v_es = self.val
        if not self.failed:
            self._r_sp_()
        if not self.failed:
            self._ch(']')
        if not self.failed:
            self._succeed(['ll_arr', None, v_es])

    def _r_digits_(self):
        self._s_digits_1_()
        if not self.failed:
            v_ds = self.val
        if not self.failed:
            self._succeed(_join('', v_ds))

    def _s_digits_1_(self):
        vs = []
        self._r_digit_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_digit_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_hexdigits_(self):
        self._s_hexdigits_1_()
        if not self.failed:
            v_hs = self.val
        if not self.failed:
            self._succeed(_join('', v_hs))

    def _s_hexdigits_1_(self):
        vs = []
        self._r_hex_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_hex_()
            if self.failed:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_hex_(self):
        p = self.pos
        self._r_digit_()
        if not self.failed:
            return
        self._rewind(p)
        self._range('a', 'f')
        if not self.failed:
            return
        self._rewind(p)
        self._range('A', 'F')

    def _r_digit_(self):
        self._range('0', '9')

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

    def _range(self, i, j):
        p = self.pos
        if p != self.end and ord(i) <= ord(self.text[p]) <= ord(j):
            self._succeed(self.text[p], self.pos + 1)
        else:
            self._fail()

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


def _join(s, vs):
    return s.join(vs)


def _strcat(a, b):
    return a + b


def _xtou(s):
    return chr(int(s, base=16))
