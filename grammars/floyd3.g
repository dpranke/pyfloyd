%whitespace = [ \f\n\r\t\v]*

%comment    = ('//' | '#') [^\r\n]*
            | '/*' ^.'*/'

%tokens     = escape hex ident int lit zpos

grammar     = rule* end                    { ['grammar', $1] }

rule        = ident '=' choice             { ['rule', [$1, $3]] }

ident       = id_start id_continue*        { scons($1, $2) }

id_start    = [a-zA-Z$_%]

id_continue = id_start | digit

choice      = seq ('|' seq)*               { ['choice', cons($1, $2)] }

seq         = expr (expr)*                 { ['seq', cons($1, $2)] }
            |                              { ['empty'] }

expr        = lit '..' lit                 { ['range', $1, $3] }
            | '<' expr '>'                 { ['run', $2] }
            | '{' result '}'               { ['result', $2] }
            | '?{' result '}'              { ['pred', $2] }
            | post_expr ':' ident          { ['label', $1, $3] }
            | post_expr

post_expr   = prim_expr '?'                { ['opt', $1] }
            | prim_expr '*'                { ['star', $1] }
            | prim_expr '+'                { ['plus', $1] }
            | prim_expr count              { ['count', $1, $2] }
            | prim_expr

count       = '{' zpos ',' zpos '}'        { [$2, $3] }
            = '{' zpos '}'                 { [$2, $2] }

prefix_expr = '~' prim_expr                { ['not', $2] }
            | '^' prim_expr                { ['not-one', $2] }
            | '^.' prim_expr               { ['ends-in', $2] }
            | prim_expr

prim_expr   = lit                          { ['lit', $1] }
            | '\\p{' ident '}'             { ['unicat', $2] }
            | '[' set_char+ ']'            { ['set', $2] }
            | '[^' set_char+ ']'           { ['not-set', cat($2)] }
            | ident ~'='                   { ['apply', $1] }
            | '(' choice ')'               { ['paren', $2] }

lit         = squote sqchar* squote        { cat($2) }
            | dquote dqchar* dquote        { cat($2) }

sqchar      = escape | ^squote

dqchar      = escape | ^dquote

bslash      = '\x5C'

squote      = '\x27'

dquote      = '\x22'

escape      = '\\b'                        { '\x08' }
            | '\\f'                        { '\x0C' }
            | '\\n'                        { '\x0A' }
            | '\\r'                        { '\x0D' }
            | '\\t'                        { '\x09' }
            | '\\v'                        { '\x0B' }
            | '\\' squote                  { '\x27' }
            | '\\' dquote                  { '\x22' }
            | '\\\\'                       { '\x5C' }
            | hex_esc
            | uni_esc
            | '\\' any                     { $2 }

hex_esc     = '\\x' hex{2}                 { itou(scat($2)) }
            | '\\x{' hex+ '}'              { itou(scat($2)) }

uni_esc     = '\\u' hex{4}                 { itou(atoi(scons('0x', $2))) }
            | '\\u{' hex+ '}'              { itou(atoi(scons('0x', $2))) }
            | '\\U' hex{8}                 { itou(atoi(scons('0x', $2))) }

set_char     = escape
            | ^']'

zpos        = '0'                          { 0 }
            | [1-9] [0-9]*                 { atoi(scons($1, $2)) }

result      = r_qual '+' result            { ['r_plus', [$1, $2]] }
            | r_qual '-' result            { ['r_minus', [$1, $2]] }
            | r_qual

results     = result (',' result)* ','?    { cons($1, $2) }
            |                              { [] }

r_qual      = r_prim r_post_op+            { ['r_qual', cons($1, $2)] }
            | r_prim

r_post_op   = '[' result ']'               { ['r_getitem', $2] }
            | '(' results ')'              { ['r_call', $2] }

r_prim      = 'false'                      { ['r_const', 'false'] }
            | 'null'                       { ['r_const', 'null'] }
            | 'true'                       { ['r_const', 'true'] }
            | ident                        { ['r_var', $1] }
            | hex                          { ['r_num', $1] }
            | int                          { ['r_num', $1] }
            | lit                          { ['r_lit', $1[1]] }
            | '(' result ')'               { ['r_paren', $2] }
            | '[' results ']'              { ['r_array', $2] }

int         = '0'
            | '-'? [1-9] [0-9]*            {
                atoi(cat(concat(cat($1), scons($2, $3))))
            }

hex         = '0x' [0-9a-fA-F]+            { atoi(strcat('0x', cat($2))) }
