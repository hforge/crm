# -*- coding: UTF-8 -*-
# Copyright (C) 2009-2010 Nicolas Deram <nicolas@itaapy.com>
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

# Import from the Standard Library
from decimal import Decimal as decimal

# Import from itools
from itools.core import merge_dicts
from itools.datatypes import Decimal, Email, Integer
from itools.datatypes import String, Unicode
from itools.gettext import MSG

# Import from ikaaro
from ikaaro.folder import Folder
from ikaaro.folder_views import Folder_BrowseContent

# Import from crm
from base import CRMFolder
from base_views import Comments_View
from contact_views import Contact_AddForm, Contact_EditForm, Contact_View
from contact_views import Contact_SearchMissions, Contact_ViewMissions
from mission_views import Mission_EditForm
from utils import generate_code, get_crm


class Contact(CRMFolder):
    class_id = 'contact'
    class_title = MSG(u'Contact')
    class_version = '20100921'

    class_views = ['view']

    # The class used to be named "Prospect" so the prefix is "p_"
    class_schema = merge_dicts(
        CRMFolder.class_schema,
        crm_p_company=String(source='metadata', indexed=True),
        crm_p_lastname=Unicode(source='metadata', stored=True),
        crm_p_firstname=Unicode(source='metadata'),
        crm_p_phone=Unicode(source='metadata'),
        crm_p_mobile=Unicode(source='metadata'),
        crm_p_email=Email(source='metadata'),
        crm_p_position=Unicode(source='metadata'),
        crm_p_description=Unicode(source='metadata'),
        crm_p_status=String(source='metadata', indexed=True),
        crm_p_assured=Decimal(source='metadata', stored=True),
        crm_p_probable=Decimal(source='metadata', stored=True),
        crm_p_opportunity=Integer(source='metadata', stored=True),
        crm_p_project=Integer(source='metadata', stored=True),
        crm_p_nogo=Integer(source='metadata', stored=True))

    # Views
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    edit_mission = Mission_EditForm()
    edit_form = Contact_EditForm()
    view = Contact_View()
    view_comments = Comments_View()
    search_missions = Contact_SearchMissions()
    view_missions = Contact_ViewMissions()


    def get_catalog_values(self):
        document = Folder.get_catalog_values(self)
        crm = get_crm(self)
        get_value = self.get_value

        document['crm_p_lastname'] = get_value('crm_p_lastname')
        # Index company name and index company title as text
        company_name = get_value('crm_p_company')
        c_title = u''
        if company_name:
            company = crm.get_resource('companies/%s' % company_name)
            get_c_value = company.get_value
            document['crm_p_company'] = company_name
            try:
                c_title = get_c_value('crm_c_title')
            except AttributeError:
                pass
        # Index lastname, firstname, email and comment as text
        values = [c_title or '']
        values.append(get_value('crm_p_lastname') or '')
        values.append(get_value('crm_p_firstname') or '')
        values.append(get_value('crm_p_email') or '')
        values.append(get_value('crm_p_description') or '')
        values.append(get_value('crm_p_comment') or '')
        # Index all comments as 'text', and check any alert
        values.extend(self.get_property('comment'))
        document['text'] = u' '.join(values)
        # Index status
        document['crm_p_status'] = get_value('crm_p_status')

        # Index assured amount (sum projects amounts)
        # Index probable amount (average missions amount by probability)
        p_assured = p_probable = decimal('0.0')
        cent = decimal('100.0')
        document['crm_p_opportunity'] = 0
        document['crm_p_project'] = 0
        document['crm_p_nogo'] = 0
        missions = crm.get_resource('missions')
        contact = self.name
        for mission in missions.get_resources():
            get_value = mission.get_value
            if contact not in get_value('crm_m_contact'):
                continue
            status = get_value('crm_m_status')
            if status:
                key = 'crm_p_%s' % status
                document[key] += 1
            if status == 'nogo':
                continue
            # Get mission amount
            m_amount = (get_value('crm_m_amount') or 0)
            if status == 'project':
                p_assured += m_amount
            else:
                # Get mission probability
                m_probability = (get_value('crm_m_probability')or 0)
                value = (m_probability * m_amount) / cent
                p_probable += value
        document['crm_p_assured'] = p_assured
        document['crm_p_probable'] = p_probable

        return document


    def get_first_mission(self, context):
        root = context.root
        crm = self.parent.parent
        parent_path = str('%s/missions' % crm.get_abspath())
        results = root.search(format='mission', parent_path=parent_path)
        mission = results.get_documents(sort_by='mtime', reverse=True)
        if not len(results):
            return None
        return mission[0].name


    def get_title(self, language=None):
        p_lastname = self.get_value('crm_p_lastname')
        p_firstname = self.get_value('crm_p_firstname')
        p_company = self.get_value('crm_p_company') or ''
        if p_company:
            company = self.get_resource('../../companies/%s' % p_company,
                                            soft=True)
            p_company =  u' (%s)' % company.get_title() if company else ''
        return '%s %s%s' % (p_lastname, p_firstname, p_company)


    def update_20100921(self):
        self.metadata.set_changed()
        self.metadata.format = 'contact'



###################################
# Container                       #
###################################
class Contacts(Folder):
    """ Container of "contact" resources. """
    class_id = 'contacts'
    class_version = '20100921'
    class_title = MSG(u'Contacts')
    class_views = ['new_contact', 'browse_content']
    class_document_types = [Contact]

    # Views
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    new_contact = Contact_AddForm()


    def add_contact(self, values):
        names = self.get_names()
        name = generate_code(names, 'c%06d')
        self.make_resource(name, Contact, **values)
        return name


    def update_20100920(self):
        self.metadata.set_changed()
        self.metadata.format = 'contacts'


    def update_20100921(self):
        """'p000001' -> 'c000001'
        """
        for name in self.get_names():
            self.move_resource(name, name.replace('p', 'c'))
