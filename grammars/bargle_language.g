# This is the grammar for the Bargle language, which has multiple
# dialects. See //README.md and the documentation for the differences
# between them. This grammar can be used to parse any dialect.

# common abbreviations used in the names of nonterminals:
# - 'ident' is short for 'identifier'
# - 'decl' is short for 'declaration'
# - 'stmt' is short for 'statement'

%
% DEFS
%

enum Dialect { Lower, Core, Middle, Upper }

# const dialect: Dialect = Dialect.Upper

# Is this Lower Bargle or a different dialect?
const is_lower_bargle: bool = (dialect == Dialect.Lower)

const allow_unicode_escapes: bool = true

const allow_unicode_names: bool = true

# Used to guard syntax that is reserved for the future. This should
# only be set to true if you want to ensure that something might be
# syntactically valid in the future even if it isn't now. Of course,
# this can't be used for syntax that hasn't been approved.
const allow_reserved: bool = false

enum Syntax { Module, Script, Interactive }

const syntax: Syntax = Syntax.Module

%
% RULES
%

%whitespace       = ws

%comment          = line_comment
                  | nested_comment

# A regular Bargle module can only contain imports, declarations, and
# compile-time if blocks, and the imports must happen before any declarations.
# When running as a script, imports must still be first, but in addition
# to declarations, any statement that can otherwise only happen inside a block
# is also allowed at the top level, as long as it makes sense. When running
# interactively, imports are also allowed at the top level at any time, not
# just at the beginning.

grammar            = ?{syntax == Syntax.Module} module
                   | ?{syntax == Syntax.Script} script
                   | ?{syntax == Syntax.Interactive} interactive

module             = import_time_expr* decl* end

script             = import_time_expr* stmt* end

interactive        = (import_time_expr | stmt)* end

#
# "Statements"
#

import_time_expr   = compile_time_expr
                   | import_expr


compile_time_expr  = compile_time_decl
                   | compile_time_if

# TODO: support URLs a la Go?
import_expr        = 'import' ident ('as' ident)? (',' ident ('as' ident)?)* ','?

decl               = compile_time_decl
                   | const_decl
                   | function_decl
                   | ?{!is_lower_bargle} type_decl
                   | ?{!is_lower_bargle} var_decl

function_decl      = 'fn' ident ++ signature (expr | block)

signature          = '(' params? ','? ')' (':' type (',' type)*)?

# TODO: Support positional-only or keyword-only args? Support **kwargs?
params             = required_params (',' rest_param)? (',' optional_params)?
                   | rest_param (',' optional_params)?
                   | optional_params

required_params    = required_param (',' required_param)*

required_param     = '*'? ident (':' type)?

rest_param         = '...' ident (':' type)? ('=' expr)?

optional_params    = optional_param (',' optional_param)*

optional_param     = '*'? ident (':' type)? '=' expr

stmt               = label
                   | decl
                   | complex_expr

complex_expr       = block_expr
                   | control_flow_expr
                   | assignment_expr
                   | update_expr
                   | expr

label              = ident ++ ':' stmt

block_expr         = 'block' block

control_flow_expr  = loop_expr
                   | if_expr
                   | compile_time_if
                   | switch_expr
                   | while_expr
                   | do_expr
                   | for_in_expr
                   | for_expr
                   | break_expr
                   | continue_expr
                   | fallthrough_expr
                   | return_expr
                   | goto_expr

compile_time_decl  = '@const' cells

const_decl         = 'const' cells

variable_decl      = 'var' cells

cells              = cells (',' cells)*

cell               = (ident size? (':' type)? ('=' expr)?) (',')

size               = ?{is_lower_bargle} ++ '[' positive_integer? ']'

assignment         = lvalues '=' exprs

lvalues            = lvalue (',' lvalue)* (',' rest_value)?

exprs              = expr (',' expr)*

update             = lvalue update_op expr

update_op          = "+="
                   | "-="
                   | "*="
                   | "/="
                   | "%="

lvalue             = ident (++ lexpr)*

lexpr              = '[' slice ']'
                   | ?{!is_lower_bargle} '.' ident

rest_value         = '...' ++ lvalue

block_expr         = 'block' block

block              = '{' stmt* '}'

loop_expr          = 'loop' block

if_expr            = 'if' block ('elif' block)* ('else' block)?

compile_time_if    = '@if' block ('@elif' block)* ('@else' block)?

switch_expr        = 'switch' expr? '{' (test_case ':' case_stmt)+  '}'

test_case          = 'case' expr (',' expr)*
                   | 'default'

case_stmt          = stmt* 'fallthrough'?

while_expr         = ('while' | 'until') expr block

do_expr            = 'do' block ('while' | 'until') expr

for_in_expr        = 'for' ident (',' ident)* 'in' expr block

for_expr           = 'for' init_expr? ';' expr? ';' update_expr? block

init_expr          = var_decl
                   | assignment_expr

break_expr         = 'break' ident? ('with' expr)?

continue_expr      = 'continue' ident? ('with' expr)?

return_expr        = 'return' expr?

goto_expr          = 'goto' ident ('with' expr)?

#
# Type declarations
#

type_declaration   = type_decl
                   | alias_decl
                   | enum_decl
                   | tuple_decl
                   | struct_decl
                   | class_decl
                   | interface_decl

type_decl          = 'type' ident '=' type

alias_decl         = 'alias' ident = ident

tuple_decl         = 'tuple' ident tuple_type

struct_decl        = 'struct' ident struct_type

enum_decl          = 'enum' ident '{' ( unassigned_enums | assigned_enums) '}'

unassigned_enums   = ident (',' ident)* ','?

assigned_enums     = ident '=' (string | number | ident) \
                     (',' ident '=' (string | number | ident))* ','?

# TODO: Is this the best way to declare the fields (slots) of an object?
#       Right now I'm picturing `class Foo { foo: string }` where `foo`
#       is an attribute of `Foo`. Attributes would desugar to a pair of
#       (possibly automatically generated) accessor methods.
# TODO: Should a method be declared with `fn foo(self, ...)`,
#       `foo: fn(self, ...)`, `method foo(self, ...)` or something else?
# TODO: Can classes or interfaces declare constants or nested types, or just
#       slots and methods?
class_decl         = 'class' \
                     ident \
                     ++super_classes? \
                     '{' \
                     named_type* \
                     function_decl \
                     '}'

super_classes      = '(' ident (',' ident)* ','? ')'

# TODO: Can interfaces have attributes?
interface_decl     = 'interface' ident '{' function_decl '}'

#
# Type (values, not declarations)
#

type               = ?{is_lower_bargle} lower_type
                   | ?{!is_lower_bargle} upper_type

lower_type         = pointer? size?

pointer            = 'pointer'

size               = ++ '[' positive_integer? ']'

upper_type         = union_type
                   | tuple_type
                   | struct_type

union_type         = simple_type size? (++ '?') ('|' simple_type size? (++ '?'))*

simple_type        = basic_type
                   | array_type
                   | map_type
                   | set_type
                   | tuple_type
                   | function_type

basic_type         = type_keyword
                   | ident

type_keyword       = 'any'
                   | 'bool'
                   | 'number'
                   | 'string'
                   | 'null'
                   | 'value'  # a JSON value
                   | 'i8'
                   | 'i16'
                   | 'i32'
                   | 'i64'
                   | 'u8'
                   | 'u16'
                   | 'u32'
                   | 'u64'
                   | 'f32'
                   | 'f64'

function_type      = 'fn' ++ signature

array_type         = '[' upper_type ']'

map_type           = '{:' upper_type '}'

set_type           = '{' upper_type '}'

tuple_type         = '<' upper_type (',' upper_type)* ',' '>'

struct_type        = '{' named_type (',' named_type)* ',' '}'

named_type         = ident ':' upper_type? ('=' expr)?

#
# "Expressions"
#
# There are three kinds of expressions: unary, binary, and "primary";
# and only two precedence levels. Primary expressions (like identifiers,
# function calls and index and field lookups) have the highest priority, and
# are evaluated from left to right. All of the other operators are required
# to be either commutative or to only work on primary expressions; that way
# there is no question of the relative precedence of the operators.

expr               = add_expr
                   | mul_expr
                   | and_expr
                   | or_expr
                   | binary_expr
                   | not_expr
                   | conditional_expr
                   | unary_expr
                   | primary_expr

add_expr           = primary_expr ('+' primary_expr)+

mul_expr           = primary_expr ('*' primary_expr)+

and_expr           = primary_expr (and_op primary_expr)+

and_op             = 'and'
                   | ?{allow_reserved} '&&'
                   | ?{allow_reserved} '/\\'
                   | ?{allow_reserved} '\u2227'  # Unicode LOGICAL AND

or_expr            = primary_expr (or_op primary_expr)+

or_op              = 'or'
                   | ?{allow_reserved} '||'
                   | ?{allow_reserved} '\/'
                   | ?{allow_reserved} '\u2228'  # Unicode LOGICAL OR

binary_expr        = primary_expr bin_op primary_expr

bin_op             = '/'       # divided by
                   | '-'       # minus
                   | '%'       # modulo
                   | '<='      # is less than or equal to
                   | '<'       # is less than
                   | '=='      # is equal to
                   | '!='      # is not equal to
                   | '>='      # is greater than or equal to
                   | '>'       # is greater than
                   | '.<.'     # bitwise left shift
                   | '.>.'     # bitwise right shift (sign extended)
                   | '.&.'     # bitwise and
                   | '.|.'     # bitwise or
                   | '.^.'     # bitwise exclusive-or

unary_expr         = unary_op ++ primary_expr

unary_op           = '-'       # `-x` is equivalent to `0 - x`
                   | '+'       # `+x` is equivalent to `x` (i.e., a no-op)
                   | '&'       # address of lvalue
                   | '*'       # value at (dereferencing an lvalue)
                   | not_op

not_op             = 'not '    # Note that the space is required
                   | '!'
                   | ?{allow_reserved} '\u00ac'  # NOT SIGN

conditional_expr   = primary_expr '?' primary_expr ':' primary_expr

primary_expr       = null
                   | boolean
                   | number
                   | string
                   | array
                   | map
                   | set
                   | tuple
                   | fn_expr
                   | compound_expr
                   | parenthesized_expr

parenthesized_expr = '(' expr ')'

null               = 'null'

boolean            = 'true'
                   | 'false'

#
# Complex literal expressions
#
# "tags" can sometimes precede strings and complex literals. A tag
# gets mapped onto a function that is immediately invoked with the
# value of the literal; if possible, the function may be evaluated at
# compile time. For now, only a few reserved tags are allowed, but
# it's possible in the future any identifier that isn't reserved will
# be allowed.

tag                = reserved_tag
                   | ?{allow_reserved} !keyword ident

# Each tags may only make sense in front of certain types of literals,
# but they are reserved in front of every literal. See the definitions
# of each type of tagged literal below for what each does.
reserved_tag       = 'r'     # for raw strings
                   | 's'     # for string lists
                   | 'byte'  # for byte strings and byte arrays
                   | 'x'     # for hex strings
                   | 'b64'   # for base64-encoded strings

array              = byte_array
                   | string_list
                   | tagged_array

# A byte array is an array literal of expressions where each expression must
# evaluate to a number between 0 and 255; it is then treated as an array
# of bytes, e.g., '[u8]' and must be stored in a single contiguous block.
# This is one of four ways of directly representing a series of bytes;
# the others are byte-strings, x-strings, and b64-strings.

byte_array         = 'byte[' expr (',' expr)* ','? ']'
                   | 'byte[]'

# A string list is an array of expressions that evaluate to strings that are
# concatenated together into a single string. These are most often used
# to specify multi-line string literals where lines contain trailing whitespace,
# but may occasionally be useful in other contexts.
string_list        = 's[' expr (',' expr)* ','? ']'
                   | 's[]'

tagged_array       = (tag ++)? '[' expr (',' expr)* ','? ']'
                   | (tag ++)? '[]'

# There are currently no reserved tags that apply to maps, sets, or tuples.

map                = (tag ++)? '{' kv (',' kv)* ',' '}'
                   | (tag ++)? '{:}'

kv                 = (string | ident) ':' expr

set                = (tag ++)? '{' expr (',' expr)* ',' '}'
                   | (tag ++)? '{}'

tuple              = (tag ++)? '<' expr (',' expr)* ',' '>'

# TODO: Is this the best we can do for a lightweight function syntax that
# isn't ambiguous in some cases depending on the value of `expr`?
fn_expr            = '(fn(' signature (expr | block) ')'

compound_expr      = compound_ident
                   | compound_string
                   | compound_array
                   | compound_map
                   | compound_tuple
                   | compound_fn_call

compound_ident     = ident (++ post_expr)*

# Lower Bargle doesn't support slices, only indices

compound_string    = ?{is_lower_bargle} string (++ index_expr)?
                   | ?{!is_lower_bargle} string (++ slice_expr)?

compound_array     = ?{is_lower_bargle} array (++ index_expr)?
                   | ?{!is_lower_bargle} (++ slice_expr (++ post_expr)*)?

compound_map       = map (++ index_expr (++ post_expr)*)?

compound_fn_call   = fn_expr (++ call_expr (++ post_expr)*)?

# Lower Bargle does not support objects or structures, so field references
# aren't allowed.
post_expr          = call_expr
                   | slice_expr
                   | index_expr
                   | ?{!is_lower_bargle} field_expr

call_expr          = '(' args ')'

args               = named_args
                   | mixed_args
                   | rest_args

named_args         = named_arg (',' named_arg)* ','?

mixed_args         = positional_args (',' rest_arg)? (',' ws named_arg)* ','?

positional_args    = arg (',' arg)*

rest_args          = rest_arg (',' ws named_args)* ','?

arg                = expr

named_arg         = ident ++ '=' ++ expr

rest_arg          = '...' ++ expr

slice_expr         = '[' expr ':' expr ']'

index_expr         = '[' expr ']'

field_expr         = '.' ++ ident

%
% TOKENS
%

sp                 = / \t\r\n/
                   | ?{allow_reserved} ('\f' | '\v' | '\u2028' | '\u2029')

ws                 = sp+

eol                = '\r\n' | '\r' | '\n'

line_comment       = ('#' | '//') ...(eol|end)

nested_comment     = '/*' (nested_comment | (!'*/' any))* '*/'

# Lower Bargle doesn't support floats, rationals, or tagged numbers

number             = hex_literal
                   | binary_literal
                   | ?{allow_reserved} octal_literal
                   | ?{is_lower_bargle} nn_integer
                   | ?{!is_lower_bargle} float_keyword
                   | ?{!is_lower_bargle} float

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

float              = nn_integer frac? exp? ![eE] tag?

frac               = '.' digit digit_sep*

exp                = [eE] ('-' | '+')? positive_integer

# non-negative integer
nn_integer         = '0'
                   | positive_integer

positive_integer   = nonzerodigit digit_sep*

digit_sep          = '_'? digit

nonzerodigit       = [1-9]

digit              = [0-9]

# Bargle supports two classes of strings: single-line and multiple line
# strings. Both may start with an optional tag, and then single-line
# strings must start with either a single apostrophe or a single
# double-quote. Multi-line strings must start with either a single
# backquote, or 3 or more apostrophes, double quotes, or backquotes.
# Multi-line strings handle embedded whitespace specially, with the
# treatment varying based on the kind of string. Nothing says that a
# multi-line string has to actually span multiple lines, though.

string             = raw_string
                   | byte_string
                   | x_string
                   | b64_string
                   | tagged_string
                   | custom_string

# "Raw strings" do not support interpolation or escape sequences. A raw string
# may contain the starting quote if it is preceded by a backslash, but
# both the backslash and the quote will be part of the result. A raw string
# may not end in a backslash. This matches what Python does.
raw_string         = single_line_raw_string
                   | multi_line_raw_string

single_line_raw_string = 'r' (squote | dquote):q (bslash q | !q !eol any)* q

multi_line_raw_string = 'r' mquote:q (bslash q | !q any)* q

# "Byte strings" contain a sequence of code points and escape sequences
# that are in the range of 0-255. The parser treats them as a byte literal.
# Any non-printable characters other than ' ', '\r', and '\n' must be escaped.
# End-of-lines are normalized to just be a newline; if you want to actually
# embed a carriage return in a string you must escape it.
byte_string        = single_line_byte_string |
                   | multi_line_byte_string

single_line_byte_string = 'byte' ++ (squote | dquote):q no_dedent? byte_char* q

multi_line_byte_string = 'byte' ++ mquote:q no_dedent? (byte_char | eol)* q

# If a unicode escape is used, it must be in the range U+0000 .. U+00FF.
byte_char          = standard_escape
                   | hex_escape
                   | ?{allow_unicode_escapes} unicode_escape
                   | [\x20-\x7E]
                   | [\xA1-\xAC]
                   | [\xB0-\xFF]

# "X strings" are sequences of two hex digits optionally surrounded
# by whitespace. The whitespace is removed from the string and then
# each hex pair is converted into the equivalent single byte value.

x_string           = 'x' mquote (sp | hex hex)* mquote

# "B64 strings" contain one or more sequences of specific characters optionally
# separated by whitespace. The whitespace is removed from the string and then
# treated as base64-encoded data as per RFC 4648 (using either the "base64"
# encoding or the "base64url" encoding), decoded, and treated as a byte
# literal. Padding is optional; if it is missing and necessary, the parser
# will append it in order to form a proper sequence.

b64_string         = 'b64' mquote ((b64char*) | (b64url_char*)) padding? mquote

b64_char           = [A-Za-z0-9] | '+' | '/'

b64url_char        = [A-Za-z0-9] | '-' | '_'

padding            = '='*

tagged_string      = string_tag? single_line_string
                   | string_tag? multi_line_string

single_line_string = (squote | dquote):q \
                     (bslash escape | '${' expr '}' | (!q !eol any))* \
                     q

# A multi-line string starts with either a single backquote or 3 or more
# quotes (single, double, or back) in a row. Multi-line can be used to
# embed any number of quotes in a row in a string as long as there are
# fewer than the number at the start. Note that this effectively means that
# a long string can contain *anything* as long as it starts with more quotes
# in a row than are found in the string.
multi_line_string  = mquote:q \
                     no_dedent? \
                     (bslash escape | '${' expr '}' | !q any)* \
                     q

# If the first characters of a raw, tagged, or custom string consist
# of a backslash followed by the end of a line, then the normal dedenting
# rules for a string will be turned off and any leading whitespace on a
# line will be included in the string. Not that trailing whitespace is
# *always* stripped from a string literal, so if you need to have trailing
# whitespace in a multi-line string you must compose it using string lists
# and single-line strings.
no_dedent          = bslash eol

# Custom strings allow you to control the delimiters used for interpolation.
# Normally you use `${foo}`, but with a custom string you use more than one
# `$` on each side of the expression, e.g. `$$${foo}$$$`.
custom_string      = tag? \
                     '$'{2,}:i mquote:q \
                     no_dedent? \
                     (bslash escape | i '{' expr '}' i | !q any)* \
                     q

bslash             = '\x5C'  # \ (backslash)

mquote             = squote{3,}
                   | dquote{3,}
                   | bquote{3,}
                   | bquote

squote             = '\u0027'   # ' APOSTROPHE (aka single quote)

dquote             = '\u0022'   # " QUOTATION MARK (aka double quote)

bquote             = '\u0060'   # ` GRAVE ACCENT (aka backquote)

escape             = standard_escape
                   | hex_escape
                   | ?{allow_reserved} octal_escape
                   | ?{allow_unicode_escapes} unicode_escape
                   | ?{allow_unicode_names} unicode_name

standard_escape    = 'n'        # \x0A, i.e. LINE FEED (aka LF)
                   | 'r'        # \x0D, i.e. CARRIAGE RETURN (aka CR)
                   | 't'        # \x09, CHARACTER TABULATION (aka tab)
                   | ?{allow_reserved} 'a'  # \x07 (bell)
                   | ?{allow_reserved} 'b'  # \x08 (backspace)
                   | ?{allow_reserved} 'f'  # \x0C (form feed)
                   | ?{allow_reserved} 'v'  # \x0B (vertical tab)
                   | squote
                   | dquote
                   | bquote
                   | '$'
                   | bslash

hex_escape         = 'x' hex{2}
                   | 'x{' hex+ '}'

octal_escape       = 'o' oct{3}

unicode_escape     = 'u' hex{4}
                   | 'U' hex{8}
                   | 'u{' hex+ '}'

# This is the syntax for a Unicode character name as of Unicode 18.
# (https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-4/#G2082)
# A unicode character name is, roughly, a series of upper case words separated
# by spaces or hyphens (although digits are allowed as anything other than the
# first character in a word).
unicode_name       = 'N{' <unicode_word (' ' unicode_word)*> '}'

unicode_word       = [A-Z] ([A-Z0-9]* ('-' [A-Z0-9]+))*

ident              = !keyword ascii_ident
                   | !keyword ?{allow_reserved} unicode_ident

keyword            = 'null'
                   | 'true'
                   | 'false'
                   | 'nan'
                   | 'infinity'
                   | ?{!allow_keywords_as_identifiers} other_keywords

other_keywords     = type_keyword
                   | existing_keywords
                   | reserved_keywords

existing_keywords  = 'and'
                   | 'alias'
                   | 'assert'
                   | 'block'
                   | 'break'
                   | 'case'
                   | 'class'
                   | 'continue'
                   | 'default'
                   | 'do'
                   | 'elif'
                   | 'else'
                   | 'fallthrough'
                   | 'fn'
                   | 'for'
                   | 'goto'
                   | 'if'
                   | 'import'
                   | 'in'
                   | 'loop'
                   | 'not'
                   | 'or'
                   | 'pointer'
                   | 'return'
                   | 'switch'
                   | 'type'
                   | 'until'
                   | 'var'
                   | 'while'

reserved_keywords  = 'ensure'
                   | 'pre'
                   | 'post'


keyword          = 'null'
# An ASCII identifier is an ascii letter or an underscore followed by
# zero or more ascii letters, digits, or underscores.
ascii_ident      = [_a-zA-Z] [_a-zA-Z0-9]*

# This is a simplified subset of the actual definition of a Unicode identifier
# as specified in https://www.unicode.org/reports/tr31/. The general intent
# is the same: a letter (or underscore) followed by zero or more letters,
# underscores, or numbers. However, this does not allow non-spacing marks,
# spacing combining marks, or other forms of punctuation that the standard
# does.
unicode_ident    = id_start id_continue*

id_start         = \p{L} | '_'

id_continue      = id_start | \p{N}

