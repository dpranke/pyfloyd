# The goals I wish to research and/or achieve with Floyd

1.  Build a production-ready PEG parser and generator that focuses its
    action language on JSON (i.e., JSON objects are returned from the
    parse).
2.  Have the generated parsers be comparable to what you would write by
    hand (i.e., be very readable).
3.  If necessary, provide two modes of generated output: clear/simple and
    fast.
4.  Benchmark the generated grammars against other Python parsing
    frameworks' output and hand-written parsers (e.g., the built-in JSON
    or TOML parsers).
5.  Have the parsers be able to handle a wide range of grammars, including
    ones with left recursion and ones that are indentation-sensitive.
6.  Potentially add the ability to generate non-PEG grammars, e.g. LL and
    LR grammars for suitable languages.
7.  Have the action language of the grammars be comparable in power to AWK
    so that you can build simple parsing scripts with some of AWK's
    utility. This might give us an external DSL.
8.  Explore how to generate code without needing any custom Python code
    (i.e., have a printing language to match the parsing language).
9.  Be able to generate code for multiple languages including perhaps C,
    C++, Go, Java, Javascript, Python, and Rust (and possibly Kotlin,
    Swift, and Zig).
10. Use the output of (9) to enable cross-language benchmarking of the
    same problem space.
11. Reimplement everything in some of the other languages in (9) so that
    we have examples of a non-trivial code base in multiple languages to
    compare and benchmark. Ideally the grammars and pretty-printing
    descriptions are host-language-independent, so that writing new
    grammars and implementing new languages are only N+M problems and not
    N*M problems.
12. Be able to use the language implemented for the parsers as a simple
    embeddable DSL. 
13. Have the language be dynamically typed but suitable for static typing.
14. Define a way to map objects to schemas and host data types so that you
    can parse directly to host data structures and not require manual 
    conversion in the host from JSON.
15. Implement grammars and pretty printers for some of JSON, JSON5, HJSON,
    TOML, a simplified subset of YAML, Ninja, GN, HTML, CSS, JavaScript,
    Protocol Buffers (text format if possible?).
16. Define a DOM-like interface that can be used to produce round-trippable
    versions of parsed docs (i.e., ones that preserve the input including
    whitespace and comments).
