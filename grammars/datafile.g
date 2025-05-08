%whitespace  = [ \n\r\t]+

%comment     = ('#'|'//') ^eol*
             | '/*' ^.'*/'

%tokens      = number | str | raw_str | bare_word | numword | eol

// allow_trailing is used to indicate whether parsing should stop
// once a value (and any trailing filler) has been reached; by default
// it is false, and it is an error for there to be any trailing non-filler
// characters before the end of the string. If allow_trailing is set
// to true, parsing stops without error ifa trailing character is reached.
%externs     = allow_trailing                         -> false
             | allow_numwords                         -> false
             | unicode                                -> true
             | unicode_names                          -> true

grammar      = value %filler trailing?                -> $1
             | member+ %filler trailing?              -> ['object', '', $1]

trailing     = ?{!allow_trailing} end

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
             | bare_word                              -> ['string', '', $1]

string_list  = string_tag
               '(' string (','? string)* ')'          -> ['string_list', $1,
                                                          scons($3, $4)]
raw_str_tag  = ('r' | 'rd' | 'dr')
                 ~(%whitespace | %comment)            -> $1

string_tag   = ('d' | tag) ~(%whitespace | %comment)  -> $1

tag          = bare_word
             |                                        -> ''

bare_word    = ~('true' | 'false' | 'null' | number)
               <(^(punct | %whitespace))+>

numword      = <number (^(punct | %whitespace))+>     -> ['numword', '', $1]

raw_str      = tsq <(^tsq)*> tsq                      -> $2
             | tdq <(^tdq)*> tdq                      -> $2
             | tbq <(^tbq)*> tbq                      -> $2
             | sq <(^sq)*> sq                         -> $2
             | dq <(^dq)*> dq                         -> $2
             | bq <(^bq)*> bq                         -> $2
             | 'L' <sq '='+ sq>:lq
               <(^(={lq}))*> ={lq}                    -> $3
             | '[' '='+:eqs '['
               <(^(']' ={eqs} ']'))*>:s
               ']' ={eqs} ']'                         -> s

str          = tsq <(~tsq bchar)*> tsq                -> $2
             | tdq <(~tdq bchar)*> tdq                -> $2
             | tbq <(~tbq bchar)*> tbq                -> $2
             | sq <(~sq bchar)*> sq                   -> $2
             | dq <(~dq bchar)*> dq                   -> $2
             | bq <(~bq bchar)*> bq                   -> $2
             | 'L' <sq '='+ sq>:lq
               <(~(={lq}) bchar)*> ={lq}              -> $3
             | '[' '='+:eqs '['
               <(~(']' ={eqs} ']') bchar)*>:s
               ']' ={eqs} ']'                         -> s

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
