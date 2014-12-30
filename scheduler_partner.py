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
from webob import exc

from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova.api.openstack import xmlutil
import nova.db.api as DbAPI
from pprint import pprint
from nova import compute
from nova.compute import flavors
from nova import exception
from nova.i18n import _
from oslo import messaging


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
        self.compute_api = compute.API()

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

        name = body['name']
        password = "1234567890"
        image_uuid = ""

        injected_files = []
        config_drive = None

        sg_names = []
        sg_names.append("default")
        sg_names = list(set(sg_names))

        requested_networks = None
        access_ip_v6 = None
        access_ip_v4 = None

        key_name = None
        user_data = None

        availability_zone = None
        block_device_mapping = []
        block_device_mapping_v2 = []
        legacy_bdm = not bool(block_device_mapping_v2)

        block_device_mapping = (block_device_mapping or block_device_mapping_v2)
        min_count = num_instances
        max_count = num_instances

        auto_disk_config = True
        scheduler_hints = {}

        try:
            _get_inst_type = flavors.get_flavor_by_flavor_id
            inst_type = _get_inst_type(flavor_id, ctxt=context,
                                       read_deleted="no")

            (instances, resv_id) = self.compute_api.create(context,
                        inst_type,
                        image_uuid,
                        display_name=name,
                        display_description=name,
                        key_name=key_name,
                        metadata={},
                        access_ip_v4=access_ip_v4,
                        access_ip_v6=access_ip_v6,
                        injected_files=injected_files,
                        admin_password=password,
                        min_count=min_count,
                        max_count=max_count,
                        requested_networks=requested_networks,
                        security_group=sg_names,
                        user_data=user_data,
                        availability_zone=availability_zone,
                        config_drive=config_drive,
                        block_device_mapping=block_device_mapping,
                        auto_disk_config=auto_disk_config,
                        scheduler_hints=scheduler_hints,
                        legacy_bdm=legacy_bdm,
                        check_server_group_quota=False)
        except (exception.QuotaError,
                exception.PortLimitExceeded) as error:
            raise exc.HTTPForbidden(
                explanation=error.format_message(),
                headers={'Retry-After': 0})
        except exception.InvalidMetadataSize as error:
            raise exc.HTTPRequestEntityTooLarge(
                explanation=error.format_message())
        except exception.ImageNotFound as error:
            msg = _("Can not find requested image")
            raise exc.HTTPBadRequest(explanation=msg)
        except exception.FlavorNotFound as error:
            msg = _("Invalid flavorRef provided.")
            raise exc.HTTPBadRequest(explanation=msg)
        except exception.KeypairNotFound as error:
            msg = _("Invalid key_name provided.")
            raise exc.HTTPBadRequest(explanation=msg)
        except exception.ConfigDriveInvalidValue:
            msg = _("Invalid config_drive provided.")
            raise exc.HTTPBadRequest(explanation=msg)
        except messaging.RemoteError as err:
            msg = "%(err_type)s: %(err_msg)s" % {'err_type': err.exc_type,
                                                 'err_msg': err.value}
            raise exc.HTTPBadRequest(explanation=msg)
        except UnicodeDecodeError as error:
            msg = "UnicodeError: %s" % error
            raise exc.HTTPBadRequest(explanation=msg)
        except (exception.ImageNotActive,
                exception.FlavorDiskTooSmall,
                exception.FlavorMemoryTooSmall,
                exception.NetworkNotFound,
                exception.PortNotFound,
                exception.FixedIpAlreadyInUse,
                exception.SecurityGroupNotFound,
                exception.InstanceUserDataTooLarge,
                exception.InstanceUserDataMalformed) as error:
            raise exc.HTTPBadRequest(explanation=error.format_message())
        except (exception.ImageNUMATopologyIncomplete,
                exception.ImageNUMATopologyForbidden,
                exception.ImageNUMATopologyAsymmetric,
                exception.ImageNUMATopologyCPUOutOfRange,
                exception.ImageNUMATopologyCPUDuplicates,
                exception.ImageNUMATopologyCPUsUnassigned,
                exception.ImageNUMATopologyMemoryOutOfRange) as error:
            raise exc.HTTPBadRequest(explanation=error.format_message())
        except (exception.PortInUse,
                exception.InstanceExists,
                exception.NoUniqueMatch) as error:
            raise exc.HTTPConflict(explanation=error.format_message())
        except exception.Invalid as error:
            raise exc.HTTPBadRequest(explanation=error.format_message())

        req.cache_db_instances(instances)
        server = self._view_builder.create(req, instances[0])

        server['server']['adminPass'] = "1234567890"

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

        if (req_vcpus <= usable_cpu) and (req_memory <= usable_memory):
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
