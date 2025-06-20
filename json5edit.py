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

    def _dict(pairs):
        return pairs

    externs['node'] = _node
    externs['dict'] = _dict

    if args.code is None:
        assert fp
        msg = fp.read()

    assert msg is not None
    result = json5.parse(msg, path)
    cst_result = json5_cst.parse(msg, path, externs)

    if result.err:
        print(result.err, file=stderr)
    if cst_result.err:
        print(result.err, file=stderr)
    if result.err or cst_result.err:
        return 1

    assert result.val == cst_result.val['v']

    tokens = _tokens(cst_result.val)
    new_msg = ''.join(t[2] for t in tokens)
    assert new_msg == msg

    if args.print:
        print()
        print(json.dumps(cst_result.val, indent=2), file=stdout)

    return 0


def _node(parser, *args):
    rule = parser._nodes[-1][1]
    begin = parser._nodes[-1][0]
    end = parser._pos
    val = args[0]

    r = {
        'r': rule,
        'v': None,
        's': None,
        'b': begin,
        'l': [],
        'c': [],
        't': [],
        'e': end,
    }

    if rule == 'grammar':
        r['r'] = val['r']
        r['v'] = val['v']
        r['c'] = val['c']
        _ = _assign_tokens(parser._tokens, r, 0)
    elif rule in ('array', 'member', 'object'):
        r['c'] = val
        if r['c']:
            v = [c['v'] for c in r['c']]
        else:
            v = []
        r['v'] = dict(v) if rule == 'object' else v
    elif rule in ('ident', 'num_literal', 'string', 'null', 'bool'):
        r['s'] = parser._text[begin:end]
        r['v'] = val
    elif rule in ('%comment', '%whitespace'):
        pass
    else:
        assert False
    return r


def _assign_tokens(tokens, obj, pos):
    begin = obj['b']
    end = obj['e']
    rule = obj['r']

    while tokens[pos][0] < begin:
        obj['l'].append(tokens[pos])
        pos += 1

    for c in obj['c']:
        pos = _assign_tokens(tokens, c, pos)

    while pos < len(tokens) and tokens[pos][0] < end:
        obj['t'].append(tokens[pos])
        pos += 1
    return pos


def _tokens(val):
    toks = list(val['l'])
    for c in val['c']:
        toks.extend(_tokens(c))
    toks.extend(val['t'])
    return toks


if __name__ == '__main__':
    main()
