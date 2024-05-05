# Things TODO

* grammars that are both left- and right-recursive end up being
  right-associative. Figure out how to make them be (optionally?)
  left-associative instead.

* analyzer.py: Change the floyd parser to use proper nodes that contain
  line number and column info so that when we catch errors in analysis
  we can actually point to where the error is happening.

* analyzer.py: Figure out how to do type analysis of predicates to
  statically catch ones that don't return booleans.

* compiler.py: Figure out if we can omit generated code when it isn't
  actually possible to execute it (E.g., catching a ParsingRuntimeError
  when one will never be thrown). See where I had to add `# pragma: no cover`
  to get the code coverage of floyd/parser.py to 100%.

* compiler.py: Figure out how to prune any methods that aren't actually
  needed for the parser.

* compiler.py: Figure out how to handle inlining methods more consistently
  in _compile so that we don't have the special-casing logic here. Same
  thing in analyzer.py rewrite_singles().

* compiler.py: Figure out how to handle blank lines at the end of a method
  better in _flatten().

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

* Figure out how to notate for associativity and precedence without
  having to encode it in the ordering of rules, e.g. so you can write
  `expr = expr '*' expr` rather than `expr = expr '*' add_expr`.
  - Also figure out how to implement it :).
