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
from itools.gettext import MSG
from itools.web import get_context

# Import from ikaaro

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
        {'name': 'opportunity', 'value': MSG(u"Opp.")},
        {'name': 'project', 'value': MSG(u"Proj.")},
        {'name': 'finished', 'value': MSG(u"Fin.")},
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

