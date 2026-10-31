
grammar     = ws (atom | list)* ws end?          -> $2

ws          = (comment | /[ \t\n]+/)*
            | /[ \t\n]+/

comment     = ';' (!'\n')*

atom        = '#t'                               -> true
            | 'true'                             -> true
            | '#f'                               -> false
            | 'false'                            -> false
            | number
            | string
            | symbol

number      = '0'                                -> 0
            | /[1-9][0-9]*/                      -> atoi($1, 10)

string      = '"' (!'"' any)* '"'                -> join('', $2)

symbol      = /[a-zA-Z][a-zA-Z0-9_]*/            -> ['symbol', $1]

list        = '(' (ws atom | list)* ws ')'       -> $2
