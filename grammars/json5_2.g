%comment_style    C++
%whitespace_style standard  // should be 'unicode'
%tokens           ident num_literal string

grammar        = value:v end                         -> v

value          = 'null'                              -> null
               | 'true'                              -> true
               | 'false'                             -> false
               | num_literal:v                       -> v
               | object:v                            -> v
               | array:v                             -> v
               | string:v                            -> v

object         = '{' member_list:v '}'               -> dict(v)
               | '{' '}'                             -> dict([])

array          = '[' element_list:v ']'              -> v
               | '[' ']'                             -> []

string         = squote sqchar*:cs squote            -> join('', cs)
               | dquote dqchar*:cs dquote            -> join('', cs)

sqchar         = bslash esc_char:c                   -> c
               | bslash eol                          -> ''
               | ~bslash ~squote ~eol any:c          -> c

dqchar         = bslash esc_char:c                   -> c
               | bslash eol                          -> ''
               | ~bslash ~dquote ~eol any:c          -> c

bslash         = '\\'

squote         = "'"

dquote         = '"'

eol            = '\r' '\n'
               | '\r'
               | '\n'
               | '\u2028'
               | '\u2029'

esc_char       = 'b'                                 -> '\b'
               | 'f'                                 -> '\f'
               | 'n'                                 -> '\n'
               | 'r'                                 -> '\r'
               | 't'                                 -> '\t'
               | 'v'                                 -> '\v'
               | squote                              -> "'"
               | dquote                              -> '"'
               | bslash                              -> '\\'
               | ~('x' | 'u' | digit | eol) any:c    -> c
               | '0' ~digit                          -> '\x00'
               | hex_esc:c                           -> c
               | unicode_esc:c                       -> c

hex_esc        = 'x' hex:h1 hex:h2                   -> xtou(h1 + h2)

unicode_esc    = 'u' hex:a hex:b hex:c hex:d         -> xtou(a + b + c + d)

element_list   = value:v (',' value)*:vs ','?        -> [v] + vs

member_list    = member:m (',' member)*:ms ','?      -> [m] + ms

member         = string:k ':' value:v                -> [k, v]
               | ident:k ':' value:v                 -> [k, v]

ident          = id_start:hd id_continue*:tl         -> join('', [hd] + tl)

id_start       = ascii_id_start
               | other_id_start
               | bslash unicode_esc

ascii_id_start = 'a'..'z' | 'A'..'Z' | '$' | '_'

other_id_start = \p{Ll}:x                            -> x
               | \p{Lm}:x                            -> x
               | \p{Lo}:x                            -> x
               | \p{Lt}:x                            -> x
               | \p{Lu}:x                            -> x
               | \p{Nl}:x                            -> x

id_continue    = ascii_id_start
               | digit
               | other_id_start
               | \p{Mn}:x                            -> x
               | \p{Mc}:x                            -> x
               | \p{Nd}:x                            -> x
               | \p{Pc}:x                            -> x
               | bslash unicode_esc
               | '\u200c'
               | '\u200d'

num_literal    = '-' num_literal:n                   -> 0 - n
               | '+' num_literal:n                   -> float(n)
               | dec_literal:d ~id_start             -> float(d)
               | hex_literal:h                       -> hex(h)
               | 'Infinity'                          -> Infinity
               | 'NaN'                               -> NaN

dec_literal    = dec_int_lit:d frac:f exp:e          -> d + f + e
               | dec_int_lit:d frac:f                -> d + f
               | dec_int_lit:d exp:e                 -> d + e
               | dec_int_lit:d                       -> d
               | frac:f exp:e                        -> f + e
               | frac:f                              -> f

dec_int_lit    = '0' ~digit                          -> '0'
               | nonzerodigit:d digit*:ds            -> d + join('', ds)

digit          = '0'..'9'

nonzerodigit   = '1'..'9'

hex_literal    = ('0x' | '0X') hex+:hs               -> '0x' + join('', hs)

hex            = 'a'..'f' | 'A'..'F' | digit

frac           = '.' digit*:ds                       -> '.' + join('', ds)

exp            = ('e' | 'E') ('+' | '-'):s digit*:ds -> 'e' + s + join('', ds)
               | ('e' | 'E') digit*:ds               -> 'e' + join('', ds)
