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

import builtins
import json
from collections import Iterable, Iterator, Mapping
from copy import copy
from types import BuiltinFunctionType, FunctionType, LambdaType, MethodType, ModuleType
from typing import Callable, Union, Any, Generator

from cerberus import Validator

from serobj.attrs import SerobjAttrs
from serobj.protocol.base import CUSTOM_NONE_TYPE, SerobjProtocolBase
from serobj.utils.path_to_object import get_object_source_info, import_object_source

_PROTOCOL_ID_KEY = "__id__"
_RECURSION_KEY = "__SO_RC__"  # RECURSION_COUNTER
_INIT_LIKE_NEW_KEY = "__SO_ILN__"  # INIT_LIKE_NEW

_VALIDATION_SCHEMA = {
    _PROTOCOL_ID_KEY: {"type": ["integer", "string"], "required": True},
    "source": {
        "type": "dict",
        "required": True,
        "schema": {
            "name": {"type": "string", "required": True},
            "module": {"type": "string"},
        },
        "nullable": True,
    },
    "representation": {"required": True, "nullable": True},
}
_SCHEMA_VALIDATOR = Validator(_VALIDATION_SCHEMA, allow_unknown=True)


class ZeroSerobjProtocol(SerobjProtocolBase):
    PROTOCOL_VERSION = 0

    def __init__(self):
        self._counter = 0
        self._recursion_map = {}

    @classmethod
    def _get_obj_main_attrs(cls, obj):
        def _filter(x):
            x_obj = getattr(obj, x)

            return (
                not x.startswith("_")
                and not x_obj.__class__.__module__ == "builtins"
                and not x_obj.__class__.__name__.startswith("_")
                and not hasattr(getattr(obj.__class__, x, object), "__get__")
            )

        return {k: getattr(obj, k) for k in filter(_filter, dir(obj))}

    @classmethod
    def _get_reduce_params(cls, obj, param_no, default=None):
        reduced_fn = getattr(obj, "__reduce__", None)
        if reduced_fn:
            try:
                reduced = reduced_fn()
                if reduced and reduced[0] != obj.__class__:
                    reduced = ()
                if not isinstance(reduced, Iterable) or isinstance(reduced, str):
                    reduced = ()
            except TypeError:
                reduced = ()
            return reduced[param_no] if len(reduced) > param_no else default
        else:
            return default

    @classmethod
    def _get_state_params(cls, obj, default=None) -> dict:
        getstate_fn = getattr(obj, "__getstate__", None)
        if getstate_fn:
            return getstate_fn()
        else:
            return default

    @classmethod
    def _get_attrs_filter(cls, obj: object) -> Union[FunctionType, LambdaType, bool]:
        attrs_filter_key, attrs_filter = SerobjAttrs.ATTRS_FILTER_KEY.search_attr_in(
            obj, default=None
        )
        if attrs_filter is None:
            return True
        if isinstance(attrs_filter, Mapping):

            def map_filter(_, attr_name, attr_val):
                return attrs_filter[attr_name] == attr_val

            attrs_filter = map_filter
        elif isinstance(attrs_filter, Iterable):

            def iter_filter(_, attr_name, __):
                return attr_name in attrs_filter

            attrs_filter = iter_filter
        elif not callable(attrs_filter):
            raise TypeError(
                "'{}' should be Callable or Mapping or Iterable".format(
                    attrs_filter_key
                )
            )
        return attrs_filter

    @classmethod
    def _get_attrs_by_str(cls, obj: object, key_string: str):
        if key_string == "from_reduce":
            attrs = cls._get_reduce_params(obj, 2, {})
        elif key_string == "from_getstate":
            attrs = cls._get_state_params(obj, {})
        elif key_string == "main":
            attrs = cls._get_obj_main_attrs(obj)
        else:
            attrs = getattr(obj.__class__, key_string, None) or getattr(obj, key_string)

        return attrs

    @classmethod
    def _get_default_attrs(cls, obj: object):
        attrs = cls._get_state_params(obj)

        if attrs is None or not isinstance(attrs, Mapping):
            attrs = cls._get_reduce_params(obj, 2)

        if attrs is None or not isinstance(attrs, Mapping):
            __dict__ = getattr(obj, "__dict__", None)
            if not __dict__:
                return {}
            attrs = {
                key: value
                for key, value in __dict__.items()
                if not key.startswith("__")
            }

        return attrs

    @classmethod
    def _get_attrs(cls, obj: object):
        attrs_filter = cls._get_attrs_filter(obj)
        attrs_key, attrs = SerobjAttrs.ATTRS_KEY.search_attr_in(obj, default=None)

        if attrs is None:
            attrs = cls._get_default_attrs(obj)

        if isinstance(attrs, str):
            attrs = cls._get_attrs_by_str(obj, attrs)
        if callable(attrs):
            attrs = attrs(obj)

        if isinstance(attrs, Mapping):
            attrs = dict(attrs)
        elif isinstance(attrs, Iterable):
            attrs = {k: getattr(obj, k) for k in attrs}

        if not attrs:
            return {}

        if not isinstance(attrs, Mapping):
            raise TypeError(
                "'{}' should be: str or None or Callable or Mapping or Iterable".format(
                    attrs_key
                )
            )

        return {
            k: v
            for k, v in attrs.items()
            if attrs_filter is True
            or callable(attrs_filter)
            and attrs_filter(obj, k, v)
        }

    @classmethod
    def _get_default_args(cls, obj: object, args_type: str):
        args = cls._get_reduce_params(obj, 1, None)

        if args and not isinstance(args, Iterable):
            raise TypeError("bad __reduce__ value")

        if args is not None:
            return args, {}

        if args_type == "new":
            _is_ex = True
            getargs_fn = getattr(obj, "__getnewargs_ex__", None)
            if not getargs_fn:
                getargs_fn = getattr(obj, "__getnewargs__", None)
                _is_ex = False
            if not getargs_fn:
                return None

            args = getargs_fn()

            if not isinstance(args, Iterable):
                raise TypeError(
                    "__getnewargs{}__ should return a tuple, not '{}'".format(
                        ("_ex" if _is_ex else ""), type(args).__name__
                    )
                )

            if _is_ex:
                pos_args, kwargs = args
            else:
                pos_args, kwargs = args, {}

            if not isinstance(pos_args, Iterable) or not isinstance(kwargs, Mapping):
                raise TypeError(
                    "bad __getnewargs{}__ value".format("_ex" if _is_ex else "")
                )

            return pos_args, kwargs

    @classmethod
    def _get_args(cls, obj: object, args_enum_key: SerobjAttrs):
        assert args_enum_key in (
            SerobjAttrs.NEW_ARGS_KEY,
            SerobjAttrs.INIT_ARGS_KEY,
        ), "'args_key' not in (SerobjAttrs.NEW_ARGS_KEY, SerobjAttrs.INIT_ARGS_KEY)"

        args_method_name = {
            SerobjAttrs.NEW_ARGS_KEY: "new",
            SerobjAttrs.INIT_ARGS_KEY: "init",
        }[args_enum_key]

        args_key, args = args_enum_key.search_attr_in(obj, default=CUSTOM_NONE_TYPE)

        if isinstance(args, str):
            args = getattr(obj, args, CUSTOM_NONE_TYPE)

        if args == CUSTOM_NONE_TYPE:
            _def_args = cls._get_default_args(obj, args_method_name)

            if not _def_args:
                return None

            args = [{"name": "", "value": arg} for arg in _def_args[0]] + [
                {"name": key, "value": value} for key, value in _def_args[1].items()
            ]

        if callable(args):
            if getattr(args, "__self__", CUSTOM_NONE_TYPE) == obj:
                args = args(args_method_name)
            else:
                args = args(obj, args_method_name)

            if args is not None and not isinstance(args, list):
                raise TypeError(
                    "'{}' result should be list of args "
                    "(like [{{'name': '', 'value': '123'}}, {{'name': 'kw', 'value': 'kw123'}}])".format(
                        args_method_name
                    )
                )

        return args

    @classmethod
    def _get_init_args(cls, obj):
        return cls._get_args(obj, SerobjAttrs.INIT_ARGS_KEY)

    @classmethod
    def _get_new_args(cls, obj):
        return cls._get_args(obj, SerobjAttrs.NEW_ARGS_KEY)

    @classmethod
    def _is_primitive_object(cls, obj):
        return isinstance(obj, (str, int, float, bool, None.__class__))

    @classmethod
    def _is_proto_object(cls, obj):
        try:
            return isinstance(obj, dict) and _SCHEMA_VALIDATOR.validate(obj)
        except Exception:
            return False

    @classmethod
    def _check_unsupported_types(cls, obj):
        if (
            isinstance(obj, ModuleType)
            or isinstance(obj, LambdaType)
            and obj.__name__ == "<lambda>"
            or isinstance(obj, Generator)
        ):
            raise TypeError("unsupported type: {}".format(obj))

    def _get_representation(self, obj: object):
        if obj is None:
            return None

        if isinstance(obj, (Iterable, Mapping)):
            return {"attrs": {}, "init_args": [{"name": "", "value": obj}]}

        repr_obj = {"attrs": {}}

        if isinstance(obj, type):
            return repr_obj

        elif obj.__class__.__module__ in ["builtins", "__builtins__"]:
            if obj.__class__.__name__ not in dir(builtins):
                return repr_obj

        attrs = self._get_attrs(obj)
        if attrs:
            for k, v in attrs.items():
                prepared_attr_val = self._deconstruct(v)
                if prepared_attr_val is CUSTOM_NONE_TYPE:
                    continue
                repr_obj["attrs"][k] = prepared_attr_val

        if isinstance(obj, type):
            return repr_obj

        new_args = self._get_new_args(obj)
        init_args = self._get_init_args(obj)

        def _process_args(args):
            _processed_args = []
            for arg in args:
                prepared_arg_val = self._deconstruct(arg["value"])
                if prepared_arg_val is CUSTOM_NONE_TYPE:
                    raise ValueError(
                        "'{}' is not serializable by serobj [{}.{} protocol]".format(
                            arg["value"], self.PROTOCOL_NAME, self.PROTOCOL_VERSION
                        )
                    )

                arg["value"] = prepared_arg_val

                _processed_args.append(arg)
            return _processed_args

        if new_args is not None:
            repr_obj["new_args"] = _process_args(new_args)

        if init_args is not None:
            if init_args == new_args:
                repr_obj["init_args"] = _INIT_LIKE_NEW_KEY
            else:
                repr_obj["init_args"] = _process_args(init_args)

        if new_args is None and init_args is None:
            repr_obj["new_args"] = []

        return repr_obj

    def _deconstruct(self, obj: Any):
        # ignore primitives
        if self._is_primitive_object(obj):
            return obj

        # module, lambda, generator, frame, code, traceback
        self._check_unsupported_types(obj)

        # ignore proto objects (already deconstructed)
        if self._is_proto_object(obj):
            return obj

        self._counter += 1

        _history_obj = self._recursion_map.get(id(obj))
        if _history_obj is not None:
            return {_RECURSION_KEY: _history_obj}

        self._recursion_map[id(obj)] = self._counter

        source_obj, repr_obj = obj, obj

        if isinstance(obj, Mapping):
            repr_obj = {
                self._deconstruct(k): self._deconstruct(v) for k, v in obj.items()
            }
        elif isinstance(obj, Iterator):
            source_obj, repr_obj = (
                iter([]),
                [self._deconstruct(v) for v in copy(obj)],
            )
        elif isinstance(obj, range):
            repr_obj = [obj.start, obj.stop, obj.step]
        elif isinstance(obj, Iterable):
            repr_obj = [self._deconstruct(v) for v in copy(obj)]
        elif obj.__class__ in [FunctionType, MethodType, BuiltinFunctionType]:
            repr_obj = None
        elif isinstance(obj, type):
            pass
        elif obj.__class__.__name__.startswith("_"):
            return CUSTOM_NONE_TYPE

        try:
            if isinstance(obj, (list, dict)):
                return {
                    "__id__": self._counter,
                    "source": None,
                    "representation": repr_obj,
                }

            obj_source_info = get_object_source_info(source_obj)

            try:
                import_object_source(obj_source_info["full_path"])
            except AttributeError:
                raise TypeError(
                    "unreachable code: {}".format(obj_source_info["full_path"])
                )

            return {
                "__id__": self._counter,
                "source": obj_source_info,
                "representation": self._get_representation(repr_obj),
            }
        finally:
            del self._recursion_map[id(obj)]

    def _construct_no_proto(self, obj):
        if isinstance(obj, (str, int, float, bool, None.__class__),):
            return obj

        if isinstance(obj, Mapping):
            return {self._construct(k): self._construct(v) for k, v in obj.items()}
        elif isinstance(obj, Iterable):
            return [self._construct(v) for v in obj]

        return obj

    def _construct(self, obj):
        if not isinstance(obj, dict):
            return self._construct_no_proto(obj)

        if _RECURSION_KEY in obj:
            raise ValueError("recursion is not supported yet")

        if _SCHEMA_VALIDATOR.validate(obj or {}):
            source = obj["source"]
            representation = obj["representation"]

            if not source:
                return self._construct_no_proto(representation)
        else:
            return self._construct_no_proto(obj)

        obj_source = import_object_source(source["full_path"])

        if not representation:
            return obj_source

        attrs = representation.get("attrs", {})
        new_args = representation.get("new_args", None)
        init_args = representation.get("init_args", None)

        def _construct_args(args):
            call_args, call_kwargs = [], {}
            for arg in args:
                arg_name, arg_value = arg["name"], self._construct(arg["value"])
                if arg_name:
                    call_kwargs[arg_name] = arg_value
                else:
                    call_args.append(arg_value)
            return call_args, call_kwargs

        def _get_method(enum_key, default):
            method_key, method = enum_key.search_attr_in(obj_source, default=default)
            if isinstance(method, str):
                method = getattr(obj_source, method)
            if not isinstance(method, Callable):
                raise TypeError("'{}' should be str or Callable".format(method_key))
            return method

        if new_args is not None or init_args is not None:

            method_new = _get_method(SerobjAttrs.CONSTRUCT_NEW_FN, obj_source.__new__)
            method_init = _get_method(
                SerobjAttrs.CONSTRUCT_INIT_FN, obj_source.__init__
            )

            if new_args is None:
                if init_args == _INIT_LIKE_NEW_KEY:
                    obj = obj_source
                else:
                    i_args, i_kwargs = _construct_args(init_args)

                    if obj_source == range:
                        i_args = i_args[0]

                    obj = obj_source(*i_args, **i_kwargs)
            elif init_args is None:
                n_args, n_kwargs = _construct_args(new_args)
                obj = method_new(obj_source, *n_args, **n_kwargs)
            else:
                n_args, n_kwargs = _construct_args(new_args)

                if init_args == _INIT_LIKE_NEW_KEY:
                    i_args, i_kwargs = n_args, n_kwargs
                else:
                    i_args, i_kwargs = _construct_args(init_args)

                obj = method_new(obj_source, *n_args, **n_kwargs)
                method_init(obj, *i_args, **i_kwargs)
        else:
            obj = obj_source

        state = {}

        for attr_name, attr_value in attrs.items():
            constructed_attr = self._construct(attr_value)
            state[attr_name] = constructed_attr

        if state:
            setstate_fn = getattr(obj, "__setstate__", None)
            if setstate_fn:
                setstate_fn(state)
            else:
                for attr_name, attr_value in state.items():
                    setattr(obj, attr_name, attr_value)

        return obj

    def is_compatible_proto_obj(
        self,
        proto_obj: dict,
        raise_exception: bool = True,
        allow_raw_value: bool = True,
    ) -> bool:
        if (
            isinstance(proto_obj, dict)
            and "meta" in proto_obj
            and "payload" in proto_obj
        ):

            payload = proto_obj["payload"]

            if allow_raw_value and not isinstance(payload, dict):
                return True

            try:
                if _SCHEMA_VALIDATOR.validate(payload):
                    return True
            except Exception as e:
                if raise_exception:
                    raise e

            if raise_exception:
                raise ValueError(
                    "SCHEMA_VALIDATOR: {}".format(json.dumps(_SCHEMA_VALIDATOR.errors))
                )
        else:
            if raise_exception:
                raise ValueError(
                    "`proto_obj` argument is invalid 'Serialized Proto Object'"
                )

        return False
