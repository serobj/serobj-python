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

import inspect
from abc import ABCMeta, abstractmethod, ABC
from typing import Union, Type, Dict, Callable

_PROTOCOLS = {}  # type: Dict[str, Dict[int, Type["SerobjProtocolBase"]]]
_DEFAULT_PROTOCOL = None  # type: Type["SerobjProtocolBase"]
_DEFAULT_PROTOCOL_NAME = "serobj"

CUSTOM_NONE_TYPE = type("NoneType", (), {})()


def _set_default_protocol(protocol: Type["SerobjProtocolBase"]):
    global _DEFAULT_PROTOCOL
    _DEFAULT_PROTOCOL = protocol


def loads(proto_obj, deserializer: Callable = None):
    if deserializer:
        proto_obj = deserializer(proto_obj)  # type: Dict

    try:
        protocol_name = proto_obj["meta"]["protocol"]
        protocol_version = proto_obj["meta"]["version"]
    except (KeyError, TypeError):
        raise ValueError("`proto_obj` has not protocol and/or version information")

    try:
        protocol = _PROTOCOLS[protocol_name][
            protocol_version
        ]()  # type: SerobjProtocolBase
    except KeyError:
        raise ValueError("`proto_obj` protocol not found")

    return protocol.deserialize(proto_obj)


def dumps(
    obj,
    protocol: Union["SerobjProtocolBase", Type["SerobjProtocolBase"], str] = None,
    serializer: Callable = None,
):
    protocol = protocol or _DEFAULT_PROTOCOL

    if isinstance(protocol, str):
        protocol_tuple = protocol.split("@")
        if len(protocol_tuple) not in [1, 2]:
            raise ValueError("bad protocol argument")

        protocol_name = protocol_tuple[0]

        if len(protocol_tuple) == 2:
            try:
                protocol_version = int(protocol_tuple[1])
            except TypeError:
                raise ValueError("bad protocol version")

            protocol = _PROTOCOLS[protocol_name][protocol_version]
        else:
            protocols_dict = _PROTOCOLS[protocol_name]
            last_version = int(sorted(protocols_dict.keys())[-1])
            protocol = protocols_dict[last_version]

    if isinstance(protocol, type):
        protocol = protocol()

    if not isinstance(protocol, SerobjProtocolBase):
        raise ValueError("protocol must inherit from `SerobjProtocolBase` class")

    proto_obj = protocol.serialize(obj)

    if serializer:
        return serializer(proto_obj)
    else:
        return proto_obj


def load(file, *, deserializer: Callable = None):
    return loads(file.read(), deserializer=deserializer)


def dump(
    obj,
    file,
    *,
    protocol: Union["SerobjProtocolBase", Type["SerobjProtocolBase"], str] = None,
    serializer: Callable = None
):
    return file.write(dumps(obj, protocol=protocol, serializer=serializer))


class SerobjProtocolMeta(ABCMeta):
    def __new__(mcs, name, bases, dct, **kwargs):
        protocol_name = dct.get("PROTOCOL_NAME", None) or _DEFAULT_PROTOCOL_NAME
        protocol_version = int(dct.get("PROTOCOL_VERSION") or 0)

        dct["PROTOCOL_NAME"] = protocol_name
        dct["PROTOCOL_VERSION"] = protocol_version

        cls = super().__new__(
            mcs, name, bases, dct, **kwargs
        )  # type: Type[SerobjProtocolBase]

        if not inspect.isabstract(cls):
            if protocol_name in _PROTOCOLS and protocol_version in _PROTOCOLS.get(
                protocol_name, {}
            ):
                raise RuntimeError(
                    "Protocol '{}@{}' already registered".format(
                        protocol_name, protocol_version
                    )
                )

            proto_versions = _PROTOCOLS.get(protocol_name, {})
            proto_versions[protocol_version] = cls
            _PROTOCOLS[protocol_name] = proto_versions

            if (
                not _DEFAULT_PROTOCOL
                or protocol_name == _DEFAULT_PROTOCOL_NAME
                and _DEFAULT_PROTOCOL.PROTOCOL_VERSION < protocol_version
            ):
                _set_default_protocol(cls)

        return cls


class SerobjProtocolBase(ABC, metaclass=SerobjProtocolMeta):
    PROTOCOL_NAME = None
    PROTOCOL_VERSION = None

    def serialize(self, real_obj):
        meta = {
            "protocol": self.PROTOCOL_NAME,
            "version": self.PROTOCOL_VERSION,
        }
        payload = self._deconstruct(real_obj)

        return {"meta": meta, "payload": payload}

    def deserialize(self, proto_obj, raise_exception=True):
        if self.is_compatible_proto_obj(proto_obj, raise_exception=raise_exception):
            return self._construct(proto_obj["payload"])

    @abstractmethod
    def _construct(self, proto_obj_payload: dict) -> object:
        raise NotImplementedError

    @abstractmethod
    def _deconstruct(self, obj: object) -> dict:
        raise NotImplementedError

    @abstractmethod
    def is_compatible_proto_obj(
        self, proto_obj: dict, raise_exception: bool = True
    ) -> bool:
        raise NotImplementedError
