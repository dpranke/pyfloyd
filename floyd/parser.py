#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys
from typing import Any, NamedTuple, Optional

import re

# pylint: disable=too-many-lines


def main(
    argv=sys.argv[1:],
    stdin=sys.stdin,
    stdout=sys.stdout,
    stderr=sys.stderr,
    exists=os.path.exists,
    opener=open,
) -> int:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('file', nargs='?')
    args = arg_parser.parse_args(argv)

    if not args.file or args.file[1] == '-':
        path = '<stdin>'
        fp = stdin
    elif not exists(args.file):
        print('Error: file "%s" not found.' % args.file, file=stderr)
        return 1
    else:
        path = args.file
        fp = opener(path)

    msg = fp.read()
    result = parse(msg, path)
    if result.err:
        print(result.err, file=stderr)
        return 1
    print(json.dumps(result.val, indent=2), file=stdout)
    return 0


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
        self.seeds = {}
        self.blocked = set()
        self.regexps = {}

    def parse(self):
        self._r_grammar_()
        if self.failed:
            return Result(None, self._err_str(), self.errpos)
        return Result(self.val, None, self.pos)

    def _r_grammar_(self):
        self._s_grammar_1_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._r_end_()
        if not self.failed:
            self._succeed(['rules', None, v__1])

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

    def _s_rule_1_(self):
        self._r__filler_()
        if not self.failed:
            self._r_ident_()

    def _r_ident_(self):
        self._r_id_start_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_ident_1_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_cat(_scons(v__1, v__2)))

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
        if self.pos == self.end:
            self._fail()
        p = re.compile('[' + 'a-zA-Z$_%' + ']')
        m = p.match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_id_continue_(self):
        p = self.pos
        self._r_id_start_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_id_continue_1_()

    def _s_id_continue_1_(self):
        if self.pos == self.end:
            self._fail()
        p = re.compile('[' + '0-9' + ']')
        m = p.match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_choice_(self):
        self._r_seq_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_choice_1_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(['choice', None, _cons(v__1, v__2)])

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
        p = self.pos
        self._s_seq_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._succeed(['empty', None, []])

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
            self._ch('{')
        if not self.failed:
            self._r_ll_expr_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch('}')
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
            self._r__filler_()
        if not self.failed:
            self._ch(':')
        if not self.failed:
            self._s_expr_5_()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._succeed(['label', v__3, [v__3]])

    def _s_expr_5_(self):
        self._r__filler_()
        if not self.failed:
            self._r_ident_()

    def _r_post_expr_(self):
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
        p = self.pos
        self._s_count_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_count_4_()

    def _s_count_1_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('{')
        if not self.failed:
            self._s_count_2_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._s_count_3_()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._r_zpos_()
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch('}')
        if not self.failed:
            self._succeed([v__2, v__3])

    def _s_count_2_(self):
        self._r__filler_()
        if not self.failed:
            self._r_zpos_()

    def _s_count_3_(self):
        self._r__filler_()
        if not self.failed:
            self._ch(',')

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
            self._succeed(['range', None, [v__1, v__3]])

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
        self._r__filler_()
        if not self.failed:
            self._ch('[')
        if not self.failed:
            self._s_prim_expr_9_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch(']')
        if not self.failed:
            self._succeed(['set', v__2, []])

    def _s_prim_expr_9_(self):
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

    def _s_prim_expr_10_(self):
        self._r__filler_()
        if not self.failed:
            self._str('[^')
        if not self.failed:
            self._s_prim_expr_11_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r__filler_()
        if not self.failed:
            self._ch(']')
        if not self.failed:
            self._succeed(['excludes', _cat(v__2), []])

    def _s_prim_expr_11_(self):
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

    def _r_dqchar_(self):
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

    def _r_bslash_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('\\')

    def _r_squote_(self):
        self._ch("'")

    def _r_dquote_(self):
        self._ch('"')

    def _r_escape_(self):
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
        p = self.pos
        self._s_hex_esc_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_hex_esc_3_()

    def _s_hex_esc_1_(self):
        self._str('\\x')
        if not self.failed:
            self._s_hex_esc_2_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_itou(_scat(v__2)))

    def _s_hex_esc_2_(self):
        vs = []
        i = 0
        cmin, cmax = [2, 2]
        while i < cmax:
            self._r_hex_()
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
            self._succeed(_itou(_scat(v__2)))

    def _s_hex_esc_4_(self):
        vs = []
        self._r_hex_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_hex_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _r_uni_esc_(self):
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

    def _s_uni_esc_1_(self):
        self._str('\\u')
        if not self.failed:
            self._s_uni_esc_2_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_itou(_atoi(_scons('0x', v__2))))

    def _s_uni_esc_2_(self):
        vs = []
        i = 0
        cmin, cmax = [4, 4]
        while i < cmax:
            self._r_hex_()
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
            self._succeed(_itou(_atoi(_scons('0x', v__2))))

    def _s_uni_esc_4_(self):
        vs = []
        self._r_hex_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._r_hex_()
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
            self._succeed(_itou(_atoi(_scons('0x', v__2))))

    def _s_uni_esc_6_(self):
        vs = []
        i = 0
        cmin, cmax = [8, 8]
        while i < cmax:
            self._r_hex_()
            if self.failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self.val)
            i += 1
        self._succeed(vs)

    def _r_set_char_(self):
        p = self.pos
        self._s_set_char_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_set_char_2_()
        if not self.failed:
            return
        self._rewind(p)
        p = self.pos
        errpos = self.errpos
        self._s_set_char_3_()
        if self.failed:
            self._succeed(None, p)
        else:
            self._rewind(p)
            self.errpos = errpos
            self._fail()
        if not self.failed:
            self._r_any_()

    def _s_set_char_1_(self):
        self._r__filler_()
        if not self.failed:
            self._r_escape_()

    def _s_set_char_2_(self):
        self._r__filler_()
        if not self.failed:
            self._str('\\]')
        if not self.failed:
            self._succeed(']')

    def _s_set_char_3_(self):
        self._r__filler_()
        if not self.failed:
            self._ch(']')

    def _r_zpos_(self):
        p = self.pos
        self._s_zpos_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_zpos_2_()

    def _s_zpos_1_(self):
        vs = []
        i = 0
        cmin, cmax = [0, 0]
        while i < cmax:
            self._ch('0')
            if self.failed:
                if i >= cmin:
                    self._succeed(vs)
                    return
                return
            vs.append(self.val)
            i += 1
        self._succeed(vs)

    def _s_zpos_2_(self):
        self._s_zpos_3_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_zpos_4_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_atoi(_scons(v__1, v__2)))

    def _s_zpos_3_(self):
        if self.pos == self.end:
            self._fail()
        p = re.compile('[' + '1-9' + ']')
        m = p.match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _s_zpos_4_(self):
        vs = []
        while True:
            p = self.pos
            self._s_zpos_5_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_zpos_5_(self):
        if self.pos == self.end:
            self._fail()
        p = re.compile('[' + '0-9' + ']')
        m = p.match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_ll_expr_(self):
        p = self.pos
        self._leftrec(self._s_ll_expr_1_, 'll_expr#1', True)
        if not self.failed:
            return
        self._rewind(p)
        self._leftrec(self._s_ll_expr_3_, 'll_expr#2', True)
        if not self.failed:
            return
        self._rewind(p)
        self._r_ll_qual_()

    def _s_ll_expr_1_(self):
        self._r_ll_qual_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_ll_expr_2_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r_ll_expr_()
        if not self.failed:
            self._succeed(['ll_plus', None, [v__1, v__2]])

    def _s_ll_expr_2_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('+')

    def _s_ll_expr_3_(self):
        self._r_ll_qual_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_ll_expr_4_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._r_ll_expr_()
        if not self.failed:
            self._succeed(['ll_minus', None, [v__1, v__2]])

    def _s_ll_expr_4_(self):
        self._r__filler_()
        if not self.failed:
            self._ch('-')

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
        p = self.pos
        self._s_ll_qual_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._r_ll_prim_()

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
        p = self.pos
        self._s_ll_post_op_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s_ll_post_op_2_()

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
        p = self.pos
        self._ch('0')
        if not self.failed:
            return
        self._rewind(p)
        self._s_int_1_()

    def _s_int_1_(self):
        self._s_int_2_()
        if not self.failed:
            v__1 = self.val
        if not self.failed:
            self._s_int_3_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._s_int_4_()
            if not self.failed:
                v__3 = self.val
        if not self.failed:
            self._succeed(_cat(_scons(_cat(v__1), _scons(v__2, v__3))))

    def _s_int_2_(self):
        p = self.pos
        self._ch('-')
        if self.failed:
            self._succeed([], p)
        else:
            self._succeed([self.val])

    def _s_int_3_(self):
        if self.pos == self.end:
            self._fail()
        p = re.compile('[' + '1-9' + ']')
        m = p.match(self.text, self.pos)
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
        if self.pos == self.end:
            self._fail()
        p = re.compile('[' + '0-9' + ']')
        m = p.match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r_hex_(self):
        self._str('0x')
        if not self.failed:
            self._s_hex_1_()
            if not self.failed:
                v__2 = self.val
        if not self.failed:
            self._succeed(_cat(_scons('0x', v__2)))

    def _s_hex_1_(self):
        vs = []
        self._s_hex_2_()
        vs.append(self.val)
        if self.failed:
            return
        while True:
            p = self.pos
            self._s_hex_2_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

    def _s_hex_2_(self):
        if self.pos == self.end:
            self._fail()
        p = re.compile('[' + '0-9a-fA-F' + ']')
        m = p.match(self.text, self.pos)
        if m:
            self._succeed(m.group(0), m.end())
            return
        self._fail()

    def _r__whitespace_(self):
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
        p = self.pos
        self._s__comment_1_()
        if not self.failed:
            return
        self._rewind(p)
        self._s__comment_5_()

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
        if self.pos == self.end or self.text[self.pos] in '\r\n':
            self._fail()
            return
        self._succeed(self.text[self.pos], self.pos + 1)

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
        vs = []
        while True:
            p = self.pos
            self._s__filler_1_()
            if self.failed or self.pos == p:
                self._rewind(p)
                break
            vs.append(self.val)
        self._succeed(vs)

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

    def _leftrec(self, rule, rule_name, left_assoc):
        pos = self.pos
        key = (rule_name, pos)
        seed = self.seeds.get(key)
        if seed:
            self.val, self.failed, self.pos = seed
            return
        if rule_name in self.blocked:
            self.val = None
            self.failed = True
            return
        current = (None, True, self.pos)
        self.seeds[key] = current
        if left_assoc:
            self.blocked.add(rule_name)
        while True:
            rule()
            if self.pos > current[2]:
                current = (self.val, self.failed, self.pos)
                self.seeds[key] = current
                self.pos = pos
            else:
                del self.seeds[key]
                self.val, self.failed, self.pos = current
                if left_assoc:
                    self.blocked.remove(rule_name)
                return

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
    return int(a)


def _cat(strs):
    return ''.join(strs)


def _cons(hd, tl):
    return [hd] + tl


def _itou(n):
    return chr(n)


def _scat(ss):
    return ''.join(ss)


def _scons(hd, tl):
    return [hd] + tl


if __name__ == '__main__':
    sys.exit(main())
