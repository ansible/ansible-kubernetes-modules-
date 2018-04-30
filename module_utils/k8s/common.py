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

from __future__ import absolute_import, division, print_function

import os

from dictdiffer import diff

from ansible.module_utils.six import iteritems
from ansible.module_utils.basic import AnsibleModule

from ansible.module_utils.k8s.helper import AUTH_ARG_SPEC
try:
    import kubernetes
    from openshift.dynamic import DynamicClient
    HAS_K8S_MODULE_HELPER = True
except ImportError:
    HAS_K8S_MODULE_HELPER = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def remove_secret_data(obj_dict):
    """ Remove any sensitive data from a K8s dict"""
    #TODO: Discuss this, these are potentially useful things.
    # if obj_dict.get('data'):
    #     # Secret data
    #     obj_dict.pop('data')
    # if obj_dict.get('string_data'):
    #     # The API should not return sting_data in Secrets, but just in case
    #     obj_dict.pop('string_data')
    # if obj_dict['metadata'].get('annotations'):
    #     # Remove things like 'openshift.io/token-secret' from metadata
    #     for key in [k for k in obj_dict['metadata']['annotations'] if 'secret' in k]:
    #         obj_dict['metadata']['annotations'].pop(key)
    pass


class KubernetesAnsibleModule(AnsibleModule):
    resource_definition = None
    api_version = None
    kind = None

    def __init__(self, *args, **kwargs):

        if not HAS_K8S_MODULE_HELPER:
            raise Exception(
                "This module requires the OpenShift Python client. Try `pip install openshift`"
            )

        if not HAS_YAML:
            raise Exception(
                "This module requires PyYAML. Try `pip install PyYAML`"
            )

        kwargs['argument_spec'] = self.argspec
        AnsibleModule.__init__(self, *args, **kwargs)

    @property
    def argspec(self):
        raise NotImplementedError()

    def execute_module(self):
        raise NotImplementedError()

    # TODO this no longer matches the structure of returned attributes
    def exit_json(self, **return_attributes):
        """ Filter any sensitive data that we don't want logged """
        if return_attributes.get('result') and \
           return_attributes['result'].get('kind') in ('Secret', 'SecretList'):
            if return_attributes['result'].get('data'):
                remove_secret_data(return_attributes['result'])
            elif return_attributes['result'].get('items'):
                for item in return_attributes['result']['items']:
                    remove_secret_data(item)
        super(KubernetesAnsibleModule, self).exit_json(**return_attributes)

    def get_api_client(self):
        auth_args = AUTH_ARG_SPEC.keys()

        configuration = kubernetes.client.Configuration()
        for key, value in iteritems(self.params):
            if key in auth_args and value is not None:
                if key == 'api_key':
                    setattr(configuration, key, {'authorization': "Bearer {}".format(value)})
                else:
                    setattr(configuration, key, value)
            elif key in auth_args and value is None:
                env_value = os.getenv('K8S_AUTH_{}'.format(key.upper()), None)
                if env_value is not None:
                    setattr(configuration, key, env_value)

        kubernetes.client.Configuration.set_default(configuration)

        if self.params.get('username') and self.params.get('password') and self.params.get('host'):
            auth_method = 'self.params'
        elif self.params.get('api_key') and self.params.get('host'):
            auth_method = 'self.params'
        elif self.params.get('kubeconfig') or self.params.get('context'):
            auth_method = 'file'
        else:
            auth_method = 'default'

        # First try to do incluster config, then kubeconfig
        # TODO: Re-evaluate at some point (can be hard to force file)
        if auth_method == 'default':
            try:
                kubernetes.config.load_incluster_config()
                return DynamicClient(kubernetes.client.ApiClient())
            except kubernetes.config.ConfigException:
                return DynamicClient(self.client_from_kubeconfig(self.params.get('kubeconfig'), self.params.get('context')))

        if auth_method == 'file':
            return DynamicClient(self.client_from_kubeconfig(self.params.get('kubeconfig'), self.params.get('context')))

        if auth_method == 'params':
            return DynamicClient(kubernetes.client.ApiClient(configuration))

    def client_from_kubeconfig(self, config_file, context):
        try:
            return kubernetes.config.new_client_from_config(config_file, context)
        except (IOError, kubernetes.config.ConfigException):
            # If we failed to load the default config file then we'll return
            # an empty configuration
            # If one was specified, we will crash
            if not config_file:
                return kubernetes.client.ApiClient()
            raise

    def exact_match(self, definition):
        return {
            'kind': definition.get('kind'),
            'api_version': definition.get('apiVersion'),
        }

    def remove_aliases(self):
        """
        The helper doesn't know what to do with aliased keys
        """
        for k, v in iteritems(self.argspec):
            if 'aliases' in v:
                for alias in v['aliases']:
                    if alias in self.params:
                        self.params.pop(alias)

    def load_resource_definitions(self, src):
        """ Load the requested src path """
        result = None
        path = os.path.normpath(src)
        if not os.path.exists(path):
            self.fail_json(msg="Error accessing {0}. Does the file exist?".format(path))
        try:
            result = list(yaml.safe_load_all(open(path, 'r')))
        except (IOError, yaml.YAMLError) as exc:
            self.fail_json(msg="Error loading resource_definition: {0}".format(exc))
        return result

    @staticmethod
    def diff_objects(existing, new):

        def get_shared_attrs(o1, o2):
            shared_attrs = {}
            for k, v in o2.items():
                if isinstance(v, dict):
                    shared_attrs[k] = get_shared_attrs(o1.get(k, {}), v)
                else:
                    shared_attrs[k] = o1.get(k)
            return shared_attrs

        diffs = list(diff(new, get_shared_attrs(existing, new)))
        match = len(diffs) == 0
        return match, diffs

