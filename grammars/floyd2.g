%whitespace_style standard
%tokens           comment digits hexdigits ident lit

grammar     = (pragma|rule)*:vs end             -> ['rules', null, vs]

sp          = ws*

ws          = '\x20' | '\x09' | eol | comment

eol         = '\x0D' '\x0A' | '\x0D' | '\x0A'

comment     = '//' (~eol any)*
            | '/*' (~'*/' any)* '*/'

pragma      = '%tokens' ident_list:is          -> ['pragma', 'tokens', is]
            | '%token' ident:t                 -> ['pragma', 'token', [t]]
            | '%whitespace_style' ident:i      -> ['pragma',
                                                   'whitespace_style', i]
            | '%whitespace' '=' choice:cs
                                               -> ['pragma', 'whitespace', [cs]]
            | '%comment_style'
              ('C++' | 'C#' | ident):c         -> ['pragma', 'comment_style', c]
            | '%comment' '=' choice:cs         -> ['pragma', 'comment', [cs]]

ident_list  = (ident:i ~'=' -> i)+:is          -> is

rule        = ident:i '=' choice:cs ','?       -> ['rule', i, [cs]]

ident       = id_start:hd id_continue*:tl      -> cat([hd] + tl)

id_start    = 'a'..'z' | 'A'..'Z' | '_' | '$'

id_continue = id_start | digit

choice      = seq:s ('|' seq)*:ss              -> ['choice', null, [s] + ss]

seq         = expr:e (expr)*:es                -> ['seq', null, [e] + es]
            |                                  -> ['empty', null, []]

expr        = post_expr:e ':' ident:l          -> ['label', l, [e]]
            | post_expr

post_expr   = prim_expr:e post_op:op           -> ['post', op, [e]]
            | prim_expr

post_op     = '?' | '*' | '+'

prim_expr   = lit:i '..' lit:j                 -> ['range', null, [i, j]]
            | lit:l                            -> l
            | escape:e                         -> e
            | ident:i ~'='                     -> ['apply', i, []]
            | '->' ll_expr:e                   -> ['action', null, [e]]
            | '{' ll_expr:e '}'                -> ['action', null, [e]]
            | '~' prim_expr:e                  -> ['not', null, [e]]
            | '?(' ll_expr:e ')'               -> ['pred', null, [e]]
            | '?{' ll_expr:e '}'               -> ['pred', null, [e]]
            | '(' choice:e ')'                 -> ['paren', null, [e]]

lit         = squote sqchar*:cs squote         -> ['lit', cat(cs), []]
            | dquote dqchar*:cs dquote         -> ['lit', cat(cs), []]

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

hex_esc     = 'x' hex:h1 hex:h2                -> xtou(h1 + h2)

unicode_esc = 'u' hex:h1 hex:h2 hex:h3 hex:h4  -> xtou(h1 + h2 + h3 + h4)
            | 'U' hex:h1 hex:h2 hex:h3 hex:h4
                  hex:h5 hex:h6 hex:h7 hex:h8  -> xtou(h1 + h2 + h3 + h4 +
                                                       h5 + h6 + h7 + h8)

escape      = '\\p{' ident:i '}'               -> ['unicat', i, []]

ll_exprs    = ll_expr:e (',' ll_expr)*:es      -> [e] + es
            |                                  -> []

ll_expr     = ll_qual:e1 '+' ll_expr:e2        -> ['ll_plus', null, [e1, e2]]
            | ll_qual:e1 '-' ll_expr:e2        -> ['ll_minus', null, [e1, e2]]
            | ll_qual

ll_qual     = ll_prim:e ll_post_op+:ps         -> ['ll_qual', null, [e] + ps]
            | ll_prim

ll_post_op  = '[' ll_expr:e ']'                -> ['ll_getitem', null, [e]]
            | '(' ll_exprs:es ')'              -> ['ll_call', null, es]

ll_prim     = 'false'                          -> ['ll_const', 'false', []]
            | 'null'                           -> ['ll_const', 'null', []]
            | 'true'                           -> ['ll_const', 'true', []]
            | 'Infinity'                       -> ['ll_const', 'Infinity', []]
            | 'NaN'                            -> ['ll_const', 'NaN', []]
            | ident:i                          -> ['ll_var', i, []]
            | '0x' hexdigits:hs                -> ['ll_num', '0x' + hs, []]
            | digits:ds                        -> ['ll_num', ds, []]
            | lit:l                            -> ['ll_lit', l[1], []]
            | '(' sp ll_expr:e sp ')'          -> ['ll_paren', null, [e]]
            | '[' sp ll_exprs:es sp ']'        -> ['ll_arr', null, es]

digits      = digit+:ds                        -> cat(ds)

hexdigits   = hex+:hs                          -> cat(hs)

hex         = digit | 'a'..'f' | 'A'..'F'

digit       = '0'..'9'