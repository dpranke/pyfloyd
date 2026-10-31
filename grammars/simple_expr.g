grammar     = expr           -> $1

expr        = prod '+' expr  -> [ $1, '+', $3 ]
            | prod '-' expr  -> [ $1, '-', $3 ]
			| prod

prod        = term '*' prod  -> [ $1, '*', $3 ]
			| term '/' prod	 -> [ $1, '/', $3 ]

term        = '0'
            | <[1-9] [0-9]*>
