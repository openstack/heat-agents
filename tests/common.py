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

import json
import os
import subprocess

import testtools


class RunScriptTest(testtools.TestCase):

    def relative_path(self, from_path, *to_paths):
        return os.path.join(
            os.path.dirname(os.path.realpath(from_path)), *to_paths)

    def run_cmd(self, args, env, input_str=None):
        subproc = subprocess.Popen(args,
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   env=env)
        if input_str:
            input_str = input_str.encode('utf-8')
        stdout, stderr = subproc.communicate(input=input_str)
        return subproc.returncode, stdout, stderr

    def json_from_file(self, path):
        with open(path) as f:
            return json.load(f)

    def json_from_files(self, path, count, delete_after=True):
        for i in range(count + 1):
            if i == 0:
                filename = path
            else:
                filename = '%s_%d' % (path, i)

            # check there are not more files than the exact number requested
            if i == count:
                self.assertFalse(
                    os.path.isfile(filename),
                    'More than %d invocations' % count
                )
            else:
                with open(filename) as f:
                    yield json.load(f)
                if delete_after:
                    os.remove(filename)
