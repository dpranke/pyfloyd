# Grammar

This document describes the syntax for a Floyd grammar. Floyd grammars
are based on Parsing Expression Grammars, and both left-recursive and
expression grammars are supported.

A Floyd grammar looks like this:

```
grammar = foo bar end

foo     = 'foo'*

bar     = 'bar'
```

That grammar will match any string that contains any number of 'foo's and
then ends in 'bar'

## Syntax

Here are the basic rules:

1. Grammars area list of one or more rules. A rule follows the format
   `rulename '=' expr`.

2. Rule names are identifiers, where identifiers are defined as they
   are in JavaScript: roughly they start with a letter, an underscore ('_'),
   a percent sign ('%'), or a dollar sign ('$'), followed by more of
   those or digits. Identifiers starting with an underscore, a percent
   sign, or a dollar sign are reserved for the parser, so a user's
   identifier has to start with a letter.

3. Rules are combinations of *terms* and *operators*. A term can be thought
   of as identifier or a literal preceded and followed by zero or more
   operators; terms usually have no whitespace in them unless they are
   surrounded by parens. The names for the rules have no particular meaning
   other than to give you something to refer to):

    * Any:        `any`
      Matches any single character.
    * *Literal:   '"'xyz'"' | "'"xyz "'"
      Matches the string inside the quotes. Escape sequences are allowed
      and work more-or-less as they do in JavaScript and Python.
      A string of length one is called a *character*. A character may
      be any Unicode character.
    * Sequence:  `expr1 expr2 expr3...`
      Matches expr1 followed immediately by expr2 and then immediately
      expr3 and so on.
    * Choice:    `expr1 "|" expr2 "|" ...`
      Choices are called *ordered*. This means that the parser first tries
      to match expr1. If that succeeds, the parser stops further processing
      of the rule. If expr1 doesn't match, then the parser will try to
      match expr2, and so on.
    * Star:      `expr "*"`
      AKA repetition. Matches zero or more occurrences of expr.
    * Not:       "~" expr
      Matches if the next thing in the grammar does *not* match expr.
      This does not consume any input.
    * Empty:     ``
      Matches an empty string. This always succeeds.
    * Result:    '->' `host_expr` | '{' host_expr '}'
      Always succeeds and the expression returns the value of `host_expr`.
      Results are described below.
    * Pred:      '?(' host_expr ')' | '?{' host_expr '}'
      Succeeds when the host_expr evaluates to true. No input is consumed
      unless the host_expr explicitly consumes it.
    * Binding:   `expr ':' ident`
      Assigns the string matching expr to the variable <ident>, which
      can then be used in subsequent preds and results in the sequence.
    * Parens:    `'(' expr ')'`
      Matches the expression inside the parentheses as if it was a
      single term.
    * Runs: `'<' expr '>'`
      Matches expr and returns the string matched by `expr` as the result
      (see below for more on results). If the grammar has filler
      defined (see below), any filler at the beginning or the end
      of the rule is discarded.
    * Unicode-Category: `'\p{' ident '}.
      Match the next character in the string if it falls into the
      Unicode character category named `ident`.


There are additional operators that can be expressed in terms of the
primitives:

    * End:      `end`
      Matches the end of the string. Equivalent to `~any`.
    * Plus:     `expr '+'`.
      Equivalent to `expr expr '*'`
    * Optional: `expr '?'`
      Equivalent to `expr |` (empty)
    * Range:    `'X' .. 'Y'`
      Matches any character between X and Y (inclusive). Equivalent
      to `X | ... | Y`
    * Not-One: `'^' expr`
      Matches any character as long as it does not match expr.
      Equivalent to `~expr any`
    * Charset: `'[' c1c2c3c4... ']'
      Equivalent to: `c1 | c2 | c3 | c4 ...`
    * Not-charset:  `'[^' c1c2c3c4... ']'
      Equivalent to: `~( c1 | c2 | c3 | c4 ...) any`
    * Ends-In: `'^.' expr`
      Matches everything up to the first occurence of `expr`. Equivalent to
      `(^expr)* expr`. This can be called a *non-greedy* match.
    * Counted: `expr '{' number '}'`
      Matches <number> exprs in a row.
    * Counted-Range: `expr '{' number1 ',' number2 '}'`
      Matches between <number1> and <number2> exprs in a row (inclusive).

## Filler (whitespace and comments)

PEGs originally (and conventionally) don't distinguish between lexing
and parsing the way the combination of LEX and YACC do. Instead, they
are known as *scannerless* parsers, and handle both kinds of syntax
consistently at once. By default this means that if you want to have
whitespace or comments in your rules, you have to be explicit about
them:

```
grammar = ws 'foo'* ws 'bar' ws end
```

In Floyd, whitespace and comments are known as *filler*, and you can
use the `%whitespace` and `%comment` rules to define how
whitespace and comments are recognized. If either or both of those
rules are specified, then whitespace and comment rules will be
be inserted in front of every string literal and at the end of the
grammar (but before `end`, if the grammar ends in `end`), allowing
any combination of whitespace and comments in between the literals.

So, the above grammar could be equivalently specified as:

```
%whitespace = [ \n\r\t]*

grammar     = 'foo'* 'bar' end
```

If '%whitespace' is specified, then the parser will automatically
define a `_ws` rule that matches the same thing. Similarly, the
parser will define a '_comment' rules that matches comments.

Floyd grammars themselves use the following definitions of whitespace
and comments:

```
%whitespace  = [ \n\r\t]*

%comment     = ('#' | '//') ^('\n'|'\r')
             | '/*' ^. '*/'
```

In other words, they follow a normal kind of whitespace and support either
JavaScript-style or Python-style comments.

### Tokens

As described above, PEGs don't usually distinguish between token or terminal
rules and non-terminal rules. However, it can be useful to have some
rules that have automatic filler insert and others that don't.

If you define a rule with `%tokens = (a | b | c)` then the parser will
not automatically insert any filler before any literals in any sub-rule
of the a, b, or c rules. This makes it so that tokens can be described
using the same basic mechanism used for non-terminals.

## Results

Grammars can be written to either just match a string or to compute
and return a value. Values can be basically anything that can be
expressed as JSON, i.e., a bool, a null, a number, a string,
a list of values (i.e, an array) or a list of key/value pairs (i.e.,
an object).

Results are computed as follows:

    * The result of `any` is the character it matched.
    * The result of a string literal is that string.
    * The result of a sequence is the result of the last term in
      the sequence.
    * The result of a choice is the result of whichever term
      that was matched.
    * The result of a star expression is an array of the values of
      each expression. If the expression didn't match anything,
      the result is an empty array.
    * The result of a not-term is null.
    * The result of a result term (something that looks like `-> ...`
      or `{ ... }` is the value of the computed expression.
    * The result of a predicate term is null.
    * The result of a binding term is the result of the expr it is
      bound to; there is also the side effect that the value of the
      result may be referred to in predicate terms or result terms
      in the same sequence.
    * The result of a parenthesized expression is the result of the
      enclosed expression.
    * The result of a run is the string matched by the run, as described
      above.
    * The result of `end` is `null`.
    * The result of a plus term is the array of matched expressions.
    * The result of an optional term is an array with either zero
      or one values depending on whether the term didn't match or it did.
    * The result of a range is the character it matched.
    * The result of a not-one is the character it matched.
    * The result of a charset is the character it matched.
    * The result of an ends-in term is the result of the ending expression.
    * The result of a counted term or a counted-range term is an array of
      the N expressions it matched.
    * The result of a unicode category match is the character it matched.

The parser will automatically assign the value of each term in a sequence
to a variable starting with '$' and numbered according to the position in
the sequence, i.e., `$1`, `$2`, and so on. These variables are available in
for reference in pred and result terms.

So,

```
expr = left '+' right
```

is equivalent to

```
expr = left:$1 '+':$2 right:$3
```

If the grammar has filler defined, the filler terms are not assigned a
value and the parser effectively acts as if the terms had been renumbered

## The host language

Floyd grammars can compute *value*s using a simple expression language
called the *host* language.

A *value* is anything that can be expressed in JSON: null,
a boolean, a number, an array of values, or an object containing
key/value pairs.

The host language roughly follows this grammar and typing rules
(typing is explained in the next section):

```
expr  = expr:number '+' expr:number
      | expr:number '-' expr:number
      | expr:str '++' expr:str
      | '[' expr:type* ']: array[type...]'
      | '(' expr:value '): value'
      | expr '[' expr:(int|str) ']: type'
      | expr '(' exprs: [type*] '): type '
      | string
      | floating-point: number
      | hexadecimal: int
      | 'true':bool | 'false':bool | 'null':null
      | ident:value

exprs = expr? (',' expr)* ','?  -> cons($1, $2)
```

Expressions have the usual associativity and precedence. Identifiers
return the result of a bound expression using the same name in a sequence.
identifiers are only visible to terms in that sequence, and not to
an sub-terms, which have their own scopes.

### Types

The host language is statically typed, with the following kinds of types:

```
type  = null
      | bool
      | int
      | number
      | char
      | str
      | Value
      | [type*]
      | {str:type*}

Value = <a union of all of the types>
```

Because a Value is an encompassing all-purpose type (or an `any` type),
the language will often feel more like it is dynamically-typed.

A *char* is a string of length 1; A *str* contains any number of chars.

An *int* is a number with an integral value (i.e., no fractional or
exponent parts).

A *number* can have either an integral value or a floating-point value;
it could also be called a float.

Any type will be automatically promoted to a Value where needed.

The array operator takes a list of N values with types T1, T2, ... T_n and
returns an array value with types [T1, T2, ... T_n].

The subscript operator takes an array of values with types T1, T2, ... T_n
and returns element N with a type of T_n.

## Functions

### Builtin

The host language has the following built-in functions with the
given types (using Python's type annotation syntax):

    * `atoi(s:str): int`
      Returns the numeric (integral) equivalent of the string value
      where the string matches either a floating-point number or a
      hexadecimal number.

    * `atof(s:str): float`
      Returns the numeric equivalent of the string value, where the
      string matches either a floating-point number or a hexadecimal
      number.

    * `cat(ss:[str]): str`
      Returns the string produced by joining all of the elements of `ss`
      together with empty strings. Equivalent to `join('', ss)`.

    * `concat(x:[Value], y:[Value]): [Value]`
      Returns an array containing all of the elements of `x` followed by
      all of the elements of `y`.

    * `cons(head:Value, tail:[Value]): [Value]`
      Returns an array with `head` as the first element, followed by
      the elements from `tail`. Equivalent to `concat([head], tail)`.

    * `dict(d:[[key:str, value:Value]]): {[str: Value]*}`
      Returns the object that contains all the key/value pairs.

    * `float(i:int): float`
      Returns the floating point equivalent of the int `i`.

    * `hex(s:str): int`
      Returns the numeric equivalent of the string, where the string
      matches a hexadecimal number.

    * `int(f:float): int`
      Returns the integer equivalent of the floating point number.

    * `is_unicat(x:char, cat:str): bool`
      *Deprecated*. Returns true if `x` is a single character in the
      the Unicode category `cat`. You should match against a
      unicode-category expression instead.

    * `itou(i:int): char`
      Returns the unicode character with code point `x`.

    * `join(x:str, y:[str]): str`
      Returns the result of joining all the strings in y with the
      string in x in between them.

    * `scons(x:str, y:[str]): str`
      Returns the string produced by joining x and the result of `cat(y)`.
      This is equivalent to `join('', arrcat([x], y))`.

    * `strcat(x:str, y:str): str`
      Returns the string concatenation of `x` and `y`. Equivalent to
      `join('', [x, y])` or `cat(concat([x], [y]))`.

    * `utoi(x:char): int`
      Returns the Unicode code point value for `x`.

### Implementation-defined

Functions that have names beginning with an underscore are reserved for
the caller of the parser to define, e.g. `_dedent(s:str): str` is a
function called `_dedent` provided by the caller of the parser
that takes a string and returns a string.
