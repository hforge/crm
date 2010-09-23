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

# Import from itools
from itools.core import merge_dicts
from itools.datatypes import Boolean, Date, DateTime, Decimal, Integer
from itools.datatypes import String, Unicode
from itools.gettext import MSG

# Import from ikaaro
from ikaaro.folder import Folder
from ikaaro.folder_views import Folder_BrowseContent

# Import from crm
from base import CRMFolder
from base_views import Comments_View
from mission_views import Mission_Add, Mission_AddForm, Mission_EditForm
from mission_views import Mission_View, Mission_ViewContacts, CancelAlert
from mission_views import Mission_EditContacts, Mission_AddContacts
from mission_views import Mission_ViewContact, Mission_EditAlerts
from datatypes import MissionStatus
from utils import generate_code


class Mission(CRMFolder):
    """ A mission is a folder containing:
        - metadata (including comments)
        - documents related to comments
    """
    class_id = 'mission'
    class_version = '20100921'
    class_title = MSG(u'Mission')
    class_views = ['view', 'add_contacts', 'edit_contacts', 'edit_alerts']

    class_schema = merge_dicts(
        CRMFolder.class_schema,
        crm_m_title=Unicode(source='metadata', indexed=True, stored=True),
        crm_m_description=Unicode(source='metadata'),
        crm_m_nextaction=Unicode(source='metadata', stored=True),
        crm_m_contact=String(source='metadata', indexed=True, multiple=True),
        crm_m_status=MissionStatus(source='metadata', indexed=True),
        crm_m_has_alerts=Boolean(indexed=True),
        alert_datetime=DateTime(source='metadata'),
        crm_m_amount=Decimal(source='metadata'),
        crm_m_probability=Integer(source='metadata'),
        crm_m_deadline=Date(source='metadata'))

    # Views
    add_contacts = Mission_AddContacts()
    cancel_alert = CancelAlert()
    browse_content = Folder_BrowseContent(access=False)
    edit_alerts = Mission_EditAlerts()
    edit_form = Mission_EditForm()
    edit_contacts = Mission_EditContacts()
    preview_content = None
    view = Mission_View()
    view_comments = Comments_View()
    view_contacts = Mission_ViewContacts()


    def get_catalog_values(self):
        document = CRMFolder.get_catalog_values(self)
        m_title = self.get_property('crm_m_title')
        contacts = self.get_property('crm_m_contact')
        m_description = self.get_property('crm_m_description')
        m_nextaction  = self.get_property('crm_m_nextaction')
        # Index all comments as 'text', and check any alert
        values = [m_title or '',
                  m_description or '',
                  m_nextaction or '']
        crm = self.parent.parent
        for p in contacts:
            contact = crm.get_resource('contacts/%s' % p)
            values.append(contact.get_value('crm_p_lastname'))
            values.append(contact.get_value('crm_p_firstname'))
            c_title = contact.get_value('crm_c_title')
            if c_title:
                values.append(c_title)
        alert_datetime = self.get_property('alert_datetime')
        values.extend(self.get_property('comment'))
        document['text'] = u' '.join(values)
        # Index title
        document['crm_m_title'] = m_title
        # Index crm_m_nextaction
        document['crm_m_nextaction'] = m_nextaction
        # Index contact
        document['crm_m_contact'] = contacts
        # Index alerts
        document['crm_m_has_alerts'] = alert_datetime is not None
        # Index status
        document['crm_m_status'] = self.get_property('crm_m_status')
        return document

    def update_20100921(self):
        """'crm_m_prospects' -> 'crm_m_contact'
        """
        contacts = self.get_property('crm_m_prospect')
        contacts = [c.replace('p', 'c') for c in contacts]
        self.set_property('crm_m_contact', contacts)
        self.set_property('crm_m_prospect', None)



###################################
# Container                       #
###################################
class Missions(Folder):
    """ Container of "mission" resources. """
    class_id = 'missions'
    class_title = MSG(u'Missions')

    class_views = ['new_mission', 'browse_content']
    class_document_types = [Mission]

    # Views
    add_form = Mission_AddForm()
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    new_mission = Mission_Add()
    view_contact = Mission_ViewContact()


    def add_mission(self, values):
        names = self.get_names()
        name = generate_code(names, 'm%06d')
        self.make_resource(name, Mission, **values)
        return name
