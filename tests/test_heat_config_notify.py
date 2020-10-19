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
import io
import json
import tempfile

import fixtures
from unittest import mock

from tests import common
from tests import heat_config_notify as hcn


class HeatConfigNotifyTest(common.RunScriptTest):

    data_signal_id = {
        'id': '5555',
        'group': 'script',
        'inputs': [{
            'name': 'deploy_signal_id',
            'value': 'mock://192.0.2.3/foo'
        }],
        'config': 'five'
    }

    data_signal_id_put = {
        'id': '5555',
        'group': 'script',
        'inputs': [{
            'name': 'deploy_signal_id',
            'value': 'mock://192.0.2.3/foo'
        }, {
            'name': 'deploy_signal_verb',
            'value': 'PUT'
        }],
        'config': 'five'
    }

    data_heat_signal = {
        'id': '5555',
        'group': 'script',
        'inputs': [{
            'name': 'deploy_auth_url',
            'value': 'mock://192.0.2.3/auth'
        }, {
            'name': 'deploy_user_id',
            'value': 'aaaa'
        }, {
            'name': 'deploy_password',
            'value': 'password'
        }, {
            'name': 'deploy_project_id',
            'value': 'bbbb'
        }, {
            'name': 'deploy_stack_id',
            'value': 'cccc'
        }, {
            'name': 'deploy_resource_name',
            'value': 'the_resource'
        }, {
            'name': 'deploy_region_name',
            'value': 'RegionOne'
        }],
        'config': 'five'
    }

    def setUp(self):
        super(HeatConfigNotifyTest, self).setUp()
        self.deployed_dir = self.useFixture(fixtures.TempDir())
        hcn.init_logging = mock.MagicMock()
        self.stdin = io.StringIO()

    def write_config_file(self, data):
        config_file = tempfile.NamedTemporaryFile(mode='w')
        config_file.write(json.dumps(data))
        config_file.flush()
        return config_file

    def test_notify_missing_file(self):

        signal_data = json.dumps({'foo': 'bar'})
        self.stdin.write(signal_data)
        self.stdin.seek(0)

        with self.write_config_file(self.data_signal_id) as config_file:
            config_file_name = config_file.name

        self.assertEqual(
            1, hcn.main(['heat-config-notify', config_file_name], self.stdin))

    def test_notify_missing_file_arg(self):

        signal_data = json.dumps({'foo': 'bar'})
        self.stdin.write(signal_data)
        self.stdin.seek(0)

        self.assertEqual(
            1, hcn.main(['heat-config-notify'], self.stdin))

    def test_notify_signal_id(self):
        requests = mock.MagicMock()
        session = mock.MagicMock()
        requests.Session.return_value = session
        retry = mock.MagicMock()
        httpadapter = mock.MagicMock()

        hcn.requests = requests
        hcn.Retry = retry
        hcn.HTTPAdapter = httpadapter

        signal_data = json.dumps({'foo': 'bar'})
        self.stdin.write(signal_data)
        self.stdin.seek(0)

        with self.write_config_file(self.data_signal_id) as config_file:
            self.assertEqual(
                0,
                hcn.main(['heat-config-notify', config_file.name], self.stdin))

        session.post.assert_called_once_with(
            'mock://192.0.2.3/foo',
            data=signal_data,
            headers={'content-type': 'application/json'})

    def test_notify_signal_id_put(self):
        requests = mock.MagicMock()
        session = mock.MagicMock()
        requests.Session.return_value = session
        retry = mock.MagicMock()
        httpadapter = mock.MagicMock()

        hcn.requests = requests
        hcn.Retry = retry
        hcn.HTTPAdapter = httpadapter

        session.post.return_value = '[200]'

        signal_data = json.dumps({'foo': 'bar'})
        self.stdin.write(signal_data)
        self.stdin.seek(0)

        with self.write_config_file(self.data_signal_id_put) as config_file:
            self.assertEqual(
                0,
                hcn.main(['heat-config-notify', config_file.name], self.stdin))

        session.put.assert_called_once_with(
            'mock://192.0.2.3/foo',
            data=signal_data,
            headers={'content-type': 'application/json'})

    def test_notify_signal_id_empty_data(self):
        requests = mock.MagicMock()
        session = mock.MagicMock()
        requests.Session.return_value = session
        retry = mock.MagicMock()
        httpadapter = mock.MagicMock()

        hcn.requests = requests
        hcn.Retry = retry
        hcn.HTTPAdapter = httpadapter

        session.post.return_value = '[200]'

        with self.write_config_file(self.data_signal_id) as config_file:
            self.assertEqual(
                0,
                hcn.main(['heat-config-notify', config_file.name], self.stdin))

        session.post.assert_called_once_with(
            'mock://192.0.2.3/foo',
            data='{}',
            headers={'content-type': 'application/json'})

    def test_notify_signal_id_invalid_json_data(self):
        requests = mock.MagicMock()
        session = mock.MagicMock()
        requests.Session.return_value = session
        retry = mock.MagicMock()
        httpadapter = mock.MagicMock()

        hcn.requests = requests
        hcn.Retry = retry
        hcn.HTTPAdapter = httpadapter

        session.post.return_value = '[200]'

        signal_data = json.dumps({'foo': 'bar'})
        self.stdin.write(signal_data)
        self.stdin.write(signal_data[:-3])
        self.stdin.seek(0)

        with self.write_config_file(self.data_signal_id) as config_file:
            self.assertEqual(
                0,
                hcn.main(['heat-config-notify', config_file.name], self.stdin))

        session.post.assert_called_once_with(
            'mock://192.0.2.3/foo',
            data='{}',
            headers={'content-type': 'application/json'})

    def _do_test_notify_heat_signal(self, data_heat_signal, expected_region):
        ksclient = mock.MagicMock()
        hcn.ksclient = ksclient
        ks = mock.MagicMock()
        ksclient.Client.return_value = ks

        heatclient = mock.MagicMock()
        hcn.heatclient = heatclient
        heat = mock.MagicMock()
        heatclient.Client.return_value = heat

        signal_data = json.dumps({'foo': 'bar'})
        self.stdin.write(signal_data)
        self.stdin.seek(0)

        ks.service_catalog.url_for.return_value = 'mock://192.0.2.3/heat'
        heat.resources.signal.return_value = 'all good'

        with self.write_config_file(data_heat_signal) as config_file:
            self.assertEqual(
                0,
                hcn.main(['heat-config-notify', config_file.name], self.stdin))

        ksclient.Client.assert_called_once_with(
            auth_url='mock://192.0.2.3/auth',
            user_id='aaaa',
            password='password',
            project_id='bbbb')
        ks.service_catalog.url_for.assert_called_once_with(
            service_type='orchestration', endpoint_type='publicURL',
            region_name=expected_region)

        heatclient.Client.assert_called_once_with(
            '1', 'mock://192.0.2.3/heat', token=ks.auth_token)
        heat.resources.signal.assert_called_once_with(
            'cccc',
            'the_resource',
            data={'foo': 'bar'})

    def test_notify_heat_signal(self):
        self._do_test_notify_heat_signal(self.data_heat_signal, 'RegionOne')

    def test_notify_heat_signal_no_region(self):
        data_heat_signal = copy.deepcopy(self.data_heat_signal)
        del data_heat_signal['inputs'][-1]  # Remove region_name input
        self._do_test_notify_heat_signal(data_heat_signal, None)

    def test_notify_heat_signal_unknown_region(self):
        data_heat_signal = copy.deepcopy(self.data_heat_signal)
        data_heat_signal['inputs'][-1]['value'] = None
        self._do_test_notify_heat_signal(data_heat_signal, None)
