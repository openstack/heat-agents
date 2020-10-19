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

import copy
import importlib
import io
import json
import logging
import sys

from multiprocessing import Lock
from unittest import mock

from tests import common

log = logging.getLogger('test_hook_chef')


def load_module(name, path):
    module_spec = importlib.util.spec_from_file_location(
        name, path
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


@mock.patch("os.chdir")
@mock.patch("os.makedirs")
@mock.patch('subprocess.Popen')
class HookChefTest(common.RunScriptTest):

    data = {
        'id': 'fake_stack',
        'name': 'fake_resource_name',
        'group': 'chef',
        'inputs': [
            {'name': 'fooval', 'value': {'bar': 'baz'}},
            {'name': 'barval', 'value': {'foo': 'biff'}},
            {'name': "deploy_server_id", 'value': 'foo'},
            {'name': "deploy_action", 'value': 'foo'},
            {'name': "deploy_stack_id", 'value': 'foo'},
            {'name': "deploy_resource_name", 'value': 'foo'},
            {'name': "deploy_signal_transport", 'value': 'foo'},
            {'name': "deploy_signal_id", 'value': 'foo'},
            {'name': "deploy_signal_verb", 'value': 'foo'}
        ],
        'options': {},
        'outputs': [
            {'name': 'first_output'},
            {'name': 'second_output'}
        ],
        'config': None
    }

    def setUp(self):
        super(HookChefTest, self).setUp()
        self.hook_path = self.relative_path(
            __file__,
            '..',
            'heat-config-chef/install.d/hook-chef.py')
        sys.stdin = io.StringIO()
        sys.stdout = io.StringIO()

    def tearDown(self):
        super(HookChefTest, self).tearDown()
        sys.stdin = sys.__stdin__
        sys.stdout = sys.__stdout__

    def get_module(self):
        lock = Lock()
        try:
            lock.acquire()
            return load_module("hook_chef", self.hook_path)
        finally:
            lock.release()

    def test_hook(self, mock_popen, mock_mkdirs, mock_chdir):
        data = copy.deepcopy(self.data)
        data['config'] = '["recipe[apache]"]'
        hook_chef = self.get_module()
        json.dump(data, sys.stdin)
        sys.stdin.seek(0)
        mock_subproc = mock.Mock()
        mock_popen.return_value = mock_subproc
        mock_subproc.communicate.return_value = (b"out", b"err")
        mock_subproc.returncode = 0
        with mock.patch("os.fdopen", mock.mock_open()) as mfdopen:
            with mock.patch("os.open", mock.mock_open()):
                hook_chef.main(json.dumps(data))
                exp_node = {
                    'barval': {'foo': 'biff'},
                    'fooval': {u'bar': u'baz'},
                    'run_list': [u'recipe[apache]']
                }
                exp_cfg = ("log_level :debug\n"
                           "log_location STDOUT\n"
                           "local_mode true\n"
                           "chef_zero.enabled true\n"
                           "cookbook_path '/var/lib/heat-config/"
                           "heat-config-chef/kitchen/cookbooks'\n"
                           "role_path '/var/lib/heat-config/"
                           "heat-config-chef/kitchen/roles'\n"
                           "environment_path '/var/lib/heat-config/"
                           "heat-config-chef/kitchen/environments'\n"
                           "node_path '/var/lib/heat-config/"
                           "heat-config-chef/node'")
                mfdopen.return_value.write.assert_any_call(exp_cfg)
                args = mfdopen.return_value.write.mock_calls[0][1][0]
                self.assertEqual(exp_node, json.loads(args))
        calls = [
            mock.call(['hostname', '-f'], env=mock.ANY, stderr=mock.ANY,
                      stdout=mock.ANY),
            mock.call([
                'chef-client', '-z', '--config',
                '/var/lib/heat-config/heat-config-chef/client.rb', '-j',
                '/var/lib/heat-config/heat-config-chef/node/out.json'],
                env=mock.ANY, stderr=mock.ANY, stdout=mock.ANY)
        ]
        mock_popen.assert_has_calls(calls, any_order=True)
        self.assertEqual({"deploy_status_code": 0,
                          "deploy_stdout": "out",
                          "deploy_stderr": "err"},
                         json.loads(sys.stdout.getvalue()))

    def test_hook_with_kitchen(self, mock_popen, mock_mkdirs, mock_chdir):
        data = copy.deepcopy(self.data)
        data['config'] = '["recipe[apache]"]'
        data['options'] = {
            "kitchen": "https://github.com/fake.git",
            "kitchen_path": "/opt/heat/chef/kitchen"
        }
        sys.stdin.write(json.dumps(data))
        hook_chef = self.get_module()
        sys.stdin.seek(0)
        mock_subproc = mock.Mock()
        mock_popen.return_value = mock_subproc
        mock_subproc.communicate.return_value = (b"out", b"err")
        mock_subproc.returncode = 0
        with mock.patch("os.fdopen", mock.mock_open()) as mfdopen:
            with mock.patch("os.open", mock.mock_open()):
                hook_chef.main(json.dumps(data))
                exp_cfg = ("log_level :debug\n"
                           "log_location STDOUT\n"
                           "local_mode true\n"
                           "chef_zero.enabled true\n"
                           "cookbook_path '/opt/heat/chef/kitchen/"
                           "cookbooks'\n"
                           "role_path '/opt/heat/chef/kitchen/roles'\n"
                           "environment_path '/opt/heat/chef/kitchen/"
                           "environments'\n"
                           "node_path '/var/lib/heat-config/heat-config-chef"
                           "/node'")
                mfdopen.return_value.write.assert_any_call(exp_cfg)
        calls = [
            mock.call(['git', 'clone', "https://github.com/fake.git",
                       "/opt/heat/chef/kitchen"], env=mock.ANY,
                      stderr=mock.ANY, stdout=mock.ANY),
            mock.call(['hostname', '-f'], env=mock.ANY, stderr=mock.ANY,
                      stdout=mock.ANY),
            mock.call([
                'chef-client', '-z', '--config',
                '/var/lib/heat-config/heat-config-chef/client.rb', '-j',
                '/var/lib/heat-config/heat-config-chef/node/out.json'],
                env=mock.ANY, stderr=mock.ANY, stdout=mock.ANY)
        ]
        mock_popen.assert_has_calls(calls, any_order=True)
        self.assertEqual({"deploy_status_code": 0,
                          "deploy_stdout": "out",
                          "deploy_stderr": "err"},
                         json.loads(sys.stdout.getvalue()))

    def test_hook_environment(self, mock_popen, mock_mkdirs, mock_chdir):
        data = copy.deepcopy(self.data)
        data['config'] = '["recipe[apache]"]'
        data['inputs'].append({'name': 'environment',
                               'value': 'production'})
        hook_chef = self.get_module()
        sys.stdin.write(json.dumps(data))
        sys.stdin.seek(0)
        mock_subproc = mock.Mock()
        mock_popen.return_value = mock_subproc
        mock_subproc.communicate.return_value = (b"out", b"err")
        mock_subproc.returncode = 0
        with mock.patch("os.fdopen", mock.mock_open()) as mfdopen:
            with mock.patch("os.open", mock.mock_open()):
                hook_chef.main(json.dumps(data))
                exp_node = {
                    'barval': {'foo': 'biff'},
                    'fooval': {u'bar': u'baz'},
                    'run_list': [u'recipe[apache]']
                }
                exp_cfg = ("log_level :debug\n"
                           "log_location STDOUT\n"
                           "local_mode true\n"
                           "chef_zero.enabled true\n"
                           "cookbook_path '/var/lib/heat-config/"
                           "heat-config-chef/kitchen/cookbooks'\n"
                           "role_path '/var/lib/heat-config/"
                           "heat-config-chef/kitchen/roles'\n"
                           "environment_path '/var/lib/heat-config/"
                           "heat-config-chef/kitchen/environments'\n"
                           "environment 'production'\n"
                           "node_path '/var/lib/heat-config/"
                           "heat-config-chef/node'")
                mfdopen.return_value.write.assert_any_call(exp_cfg)
                args = mfdopen.return_value.write.mock_calls[0][1][0]
                self.assertEqual(exp_node, json.loads(args))
