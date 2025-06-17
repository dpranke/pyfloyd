%externs       = strict                            -> true
               | node                              -> func
               | f3                                -> func

grammar        = value f_ end                      -> node('grammar', [$1, $2], [1, 2], $1[3])

ws_    = <(' '
           | '\t'
           | '\n'
           | '\r'
           | '\v'
           | '\f'
           | '\xa0'
           | '\u2028'
           | '\u2029'
           | '\ufeff'
           | \p{Zs})+>  -> node('ws_', [$1], [1, 2], $1)

c_     = <'//' [^\r\n]*> -> node('c_', [$1], [1, 2], $1)
       | <'/*' ^.'*/'>   -> node('c_', [$1], [1, 2], $1)

%tokens        = ident num_literal string

value          = f_ 'null'
                   -> node('value', [$1, $2], [2, 3], null)
               | f_ 'true'
                   -> node('value', [$1, $2], [2, 3], true)
               | f_ 'false'
                   -> node('value', [$1, $2], [2, 3], false)
               | f_ num_literal
                   -> node('value', [$1, $2], [2, 3], $2[3])
               | object
                   -> node('value', [$1], [1, 2], $1[3])
               | array
                   -> node('value', [$1], [1, 2], $1[3])
               | f_ string
                   -> node('value', [$1, $2], [2, 3], $2[3])

object         = f_ '{' member_list f_ '}'
                   -> node('object', [$1, $2, $3, $4, $5], [3, 4], dict($3[3]))
               | f_ '{' f_ '}'
                   -> node('object', [$1, $2, $3, $4], [3, 4], dict([]))

array          = f_ '[' element_list f_ ']'
                   -> node('object', [$1, $2, $3, $4, $5], [3, 4], $3[3])
               | f_ '[' f_ ']'
                   -> node('object', [$1, $2, $3, $4], [3, 4], [])

string         = squote sqchar* squote
                   -> node('string', [$1, $2, $3], [2, 3], cat($2))
               | dquote dqchar* dquote
                   -> node('string', [$1, $2, $3], [2, 3], cat($2))

sqchar         = bslash esc_char                   -> $2
               | bslash eol                        -> ''
               | ~bslash ~squote ~eol any          -> $4
               | ?{ !strict } '\x00'..'\x1f'

dqchar         = bslash esc_char                   -> $2
               | bslash eol                        -> ''
               | ~bslash ~dquote ~eol any          -> $4
               | ?{ !strict } '\x00'..'\x1f'

bslash         = '\\'

squote         = "'"

dquote         = '"'

eol            = '\r' '\n'
               | '\r'
               | '\n'
               | '\u2028'
               | '\u2029'

esc_char       = 'b'                               -> '\b'
               | 'f'                               -> '\f'
               | 'n'                               -> '\n'
               | 'r'                               -> '\r'
               | 't'                               -> '\t'
               | 'v'                               -> '\v'
               | squote                            -> "'"
               | dquote                            -> '"'
               | bslash                            -> '\\'
               | ~('x' | 'u' | digit | eol) any    -> $2
               | '0' ~digit                        -> '\x00'
               | hex_esc
               | unicode_esc

hex_esc        = 'x' hex{2}                        -> xtou(cat($2))

unicode_esc    = 'u' hex{4}                        -> xtou(cat($2))

element_list   = value
                 (f_ ',' value -> node('<>', [$1, $2, $3], [3, 4], $3[3]))*
                 (f_ ',' -> node('<>', [$1, $2], [], []))?
                   -> node(
                          'element_list',
                          [$1, $2, $3],
                          [1, 2],
                          cons($1[3], f3($2))
                      )


member_list    = member
                 (f_ ',' member -> node('<>', [$1, $2, $3], [3, 4], $3[3]))*
                 (f_ ',' -> node('<>', [$1, $2], [], []))?
                   -> node(
                          'member_list',
                          [$1, $2, $3],
                          [1, 2],
                          cons($1[3], f3($2))
                      )

member         = f_ string f_ ':' value
                   -> node(
                          'member',
                          [$1, $2, $3, $4, $5],
                          [2, 5],
                          [$2[3], $5[3]]
                      )
               | f_ ident f_ ':' value
                   -> node(
                          'member',
                          [$1, $2, $3, $4, $5],
                          [2, 5],
                          [$2[3], $5[3]]
                      )

ident          = id_start id_continue*
                   -> node('ident', [], cat(scons($1[3], $2[3])))

id_start       = ascii_id_start
               | other_id_start
               | bslash unicode_esc

ascii_id_start = 'a'..'z'
               | 'A'..'Z'
               | '$'
               | '_'

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

num_literal    = '-' num_literal
                   -> node(
                          'num_literal',
                          [$1, $2],
                          [2, 3],
                          0 - $2
                      )
               | '+' num_literal
                   -> node(
                          'num_literal',
                          [$1, $2],
                          [2, 3],
                          $2
                      )
               | dec_literal ~id_start
                    -> node(
                           'num_literal',
                           [$1, $2],
                           [1, 2],
                           atof($1)
                       )
               | hex_literal
                    -> node(
                           'num_literal',
                           [$1],
                           [1, 2],
                           atoi($1, 16)
                       )
               | 'Infinity'
                    -> node(
                           'num_literal',
                           [$1],
                           [1, 2],
                           'Infinity'
                       )
               | 'NaN'
                   -> node('num_literal' [$1], [1, 2], 'NaN')

dec_literal    = <dec_int_lit frac? exp?>
               | <frac exp?>

dec_int_lit    = '0' ~digit
               | nonzerodigit digit*

digit          = '0'..'9'

nonzerodigit   = '1'..'9'

hex_literal    = ('0x' | '0X') hex+                -> strcat('0x', cat($2))

hex            = 'a'..'f'
               | 'A'..'F'
               | digit

frac           = '.' digit+

exp            = ('e' | 'E') ('+' | '-')? digit+

f_             = (ws_ | c_)*
