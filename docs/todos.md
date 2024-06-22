# Things TODO

* analyzer.py: Change the floyd parser to use proper nodes that contain
  line number and column info so that when we catch errors in analysis
  we can actually point to where the error is happening.

* analyzer.py: Figure out how to do type analysis of predicates to
  statically catch ones that don't return booleans.

* compiler.py: Figure out if we can omit generated code when it isn't
  actually possible to execute it (E.g., catching a ParsingRuntimeError
  when one will never be thrown). See where I had to add `# pragma: no cover`
  to get the code coverage of floyd/parser.py to 100%.

* printer_test.py: Improve printer algorithm so that two choices with
  actions are not printed on a single line (see test_actions).

* printer_test.py: Improve printer algorithm so that it can pretty-print
  floyd.g and stay under 80 characters wide (see test_floyd).

* Use `\1` for "text matching $1".

* Support regexp escapes like \d, \s, and so on.

* Ensure that only reserved rules start with underscores.
  - Ensure that only reserved identifiers in values start with underscores,
    too?

* Define `\.` as a synonym for `_any`, `\$` as a synonym for `_end`?

* Allow customizable functions that will override the builtins like
  `dict()` in the parsers.
  - Would it make sense to have something like this for the compiler
    as well?

* Add bounded qualifiers like `foo^3`, `foo^3+`, `foo^3,4` or something.

* Maybe add `_pos` built-in rule (and _pos() built-in function), 
  `_text` built-in value.

* Handle more types of operator expressions. See test_not_quite_operators
  for some examples.

* analyzer.py: Figure out if it is possible to mix operator expressions and
  left-recursive expressions so that we trip the unexpected AST node
  assertion in _check_lr
