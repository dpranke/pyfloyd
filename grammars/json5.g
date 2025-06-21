%externs       = strict                          -> true
               | node                            -> pfunc
               | dict                            -> func

%whitespace    = <(' '
               | '\t'
               | '\n'
               | '\r'
               | '\v'
               | '\f'
               | '\xa0'
               | '\u2028'
               | '\u2029'
               | '\ufeff'
               | \p{Zs})+>                       -> node($1)

%comment       = <'//' [^\r\n]*>                 -> node($1)
               | <'/*' ^.'*/'>                   -> node($1)

%tokens        = bool ident null num_literal string

grammar        = value end                       -> node($1)

value          = null
               | bool
               | num_literal
               | object
               | array
               | string

null           = 'null'                          -> node(null)

bool           = 'true'                          -> node(true)
               | 'false'                         -> node(false)

object         = '{' member_list '}'              -> node(dict($2), $1, $3)
               | '{' '}'                          -> node(dict([]), $1, $2)

array          = '[' element_list ']'            -> node($2, $1, $3)
               | '[' ']'                         -> node([], $1, $2)

string         = squote sqchar* squote           -> node(cat($2))
               | dquote dqchar* dquote           -> node(cat($2))

sqchar         = bslash esc_char                 -> $2
               | bslash eol                      -> ''
               | ~bslash ~squote ~eol any        -> $4
               | ?{ !strict } '\x00'..'\x1f'

dqchar         = bslash esc_char                 -> $2
               | bslash eol                      -> ''
               | ~bslash ~dquote ~eol any        -> $4
               | ?{ !strict } '\x00'..'\x1f'

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

hex_esc        = 'x' hex{2}                      -> xtou(cat($2))

unicode_esc    = 'u' hex{4}                      -> xtou(cat($2))

element_list   = value (',' value)* ','?         -> cons($1, $2)

member_list    = member (',' member)* ','?       -> cons($1, $2)

member         = string ':' value                -> node([$1, $3])
               | ident ':' value                 -> node([$1, $3])

ident          = <id_start id_continue*>         -> node($1)

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

num_literal    = '-' num_literal                 -> node(0 - $2)
               | '+' num_literal                 -> node($2)
               | dec_literal ~id_start           -> node(atof($1))
               | hex_literal                     -> node(atoi($1, 16))
               | 'Infinity'                      -> node('Infinity')
               | 'NaN'                           -> node('NaN')

dec_literal    = <dec_int_lit frac? exp?>
               | <frac exp?>

dec_int_lit    = '0' ~digit
               | nonzerodigit digit*

digit          = '0'..'9'

nonzerodigit   = '1'..'9'

hex_literal    = ('0x' | '0X') hex+              -> strcat('0x', cat($2))

hex            = 'a'..'f'
               | 'A'..'F'
               | digit

frac           = '.' digit+

exp            = ('e' | 'E') ('+' | '-')? digit+
