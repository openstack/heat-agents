Heat Agents
===========

Heat Agents are python hooks for deploying software configurations using
`Heat`_.


This repository contains `diskimage-builder`_ elements to build an image with
the software configuration hooks required to use your preferred configuration
method.

These elements depend on some elements found in the `tripleo-image-elements`_
repository. These elements will build an image which uses `os-collect-config`_,
`os-refresh-config`_, and `os-apply-config`_ together to invoke a hook with the
supplied configuration data, and return any outputs back to Heat.

.. _Heat: https://docs.openstack.org/heat/latest
.. _diskimage-builder: https://docs.openstack.org/diskimage-builder/latest/
.. _tripleo-image-elements: https://git.openstackorg/cgit/openstack/tripleo-image-elements
.. _os-collect-config: https://git.openstackorg/cgit/openstack/os-collect-config
.. _os-refresh-config: https://git.openstackorg/cgit/openstack/os-refresh-config
.. _os-apply-config: https://git.openstackorg/cgit/openstack/os-apply-config

.. toctree::
   :maxdepth: 3

   install/index
