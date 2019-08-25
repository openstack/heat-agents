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

import mock
from six.moves import cStringIO as StringIO

from tests import common
from tests import hook_docker_cmd


class HookDockerCmdTest(common.RunScriptTest):
    data = {
        "name": "abcdef001",
        "group": "docker-cmd",
        "id": "abc123",
        "inputs": [{
            "name": "deploy_stack_id",
            "value": "the_stack",
        }, {
            "name": "deploy_resource_name",
            "value": "the_deployment",
        }],
        "config": {
            "db": {
                "name": "x",
                "image": "xxx",
                "privileged": False,
                "environment": ["foo=bar"],
                "env_file": "env.file",
                "start_order": 0
            },
            "web-ls": {
                "action": "exec",
                "start_order": 2,
                "command": ["web", "/bin/ls", "-l"]
            },
            "web": {
                "name": "y",
                "start_order": 1,
                "image": "yyy",
                "net": "host",
                "restart": "always",
                "privileged": True,
                "user": "root",
                "command": "/bin/webserver start",
                "volumes": [
                    "/run:/run",
                    "db:/var/lib/db"
                ],
                "environment": [
                    "KOLLA_CONFIG_STRATEGY=COPY_ALWAYS",
                    "FOO=BAR"
                ],
                "env_file": [
                    "foo.env",
                    "bar.conf"
                ]
            }
        }
    }

    @mock.patch('paunch.apply', autospec=True)
    def test_hook(self, mock_apply):
        mock_apply.return_value = (['it', 'done'], ['one', 'two', 'three'], 0)
        stdin = StringIO(json.dumps(self.data))
        stdout = StringIO()
        stderr = StringIO()
        hook_docker_cmd.main(
            ['/path/to/hook-docker-cmd'], stdin, stdout, stderr)
        mock_apply.assert_called_once_with(
            'abc123',
            self.data['config'],
            'docker-cmd',
            {
                'deploy_stack_id': 'the_stack',
                'deploy_resource_name': 'the_deployment'
            },
            'docker'
        )

        resp = json.loads(stdout.getvalue())

        self.assertEqual({
            'deploy_status_code': 0,
            'deploy_stderr': 'one\ntwo\nthree',
            'deploy_stdout': 'it\ndone'
        }, resp)

    @mock.patch('paunch.apply', autospec=True)
    def test_missing_config(self, mock_apply):
        data = {
            "name": "abcdef001",
            "group": "docker-cmd",
            "id": "abc123",
        }
        stdin = StringIO(json.dumps(data))
        stdout = StringIO()
        stderr = StringIO()
        hook_docker_cmd.main(
            ['/path/to/hook-docker-cmd'], stdin, stdout, stderr)
        mock_apply.assert_not_called()

        resp = json.loads(stdout.getvalue())

        self.assertEqual({
            'deploy_status_code': 0,
            'deploy_stderr': '',
            'deploy_stdout': ''
        }, resp)

    @mock.patch('paunch.apply', autospec=True)
    def test_action_delete(self, mock_apply):
        data = {
            "name": "abcdef001",
            "group": "docker-cmd",
            "id": "abc123",
            "inputs": [{
                "name": "deploy_action",
                "value": "DELETE"
            }, {
                "name": "deploy_stack_id",
                "value": "the_stack",
            }, {
                "name": "deploy_resource_name",
                "value": "the_deployment",
            }],
            "config": {
                "db": {
                    "name": "x",
                    "image": "xxx",
                    "privileged": False,
                    "environment": ["foo=bar"],
                    "env_file": "env.file",
                    "start_order": 0
                }
            }
        }
        stdin = StringIO(json.dumps(data))
        stdout = StringIO()
        stderr = StringIO()
        hook_docker_cmd.main(
            ['/path/to/hook-docker-cmd'], stdin, stdout, stderr)
        mock_apply.assert_not_called()

        resp = json.loads(stdout.getvalue())

        self.assertEqual({
            'deploy_status_code': 0,
            'deploy_stderr': '',
            'deploy_stdout': ''
        }, resp)
