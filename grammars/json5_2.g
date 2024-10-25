%whitespace    = ' '
               | '\t'
               | '\n'
               | '\r'
               | '\v'
               | '\f'
               | '\xa0'
               | '\u2028'
               | '\u2029'
               | '\ufeff'
               | \p{Zs}

%comment       = '//' (~'\n' any)*
               | '/*' (~'*/' any)* '*/'

%tokens        = ident num_literal string

grammar        = value end                       -> $1

value          = 'null'                          -> null
               | 'true'                          -> true
               | 'false'                         -> false
               | num_literal
               | object
               | array
               | string

object         = '{' member_list '}'             -> dict($2)
               | '{' '}'                         -> dict([])

array          = '[' element_list ']'            -> $2
               | '[' ']'                         -> []

string         = squote sqchar* squote           -> join('', $2)
               | dquote dqchar* dquote           -> join('', $2)

sqchar         = bslash esc_char                 -> $2
               | bslash eol                      -> ''
               | ~bslash ~squote ~eol any        -> $4

dqchar         = bslash esc_char                 -> $2
               | bslash eol                      -> ''
               | ~bslash ~dquote ~eol any        -> $4

bslash         = '\\'

squote         = "'"

dquote         = '"'

eol            = '\r' '\n'
               | '\r'
               | '\n'
               | '\u2028'
               | '\u2029'

esc_char       = 'b'                             -> '\b'
               | 'f'                             -> '\f'
               | 'n'                             -> '\n'
               | 'r'                             -> '\r'
               | 't'                             -> '\t'
               | 'v'                             -> '\v'
               | squote                          -> "'"
               | dquote                          -> '"'
               | bslash                          -> '\\'
               | ~('x' | 'u' | digit | eol) any  -> $2
               | '0' ~digit                      -> '\x00'
               | hex_esc
               | unicode_esc

hex_esc        = 'x' hex hex                     -> xtou($2 + $3)

unicode_esc    = 'u' hex hex hex hex             -> xtou($2 + $3 + $4 + $5)

element_list   = value (',' value)* ','?         -> concat([$1], $2)

member_list    = member (',' member)* ','?       -> concat([$1], $2)

member         = string ':' value                -> [$1, $3]
               | ident ':' value                 -> [$1, $3]

ident          = id_start id_continue*           -> join('', concat([$1], $2))

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

num_literal    = '-' num_literal                 -> 0 - $2
               | '+' num_literal                 -> $2
               | dec_literal ~id_start           -> float($1)
               | hex_literal                     -> hex($1)
               | 'Infinity'                      -> 'Infinity'
               | 'NaN'                           -> 'NaN'

dec_literal    = dec_int_lit frac? exp?          
                   -> join('', concat(concat([$1], $2), $3))
               | frac exp?                       -> join('', concat([$1], $2))

dec_int_lit    = '0' ~digit                      -> '0'
               | nonzerodigit digit*             -> $1 + join('', $2)

digit          = '0'..'9'

nonzerodigit   = '1'..'9'

hex_literal    = ('0x' | '0X') hex+              -> '0x' + join('', $2)

hex            = 'a'..'f' | 'A'..'F' | digit

frac           = '.' digit*                      -> '.' + join('', $2)

exp            = ('e' | 'E') ('+' | '-') digit*  -> 'e' + $2 + join('', $3)
               | ('e' | 'E') digit*              -> 'e' + join('', $2)
