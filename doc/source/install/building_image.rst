=============================================
Build image with software configuration hooks
=============================================

When building an image only the elements for the preferred configuration methods are required.
The heat-config element is automatically included as a dependency.

An example fedora based image containing some hooks can be built and uploaded to glance
with the following:

::

  sudo pip install git+https://git.openstack.org/openstack/diskimage-builder.git
  git clone https://git.openstack.org/openstack/tripleo-image-elements.git
  git clone https://git.openstack.org/openstack/heat-agents.git
  export ELEMENTS_PATH=tripleo-image-elements/elements:heat-agents/
  disk-image-create vm \
    fedora selinux-permissive \
    os-collect-config \
    os-refresh-config \
    os-apply-config \
    heat-config \
    heat-config-ansible \
    heat-config-cfn-init \
    heat-config-docker-compose \
    heat-config-kubelet \
    heat-config-puppet \
    heat-config-salt \
    heat-config-script \
    -o fedora-software-config.qcow2
  openstack image create --disk-format qcow2 --container-format bare fedora-software-config < \
    fedora-software-config.qcow2
