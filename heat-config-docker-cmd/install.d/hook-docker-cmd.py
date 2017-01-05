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

import collections
import json
import logging
import os
import sys

import paunch
import yaml

DOCKER_CMD = os.environ.get('HEAT_DOCKER_CMD', 'docker')


log = None


def build_response(deploy_stdout, deploy_stderr, deploy_status_code):
    return {
        'deploy_stdout': deploy_stdout,
        'deploy_stderr': deploy_stderr,
        'deploy_status_code': deploy_status_code,
    }


def main(argv=sys.argv):
    global log
    log = logging.getLogger('heat-config')
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            '[%(asctime)s] (%(name)s) [%(levelname)s] %(message)s'))
    log.addHandler(handler)
    log.setLevel('DEBUG')

    c = json.load(sys.stdin)

    input_values = dict((i['name'], i['value']) for i in c.get('inputs', {}))

    if input_values.get('deploy_action') == 'DELETE':
        json.dump(build_response(
            '', '', 0), sys.stdout)
        return

    config = c.get('config', '')
    cid = c.get('id')
    if not config:
        log.debug("No 'config' input found, nothing to do.")
        json.dump(build_response(
            '', '', 0), sys.stdout)
        return

    stdout = []
    stderr = []
    deploy_status_code = 0

    # convert config to dict
    if not isinstance(config, dict):
        config = yaml.safe_load(config)

    labels = collections.OrderedDict()
    labels['deploy_stack_id'] = input_values.get('deploy_stack_id')
    labels['deploy_resource_name'] = input_values.get('deploy_resource_name')
    stdout, stderr, deploy_status_code = paunch.apply(
        cid,
        config,
        managed_by='docker-cmd',
        labels=labels,
        docker_cmd=DOCKER_CMD
    )

    json.dump(build_response(
        '\n'.join(stdout), '\n'.join(stderr), deploy_status_code), sys.stdout)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
