%externs       = strict                             -> true
               | node                               -> func

grammar        = value f_ end                       -> node($1)

ws_            = <(' '
                   | '\t'
                   | '\n'
                   | '\r'
                   | '\v'
                   | '\f'
                   | '\xa0'
                   | '\u2028'
                   | '\u2029'
                   | '\ufeff'
                   | \p{Zs})+>                      -> node($1)

c_             = <'//' [^\r\n]*>                    -> node($1)
               | <'/*' ^.'*/'>                      -> node($1)

%tokens        = ident num_literal string null bool

value          = f_ null
               | f_ bool
               | f_ num_literal
               | object
               | array
               | f_ string

object         = f_ '{' member_list f_ '}'          -> $3
               | f_ '{' f_ '}'                      -> node([])

array          = f_ '[' element_list f_ ']'         -> $3
               | f_ '[' f_ ']'                      -> node([])

null           = 'null'                             -> node(null)

bool           =  'true'                            -> node(true)
               | 'false'                            -> node(false)

string         = squote sqchar* squote              -> node(cat($2))
               | dquote dqchar* dquote              -> node(cat($2))

sqchar         = bslash esc_char                    -> $2
               | bslash eol                         -> ''
               | ~bslash ~squote ~eol any           -> $4
               | ?{ !strict } '\x00'..'\x1f'

dqchar         = bslash esc_char                    -> $2
               | bslash eol                         -> ''
               | ~bslash ~dquote ~eol any           -> $4
               | ?{ !strict } '\x00'..'\x1f'

bslash         = '\\'

squote         = "'"

dquote         = '"'

eol            = '\r' '\n'
               | '\r'
               | '\n'
               | '\u2028'
               | '\u2029'

esc_char       = 'b'                                -> '\b'
               | 'f'                                -> '\f'
               | 'n'                                -> '\n'
               | 'r'                                -> '\r'
               | 't'                                -> '\t'
               | 'v'                                -> '\v'
               | squote                             -> "'"
               | dquote                             -> '"'
               | bslash                             -> '\\'
               | ~('x' | 'u' | digit | eol) any     -> $2
               | '0' ~digit                         -> '\x00'
               | hex_esc
               | unicode_esc

hex_esc        = 'x' hex{2}                         -> xtou(cat($2))

unicode_esc    = 'u' hex{4}                         -> xtou(cat($2))

element_list   = value (f_ ',' value)* (f_ ',' )?   -> node(cons($1, $2))


member_list    = member (f_ ',' member)* (f_ ',')?  -> node(cons($1, $2))

member         = f_ string f_ ':' value             -> node([$2, $5])
               | f_ ident f_ ':' value              -> node([$2, $5])

ident          = id_start id_continue*              -> node(cat(scons($1, $2)))

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

num_literal    = '-' num_literal                    -> node(0 - $2)
               | '+' num_literal                    -> node($2)
               | dec_literal ~id_start              -> node(atof($1))
               | hex_literal                        -> node(atoi($1, 16))
               | 'Infinity'                         -> node('Infinity')
               | 'NaN'                              -> node('NaN')

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
