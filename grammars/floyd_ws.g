// This is a version of the Floyd parser grammar that does not
// use automatic whitespace insertion. It also uses named 
// variables rather than position ones. It should behave identically
// to the refence grammar (//grammars/floyd.g)

grammar     = (sp rule)*:vs sp end                  -> ['rules', null, vs]

sp          = ws*

ws          = ' ' | '\t' | '\r' | eol | comment

eol         = '\n'

comment     = '//' (~eol any)*
            | '/*' (~'*/' any)* '*/'

ident_list  = (sp ident:i sp ~'=' -> i)+:is         -> is

rule        = ident:i sp '=' sp choice:cs sp ','?   -> ['rule', i, [cs]]

ident       = id_start:hd id_continue*:tl           -> strcat(hd, cat(tl))

id_start    = 'a'..'z' | 'A'..'Z' | '_' | '$'

id_continue = id_start | digit

choice      = seq:s (sp '|' sp seq)*:ss        -> ['choice', null, cons(s, ss)]

seq         = sp expr:e (ws sp expr)*:es           -> ['seq', null, cons(e, es)]
            |                                      -> ['empty', null, []]

expr        = '<' sp choice:c sp '>'               -> ['run', null, [c]]
            | '->' sp ll_expr:e                    -> ['action', null, [e]]  
            | '?{' sp ll_expr:e sp '}'             -> ['pred', null, [e]]
            | post_expr:e sp ':' sp ident:l        -> ['label', l, [e]]
            | post_expr

post_expr   = prim_expr:e sp post_op:op            -> ['post', op, [e]]
            | prim_expr:e sp count:c               -> ['count', c, [e]]
            | prim_expr

post_op     = '?' | '*' | '+'

count       = '{' sp zpos:z1 sp ',' sp zpos:z2 sp '}'   -> [z1, z2]
            | '{' sp zpos:z sp '}'                      -> [z, z]

prim_expr   = lit:i sp '..' sp lit:j              -> ['range', null, [i, j]]
            | lit:l                               -> ['lit', l, []] 
            | '\\p{' ident:i sp '}'               -> ['unicat', i, []]
            | ident:i ~(sp '=')                   -> ['apply', i, []]
            | '~' prim_expr:e                     -> ['not', null, [e]]
            | '^.' prim_expr:e                    -> ['ends_in', null, [e]]
            | '^' prim_expr:e                     -> ['not_one', null, [e]]
            | '[' set_char+:es ']'                -> ['set', cat(es), []]
            | '/' re_char+:rs '/'                 -> ['regexp', cat(rs), []]
            | '(' sp choice:e sp ')'              -> ['paren', null, [e]]

lit         = squote sqchar*:cs squote            -> ['lit', cat(cs), []]
            | dquote dqchar*:cs dquote            -> ['lit', cat(cs), []]

sqchar      = bslash (squote | esc_char):c        -> c
            | ~squote any:c                       -> c

dqchar      = bslash (dquote | esc_char):c        -> c
            | ~dquote any:c                       -> c

bslash      = '\x5C'

squote      = '\x27'

dquote      = '\x22'

esc_char    = 'b'                                 -> '\x08'
            | 'f'                                 -> '\x0C'
            | 'n'                                 -> '\x0A'
            | 'r'                                 -> '\x0D'
            | 't'                                 -> '\x09'
            | 'v'                                 -> '\x0B'
            | bslash                              -> '\x5C'
            | hex_esc
            | uni_esc

hex_esc     = 'x' hex{2}:hs                       -> xtou(cat(hs))

uni_esc     = 'u' hex{4}:hs                       -> xtou(cat(hs))
            | 'U' hex{8}:hs                       -> xtou(cat(hs))

set_char    = esc_char
            | '\\]'                               -> ']'
            | ^']'

re_char     = bslash '/'                          -> '/'
            | esc_char
            | ^'/'

zpos        = '0'                                 -> 0
            | <[1-9] [0-9]*>                      -> atoi($1, 10)

ll_exprs    = ll_expr:e (sp ',' sp ll_expr)*:es   -> concat([e], es)
            |                                     -> []

ll_expr     = ll_qual:e1 sp '+' sp ll_expr:e2
                -> ['ll_plus', null, [e1, e2]]
            | ll_qual:e1 sp '-' sp ll_expr:e2
                -> ['ll_minus', null, [e1, e2]]
            | ll_qual

ll_qual     = ll_prim:e ll_post_op+:ps
                -> ['ll_qual', null, cons(e, ps)]
            | ll_prim

ll_post_op  = '[' sp ll_expr:e sp ']'             -> ['ll_getitem', null, [e]]
            | '(' sp ll_exprs:es sp ')'           -> ['ll_call', null, es]

ll_prim     = 'false'                             -> ['ll_const', 'false', []]
            | 'null'                              -> ['ll_const', 'null', []]
            | 'true'                              -> ['ll_const', 'true', []]
            | ident:i                             -> ['ll_var', i, []]
            | '0x' hexdigits:hs
                -> ['ll_num', strcat('0x', hs), []]
            | digits:ds                           -> ['ll_num', ds, []]
            | lit:l                               -> ['ll_lit', l[1], []]
            | '(' sp ll_expr:e sp ')'             -> ['ll_paren', null, [e]]
            | '[' sp ll_exprs:es sp ']'           -> ['ll_arr', null, es]

digits      = digit+:ds                           -> cat(ds)

hexdigits   = hex+:hs                             -> cat(hs)

hex         = digit | 'a'..'f' | 'A'..'F'

digit       = '0'..'9'
