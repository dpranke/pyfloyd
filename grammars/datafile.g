# Copyright 2025 Dirk Pranke. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This grammar describes the "Floyd datafile" file format (also known
# as just "datafile" for short). The format is a strict superset of
# JSON, designed for human use with three things in mind:
# - Minimize punctuation whereever possible.
# - Support multiline strings as cleanly as possible.
# - Provide a mechanism for extensibility (via a 'tag' mechanism).
#
# For more details on the format, see docs/grammar.md.


%externs     = memoize                                -> true

%whitespace  = [ \n\r\t]+

%comment     = ('#'|'//') ^eol*
             | '/*' ^.'*/'

%tokens      = number | str | raw_str | bareword | numword | eol

// allow_trailing is used to indicate whether parsing should stop
// once a value (and any trailing filler) has been reached; by default
// it is false, and it is an error for there to be any trailing non-filler
// characters before the end of the string. If allow_trailing is set
// to true, parsing stops without error ifa trailing character is reached.
%externs     = allow_trailing                         -> false
             | allow_numwords                         -> false
             | unicode                                -> true
             | unicode_names                          -> true

grammar      = member+ %filler trailing               -> ['object', '', $1]
             | value %filler trailing                 -> $1

trailing     = ?{!allow_trailing} end
             | ?{allow_trailing}

eol          = '\r\n' | '\r' | '\n'

value        = 'true'                                 -> ['true', '', null]
             | 'false'                                -> ['false', '', null]
             | 'null'                                 -> ['null', '', null]
             | numword
             | <number>                               -> ['number', '', $1]
             | array
             | object
             | string

number       = '0b' bin ('_' bin | bin)*
             | '0o' oct ('_' oct | oct)*
             | '0x' hex ('_' hex | hex)*
             | ('-' | '+')? int frac? exp?

int          = '0'
             | nonzerodigit digit_sep

digit_sep    = ('_' digit | digit)*

digit        = [0-9]

nonzerodigit = [1-9]

frac         = '.' digit? digit_sep

exp          = ('e'|'E') ('+'|'-')? digit? digit_sep

bin          = [01]

oct          = [0-7]

hex          = [0-9a-fA-F]

// Raw strings differ from strings in that escape sequences are unrecognized;
// a raw string may contain anything between the starting and ending delimiter
// except for the delimiter itself. Strings have to be parsed separately
// from raw strings in order to not stop parsing when you hit the ending
// delimiter if it is immediately preceded by a backslash.

string       = raw_str_tag raw_str                    -> ['string', $1, $2]
             | string_tag str                         -> ['string', $1, $2]
             | string_list
             | bareword                               -> ['bareword', '', $1]

string_list  = string_tag
               '(' string (','? string)* ')'          -> ['string_list', $1,
                                                          cons($3, $4)]
raw_str_tag  = ('r' | 'ri' | 'ir')
                 ~(%whitespace | %comment)            -> $1

string_tag   = ('i' | tag) ~(%whitespace | %comment)  -> $1

tag          = bareword
             | %filler                                -> ''

bareword     = ~('true' | 'false' | 'null' | number)
               <(^(punct | %whitespace))+>

numword      = <number (^(punct | %whitespace))+>     -> ['numword', '', $1]

# The AST for a raw string or a string returns the text of the opening
# quote and the colno following the opening quote. The latter is used
# to be able to dedent multiline strings with text on the first line
# properly. The former isn't currently used but could be useful to
# round-trip the pretty-printed string properly.
raw_str      = tsq (-> colno()) <(^tsq)*> tsq         -> [$1, $2, $3]
             | tdq (-> colno()) <(^tdq)*> tdq         -> [$1, $2, $3]
             | tbq (-> colno()) <(^tbq)*> tbq         -> [$1, $2, $3]
             | sq  (-> colno()) <(^sq)*>  sq          -> [$1, $2, $3]
             | dq  (-> colno()) <(^dq)*>  dq          -> [$1, $2, $3]
             | bq  (-> colno()) <(^bq)*>  bq          -> [$1, $2, $3]
             | 'L'
               <sq '='+ sq>:lq
               (-> colno()):c
               <(^(={lq}))*>:s
               ={lq}
               ->                             [strcat('L', lq), c, s]

str          = tsq (-> colno()) <(~tsq bchar)*> tsq   -> [$1, $2, $3]
             | tdq (-> colno()) <(~tdq bchar)*> tdq   -> [$1, $2, $3]
             | tbq (-> colno()) <(~tbq bchar)*> tbq   -> [$1, $2, $3]
             | sq  (-> colno()) <(~sq bchar)*>  sq    -> [$1, $2, $3]
             | dq  (-> colno()) <(~dq bchar)*>  dq    -> [$1, $2, $3]
             | bq  (-> colno()) <(~bq bchar)*>  bq    -> [$1, $2, $3]
             | 'L'
               <sq '='+ sq>:lq
               (-> colno()):c
               <(~(={lq}) bchar)*>:s
               ={lq}
               ->                             [strcat('L', lq), c, s]

punct        = /(L'=+')|[\/#'"`\[\](){}:=,]/

sq           = "'"

dq           = '"'

bq           = "`"

tsq          = "'''"

tbq          = "```"

tdq          = '"""'

bchar        = bslash escape
             | any

bslash       = '\\'

escape       = bslash
             | [abfnrtv'"`]
             | oct{1,3}
             | 'x' hex{2}
             | ?{ unicode } 'u' hex{4}
             | ?{ unicode } 'U' hex{8}
             | ?{ unicode_names }
               'N{' /[A-Z][A-Z0-9]*(( [A-Z][A-Z0-9]*|(-[A-Z0-9]*)))*/ '}'

nchar        = [0-9A-Z -]

array        = array_tag '[' value? (','? value)* ','? ']' -> ['array', $1,
                                                               concat($3, $4)]

array_tag    = tag ~(%whitespace | %comment)          -> $1

object       = object_tag
               '{' member? (','? member)* ','? '}'    -> ['object', $1,
                                                          concat($3, $4)]

object_tag   = tag ~(%whitespace | %comment)          -> $1

member       = key (':'|'=') value                    -> [$1, $3]

key          = string
             | ?{ allow_numwords } numword
