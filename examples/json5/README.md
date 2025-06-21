# JSON 5 example

This data contains a few files demonstrating some aspects of the grammars.
In particular, it uses the //grammars/json5.g grammar for the JSON5 config
file format, and generates a parser that will preserve tokens and return
a concrete syntax tree (aka parse tree). This allows you to be able to
round-trip data between text and a parsed format, so you can programmatically
edit things.

This example is not yet fully fleshed out; there is no actual mechanism
for editing things via a useful/good API, and there is no mechanism for
pretty-printing out the tree while including comments.

To recreate, use

```
$ flc -o ./json5.py ../../grammars/json5.g
$ flc -o ./json5_cst.py --tokenize ../../grammars/json5.g
$ ./json5edit.py --print t.json5 > t.cst
$ flt -o ./t.cst.fmt -T ../../templates/json.dft t.cst
