# Copyright 2020 Vadim Sharay <vadimsharay@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
from abc import ABCMeta
from typing import Mapping, Iterable

import serobj


def fn(self, arg, kw=1, *args, **kwargs):
    def inner():
        return [self, arg, kw, args, kwargs]

    return inner


class Meta(ABCMeta):
    meta_attr = 1


class CLS(metaclass=Meta):
    attr = 2

    def __init__(self):
        self.obj_attr = {"a": [1, None, True], "b": CLS, "c": 3}
        self._obj_attr = "_protected"
        self.__obj_attr = "_private"

    def __eq__(self, other: "CLS"):
        return (
            self.attr == other.attr
            and self.obj_attr == other.obj_attr
            and self._obj_attr == other._obj_attr
        )

    @classmethod
    def instance(cls):
        instance = cls()
        instance._obj_attr = "protected"
        instance.__obj_attr = "private"

        return instance


tests = [
    None,
    1,
    1.0,
    "str",
    b"str",
    True,
    {},
    [],
    set(),
    tuple(),
    {"key": 1},
    ["key", 1.0],
    {"key", b"str"},
    tuple(["key", True]),
    fn,
    type,
    Meta,
    CLS,
    Exception,
    CLS.instance(),
    Exception("exc"),
    ValueError("err"),
    dict,
    list,
    set,
    tuple,
    map,
    filter,
    reversed,
    iter,
    range,
    sorted,
    iter([1, 2, 3]),
    range(1, 10, 2),
    reversed([1, 2, 3]),
    sorted([1, 2, 3]),
    {"complex": [{1, "2", b"3"}, {"nested": True, "cls": CLS, "obj": CLS.instance()}]},
]


class TestBasicValues:
    @classmethod
    def teardown_class(cls):
        try:
            os.remove("test.json")
        except FileNotFoundError:
            pass

    @classmethod
    def check_value_factory(cls, test_obj):
        def check_value(_):
            test_obj_desc = str(test_obj)

            try:
                data = serobj.dumps(test_obj, serializer=json.dumps)

                with open("test.json", "w") as f:
                    f.write(data)
                with open("test.json", "r") as f:
                    new_data = f.read()

                new_obj = serobj.loads(new_data, deserializer=json.loads)
            except Exception as e:
                raise e.__class__(str(e) + " | " + test_obj_desc)

            if isinstance(test_obj, Exception):
                assert str(test_obj) == str(new_obj), test_obj_desc
            elif isinstance(test_obj, Mapping):
                assert dict(test_obj) == dict(new_obj), test_obj_desc
            elif isinstance(test_obj, set):
                assert set(test_obj) == set(new_obj), test_obj_desc
            elif isinstance(test_obj, Iterable):
                assert list(test_obj) == list(new_obj), test_obj_desc
            else:
                assert test_obj == new_obj, test_obj_desc

        return check_value


for i, obj in enumerate(tests, start=1):
    setattr(
        TestBasicValues, "test_{}".format(i), TestBasicValues.check_value_factory(obj)
    )
