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
    def provision(self, req, id, body=None):

    @wsgi.serializers(xml=PartnerTemplate)
    def estimate(self, req, id, body=None):
        num_instances = body['num_instances']
        context = req.environ['nova.context']
        compute_nodes = self.host_api.compute_node_get_all(context)

        pprint.pprint(compute_nodes)

    @wsgi.serializers(xml=PartnerTemplate)
    def create(self, req, body=None):
        #Define some constant
        cpus = 8
        ram = 16384
        points = {
            '1': 8,
            '2': 1,
            '3': 16,
            '4': 32,
            '5': 4
        }
        start_max_point = 8

        # pprint(req)
        # return {'scheduler_partner': {'scheduler': 'ACCEPTED'}}

        ctxt = req.environ['nova.context']

        partner_name = ctxt.user_name
        print "Receive request from %s" % partner_name
        req_flavor = DbAPI.flavor_get(ctxt, body['flavor'])
        req_num_instances = int(body['num_instances'])

        partner = DbAPI.partners_get_by_shortname(ctxt, partner_name)

        if not partner:
            return {'scheduler_partner': {'success': 0, 'message': 'You are not our partner! %s' % host}}

        print 'FLAVOR ID'
        print req_flavor['id']
        req_point = req_num_instances * points[str(req_flavor['id'])]
        requested = int(partner['requested'])
        satisfied = int(partner['satisfied'])
        limit_ratio = float(partner['limit_ratio'])
        if requested == 0:
            if (req_point + satisfied) > start_max_point:
                return {'scheduler_partner': {'success': 0, 'message': 'Limit ratio exceed! First request is just ' + `start_max_point`}}
        else:
            if ((req_point + satisfied) / float(requested)) > limit_ratio:
                return {'scheduler_partner': {'success': 0, 'message': 'Limit ratio exceed'}}

        instances = DbAPI.temp_instances_get_by_host(ctxt, partner_name)
        used_cpus = 0
        used_ram = 0
        for instance in instances:
            flavor = DbAPI.flavor_get(ctxt, instance.flavor)
            used_cpus += int(flavor['vcpus'])
            used_ram += int(flavor['memory_mb'])

        print used_cpus
        print used_ram

        cpus_need = int(req_flavor['vcpus']) * req_num_instances
        ram_need = int(req_flavor['memory_mb']) * req_num_instances

        if (used_ram + ram_need) <= ram or (used_cpus + cpus_need) <= cpus:

            DbAPI.partners_update(ctxt, partner_name, {
                'satisfied': req_point + satisfied
            })

            for i in range(req_num_instances):
                DbAPI.temp_instances_create({
                    'host': partner_name,
                    'flavor': req_flavor['id']
                })

            return {'scheduler_partner': {'success': 1, 'message': 'ACCEPTED', 'points': (req_point + satisfied)}}
        else:
            instance_ram_satisfy = (ram - used_ram) // int(req_flavor['memory_mb'])
            instance_cpu_satisfy = (cpus - used_cpus) // int(req_flavor['vcpus'])
            satisfy_instance = min(instance_cpu_satisfy, instance_ram_satisfy)
            return {'scheduler_partner': {'success': 0, 'message': 'REJECTED. We can only satisfy %s instances at this time' % satisfy_instance}}


class Scheduler_partner(extensions.ExtensionDescriptor):
    """Pass arbitrary key/value pairs to the scheduler."""

    name = "Partner"
    alias = "os-scheduler-partner"
    namespace = "http://docs.openstack.org/compute/ext/partner/api/v2"
    updated = "2014-10-27T00:00:00+00:00"

    def get_resources(self):
        resources = []

        res = extensions.ResourceExtension('os-scheduler-partner', PartnerController())

        resources.append(res)
        return resources
