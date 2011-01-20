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
from utils import get_crm, get_crm_path_query, get_contact_title


class ContactsMenu(ContextMenu):
    template = '/ui/crm/generic/menu.xml'
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
        resource = context.resource
        abspath = resource.abspath
        items = []
        for brain in self.get_contacts(context):
            items.append({
                'title': get_contact_title(brain, context),
                'src': '/ui/crm/icons/16x16/contact.png',
                'href': context.get_link(brain),
                'selected': (brain.abspath == abspath)})
        if resource.class_id == 'mission':
            items.append({
                'title': MSG(u"New contact"),
                'src': '/ui/icons/16x16/add.png',
                'href': ';add_contacts',
                'selected': False})
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
    template = '/ui/crm/generic/menu.xml'
    title = MSG(u"Related Missions")
    contact_menu = None


    def get_items(self):
        context = get_context()
        resource = context.resource
        abspath = resource.abspath
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
            selected = False
            if resource.class_id == 'mission':
                selected = brain.abspath == abspath
            elif resource.class_id == 'contact':
                selected = (resource.name in brain.crm_m_contact)
            items.append({
                'title': brain.title,
                'src': '/ui/crm/icons/16x16/mission.png',
                'href': context.get_link(brain),
                'selected': selected})
        # New mission
        if resource.class_id == 'mission':
            m_contact = resource.get_property('crm_m_contact')[0]
            items.append({
                'title': MSG(u"New mission"),
                'src': '/ui/icons/16x16/add.png',
                'href': ('../;new_mission?crm_m_contact=' + m_contact),
                'selected': False})
        elif resource.class_id == 'contact':
            items.append({
                'title': MSG(u"New mission"),
                'src': '/ui/icons/16x16/add.png',
                'href': ('../../missions/;new_mission?crm_m_contact=' +
                    resource.name),
                'selected': False})
        return items



class CompaniesMenu(ContextMenu):
    template = '/ui/crm/generic/menu.xml'
    title = u"Related Companies"


    def get_items(self):
        context = get_context()
        resource = context.resource
        items = []
        if resource.class_id in ('contact', 'mission'):
            todo = []
            if resource.class_id == 'contact':
                p_company = resource.get_property('crm_p_company')
                todo.append(p_company)
            else:
                contacts = resource.get_resource('../../contacts')
                for m_contact in resource.get_property('crm_m_contact'):
                    contact = contacts.get_resource(m_contact)
                    p_company = contact.get_property('crm_p_company')
                    if p_company not in todo:
                        todo.append(p_company)
            companies = resource.get_resource('../../companies')
            for p_company in todo:
                company = companies.get_resource(p_company)
                items.append({
                    'title': company.get_property('title'),
                    'src': '/ui/crm/icons/16x16/company.png',
                    'href': context.get_link(company),
                    'selected': True})
        items.append({
            'title': MSG(u"New Company"),
            'src': '/ui/icons/16x16/add.png',
            'href': context.get_link(companies),
            'selected': False})
        return items



class CompanyMenu(ContextMenu):
    template = '/ui/crm/generic/menu.xml'
    title = MSG(u"New Company")
    contact_menu = None


    def get_items(self):
        context = get_context()
        resource = context.resource
        items = []
        if resource.class_id == 'company':
            items.append({
                'title': MSG(u"New Company"),
                'src': '/ui/icons/16x16/add.png',
                'href': '..',
                'selected': False})
        return items
