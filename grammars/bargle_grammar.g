# This is the grammar for a Bargle grammar itself.

%externs = memoize                  -> true
         | allow_unicode_escapes    -> true
         | allow_unicode_categories -> true
         | allow_unicode_names      -> true
         | has_builtin_regexps      -> true
         | node                     -> pfunc

# %defs    = {
#
# # Whether to memoize values in the parser
# const memoize: bool = true
#
# # Whether to allow unicode escapes with '\u'
# const allow_unicode_escapes: bool = true
#
# # Whether to allow unicode categories with '\p{}'
# const allow_unicode_categories: bool = true
#
# # Whether to allow unicode named entities with '\N{}' as part of an
# # escape sequence
# const allow_unicode_names: bool = true
#
# # If true, the parser has a built-in regexp engine compatible w/
# # the Bargle regexp syntax and can take a whole string as a single node;
# # If false, the parser will break down the regexp into an equivalent set of
# # parse nodes.
# const has_builtin_regexps: bool = true
#
# fn car(l: [value]): value { l[0] }
#
# fn cdr(l: [value]): [value] { l[1:] }
#
# fn cons(hd: value, tail: [value]): [value] { [hd] + tail }
#
# # Takes a string of hex digits and returns a string containing the
# # corresponding Unicode code point. Even if the implementation sets
# # `allow_unicode_escapes` to False, they should implement this
# # and handle 1-2 character strings that are the hex equivalents of ascii
# # characters, i.e. ([0-9a-fA-F] | [0-7][0-9a-fA-F])
# fn hex2u(s: string): string { '' }
#
# # Takes a unicode character name and returns a string containing the
# # corresponding Unicode code point. Not needed if `allow_unicode_names`
# # is false.
# fn name2u(s: string): string { '' }
#
# fn node(
#     tag: string,
#     children: [any] = [],
#     val: any = null,
# ): any { ['node', tag, val] + children }
#
# }

%tokens              = sp ws eol line_comment nested_comment
                       ident string regexp set nn_integer positive_integer

%whitespace          = ws

%comment             = line_comment | nested_comment

grammar              = rule* end                -> node(['rules', null, $1])

rule                 = ident '=' choice         -> node(['rule', $1, [$3]])

choice               = seq ('|' seq)*           -> node(['choice', null, cons($1, $2)])

seq                  = clause (bslash | clause)*  -> node(['seq', null, cons($1, $2)])
                     |                            -> node(['empty', null, []])

clause               = host_clause
                     | check_clause
                     | match_clause
                     | not_clause
                     | next_to_clause
                     | ends_in_clause
                     | run_clause
                     | postfix_clause

# Return the value of the Bargle expression. This always succeeds, and
# consumes no input.
host_clause          = '->' expr                -> node(['action', null, [$2]])
                     | '{' decl* expr '}'       -> node(['action', null, [$3]])

# Succeeds if the Bargle expression is true. This consumes no input.
check_clause         = '?{' expr '}'            -> node(['pred', null, [$2]])

# Check that the next input starts with the Bargle expression, and consume it.
match_clause         = '={' expr '}'            -> node(['equals', null, [$2]])

next_to_clause       = '++'                     -> node(['next_to', null, []])

# Check that the next input does not match the clause. This consumes no input.
not_clause           = '!' ++ simple_clause        -> node(['not', null, [$3]])

ends_in_clause       = '...' ++ simple_clause      -> node(['ends_in', null, [$3]])

postfix_clause       = simple_clause ++ post_op    -> node([$3[0], $3[1], [$1]])
                     | simple_clause

post_op              = ':' ++ ident             -> ['label', $3]
                     | '*'                      -> ['star', null]
                     | '+'                      -> ['plus', null]
                     | '?'                      -> ['opt', null]
                     | count

count                = '{' nn_integer ',' positive_integer '}'  -> ['count', [$2, $4]]
                     | '{' nn_integer ',' '}'                   -> ['count', [$2, 'infinity']]
                     | '{' positive_integer '}'                 -> ['count', [$2, $2]]

simple_clause        = string
                     | set
                     | regexp
                     | ?{allow_unicode_categories} category
                     | apply
                     | parenthesized_clause

apply                = ident !'='               -> node(['apply', $1, []])

parenthesized_clause = '(' choice ')'           -> node(['paren', null, [$2]])

run_clause           = '<' choice '>'           -> node(['run', null, [$2]])

#
# Bargle declarations
#
# TODO: Right now this is the small subset of the Bargle declaration syntax
# needed to support just this file. Expand this to the full syntax.

decl                 = constant_decl
                     | enum_decl
                     | function_decl

constant_decl        = 'const' ident ':' type '=' expr \
                                                -> node(['const', null, [$2, $4, $6]])

enum_decl            = 'enum' ident '{' ident (',' ident)* ','? '}'

function_decl        = 'fn' ident '(' params ')' (':' type)? expr \
                                                -> node(['fn', null, [$2, $4, $6, $7]])

params               = param (',' param)* ','?  -> cons($1, $2)

param                = ident ':' type ('=' expr)? \
                                                -> node(['param', null, [$1, $3, $4]])

type           = 'bool'                         -> node(['bool_type', null, []])
               | 'string'                       -> node(['string_type', null, []])
               | 'value'                        -> node(['value_type', null, []])
               | 'any'                          -> node(['any_type', null, []])
               | '[' type ']'                   -> node(['list_type', null, $2])

#
# Bargle expressions
#
# TODO: Right now this is the small subset of Bargle sufficient to parse the
# expressions used in this file itself. Expand this to the full syntax.
#

expr           = add_expr
               | sub_expr
               | not_expr
               | equals_expr
               | not_equals_expr
               | cond_expr
               | compound_expr

exprs          = expr (',' expr)* ','?          -> cons($1, $2)
               |                                -> []

add_expr       = compound_expr ('+' compound_expr)* \
                                                -> node(['add', null, cons($1, $2)])

sub_expr       = compound_expr '-' compound_expr \
                                                -> node(['sub', null, [$1, $3]])

equals_expr    = compound_expr '==' compound_expr \
                                                -> node(['equals', null, [$1, $3]])


not_equals_expr = compound_expr '!=' compound_expr \
                                                -> node(['not_equals', null, [$1, $3]])

not_expr       = '!' compound_expr

cond_expr      = compound_expr '?' compound_expr ':' compound_expr \
                                                -> node(['cond', null, [$1, $3, $5]])

compound_expr  = primary_expr post_op            -> node(
                                                   [car($2), null, cons($1, cdr($2))]
                                                )
               | primary_expr

post_op        = '[' expr ':' (expr | -> 'inf') ']' \
                                                -> ['slice', $2, $4]
               | '[' expr ']'                   -> ['getitem', $2]
               | '(' args ')'                   -> cons('call',  $2)
               | '.' ident                      -> ['field', $2]

args           = positional_args named_args?    -> concat($1, $2)
               | named_args

positional_args = expr (',' expr)* ','?         -> cons($1, $2)

named_args     = named_arg (',' named_arg)* ','? -> cons($1, $2)

named_arg      = ident '=' expr                 -> node(['named_arg', $1, [$3]])

primary_expr   = 'false'                        -> node(['bool', 'false', []])
               | 'null'                         -> node(['null', 'null', []])
               | 'true'                         -> node(['bool', 'true', []])
               | ident                          -> node(['ident', $1, []])
               | number                         -> node(['number', $1, []])
               | string                         -> node(['string', $1, []])
               | '(' expr ')'                   -> node(['paren', null, [$2]])
               | '[' exprs ']'                  -> node(['array', null, $2])

#
# TOKENS
#

sp                 = [ \t]

ws                 = sp+

eol                = '\r\n' | '\r' | '\n'

line_comment       = ('#' | '//') ...(eol|end)

nested_comment     = '/*' (nested_comment | (!'*/' any))* '*/'

ident              = /[_$a-zA-Z] [_a-zA-Z0-9]*/

string             = <quote:q (bslash escape | !(={q}) any)* ={q}> \
                                                -> node(['lit', $1, []])

bslash             = '\x5C'   # \ (backslash)

quote              = squote
                   | dquote
                   | bquote

squote             = '\x27'   # ' (single quote)

dquote             = '\x22'   # " (double quote)

bquote             = '\x60'    # ` (backquote)

escape             = 'n'                        -> '\x0A'
                   | 'r'                        -> '\x0D'
                   | 't'                        -> '\x09'
                   | quote
                   | '$'
                   | bslash
                   | hex_escape
                   | ?{allow_unicode_escapes} unicode_escape
                   | ?{allow_unicode_names} unicode_name

quote              = '\x27'  # ' (single quote)
                   | '\x22'  # " (double quote)
                   | '\x60'  # ` (backquote)

hex_escape         = 'x' <hex{2}>          -> atou($2, 16)
                   | 'x{' <hex+> '}'       -> atou($2, 16)

# TODO: Handle surrogate pairs.
unicode_escape     = 'u' <hex{4}>            -> atou($2, 16)
                   | 'U' <hex{8}>            -> atou($2, 16)
                   | 'u{' <hex+> '}'       -> atou($2, 16)

# This is the syntax for a Unicode character name as of Unicode 18.
# (https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-4/#G2082)
unicode_name       = 'N{' <unicode_word (' ' unicode_word)*> '}' \
                                                -> ulookup($2)

unicode_word       = [A-Z] ([A-Z0-9]* ('-' [A-Z0-9]+))*

# The syntax for regular expressions in grammars (and in Bargle generally) is
# a subset of what is often supported in other languages, and is closer to
# POSIX basic regexps. There are no backreferences, no lookahead control, no
# grouping (for matches), no counts, and no character classes other than using
# the standard escaping mechanism. '(' and ')' do not need to be escaped.
# There is no need for '^' or '$' to match the start or the end of an
# expression, as the regexp *always* has to do so. The reasons the syntax
# (and semantics) are so limited are (a) to help ensure that if an
# implementation does have an optimized regular expression engine (i.e., one
# faster than just the regular Bargle's implementation would be), this
# subset will likely work in it, and (b) more complicated regexps are hard to
# understand (you're better off just describing them as part of the regular
# grammar).

regexp             = '/' parsed_regexp '/'      -> $2

parsed_regexp      = ?{has_builtin_regexps} <pattern+>
                                                -> node(['regexp', $2, []])
                   | pattern+                   -> node(['seq', $1, []])

pattern            = single
                   | set
                   | star_group
                   | plus_group
                   | opt_group
                   | group

escaped_re_meta    = bslash re_meta

# This is the list of characters that have special meaning as part of
# a regular expression.
re_meta            = bslash
                   | '[' | ']'
                   | '|'
                   | '(' | ')'
                   | '*' | '?' | '+' | '/'

set                = '[' '^'? '-'? subset* '-'? ']' \
                                                -> node([
                                                       'set',
                                                       $2,
                                                       $3 + ($4 + $5)
                                                   ])

subset             = safe_char '-' safe_char    -> node(['range', [$1, $3], []])
                   | safe_char

single             = escaped_re_meta
                   | ?{allow_unicode_categories} category
                   | escape
                   | safe_char

star_group         = group '*'                  -> node(['star', null, [$1]])

plus_group         = group '+'                  -> node(['plus', null, [$1]])

opt_group          = group '?'                  -> node(['opt', null, [$1]])

group              = '(' pattern ('|' pattern)* ')' \
                                                -> node(['choice', null, cons($2, $3)])

safe_char          = !re_meta any

category           = '\p{' category_name '}'    -> node('unicat', $2, [])

# This must be one of the Unicode General_Category values defined in
# https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-4/#G134153
# (either the short form like 'Nl' or the long form like 'Letter_Number')
category_name      = [A-Z] [a-z]?
                   | [A-z] [a-z]* ('_' [A-Z] [a-z]*)*


number             = hex_literal
                   | binary_literal
                   | octal_literal
                   | nn_integer
                   | float_keyword
                   | float

hex_literal        = '0x' hex hex_sep*

hex                = [0-9a-fA-F]

hex_sep            = '_'? hex

# Octal literals and escapes may or may not b supported, but if they are
# they are limited to representing only numbers in the range of [0, 256).
octal_literal      = '0o' [0-7]{3}

binary_literal     = <'0b' bin bin_sep*>

bin                = [01]

bin_sep            = '_'? bin

float_keyword      = 'nan' | 'infinity' | '-infinity'

float              = nn_integer frac? exp? ![eE]

frac               = '.' digit digit_sep*

exp                = [eE] ('-' | '+')? positive_integer

# non-negative integer
nn_integer         = '0'
                   | positive_integer

digit              = [0-9]

digit_sep          = [_0-9]

# integer
positive_integer   = [1-9] [_0-9]*