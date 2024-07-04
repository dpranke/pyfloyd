#!/usr/bin/env node
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

  parse() {
    this.#_r_grammar_();
    if (this.failed) {
      return new Result(null, this.#error(), this.errpos);
    } else {
      return new Result(this.val, null, this.pos);
    }
  }

  #_r_grammar_() {
    let p = this.pos
    this.#_s_grammar_1_()
    if (!this.failed) {
      return;
    }
    this.#rewind(p)
    this.#_s_grammar_2_()
  }

  #_s_grammar_1_() {
    this.#str('foo')
    if (!this.failed) {
      this.#succeed(true)
    }
  }

  #_s_grammar_2_() {
    this.#str('bar')
    if (!this.failed) {
      this.#succeed(false)
    }
  }

  #ch(ch) {
     let p = this.pos;
     if (p < this.end && this.text[p] === ch) {
       this.#succeed(ch, this.pos + 1);
     } else {
       this.#fail();
    }
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


  #errorOffsets() {
    let lineno = 1;
    let colno = 1;
    for (let i = 0; i < this.errpos ; i++) {
      if (this.text[i] === '\n') {
        lineno += 1;
        colno = 1;
      } else {
        colno += 1;
      }
    }
    return [lineno, colno];
  }


  #fail() {
    this.val = undefined;
    this.failed = true;
    this.errpos = Math.max(this.errpos, this.pos);
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
}

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
