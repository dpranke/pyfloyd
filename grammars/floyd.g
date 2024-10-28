// This is the primary description of the Floyd parser grammar.

%whitespace = (' ' | '\f' | '\n' | '\r' | '\t' | '\v')+

%comment    = ('//' | '#') [^\r\n]*
            | '/*' ^.'*/'

%tokens     = escape hex ident int lit regexp set zpos

grammar     = rule* end                    -> ['rules', null, $1]

rule        = ident '=' choice             -> ['rule', $1, [$3]]

ident       = id_start id_continue*        -> cat(scons($1, $2))

id_start    = [a-zA-Z$_%]

id_continue = id_start | [0-9]

choice      = seq ('|' seq)*               -> ['choice', null, cons($1, $2)]

seq         = expr (expr)*                 -> ['seq', null, cons($1, $2)]
            |                              -> ['empty', null, []]

expr        = '->' e_expr                 -> ['action', null, [$2]]
            | '?{' e_expr '}'             -> ['pred', null, [$2]]
            | post_expr ':' ident          -> ['label', $3, [$1]]
            | post_expr

post_expr   = prim_expr '?'                -> ['opt', null, [$1]]
            | prim_expr '*'                -> ['star', null, [$1]]
            | prim_expr '+'                -> ['plus', null, [$1]]
            | prim_expr count              -> ['count', $2, [$1]]
            | prim_expr

count       = '{' zpos ',' zpos '}'        -> [$2, $4]
            | '{' zpos '}'                 -> [$2, $2]

prim_expr   = lit '..' lit                 -> ['range', [$1, $3], []]
            | lit                          -> ['lit', $1, []]
            | '\\p{' ident '}'             -> ['unicat', $2, []]
            | set                          -> ['set', $1, []]
            | regexp                       -> ['regexp', $1, []]
            | '~' prim_expr                -> ['not', null, [$2]]
            | '^.' prim_expr               -> ['ends_in', null, [$2]]
            | '^' prim_expr                -> ['not_one', null, [$2]]
            | ident ~'='                   -> ['apply', $1, []]
            | '(' choice ')'               -> ['paren', null, [$2]]
            | '<' choice '>'               -> ['run', null, [$2]]

lit         = squote sqchar* squote        -> cat($2)
            | dquote dqchar* dquote        -> cat($2)

sqchar      = escape | ^squote

dqchar      = escape | ^dquote

bslash      = '\x5C'

squote      = '\x27'

dquote      = '\x22'

escape      = '\\b'                        -> '\x08'
            | '\\f'                        -> '\x0C'
            | '\\n'                        -> '\x0A'
            | '\\r'                        -> '\x0D'
            | '\\t'                        -> '\x09'
            | '\\v'                        -> '\x0B'
            | '\\' squote                  -> '\x27'
            | '\\' dquote                  -> '\x22'
            | '\\\\'                       -> '\x5C'
            | hex_esc
            | uni_esc
            | '\\' any                     -> $2

hex_esc     = '\\x' hex_char{2}            -> xtou(cat($2))
            | '\\x{' hex_char+ '}'         -> xtou(cat($2))

uni_esc     = '\\u' hex_char{4}            -> xtou(cat($2))
            | '\\u{' hex_char+ '}'         -> xtou(cat($2))
            | '\\U' hex_char{8}            -> xtou(cat($2))

set         = '[' '^' set_char+ ']'        -> cat(scons($2, $3))
            | '[' ~'^' set_char+ ']'       -> cat($3)

set_char    = escape
            | '\\]'                        -> ']'
            | ^']'

regexp      = '/' re_char+ '/'             -> cat($2)

re_char     = bslash '/'                   -> '/'
            | escape
            | [^/]

zpos        = '0'                          -> 0
            | <[1-9] [0-9]*>               -> atoi($1)

e_expr     = e_qual '+' e_expr             -> ['e_plus', null, [$1, $3]]
           | e_qual '-' e_expr             -> ['e_minus', null, [$1, $3]]
           | e_qual

e_exprs    = e_expr (',' e_expr)* ','?     -> cons($1, $2)
            |                              -> []

e_qual     = e_prim e_post_op+             -> ['e_qual', null, cons($1, $2)]
            | e_prim

e_post_op  = '[' e_expr ']'               -> ['e_getitem', null, [$2]]
            | '(' e_exprs ')'             -> ['e_call', null, $2]

e_prim     = 'false'                      -> ['e_const', 'false', []]
            | 'null'                      -> ['e_const', 'null', []]
            | 'true'                      -> ['e_const', 'true', []]
            | ident                       -> ['e_var', $1, []]
            | hex                         -> ['e_num', $1, []]
            | int                         -> ['e_num', $1, []]
            | lit                         -> ['e_lit', $1, []]
            | '(' e_expr ')'              -> ['e_paren', null, [$2]]
            | '[' e_exprs ']'             -> ['e_arr', null, $2]

int         = '0'
            | <'-'? [1-9] [0-9]*>

hex         = <'0x' hex_char+>

hex_char    = [0-9a-fA-F]
