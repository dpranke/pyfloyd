# Copyright 2024 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
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

import unittest

from pyfloyd.formatter import (
    flatten,
    flatten_as_lisplist,
    from_list,
    to_list,
    to_lisplist,
    Comma,
    Hang,
    HList,
    Indent,
    LispList as LL,
    Pack,
    Triangle,
    Tree,
    VList,
    Wrap,
)


class Tests(unittest.TestCase):
    def test_comma(self):
        t = Comma('1', '2', '3')
        self.assertEqual(['1, 2, 3'], flatten(t))

        t = Comma('1', Triangle('[', Comma('2'), ']'))
        self.assertEqual(['1, [2]'], flatten(t))

        # This tests an array that needs to span multiple lines.
        t = Comma(
            'self._long_rule_1',
            'self._long_rule_2',
            'self._long_rule_3',
            'self._long_rule_4',
            'self._long_rule_5',
        )
        self.assertEqual(
            [
                'self._long_rule_1,',
                'self._long_rule_2,',
                'self._long_rule_3,',
                'self._long_rule_4,',
                'self._long_rule_5,',
            ],
            flatten(t),
        )

    def test_comma_repr(self):
        self.assertEqual("Comma('1', '2')", repr(Comma('1', '2')))
        self.assertEqual(
            "Comma('1', Triangle('[', Comma('2'), ']'))",
            repr(Comma('1', Triangle('[', Comma('2'), ']'))),
        )

    def test_complex(self):
        obj = Pack(
            'self._o_succeed',
            Triangle(
                '(',
                Triangle(
                    '[',
                    Comma(
                        Pack(
                            'self._fn_strcat',
                            Triangle(
                                '(',
                                Comma(
                                    "'L'",
                                    Pack(
                                        'self._o_lookup',
                                        Triangle('(', Comma("'lq'"), ')'),
                                    ),
                                ),
                                ')',
                            ),
                        ),
                        'v_c',
                        'v_s',
                    ),
                    ']',
                ),
                ')',
            ),
        )
        self.assertEqual(
            [
                (
                    "self._o_succeed([self._fn_strcat('L', "
                    "self._o_lookup('lq')), v_c, v_s])"
                ),
            ],
            flatten(obj, 71),
        )

    def test_complex_2(self):
        lines = flatten(
            Pack(
                'self._succeed',
                Triangle(
                    '(',
                    Pack(
                        'self.xtou',
                        Triangle(
                            '(',
                            Comma(
                                Tree(
                                    "self._get('long_variable_1')",
                                    '+',
                                    Tree(
                                        "self._get('long_variable_2')",
                                        '+',
                                        "self._get('long_variable_3')",
                                    ),
                                )
                            ),
                            ')',
                        ),
                    ),
                    ')',
                ),
            )
        )
        self.assertEqual(
            [
                'self._succeed(',
                '    self.xtou(',
                "        self._get('long_variable_1')",
                "        + self._get('long_variable_2')",
                "        + self._get('long_variable_3')",
                '    )',
                ')',
            ],
            lines,
        )

    def test_complex_3(self):
        obj = Pack(
            'self._o_succeed',
            Triangle(
                '(',
                Comma(
                    Triangle(
                        "self._externs['node'](",
                        Comma(
                            'self',
                            Triangle(
                                '[',
                                Comma(
                                    "'range'",
                                    Triangle(
                                        '[',
                                        Comma('v__1', 'v__3'),
                                        ']',
                                    ),
                                    '[]'
                                ),
                                ']'
                            )
                        ),
                        ')'
                    ),
                'self._pos'
                ),
                ')'
            )
        )
        self.assertEqual(
            [
                'self._o_succeed(',
                "    self._externs['node'](self, ['range', [v__1, v__3], []]), self._pos",
                ')'
            ],
            flatten(obj, 71)
        )

    def test_from_list(self):
        obj = [
            'comma',
            '1',
            '2',
            ['ind', ['hl', '3', '4']],
            ['ll', '6'],
            ['tri', '7', '8', '9'],
            ['tree', '10', '+', '11'],
            ['vl', '12', '13'],
        ]
        lis = from_list(obj)
        expected_obj = Comma(
            '1',
            '2',
            Indent(HList('3', '4')),
            LL('6'),
            Triangle('7', '8', '9'),
            Tree('10', '+', '11'),
            VList('12', '13'),
        )
        self.assertEqual(lis, expected_obj)

    def test_hang(self):
        obj = Hang([], ' ')
        self.assertEqual([], flatten(obj))

        obj = Hang(['1'], ' ')
        self.assertEqual(['1'], flatten(obj))

        obj = Hang(['1', '2'], ' ')
        self.assertEqual(['1 2'], flatten(obj))

        obj = Hang(['very', 'long', 'argument'], ' ')
        self.assertEqual(['very long argument'], flatten(obj, length=None))
        self.assertEqual(['very long argument'], flatten(obj, length=50))
        self.assertEqual(
            ['very long', '     argument'], flatten(obj, length=10)
        )

        # Test that the first two arguments are always on the first line,
        # even if that makes the line be too long.
        self.assertEqual(
            ['very long', '     argument'], flatten(obj, length=6)
        )

    def test_hlist(self):
        obj = HList()
        self.assertEqual([''], flatten(obj))

        obj = HList('1')
        self.assertEqual(['1'], flatten(obj))

        obj = HList('1', '2')
        self.assertEqual(['12'], flatten(obj))

        obj = HList('1', HList('2', '3'))
        self.assertEqual(['123'], flatten(obj))

    def test_hlist_collapsing(self):
        obj = HList()
        self.assertEqual(obj.objs, [])
        obj = HList(HList())
        self.assertEqual(obj.objs, [])
        obj = HList('1', HList('2', '3'))
        self.assertEqual(obj.objs, ['1', '2', '3'])
        obj = HList(['1', '2'], '3', HList('4'))
        self.assertEqual(obj.objs, ['1', '2', '3', '4'])

    def test_indent(self):
        obj = Indent(VList('1', '2'))
        self.assertEqual(['    1', '    2'], flatten(obj))

    def test_indent_collapsing(self):
        self.assertEqual(Indent().objs, [])
        self.assertEqual(Indent([]).objs, [])
        self.assertEqual(Indent(None).objs, [])
        self.assertEqual(Indent(None, [], VList()).objs, [])
        self.assertEqual(
            Indent('1', None, ['2', '3'], VList('4'), VList()).objs,
            ['1', '2', '3', '4'],
        )

        # test that indents are *not* collapsed.
        self.assertEqual(
            Indent('foo', Indent('bar')).objs, ['foo', Indent('bar')]
        )

    def test_line_too_long(self):
        long_str = (
            'this is a string line that stretches out for a'
            'really long time and will not fit on one line'
        )
        self.assertEqual([long_str], flatten(long_str))

    def test_lisplist(self):
        self.assertEqual(['[]'], flatten(LL()))

        self.assertEqual(['[1]'], flatten(LL('1')))

        lis = LL('1', '2', '3')
        self.assertEqual(['[1 2 3]'], flatten(lis))

        lis = LL('foo', LL('fn', LL('arg'), LL('length', 'arg')))
        self.assertEqual(['[foo [fn [arg] [length arg]]]'], flatten(lis))
        self.assertEqual(
            ['[foo [fn [arg]', '         [length arg]]]'],
            flatten(lis, length=14),
        )

    def test_pack(self):
        # test short triangle cases.
        t = Pack('foo', Triangle('(', '0', ')'))
        self.assertEqual(['foo(0)'], flatten(t))

        t = Pack('foo', Triangle('(', '0', ')'), Triangle('(', '0', ')'))
        self.assertEqual(['foo(0)(0)'], flatten(t))

        # Test case where the first arg isn't a string.
        t = Pack(Triangle('[', Comma('1'), ']'), Triangle('[', '0', ']'))
        self.assertEqual(['[1][0]'], flatten(t))

        # Test the three different cases for a pack with one long triangle.
        t = Pack(
            'foobar',
            Triangle(
                '(',
                Comma(
                    'self._long_rule_1',
                    'self._long_rule_2',
                    'self._long_3',
                    'self._long4',
                ),
                ')',
            ),
        )
        self.assertEqual(
            [
                (
                    'foobar(self._long_rule_1, self._long_rule_2, self._long_3, '
                    'self._long4)'
                ),
            ],
            flatten(t, length=74),
        )

        self.assertEqual(
            [
                'foobar(',
                (
                    '    self._long_rule_1, self._long_rule_2, self._long_3, '
                    'self._long4'
                ),
                ')',
            ],
            flatten(t, length=70),
        )
        self.assertEqual(
            [
                'foobar(',
                '    self._long_rule_1,',
                '    self._long_rule_2,',
                '    self._long_3,',
                '    self._long4,',
                ')',
            ],
            flatten(t, length=66),
        )

        t = Pack(
            'foo',
            Triangle(
                '(',
                Comma(
                    'self._long_rule_1',
                    'self._long_rule_2',
                    'self._long_rule_3',
                    'self._long_rule_4',
                    'self._long_rule_5',
                    'self._long_rule_6',
                ),
                ')',
            ),
            Triangle('[', '4', ']'),
        )
        self.assertEqual(
            [
                'foo(',
                '    self._long_rule_1,',
                '    self._long_rule_2,',
                '    self._long_rule_3,',
                '    self._long_rule_4,',
                '    self._long_rule_5,',
                '    self._long_rule_6,',
                ')[4]',
            ],
            flatten(t),
        )

    def test_str(self):
        self.assertEqual([''], flatten(''))
        self.assertEqual(['foo'], flatten('foo'))
        self.assertEqual(['foo', 'bar'], flatten('foo\nbar'))

        # TODO: Is this the behavior we want, or should there be
        # one more line on each?
        self.assertEqual(['foo', 'bar'], flatten('foo\nbar\n'))
        self.assertEqual([''], flatten('\n'))
        self.assertEqual(['foo'], flatten('foo\n'))

    def test_tree(self):
        t = Tree('1', '+', '2')
        self.assertEqual(['1 + 2'], flatten(t))
        t = Tree(
            "'long string 1'",
            '+',
            Tree(
                "'long string 2'",
                '+',
                Tree(
                    "'long string 3'",
                    '+',
                    Tree("'long string 4'", '+', "'long string5'"),
                ),
            ),
        )
        self.assertEqual(
            [
                "'long string 1'",
                "+ 'long string 2'",
                "+ 'long string 3'",
                "+ 'long string 4'",
                "+ 'long string5'",
            ],
            flatten(t),
        )

    def test_tree_repr(self):
        self.assertEqual("Tree('1', '+', '2')", repr(Tree('1', '+', '2')))
        self.assertEqual(
            "Tree('1', '+', Tree('2', '+', '3'))",
            repr(Tree('1', '+', Tree('2', '+', '3'))),
        )

    def test_tri(self):
        self.assertEqual(['(1)'], flatten(Triangle('(', '1', ')')))
        t = Triangle('(', Comma('foo', 'bar', 'baz', 'qux'), ')')
        self.assertEqual(
            ['(', '    foo,', '    bar,', '    baz,', '    qux,', ')'],
            flatten(t, 10),
        )

    def test_vlist(self):
        self.assertEqual([], flatten(VList()))
        self.assertEqual([''], flatten(VList('')))
        self.assertEqual(['1', '2'], flatten(VList('1', '2')))
        vl = VList()
        vl += 'foo\nbar'
        vl += ''
        vl += 'baz'
        vl += VList('1', '2')
        self.assertEqual(['foo', 'bar', '', 'baz', '1', '2'], flatten(vl))

    def test_vlist_collapsing(self):
        self.assertEqual(VList().objs, [])
        self.assertEqual(VList([]).objs, [])
        self.assertEqual(VList(None).objs, [])
        self.assertEqual(VList(None, [], VList()).objs, [])
        self.assertEqual(
            VList('1', None, ['2', '3'], VList('4'), VList()).objs,
            ['1', '2', '3', '4'],
        )

        # test that indents are *not* collapsed.
        self.assertEqual(
            VList('foo', Indent('bar')).objs, ['foo', Indent('bar')]
        )

    def test_wrap(self):
        args = ['prefix ', ' suffix', 'first  ', ' last  ']

        w = Wrap('str', *args)
        self.assertEqual(['first  str last'], flatten(w))

        w = Wrap(HList(), *args)
        self.assertEqual(['first   last'], flatten(w))

        w = Wrap(HList('foo', 'bar'), *args)
        self.assertEqual(['first  foobar last'], flatten(w))

        w = Wrap(VList('foo', 'bar'), *args)
        self.assertEqual(['first  foo suffix', 'prefix bar last'], flatten(w))

        w = Wrap(Hang(['foo', 'bar', 'baz'], ' '), '#  ', ' \\', '# `', '`')
        self.assertEqual(['# `foo bar baz`'], flatten(w))
        self.assertEqual(
            ['# `foo bar \\', '#      baz`'], flatten(w, length=10)
        )


class AsListTests(unittest.TestCase):
    def check(
        self,
        obj,
        expected_list,
        expected_lisp_obj,
        expected_lines,
        line_length=79,
        indent='    ',
    ):
        actual_list = to_list(obj)
        self.assertEqual(expected_list, actual_list)

        actual_lisp_obj = to_lisplist(obj)
        self.assertEqual(expected_lisp_obj, actual_lisp_obj)

        actual_lines = flatten_as_lisplist(obj, line_length, indent)
        self.assertEqual(expected_lines, actual_lines)

    def test_comma(self):
        self.check(
            Comma('1', '2', Indent('bar')),
            ['comma', '1', '2', ['ind', 'bar']],
            LL('comma', '1', '2', LL('ind', 'bar')),
            ["[comma '1' '2' [ind 'bar']]"],
        )

    def test_hlist(self):
        self.check(
            HList('foo', Indent('bar')),
            ['hl', 'foo', ['ind', 'bar']],
            LL('hl', 'foo', LL('ind', 'bar')),
            ["[hl 'foo' [ind 'bar']]"],
        )

    def test_indent(self):
        self.check(
            Indent('foo'), ['ind', 'foo'], LL('ind', 'foo'), ["[ind 'foo']"]
        )
        self.check(
            Indent(VList('foo', 'bar')),
            ['ind', 'foo', 'bar'],
            LL('ind', 'foo', 'bar'),
            ["[ind 'foo' 'bar']"],
        )

    def test_pack(self):
        self.check(
            Pack('foo', Triangle('(', '4', ')')),
            ['pack', 'foo', ['tri', '(', '4', ')']],
            LL('pack', 'foo', LL('tri', '(', '4', ')')),
            ["[pack 'foo' [tri '(' '4' ')']]"],
        )
        self.check(
            Pack('foo', Triangle('(', '4', ')'), Triangle('[', 'a', ']')),
            ['pack', 'foo', ['tri', '(', '4', ')'], ['tri', '[', 'a', ']']],
            LL(
                'pack',
                'foo',
                LL('tri', '(', '4', ')'),
                LL('tri', '[', 'a', ']'),
            ),
            ["[pack 'foo' [tri '(' '4' ')'] [tri '[' 'a' ']']]"],
        )

    def test_str(self):
        self.check('foo', 'foo', 'foo', ["'foo'"])
        self.check('foo\n', 'foo\n', 'foo\n', ["'foo'"])
        self.check(
            'foo\nbar',
            'foo\nbar',
            'foo\nbar',
            ['(', "    'foo'", "    'bar'", ')'],
        )
        self.check(
            'foo\nbar\n',
            'foo\nbar\n',
            'foo\nbar\n',
            ['(', "    'foo'", "    'bar'", ')'],
        )

    def test_tree(self):
        self.check(
            Tree('1', '+', Tree('2', '+', '3')),
            ['tree', '1', '+', ['tree', '2', '+', '3']],
            LL('tree', '1', '+', LL('tree', '2', '+', '3')),
            ["[tree '1' '+' [tree '2' '+' '3']]"],
        )

    def test_vlist(self):
        self.check(
            VList(),
            ['vl'],
            LL('vl'),
            ['[vl]'],
        )
        self.check(VList([]), ['vl'], LL('vl'), ['[vl]'])

        self.check(
            VList('1'),
            ['vl', '1'],
            LL('vl', '1'),
            ["[vl '1']"],
        )
        self.check(
            VList('1', '2'),
            ['vl', '1', '2'],
            LL('vl', '1', '2'),
            ["[vl '1' '2']"],
        )

        self.check(
            VList('1', None, ['2', '3'], VList('4'), VList()),
            ['vl', '1', '2', '3', '4'],
            LL('vl', '1', '2', '3', '4'),
            ["[vl '1' '2' '3' '4']"],
        )

        self.check(
            VList('foo', VList('bar')),
            ['vl', 'foo', 'bar'],
            LL('vl', 'foo', 'bar'),
            ["[vl 'foo' 'bar']"],
        )

        # test that indents are *not* collapsed.
        self.check(
            VList('foo', Indent('bar')),
            ['vl', 'foo', ['ind', 'bar']],
            LL('vl', 'foo', LL('ind', 'bar')),
            ["[vl 'foo' [ind 'bar']]"],
        )
