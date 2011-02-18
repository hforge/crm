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
from itools.core import thingy_property
from itools.datatypes import Enumerate
from itools.gettext import MSG
from itools.web import get_context

# Import from ikaaro
from ikaaro.cc import UsersList

# Import from crm
from utils import get_crm



############################################################
# CRM
############################################################

class CompanyName(Enumerate):

    @classmethod
    def get_options(cls):
        context = get_context()
        crm = get_crm(context.resource)
        parent_path = '%s/companies' % crm.get_abspath()
        root = context.root
        results = root.search(format='company', parent_path=parent_path)
        options = []
        for brain in results.get_documents(sort_by='title'):
            value = brain.title
            # Reduce the length of the title
            if len(value) > 63:
                value = '%s...%s' % (value[:30], value[-30:])
            options.append({
                'name': brain.name,
                'value': value})

        return options



class MissionStatus(Enumerate):
    options = [
        {'name': 'opportunity', 'value': MSG(u"Opportunity")},
        {'name': 'project', 'value': MSG(u"Project")},
        {'name': 'finished', 'value': MSG(u"Finished")},
        {'name': 'nogo', 'value': MSG(u"NoGo")}]



class MissionStatusShortened(Enumerate):
    options = [
        {'name': 'opportunity', 'value': MSG(u"Opportunity")},
        {'name': 'project', 'value': MSG(u"Win")},
        {'name': 'finished', 'value': MSG(u"Finished")},
        {'name': 'nogo', 'value': MSG(u"NoGo")}]



class ContactStatus(Enumerate):
    options = [
        {'name': 'lead', 'value': MSG(u"Lead")},
        {'name': 'client', 'value': MSG(u"Client")},
        {'name': 'dead', 'value': MSG(u"Dead")}]



class ContactName(Enumerate):

    @classmethod
    def get_options(cls):
        context = get_context()
        crm = get_crm(context.resource)
        parent_path = '%s/contacts' % crm.get_abspath()
        root = context.root
        results = root.search(format='contact', parent_path=parent_path)
        options = []
        for brain in results.get_documents(sort_by='crm_p_lastname'):
            options.append({
                'name': brain.name,
                'value': brain.title})

        return options



class CSVEditor(Enumerate):
    options = [
        {'name': 'oo', 'value': MSG(u"OpenOffice.org / LibreOffice"),
            'parameters': ('UTF-8', ','),
        },
        {'name': 'excel', 'value': MSG(u"MS Excel"),
            'parameters': ('CP1252', ';'),
        }]


    def get_parameters(cls, name):
        """Returns the value matching the given name, or the default value.
        """
        for option in cls.options:
            if option['name'] == name:
                return option['parameters']

        raise ValueError, name



class AssignedList(UsersList):
    NOT_ASSIGNED = 'notassigned'

    def get_default(self):
        return get_context().user.name


    @thingy_property
    def resource(self):
        return get_context().resource


    def get_options(self):
        options = super(AssignedList, self).get_options()
        options.append({
            'name': self.NOT_ASSIGNED,
            'value': MSG(u"(Not Assigned)")})
        return options
