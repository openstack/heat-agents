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


def docker_run_args(cmd, container, config):
    cconfig = config[container]
    if cconfig.get('detach', True):
        cmd.append('--detach=true')
    if 'env_file' in cconfig:
        if isinstance(cconfig['env_file'], list):
            for f in cconfig.get('env_file', []):
                if f:
                    cmd.append('--env-file=%s' % f)
        else:
            cmd.append('--env-file=%s' % cconfig['env_file'])
    for v in cconfig.get('environment', []):
        if v:
            cmd.append('--env=%s' % v)
    if 'net' in cconfig:
        cmd.append('--net=%s' % cconfig['net'])
    if 'pid' in cconfig:
        cmd.append('--pid=%s' % cconfig['pid'])
    if 'privileged' in cconfig:
        cmd.append('--privileged=%s' % str(cconfig['privileged']).lower())
    if 'restart' in cconfig:
        cmd.append('--restart=%s' % cconfig['restart'])
    if 'user' in cconfig:
        cmd.append('--user=%s' % cconfig['user'])
    for v in cconfig.get('volumes', []):
        if v:
            cmd.append('--volume=%s' % v)
    for v in cconfig.get('volumes_from', []):
        if v:
            cmd.append('--volumes_from=%s' % v)

    cmd.append(cconfig.get('image', ''))
    cmd.extend(command_argument(cmd, cconfig.get('command')))


def docker_exec_args(cmd, container, config, cid):
    cconfig = config[container]
    if 'privileged' in cconfig:
        cmd.append('--privileged=%s' % str(cconfig['privileged']).lower())
    if 'user' in cconfig:
        cmd.append('--user=%s' % cconfig['user'])
    command = command_argument(cmd, cconfig.get('command'))
    # for exec, the first argument is the container name,
    # make sure the correct one is used
    command[0] = discover_container_name(command[0], cid)
    cmd.extend(command)


def command_argument(cmd, command):
    if not command:
        return []
    if not isinstance(command, list):
        return command.split()
    return command


def execute(cmd):
    log.debug("execute command: %s" % cmd)
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


def main(argv=sys.argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    cmd_stderrs = []
    cmd_stdouts = []
    global log
    log = logging.getLogger('heat-config')
    handler = logging.StreamHandler(stderr)
    handler.setFormatter(
        logging.Formatter(
            '[%(asctime)s] (%(name)s) [%(levelname)s] %(message)s'))
    log.addHandler(handler)
    log.setLevel('DEBUG')

    c = json.load(stdin)

    input_values = dict((i['name'], i['value']) for i in c.get('inputs', {}))

    if input_values.get('deploy_action') == 'DELETE':
        json.dump(build_response(
            '', '', 0), stdout)
        return

    config = c.get('config', '')
    cid = c.get('id')
    if not config:
        log.debug("No 'config' input found, nothing to do.")
        json.dump(build_response(
            '', '', 0), stdout)
        return

    deploy_status_code = 0

    # convert config to dict
    if not isinstance(config, dict):
        config = yaml.safe_load(config)

    def key_fltr(key):
        return config[key].get('start_order', 0)
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
            label_arguments(cmd, container, cid, input_values)
            docker_run_args(cmd, container, config)
        elif action == 'exec':
            cmd = [DOCKER_CMD, 'exec']
            docker_exec_args(cmd, container, config, cid)

        (cmd_stdout, cmd_stderr, returncode) = execute(cmd)
        if cmd_stdout:
            out_str = cmd_stdout.decode('utf-8')
            stdout.write(out_str)
            cmd_stdouts.append(out_str)
        if cmd_stderr:
            err_str = cmd_stderr.decode('utf-8')
            stderr.write(err_str)
            cmd_stderrs.append(err_str)

        if returncode not in exit_codes:
            log.error("Error running %s. [%s]\n" % (cmd, returncode))
            deploy_status_code = returncode
        else:
            log.debug('Completed %s' % cmd)
    json.dump(build_response('\n'.join(cmd_stdouts), '\n'.join(cmd_stderrs),
              deploy_status_code), sys.stdout)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
