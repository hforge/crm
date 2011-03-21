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
from itools.core import merge_dicts, freeze
from itools.datatypes import Decimal, Email, Integer
from itools.datatypes import String, Unicode
from itools.gettext import MSG

# Import from ikaaro
from ikaaro.comments import comment_datatype
from ikaaro.folder import Folder
from ikaaro.folder_views import Folder_BrowseContent

# Import from crm
from base import CRMFolder
from base_views import Comments_View
from contact_views import Contact_AddForm, Contact_EditForm, Contact_View
from contact_views import Contact_SearchMissions, Contact_ViewMissions
from datatypes import ContactStatus
from mission_views import Mission_EditForm
from utils import generate_code


class Contact(CRMFolder):
    class_id = 'contact'
    class_version = '20100924'
    class_icon16 = 'crm/icons/16x16/contact.png'
    class_icon48 = 'crm/icons/48x48/contact.png'
    # The class used to be named "Prospect" so the prefix is "p_"
    class_schema = freeze(merge_dicts(
        CRMFolder.class_schema,
        crm_p_company=String(source='metadata', indexed=True, stored=True),
        crm_p_lastname=Unicode(source='metadata', indexed=True, stored=True),
        crm_p_firstname=Unicode(source='metadata', indexed=True, stored=True),
        crm_p_phone=Unicode(source='metadata', stored=True),
        crm_p_mobile=Unicode(source='metadata', stored=True),
        crm_p_email=Email(source='metadata', stored=True),
        crm_p_position=Unicode(source='metadata'),
        crm_p_description=Unicode(source='metadata'),
        crm_p_status=ContactStatus(source='metadata', indexed=True,
            stored=True),
        comment=comment_datatype,
        # Store contact statistics
        crm_p_assured=Decimal(stored=True),
        crm_p_probable=Decimal(stored=True),
        crm_p_opportunity=Integer(stored=True),
        crm_p_project=Integer(stored=True),
        crm_p_finished=Integer(stored=True),
        crm_p_nogo=Integer(stored=True)))
    class_sprite16 = 'contact'
    class_title = MSG(u'Contact')
    class_views = ['view'] + CRMFolder.class_views_shortcuts

    # Views
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    edit_mission = Mission_EditForm()
    edit_form = Contact_EditForm()
    view = Contact_View()
    view_comments = Comments_View()
    search_missions = Contact_SearchMissions()
    view_missions = Contact_ViewMissions()


    #############################################
    # Ikaaro API
    #############################################
    def get_catalog_values(self):
        document = super(Contact, self).get_catalog_values()
        crm = self.parent.parent
        get_property = self.get_property

        document['crm_p_lastname'] = get_property('crm_p_lastname')
        # Index company name and index company title as text
        company_name = get_property('crm_p_company')
        title = u''
        if company_name:
            document['crm_p_company'] = company_name
            company = crm.get_resource('companies/%s' % company_name)
            try:
                title = company.get_property('title')
            except AttributeError:
                pass
        # Index lastname, firstname, email and comment as text
        values = [title or u'']
        values.append(get_property('crm_p_lastname') or u'')
        values.append(get_property('crm_p_firstname') or u'')
        values.append(get_property('crm_p_email') or u'')
        values.append(get_property('crm_p_description') or u'')
        # Index all comments as 'text', and check any alert
        values.extend(self.get_property('comment'))
        document['text'] = u' '.join(values)
        # Index status
        document['crm_p_status'] = get_property('crm_p_status')

        # Index assured amount (sum projects amounts)
        # Index probable amount (average missions amount by probability)
        assured = probable = decimal('0.0')
        cent = decimal('100.0')
        document['crm_p_opportunity'] = 0
        document['crm_p_project'] = 0
        document['crm_p_finished'] = 0
        document['crm_p_nogo'] = 0
        missions = crm.get_resource('missions')
        contact = self.name
        for mission in missions.get_resources():
            get_property = mission.get_property
            if contact not in get_property('crm_m_contact'):
                continue
            status = get_property('crm_m_status')
            if status:
                document['crm_p_' + status] += 1
            if status == 'nogo':
                continue
            # Get mission amount
            amount = (get_property('crm_m_amount') or 0)
            if status in ('project', 'finished'):
                assured += amount
            else:
                # Get mission probability
                if status == 'finished':
                    value = amount
                else:
                    probability = (get_property('crm_m_probability') or 0)
                    value = (probability * amount) / cent
                probable += value
        document['crm_p_assured'] = assured
        document['crm_p_probable'] = probable

        return document


    def get_title(self, language=None):
        p_lastname = self.get_property('crm_p_lastname').upper()
        p_firstname = self.get_property('crm_p_firstname')
        p_company = self.get_property('crm_p_company') or u''
        if p_company:
            company = self.get_resource('../../companies/%s' % p_company,
                    soft=True)
            p_company =  u' (%s)' % company.get_title() if company else u''
        return u'%s %s%s' % (p_lastname, p_firstname, p_company)


    #############################################
    # CRM API
    #############################################
    def get_first_mission(self, context):
        root = context.root
        crm = self.parent.parent
        parent_path = str('%s/missions' % crm.get_abspath())
        results = root.search(format='mission', parent_path=parent_path)
        mission = results.get_documents(sort_by='mtime', reverse=True)
        if not len(results):
            return None
        return mission[0].name



###################################
# Container                       #
###################################
class Contacts(Folder):
    """ Container of "contact" resources. """
    class_id = 'contacts'
    class_version = '20100922'
    class_title = MSG(u'Contacts')
    class_views = ['new_contact', 'browse_content']
    class_document_types = [Contact]

    # Views
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    new_contact = Contact_AddForm()


    def add_contact(self, **values):
        names = self.get_names()
        name = generate_code(names, 'c%06d')
        return self.make_resource(name, Contact, **values)
