grammar     = (sp (pragma|rule))*:vs sp end       -> ['rules', null, vs]

sp          = ws*

ws          = ' ' | '\t' | '\r' | eol | comment

eol         = '\n'

comment     = '//' (~eol any)*
            | '/*' (~'*/' any)* '*/'

pragma      = '%tokens' ident_list:is             -> ['pragma', 'tokens', is]
            | '%token' sp ident:i                 -> ['pragma', 'token', [i]]
            | '%whitespace' sp '=' sp choice:cs
                -> ['pragma', 'whitespace', [cs]]
            | '%comment' sp '=' sp choice:cs      -> ['pragma', 'comment', [cs]]
            | '%assoc' sp lit:l sp dir:d          -> ['pragma', 'assoc', [l, d]]
            | '%prec' (sp lit)+:ls                -> ['pragma', 'prec', ls]

dir         = ('left'|'right'):d                  -> d

ident_list  = (sp ident:i sp ~'=' -> i)+:is       -> is

rule        = ident:i sp '=' sp choice:cs sp ','? -> ['rule', i, [cs]]

ident       = id_start:hd id_continue*:tl         -> strcat(hd, join('', tl))

id_start    = 'a'..'z' | 'A'..'Z' | '_' | '$'

id_continue = id_start | digit

choice      = seq:s (sp '|' sp seq)*:ss
                -> ['choice', null, arrcat([s], ss)]

seq         = expr:e (ws sp expr)*:es
                -> ['seq', null, arrcat([e], es)]
            |                                     -> ['empty', null, []]

expr        = post_expr:e ':' ident:l             -> ['label', l, [e]]
            | post_expr

post_expr   = prim_expr:e post_op:op              -> ['post', op, [e]]
            | prim_expr

post_op     = '?' | '*' | '+'

prim_expr   = lit:i sp '..' sp lit:j              -> ['range', null, [i, j]]
            | lit:l                               -> l
            | escape:e                            -> e
            | ident:i ~(sp '=')                   -> ['apply', i, []]
            | '->' sp ll_expr:e                   -> ['action', null, [e]]
            | '{' sp ll_expr:e sp '}'             -> ['action', null, [e]]
            | '~' prim_expr:e                     -> ['not', null, [e]]
            | '?(' sp ll_expr:e sp ')'            -> ['pred', null, [e]]
            | '?{' sp ll_expr:e sp '}'            -> ['pred', null, [e]]
            | '(' sp choice:e sp ')'              -> ['paren', null, [e]]
            | '[^' exchar+:es ']'
                -> ['exclude', join('', es), []]
            | '/' rechar+:rs '/'
                -> ['regexp', join('', rs), []]

lit         = squote sqchar*:cs squote            -> ['lit', join('', cs), []]
            | dquote dqchar*:cs dquote            -> ['lit', join('', cs), []]

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
            | hex_esc:c                           -> c
            | unicode_esc:c                       -> c

hex_esc     = 'x' hex:h1 hex:h2                   -> xtou(h1 + h2)

unicode_esc = 'u' hex:h1 hex:h2 hex:h3 hex:h4     -> xtou(h1 + h2 + h3 + h4)
            | 'U' hex:h1 hex:h2 hex:h3 hex:h4 hex:h5 hex:h6 hex:h7 hex:h8
                -> xtou(h1 + h2 + h3 + h4 + h5 + h6 + h7 + h8)

escape      = '\\p{' ident:i '}'                  -> ['unicat', i, []]

exchar      = bslash (']' | esc_char):c           -> c
            | (~']' ~bslash any)+:cs              -> join('', cs)

rechar      = bslash ('/' | esc_char):c           -> c
            | [^/]+:cs                            -> join('', cs)

ll_exprs    = ll_expr:e (sp ',' sp ll_expr)*:es   -> arrcat([e], es)
            |                                     -> []

ll_expr     = ll_qual:e1 sp '+' sp ll_expr:e2     -> ['ll_plus', null, [e1, e2]]
            | ll_qual:e1 sp '-' sp ll_expr:e2
               -> ['ll_minus', null, [e1, e2]]
            | ll_qual

ll_qual     = ll_prim:e ll_post_op+:ps
                -> ['ll_qual', null, arrcat([e], ps)]
            | ll_prim

ll_post_op  = '[' sp ll_expr:e sp ']'             -> ['ll_getitem', null, [e]]
            | '(' sp ll_exprs:es sp ')'           -> ['ll_call', null, es]

ll_prim     = 'false'                             -> ['ll_const', 'false', []]
            | 'null'                              -> ['ll_const', 'null', []]
            | 'true'                              -> ['ll_const', 'true', []]
            | 'Infinity'
                -> ['ll_const', 'Infinity', []]
            | 'NaN'                               -> ['ll_const', 'NaN', []]
            | ident:i                             -> ['ll_var', i, []]
            | '0x' hexdigits:hs                   -> ['ll_num', '0x' + hs, []]
            | digits:ds                           -> ['ll_num', ds, []]
            | lit:l                               -> ['ll_lit', l[1], []]
            | '(' sp ll_expr:e sp ')'             -> ['ll_paren', null, [e]]
            | '[' sp ll_exprs:es sp ']'           -> ['ll_arr', null, es]

digits      = digit+:ds                           -> join('', ds)

hexdigits   = hex+:hs                             -> join('', hs)

hex         = digit | 'a'..'f' | 'A'..'F'

digit       = '0'..'9'
