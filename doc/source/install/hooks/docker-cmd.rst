==========
docker-cmd
==========

A hook which uses the ``docker`` command via `paunch`_ to deploy containers.

The hook currently supports specifying containers in the `docker-compose v1
format`_. The intention is for this hook to also support the kubernetes pod
format.

A dedicated os-refresh-config script will remove running containers if a
deployment is removed or changed, then the docker-cmd hook will run any
containers in new or updated deployments.

.. _paunch: https://docs.openstack.org/paunch/latest/
.. _docker-compose v1 format: https://docs.docker.com/compose/compose-file/#/version-1
