# -*- coding: UTF-8 -*-
# Copyright (C) 2007-2008 Henry Obein <henry@itaapy.com>
# Copyright (C) 2008 Nicolas Deram <nicolas@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from itools
from itools.datatypes import Enumerate
from itools.web import get_context

# Import from ikaaro
from ikaaro.registry import get_resource_class



############################################################
# CRM
############################################################

class CompanyName(Enumerate):

    @classmethod
    def get_options(cls):
        context = get_context()
        site_root = context.resource.get_site_root()
        cls_crm = get_resource_class('crm')
        crm = context.resource
        while not isinstance(crm, cls_crm):
            crm = crm.parent
        parent_path = '%s/companies' % crm.get_abspath()
        results = context.root.search(format='company',
                                      parent_path=parent_path)

        options = []
        for brain in results.get_documents(sort_by='c_title'):
            name = brain.name
            value = brain.c_title
            # Reduce the length of the title
            if len(value) > 63:
                value = '%s...%s' % (value[:30], value[-30:])
            option = {'name': name, 'value': value}
            options.append(option)

        return options



class MissionStatus(Enumerate):

    options = [
        {'name': 'opportunity', 'value': u'Opportunity'},
        {'name': 'project', 'value': u'Project'},
        {'name': 'nogo', 'value': u'NoGo'}]



class ProspectStatus(Enumerate):

    options = [
        {'name': 'lead', 'value': u'Lead'},
        {'name': 'client', 'value': u'Client'},
        {'name': 'dead', 'value': u'Dead'}]



class ProspectName(Enumerate):

    @classmethod
    def get_options(cls):
        context = get_context()
        site_root = context.resource.get_site_root()
        cls_crm = get_resource_class('crm')
        crm = context.resource
        while not isinstance(crm, cls_crm):
            crm = crm.parent
        parent_path = '%s/prospects' % crm.get_abspath()
        results = context.root.search(format='prospect',
                                      parent_path=parent_path)

        options = []
        for brain in results.get_documents(sort_by='p_lastname'):
            name = brain.name
            value = brain.p_lastname
            option = {'name': name, 'value': value}
            options.append(option)

        return options

