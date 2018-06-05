==============
docker-compose
==============

A hook which uses ``docker-compose`` to deploy containers.

A special input ``env_files`` can be used with SoftwareConfig and
StructuredConfig for docker-compose env_file key(s). If any env_file
keys specified in ``docker-compose.yml`` do not exist in the ``input_values``
supplied, docker-compose will throw an error, as it can't find these files.

Also, the ``--parameter-file`` option can be used to pass env files from the
client.

Example::

 $ openstack stack create test_stack -t example-docker-compose-template.yaml \
    --parameter-file env_file_0=./common.env \
    --parameter-file env_file_1=./apps/web.env \
    --parameter-file env_file_2=./test.env \
    --parameter-file env_file_3=./busybox.env
