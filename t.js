#!/usr/bin/env node

function parse(s, path = "<string>") {
  const p = new Parser(s, path);
  return p.parse();
}

class Result {
  constructor(val, err, pos) {
    this.val = val;
    this.err = err;
    this.pos = pos;
  }
}

class Parser {
  constructor(text, path) {
    this.text = text;
    this.path = path;
    this.end = this.text.length;
    this.errpos = 0;
    this.failed = false;
    this.pos = 0;
    this.val = null;
  }

  parse() {
    this.grammar();
    if (this.failed) {
      return new Result(null, this._err_str(), this.errpos);
    }
    return new Result(this.val, null, this.pos);
  }

  _err_offsets() {
    let lineno = 1;
    let colno = 1;
    for (let i = 0; i < this.errpos; i++) {
      if (this.text[i] == "\n") {
        lineno += 1;
        colno = 1;
      } else {
        colno += 1;
      }
    }
    return [lineno, colno];
  }

  _err_str() {
    let [lineno, colno] = this._err_offsets();
    let thing;
    if (this.errpos == this.text.length) {
      thing = "end of input";
    } else {
      thing = `"${this.text[this.errpos]}"`;
    }
    return `${this.path}:${lineno} Unexpected ${thing} at column ${colno}`;
  }

  grammar() {
    this.succeed(true);
  }

  fail() {
    this.val = null;
    this.failed = true;
    this.errpos = Math.max(this.errpos, this.pos);
  }

  succeed(val, newpos = undefined) {
    this.val = val;
    this.failed = false;
    if (newpos != undefined) {
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

  let result = parse(s);
  if (result.err != undefined) {
    console.log(`err = ${result.err}`);
  } else {
    console.log(result.val);
  }
}

if (typeof process !== "undefined" && process.release.name === "node") {
  (async () => {
    main();
  })();
}