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
import json
import os
import tempfile

import fixtures

from tests import common


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

    data_exit_code = {
        "name": "abcdef001",
        "group": "docker-cmd",
        "id": "abc123",
        "config": {
            "web-ls": {
                "action": "exec",
                "command": ["web", "/bin/ls", "-l"],
                "exit_codes": [0, 1]
            }
        }
    }

    def setUp(self):
        super(HookDockerCmdTest, self).setUp()
        self.hook_path = self.relative_path(
            __file__,
            '..',
            'heat-config-docker-cmd/install.d/hook-docker-cmd.py')

        self.cleanup_path = self.relative_path(
            __file__,
            '..',
            'heat-config-docker-cmd/',
            'os-refresh-config/configure.d/50-heat-config-docker-cmd')

        self.fake_tool_path = self.relative_path(
            __file__,
            'config-tool-fake.py')

        self.working_dir = self.useFixture(fixtures.TempDir())
        self.outputs_dir = self.useFixture(fixtures.TempDir())
        self.test_state_path = self.outputs_dir.join('test_state.json')

        self.env = os.environ.copy()
        self.env.update({
            'HEAT_DOCKER_CMD': self.fake_tool_path,
            'TEST_STATE_PATH': self.test_state_path,
        })

    def assert_args_and_labels(self, expected_args, expected_labels, observed):
        '''Assert the labels arguments separately to other arguments.

        Tests that each expected_labels label exists, and remaining
        expected arguments match exactly.

        This allows paunch to add new label arguments without breaking these
        tests.
        '''

        args = []
        labels = []
        j = 0
        while j < len(observed):
            if observed[j] == '--label':
                j += 1
                labels.append(observed[j])
            else:
                args.append(observed[j])
            j += 1

        self.assertEqual(expected_args, args)
        for label in expected_labels:
            self.assertIn(label, labels)

    def test_hook(self):

        self.env.update({
            'TEST_RESPONSE': json.dumps([
                # ps for delete missing
                {},
                # ps for renames
                {},
                # ps for currently running containers
                {},
                # inspect for db unique container name
                {},
                # docker run db
                {'stderr': 'Creating db...'},
                # inspect for web unique container name
                {},
                # docker run web
                {'stderr': 'Creating web...'},
                # name lookup for exec web
                {'stdout': 'web'},
                # docker exec web
                {'stderr': 'one.txt\ntwo.txt\nthree.txt'},
            ])
        })
        returncode, stdout, stderr = self.run_cmd(
            [self.hook_path], self.env, json.dumps(self.data))

        self.assertEqual(0, returncode, stderr)

        self.assertEqual({
            'deploy_stdout': '',
            'deploy_stderr': 'Creating db...\n'
                             'Creating web...\n'
                             'one.txt\ntwo.txt\nthree.txt',
            'deploy_status_code': 0
        }, json.loads(stdout))

        state = list(self.json_from_files(self.test_state_path, 9))
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--filter',
            'label=config_id=abc123',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[0]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[1]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--filter',
            'label=config_id=abc123',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[2]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'inspect',
            '--format',
            'exists',
            'db'
        ], state[3]['args'])
        self.assert_args_and_labels([
            self.fake_tool_path,
            'run',
            '--name',
            'db',
            '--detach=true',
            '--env-file=env.file',
            '--env=foo=bar',
            '--privileged=false',
            'xxx'
            ''
        ], [
            'deploy_stack_id=the_stack',
            'deploy_resource_name=the_deployment',
            'config_id=abc123',
            'container_name=db',
            'managed_by=docker-cmd',
        ], state[4]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'inspect',
            '--format',
            'exists',
            'web',
        ], state[5]['args'])
        self.assert_args_and_labels([
            self.fake_tool_path,
            'run',
            '--name',
            'web',
            '--detach=true',
            '--env-file=foo.env',
            '--env-file=bar.conf',
            '--env=KOLLA_CONFIG_STRATEGY=COPY_ALWAYS',
            '--env=FOO=BAR',
            '--net=host',
            '--privileged=true',
            '--restart=always',
            '--user=root',
            '--volume=/run:/run',
            '--volume=db:/var/lib/db',
            'yyy',
            '/bin/webserver',
            'start'
        ], [
            'deploy_stack_id=the_stack',
            'deploy_resource_name=the_deployment',
            'config_id=abc123',
            'container_name=web',
            'managed_by=docker-cmd',
        ], state[6]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=container_name=web',
            '--filter',
            'label=config_id=abc123',
            '--format',
            '{{.Names}}',
        ], state[7]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'exec',
            'web',
            '/bin/ls',
            '-l'
        ], state[8]['args'])

    def test_hook_exit_codes(self):

        self.env.update({
            'TEST_RESPONSE': json.dumps([
                # ps for delete missing
                {},
                # ps for renames
                {},
                # ps for currently running containers
                {},
                {'stdout': 'web'},
                {
                    'stdout': '',
                    'stderr': 'Warning: custom exit code',
                    'returncode': 1
                }
            ])
        })
        returncode, stdout, stderr = self.run_cmd(
            [self.hook_path], self.env, json.dumps(self.data_exit_code))

        self.assertEqual({
            'deploy_stdout': '',
            'deploy_stderr': 'Warning: custom exit code',
            'deploy_status_code': 0
        }, json.loads(stdout))

        state = list(self.json_from_files(self.test_state_path, 5))
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--filter',
            'label=config_id=abc123',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[0]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[1]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--filter',
            'label=config_id=abc123',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[2]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=container_name=web',
            '--filter',
            'label=config_id=abc123',
            '--format',
            '{{.Names}}',
        ], state[3]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'exec',
            'web',
            '/bin/ls',
            '-l'
        ], state[4]['args'])

    def test_hook_failed(self):

        self.env.update({
            'TEST_RESPONSE': json.dumps([
                # ps for delete missing
                {},
                # ps for renames
                {},
                # ps for currently running containers
                {},
                # inspect for db unique container name
                {},
                # docker run db
                {'stderr': 'Creating db...'},
                # inspect for web unique container name
                {},
                # docker run web
                {'stderr': 'Creating web...'},
                # name lookup for exec web
                {'stdout': 'web'},
                # docker exec web fails
                {
                    'stdout': '',
                    'stderr': 'No such file or directory',
                    'returncode': 2
                }
            ])
        })
        returncode, stdout, stderr = self.run_cmd(
            [self.hook_path], self.env, json.dumps(self.data))

        self.assertEqual({
            'deploy_stdout': '',
            'deploy_stderr': 'Creating db...\n'
                             'Creating web...\n'
                             'No such file or directory',
            'deploy_status_code': 2
        }, json.loads(stdout))

        state = list(self.json_from_files(self.test_state_path, 9))
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--filter',
            'label=config_id=abc123',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[0]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[1]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--filter',
            'label=config_id=abc123',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[2]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'inspect',
            '--format',
            'exists',
            'db'
        ], state[3]['args'])
        self.assert_args_and_labels([
            self.fake_tool_path,
            'run',
            '--name',
            'db',
            '--detach=true',
            '--env-file=env.file',
            '--env=foo=bar',
            '--privileged=false',
            'xxx'
            ''
        ], [
            'deploy_stack_id=the_stack',
            'deploy_resource_name=the_deployment',
            'config_id=abc123',
            'container_name=db',
            'managed_by=docker-cmd',
        ], state[4]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'inspect',
            '--format',
            'exists',
            'web',
        ], state[5]['args'])
        self.assert_args_and_labels([
            self.fake_tool_path,
            'run',
            '--name',
            'web',
            '--detach=true',
            '--env-file=foo.env',
            '--env-file=bar.conf',
            '--env=KOLLA_CONFIG_STRATEGY=COPY_ALWAYS',
            '--env=FOO=BAR',
            '--net=host',
            '--privileged=true',
            '--restart=always',
            '--user=root',
            '--volume=/run:/run',
            '--volume=db:/var/lib/db',
            'yyy',
            '/bin/webserver',
            'start'
        ], [
            'deploy_stack_id=the_stack',
            'deploy_resource_name=the_deployment',
            'config_id=abc123',
            'container_name=web',
            'managed_by=docker-cmd',
        ], state[6]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=container_name=web',
            '--filter',
            'label=config_id=abc123',
            '--format',
            '{{.Names}}',
        ], state[7]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'exec',
            'web',
            '/bin/ls',
            '-l'
        ], state[8]['args'])

    def test_hook_unique_names(self):
        self.env.update({
            'TEST_RESPONSE': json.dumps([
                # ps for delete missing in this config id
                {},
                # ps for renames
                {'stdout': 'web web\ndb db\n'},
                # ps for currently running containers in this config id
                {},
                # inspect for db unique container name
                {'stdout': 'exists'},
                {
                    'stderr': 'Error: No such container: db-blah',
                    'returncode': 1
                },
                # docker run db
                {'stderr': 'Creating db...'},
                # # inspect for web unique container name
                {'stdout': 'exists'},
                {
                    'stderr': 'Error: No such container: web-blah',
                    'returncode': 1
                },
                # # docker run web
                {'stderr': 'Creating web...'},
                # name lookup for exec web
                {'stdout': 'web-asdf1234'},
                # docker exec web-asdf1234
                {'stderr': 'one.txt\ntwo.txt\nthree.txt'},
            ])
        })

        returncode, stdout, stderr = self.run_cmd(
            [self.hook_path], self.env, json.dumps(self.data))

        self.assertEqual(0, returncode, stderr)

        self.assertEqual({
            'deploy_stdout': '',
            'deploy_stderr': 'Creating db...\n'
                             'Creating web...\n'
                             'one.txt\ntwo.txt\nthree.txt',
            'deploy_status_code': 0
        }, json.loads(stdout))

        state = list(self.json_from_files(self.test_state_path, 11))
        db_container_name = state[4]['args'][4]
        web_container_name = state[7]['args'][4]
        self.assertRegex(db_container_name, 'db-[0-9a-z]{8}')
        self.assertRegex(web_container_name, 'web-[0-9a-z]{8}')
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--filter',
            'label=config_id=abc123',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[0]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[1]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--filter',
            'label=config_id=abc123',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[2]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'inspect',
            '--format',
            'exists',
            'db'
        ], state[3]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'inspect',
            '--format',
            'exists',
            db_container_name,
        ], state[4]['args'])
        self.assert_args_and_labels([
            self.fake_tool_path,
            'run',
            '--name',
            db_container_name,
            '--detach=true',
            '--env-file=env.file',
            '--env=foo=bar',
            '--privileged=false',
            'xxx'
        ], [
            'deploy_stack_id=the_stack',
            'deploy_resource_name=the_deployment',
            'config_id=abc123',
            'container_name=db',
            'managed_by=docker-cmd',
        ], state[5]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'inspect',
            '--format',
            'exists',
            'web',
        ], state[6]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'inspect',
            '--format',
            'exists',
            web_container_name,
        ], state[7]['args'])
        self.assert_args_and_labels([
            self.fake_tool_path,
            'run',
            '--name',
            web_container_name,
            '--detach=true',
            '--env-file=foo.env',
            '--env-file=bar.conf',
            '--env=KOLLA_CONFIG_STRATEGY=COPY_ALWAYS',
            '--env=FOO=BAR',
            '--net=host',
            '--privileged=true',
            '--restart=always',
            '--user=root',
            '--volume=/run:/run',
            '--volume=db:/var/lib/db',
            'yyy',
            '/bin/webserver',
            'start'
        ], [
            'deploy_stack_id=the_stack',
            'deploy_resource_name=the_deployment',
            'config_id=abc123',
            'container_name=web',
            'managed_by=docker-cmd',
        ], state[8]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=container_name=web',
            '--filter',
            'label=config_id=abc123',
            '--format',
            '{{.Names}}',
        ], state[9]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'exec',
            'web-asdf1234',
            '/bin/ls',
            '-l'
        ], state[10]['args'])

    def test_cleanup_deleted(self):
        self.env.update({
            'TEST_RESPONSE': json.dumps([{
                # first run, no running containers
                'stdout': '\n'
            }, {
                # list name and container_name label for all containers
                'stdout': '\n'
            }])
        })
        conf_dir = self.useFixture(fixtures.TempDir()).join()
        with tempfile.NamedTemporaryFile(dir=conf_dir, delete=False) as f:
            f.write(json.dumps([self.data]))
            f.flush()
            self.env['HEAT_SHELL_CONFIG'] = f.name

            returncode, stdout, stderr = self.run_cmd(
                [self.cleanup_path], self.env)

        # on the first run, no docker rm calls made
        state = list(self.json_from_files(self.test_state_path, 2))
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Label "config_id"}}'
        ], state[0]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[1]['args'])

        self.env.update({
            'TEST_RESPONSE': json.dumps([{
                # list config_id labels, 3 containers same config
                'stdout': 'abc123\nabc123\nabc123\n'
            }, {
                # list containers with config_id
                'stdout': '111\n222\n333\n'
            }, {
                'stdout': '111 deleted'
            }, {
                'stdout': '222 deleted'
            }, {
                'stdout': '333 deleted'
            }, {
                # list name and container_name label for all containers
                'stdout': '\n'
            }])
        })

        # run again with empty config data
        with tempfile.NamedTemporaryFile(dir=conf_dir, delete=False) as f:
            f.write(json.dumps([]))
            f.flush()
            self.env['HEAT_SHELL_CONFIG'] = f.name

            returncode, stdout, stderr = self.run_cmd(
                [self.cleanup_path], self.env)

        # on the second run, abc123 is deleted,
        # docker rm is run on all containers
        state = list(self.json_from_files(self.test_state_path, 6))
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Label "config_id"}}'
        ], state[0]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-q',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--filter',
            'label=config_id=abc123'
        ], state[1]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'rm',
            '-f',
            '111',
        ], state[2]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'rm',
            '-f',
            '222',
        ], state[3]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'rm',
            '-f',
            '333',
        ], state[4]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[5]['args'])

    def test_cleanup_changed(self):
        self.env.update({
            'TEST_RESPONSE': json.dumps([{
                # list config_id labels, 3 containers same config
                'stdout': 'abc123\nabc123\nabc123\n'
            }, {
                # list name and container_name label for all containers
                'stdout': '111 111\n'
                          '222 222\n'
                          '333\n'
            }])
        })
        conf_dir = self.useFixture(fixtures.TempDir()).join()
        with tempfile.NamedTemporaryFile(dir=conf_dir, delete=False) as f:
            f.write(json.dumps([self.data]))
            f.flush()
            self.env['HEAT_SHELL_CONFIG'] = f.name

            returncode, stdout, stderr = self.run_cmd(
                [self.cleanup_path], self.env)

        # on the first run, no docker rm calls made
        state = list(self.json_from_files(self.test_state_path, 2))
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Label "config_id"}}'
        ], state[0]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[1]['args'])

        # run again with changed config data
        self.env.update({
            'TEST_RESPONSE': json.dumps([{
                # list config_id labels, 3 containers same config
                'stdout': 'abc123\nabc123\nabc123\n'
            }, {
                # list containers with config_id
                'stdout': '111\n222\n333\n'
            }, {
                'stdout': '111 deleted'
            }, {
                'stdout': '222 deleted'
            }, {
                'stdout': '333 deleted'
            }, {
                # list name and container_name label for all containers
                'stdout': 'abc123 abc123\n'
            }])
        })
        new_data = copy.deepcopy(self.data)
        new_data['config']['web']['image'] = 'yyy'
        new_data['id'] = 'def456'
        with tempfile.NamedTemporaryFile(dir=conf_dir, delete=False) as f:
            f.write(json.dumps([new_data]))
            f.flush()
            self.env['HEAT_SHELL_CONFIG'] = f.name

            returncode, stdout, stderr = self.run_cmd(
                [self.cleanup_path], self.env)

        # on the second run, abc123 is deleted,
        # docker rm is run on all containers
        state = list(self.json_from_files(self.test_state_path, 6))
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Label "config_id"}}'
        ], state[0]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-q',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--filter',
            'label=config_id=abc123'
        ], state[1]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'rm',
            '-f',
            '111',
        ], state[2]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'rm',
            '-f',
            '222',
        ], state[3]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'rm',
            '-f',
            '333',
        ], state[4]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[5]['args'])

    def test_cleanup_rename(self):
        self.env.update({
            'TEST_RESPONSE': json.dumps([{
                # list config_id labels, 3 containers same config
                'stdout': 'abc123\nabc123\nabc123\n'
            }, {
                # list name and container_name label for all containers
                'stdout': '111 111-s84nf83h\n'
                          '222 222\n'
                          '333 333-3nd83nfi\n'
            }])
        })
        conf_dir = self.useFixture(fixtures.TempDir()).join()
        with tempfile.NamedTemporaryFile(dir=conf_dir, delete=False) as f:
            f.write(json.dumps([self.data]))
            f.flush()
            self.env['HEAT_SHELL_CONFIG'] = f.name

            returncode, stdout, stderr = self.run_cmd(
                [self.cleanup_path], self.env)

        # on the first run, no docker rm calls made
        state = list(self.json_from_files(self.test_state_path, 4))
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Label "config_id"}}'
        ], state[0]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'ps',
            '-a',
            '--filter',
            'label=managed_by=docker-cmd',
            '--format',
            '{{.Names}} {{.Label "container_name"}}'
        ], state[1]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'rename',
            '111',
            '111-s84nf83h'
        ], state[2]['args'])
        self.assertEqual([
            self.fake_tool_path,
            'rename',
            '333',
            '333-3nd83nfi'
        ], state[3]['args'])
