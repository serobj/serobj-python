<!--
 Copyright 2020 Vadim Sharay <vadimsharay@gmail.com>

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 -->

# Serobj

[![License](http://img.shields.io/:license-Apache%202-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0.txt)


_Serobj_ is a library for serializing and de-serializing program objects. 



## Getting started

Run ``pip install serobj`` to install the latest stable version from 
[PyPI](https://pypi.python.org/pypi/serobj). 


### Example:

```
import json
import serobj

def print_fn(self, *args):
    print(*args)

class A:
    print_fn = print_fn
   
    def __init__(self):
        self.some_attr = 1, 2, 3


# -------------- dump --------------

obj = A()
data = serobj.dumps(obj)

with open("A.json", "w") as f:
    json.dump(data, f, indent=4)


# -------------- load --------------

with open("A.json", "r") as f:
    data = json.load(f)
    
obj = serobj.loads(data)
obj.print_fn(*obj.some_attr) # 1 2 3

```
