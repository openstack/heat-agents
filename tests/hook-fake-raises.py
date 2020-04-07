#!/usr/bin/env python
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
'''
A fake heat-config hook for unit testing the 55-heat-config
os-refresh-config script, this version raises an error.
'''

import json
import os
import sys


def main(argv=sys.argv):
    c = json.load(sys.stdin)

    inputs = {}
    for input in c['inputs']:
        inputs[input['name']] = input.get('value', '')

    # write out stdin json for test asserts
    stdin_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '%s.stdin' % c['group'])

    with open(stdin_path, 'w') as f:
        json.dump(c, f)
        f.flush()
    raise OSError("Something bad happened!")


if __name__ == '__main__':
    sys.exit(main(sys.argv))
