// This is the primary description of the Floyd parser grammar.

%externs    = memoize                      -> true
            | unicode                      -> true
            | unicode_categories           -> true
            | unicode_names                -> true
            | node                         -> func

%whitespace = <(' ' | '\f' | '\n' | '\r' | '\t' | '\v')+>

%comment    = <('//' | '#') [^\r\n]*>
            | <'/*' ^.'*/'>

%tokens     = escape hex ident int lit regexp set zpos

grammar     = rule* end                    -> node(['rules', null, $1])

rule        = ident '=' choice             -> node(['rule', $1, [$3]])

ident       = id_start id_continue*        -> cat(scons($1, $2))

id_start    = [a-zA-Z$_%]

id_continue = id_start | [0-9]

choice      = seq ('|' seq)*               -> node(['choice', null, cons($1, $2)])

seq         = expr (expr)*                 -> node(['seq', null, cons($1, $2)])
            |                              -> node(['empty', null, []])

expr        = '->' e_expr                  -> node(['action', null, [$2]])
            | '?{' e_expr '}'              -> node(['pred', null, [$2]])
            | '={' e_expr '}'              -> node(['equals', null, [$2]])
            | post_expr ':' ident          -> node(['label', $3, [$1]])
            | post_expr

post_expr   = prim_expr '?'                -> node(['opt', null, [$1]])
            | prim_expr '*'                -> node(['star', null, [$1]])
            | prim_expr '+'                -> node(['plus', null, [$1]])
            | prim_expr count              -> node(['count', $2, [$1]])
            | prim_expr

count       = '{' zpos ',' zpos '}'        -> [$2, $4]
            | '{' zpos '}'                 -> [$2, $2]

prim_expr   = lit '..' lit                 -> node(['range', [$1, $3], []])
            | lit                          -> node(['lit', $1, []])
            | ?{ unicode_categories } '\\p{' ident '}'
                                           -> node(['unicat', $3, []])
            | set                          -> node(['set', $1, []])
            | regexp                       -> node(['regexp', $1, []])
            | '~' prim_expr                -> node(['not', null, [$2]])
            | '^.' prim_expr               -> node(['ends_in', null, [$2]])
            | '^' prim_expr                -> node(['not_one', null, [$2]])
            | ident ~'='                   -> node(['apply', $1, []])
            | '(' choice ')'               -> node(['paren', null, [$2]])
            | '<' choice '>'               -> node(['run', null, [$2]])

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
            | ?{ unicode } uni_esc
            | '\\' any                     -> strcat('\\', $2)

hex_esc     = '\\x' hex_char{2}            -> atou(cat($2), 16)
            | '\\x{' hex_char+ '}'         -> atou(cat($2), 16)

uni_esc     = '\\u' hex_char{4}            -> atou(cat($2), 16)
            | '\\u{' hex_char+ '}'         -> atou(cat($2), 16)
            | '\\U' hex_char{8}            -> atou(cat($2), 16)
            | ?{ unicode_names } uni_name

uni_name    = 'N{' /[A-Z][A-Z0-9]*(( [A-Z][A-Z0-9]*|(-[A-Z0-9]*)))*/ '}'
                                           -> ulookup($2)

set         = '[' '^' set_char+ ']'        -> cat(scons($2, $3))
            | '[' ~'^' set_char+ ']'       -> cat($3)

set_char    = '\\]'                        -> '\\]'
            | escape
            | ^']'

regexp      = '/' re_char+ '/'             -> cat($2)

re_char     = bslash '/'                   -> '/'
            | escape
            | [^/]

zpos        = '0'                          -> 0
            | <[1-9] [0-9]*>               -> atoi($1, 10)

e_expr     = e_qual '+' e_expr             -> node(['e_plus', null, [$1, $3]])
           | e_qual '-' e_expr             -> node(['e_minus', null, [$1, $3]])
           | '!' e_qual                    -> node(['e_not', null, [$2]])
           | e_qual

e_exprs    = e_expr (',' e_expr)* ','?     -> cons($1, $2)
            |                              -> []

e_qual     = e_prim e_post_op+             -> node(['e_qual', null, cons($1, $2)])
            | e_prim

e_post_op  = '[' e_expr ']'               -> node(['e_getitem', null, [$2]])
            | '(' e_exprs ')'             -> node(['e_call', null, $2])

e_prim     = 'false'                      -> node(['e_const', 'false', []])
            | 'null'                      -> node(['e_const', 'null', []])
            | 'true'                      -> node(['e_const', 'true', []])
            | 'func'                      -> node(['e_const', 'func', []])
            | ident                       -> node(['e_ident', $1, []])
            | hex                         -> node(['e_num', $1, []])
            | int                         -> node(['e_num', $1, []])
            | lit                         -> node(['e_lit', $1, []])
            | '(' e_expr ')'              -> node(['e_paren', null, [$2]])
            | '[' e_exprs ']'             -> node(['e_arr', null, $2])

int         = '0' ~'x'                    -> '0'
            | <'-'? [1-9] [0-9]*>

hex         = <'0x' hex_char+>

hex_char    = [0-9a-fA-F]
