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
        print(cst_result.err, file=stderr)
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


def _node(parser, val, t=None, bt=None, *args):
    rule = parser._nodes[-1][1]
    begin = parser._nodes[-1][0]
    end = parser.pos()
    assert len(args) == 0

    r = {
        'r': rule,   # rule name from grammar
        'b': begin,  # beginning position
        'l': [],     # leading tokens, if any
        'v': val,    # value, if any
    }

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
        return r
    elif rule in ('ident', 'num_literal', 'string', 'null', 'bool', 't'):
        r['s'] = parser._text[begin:end]
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

    r.setdefault('t', [])  # trailing tokens, if any
    r['e'] = end   # ending position
    initial_token = parser._state.cur_token
    _assign_tokens(parser, r, t, bt)
    if not r['l']:
        del r['l']
    if not r['t']:
        del r['t']

    #assert (''.join(t[2] for t in _tokens(r) if t[0] >= r['b']) ==
    #        parser._text[r['b']:r['e']])
    return r


def _assign_tokens(parser, obj, t, bt):
    begin = obj['b']
    end = obj['e']
    rule = obj['r']
    tokens = parser._tokens

    if t:
        obj['l'].extend(t.get('l', []))
        obj['l'].extend(t.get('t', []))
    while (parser._state.cur_token < len(tokens) and
           tokens[parser._state.cur_token][0] < begin):
        obj['l'].append(tokens[parser._state.cur_token])
        parser._state.cur_token += 1
    if bt:
        f = obj
        l = None
        while True:
            if f.get('c', []):
                f = f['c'][0]
                if 'l' not in f and f.get('c', []):
                    f = f['c'][0]
                    continue
            break
        if f != obj:
            assert f['l'][0][2] == bt
            obj.setdefault('l', [])
            obj['l'].append(f['l'][0])
            f['l'] = f['l'][1:]
        else:
            assert parser._state.cur_token < len(tokens)
            assert tokens[parser._state.cur_token][2] == bt
            obj['l'].append(tokens[parser._state.cur_token])
            parser._state.cur_token += 1

    while (parser._state.cur_token < len(tokens) and
           tokens[parser._state.cur_token][0] < end):
        obj.setdefault('t', [])
        obj['t'].append(tokens[parser._state.cur_token])
        parser._state.cur_token += 1


def _tokens(node):
    toks = list(node.get('l', []))
    assert ('s' in node) ^ ('c' in node)
    if 's' in node:
        toks.append((node['b'], node['r'], node['s']))
    else:
        for c in node['c']:
            toks.extend(_tokens(c))
    toks.extend(node.get('t', []))
    return toks


if __name__ == '__main__':
    main()
