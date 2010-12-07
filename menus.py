# -*- coding: UTF-8 -*-
# Copyright (C) 2010 Hervé Cauwelier <herve@itaapy.com>
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
from itools.database import OrQuery, PhraseQuery, AndQuery
from itools.gettext import MSG
from itools.web import get_context

# Import from ikaaro
from ikaaro.views import ContextMenu

# Import from crm
from utils import get_crm, get_crm_path_query


class ContactsMenu(ContextMenu):
    title = MSG(u"Related Contacts")


    def get_crm_path_query(self, context):
        """Shortcut.
        """
        return get_crm_path_query(get_crm(context.resource))


    def get_companies(self, context):
        """Get a list of companies related to context.resource.
        """
        raise NotImplementedError


    def get_contacts(self, context):
        """Get a list of all contacts from these companies.
        """
        company_names = self.get_companies(context)
        query = AndQuery(self.get_crm_path_query(context),
                PhraseQuery('format', 'contact'),
                OrQuery(*[PhraseQuery('crm_p_company', company)
                    for company in company_names]))
        results = context.root.search(query)
        for brain in results.get_documents(sort_by='title'):
            yield brain


    def get_items(self):
        context = get_context()
        root = context.root
        items = []
        for brain in self.get_contacts(context):
            contact = root.get_resource(brain.abspath)
            items.append({
                # TODO read brain.title
                'title': contact.get_title(),
                # TODO icon
                'src': '/ui/crm/icons/16x16/crm.png',
                'href': context.get_link(contact)})
        return items



class ContactsByMissionMenu(ContactsMenu):

    def get_companies(self, context):
        """From mission to companies.
        """
        root = context.root
        resource = context.resource
        query = AndQuery(self.get_crm_path_query(context),
                PhraseQuery('format', 'contact'),
                OrQuery(*[PhraseQuery('name', contact)
                    for contact in resource.get_property('crm_m_contact')]))
        results = root.search(query)
        return (brain.crm_p_company for brain in results.get_documents())



class ContactsByContactMenu(ContactsMenu):

    def get_companies(self, context):
        """From contact to companies.
        """
        return [context.resource.get_property('crm_p_company')]



class ContactsByCompanyMenu(ContactsMenu):

    def get_companies(self, context):
        """From company to... companies.
        """
        return [context.resource.name]



class MissionsMenu(ContextMenu):
    title = MSG(u"Related Missions")
    contact_menu = None


    def get_items(self):
        context = get_context()
        root = context.root
        contact_names = [brain.name
                for brain in self.contact_menu.get_contacts(context)]
        query = AndQuery(self.contact_menu.get_crm_path_query(context),
                PhraseQuery('format', 'mission'),
                OrQuery(*[PhraseQuery('crm_m_contact', contact)
                    for contact in contact_names]))
        results = root.search(query)
        items = []
        for brain in results.get_documents(sort_by='mtime', reverse=True):
            mission = root.get_resource(brain.abspath)
            items.append({
                # TODO read brain.title
                'title': mission.get_title(),
                # TODO icon
                'src': '/ui/crm/icons/16x16/crm.png',
                'href': context.get_link(mission)})
        return items
