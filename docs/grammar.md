# Grammar

This document describes the syntax for a Floyd grammar. Floyd grammars
are based on Parsing Expression Grammars, with both left-recursive and
expression grammars are supported.

A Floyd grammar looks like this:

```
grammar = foo bar end

foo     = 'foo'*

bar     = 'bar'
```

That grammar will match a string that contains any number of 'foo's and
then ends in 'bar'.

## Syntax

Here are the basic rules:

1.  Grammars are a list of one or more rules. A rule follows the format
    `rulename '=' expr`. Unless otherwise specified, parsing will begin
    with the first rule in the list (skipping over `%whitespace` and
    `%comment`, if they are present).

2.  Rule names are identifiers, where identifiers are defined as they
    are in JavaScript: roughly, they start with a letter, an underscore ('_'),
    a percent sign ('%'), or a dollar sign ('$'), followed by more of
    those or digits. Identifiers starting with an underscore, a percent
    sign, or a dollar sign are reserved for the parser, so a user's
    identifier has to start with a letter.

3.  Rules are combinations of *terms* and *operators*. A term can be thought
    of as identifier or a literal preceded and followed by zero or more
    operators; terms usually have no whitespace in them unless they are
    surrounded by parens. The names for the rules have no particular meaning
    other than to give us something to refer to.

    The basic rules work as follows:

    * Any:        `any`<br>
      Matches any single character.

    * Literal:   `'xyz' | "xyz"`<br>
      Matches the string inside the quotes. Escape sequences are allowed
      and work more-or-less as they do in JavaScript and Python.
      A string of length one is called a *character*. A character may
      be any Unicode character.

    * Sequence:  `expr1 expr2 expr3...`<br>
      Matches `expr1` followed immediately by `expr2` and then immediately
      `expr3` and so on.

    * Choice:    `expr1 "|" expr2 "|" ...`<br>
      Choices are called *ordered*. This means that the parser first tries
      to match `expr1`. If that succeeds, the parser stops further processing
      of the rule. If `expr1` doesn't match, then the parser will try to
      match `expr2`, and so on.

    * Star:      `expr "*"`<br>
      AKA repetition. Matches zero or more occurrences of `expr`.

    * Not:       `"~" expr`<br>
      Matches if the next thing in the grammar does *not* match `expr`.
      This does not consume any input.

    * Empty:<br>
      Matches an empty string. This always succeeds.

    * Result:    `'->' `result_expr` | '{' result_expr '}'`<br>
      Always succeeds and the expression returns the value of `result_expr`.
      Results (or result expressions) are described below.

    * Pred:      `'?(' result_expr ')' | '?{' result_expr '}'`<br>
      Succeeds when the `result_expr` evaluates to true. No input is consumed
      unless the `result_expr` explicitly consumes it.

    * Binding:   `expr ':' ident`<br>
      Assigns the string matching `expr` to the variable `ident`, which
      can then be used in subsequent preds and results terms in the 
      same sequence that the binding happens in.

    * Parens:    `'(' expr ')'`<br>
      Matches the expression inside the parentheses as if it was a
      single term.

    * Runs: `'<' expr '>'`<br>
      Matches `expr` and returns the string matched by `expr` as the result
      (see below for more on results). If the grammar has filler
      defined (see below), any filler at the beginning or the end
      of the rule is discarded.

    * Unicode-Category: `'\p{' ident '}`<br>
      Match the next character in the string if it falls into the
      Unicode character category named `ident`.

4.  There are additional operators that can be expressed in terms of the
    primitives:

    * End:      `end`<br>
      Matches the end of the string. Equivalent to `~any`.

    * Plus:     `expr '+'`<br>
      Equivalent to `expr expr '*'`

    * Optional: `expr '?'`<br>
      Equivalent to `expr |` (empty)

    * Range:    `'X' .. 'Y'`<br>
      Matches any character between X and Y (inclusive), where Y has a
      greater code point than X. Equivalent to `'(' X '|' ... '|' Y ')'`.

    * Not-One: `'^' expr`<br>
      Matches any character as long as it does not match `expr`.
      Equivalent to `~expr any`.

    * Set: `'[' c1c2c3c4... ']'`<br>
      Matches any of a set of characters, where `c1` ... `c_n` are 
      either single characters, or two characters separated by a dash.
      characters, optionally separated by '-'. Equivalent to: 
      `c1 | c2 | c3 | c4 ...` where `c1` is either a single character
      or the range of characters from `'c1'..'c2'` (inclusive), where
      c2 has a greater code point value than c1. Each `c` may be an
      escape sequence. To match against '-', it should be either the
      first or the last character in the set, or you can match against
      '\\-'. To match against ']', use an escaped version ('\\]').

    * Not-set:  `'[^' c1c2c3c4... ']'`<br>
      Matches anything not in the set of characters (using the same 
      syntax and semantics as Set, above). Equivalent to:
      `~( c1 | c2 | c3 | c4 ...) any`.

    * Ends-In: `'^.' expr`<br>
      Matches everything up to the first occurrence of `expr`. Equivalent to
      `(^expr)* expr`. This can be called a *non-greedy* match.

    * Count: `expr '{' (n | n1 ',' n2) '}'`<br>
      The first form matches `n` `expr`s in a row, where `n` is a 
      non-negative integer. The second form matches from `n1` to `n2`
      `expr`s (inclusive) in a row where n1 and n2 are both non-negative
      integers and `n2` >= `n1`.

## Filler (whitespace and comments)

PEGs originally (and conventionally) don't distinguish between lexing and
parsing the way compilers like the combination of LEX and YACC do.  Instead,
they are known as *scannerless* parsers, and handle both kinds of syntax
consistently at once. By default this means that if you want to have whitespace
or comments in your rules, you have to be explicit about them:

```
grammar = ws 'foo'* ws 'bar' ws end
```

In Floyd, whitespace and comments are known as *filler*, and you can use the
`%whitespace` and `%comment` rules to define how they are recognized. If
either or both of those rules are specified, then whitespace and comment rules
will be be inserted in front of every string literal and at the end of the
grammar (but before `end`, if the grammar ends in `end`), allowing any
combination of whitespace and comments in between the literals.

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

*   The result of `any` is the character it matched.

*   The result of a string literal is that string.

*   The result of a sequence is the result of the last term in the sequence.

*   The result of a choice is the result of whichever term that was matched.

*   The result of a star expression is an array of the values of
    each expression. If the expression didn't match anything,
    the result is an empty array.

*   The result of a not-term is null.

*   The result of a result term (something that looks like `-> ...`
    or `{ ... }` is the value of the computed expression.

*   The result of a predicate term is null.

*   The result of a binding term is the result of the expr it is
    bound to; there is also the side effect that the value of the
    result may be referred to in predicate terms or result terms
    in the same sequence.

*   The result of a parenthesized expression is the result of the
    enclosed expression.

*   The result of a run is the string matched by the run, as described
    above.

*   The result of `end` is `null`.

*   The result of a plus term is the array of matched expressions.

*   The result of an optional term is an array with either zero
    or one values depending on whether the term didn't match or it did.

*   The result of a range is the character it matched.

*   The result of a not-one is the character it matched.

*   The result of a charset is the character it matched.

*   The result of an ends-in term is the result of the ending expression.

*   The result of a counted term or a counted-range term is an array of
    the N expressions it matched.

*   The result of a unicode category match is the character it matched.

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

## The result language

Floyd grammars can also compute *results* or *values* using a simple
expression language called the Floyd result language (or Floyd language
or just Floyd where the meaning is clear from context). The result
language is intended to have roughly the expressive power of AWK
(although it doesn't yet) and be easily and safely compilable into a
statically typed language like C. When the code is being used as
a library or API in a given language, that language is called the
*host language*. Currently only Python is supported as a host language.

A *Result* is anything that can be expressed in JSON: null,
a boolean, a number, an array of values, or an object containing
key/value pairs.

The result language roughly follows this grammar and typing rules
(typing is explained in the next section):

```
expr  = expr:number '+' expr:number
      | expr:number '-' expr:number
      | expr:str '++' expr:str
      | '[' expr:type* ']: array[type...]'
      | '(' expr:result '): result'
      | expr '[' expr:(int|str) ']: type'
      | expr '(' exprs: [type*] '): type '
      | string
      | floating-point: number
      | hexadecimal: int
      | 'true':bool | 'false':bool | 'null':null
      | ident:result

exprs = expr? (',' expr)* ','?  -> cons($1, $2)
```

Expressions have the usual associativity and precedence. Identifiers
return the result of a bound expression using the same name in a sequence.
identifiers are only visible to terms in that sequence, and not to
an sub-terms, which have their own scopes.

When the host language is dynamically typed or supports sufficiently
powerful polymorphic functions, values can be automaticallyt converted
between Results and primitive or container types as needed.

### Types

The host language is statically typed, with the following kinds of types:

```
type = null
     | bool
     | int
     | number
     | char
     | str
     | Result
     | [type*]
     | {str:type*}

Result = &lt;a union of all of the other types&gt;
```

Because a `Result` is an encompassing all-purpose type (or an `any` type),
the language will often feel more like it is dynamically-typed.

A `char` is a string of length 1; A `str` contains any number of chars.

An `int` is a number with an integral value (i.e., no fractional or
exponent parts).

A `number` can have either an integral value or a floating-point value;
it could also be called a float.

Any type will be automatically promoted to a Result where needed.

The array operator takes a list of N values with types T1, T2, ... T_n and
returns an array value with types [T1, T2, ... T_n].

The subscript operator takes an array of values with types T1, T2, ... T_n
and returns element N with a type of T_n.

Variables are statically typed, with their type inferred as necessary
by the program (i.e., variable types are not currently explicitly
declared).

## Variables

The result of a term in a grammar may be *bound* or assigned to an identifier,
which then acts as a variable and may then be referenced in expressions in any
following terms of the enclosing term sequence (i.e., the scope is the
remaining terms in the sequence).

A term in a sequence may itself be a parenthesized choice containing one
or more sequences; in this case the inner sequence of the choice has its
own scope and variables from the outer scope are shadowed by any variables
in the inner scope.

For example:

```
grammar = 'a' ('b' 'c' -> $1) -> $1
```

Has a result of `'a'`, from the first term in the outer sequence expression.

## Functions

### Builtin

The host language has the following built-in functions with the
given types (using Python's type annotation syntax):

* `atof(s:str): float`<br>
  Returns the numeric equivalent of the string value, where the
  string matches either a floating-point number.

* `atoi(s:str, base: int): int`<br>
  Returns the numeric (integral) equivalent of the string value
  where the string is a series of either decimal or hexadecimal
  digits (and an optional leading '-' if the string is all decimals).

* `atou(s:str, base: int): str`<br>
  Returns the unicode character matching the given string in the given
  base.

* `cat(ss:[str]): str`<br>
  Returns the string produced by joining all of the elements of `ss`
  together with empty strings. Equivalent to `join('', ss)`.

* `colno(): int`<br>`
  Returns the current (1-based) column number in the text at the point
  where the function is called. If the text is empty, returns 1. If
  at the end of the text, returns 1 + the colno of the last character
  in the file.

* `concat(x:[Result], y:[Result]): [Result]`<br>
  Returns an array containing all of the elements of `x` followed by
  all of the elements of `y`.

* `cons(head:Result, tail:[Result]): [Result]`<br>
  Returns an array with `head` as the first element, followed by
  the elements from `tail`. Equivalent to `concat([head], tail)`.

* `dedent(s: str): str`<br>
  Returns an unindented version of the given string. Any characters up to
  and including the first newline are discarded. Then, looking at the
  remaining lines, the line with the fewest number of spaces before a
  non-space character (or the end of the string) is taken to be the
  indentation to undo. Each line then has that many characters removed.
  Anything after the last newline is discarded as well, and then the
  lines are cat'ed together and returned as a string.

* `dict(d:[[key:str, value:Result]]): {[str: Result]*}`<br>
  Returns the object that contains all the key/value pairs.

* `float(i:int): float`<br>
  Returns the floating point equivalent of the int `i`.

* `int(f:float): int`<br>
  Returns the integer equivalent of the floating point number. values
  are truncated towards zero (i.e., int(3.5) returns 3).

* `itou(i:int): char`<br>
  Returns the unicode character with code point `x`.

* `join(x:str, y:[str]): str`<br>
  Returns the result of joining all the strings in y with the
  string in x in between them.

* `scons(x:str, y:[str]): str`<br>
  Returns an array with `x` as the first element, followed by the
  elements from `y`. Equivalen to `cons`, but takes strings instead of
  Results.

* `strcat(x:str, y:str): str`<br>
  Returns the string concatenation of `x` and `y`. Equivalent to
  `cat([x, y])` or `join('', [x, y])`.

* `utoi(x:char): int`<br>
  Returns the Unicode code point value for `x`.

* `xtou(s:str): str`<br>
  Returns the Unicode character with the code point value that is
  the hexadecimal value in `s`. The string may have an optional "0x"
  in front, or may be just a string of hexadecimal digits.

### Implementation-defined

Functions that have names beginning with an underscore are reserved for
the caller of the parser to define, e.g. `_dedent(s:str): str` is a
function called `_dedent` provided by the caller of the parser
that takes a string and returns a string.
