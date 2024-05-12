grammar = expr end -> $1

expr = expr '+' '0'..'9'   -> [$1, $2, $3]
     | '0'..'9'
