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

import os

from setuptools import setup


def read(file_name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), file_name)
    try:
        file = open(path, encoding="utf-8")
    except TypeError:
        file = open(path)

    return file.read()


VERSION = read("serobj/VERSION").strip()
README = read("README.md").strip()
REQUIREMENTS = read("requirements/requirements.txt").strip().split("\n")
DEV_REQUIREMENTS = read("requirements/requirements.dev.txt").strip().split("\n")


setup(
    name="serobj",
    version=VERSION,
    description="Python objects serialization",
    long_description=README,
    long_description_content_type="text/markdown",
    keywords="serialization representation format serobj syrup",
    author="Vadim Sharay",
    author_email="vadimsharay@gmail.com",
    python_requires="~=3.5",
    packages=["serobj", "serobj.protocol", "serobj.utils"],
    install_requires=REQUIREMENTS,
    extras_require={"dev": DEV_REQUIREMENTS},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering",
        "Topic :: System :: Distributed Computing",
        "Topic :: Utilities",
    ],
    url="https://github.com/serobj/serobj-python",
)
