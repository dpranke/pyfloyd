%assoc expr_1 right

grammar = expr end -> $1

expr = expr '+' expr   -> [$1, $2, $3]
     | '0'..'9'
