%assoc expr#1 left
%assoc expr#2 right

grammar = expr -> $1

expr = expr '+' expr   -> [$1, $2, $3]
     | expr '^' expr   -> [$1, $2, $3]
     | '0'..'9'
