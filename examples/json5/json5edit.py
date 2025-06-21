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
    arg_parser.add_argument('-o', '--output', action='store', default='-')
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

    if args.output == '-':
        out_fp = stdout
    else:
        out_fp = opener(args.output, 'w')
    print(json.dumps(cst_result.val, indent=2), file=out_fp)

    return 0


def _node(parser, *args):
    rule = parser._nodes[-1][1]
    begin = parser._nodes[-1][0]
    end = parser._pos
    val = args[0]

    r = {
        'r': rule,   # rule name from grammar
        'b': begin,  # beginning position
        'e': end,    # ending position
    }
    if len(args) > 1:
        r['bt'] = args[1] # beginning token
        r['et'] = args[2] # ending token

    # Other possible fields in a parse node:
    # 'c': children of the node, if any
    # 'v': value of the node (includes values from children)
    # 's': string representation of the node's value, if the node
    #      represents a token that isn't a comment, whitespace, or a literal).
    # 'l': any leading tokens (assigned by _assign_tokens)
    # 't': any trailing tokens (assigned by _assign_tokens)

    def _is_node(v):
        return isinstance(v, dict) and 'r' in v and 'b' in v and 'e' in v

    if rule in ('%comment', '%whitespace'):
        pass
    elif rule in ('ident', 'num_literal', 'string', 'null', 'bool'):
        r['s'] = parser._text[begin:end]
        r['v'] = val
    elif isinstance(val, list):
        # The value must be a list of nodes.
        assert rule in ('array', 'member', 'object')
        assert all(_is_node(c) for c in val)
        r['c'] = val
        vals = [c['v'] for c in val]
        r['v'] = dict(vals) if rule == 'object' else vals
    else:
        # The value must be a single (child) node.
        assert _is_node(val)
        assert rule == 'grammar'
        # Merge the child node into this node, by keeping the begin and end
        # from this node, but keeping everything else (including the rule
        # name?) from the child.
        for k in [k for k in val.keys() if k not in ('b', 'e')]:
            r[k] = val[k]

    if rule == 'grammar':
        _ = _assign_tokens(parser._tokens, r, 0)

    return r


def _assign_tokens(tokens, obj, pos):
    begin = obj['b']
    end = obj['e']
    rule = obj['r']

    while tokens[pos][0] < begin:
        obj.setdefault('l', [])
        obj['l'].append(tokens[pos])
        pos += 1
    if 'bt' in obj:
        while tokens[pos][2] != obj['bt']:
            obj.setdefault('l', [])
            obj['l'].append(tokens[pos])
            pos += 1
        obj['l'].append(tokens[pos])
        pos += 1

    assert ('c' in obj) ^ ('s' in obj)
    if 's' in obj:
        assert tokens[pos] == (obj['b'], obj['r'], obj['s'])
        pos += 1
    else:
        for c in obj['c']:
            pos = _assign_tokens(tokens, c, pos)

    while pos < len(tokens) and tokens[pos][0] < end:
        obj.setdefault('t', [])
        obj['t'].append(tokens[pos])
        pos += 1
    return pos


def _tokens(node):
    toks = list(node.get('l', []))
    assert ('s' in node) ^ ('c' in node)
    if 's' in node:
        toks.append((node['r'], node['b'], node['s']))
    else:
        for c in node['c']:
            toks.extend(_tokens(c))
    toks.extend(node.get('t', []))
    return toks


if __name__ == '__main__':
    main()
