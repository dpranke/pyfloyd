#!/usr/bin/env python3
import argparse
import json
import os
import sys

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

    del stdout
    # pylint: disable=protected-access
    fp = None
    msg = None
    if args.code is not None:
        msg = args.code
        path = '<code>'
    elif not args.file or args.file[1] == '-':
        path = '<stdin>'
        fp = stdin
    elif not exists(args.file):
        print(f'Error: file "{args.file}" not found.', file=stderr)
        return 1
    else:
        path = args.file
        fp = opener(path)

    externs = {}
    for d in args.define:
        k, v = d.split('=', 1)
        externs[k] = json.loads(v)

    def _node(parser, *args):
        return [
            args[0],
            args[1],
            parser._nodes[-1][0],
            parser._nodes[-1][1],
            parser._pos,
            parser
        ]

    def _f3(parser, *args):
        del parser
        fields = []
        for arg in args[0]:
            fields.append(arg[1])
        return fields

    externs['f3'] = _f3
    externs['node'] = _node

    if args.code is None:
        assert fp
        msg = fp.read()
    assert msg is not None
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
    if result.val != cst_result.val[1]:
        print("want:")
        for line in repr(result.val).splitlines():
            print('  ' + line)
        print("got:")
        for line in repr(cst_result.val).splitlines():
            print('  ' + line)

    # walk2(msg, cst_result.val)
    if args.print:
        print()
        print(json.dumps(_walk3(cst_result.val, 0)[0], indent=2))

    return 0


def _walk3(obj, pos):
    assert isinstance(obj, list) and len(obj) == 6 and isinstance(obj[2], str)
    start = obj[3]
    toks = []
    parser = obj[5]
    tokens = parser._tokens
    while tokens[pos][0] < obj[3]:
        toks.append(tokens[pos])
        pos += 1

    r = {'r': obj[2], 'b': obj[3], 'e': obj[4], 'p': toks, 'v': obj[1]}
    if obj[2] == 'grammar':
        r['v'], pos = _walk3(obj[0][0], pos)
    if obj[2] == 'value':
        if len(obj[0]) == 1:
            r['c'], pos = _walk3(obj[0][0], pos)
        elif isinstance(obj[0][1], list):
            r['c'], pos = _walk3(obj[0][1], pos)
        else:
            while tokens[pos][0] < obj[4]:
                toks.append(tokens[pos])
                pos += 1
            r['s'] = obj[0][1]
            assert toks[-1][1] == r['s']
            toks.pop()
            r['t'] = toks
    if obj[2] == 'object':
        if len(obj[0]) == 5:
            r['c'], pos = _walk3(obj[0][2], pos)
        else:
            pass
    if obj[2] == 'array':
        if len(obj[0]) == 5:
            r['c'], pos = _walk3(obj[0][2], pos)
        else:
            pass
    if obj[2] in ('ident', 'num_literal', 'string'):
        r['s'] = obj[5]._text[obj[3]:obj[4]]
        assert tokens[pos][0] == obj[3]
        assert tokens[pos][1] == r['s']
        pos += 1
    if obj[2] in ('element_list', 'member_list'):
        subs = []
        v, pos = _walk3(obj[0][0], pos)
        subs.append(v)
        for el in obj[0][1]:
            v, pos = _walk3(el[0][2], pos)
            subs.append(v)
        r['c'] = subs
    if obj[2] == 'member':
        k, pos = _walk3(obj[0][1], pos)
        v, pos = _walk3(obj[0][4], pos)
        r['c'] = [k, v]

    t = []
    while pos < len(tokens) and tokens[pos][0] < obj[4]:
        t.append(tokens[pos])
        pos += 1
    r['t'] = t
    return r, pos


def walk(s, obj, pos=0, should_print=False):
    if isinstance(obj, str):
        r = obj
        if should_print:
            print(f'{pos:5d}: {obj!r}')
        return pos + len(obj), r
    assert isinstance(obj, list)
    if obj:
        if len(obj) == 6 and isinstance(obj[2], str):
            if obj[2] in ('string', 'num_literal', 'ident', 'ws_', 'c_'):
                if should_print:
                    print(f'{pos:5d}: {repr(s[obj[3]:obj[4]])}')
                return obj[4], s[obj[3]:obj[4]]
            r = ''
            for el in obj[0]:
                pos, q = walk(s, el, pos, should_print)
                r += q
        else:
            r = ''
            for el in obj:
                pos, q = walk(s, el, pos, should_print)
                r += q
        return pos, r
    return pos, ''


def walk2(msg, obj, level=0) -> int:
    ind = '  ' * level
    if isinstance(obj, list) and obj and len(obj) == 6 and isinstance(obj[2], str):
        pos = obj[3]
        if obj[2] in ('string', 'num_literal', 'ident', 'ws_', 'c_'):
            print(f'{ind}{pos:2d}: {obj[2]}: {msg[obj[3]:obj[4]]!r}')
            return obj[4]
        print(f'{ind}{pos:2d}: {obj[2]}')
        for el in obj[0]:
            pos = walk2(msg, el, level + 1)
        return pos
    pos = 0
    for el in obj:
        if isinstance(el, str):
            print(f'{ind}--: str: {el!r}')
            continue
        pos = walk2(msg, el, level + 1)
    return pos


if __name__ == '__main__':
    main()
