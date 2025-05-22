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

# This grammar describes a subset of the "at-exp" syntax used by the Scribble
# dialect of the Racket programming language. It is used to generate
# text and is designed to easily intermix text and programming constructs,
# where the text is more common than the programming constructs. This makes
# this a good simple language for templating.
#
# The basic idea is that text is output verbatim, except when an `@`
# is encountered. You then get an expression of the form `@id[x y]{z w}`,
# where all three parts are optional. That evaluates to the equivalent
# Lisp function `(id x y "z w")`. The brace-bracketed part can include
# nested @-exps, and id, x, and y are all valid Lisp expressions.
#
# See https://docs.racket-lang.org/scribble/reader.html for more.
#
# Only the subset of the at-exp syntax that is needed by the Floyd templates
# is currently implemented. There is one significant difference between
# the Scribble implementation and the Floyd implementation, which is that
# in Scribble, if the id part is omitted, it defaults to 'list'. In
# Floyd, it defaults to defining a lambda where the [] part lists the
# parameters to the lambda and the {} is the body of the lambda. This
# difference, however, is implemented outside of the parser.

%externs = allow_trailing                  -> false

grammar = term* opt_end                    -> $1

term    = '@' at_expr
        | '\n'
        | /[^@\n]+/

opt_end = ?{allow_trailing}
        | end

ws      =  /[ \t\n]+/

at_expr = opt_id list braces               -> concat(cons($1, $2), [$3])
        | opt_id list                      -> cons($1, $2)
        | opt_id braces                    -> [$1, $2]
        | id                               -> $1
        | string                           -> $1

opt_id  = id
        |                                  -> ['symbol', 'fn']

id      = /[a-zA-Z_][\.a-zA-Z0-9_]*/       -> ['symbol', $1]

expr    = id
        | 'true'                           -> true
        | 'false'                          -> false
        | number
        | string
        | list

number  = '0'                              -> 0
        | /[1-9][0-9]*/                    -> atoi($1, 10)

string  = '"' dqch* '"'                    -> join('', $2)
        | "'" sqch* "'"                    -> join('', $2)

dqch    = '\\"'                            -> '"'
        | [^"]

sqch    = "\\'"                            -> "'"
        | [^']

list = '[' ws? expr (ws expr)* ws? ']'     -> cons($3, $4)
        | '[' ws? ']'                      -> []

braces   = '{' <(^'}')*> '}'               -> $2
