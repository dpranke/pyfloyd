grammar        = sp value:v sp end                    -> v

sp             = ws*

ws             = ' '
               | eol
               | comment
               | '\t'
               | '\v'
               | '\f'
               | '\xa0'
               | '\ufeff'
               | \p{Zs}

eol            = '\r' '\n'
               | '\r'
               | '\n'
               | '\u2028'
               | '\u2029'

comment        = '//' ['\r\n]*
               | '/*' ^.'*/'

value          = 'null'                               -> null
               | 'true'                               -> true
               | 'false'                              -> false
               | num_literal:v                        -> v
               | object:v                             -> v
               | array:v                              -> v
               | string:v                             -> v

object         = '{' sp member_list:v sp '}'          -> dict(v)
               | '{' sp '}'                           -> dict([])

array          = '[' sp element_list:v sp ']'         -> v
               | '[' sp ']'                           -> []

string         = squote sqchar*:cs squote             -> cat(cs)
               | dquote dqchar*:cs dquote             -> cat(cs)

sqchar         = bslash esc_char:c                    -> c
               | bslash eol                           -> ''
               | ~bslash ~squote ~eol any:c           -> c

dqchar         = bslash esc_char:c                    -> c
               | bslash eol                           -> ''
               | ~bslash ~dquote ~eol any:c           -> c

bslash         = '\\'

squote         = "'"

dquote         = '"'

esc_char       = 'b'                                  -> '\b'
               | 'f'                                  -> '\f'
               | 'n'                                  -> '\n'
               | 'r'                                  -> '\r'
               | 't'                                  -> '\t'
               | 'v'                                  -> '\v'
               | squote                               -> "'"
               | dquote                               -> '"'
               | bslash                               -> '\\'
               | ~('x' | 'u' | digit | eol) any:c     -> c
               | '0' ~digit                           -> '\x00'
               | hex_esc:c                            -> c
               | unicode_esc:c                        -> c

hex_esc        = 'x' hex{2}:hs                        -> xtou(cat(hs))

unicode_esc    = 'u' hex{4}:hs                        -> xtou(cat(hs))

element_list   = value:v (sp ',' sp value)*:vs sp ','?
                   -> cons(v, vs)

member_list    = member:m (sp ',' sp member)*:ms sp ','? 
                   -> cons(m, ms)

member         = string:k sp ':' sp value:v          -> [k, v]
               | ident:k sp ':' sp value:v           -> [k, v]

ident          = id_start:hd id_continue*:tl         -> cat(cons(hd, tl))

id_start       = ascii_id_start
               | other_id_start
               | bslash unicode_esc

ascii_id_start = 'a'..'z' | 'A'..'Z' | '$' | '_'

other_id_start = \p{Ll}
               | \p{Lm}
               | \p{Lo}
               | \p{Lt}
               | \p{Lu}
               | \p{Nl}

id_continue    = ascii_id_start
               | digit
               | other_id_start
               | \p{Mn}
               | \p{Mc}
               | \p{Nd}
               | \p{Pc}
               | bslash unicode_esc
               | '\u200c'
               | '\u200d'

num_literal    = '-' num_literal:n                   -> 0 - n
               | '+' num_literal:n                   -> n
               | dec_literal:d ~id_start             -> float(d)
               | hex_literal:h                       -> hex(h)
               | 'Infinity'                          -> 'Infinity'
               | 'NaN'                               -> 'NaN'

dec_literal    = dec_int_lit:d frac:f exp:e          -> strcat(d, strcat(f, e))
               | dec_int_lit:d frac:f                -> strcat(d, f)
               | dec_int_lit:d exp:e                 -> strcat(d, e)
               | dec_int_lit:d                       -> d
               | frac:f exp:e                        -> strcat(f, e)
               | frac:f                              -> f

dec_int_lit    = '0' ~digit                          -> '0'
               | nonzerodigit:d digit*:ds            -> cat(cons(d, ds))

digit          = '0'..'9'

nonzerodigit   = '1'..'9'

hex_literal    = ('0x' | '0X') hex+:hs               -> cat(cons('0x', hs))

hex            = 'a'..'f' | 'A'..'F' | digit

frac           = '.' digit*:ds                       -> cat(cons('.', ds))

exp            = ('e' | 'E') ('+' | '-'):s digit*:ds 
                   -> cat(cons('e', cons(s, ds)))
               | ('e' | 'E') digit*:ds               -> cat(cons('e', ds))
