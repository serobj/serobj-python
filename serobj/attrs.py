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

from enum import Enum

_MISSING_VALUE = object()


class SerobjAttrs(Enum):
    CONSTRUCT_INIT_FN = "SEROBJ__CONSTRUCT_INIT_FN"
    CONSTRUCT_NEW_FN = "SEROBJ__CONSTRUCT_NEW_FN"

    INIT_ARGS_KEY = "SEROBJ__INIT_ARGS"
    NEW_ARGS_KEY = "SEROBJ__NEW_ARGS"

    ATTRS_KEY = "SEROBJ__ATTRS"
    ATTRS_FILTER_KEY = "SEROBJ__ATTRS_FILTER"

    def search_attr_in(self, obj, name=None, default=_MISSING_VALUE):
        if name is None:
            name = self.value
        else:
            name = name.value if isinstance(name, Enum) else str(name)

        key = "_{}__{}".format(obj.__class__.__name__, name)
        val = getattr(obj, key, _MISSING_VALUE)
        if val == _MISSING_VALUE:
            key = "_{}".format(name)
            val = getattr(obj, key, _MISSING_VALUE)
        if val == _MISSING_VALUE:
            key = name
            if default == _MISSING_VALUE:
                val = getattr(obj, key)
            else:
                val = getattr(obj, key, default)

        return key, val
