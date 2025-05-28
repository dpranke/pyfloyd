# Datafiles

Floyd defines a file format I call "datafiles" (or "Floyd datafiles"
when less ambiguity is needed).

The format is a strict superset of JSON, designed for human use, with three
things in mind:

- Minimize punctuation whereever possible.
- Support multiline strings as cleanly as possible.
- Provide a mechanism for extensibility (via a 'tag' mechanism).

It has the following features:

- Any string value may be unquoted if it is a single word (i.e., contains
  no whitespace), as long as it cannot be interpreted as a boolean value,
  null, or a number.
- Trailing commas are always unnecessary.
- Multiline strings are fully supported with sensible handling of
  indentation.
- There are a variety of quoting styles supported (single quotes, double
  quotes, backquotes, triple-quoted versions of the same, and two different
  kinds of "long strings"), and strings come in "regular" forms (allowing
  escape sequences) and "raw" forms (where nothing is interpreted). This
  ensures that it is as easy as possible to embed any other kind of text into
  a string without needing to worry about escaping it.
- Both single-line and multi-line comments are supported.
- A top-level object can be expressed as either a standalone series of
  key-value pairs or as a regular object.
- While the base format is strictly equivalent to JSON (it can express
  nothing that JSON can't express, meaning that NaNs and Infinities are
  not supported as numbers), it supports a generic "tag" mechanism where
  you can annotate values with how they should be decoded or interpreted.
  This is similar to how Python supports different types of strings
  (raw-strings, f-strings, t-strings and so on) and to the idea of
  tagFunctions in JavaScript template strings, but the tags can be applied
  to lists and objects as well as strings.

## Comparison with alternatives.

Why yet another config file format? Because I wasn't quite happy with
the ones I had found. Frankly, if you're happy with one of the following,
you should probably use it instead, as it is likely to be more widely
supported (*much more*, in some cases).

### JSON

[JSON](https://json.org) is a near-ideal file format in many ways; it is about
as simple as possible while supporting both lists and maps/objects/structures
in a first-class way. While it is very readable, it is not otherwise designed
for ease of use by humans. In particular, it lacks support for comments and
requires a bit more punctuation than you might otherwise like.

### JSON5

[JSON5](https://json5.org), aka "JSON for Humans", improves upon JSON
significantly, human-editing-wise, in that it allows for unquoted object keys
and supports comments.  However, more can be stripped away (IMO) to improve
things further, it is a bit limited by still trying to remain a subset
of JavaScript, and it extends the datatypes supported by JSON to support
floating-point NaNs and Infinities, making it not strictly JSON-compatible.

### YAML

[YAML](https://yaml.org), aka "YAML Ain't Markup Language", is definitely
more human-friendly than JSON, but it is a much bigger and more complex
file format, and in some ways relies on whitespace for semantics in ways
that I find a bit unappealing.

### TOML

[TOML](https://toml.io/en), aka "Tom's Obvious Minimal Language" is
also a very nice approach to human-friendliness. It is a little too
close to .ini-style config files for my aesthetics, however. It also
supports dates and time values directly which, while useful, also means
that it encourages things that may not be directly mappable back to JSON
values without loss of meaning.

### HJSON

[HJSON](https://hjson.github.io) is very close to what I would want
in a config file format. The most significant difference between
HJSON and datafiles is in the way that HJSON will interpreter a series
of unquoted words as a single string, rather than as a series of strings.
IMO the latter is more useful. The tagging mechanism gives datafiles
a bit more flexibility as well (though admittedly using tags also
takes things away from strict JSON compatibility).

### S-Expressions

[S-expressions](https://en.wikipedia.org/wiki/S-expression) can arguably
also be a player in this space. Due to datafile's support for bare words
and numwords, most S-expressions can be directly translated into
datafile values by just substituting '[' and ']' for '(' and ')'. In
a language like Racket, where parentheses and brackets can be used
almost interchangeably, things are even closer. However, S-expressions
don't have native support for objects/dicts. Some languages like Racket
support extensions to S-expressions for to add keyword arguments, but
this is a bit unorthodox and isn't quite as simple as just using a different
syntactic form for objects.

