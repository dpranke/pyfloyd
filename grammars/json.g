%whitespace    = [ \n\r\t]

%tokens        = string number 

grammar        = value end                            -> $1 

value          = object                               -> dict($1)
               | array                                -> $1
               | string                               -> $1
               | number                               -> atof($1)
               | 'true'                               -> true
               | 'false'                              -> false
               | 'null'                               -> null

object         = '{' members '}'                      -> $2
               | '{' '}'                              -> []

members        = pair (',' pair)*                     -> cons($1, $2)

pair           = string ':' value                     -> [$1, $3]

array          = '[' elements ']'                     -> $2
               | '[' ']'                              -> []

elements       = value (',' value)*                   -> cons($1, $2)

string         = <dquote dqchar* dquote>

dqchar         = bslash esc_char
               | ~bslash ~dquote ~ctrl any

bslash         = '\x5C'

dquote         = '\x22'

ctrl           = '\x00'..'\x1F'

esc_char       = 'b'
               | 'f'
               | 'n'
               | 'r'
               | 't'
               | dquote
               | bslash
               | '/'
               | 'u' hex{4}

number         = <'-'? int ('.' [0-9]+)? (e [0-9]+)?>

int            = [1-9] [0-9]*
               | '0'

hex            = [0-9a-fA-F]

e              = 'e+' | 'e-' | 'e' | | 'E+' | 'E-' | 'E'
