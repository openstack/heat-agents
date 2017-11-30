=====
hiera
=====

A hook which helps write `hiera`_ files to disk and creates the ``hiera.yaml``
to order them. This is typically used alongside the puppet hook to generate
Hiera in a more composable manner.

Example::

    ComputeConfig:
      type: OS::Heat::StructuredConfig
      properties:
        group: hiera
        config:
          hierarchy:
            - compute
          datafiles:
            compute:
              debug: true
              db_connection: foo:/bar
              # customized hiera goes here...

This would write out:

- An ``/etc/hiera.yaml`` config file with compute in the hierarchy.
- An ``/etc/puppet/hieradata/compute.json`` file loaded with the
  custom hiera data.

.. _hiera: https://docs.puppet.com/hiera/
