# Copyright 2011 OpenStack Foundation
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

import webob.exc

from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova.api.openstack import xmlutil
import nova.db.api as DbAPI
from pprint import pprint
from nova import compute
from nova.compute import flavors

authorize = extensions.extension_authorizer('compute', 'partner')


class PartnerTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        # root = xmlutil.TemplateElement('scheduler_partner', selector='scheduler')
        root = xmlutil.TemplateElement('scheduler_partner')
        # elem = xmlutil.make_flat_dict('scheduler_partner', selector='scheduler_partner',
        #                               subselector='scheduler_partner')
        # root.append(elem)

        return xmlutil.MasterTemplate(root, 1)


class PartnerController(object):
    def __init__(self):
        print "INIT PARTNER CONTROLLER"
        self.host_api = compute.HostAPI()

    def index(self, req):
        """Test new extension."""
        print "LIST"
        return "YEAH"
        # context = req.environ['nova.context']
        # authorize(context, action='index')
        #
        # rval = []
        # rval.append({'partner': 'test'})
        #
        # return {'partner': rval}

    @wsgi.serializers(xml=PartnerTemplate)
    def detail(self, req, body=None):
        print "LIST"
        return {'scheduler_partner': {'partner': 'detail'}}

    @wsgi.serializers(xml=PartnerTemplate)
    def action(self, req, id, body=None):
        context = req.environ['nova.context']
        compute_nodes = self.host_api.compute_node_get_all(context)
        pprint(compute_nodes)

    @wsgi.serializers(xml=PartnerTemplate)
    def provision(self, req, id, body=None):
        flavor_id = body['flavor_id']
        num_instances = body['num_instances']
        context = req.environ['nova.context']

        partner = DbAPI.partners_get_by_shortname(context, id)
        satisfied = partner['satisfied']

        DbAPI.partners_update(context, id, {
            'satisfied': satisfied + num_instances
        })

        print("Provisioning %s instances." % num_instances)

        return {'scheduler_partner': {'success': 1}}

    @wsgi.serializers(xml=PartnerTemplate)
    def estimate(self, req, id, body=None):
        flavor_id = body['flavor_id']
        num_instances = body['num_instances']
        context = req.environ['nova.context']

        compute_nodes = self.host_api.compute_node_get_all(context)
        total_cpu = 0
        usable_cpu = 0
        usable_memory = 0

        for hyp in compute_nodes:
            total_cpu += hyp['vcpus']
            usable_cpu = total_cpu - hyp['vcpus_used']

            usable_memory += hyp['memory_mb']
            usable_memory -= hyp['memory_mb_used']

        flavor = flavors.get_flavor_by_flavor_id(flavor_id, ctxt=context)
        req_vcpus = flavor.vcpus * num_instances
        req_memory = flavor.memory_mb * num_instances

        partner = DbAPI.partners_get_by_shortname(context, id)

        if not partner:
            print("This is not my partner")
            return {'scheduler_partner': {'success': 0, 'message': 'Contact our administrator to become our partner'}}

        if not self._is_can_satisfy(partner, flavor, total_cpu, num_instances):
            print("Out of ratio")
            return {'scheduler_partner': {'success': 0, 'message': 'Out of ratio'}}

        if (req_vcpus > usable_cpu) and (req_memory > usable_memory):
            print("ACCEPTED")
            return {'scheduler_partner': {'success': 1, 'message': 'ACCEPTED'}}
        else:
            print("Out of resources")
            return {'scheduler_partner': {'success': 0, 'message': 'Out of resources'}}

    @wsgi.serializers(xml=PartnerTemplate)
    def create(self, req, body=None):
        context = req.environ['nova.context']
        compute_nodes = self.host_api.compute_node_get_all(context)
        pprint(compute_nodes)

    def _is_can_satisfy(self, partner, flavor, total_cpu, num_instances):
        requested = partner['requested']
        satisfied = partner['satisfied']
        ratio = partner['limit_ratio']

        max_satisfiable = requested / ratio * total_cpu
        can_satisfy = max_satisfiable - satisfied

        return flavor.vcpus * num_instances <= can_satisfy


class Scheduler_partner(extensions.ExtensionDescriptor):
    """Pass arbitrary key/value pairs to the scheduler."""

    name = "Partner"
    alias = "os-scheduler-partner"
    namespace = "http://docs.openstack.org/compute/ext/partner/api/v2"
    updated = "2014-10-27T00:00:00+00:00"

    def get_resources(self):
        member_actions = {'estimate': 'POST', 'provision': 'POST'}
        resources = []

        res = extensions.ResourceExtension('os-scheduler-partner', PartnerController(),
                                           member_actions=member_actions)

        resources.append(res)
        return resources
