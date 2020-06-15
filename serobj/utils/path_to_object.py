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

import importlib
import re

__PATH_PATTERN = r"[a-zA-Z_][a-zA-Z_0-9]*(\.[a-zA-Z_][a-zA-Z_0-9]*)*"
FULL_PATH_REGEXP = re.compile(r"{}(:{})?".format(__PATH_PATTERN, __PATH_PATTERN))
ALIASES = {"list_iterator": "iter"}


def get_object_source_info(obj):
    if not isinstance(obj, type) and (
        not getattr(obj, "__module__", None) or type(obj).__module__ != "builtins"
    ):
        obj = type(obj)

    def replace_aliases(a_name):
        return ALIASES.get(a_name, a_name)

    name, path, module = (
        replace_aliases(obj.__name__),
        replace_aliases(obj.__qualname__),
        obj.__module__,
    )

    if "<locals>" in path:
        raise ValueError("unsupported path with locals: {}".format(path))

    return {
        "name": name,
        "module": module,
        "path": path,
        "full_path": ":".join([module, path]),
    }


def get_object_source_path(obj, full=True):
    return get_object_source_info(obj)["full_path" if full else "path"]


def import_object_source(path: str):
    assert isinstance(path, str) and FULL_PATH_REGEXP.fullmatch(
        path
    ), "`path` argument is not valid 'Path to Object'"

    if ":" in path:
        module_name, path = path.split(":")
    else:
        module_name, path = "__main__", path

    module = importlib.import_module(module_name)
    obj = module

    for token in path.split("."):
        obj = getattr(obj, token)

    return obj
