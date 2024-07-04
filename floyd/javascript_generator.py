# Copyright 2024 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 as found in the LICENSE file.
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Dict, List, Union

from floyd.analyzer import Grammar
from floyd.formatter import flatten, Comma, Saw, Tree
from floyd.generator import Generator, GeneratorOptions
from floyd import string_literal as lit


_FormatObj = Union[Comma, Tree, Saw, str]


class JavaScriptGenerator(Generator):
    def __init__(self, grammar: Grammar, options: GeneratorOptions):
        super().__init__(grammar, options)
        self._builtin_methods = self._load_builtin_methods()
        self._builtin_functions = self._load_builtin_functions()
        self._exception_needed = False
        self._methods: Dict[str, List[str]] = {}
        self._operators: Dict[str, str] = {}

        # These methods are pretty much always needed.
        self._needed_methods = set(
            {
                'error',
                'errorOffsets',
                'fail',
                'rewind',
                'succeed',
            }
        )
        if grammar.ch_needed:
            self._needed_methods.add('ch')
        if grammar.leftrec_needed:
            self._needed_methods.add('leftrec')
        if grammar.operator_needed:
            self._needed_methods.add('operator')
        if grammar.range_needed:
            self._needed_methods.add('range')
        if grammar.str_needed:
            self._needed_methods.add('str')
        if grammar.unicat_needed:
            self._needed_methods.add('unicat')

    def generate(self) -> str:
        self._gen_rules()
        return self._gen_text()

    def _gen_rules(self) -> None:
        for rule, node in self.grammar.rules.items():
            self._methods[rule] = self._gen(node)

    def _gen_text(self) -> str:
        if self.options.main:
            text = _MAIN_HEADER
        else:
            text = _DEFAULT_HEADER

        if self._exception_needed:
            text += _PARSING_RUNTIME_EXCEPTION

        if self.grammar.operators:
            text += _OPERATOR_CLASS

        text += _CLASS

        text += self._state()
        text += '\n'

        if self._exception_needed:
            text += _PARSE_WITH_EXCEPTION.replace(
                '{starting_rule}', self.grammar.starting_rule
            )
        else:
            text += _PARSE.replace('{starting_rule}', self.grammar.starting_rule)

        text += self._gen_methods()
        if self.grammar.needed_builtin_functions:
            text += '\n\n'
            text += self._gen_functions()
        text += '}\n'

        if self.options.main:
            text += _MAIN_FOOTER
        else:
            text += _DEFAULT_FOOTER
        return text

    def _state(self) -> str:
        text = ''
        if self.options.memoize:
            text += '        this.cache = {}\n'
        if self.grammar.leftrec_needed or self.grammar.operator_needed:
            text += '        this.seeds = {}\n'
        if self.grammar.leftrec_needed:
            text += '        this.blocked = Set()\n'
        if self.grammar.operator_needed:
            text += self._operator_state()
            text += '\n'

        return text

    def _operator_state(self) -> str:
        text = '        this.operators = {}\n'
        for rule, o in self.grammar.operators.items():
            text += '        o = OperatorState()\n'
            text += '        o.precOps = {\n'
            for prec in sorted(o.prec_ops):
                text += '            %d: [' % prec
                text += ', '.join("'%s'" % op for op in o.prec_ops[prec])
                text += '],\n'
            text += '        }\n'
            text += '        o.precs = sorted(o.precOps, reverse=True)\n'
            text += '        o.rassoc = Set(['
            text += ', '.join("'%s'" % op for op in o.rassoc)
            text += '])\n'
            text += '        o.choices = {\n'
            for op in o.choices:
                text += "            '%s': this.%s,\n" % (op, o.choices[op])
            text += '        }\n'
            text += "        this.operators['%s'] = o\n" % rule
        return text

    def _load_builtin_methods(self) -> Dict[str, str]:
        blocks = _BUILTIN_METHODS.split('\n  #')
        blocks[0] = blocks[0][3:]
        builtins = {}
        for block in blocks:
            name = block[ :block.find('(')]
            text = block
            builtins[name] = text
        return builtins

    def _load_builtin_functions(self) -> Dict[str, str]:
        blocks = _BUILTIN_FUNCTIONS[:-1].split('\n\n')
        builtins = {}
        for block in blocks:
            name = block[:block.find('(')]
            builtins[name] = block + '\n'
        return builtins

    def _gen_methods(self) -> str:
        text = ''
        for rule, method_body in self._methods.items():
            memoize = self.options.memoize and rule.startswith('_r_')
            text += self._gen_method_text(rule, method_body, memoize)
        text += '\n'
        if self.grammar.needed_builtin_rules or self._needed_methods:
            text += '\n'

        if self.grammar.needed_builtin_rules:
            text += '  #' + '\n\n  #'.join(
                self._builtin_methods[f'r_{name}_']
                for name in sorted(self.grammar.needed_builtin_rules)
            )
            text += '\n'

        text += '  #' + '\n\n  #'.join(
            self._builtin_methods[name]
            for name in sorted(self._needed_methods)
        )
        return text

    def _gen_method_text(self, method_name, method_body, memoize) -> str:
        text = '\n\n'
        text += '  #%s() {\n' % method_name
        if memoize:
            text += '    let r = this.cache.get(("%s", ' % method_name
            text += 'this.pos))\n'
            text += '    if (r) {\n'
            text += '      [this.val, this.failed, this.pos] = r;\n'
            text += '      return;\n'
            text += '    }\n'
            text += '    pos = this.pos;\n'
        for line in method_body:
            text += f'    {line}\n'
        if memoize:
            text += f'    this.cache[("{method_name}", pos)] = ('
            text += 'this.val, this.failed, this.pos);\n'
        text += '  }'
        return text

    def _gen_functions(self) -> str:
        return '\n\n'.join(
            self._builtin_functions[name]
            for name in sorted(self.grammar.needed_builtin_functions)
        )

    def _gen(self, node) -> List[str]:
        # All of the rule methods return a list of lines.
        fn = getattr(self, f'_{node[0]}_')
        return fn(node)

    def _gen_expr(self, node) -> _FormatObj:
        # All of the host methods return a formatter object.
        fn = getattr(self, f'_{node[0]}_')
        return fn(node)

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _action_(self, node) -> List[str]:
        obj = self._gen_expr(node[2][0])
        return flatten(Saw('this.#succeed(', obj, ')'))

    def _apply_(self, node) -> List[str]:
        return [f'this.#{node[1]}()']

    def _choice_(self, node) -> List[str]:
        lines = ['let p = this.pos']
        for subnode in node[2][:-1]:
            lines.extend(self._gen(subnode))
            lines.append('if (!this.failed) {')
            lines.append('  return;')
            lines.append('}')
            lines.append('this.#rewind(p)')
        lines.extend(self._gen(node[2][-1]))
        return lines

    def _empty_(self, node) -> List[str]:
        del node
        return ['this.#succeed(null)']

    def _label_(self, node) -> List[str]:
        lines = self._gen(node[2][0])
        lines.extend(
            [
                'if (!this.failed) {',
                f'  v_{node[1].replace("$", "_")} = this.val',
                '}'
            ]
        )
        return lines

    def _leftrec_(self, node) -> List[str]:
        left_assoc = self.grammar.assoc.get(node[1], 'left') == 'left'
        lines = [
            f'this._leftrec(this.{node[2][0][1]}, '
            + f"'{node[1]}', {left_assoc})"
        ]
        return lines

    def _lit_(self, node) -> List[str]:
        expr = lit.encode(node[1])
        if len(node[1]) == 1:
            method = 'ch'
        else:
            method = 'str'
        return [f'this.#{method}({expr})']

    def _not_(self, node) -> List[str]:
        sublines = self._gen(node[2][0])
        lines = (
            [
                'p = this.pos;',
                'errpos = this.errpos;',
            ]
            + sublines
            + [
                'if (this.failed) {',
                '  this.#succeed(None, p);',
                '} else {',
                '  this.#rewind(p);',
                '  this.errpos = errpos;',
                '  this.#fail();',
                '}',
            ]
        )
        return lines

    def _operator_(self, node) -> List[str]:
        self._needed_methods.add('operator')
        # Operator nodes have no children, but subrules for each arm
        # of the expression cluster have been defined and are referenced
        # from self.grammar.operators[node[1]].choices.
        assert node[2] == []
        return [f"this._operator(f'{node[1]}')"]

    def _paren_(self, node) -> List[str]:
        return self._gen(node[2][0])

    def _post_(self, node) -> List[str]:
        sublines = self._gen(node[2][0])
        if node[1] == '?':
            lines = (
                [
                    'p = this.pos;',
                ]
                + sublines
                + [
                    'if (this.failed) {',
                    '  this._succeed([], p);',
                    '} else {',
                    '  this._succeed([this.val]);',
                    '}',
                ]
            )
        else:
            lines = ['vs = [];']
            if node[1] == '+':
                lines.extend(sublines)
                lines.extend(
                    [
                        'vs.append(this.val);',
                        'if (this.failed) {',
                        '  return;',
                        '}',
                    ]
                )
            lines.extend(
                [
                    'while (true) {',
                    '  p = this.pos;',
                ]
                + ['  ' + line for line in sublines]
                + [
                    '  if (this.failed) {',
                    '    this._rewind(p);',
                    '    break',
                    '  }',
                    '  vs.append(this.val);',
                    'this._succeed(vs);',
                ]
            )
        return lines

    def _pred_(self, node) -> List[str]:
        arg = self._gen_expr(node[2][0])
        # TODO: Figure out how to statically analyze predicates to
        # catch ones that don't return booleans, so that we don't need
        # the _ParsingRuntimeError exception
        self._exception_needed = True
        return [
            'v = ' + flatten(arg)[0],
            'if (v === true) {',
            '  this._succeed(v);',
            '} else if (v === false) {',
            '  this._fail();',
            '} else {',
            "  throw new ParsingRuntimeError('Bad predicate value');",
            '}',
        ]

    def _range_(self, node) -> List[str]:
        return [
            'this.#range(%s, %s)'
            % (lit.encode(node[2][0][1]), lit.encode(node[2][1][1]))
        ]

    def _seq_(self, node) -> List[str]:
        lines = self._gen(node[2][0])
        for subnode in node[2][1:]:
            lines.append('if (!this.failed) {')
            lines.extend('  ' + line for line in self._gen(subnode))
            lines.append('}')
        return lines

    def _unicat_(self, node) -> List[str]:
        return ['this.#unicat(%s)' % lit.encode(node[1])]

    #
    # Handlers for the host nodes in the AST
    #
    def _ll_arr_(self, node) -> _FormatObj:
        if len(node[2]) == 0:
            return '[]'
        args = [self._gen(n) for n in node[2]]
        return Saw('[', Comma(args), ']')

    def _ll_call_(self, node) -> Saw:
        # There are no built-in functions that take no arguments, so make
        # sure we're not being called that way.
        # TODO: Figure out if we need this routine or not when we also
        # fix the quals.
        assert len(node[2]) != 0
        args = [self._gen(n) for n in node[2]]
        return Saw('(', Comma(args), ')')

    def _ll_getitem_(self, node) -> Saw:
        return Saw('[', self._gen(node[2][0]), ']')

    def _ll_lit_(self, node) -> str:
        return lit.encode(node[1])

    def _ll_minus_(self, node) -> Tree:
        return Tree(
            self._gen_expr(node[2][0]), '-', self._gen_expr(node[2][1])
        )

    def _ll_num_(self, node) -> str:
        return node[1]

    def _ll_paren_(self, node) -> _FormatObj:
        return self._gen_expr(node[2][0])

    def _ll_plus_(self, node) -> Tree:
        return Tree(
            self._gen_expr(node[2][0]), '+', self._gen_expr(node[2][1])
        )

    def _ll_qual_(self, node) -> Saw:
        first = node[2][0]
        second = node[2][1]
        if first[0] == 'll_var':
            if second[0] == 'll_call':
                # first is an identifier, but it must refer to a
                # built-in function if second is a call.
                fn = first[1]
                # Note that unknown functions were caught during analysis
                # so we don't have to worry about that here.
                start = f'_{fn}'
            else:
                # If second isn't a call, then first refers to a variable.
                start = self._ll_var_(first)
            saw = self._gen_expr(second)
            if not isinstance(saw, Saw):  # pragma: no cover
                raise TypeError(second)
            saw.start = start + saw.start
            i = 2
        else:
            # TODO: We need to do typechecking, and figure out a better
            # strategy for propagating errors/exceptions.
            saw = self._gen_expr(first)
            if not isinstance(saw, Saw):  # pragma: no cover
                raise TypeError(first)
            i = 1
        next_saw = saw
        for n in node[2][i:]:
            new_saw = self._gen_expr(n)
            if not isinstance(new_saw, Saw):  # pragma: no cover
                raise TypeError(n)
            new_saw.start = next_saw.end + new_saw.start
            next_saw.end = new_saw
            next_saw = new_saw
        return saw

    def _ll_var_(self, node) -> str:
        return 'v_' + node[1].replace('$', '_')

    def _ll_const_(self, node) -> str:
        return node[1]


_DEFAULT_HEADER = """\
"""


_DEFAULT_FOOTER = ''


_MAIN_HEADER = """\
#!/usr/bin/env node
"""


_MAIN_FOOTER = """\

async function main() {
  const fs = require("fs");

  let s = "";
  if (process.argv.length == 2 || process.argv[2] == "-") {
    function readStream(stream) {
      stream.setEncoding("utf8");
      return new Promise((resolve, reject) => {
        let data = "";

        stream.on("data", (chunk) => (data += chunk));
        stream.on("end", () => resolve(data));
        stream.on("error", (error) => reject(error));
      });
    }
    s = await readStream(process.stdin);
  } else {
    s = await fs.promises.readFile(process.argv[2]);
  }

  let result = parse(s.toString());
  if (result.err != undefined) {
    console.log(result.err);
    process.exit(1);
  } else {
    console.log(JSON.stringify(result.val, null, 2));
    process.exit(0);
  }
}

if (typeof process !== "undefined" && process.release.name === "node") {
  (async () => {
    main();
  })();
}
"""


_PARSING_RUNTIME_EXCEPTION = """\
class ParsingRuntimeError extends Exception;


"""

_OPERATOR_CLASS = """\
class OperatorState {
  constructor():
    this.currentDepth = 0
    this.currentPrec = 0
    this.precOps = {}
    this.precs = []
    this.rassoc = set()
    this.choices = {}

"""

_CLASS = """\
class Result {
  constructor(val, err, pos) {
    this.val = val;
    this.err = err;
    this.pos = pos;
  }
}

function parse(text, path = '<string>') {
  const p = new Parser(text, path);
  return p.parse();
}

class Parser {
  constructor(text, path) {
    this.text = text;
    this.end = text.length;
    this.errpos = 0;
    this.failed = false;
    this.path = path;
    this.pos = 0;
    this.val = undefined;
  }
"""

_PARSE = """\
  parse() {
    this.#_r_{starting_rule}_();
    if (this.failed) {
      return new Result(null, this.#error(), this.errpos);
    } else {
      return new Result(this.val, null, this.pos);
    }
  }\
"""

_PARSE_WITH_EXCEPTION = """\
  parse() {
    try {
      this.#_r_{starting_rule}_();
      if (this.failed) {
        return new Result(null, this.#error(), this.errpos);
      } else {
        return new Result(this.val, null, this.pos);
      }
    } catch (e) {
      if (instanceof(e, ParsingRuntimeError)) {
        let lineno, _ = this.#errorOffsets();
        return new Result(null, this.path + ':' + lineno + ' ' + e.toString());
      } else {
        throw e;
      }
    }
  }\
"""

_BUILTIN_METHODS = """\
  #_r_any_() {
    if (this.pos < this.end) {
      this.#succeed(this.text[this.pos], this.pos + 1);
    } else {
      this.#fail();
    }

  #_r_end_() {
    if (this.pos === this.end) {
      this.#succeed(null);
    } else {
      this.#fail();
    }

  #ch(ch) {
     let p = this.pos;
     if (p < this.end && this.text[p] === ch) {
       this.#succeed(ch, this.pos + 1);
     } else {
       this.#fail();
    }
  }

  #errorOffsets() {
    let lineno = 1;
    let colno = 1;
    for (let i = 0; i < this.errpos ; i++) {
      if (this.text[i] === '\\n') {
        lineno += 1;
        colno = 1;
      } else {
        colno += 1;
      }
    }
    return [lineno, colno];
  }

  #error() {
    let [lineno, colno] = this.#errorOffsets();
    let thing;
    if (this.errpos === this.end) {
      thing = 'end of input';
    } else {
      thing = `"${this.text[this.errpos]}"`;
    }
    return `${this.path}:${lineno} Unexpected ${thing} at column ${colno}`;
  }

  #fail() {
    this.val = undefined;
    this.failed = true;
    this.errpos = Math.max(this.errpos, this.pos);
  }

  #leftrec(rule, rule_name, left_assoc) {
    let pos = this.pos;
    let key = [rule_name, pos];
    let seed = this.seeds[key];
    if (seed) {
      [this.val, this.failed, this.pos] = seed;
      return
    }
    if (rule_name in this.blocked) {
      this.val = undefined;
      this.failed = true;
      return;
    }
    let current = [undefined, true, this.pos];
    this.seeds[key] = current;
    if (left_assoc) {
      this.blocked.add(rule_name);
    }
    while (true) {
      rule();
      if (this.pos > current[2]) {
        current = [this.val, this.failed, this.pos];
        this.seeds[key] = current;
        this.pos = pos;
      } else {
        delete this.seeds[key];
        [this.val, this.failed, this.pos] = current;
        if (left_assoc) {
          this.blocked.remove(rule_name);
          return;
        }
      }
    }
  }

  #operator(rule_name) {
    let o = this.operators[rule_name];
    let pos = this.pos;
    let key = [rule_name, pos];
    let seed = this.seeds.get(key);
    if (seed) {
        [this.val, this.failed, this.pos] = seed;
        return;
    }
    o.current_depth += 1;
    let current = [null, true, pos];
    this.seeds[key] = current;
    let minPrec = o.currentPrec;
    let i = 0;
    while (i < o.precs.length) {
      let repeat = false;
      let prec = o.precs[i];
      let precOps = o.precOps[prec];
      if (prec < minPrec) {
        break;
      }
      o.current_prec = prec;
      if (precOps[0] not in o.rassoc) {
        o.currentPrec += 1;
      }
      for (let j = 0; j+= 1; j < precOps.length) {
        let op = precOps[j];
        o.choices[op]();
        if (!this.failed && this.pos > pos) {
          current = [this.val, this.failed, this.pos];
          this.seeds[key] = current;
          repeat = true;
          break;
        } else {
          this.#rewind(pos);
        }
      }
      if (!repeat) {
        i += 1;
      }
    }

    delete this.seeds[key];
    o.currentDepth -= 1;
    if (o.currentDepth == 0) {
      o.currentPrec = 0;
    }
    [this.val, this.failed, this.pos] = current;
  }

  #range(i, j) {
    p = this.pos;
    if (p != this.end && ord(i) <= ord(this.text[p]) <= ord(j)) {
      this.#succeed(this.text[p], this.pos + 1);
    } else {
      this.#fail();
    }

  #rewind(newpos) {
     this.#succeed(null, newpos);
  }

  #str(s) {
    for (let ch of s) {
      this.#ch(ch);
      if (this.failed) {
        return;
      } 
      this.val = s
    }
  }

  #succeed(v, newpos=null) {
    this.val = v;
    this.failed = false;
    if (newpos !== null) {
      this.pos = newpos;
    }
  }

  #unicat(this, cat):
    this.#fail();
  }
"""

_BUILTIN_FUNCTIONS = """\
cat(strs) {
  return ''.join(strs);
}

dict(pairs) {
  return dict(pairs);
}

float(s) {
  if ('.' in s or 'e' in s or 'E' in s) {
    return float(s);
  }
  return int(s);

hex(s) {
  return int(s, base=16);
}

is_unicat(var, cat) {
  return unicodedata.category(var) == cat;
}

itou(n) {
  return chr(n);
}

join(s, vs) {
  return s.join(vs);
}

utoi(s) {
  return ord(s);
}

xtoi(s) {
  return int(s, base=16);
}

xtou(s) {
  return chr(int(s, base=16));
}
"""
