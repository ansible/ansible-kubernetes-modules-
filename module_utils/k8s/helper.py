#
#  Copyright 2018 Red Hat | Ansible
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import copy

try:
    from openshift.dynamic import DynamicClient  # NOQA
    HAS_K8S_MODULE_HELPER = True
except ImportError as exc:
    HAS_K8S_MODULE_HELPER = False


ARG_ATTRIBUTES_BLACKLIST = ('property_path',)

COMMON_ARG_SPEC = {
    'state': {
        'default': 'present',
        'choices': ['present', 'absent'],
    },
    'force': {
        'type': 'bool',
        'default': False,
    },
    'resource_definition': {
        'type': 'dict',
        'aliases': ['definition', 'inline']
    },
    'src': {
        'type': 'path',
    },
    'kind': {},
    'name': {},
    'namespace': {},
    'api_version': {
        'default': 'v1',
        'aliases': ['api', 'version'],
    },
}

AUTH_ARG_SPEC = {
    'kubeconfig': {
        'type': 'path',
    },
    'context': {},
    'host': {},
    'api_key': {
        'no_log': True,
    },
    'username': {},
    'password': {
        'no_log': True,
    },
    'verify_ssl': {
        'type': 'bool',
    },
    'ssl_ca_cert': {
        'type': 'path',
    },
    'cert_file': {
        'type': 'path',
    },
    'key_file': {
        'type': 'path',
    },
}

OPENSHIFT_ARG_SPEC = {
    'description': {},
    'display_name': {},
}


class AnsibleMixin(object):
    _argspec_cache = None

    @property
    def argspec(self):
        """
        Introspect the model properties, and return an Ansible module arg_spec dict.
        :return: dict
        """
        if self._argspec_cache:
            return self._argspec_cache
        argument_spec = copy.deepcopy(COMMON_ARG_SPEC)
        argument_spec.update(copy.deepcopy(AUTH_ARG_SPEC))
        argument_spec.update(copy.deepcopy(OPENSHIFT_ARG_SPEC))
        self._argspec_cache = argument_spec
        return self._argspec_cache
