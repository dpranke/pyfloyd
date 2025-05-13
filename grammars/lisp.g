
%externs    = allow_trailing                     -> false

%tokens     = atom

%whitespace = /[ \t\n]+/

%comment    = ';' (^'\n')* 

grammar     = (atom | list)* opt_end             -> $1

ws          = /[ \t\n]+/

atom        = '#t'                               -> true
            | 'true'                             -> true
            | '#f'                               -> false
            | 'false'                            -> false
            | number
            | string
            | symbol

number      = '0'                                -> 0
            | /[1-9][0-9]*/                      -> atoi($1, 10)

string      = '"' ch* '"'                        -> join('', $2)

ch          = '\\\\'                             -> '\\'
            | '\\\n'                             -> '\n'
            | ^'"'

symbol      = /[a-zA-Z][a-zA-Z0-9_]*/            -> ['symbol', $1]

list        = '(' (atom | list)* ')'             -> $2

opt_end     = ?{allow_trailing}
            | end
