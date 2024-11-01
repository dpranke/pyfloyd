%whitespace  = ws+

%comment     = ('#'|'//') (^eol)*
             | '/*' ^.'*/'

%tokens      = number | id | string | string_list | ws | eol

ws           = [ \n\r\t]

eol          = '\r\n' | '\r' | '\n'

delimiter    = [{}\[\]():#/\\"'`]

grammar      = value
             | member+                              -> ['object', $1]

value        = 'true'                               -> ['true']
             | 'false'                              -> ['false']
             | 'null'                               -> ['null']
             | number                               -> ['number', $1]
             | string_list                          -> ['string_list', $1]
             | array                                -> ['array', $1]
             | object                               -> ['object', $1]
             | bare_word                            -> ['string', $1]

number       = <('-'|'+')? int frac? exp?>          -> atof($1)
             | <'0b' bin ((bin | '_')* bin)?>       -> atoi($1, 2)
             | <'0o' oct ((oct | '_')* oct)?>       -> atoi($1, 8)
             | <'0x' hex ((hex | '_')* hex)?>       -> atoi($1, 16)

int          = '0'
             | nonzerodigit digit_sep

digit_sep    = ((digit | '_')* digit)?

digit        = [0-9]

nonzerodigit = [1-9]

frac         = '.' digit_sep

exp          = ('e'|'E') ('+'|'-')? digit_sep

bin          = [01]

oct          = [0-7]

hex          = [0-9a-fA-F]

string_list  = single_str ('++' ws* single_str)*    -> cons($1, $2)

string       = single_str
             | multi_str
             | here_str

bare_word    = (~delimiter ~ws any)+

single_str   = 'r' squote rsqchar* squote           -> cat($3)
             | 'r' dquote rdqchar* dquote           -> cat($3)
             | 'r' bquote rbqchar* bquote           -> cat($3)
             | squote sqchar* squote                -> cat($2)
             | dquote dqchar* dquote                -> cat($2)
             | bquote bqchar* bquote                -> cat($2)

multi_str    = 'r' tsquote rtsqchar* tsquote        -> dedent(cat($3))
             | 'r' tdquote rtdqchar* tdquote        -> dedent(cat($3))
             | 'r' tbquote rtbqchar* tbquote        -> dedent(cat($3))
             | tsquote tsqchar* tsquote             -> dedent(cat($2))
             | tdquote tdqchar* tdquote             -> dedent(cat($2))
             | tbquote tbqchar* tbquote             -> dedent(cat($2))

here_str     = 'r<<' here:h (~(eol ws* ={h}) rhchar)* eol ws* ={h}
                 -> dedent(strcat(strcat(cat($3), $4), cat($5)))
             | '<<' here:h (~(eol ws* ={h}) hchar)* eol ws* ={h}
                 -> dedent(strcat(strcat(cat($3), $4), cat($5)))

here         = <~(delimiter | ws)*>

rhchar       = any

hchar        = bslash escape
             | any

squote       = "'"

sqchar       = bslash escape
             | ^(bslash | squote | eol)

dquote       = '"'

dqchar       = bslash escape
             | ^(bslash | dquote | eol)

bquote       = '`'

bqchar       = bslash escape
             | ^(bslash | bquote | eol)

rsqchar      = bslash bslash
             | bslash squote
             | ^(squote | eol)

rdqchar      = bslash bslash
             | bslash dquote
             | ^(dquote | eol)

rbqchar      = bslash bslash
             | bslash bquote
             | ^(bquote | eol)

tsquote      = "'''"

tsqchar      = bslash escape
             | ^(bslash tsquote)

tdquote      = '"""'

tbquote      = '```'

tdqchar      = bslash escape
             | ^(bslash | tdquote)

tbqchar      = bslash escape
             | ^(bslash | tbquote)

rtsqchar     = ~tsquote any

rtdqchar     = ~tdquote any

rtbqchar     = ~tbquote any

bslash       = '\\'

escape       = 'b'                                  -> '\b'
             | 'f'                                  -> '\f'
             | 'n'                                  -> '\n'
             | 'r'                                  -> '\r'
             | 't'                                  -> '\t'
             | 'v'                                  -> '\v'
             | '/'                                  -> '/'
             | squote
             | dquote
             | bquote
             | bslash
             | oct_escape
             | hex_escape
             | uni_escape
             | any

oct_escape   = ('0'..'7'){1,3}                      -> atou(cat($1), 8)

hex_escape   = 'x{' hex{2} '}'                      -> atou(cat($2), 16)
             | 'x' hex{2}                           -> atou(cat($2), 16)

uni_escape   = 'u{' hex+ '}'                        -> atou(cat($2), 16)
             | 'u' hex{4}                           -> atou(cat($2), 16)
             | 'U' hex{8}                           -> atou(cat($2), 16)

array        = '[' value? (','? value)* ']'         -> cons($2, $3)

object       = '{' member? (','? member)* '}'       -> cons($2, $3)

member       = key ':' value                        -> [$1, $3]

key          = id
             | string

id           = <id_start id_continue*>

id_start     = 'a'..'z'
             | 'A'..'Z'
             | '$'
             | '_'
             | \p{Ll}
             | \p{Lm}
             | \p{Lo}
             | \p{Lt}
             | \p{Lu}
             | \p{Nl}
             | bslash uni_escape

id_continue  = id_start
             | digit
             | \p{Mn}
             | \p{Mc}
             | \p{Nd}
             | \p{Pc}
             | '\u200c'  # zero width non-joiner
             | '\u200d'  # zero width joiner
