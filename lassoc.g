%assoc expr left

grammar = expr end -> $1

expr = expr '+' expr   -> [$1, $2, $3]
     | '0'..'9'
