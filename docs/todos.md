# Things TODO (semi-prioritized)

* Support template reuse/sharing.
  - Currently one template can "inherit" from another (basically overriding
    the definitions in the former), but it might be good to also be able to
    reuse definitions from a template without bringing everything from the
    template in and without overridding everything in the template.

* Replace hard-coded grammar pretty-printing with template-based
  pretty-printing.

* Support grammar reuse, sharing, inheritance.

* Allow customizable externs that can be used as functions in addition
  to the existing support for constants. They should be able to override
  the builtin methods.

* Change the floyd parser to use proper nodes that contain line number and
  column info so that when we catch errors in analysis we can actually point
  to where the error is happening.

* Figure out how to generate a full concrete syntax tree with comments
  and whitespace properly annotated so we have a more generic DOM-like
  approach for manipulating parsed documents. Ultimately this should
  result in something like the ability to programmatically edit a
  JSON5 file in a round trip.

* Add ability to declare types and/or constructors for values in the
  expression language.

* Add more primitives/built-in functions, logic so that we don't need
  separate api.py files to implement the rest of encoding and decoding.

* Support separating out semantic actions from grammar syntax; look at
  existing work in Rats and Ohm for approaches.

* Add options to generate ES or CommonJS modules in the JS backend
  and clean up the namespace in the regular generated script version
  using an IIFE to declare `parse()`.

* Add Java code gen.

* Add C, C++ code gen. This may require a revamp of the API and CLI in order
  to be able to generate both an interface/header file and a source file
  in one go.

* Add Rust code gen.

* Add PHP, Swift, C#, Dart, Kotlin, TypeScript code gen.

* Flesh out Floyd into a full language so that we can declare functions
  in grammars and write complete programs in Floyd.

* Port Floyd to other (host) languages.

* Support streaming input (don't require all of the input up front).

* Improve generated code quality (performance) / do profiling.

* Implement byte-code/VM-based interpreter.

* Add D, Lua, Racket/Scheme, Haskell, OCaml, Nim, Zig, Delphi/Object Pascal,
  VB code gen.

* Add assembly code gen?

* Add Python extension (native method) code gen (likely needs either C/C++
  or Rust codegen first). Could also investigate
  https://github.com/go-python/gopy ?

* Add support for handling indentation; be able to parse Python-like
  languages.

* Write a grammar for Markdown; if we can't do it with existing
  functionality, add features until we can.

* Write a grammar for HJSON; if we can't do it with existing
  functionality, add features until we can.

* Add more sample grammars (CSV, TOML, YAML, protobufs, etc.?) and
  tests for them.

* Add support for using regexps for AST nodes where it makes sense
  to use them: this should produce a substantial speed up if, for
  example, we can use regexps for tokens in the Python version of
  json.g.

* Add ability to embed grammars into source files and be able to regenerate
  the source file with an updated grammar or parser.

* Figure out a better mechanism for reporting runtime errors that aren't
  syntax errors.

* Extract most of the grammar tests into a separate declarative data file
  and format, and figure out a more generic test harness that can be
  easily ported to different implementations of Floyd.

* Figure out if we can omit generated code when it isn't actually
  possible to execute it (E.g., catching a ParsingRuntimeError when one will
  never be thrown). See where I had to add `# pragma: no cover` to get the
  code coverage of floyd/parser.py to 100%.

* printer_test.py: Improve printer algorithm so that two choices with
  actions are not printed on a single line (see test_actions).

* printer_test.py: Improve printer algorithm so that it can pretty-print
  floyd.g and stay under 80 characters wide (see test_floyd).

* Support regexp escapes like \d, \s, and so on.

* Ensure that only reserved rules start with underscores.
  - Ensure that only reserved identifiers in values start with underscores,
    too?

* Handle more types of operator expressions. See test_not_quite_operators
  for some examples.

* analyzer.py: Figure out if it is possible to mix operator expressions and
  left-recursive expressions so that we trip the unexpected AST node
  assertion in _check_lr.

* Support incremental parsing?
