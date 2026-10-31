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

fn car(l: [value]): value { l[0] }

fn cdr(l: [value]): [value] { l[1:] }

fn cons(hd: value, tail: [value]): [value] { [hd] + tail }

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
): any { ['node', tag, val] + children }

%
% RULES
%

%whitespace          = ws

%comment             = comment

grammar              = sections end                           -> $1
                     | !(defs_delim | rules_delim) rules end  -> $2
                     | !(defs_delim | rules_delim) seq end    -> $2

sections             = defs? \
                       rules_delim? \
                       rules \
                       (tokens_delim rules)?    -> node(
                                                   'sections',
                                                   $4,
                                                   val=[$1, $2, $5]
                                                )

defs                 = defs_delim decl*

rules                = rule*                    -> node('rules', $1)

rule                 = ident '=' choice         -> node('rule', [$3], $1)

choice               = seq ('|' seq)*           -> node('choice', [$1] + $2)

seq                  = clause (bslash | clause)*   -> node('seq', [$1] + $2)
                     |                          -> node('empty')

clause               = host_clause
                     | check_clause
                     | match_clause
                     | not_clause
                     | ends_in_clause
                     | run_clause
                     | postfix_clause

# Return the value of the Bargle expression. This always succeeds, and
# consumes no input.
host_clause          = '->' expr                -> node('expr', [$2])
                     | '{' expr '}'             -> node('expr', [$2])

# Succeeds if the Bargle expression is true. This consumes no input.
check_clause         = '?{' expr '}'            -> node('check', [$2])

# Check that the next input starts with the Bargle expression, and consume it.
match_clause         = '={' expr '}'            -> node('match', [$2])

# Check that the next input does not match the clause. This consumes no input.
not_clause           = '!' simple_clause        -> node('not', [$2])

ends_in_clause       = '...' simple_clause      -> node('ends_in', [$2])

postfix_clause       = simple_clause post_op    -> node($2[0], [$1], $2[1])
                     | simple_clause

post_op              = ':' ident                -> ['label', $2]
                     | '*'                      -> ['star', null]
                     | '+'                      -> ['plus', null]
                     | '?'                      -> ['opt', null]
                     | count

count                = '{' nn_int ',' int '}'   -> ['count', [$2, $4]]
                     | '{' nn_int ',' '}'       -> ['count', [$2, 'infinity']]
                     | '{' int '}'              -> ['count', [$2, $2]]

simple_clause        = string
                     | set
                     | regexp
                     | next_to
                     | ?{allow_unicode_categories} category
                     | apply
                     | parenthesized_clause

next_to              = '++'                     -> node('next_to')

apply                = ident !'='               -> node('apply', val=$1)

parenthesized_clause = '(' choice ')'           -> node('paren', [$2])

run_clause           = '<' choice '>'           -> node('run', [$2])

#
# Bargle declarations
#
# TODO: Right now this is the small subset of the Bargle declaration syntax
# needed to support just this file. Expand this to the full syntax.

decl                 = constant_decl
                     | enum_decl
                     | function_decl

constant_decl        = 'const' ident ':' type '=' expr \
                                                -> node('const', [$2, $4, $6])

enum_decl            = 'enum' ident '{' ident (',' ident)* ','? '}'

function_decl        = 'fn' ident '(' params ')' (':' type)? expr \
                                                -> node('fn', [$2, $4, $6, $8])

params               = param (',' param)* ','?  -> cons($1, $2)

param                = ident ':' type ('=' expr)? \
                                                -> node('param', [$1, $3, $4])

type           = 'bool'                         -> node('bool_type', null, [])
               | 'string'                       -> node('string_type', null, [])
               | 'value'                        -> node('value_type', null, [])
               | 'any'                          -> node('any_type', null, [])
               | '[' type ']'                   -> node('list_type', null, $2)

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
                                                -> node('add', cons($1, $2))

sub_expr       = compound_expr '-' compound_expr \
                                                -> node('sub', [$1, $3])

equal_expr     = compound_expr '==' compound_expr \
                                                -> node('equals', [$1, $3])


not_equals_expr = compound_expr '!=' compound_expr \
                                                -> node('not_equals', [$1, $3])

not_expr       = '!' compound_expr

cond_expr      = compound_expr '?' compound_expr ':' compound_expr \
                                                -> node('cond', [$1, $3, $5])

compound_expr  = simple_expr post_op            -> node(
                                                   car($2), cons($1, cdr($2))
                                                )
               | primary_expr

post_op        = '[' expr ':' (expr | -> 'inf') ']' \
                                                -> ['slice', $2, $4]
               | '[' expr ']'                   -> ['getitem', $2]
               | '(' args ')'                   -> cons('call',  $2)
               | '.' ident                      -> ['field', $2]

args           = positional_args named_args?    -> $1 + $2
               | named_args

positional_args = expr (',' expr)* ','?         -> [$1] + $2

named_args     = named_arg (',' named_arg)* ','? -> [$1] + $2

named_arg      = ident '=' expr                 -> node('named_arg', $4, val=$1)

primary_expr   = 'false'                        -> node('bool', val='false')
               | 'null'                         -> node('null', val='null')
               | 'true'                         -> node('bool', val='true')
               | ident                          -> node('ident', val=$1)
               | hex_number                     -> node('number', val=$1)
               | integer                        -> node('number', val=$1)
               | string                         -> node('string', val=$1)
               | '(' expr ')'                   -> node('paren', [$2])
               | '[' exprs ']'                  -> node('array', $2)

%
% TOKENS
%

sp                 = [ \t]

ws                 = sp+

eol                = '\r\n' | '\r' | '\n'

line_comment       = ('#' | '//') ...(eol|end)

nested_comment     = '/*' (nested_comment | (!'*/' any))* '*/'

defs_delim         = '%' ' '* defs_literal ' '* '%'
                   | '%' eol '%' ' '* defs_literal ' '* eol '%' eol

defs_literal       = /[Dd][Ee][Ff][Ss]/

rules_delim        = '%' ' '* rules_literal ' '* '%'
                   | '%' eol '%' ' '* rules_literal ' '* eol '%' eol

rules_literal      = /[Rr][Uu][Ll][Ee][Ss]/

tokens_delim       = '%' ' '* tokens_literal ' '* '%'
                   | '%' eol '%' ' '* tokens_literal ' '* eol '%' eol

tokens_literal     = /[Tt][Oo][Kk][Ee][Nn][Ss]/

ident              = /[_$a-zA-Z] [_a-zA-Z0-9]*/

string             = <quote:q (bslash escape | !q any)* q> \
                                                -> node('string', val=$1)

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

hex_escape         = 'x' hex_char{2}            -> hextou($2)
                   | 'x{' <hex_char+> '}'       -> hextou($2)

# TODO: Handle surrogate pairs.
unicode_escape     = 'u' hex_char{4}            -> hex2u($2)
                   | 'U' hex_char{8}            -> hex2u($2)
                   | 'u{' <hex_char+> '}'       -> hex2u($2)

# This is the syntax for a Unicode character name as of Unicode 18.
# (https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-4/#G2082)
unicode_name       = 'N{' <unicode_word (' ' unicode_word)*> '}' \
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

escaped_re_meta    = bslash re_meta

# This is the list of characters that have special meaning as part of
# a regular expression.
re_meta            = bslash
                   | '[' | ']'
                   | '|'
                   | '(' | ')'
                   | '*' | '?' | '+' | '/'

set                = '[' '^'? '-'? subset* '-'? ']' \
                                                -> node(
                                                       'set',
                                                       $2,
                                                       $3 + ($4 + $5)
                                                   )

subset             = safe_char '-' safe_char    -> node('range', val=[$1, $3])
                   | safe_char

single             = escaped_re_meta
                   | ?{allow_unicode_categories} category
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