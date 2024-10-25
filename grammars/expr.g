%whitespace = [ \n\r\t]

%prec       = '+' '-'
            | '*' '/'
            | '^'

%assoc      = '^' right

expr        = expr '+' expr  -> [ $1, '+', $3 ]
            | expr '-' expr  -> [ $1, '-', $3 ]
            | expr '*' expr  -> [ $1, '*', $3 ]
            | expr '/' expr  -> [ $1, '/', $3 ]
            | expr '^' expr  -> [ $1, '^', $3 ]
            | '0'..'9'
