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
from itools.core import thingy
from itools.database import OrQuery, PhraseQuery, AndQuery
from itools.gettext import MSG
from itools.web import get_context

# Import from ikaaro
from ikaaro.utils import CMSTemplate

# Import from crm
from base_views import m_status_icons
from datatypes import MissionStatus
from utils import get_crm, get_crm_path_query, get_contact_title


class item(thingy):
    title = u""
    src = None
    src_title = None
    href = None
    css_class = None
    selected = False



class ContextMenu(CMSTemplate):
    template = '/ui/crm/generic/menu.xml'


    def items(self):
        raise NotImplementedError



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
                    for company in company_names if company]))
        results = context.root.search(query)
        for brain in results.get_documents(sort_by='title'):
            yield brain


    def is_selected(self, brain, resource, context):
        return brain.abspath == context.abspath


    def items(self):
        context = get_context()
        resource = context.resource
        items = []
        for brain in self.get_contacts(context):
            items.append(item(
                title=get_contact_title(brain, context),
                icon='contact',
                href=context.get_link(brain),
                selected=self.is_selected(brain, resource, context)))
        # New contact
        if resource.class_id == 'mission':
            items.append(item(
                title=MSG(u"Link Existing Contact"),
                icon='contact-add',
                href=';add_contacts',
                selected=False))
            m_contact = resource.get_property('crm_m_contact')
            if m_contact:
                contacts = resource.get_resource('../../contacts')
                contact = contacts.get_resource(m_contact[0])
                p_company = contact.get_property('crm_p_company')
                items.append(item(
                    title=MSG(u"New Contact"),
                    icon='contact-add',
                    href='../../contacts/?crm_p_company=' + p_company,
                    selected=False))
        elif resource.class_id == 'contact':
            p_company = resource.get_property('crm_p_company')
            items.append(item(
                title=MSG(u"New Contact"),
                icon='contact-add',
                href='../?crm_p_company=' + p_company,
                selected=False))
        elif resource.class_id == 'company':
            items.append(item(
                title=MSG(u"New Contact"),
                icon='contact-add',
                href='../../contacts/?crm_p_company=' + resource.name,
                selected=False))
        return items



class ContactsByMissionMenu(ContactsMenu):

    def is_selected(self, brain, resource, context):
        return brain.name in resource.get_property('crm_m_contact')


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

    def is_selected(self, brain, resource, context):
        return brain.name == resource.name


    def get_companies(self, context):
        """From contact to companies.
        """
        return [context.resource.get_property('crm_p_company')]



class ContactsByCompanyMenu(ContactsMenu):

    def is_selected(self, brain, resource, context):
        return brain.crm_p_company == resource.name


    def get_companies(self, context):
        """From company to... companies.
        """
        return [context.resource.name]



class MissionsMenu(ContextMenu):
    title = MSG(u"Related Missions")
    contact_menu = None


    def items(self):
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
            items.append(item(
                title=brain.title,
                icon=m_status_icons[brain.crm_m_status],
                src_title=MissionStatus.get_value(brain.crm_m_status),
                href=context.get_link(brain),
                selected=selected))
        # New mission
        if resource.class_id == 'mission':
            m_contact = resource.get_property('crm_m_contact')[0]
            items.append(item(
                title=MSG(u"New Mission"),
                icon='mission-add',
                href=('../;new_mission?crm_m_contact=' + m_contact),
                selected=False))
        elif resource.class_id == 'contact':
            items.append(item(
                title=MSG(u"New Mission"),
                icon='mission-add',
                href=('../../missions/;new_mission?crm_m_contact=' +
                    resource.name),
                selected=False))
        return items



class CompaniesMenu(ContextMenu):
    title = u"Related Companies"


    def items(self):
        context = get_context()
        resource = context.resource
        items = []
        if resource.class_id in ('contact', 'mission'):
            todo = []
            if resource.class_id == 'contact':
                p_company = resource.get_property('crm_p_company')
                if p_company:
                    todo.append(p_company)
            elif resource.class_id == 'mission':
                contacts = resource.get_resource('../../contacts')
                for m_contact in resource.get_property('crm_m_contact'):
                    contact = contacts.get_resource(m_contact)
                    p_company = contact.get_property('crm_p_company')
                    if p_company not in todo:
                        todo.append(p_company)
            companies = resource.get_resource('../../companies')
            for p_company in todo:
                company = companies.get_resource(p_company)
                items.append(item(
                    title=company.get_property('title'),
                    icon='company',
                    href=context.get_link(company),
                    selected=True))
        items.append(item(
            title=MSG(u"New Company"),
            icon='company-add',
            href=context.get_link(companies),
            selected=False))
        return items



class CompanyMenu(ContextMenu):
    title = MSG(u"New Company")
    contact_menu = None


    def items(self):
        context = get_context()
        resource = context.resource
        items = []
        if resource.class_id == 'company':
            items.append(item(
                title=MSG(u"New Company"),
                icon='company-add',
                href='..',
                selected=False))
        return items
