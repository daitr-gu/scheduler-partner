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

authorize = extensions.extension_authorizer('compute', 'partner')


class PartnerTemplate(xmlutil.TemplateBuilder):
    def construct(self):
        root = xmlutil.TemplateElement('partner')
        elem = xmlutil.make_flat_dict('partner', selector='partner',
                                      subselector='partner')
        root.append(elem)

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
        rval = []
        rval.append({'partner': 'detail'})
        return {'partner': rval}

    @wsgi.serializers(xml=PartnerTemplate)
    def create(self, req):
        print "CREATE"
        return {'create': 'done'}


class Scheduler_partner(extensions.ExtensionDescriptor):
    """Pass arbitrary key/value pairs to the scheduler."""

    name = "Partner"
    alias = "os-scheduler-partner"
    namespace = "http://docs.openstack.org/compute/ext/partner/api/v2"
    updated = "2014-10-27T00:00:00+00:00"

    def get_resources(self):
        resources = []

        res = extensions.ResourceExtension('os-scheduler-partner', PartnerController(),
                                           collection_actions={"create": "POST"})

        resources.append(res)
        return resources
