%whitespace = (' ' | '\t' | '\r' | '\n')+

%comment    = '//' (~'\n' any)*
            | '/*' (~'*/' any)* '*/'

%tokens     digits hexdigits ident lit

grammar     = (pragma|rule)*:vs end             -> ['rules', null, vs]

pragma      = '%tokens' ident_list:is          -> ['pragma', 'tokens', is]
            | '%token' ident:i                 -> ['pragma', 'token', [i]]
            | '%whitespace' '=' choice:cs
                                               -> ['pragma', 'whitespace', [cs]]
            | '%comment' '=' choice:cs         -> ['pragma', 'comment', [cs]]
            | '%assoc' lit:l dir:d             -> ['pragma', 'assoc', [l, d]]
            | '%prec' lit+:ls                  -> ['pragma', 'prec', ls]

dir         = ('left'|'right'):d               -> d

ident_list  = (ident:i ~'=' -> i)+:is          -> is

rule        = ident:i '=' choice:cs ','?       -> ['rule', i, [cs]]

ident       = id_start:hd id_continue*:tl      -> strcat(hd, join('', tl))

id_start    = 'a'..'z' | 'A'..'Z' | '_' | '$'

id_continue = id_start | digit

choice      = seq:s ('|' seq)*:ss              
                -> ['choice', null, arrcat([s], ss)]

seq         = expr:e (expr)*:es                -> ['seq', null, arrcat([e], es)]
            |                                  -> ['empty', null, []]

expr        = '<' expr:e '>'                   -> ['run', e, []]
            | post_expr:e ':' ident:l          -> ['label', l, [e]]
            | post_expr

post_expr   = prim_expr:e post_op:op           -> ['post', op, [e]]
            | prim_expr:e count:c              -> ['count', c, [e]]
            | prim_expr

post_op     = '?' | '*' | '+'

count       = '{' zpos:x ',' zpos:y '}'        -> [x, y]
            | '{' zpos:x '}'                   -> [x, x]

zpos        = '0'                              -> 0
            | ('1' .. '9'):hd ('0'..'9')*:tl 
                 -> atoi(join('', arrcat([hd], tl)))

prim_expr   = lit:i '..' lit:j                 -> ['range', null, [i, j]]
            | lit:l                            -> l
            | escape:e                         -> e
            | ident:i ~'='                     -> ['apply', i, []]
            | '->' ll_expr:e                   -> ['action', null, [e]]
            | '{' ll_expr:e '}'                -> ['action', null, [e]]
            | '~' prim_expr:e                  -> ['not', null, [e]]
            | '^' prim_expr:e                  -> ['not-one', null, [e]]
            | '^.' prim_expr:e                 -> ['ends-in', null, [e]]
            | '?(' ll_expr:e ')'               -> ['pred', null, [e]]
            | '?{' ll_expr:e '}'               -> ['pred', null, [e]]
            | '(' choice:e ')'                 -> ['paren', null, [e]]
            | '[^' exchar+:es ']'
                -> ['exclude', join('', es), []]
            | '[' ~'^' exchar+:es ']'
                -> ['set', join('', es), []]
            | '/' rechar+:rs '/'
                -> ['regexp', join('', rs), []]

lit         = squote sqchar*:cs squote         -> ['lit', join('', cs), []]
            | dquote dqchar*:cs dquote         -> ['lit', join('', cs), []]

sqchar      = bslash esc_char:c                -> c
            | ~squote any:c                    -> c

dqchar      = bslash esc_char:c                -> c
            | ~dquote any:c                    -> c

bslash      = '\x5C'

squote      = '\x27'

dquote      = '\x22'

esc_char    = 'b'                              -> '\x08'
            | 'f'                              -> '\x0C'
            | 'n'                              -> '\x0A'
            | 'r'                              -> '\x0D'
            | 't'                              -> '\x09'
            | 'v'                              -> '\x0B'
            | squote                           -> '\x27'
            | dquote                           -> '\x22'
            | bslash                           -> '\x5C'
            | hex_esc:c                        -> c
            | unicode_esc:c                    -> c

rechar      = bslash ('/' | esc_char):c           -> c
            | [^/]+:cs                            -> join('', cs)

hex_esc     = 'x' hex:h1 hex:h2                -> xtou(h1 + h2)
            | 'x{' hex+:hs '}'                 -> xtou(join('', hs))

unicode_esc = 'u' hex:h1 hex:h2 hex:h3 hex:h4  -> xtou(h1 + h2 + h3 + h4)
            | 'u{' hex+:hs '}'                 -> xtou(join('', hs))
            | 'U' hex:h1 hex:h2 hex:h3 hex:h4 hex:h5 hex:h6 hex:h7 hex:h8
                -> xtou(h1 + h2 + h3 + h4 + h5 + h6 + h7 + h8)

escape      = '\\p{' ident:i '}'               -> ['unicat', i, []]

exchar      = bslash (']' | esc_char):c        -> c
            | (~']' ~bslash any)+:cs           -> join('', cs)

rechar      = bslash ('/' | esc_char):c           -> c
            | [^/]+:cs                            -> join('', cs)

ll_exprs    = ll_expr:e (',' ll_expr)*:es      -> arrcat([e], es)
            |                                  -> []

ll_expr     = ll_qual:e1 '+' ll_expr:e2        -> ['ll_plus', null, [e1, e2]]
            | ll_qual:e1 '-' ll_expr:e2        -> ['ll_minus', null, [e1, e2]]
            | ll_qual

ll_qual     = ll_prim:e ll_post_op+:ps
                -> ['ll_qual', null, arrcat([e], ps)]
            | ll_prim

ll_post_op  = '[' ll_expr:e ']'                -> ['ll_getitem', null, [e]]
            | '(' ll_exprs:es ')'              -> ['ll_call', null, es]

ll_prim     = 'false'                          -> ['ll_const', 'false', []]
            | 'null'                           -> ['ll_const', 'null', []]
            | 'true'                           -> ['ll_const', 'true', []]
            | 'Infinity'                       -> ['ll_const', 'Infinity', []]
            | 'NaN'                            -> ['ll_const', 'NaN', []]
            | ident:i                          -> ['ll_var', i, []]
            | hexdigits:hs                     -> ['ll_num', hs, []]
            | digits:ds                        -> ['ll_num', ds, []]
            | lit:l                            -> ['ll_lit', l[1], []]
            | '(' ll_expr:e ')'                -> ['ll_paren', null, [e]]
            | '[' ll_exprs:es ']'              -> ['ll_arr', null, es]

digits      = digit+:ds                        -> join('', ds)

hexdigits   = '0x' hex+:hs                     -> '0x' + join('', hs)

hex         = digit | 'a'..'f' | 'A'..'F'

digit       = '0'..'9'
