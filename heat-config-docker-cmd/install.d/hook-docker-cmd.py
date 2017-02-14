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

import json
import logging
import os
import random
import string
import subprocess
import sys
import yaml


DOCKER_CMD = os.environ.get('HEAT_DOCKER_CMD', 'docker')


log = None


def build_response(deploy_stdout, deploy_stderr, deploy_status_code):
    return {
        'deploy_stdout': deploy_stdout,
        'deploy_stderr': deploy_stderr,
        'deploy_status_code': deploy_status_code,
    }


def docker_arg_map(key, value):
    value = str(value).encode('ascii', 'ignore')
    return {
        'environment': "--env=%s" % value,
        'image': value,
        'net': "--net=%s" % value,
        'pid': "--pid=%s" % value,
        'privileged': "--privileged=%s" % value.lower(),
        'restart': "--restart=%s" % value,
        'user': "--user=%s" % value,
        'volumes': "--volume=%s" % value,
        'volumes_from': "--volumes-from=%s" % value,
    }.get(key, None)


def execute(cmd):
    log.debug(' '.join(cmd))
    subproc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    cmd_stdout, cmd_stderr = subproc.communicate()
    log.debug(cmd_stdout)
    log.debug(cmd_stderr)
    return cmd_stdout, cmd_stderr, subproc.returncode


def label_arguments(cmd, container, cid, iv):
    cmd.extend([
        '--label',
        'deploy_stack_id=%s' % iv.get('deploy_stack_id'),
        '--label',
        'deploy_resource_name=%s' % iv.get('deploy_resource_name'),
        '--label',
        'config_id=%s' % cid,
        '--label',
        'container_name=%s' % container,
        '--label',
        'managed_by=docker-cmd'
    ])


def inspect(container, format=None):
    cmd = [DOCKER_CMD, 'inspect']
    if format:
        cmd.append('--format')
        cmd.append(format)
    cmd.append(container)
    (cmd_stdout, cmd_stderr, returncode) = execute(cmd)
    if returncode != 0:
        return
    try:
        if format:
            return cmd_stdout
        else:
            return json.loads(cmd_stdout)[0]
    except Exception as e:
        log.error('Problem parsing docker inspect: %s' % e)


def unique_container_name(container):
    container_name = container
    while inspect(container_name, format='exists'):
        suffix = ''.join(random.choice(
            string.ascii_lowercase + string.digits) for i in range(8))
        container_name = '%s-%s' % (container, suffix)
    return container_name


def discover_container_name(container, cid):
    cmd = [
        DOCKER_CMD,
        'ps',
        '-a',
        '--filter',
        'label=container_name=%s' % container,
        '--filter',
        'label=config_id=%s' % cid,
        '--format',
        '{{.Names}}'
    ]
    (cmd_stdout, cmd_stderr, returncode) = execute(cmd)
    if returncode != 0:
        return container
    names = cmd_stdout.split()
    if names:
        return names[0]
    return container


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

    key_fltr = lambda k: config[k].get('start_order', 0)
    for container in sorted(config, key=key_fltr):
        log.debug("Running container: %s" % container)
        action = config[container].get('action', 'run')
        exit_codes = config[container].get('exit_codes', [0])

        if action == 'run':
            cmd = [
                DOCKER_CMD,
                'run',
                '--name',
                unique_container_name(container)
            ]
            label_arguments(cmd, container, c.get('id'), input_values)
            if config[container].get('detach', True):
                cmd.append('--detach=true')
        elif action == 'exec':
            cmd = [DOCKER_CMD, 'exec']

        image_name = ''
        for key in sorted(config[container]):
            # These ones contain a list of values
            if key in ['environment', 'volumes', 'volumes_from']:
                for value in config[container][key]:
                    # Somehow the lists get empty values sometimes
                    if type(value) is unicode and not value.strip():
                        continue
                    cmd.append(docker_arg_map(key, value))
            elif key == 'image':
                image_name = config[container][key].encode('ascii', 'ignore')
            else:
                arg = docker_arg_map(key, config[container][key])
                if arg:
                    cmd.append(arg)

        # Image name and command come last.
        if action == 'run':
            cmd.append(image_name)

        if 'command' in config[container]:
            command = config[container].get('command')

            if action == 'exec':
                # for exec, the first argument is the container name,
                # make sure the correct one is used
                command[0] = discover_container_name(command[0], c.get('id'))

            cmd.extend(command)

        (cmd_stdout, cmd_stderr, returncode) = execute(cmd)
        if cmd_stdout:
            stdout.append(cmd_stdout)
        if cmd_stderr:
            stderr.append(cmd_stderr)

        if returncode not in exit_codes:
            log.error("Error running %s. [%s]\n" % (cmd, returncode))
            deploy_status_code = returncode
        else:
            log.debug('Completed %s' % cmd)

    json.dump(build_response(
        '\n'.join(stdout), '\n'.join(stderr), deploy_status_code), sys.stdout)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
