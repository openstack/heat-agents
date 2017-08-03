.. heat-agents documentation master file, created by
   sphinx-quickstart on Thu Jul 20 08:52:00 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Heat Agents!
=======================

Overview
========

Heat Agents are python hooks for deploying software configurations using heat.


This repository contains `diskimage-builder <https://github.com/openstack/diskimage-builder>`_
elements to build an image with the software configuration hooks
required to use your preferred configuration method.

These elements depend on some elements found in the
`tripleo-image-elements <https://github.com/openstack/tripleo-image-elements>`_
repository. These elements will build an image which uses
`os-collect-config <https://github.com/openstack/os-collect-config>`_,
`os-refresh-config <https://github.com/openstack/os-refresh-config>`_, and
`os-apply-config <https://github.com/openstack/os-apply-config>`_ together to
invoke a hook with the supplied configuration data, and return any outputs back
to heat.


Index
=====
.. toctree::
   :maxdepth: 1

   install/index
   contributor/index


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
