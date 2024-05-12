%assoc expr_1 left
%assoc expr_2 right

grammar = expr -> $1

expr = expr '+' expr   -> [$1, $2, $3]
     | expr '^' expr   -> [$1, $2, $3]
     | '0'..'9'
