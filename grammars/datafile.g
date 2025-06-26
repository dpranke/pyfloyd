// Copyright 2025 Dirk Pranke. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// This grammar describes the "Floyd datafile" file format (also known
// as just "datafile" for short). The format is a strict superset of
// JSON, designed for human use with three things in mind:
// - Minimize punctuation whereever possible.
// - Support multiline strings as cleanly as possible.
// - Provide a mechanism for extensibility (via "tags").
//
// For more details on the format, see docs/grammar.md.

%externs     = memoize                                -> true

%whitespace  = [ \n\r\t]+

%comment     = <('#'|'//') [^\r\n]* (end | '\r' '\n'? | '\n')>
             | <'/*' ^.'*/'>

%tokens      = string | number | bareword | numword

// `allow_trailing` is used to indicate whether parsing should stop
// once a value (and any trailing filler) has been reached; by default
// it is false, and it is an error for there to be any trailing non-filler
// characters before the end of the string. If allow_trailing is set
// to true, parsing stops without error ifa trailing character is reached.
//
// `allow_numwords` is used to indicate whether "numwords" should be allowed;
// a "numword" is a string of characters that begins with a number. They
// are not allowed by default as it's easy for them to be used by accident.
//
// `unicode` indicates whether unicode escapes should be allowed. Nearly
// every environment is likely to support them. `unicode_names` indicates
// whether unicode names should be allowed. Fewer environments will support
// these, as they require you to have access to the list of legal unicode
// names.
%externs     = allow_trailing                         -> false
             | allow_numwords                         -> false
             | unicode                                -> true
             | unicode_names                          -> true

grammar      = member+ %filler trailing               -> ['object', '', $1]
             | value %filler trailing                 -> $1

nofiller     = ~(%whitespace | %comment)

trailing     = ?{!allow_trailing} end
             | ?{allow_trailing}

eol          = '\r\n' | '\r' | '\n'

value        = string                                 -> ['string', $1, []]
             | object
             | array
             | 'true'                                 -> ['true', true, []]
             | 'false'                                -> ['false', false, []]
             | 'null'                                 -> ['null', null, []]
             | ?{allow_numwords} numword              -> ['numword', $2, []]
             | number                                 -> ['number', $1, []]
             | bareword                               -> ['bareword', $1, []]

string       = string_tag
               nofiller
               quote:q
               (-> colno())
               <(('\\' any) | ~(={q}) any)*>
               ={q}                                   -> [$1, q, $4, $5]

// Only the 'r' and 'i' tags and their combinations are guaranteed to be
// supported in every environment, as they can be directly represented in
// JSON. 'x' and 'b64' are reserved and may be supported in some environments.
string_tag   = 'r' | 'i' | 'ri' | 'ir'
             | 'x' | 'b64' | <tag?>

tag          = bareword
             |

quote        = "'''" | "'" | '"""'
             | '"' | '```' | '`'
             | 'L' <"'" '='+ "'">                     -> $2

numword      = <number (^(punct | %whitespace))+>

number       = <'0b' bin ('_' bin | bin)*>
             | <'0o' oct ('_' oct | oct)*>
             | <'0x' hex ('_' hex | hex)*>
             | <('-' | '+')? int frac? exp?>

bareword     = ~('true' | 'false' | 'null' | number)
               <(^(punct | %whitespace))+>

punct        = /(L'=+')|[\\\/#'"`\[\](){}:=,]/

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

// These rules are not actually used directly in the grammar, as
// string decoding is done via a fast built-in function, but they
// represent the syntax that is legal.
bchar        = '\\' escape
             | any

escape       = [\\abfnrtv'"`]
             | oct{1,3}
             | 'x' hex{1,2}
             | ?{unicode} 'u' hex{1,8}
             | ?{unicode_names} 'N{' unicode_name '}'

unicode_name = /[A-Z][A-Z0-9]*([ -][A-Z][A-Z0-9]*)*/

array        = array_tag
               nofiller
               '['
               value?
               (','? value)*
               ','?
               ']'
               -> ['array', $1, concat($4, $5)]
             | array_tag
               nofiller
               '('
               value?
               (','? value)*
               ','?
               ')'
               -> ['array', $1, concat($4, $5)]

// Only the 's' tag is guaranteed to be supported in every environment, as
// it is the only one that be directly translated to a JSON value. The others
// are reserved and may be supported in certain environments; if they aren't,
// using them will raise an error.
array_tag    = 's'    // string list
             | 'b'    // bytes
             | 'q'    // quote
             | 'qq'   // quasiquote
             | 'uq'   // unquote
             | 'us'   // unquote-splice
             | <tag?>

object       = object_tag
               nofiller
               '{'
               member?
               (','? member)*
               ','?
               '}'
               -> ['object', $1, concat($4, $5)]

object_tag   = <tag?>                                 -> $1

member       = key (':'|'=') value                    -> [$1, $3]

key          = string                                 -> ['string', $1, []]
             | bareword                               -> ['bareword', $1, []]
             | ?{ allow_numwords } numword            -> ['numword', $1, []]
