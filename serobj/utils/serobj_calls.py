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

import functools
import inspect
from abc import ABCMeta

from serobj.attrs import SerobjAttrs

_CALLS = {}


def _register_call(obj, args, kwargs):
    call_args = []

    sign = inspect.signature(obj.__init__)
    parameters = sign.parameters
    bound_parameters = sign.bind(*args, **kwargs)
    bound_parameters.apply_defaults()

    for arg_name, arg_value in bound_parameters.arguments.items():
        parameter = parameters[arg_name]

        if parameter.kind in [
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ]:
            call_args.append({"name": "", "value": arg_value})
        elif parameter.kind == inspect.Parameter.VAR_POSITIONAL:
            for _arg_value in arg_value:
                call_args.append({"name": "", "value": _arg_value})
        elif parameter.kind == inspect.Parameter.KEYWORD_ONLY:
            call_args.append({"name": arg_name, "value": arg_value})
        elif parameter.kind == inspect.Parameter.VAR_KEYWORD:
            for _arg_name, _arg_value in arg_value.items():
                call_args.append({"name": _arg_name, "value": _arg_value})

    _CALLS[id(obj)] = call_args


class SerobjCallsMetaClass(ABCMeta):
    def __new__(mcs, name, bases, dct):
        old_init = dct.get("__init__")
        if not old_init:
            for b in bases:
                old_init = getattr(b, "__init__", None)
                if old_init:
                    break

        @functools.wraps(old_init or type.__init__)
        def __init__(self, *args, **kwargs):
            _register_call(self, args, kwargs)

            if old_init:
                old_init(self, *args, **kwargs)

        def __getserobjargs__(self, method_name, *args):
            if method_name != "init":
                return None
            return _CALLS.get(id(self))

        dct["__init__"] = __init__
        dct["__getserobjargs__"] = __getserobjargs__
        dct["_{}".format(SerobjAttrs.INIT_ARGS_KEY.value)] = "__getserobjargs__"
        dct["_{}".format(SerobjAttrs.NEW_ARGS_KEY.value)] = "__getserobjargs__"

        return super().__new__(mcs, name, bases, dct)


class SerobjCallsBase(metaclass=SerobjCallsMetaClass):
    pass
