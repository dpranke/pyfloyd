grammar = (at_expr | text)*

ws      =  /[ \t\n]+/

at_expr = '@' opt_id bracket brace           -> concat(cons($2, $3), [$4])
        | '@' opt_id bracket                 -> cons($2, $3)
        | '@' opt_id brace                   -> [$2, $3]
        | '@' id                             -> [$2]                       
        | '@' string                         -> $2

opt_id  = id
        | string
        |                                     -> ['symbol', 'quote']

id      = /[a-zA-Z_][\.a-zA-Z0-9_]*/           -> ['symbol', $1]

expr    = id
        | 'true'                              -> true
        | 'false'                            -> false
        | number
        | string
        | bracket

number  = '0'
        | /[1-9][0-9]*/                   -> atoi($1, 10)

string  = '"' <(^'"')*> '"'               -> $2 
        | "'" <(^"'")*> "'"               -> $2

bracket = '[' ws? expr (ws expr)* ws? ']' -> cons($3, $4)
        | '[' ws? ']'                     -> []

brace   = '{' <(^'}')*> '}'               -> $2

text    = <^'@'*>                         -> $1
