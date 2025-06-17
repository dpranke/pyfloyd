#!/usr/bin/env python3
import argparse
import json
import os
import sys

import json
import json5
import json5_cst

def main(
    argv=sys.argv[1:],
    stdin=sys.stdin,
    stdout=sys.stdout,
    stderr=sys.stderr,
    exists=os.path.exists,
    opener=open,
) -> int:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-p', '--print', action='store_true')
    arg_parser.add_argument('-c', '--code')
    arg_parser.add_argument(
        '-D',
        '--define',
        action='append',
        metavar='var=val',
        default=[],
        help='define an external var=value (may use multiple times)'
    )
    arg_parser.add_argument('file', nargs='?')
    args = arg_parser.parse_args(argv)

    if args.code is not None:
        msg = args.code
        path = '<code>'
    elif not args.file or args.file[1] == '-':
        path = '<stdin>'
        fp = stdin
    elif not exists(args.file):
        print('Error: file "%s" not found.' % args.file, file=stderr)
        return 1
    else:
        path = args.file
        fp = opener(path)

    externs = {}
    for d in args.define:
        k, v = d.split('=', 1)
        externs[k] = json.loads(v)

    def _node(parser, *args):
        return list(args) + [-1, parser._pos]

    def _f3(parser, *args):
        del parser
        l = []
        for arg in args[0]:
            l.append(arg[3])
        return l

    externs['f3'] = _f3
    externs['node'] = _node

    if args.code is None:
        msg = fp.read()
    result = json5.parse(msg, path)
    cst_result = json5_cst.parse(msg, path, externs)
    if result.err:
        print(result.err, file=stderr)
        return 1

    pos, r = walk(msg, cst_result.val, should_print=False)
    if pos != len(msg) or r != msg:
        print("want:")
        print('  ' + repr(msg))
        print("got:")
        print('  ' + repr(r))
    if result.val != cst_result.val[3]:
        print("want:")
        for l in repr(result.val):
            print('  ' + l)
        print("got:")
        for l in repr(cst_result.val):
            print('  ' + l)
    if args.print:
        print()
        print(json.dumps(cst_result.val, indent=2))

    return 0


def walk(s, obj, pos=0, should_print=False):
    if isinstance(obj, str):
        r = obj
        if should_print:
            print(f'{pos:5d}: {obj!r}')
        return pos + len(obj), r
    assert isinstance(obj, list)
    if obj:
        if isinstance(obj[0], str):
            obj[4] = pos
            if obj[0] in ('string', 'num_literal', 'ident'):
                if should_print:
                    print(f'{pos:5d}: {repr(s[pos:obj[5]])}')
                return obj[5], s[pos:obj[5]]
            r = ''
            for el in obj[1]:
                pos, q = walk(s, el, pos, should_print)
                r += q
        else:
            r = ''
            for el in obj:
                pos, q = walk(s, el, pos, should_print)
                r += q
        return pos, r
    return pos, ''


if __name__ == '__main__':
    main()
