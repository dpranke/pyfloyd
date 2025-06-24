# JSON 5 example

This data contains a few files demonstrating some aspects of the grammars.
It uses the //grammars/json5.g grammar for the JSON5 config file format, and
generates a parser that will preserve tokens and return a concrete syntax
tree (aka parse tree). This allows you to be able to round-trip data between
text and a parsed format, so you can programmatically edit things.

This example is not yet fully fleshed out, and has the following problems:

1. There is no actual mechanism for editing things via a useful/good API
2. There is no mechanism for printing an edited document back out while
   including comments and comments.
3. There is no mechanism for being able to pretty-print out an edited
   document while preserving whitespace and comments as otherwise appropriate.
4. The CST generation logic is completely defined by the client, rather than
   being handled by the parser.

The files are:

* json5.g: A grammar for JSON5 (a symlink to [../../grammars/json5.g]())
* json.dft: A pretty-printing template for a JSON object (a symlink to
  [../../templates/json.dft]())
* json5.py: A generated parser returning a JSON object
* json5_cst.py: A generated parser returning a parse tree (aka concrete
  syntax tree or CST) for a JSON object.
* json5edit.py: A simple driver file that:
  - reads a JSON document
  - parses it with both json5 and json5_cst
  - checks that the values returned from each parse match
  - checks that the concatenated list of tokens from the CST matches
    the input JSON document (i.e., that no text is lost).
  - writes out the CST back out using `json.dump`.
* t.json5: A sample JSON5 document
* t.cst: The resulting concrete syntax tree
* t.cst.fmt: A pretty-printed version of the same concrete syntax tree.
  Note how it is more than 50% shorter than t.cst; this is achieved by
  attempting by printing objects and arrays on a single line where possible;
  the standard JSON library will just print every member of an object or
  an array onto separate lines.

To recreate:

```bash
# Generate a regular parser that discards whitespace, comments, and the
# literal representation of any abstract values.
$ flc ./json5.g

# Generate a token-preserving parser capable of being used to round-trip
# documents while preserving comments.
$ flc -o ./json5_cst.py --tokenize ./json5.g

# Generate the actual CST for a JSON5 document.
$ ./json5edit.py -o t.cst t.json5

# Pretty-print the CST.
$ flt -o ./t.cst.fmt -T ./json.dft t.cst
```

## Notes

The driver provides an implementation of `node()` that creates the CST
and assigns the list of tokens recognized by the parser onto the appropriate
nodes. Ideally this logic should live in `json5_cst`, so that each client
doesn't need to recreate it. It's unclear yet whether the logic for creating
a CST can be made sufficiently generic for this to just be part of the
generated parser, or whether the logic needs to be specified in the grammar
somehow.

The drive also needs to override `dict()` to be able to handle arguments
that are parse nodes instead of values.

Tokens are assigned as follows:

1. Any tokens that have not already been assigned in the input stream
   that occur before the beginning of a node are assigned to the node
   as "leading tokens" to the 'l' field.
2. Any tokens that occur before an optional 'beginning token' in the
   node are assigned to the node.
3. If the node itself represents a token (and isn't representing whitespace,
   a comment, or some form of literal that is probably acting as syntactically
   bracketing/delimiting punctuation), it is assigned to the 's' field in the
   tree. If the next unassigned token matches the 's' field, it is skipped
   over (TODO: Can we assert that this will always be skipped over?).
4. Next any unassigned tokens that occur before the ending position of the
   node are assigned as "trailing tokens" to the 't' field.

The token assignments happen while constructing the root 'grammar' node of the
tree; this essentially means it is done in a post-processing phase after the
parse itself. Ideally token assignment should instead by done while each node
is being created, in basically a post-order traversal of the tree. However, the
current parser object does not contain enough state to know how to do that; it
at the very least needs to track the most recently consumed/assigned token, and
be able to undo those assignments when the parser backtracks.
