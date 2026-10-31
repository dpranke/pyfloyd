# This is a Floyd grammar capable of parsing the grammar for a
# Bargle grammar (the actual grammar, not just *a* grammar).

%externs       = memoize                      -> true
               | allow_unicode_escapes        -> true
               | allow_unicode_categories     -> true
               | allow_unicode_names          -> true
               | has_builtin_regexps          -> true
               | node                         -> pfunc  # [any]

%whitespace    = ws

%comment       = line_comment
               | nested_comment

%tokens        = line_comment nested_comment
                 defs_delim rules_delim tokens_delim
                 ident string regexp set category nn_int integer

grammar        = sections

sections       = defs?
                 rules_delim?
                 rules
                 (tokens_delim rules)?
                 end
                                              -> node([
                                                'sections', [$1, $3, $4], []
                                              ])

#
# This is the subset of the bargle language that is needed to support
# the %DEFS% section of the bargle grammar
#

defs           = defs_delim? decl*            -> node(['defs', null, $2])

decl           = constant_decl
               | enum_decl
               | function_decl

constant_decl  = 'const' ident ':' type '=' e_expr
                                              -> node([
                                                 'const', null, [$2, $4, $6]
                                              ])

enum_decl      = 'enum' ident '{' ident (',' ident)* ','? '}'
                                              -> node([
                                                 'enum_decl', $1, cons($4, $5)
                                                 ])
function_decl  = 'fn' ident '(' params ')' (':' type)? '{' e_expr '}'
                                              -> node([
                                                'fn',
                                                null,
                                                [$2, $4, $6, $8]
                                              ])

params         = param (',' param)* ','?      -> cons($1, $2)

param          = ident ':' type ('=' e_expr)?
                                              -> node([
                                                 'param',
                                                 null,
                                                 [$1, $3, $4]
                                              ])

type           = 'bool'                       -> node(['bool_type', null, []])
               | 'string'                     -> node(['string_type', null, []])
               | 'value'                      -> node(['value_type', null, []])
               | 'any'                        -> node(['any_type', null, []])
               | ident                        -> node(['ident_type', null, [$1]])
               | '[' type ']'                 -> node(['list_type', null, [$2]])

#
# Now the actual rules of the grammar
#

rules          = rule*                        -> node(['rules', null, $1])

rule           = ident '=' choice             -> node(['rule', $1, [$3]])

choice         = seq ('|' seq)*               -> node([
                                                 'choice', null, cons($1, $2)
                                              ])

seq            = expr ('\\'? expr)*         -> node([
                                                 'seq', null, cons($1, $2)
                                              ])
               |                              -> node(['empty', null, []])

expr           = '->' e_expr                  -> node(['action', null, [$2]])
               | '?{' e_expr '}'              -> node(['pred', null, [$2]])
               | '={' e_expr '}'              -> node(['equals', null, [$2]])
               | post_expr ':' ident          -> node(['label', $3, [$1]])
               | post_expr

post_expr      = prim_expr ~ws '?'            -> node(['opt', null, [$1]])
               | prim_expr ~ws '*'            -> node(['star', null, [$1]])
               | prim_expr ~ws '+'            -> node(['plus', null, [$1]])
               | prim_expr ~ws count          -> node(['count', $2, [$1]])
               | prim_expr

count          = '{' nn_int ',' nn_int '}'    -> [$2, $4]
               | '{' nn_int ',' '}'           -> [$2, 'Infinity']
               | '{' nn_int '}'               -> [$2, $2]

prim_expr      = string                       -> node(['lit', $1, []])
               | ?{ allow_unicode_categories } category
                                              -> node(['unicat', $2, []])
               | set                          -> node(['set', $1, []])
               | regexp                       -> node(['regexp', $1, []])
               | '!' ~ws prim_expr            -> node(['not', null, [$2]])
               | '...' ~ws prim_expr          -> node(['ends_in', null, [$2]])
               | '++'                         -> node(['next_to', null, []])
               | ident ~'='                   -> node(['apply', $1, []])
               | '(' choice ')'               -> node(['paren', null, [$2]])
               | '<' choice '>'               -> node(['run', null, [$2]])

#
# HOST (Bargle) expressions
#
# This is a small subset of Bargle sufficient to parse the stuff in
# the bargle grammar %defs% section and any host expressions
#

e_expr         = e_qual '+' e_qual            -> node([
                                                 'e_plus', null, [$1, $3]
                                              ])
               | e_qual '-' e_qual            -> node([
                                                 'e_minus', null, [$1, $3]
                                              ])
               | e_qual '==' e_qual           -> node([
                                                 'e_eq', null, [$1, $3]
                                              ])
               | e_qual '!=' e_qual           -> node([
                                                  'e_ne', null, [$1, $3]
                                              ])
               | e_qual '?' e_qual ':' e_qual -> node([
                                                  'e_cond', null, [$1, $3, $5]
                                              ])
               | '!' e_qual                   -> node(['e_not', null, [$2]])
               | e_qual

e_qual         = e_prim e_post_op+            -> node([
                                                 'e_qual', null, cons($1, $2)
                                              ])
               | e_prim

e_post_op      = e_slice
               | '[' e_expr ']'               -> node(['e_getitem', null, [$2]])
               | '(' e_args ')'               -> node(['e_call', null, [$2]])
               | '.' ident                    -> node(['e_field', null, [$2]])

e_slice        = '[' e_expr ':' e_expr ']'    -> node([
                                                     'e_slice',
                                                     null,
                                                     [$2, $4]
                                                 ])
               | '[' e_expr ':' ']'           -> node([
                                                     'e_slice',
                                                     null,
                                                     [$2, node(['e_num', -1, []])]
                                                 ])
               | '[' ':' e_expr ']'           -> node([
                                                     'e_slice',
                                                     null,
                                                     [node(['e_num', 0, []]), $3]
                                                 ])

e_args         = e_pos_args ',' e_named_args  -> node(['e_args', null, $1 + $3])
               | e_pos_args ','?              -> node(['e_args', null, $1])
               | e_named_args ','?            -> node(['e_args', null, $1])

e_pos_args     = e_pos_arg (',' e_pos_arg)*   -> cons($1, $2)

e_pos_arg      = ~(ident '=') e_expr

e_named_args   = e_named_arg (',' e_named_arg)* -> cons($1, $2)

e_named_arg    = ident '=' e_expr             -> node(['e_named_arg', null, [$1, $2]])

e_prim         = 'false'                      -> node(['e_const', 'false', []])
               | 'null'                       -> node(['e_const', 'null', []])
               | 'true'                       -> node(['e_const', 'true', []])
               | ident                        -> node(['e_ident', $1, []])
               | hex_number                   -> node(['e_num', $1, []])
               | integer                      -> node(['e_num', $1, []])
               | string                       -> node(['e_lit', $1, []])
               | '(' e_expr ')'               -> node(['e_paren', null, [$2]])
               | '[' e_exprs ']'              -> node(['e_arr', null, $2])

e_exprs        = e_expr (',' e_expr)* ','?    -> cons($1, $2)
               |                              -> []

#
# TOKENS
#

ws             = /[ \t\f\r\n]+/

sp             = [ \t\f\r\n]

eol            = /\r\n|\r|\n/

line_comment   = <('#' | '//') (~(eol | end) any)*>

nested_comment = <'/*' (nested_comment | (~'*/' ~'/*' any))* '*/'>

defs_delim     = '%' ' '* defs_literal ' '* '%'
               | '%' eol '%' ' '* defs_literal ' '* eol '%' eol

defs_literal   = /[Dd][Ee][Ff][Ss]/

rules_delim    = '%' ' '* rules_literal ' '* '%'
               | '%' eol '%' ' '* rules_literal ' '* eol '%' eol

rules_literal  = /[Rr][Uu][Ll][Ee][Ss]/

tokens_delim   = '%' ' '* tokens_literal ' '* '%'
               | '%' eol '%' ' '* tokens_literal ' '* eol '%' eol

tokens_literal = /[Tt][Oo][Kk][Ee][Nn][Ss]/

ident          = /%?[a-zA-Z_$][a-zA-Z0-9_]*/  -> $1

category       = '\\p{' ident '}'             -> $2

string         = squote sqchar* squote        -> cat($2)
               | dquote dqchar* dquote        -> cat($2)

sqchar         = bslash escape | (~squote ~eol any)

dqchar         = bslash escape | (~dquote ~eol any)

bslash         = '\x5C'

squote         = '\x27'

dquote         = '\x22'

escape         = '\n'                         -> '\x0A'
               | '\r'                         -> '\x0D'
               | '\t'                         -> '\x09'
               | squote                       -> '\x27'
               | dquote                       -> '\x22'
               | bslash                       -> '\x5C'
               | hex_escape
               | ?{ allow_unicode_escapes } unicode_escape
               | ?{ allow_unicode_names } unicode_name

hex_escape     = 'x' hex_digit{2}             -> atou(cat($2), 16)
               | 'x{' hex_digit+ '}'          -> atou(cat($2), 16)

unicode_escape = '\\u' hex_digit{4}           -> atou(cat($2), 16)
               | '\\u{' hex_digit+ '}'        -> atou(cat($2), 16)
               | '\\U' hex_digit{8}           -> atou(cat($2), 16)

unicode_name   = 'N{' /[A-Z][A-Z0-9]*(([A-Z][A-Z0-9]*|(-[A-Z0-9]*)))*/ '}'
                                              -> ulookup($2)

# The actual bargle grammar has a full definition of regexps, but
# the below is good enough for Floyd for now.

set            = '[' '^' set_char+ ']'        -> cat(scons($2, $3))
               | '[' ~'^' set_char+ ']'       -> cat($3)

set_char       = '\\]'                        -> '\\]'
               | escape
               | ^']'

regexp         = '/' re_char+ '/'             -> cat($2)

re_char        = bslash '/'                   -> '/'
               | escape
               | [^/]

nn_int         = '0' ~'x'                     -> 0
               | pos_integer

pos_integer    = /[+]?[1-9][0-9]*/            -> atoi($1, 10)

integer        = '0' ~'x'                     -> 0
               | /[-+]?[1-9][0-9]*/           -> atoi($1, 10)

hex_number     = /0x[0-9a-fA-F]+/             -> atoi($1, 16)

hex_digit      = [0-9a-fA-F]