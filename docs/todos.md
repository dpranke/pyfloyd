# Things TODO (semi-prioritized)

* Change generators to indicate how the output files were generated.

* Figure out how to do proper typechecking and decide how to handle
  union/json types in a static language like Go or C++. Do we need
  to add functions like an `add()` that takes two JSON values and
  does the right thing, rather than relying on `a + b` just working
  for free in the host environment (which works in Python, but doesn't
  really work in JavaScript as the type promotion rules are weird and
  wouldn't work at all in C). Once we do this we should be able to
  statically catch type errors that would cause predicates to not work
  right.

* analyzer.py: Change the floyd parser to use proper nodes that contain
  line number and column info so that when we catch errors in analysis
  we can actually point to where the error is happening.

* Add support for handling indentation.

* Add support for using regexps for AST nodes where it makes sense
  to use them: this should produce a substantial speed up if, for
  example, we can use regexps for tokens in the Python version of
  json.g.

* Figure out a better mechanism for reporting runtime errors that aren't
  syntax errors.

* Add options to generate ES or CommonJS modules in the JS backend
  and clean up the namespace in the regular generated script version
  using an IIFE to declare `parse()`.

* Figure out how much to make the backend templating language-independent,
  whether that be via something like StringTemplate or something else.

* Extract most of the grammar tests into a separate declarative data file
  and format, and figure out a more generic test harness that can be
  easily ported to different implementations of Floyd.

* Add a C++ backend. This may require a revamp of the API and CLI in orderi
  to be able to generate both an interface/header file and a source file
  in one go.

* Add a Go backend.

* Add a Java backend.

* Figure out how to generate a full concrete syntax tree with comments
  and whitespace properly annotated so we have a more generic DOM-like
  approach for manipulating parsed documents. Ultimately this should
  result in something like the ability to programmatically edit a
  JSON5 file in a round trip.

* Write a grammar for Markdown; if we can't do it with existing
  functionality, add features until we can.

* Write a grammar for HJSON; if we can't do it with existing
  functionality, add features until we can.

* Add more sample grammars (CSV, TOML, YAML, protobufs, etc.?) and
  tests for them.

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
  assertion in _check_lr.
