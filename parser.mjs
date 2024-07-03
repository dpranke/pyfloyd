export function parse(s) {
  console.log("in parser, s = '" + s + "'");
}

async function main() {
  const fs = await import('fs');

  let s = '';
  if (process.argv.length == 2 || process.argv[2] == '-') {
    const buffer_length = 8192;
    let chunk = new Buffer.alloc(buffer_length);
    let buf = new Buffer.alloc(0);
    let num_bytes = 0;
    let total_length = 0;
    do {
      num_bytes = fs.readSync(process.stdin.fd, chunk, 0, buffer_length);
      if (num_bytes > 0) {
        buf = Buffer.concat([buf, chunk.subarray(0, num_bytes)]);
        total_length += num_bytes;
      }
    } while (num_bytes > 0);
    s = buf.toString('utf8', 0, total_length);
  } else {
    s = fs.readFileSync(process.argv[2]);
  }
  parse(s);
}

if ((typeof process !== 'undefined') && (process.release.name === 'node')) {
  const path = await import('path');
  const url = await import('url');
  let filename = url.fileURLToPath(import.meta.url);
  if (filename === process.argv[1]) {
    main();
  }
}
