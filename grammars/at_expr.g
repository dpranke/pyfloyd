grammar = (at_expr | text)*

ws      =  /[ \t\n]+/

at_expr = '@' opt_id list braces           -> concat(cons($2, $3), [$4])
        | '@' opt_id list                  -> cons($2, $3)
        | '@' opt_id braces                -> [$2, $3]
        | '@' id                           -> [$2]
        | '@' string                       -> $2

opt_id  = id
        |                                  -> ['symbol', 'quote']

id      = /[a-zA-Z_][\.a-zA-Z0-9_]*/       -> ['symbol', $1]

expr    = id
        | 'true'                           -> true
        | 'false'                          -> false
        | number
        | string
        | list

number  = '0'                              -> 0
        | /[1-9][0-9]*/                    -> atoi($1, 10)

string  = '"' dqch* '"'                    -> join('', $2)
        | "'" sqch* "'"                    -> join('', $2)

dqch    = '\\"'                            -> '"'
        | [^"]

sqch    = "\\'"                            -> "'"
        | [^']

list = '[' ws? expr (ws expr)* ws? ']'     -> cons($3, $4)
        | '[' ws? ']'                      -> []

braces   = '{' <(^'}')*> '}'               -> $2

text    = <^'@'*>                          -> $1
