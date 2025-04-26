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

# pylint: disable=too-many-lines

import re
import shlex
import sys
from typing import Dict, List, Set

from pyfloyd.ast import Not
from pyfloyd.analyzer import Grammar
from pyfloyd.formatter import flatten, Comma, Saw, Tree
from pyfloyd.generator import Generator, GeneratorOptions, FormatObj
from pyfloyd.version import __version__
from pyfloyd import string_literal as lit


class JavaScriptGenerator(Generator):
    def __init__(self, grammar: Grammar, options: GeneratorOptions):
        super().__init__(grammar, options)
        self._builtin_methods = self._load_builtin_methods()
        self._methods: Dict[str, List[str]] = {}
        self._operators: Dict[str, str] = {}
        self._map = {
            'end': ';',
            'false': 'false',
            'indent': '  ',
            'Infinity': 'Infinity',
            'NaN': 'NaN',
            'not': '!',
            'null': 'null',
            'true': 'true',
        }

    def _gen_text(self) -> str:
        imports = self._imports()
        version = __version__
        args = shlex.join(sys.argv[1:])

        if self._options.main:
            text = _MAIN_HEADER.format(
                version=version, args=args, imports=imports
            )
        else:
            text = _DEFAULT_HEADER.format(
                version=version, args=args, imports=imports
            )

        if self._grammar.exception_needed:
            text += _PARSING_RUNTIME_EXCEPTION

        if self._grammar.operators:
            text += _OPERATOR_CLASS

        externs = self._externs()
        text += _CLASS.format(externs=externs)

        text += self._state()

        if self._grammar.exception_needed:
            text += _PARSE_WITH_EXCEPTION.format(
                starting_rule=self._grammar.starting_rule
            )
        else:
            text += _PARSE.format(starting_rule=self._grammar.starting_rule)

        text += self._gen_methods()
        text += self._endclass()

        if self._options.main:
            text += _MAIN_FOOTER
        else:
            text += _DEFAULT_FOOTER
        return text

    def _imports(self) -> str:
        return ''

    def _externs(self) -> str:
        externs = ''
        if self._grammar.externs:
            for k, v in self._grammar.externs.items():
                v = 'true' if v else 'false'
                externs += f"    this.externs.set('{k}', {v});\n"
        else:
            externs = '\n'
        return externs

    def _state(self) -> str:
        text = ''
        if self._options.memoize:
            text += '    this.cache = new Map();\n'
        if self._grammar.leftrec_needed or self._grammar.operator_needed:
            text += '    this.seeds = {};\n'
        if self._grammar.leftrec_needed:
            text += '    this.blocked = new Set();\n'
        if self._grammar.operator_needed:
            text += self._operator_state()
        if self._grammar.outer_scope_rules:
            text += '    this.scopes = [];\n'
        text += '  }\n'
        text += '\n'

        return text

    def _operator_state(self) -> str:
        text = '    this.operators = {}\n'
        text += '    let o;\n'
        for rule, o in self._grammar.operators.items():
            text += '    o = new OperatorState()\n'
            text += '    o.precOps = new Map()\n'
            for prec in sorted(o.prec_ops):
                text += '    o.precOps.set(%d, [' % prec
                text += ', '.join("'%s'" % op for op in o.prec_ops[prec])
                text += ']);\n'
            text += '    o.precs = [...o.precOps.keys()].sort('
            text += '(a, b) => b - a);\n'
            text += '    o.rassoc = new Set(['
            text += ', '.join("'%s'" % op for op in o.rassoc)
            text += ']);\n'
            text += '    o.choices = new Map()\n'
            for op in o.choices:
                text += "    o.choices.set('%s', this.%s)\n" % (
                    op,
                    o.choices[op],
                )
            text += "    this.operators['%s'] = o;\n" % rule
        return text

    def _endclass(self):
        return '}\n'

    def _load_builtin_methods(self) -> Dict[str, str]:
        blocks = _BUILTIN_METHODS.split('\n  }\n\n  ')
        blocks[0] = blocks[0][2:]
        builtins = {}
        for block in blocks[:-1]:
            name = block[: block.find('(')]
            text = block + '\n  }\n'
            builtins[name] = text
        block = blocks[-1]
        name = block[: block.find('(')]
        text = block
        builtins[name] = text
        return builtins

    def _gen_methods(self) -> str:
        text = self._gen_rule_methods()

        if self._grammar.needed_builtin_rules:
            for name in sorted(self._grammar.needed_builtin_rules):
                method_txt = self._builtin_methods[f'r_{name}']
                text += '  ' + method_txt
                text += '\n'

        text += self._needed_methods()

        if self._grammar.needed_builtin_functions:
            text += '\n'
            text += '  ' + '\n  '.join(
                self._builtin_methods[f'fn_{name}']
                for name in sorted(self._grammar.needed_builtin_functions)
            )
        return text

    def _gen_rule_methods(self):
        text = ''
        local_vars = ('errpos', 'found', 'p', 'regexp')
        for rule, node in self._grammar.rules.items():
            self._current_rule = self._base_rule_name(rule)
            local_vars_defined = set()
            lines = []
            original_lines = self._gen(node)
            for line in original_lines:
                modified = False
                for v in local_vars:
                    if f'let {v} =' in line:
                        if v in local_vars_defined:
                            lines.append(line.replace(f'let {v}', v))
                            modified = True
                            break
                        local_vars_defined.add(v)
                if not modified:
                    lines.append(line)

            text += self._gen_method_text(rule, lines)
            self._methods[rule] = lines
            self._current_rule = None

        text += '\n'
        text += '\n'
        return text

    def _gen_method_text(self, method_name, method_body) -> str:
        text = '\n\n'
        text += '  %s() {\n' % method_name
        for line in method_body:
            text += f'    {line}\n'
        text += '  }'
        return text

    def _gen(self, node) -> List[str]:
        # All of the rule methods return a list of lines.
        lines: List[str] = []
        if node.t == 'seq':
            vs: Set[str] = self._find_vars(node)
            lines = []
            for v in sorted(vs):
                lines.append(f'let {v};')

        fn = getattr(self, f'_ty_{node.t}')
        return lines + fn(node)

    def _thisvar(self, v):
        return 'this.' + v

    def _rulename(self, fn):
        return 'this.' + fn

    def _extern(self, v):
        return "this.externs.get('" + v + "');"

    def _invoke(self, fn, *args):
        return 'this.' + fn + '(' + ', '.join(args) + ')'

    #
    # Handlers for each non-host node in the glop AST follow.
    #

    def _ty_choice(self, node) -> List[str]:
        lines = ['let p = this.pos;']
        for subnode in node.ch[:-1]:
            lines.extend(self._gen(subnode))
            lines.append('if (!this.failed) {')
            lines.append('  return;')
            lines.append('}')
            lines.append('this.rewind(p);')
        lines.extend(self._gen(node.ch[-1]))
        return lines

    def _ty_count(self, node) -> List[str]:
        lines = [
            'let vs = [];',
            'let i = 0;',
            f'let cmin = {node[1][0]};',
            f'let cmax = {node[1][1]};',
            'while (i < cmax) {',
        ]
        lines.extend(['    ' + line for line in self._gen(node.child)])
        lines.extend(
            [
                '    if (this.failed) {',
                '        if (i >= cmin) {',
                '            this.succeed(vs);',
                '            return;',
                '        }',
                '        return;',
                '    }',
                '    vs.push(this.val);',
                '    i += 1;',
                '}',
                'this.succeed(vs);',
            ]
        )
        return lines

    def _ty_ends_in(self, node) -> List[str]:
        sublines = self._gen(node.child)
        lines = (
            [
                'while (true) {',
            ]
            + ['    ' + line for line in sublines]
            + [
                '    if (!this.failed) {',
                '        break;',
                '    }',
                '    this.r_any();',
                '    if (this.failed) {',
                '        break;',
                '    }',
                '}',
            ]
        )
        return lines

    def _ty_label(self, node) -> List[str]:
        lines = self._gen(node.child)
        varname = self._varname(node[1])
        if self._current_rule in self._grammar.outer_scope_rules:
            lines.extend(
                [
                    'if (!this.failed) {',
                    f"  this.scopes[this.scopes.length-1].set('{node[1]}', this.val);"
                    '}',
                ]
            )
        else:
            lines.extend(
                [
                    'if (!this.failed) {',
                    f'  {varname} = this.val;',
                    '}',
                ]
            )
        return lines

    def _ty_not(self, node) -> List[str]:
        sublines = self._gen(node.child)
        lines = (
            [
                'let p = this.pos;',
                'let errpos = this.errpos;',
            ]
            + sublines
            + [
                'if (this.failed) {',
                '  this.succeed(null, p);',
                '} else {',
                '  this.rewind(p);',
                '  this.errpos = errpos;',
                '  this.fail();',
                '}',
            ]
        )
        return lines

    def _ty_not_one(self, node) -> List[str]:
        sublines = self._gen(Not(node.child))
        return sublines + [
            'if (!this.failed) {',
            '    this.r_any(p);',
            '}',
        ]

    def _ty_opt(self, node) -> List[str]:
        sublines = self._gen(node.child)
        lines = (
            [
                'let p = this.pos;',
            ]
            + sublines
            + [
                'if (this.failed) {',
                '  this.succeed([], p);',
                '} else {',
                '  this.succeed([this.val]);',
                '}',
            ]
        )
        return lines

    def _ty_paren(self, node) -> List[str]:
        return self._gen(node.child)

    def _ty_plus(self, node) -> List[str]:
        sublines = self._gen(node.child)
        lines = (
            ['let vs = [];']
            + sublines
            + [
                'vs.push(this.val);',
                'if (this.failed) {',
                '  return;',
                '}',
                'while (true) {',
                '  let p = this.pos;',
            ]
            + ['  ' + line for line in sublines]
            + [
                '  if (this.failed || this.pos === p) {',
                '    this.rewind(p);',
                '    break;',
                '  }',
                '  vs.push(this.val);',
                '}',
                'this.succeed(vs);',
            ]
        )
        return lines

    def _ty_pred(self, node) -> List[str]:
        arg = self._gen_expr(node.child)
        return [
            'let v = ' + flatten(arg, indent=self._map['indent'])[0],
            'if (v === true) {',
            '  this.succeed(v);',
            '} else if (v === false) {',
            '  this.fail();',
            '} else {',
            "  throw new ParsingRuntimeError('Bad predicate value');",
            '}',
        ]

    def _ty_regexp(self, node) -> List[str]:
        # TODO: Explain why this is correct.
        s = lit.escape(node[1], '/').replace('\\\\', '\\')
        return [
            f'let regexp = /{s}/gy;',
            'regexp.lastIndex = this.pos;',
            'let found = regexp.exec(this.text);',
            'if (found) {',
            '    this.succeed(found[0], this.pos + found[0].length);',
            '    return;',
            '}',
            'this.fail();',
        ]

    def _ty_run(self, node) -> List[str]:
        lines = self._gen(node.child)
        return (
            ['let start = this.pos;']
            + lines
            + [
                'if (this.failed) {',
                '    return;',
                '}',
                'let end = this.pos;',
                'this.val = this.text.substr(start, end);',
            ]
        )

    def _ty_scope(self, node) -> List[str]:
        return (
            [
                'this.scopes.push(new Map());',
            ]
            + self._gen(node.child)
            + [
                'this.scopes.pop();',
            ]
        )

    def _ty_seq(self, node) -> List[str]:
        lines = self._gen(node.ch[0])
        for subnode in node.ch[1:]:
            lines.append('if (!this.failed) {')
            lines.extend('  ' + line for line in self._gen(subnode))
            lines.append('}')
        return lines

    def _ty_star(self, node) -> List[str]:
        sublines = self._gen(node.child)
        lines = (
            [
                'let vs = [];',
                'while (true) {',
                '  let p = this.pos;',
            ]
            + ['  ' + line for line in sublines]
            + [
                '  if (this.failed || this.pos === p) {',
                '    this.rewind(p);',
                '    break;',
                '  }',
                '  vs.push(this.val);',
                '}',
                'this.succeed(vs);',
            ]
        )
        return lines


_DEFAULT_HEADER = """\
"""


_DEFAULT_FOOTER = ''


_MAIN_HEADER = """\
#!/usr/bin/env node
//
// Generated by pyfloyd version {version}
//    https://github.com/dpranke/pyfloyd
//    `pyfloyd {args}`

"""


_MAIN_FOOTER = """\

async function main() {
  const fs = require('fs');
  const path = require('path');

  let s = "";
  let externs = new Map();
  let i = 2;
  while (i < process.argv.length) {
    if (process.argv[i] == '-h' || process.argv[i] == '--help') {
      console.log(`\
usage: ${path.basename(process.argv[1])} [-h] [-D var=val] [file]

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  -D, --define var=val  define an external var=value (may use multiple times)`);
      process.exit(0);
    }

    if (process.argv[i] == '-D' || process.argv[i] == '--define') {
      let [k, v] = process.argv[i+1].split('=', 2);
      externs.set(k, JSON.parse(v))
      i += 2;
    } else {
      break;
    }
  }
  let filename;
  if (process.argv.length == i || process.argv[i] == "-") {
    filename = '<stdin>';
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
    filename = process.argv[i];
    s = await fs.promises.readFile(filename);
  }

  let result = parse(s.toString(), filename, externs);

  let txt, stream, ret;
  if (result.err != undefined) {
    txt = result.err;
    stream = process.stderr;
    ret = 1;
  } else {
    txt = JSON.stringify(result.val, null, 2);
    stream = process.stdout;
    ret = 0;
  }
  await new Promise(function(resolve, reject) {
    stream.write(txt + '\\n', 'utf8', function(err, data) {
      if (err != null) {
        reject(err);
      } else {
        resolve(data);
      }
    });
  });
  process.exit(ret);
}

if (typeof process !== "undefined" && process.release.name === "node") {
  (async () => {
    main();
  })();
}
"""


_PARSING_RUNTIME_EXCEPTION = """\
class ParsingRuntimeError extends Error {
  toString() {
    return this.message.toString();
  }
}


"""

_OPERATOR_CLASS = """\
class OperatorState {
  constructor() {
    this.currentDepth = 0
    this.currentPrec = 0
    this.precOps = {}  // Map[int, [str]]
    this.precs = []    // List[int]
    this.rassoc = new Set()
    this.choices = {}  // Map[str, rule]
  }
}

"""

_CLASS = """\
class Result {{
  constructor(val, err, pos) {{
    this.val = val;
    this.err = err;
    this.pos = pos;
  }}
}}

function parse(text, path = '<string>', externs = null) {{
  externs = externs || new Map();
  const p = new Parser(text, path);
  return p.parse(externs);
}}

class Parser {{
  constructor(text, path) {{
    this.text = text;
    this.end = text.length;
    this.errpos = 0;
    this.failed = false;
    this.path = path;
    this.pos = 0;
    this.val = undefined;
    this.externs = new Map();
    {externs}
"""

_PARSE = """\
  parse(externs = null) {{
    externs = externs || new Map();
    let errors = '';
    for (let key of externs.keys()) {{
      if (!this.externs.has(key)) {{
        errors += `Unexpected extern "${{key}}"\\n`;
      }} else {{
        this.externs[key] = externs[key];
      }}
    }}
      
    if (errors != '') {{
      return new Result(null, errors.trim(), 0);
    }}
    this.r_{starting_rule}();
    if (this.failed) {{
      return new Result(null, this.error(), this.errpos);
    }} else {{
      return new Result(this.val, null, this.pos);
    }}
  }}\
"""

_PARSE_WITH_EXCEPTION = """\
  parse(externs = null) {{
    externs = externs || new Map();
    let errors = '';
    for (let key of externs.keys()) {{
      if (!this.externs.has(key)) {{
        errors += `Unexpected extern "${{key}}"\\n`;
      }} else {{
        this.externs[key] = externs[key];
      }}
    }}
    if (errors != '') {{
      return new Result(null, errors.trim(), 0);
    }}
    try {{
      this.r_{starting_rule}();
      if (this.failed) {{
        return new Result(null, this.error(), this.errpos);
      }} else {{
        return new Result(this.val, null, this.pos);
      }}
    }} catch (e) {{
      if (e instanceof ParsingRuntimeError) {{
        let [lineno, _] = this.offsets(this.errpos);
        return new Result(null, this.path + ':' + lineno + ' ' + e.toString());
      }} else {{
        throw e;
      }}
    }}
  }}\
"""

_BUILTIN_METHODS = """\
  r_any() {
    if (this.pos < this.end) {
      this.succeed(this.text[this.pos], this.pos + 1);
    } else {
      this.fail();
    }
  }

  r_end() {
    if (this.pos === this.end) {
      this.succeed(null);
    } else {
      this.fail();
    }
  }

  ch(c) {
    let p = this.pos;
    if (p < this.end && this.text[p] === c) {
      this.succeed(c, this.pos + 1);
    } else {
      this.fail();
    }
  }

  offsets(pos) {
    let lineno = 1;
    let colno = 1;
    for (let i = 0; i < pos; i++) {
      if (this.text[i] === '\\n') {
        lineno += 1;
        colno = 1;
      } else {
        colno += 1;
      }
    }
    return [lineno, colno];
  }

  error() {
    let [lineno, colno] = this.offsets(this.errpos);
    let thing;
    if (this.errpos === this.end) {
      thing = 'end of input';
    } else {
      thing = JSON.stringify(this.text[this.errpos]);
      // thing = JSON.stringify(`"${this.text[this.errpos]}"`);
    }
    return `${this.path}:${lineno} Unexpected ${thing} at column ${colno}`;
  }

  fail() {
    this.val = undefined;
    this.failed = true;
    this.errpos = Math.max(this.errpos, this.pos);
  }

  leftrec(rule, rule_name, left_assoc) {
    let pos = this.pos;
    let key = [rule_name, pos];
    let seed = this.seeds[key];
    if (seed) {
      [this.val, this.failed, this.pos] = seed;
      return
    }
    if (this.blocked.has(rule_name)) {
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
      rule.call(this);
      if (this.pos > current[2]) {
        current = [this.val, this.failed, this.pos];
        this.seeds[key] = current;
        this.pos = pos;
      } else {
        delete this.seeds[key];
        [this.val, this.failed, this.pos] = current;
        if (left_assoc) {
          this.blocked.delete(rule_name);
        }
        return;
      }
    }
  }

  lookup(v) {
    let l = this.scopes.length - 1;
    while (l >= 0) {
      if (this.scopes[l].has(v)) {
        return this.scopes[l].get(v);
      }
      l -= 1;
    }
    if (this.externs.has(v)) {
      return this.externs.get(v);
    }
    throw new ParsingRuntimeError(`Unknown var "${v}"`);
  }

  memoize(rule_name, fn) {
    let p = this.pos;
    if (!this.cache.has(p)) {
      this.cache.set(p, new Map());
    }
    if (this.cache.get(p).has(rule_name)) {
      [this.val, this.failed, this.pos] = this.cache.get(p).get(rule_name);
      return;
    }
    fn.call(this);
    this.cache.get(p).set(rule_name, [this.val, this.failed, this.pos]);
  }

  operator(rule_name) {
    let o = this.operators[rule_name];
    let pos = this.pos;
    let key = [rule_name, pos];
    let seed = this.seeds[key];
    if (seed) {
        [this.val, this.failed, this.pos] = seed;
        return;
    }
    o.currentDepth += 1;
    let current = [null, true, pos];
    this.seeds[key] = current;
    let minPrec = o.currentPrec;
    let i = 0;
    while (i < o.precs.length) {
      let repeat = false;
      let prec = o.precs[i];
      let precOps = o.precOps.get(prec);
      if (prec < minPrec) {
        break;
      }
      o.currentPrec = prec;
      if (!o.rassoc.has(precOps[0])) {
        o.currentPrec += 1;
      }
      for (let j = 0; j < precOps.length; j += 1) {
        let op = precOps[j];
        o.choices.get(op).call(this);
        if (!this.failed && this.pos > pos) {
          current = [this.val, this.failed, this.pos];
          this.seeds[key] = current;
          repeat = true;
          break;
        }
        this.rewind(pos);
      }
      if (!repeat) {
        i += 1;
      }
    }

    delete this.seeds[key];
    o.currentDepth -= 1;
    if (o.currentDepth === 0) {
      o.currentPrec = 0;
    }
    [this.val, this.failed, this.pos] = current;
  }

  range(i, j) {
    let p = this.pos;
    if (p == this.end) {
      this.fail();
      return;
    }
    let c = this.text[p];
    if (i <= c && c <= j) {
      this.succeed(this.text[p], this.pos + 1);
    } else {
      this.fail();
    }
  }

  rewind(newpos) {
    this.succeed(null, newpos);
  }

  str(s) {
    for (let ch of s) {
      this.ch(ch);
      if (this.failed) {
        return;
      }
      this.val = s;
    }
  }

  succeed(v, newpos = null) {
    this.val = v;
    this.failed = false;
    if (newpos !== null) {
      this.pos = newpos;
    }
  }

  unicat(cat) {
    if (this.pos == this.end) {
      this.fail();
      return
    }
    let c = this.text[this.pos];
    let re = new RegExp(`\\\\p{${cat}}`, 'u');
    if (c.match(re)) {
      this.succeed(c, this.pos + 1);
    } else {
      this.fail();
    }
  }

  fn_atof(a) {
    return parseFloat(a)
  }

  fn_atoi(a, base) {
    return parseInt(a, base);
  }

  fn_atou(a, base) {
    return String.fromCharCode(Number.parseInt(a, base));
  }

  fn_cat(ss) {
    return ss.join('');
  }

  fn_concat(xs, ys) {
    return xs.concat(ys);
  }

  fn_cons(hd, tl) {
    return [hd].concat(tl)
  }

  fn_dedent(s) {
    return s
  }

  fn_dict(pairs) {
    let m = new Map();
    for (let [k, v] of pairs) {
      m[k] = v;
    }
    return m;
  }

  fn_itou(n) {
    return String.fromCharCode(n);
  }

  fn_join(s, vs) {
    return vs.join(s);
  }

  fn_scat(ss) {
    return ss.join('');
  }

  fn_scons(hd, tl) {
    return [hd].concat(tl);
  }

  fn_strcat(a, b) {
    return a.concat(b);
  }

  fn_unicode_lookup(s) {
    throw new ParsingRuntimeError('Unsupported function "unicode_lookup"');
  }

  fn_utoi(s) {
    return s.charCodeAt(0);
  }

  fn_xtoi(s) {
    return Number.parseInt(s, 16);
  }

  fn_xtou(s) {
    return String.fromCharCode(Number.parseInt(s, 16));
  }
"""
