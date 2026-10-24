# This is the grammar for a Bargle grammar itself.

%
% DEFS
%

# Whether to memoize values in the parser
const memoize: bool = true

# Whether to allow unicode escapes with '\u'
const allow_unicode_escapes: bool = true

# Whether to allow unicode categories with '\p{}'
const allow_unicode_categories: bool = true

# Whether to allow unicode named entities with '\N{}' as part of an
# escape sequence
const allow_unicode_names: bool = true

# If true, the parser has a built-in regexp engine compatible w/
# the Bargle regexp syntax and can take a whole string as a single node;
# If false, the parser will break down the regexp into an equivalent set of
# parse nodes.
const has_builtin_regexps: bool = true

# Takes a string of hex digits and returns a string containing the
# corresponding Unicode code point. Even if the implementation sets
# `allow_unicode_escapes` to False, they should implement this
# and handle 1-2 character strings that are the hex equivalents of ascii
# characters, i.e. ([0-9a-fA-F] | [0-7][0-9a-fA-F])
fn hex2u(s: string): string { '' }

# Takes a unicode character name and returns a string containing the
# corresponding Unicode code point. Not needed if `allow_unicode_names`
# is false.
fn name2u(s: string): string { '' }

fn node(
    tag: string,
    children: [any] = [],
    val: any = null,
): any,

%
% RULES
%

%whitespace        = ws

%comment           = comment

grammar            = sections
                   | rules
                   | seq

sections           = imports? \
                     defs? \
                     rules_delim \
                     rules \
                     (tokens_delim rules)? \
                     end                        -> node(
                                                       'sections',
                                                       $4,
                                                       val=($1, $2, $5)
                                                   )

imports            = 'import' import (',' import)* \
                                                -> node('imports', [$2] + $3)

import             = ident ('as' ident)?        -> node('import', val=($1, $2))

defs               = defs_delim b.script

rules              = rule* end                  -> node('rules', $1)

rule               = ident '=' choice           -> node('rule', [$3], $1)

choice             = seq ('|' seq)*             -> node('choice', [$1] + $2)

seq                = expr ('\' | expr)*         -> node('seq', [$1] + $2)
                   |                            -> node('empty')

expr               = host_expr
                   | check_expr
                   | match_expr
                   | labelled_expr
                   | unary_expr

# Return the host expression. This always succeeds, and consumes no input.
host_expr          = '->' b.expr                -> node('host', [$2])
                   | '{' b.expr '}'             -> node('host', [$2])

# Check to see if the host expression is true. This consumes no input.
check_expr         = '?{' b.expr '}'            -> node('check', [$2])

# Check that the input matches the host expression, and consume it.
match_expr         = '={' b.expr '}'            -> node('match', [$2])

labelled_expr      = prim_expr ':' ident        -> node('label', [$1], $3)

unary_expr         = not_expr
                   | opt_expr
                   | star_expr
                   | plus_expr
                   | not_expr
                   | count_expr
                   | ends_in_expr
                   | run_expr

# Check that the input does not match the primary_expression; this consumes
# no input.
not_expr           = '!' primary_expr           -> node('not', [$2]

opt_expr           = primary_expr '?'           -> node('opt', [$1])

star_expr          = primary_expr '*'           -> node('star', [$1])

plus_expr          = primary_expr '+'           -> node('plus', [$1])

count_expr         = primary_expr count         -> node('count', [$1], $2)

count              = '{' nn_int ',' int '}'     -> [$2, $4]
                   | '{' nn_int ',' '}'         -> [$2, 'infinity']
                   | '{' int '}'                -> [$2, $2]

ends_in_expr       = '...' primary_expr         -> node('ends_in', [$2])

primary_expr       = string
                   | set
                   | regexp
                   | next_to
                   | {allow_unicode_categories} category
                   | apply
                   | parenthesized_expr
                   | run_expr

next_to            = '++'                       -> node('next_to')

apply              = ident !'='                 -> node('apply', val=$1)

parenthesized_expr = '(' choice ')'             -> node('paren', [$2])

run_expr           = '<' choice '>'             -> node('run', [$2])

%
% TOKENS
%

# same as b.sp
sp                 = / \t\f\r\n/

# same as b.ws
ws                 = sp+

# same as b.eol
eol                = '\r\n' | '\r' | '\n'

# same as b.line_comment
line_comment       = ('#' | '//') ...(eol|end)

# same as b.nested_comment
nested_comment     = '/*' (nested_comment | (!'*/' any))* '*/'

defs_delim         = '%' ' '* defs_literal ' '* '%'
                   | '%' eol '%' ' '* defs_literal ' '* eol '%' eol

defs_literal       = [Dd][Ee][Ff][Ss]

rules_delim        = '%' ' '* rules_literal ' '* '%'
                   | '%' eol '%' ' '* rules_literal ' '* eol '%' eol

rules_literal      = [Rr][Uu][Ll][Ee][Ss]

tokens_delim       = '%' ' '* tokens_literal ' '* '%'
                   | '%' eol '%' ' '* tokens_literal ' '* eol '%' eol

tokens_literal     = [Tt][Oo][Kk][Ee][Nn][Ss]

# same as b.ident except that '$' is allowed as well.
ident              = [_$a-zA-Z] [_$a-zA-Z0-9]*

# mostly same as b.string except there are no tags, raw_strings, custom_strings,
# long quotes, or interpolations
string             = <quote:q (bslash escape | !q any)* q> \
                                                -> node('string', val=$1)

bslash             = '\x5C'   # \ (backslash)

quote              = squote
                   | dquote
                   | bquote

squote             = '\x27'   # ' (single quote)

dquote             = '\x22    # " (double quote)

bquote             = '\x60    # ` (backquote)

# same as b.escape
escape             = 'f'                        -> '\x0C'
                   | 'n'                        -> '\x0A'
                   | 'r'                        -> '\x0D'
                   | 't'                        -> '\x09'
                   | 'v'                        -> '\x0B'
                   | quote
                   | '$'
                   | bslash
                   | hex_escape
                   | {allow_unicode_escapes} unicode_escape
                   | {allow_unicode_names} unicode_name

quote              = '\x27'  # ' (single quote)
                   | '\x22'  # " (double quote)
                   | '\x60'  # ` (backquote)

hex_escape         = 'x' hex_char{2}            -> hextou($2)
                   | 'x{' <hex_char+> '}'       -> hextou($2)

# TODO: Handle surrogate pairs.
unicode_escape     = 'u' hex_char{4}            -> hex2u($2)
                   | 'U' hex_char{8}            -> hex2u($2)
                   | 'u{' <hex_char+> '}'       -> hex2u($2)

# This is the syntax for a Unicode character name as of Unicode 18.
# (https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-4/#G2082)
# This is the same as b.unicode_name
unicode_name       = 'N{' <unicode_word (' ' unicode_word)*> '} \
                                                -> name2u($2)

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
                                                -> node('regexp', val=$2)
                   | pattern+                   -> node('seq', $1)

pattern            = single
                   | set
                   | star_group
                   | plus_group
                   | opt_group
                   | group

escaped_re_meta = bslash re_meta

# This is the list of characters that have special meaning as part of
# a regular expression.
re_meta            = bslash | '[' | ']' | '|' | '(' | ')' | '*' | '?' | '+ | '/'

set                = '[' ^'? '-'? subset* '-'? ']' \
                                                -> node('set', $2, $3 + $4 + $5)


subset             = safe_char '-' safe_char    -> node('range', val=($1, $3))
                   | safe_char

single             = escaped_re_meta
                   | {allow_unicode_categories} category
                   | escape
                   | safe_char

star_group         = group '*'                  -> node('star', [$1])

plus_group         = group '+'                  -> node('plus', [$1])

opt_group          = group '?'                  -> node('opt', [$1])

group              = '(' pattern ('|' pattern)* ')' \
                                                -> node('choice', [$1] + $2)

safe_char          = !re_meta any

category           = '\p{' category_name '}'    -> node('unicat', $2)

# This must be one of the Unicode General_Category values defined in
# https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-4/#G134153
# (either the short form like 'Nl' or the long form like 'Letter_Number')
category_name      = [A-Z] [a-z]?
                   | [A-z] [a-z]* ('_' [A-Z] [a-z]*)*

# non-negative integer
nn_int             = '0'
                   | int

# integer
int                = [1-9] [_0-9]*