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

    def _node(parser, *args):
        return [
            parser._nodes[-1][1],
            parser._nodes[-1][0],
            parser._pos,
            args[0],
            parser
        ]

    externs['node'] = _node

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

    val, pos = _val(cst_result.val, 0)
    assert pos == len(cst_result.val[4]._tokens)
    tokens = _tokens(val)
    new_msg = ''.join(t[1] for t in tokens)
    assert new_msg == msg
    if args.print:
        print()
        print(json.dumps(val, indent=2), file=stdout)

    return 0


def _val(obj, pos):
    assert isinstance(obj, list) and len(obj) == 5 and isinstance(obj[0], str)
    rule, begin, end, val, parser = obj
    tokens = parser._tokens
    r = {
        'r': rule,
        'v': None,
        's': None,
        'b': begin,
        'l': [],
        'c': [],
        't': [],
        'e': end
    }

    while tokens[pos][0] < begin:
        r['l'].append(tokens[pos])
        pos += 1

    def _merge(outer, inner, rule):
        return {
            'r': rule,
            'v': inner['v'],
            'b': outer['b'],
            'l': outer['l'] + inner['l'],
            'c': inner['c'],
            't': inner['t'],
            'e': outer['e'],
        }

    if rule == 'grammar':
        v, pos = _val(val, pos)
        r = _merge(r, v, v['r'])
    elif rule == 'object':
        if val != []:
            v, pos = _val(val, pos)
            r = _merge(r, v, r['r'])
            pairs = [c['v'] for c in r['c']]
            r['v'] = dict(pairs)
        else:
            r['v'] = {}
    elif rule == 'array':
        if val != []:
            v, pos = _val(val, pos)
            r = _merge(r, v, r['r'])
            r['v'] = [c['v'] for c in r['c']]
        else:
            r['v'] = []
    elif rule in ('ident', 'num_literal', 'string', 'null', 'bool'):
        r['s'] = parser._text[begin:end]
        r['v'] = val
    elif rule in ('element_list', 'member', 'member_list'):
        for el in val:
            v, pos = _val(el, pos)
            r['c'].append(v)
        r['v'] = [c['v'] for c in r['c']]
    else:
        assert False

    while pos < len(tokens) and tokens[pos][0] < end:
        r['t'].append(tokens[pos])
        pos += 1
    return r, pos


def _tokens(val):
    toks = list(val['l'])
    for c in val['c']:
        toks.extend(_tokens(c))
    toks.extend(val['t'])
    return toks


if __name__ == '__main__':
    main()
