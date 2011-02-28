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
from itools.core import merge_dicts, freeze
from itools.datatypes import Date, DateTime, Decimal, Integer
from itools.datatypes import String, Unicode
from itools.gettext import MSG

# Import from ikaaro
from ikaaro.comments import comment_datatype
from ikaaro.folder import Folder
from ikaaro.folder_views import Folder_BrowseContent

# Import from crm
from base import CRMFolder
from base_views import Comments_View
from mission_views import Mission_Add, Mission_AddForm, Mission_EditForm
from mission_views import Mission_View, Mission_ViewContacts
from mission_views import Mission_EditContacts, Mission_AddContacts
from mission_views import Mission_ViewContact
from datatypes import MissionStatus
from utils import generate_code


class Mission(CRMFolder):
    """ A mission is a folder containing:
        - metadata (including comments)
        - documents related to comments
    """
    class_id = 'mission'
    class_version = '20100927'
    class_title = MSG(u'Mission')
    class_icon16 = 'crm/icons/16x16/mission.png'
    class_icon48 = 'crm/icons/48x48/mission.png'
    class_views = ['view', 'add_contacts', 'edit_contacts', 'edit_alerts',
            'goto_missions', 'goto_contacts', 'goto_companies']

    class_schema = freeze(merge_dicts(
        CRMFolder.class_schema,
        crm_m_contact=String(source='metadata', indexed=True, stored=True,
            multiple=True),
        crm_m_status=MissionStatus(source='metadata', indexed=True,
            stored=True),
        crm_m_assigned=String(source='metadata', default='', indexed=True,
            stored=True),
        crm_m_cc=String(source='metadata', multiple=True),
        crm_m_amount=Decimal(source='metadata', stored=True),
        crm_m_probability=Integer(source='metadata', stored=True),
        crm_m_deadline=Date(source='metadata', stored=True),
        crm_m_alert=DateTime(source='metadata', indexed=False, stored=True),
        crm_m_nextaction=Unicode(source='metadata', indexed=False,
            stored=True),
        comment=comment_datatype(parameters_schema=merge_dicts(
            comment_datatype.parameters_schema,
            attachment=String))))

    # Views
    add_contacts = Mission_AddContacts()
    browse_content = Folder_BrowseContent(access=False)
    edit_form = Mission_EditForm()
    edit_contacts = Mission_EditContacts()
    preview_content = None
    view = Mission_View()
    view_comments = Comments_View()
    view_contacts = Mission_ViewContacts()


    #############################################
    # Ikaaro API
    #############################################
    def get_catalog_values(self):
        document = super(Mission, self).get_catalog_values()
        title = self.get_property('title')
        description = self.get_property('description')
        nextaction  = self.get_property('crm_m_nextaction')
        # Index all comments as 'text'
        values = [title or u'',
                  description or u'',
                  nextaction or u'']
        m_contacts = self.get_property('crm_m_contact')
        contacts = self.parent.parent.get_resource('contacts')
        for m_contact in m_contacts:
            contact = contacts.get_resource(m_contact)
            values.append(contact.get_property('crm_p_lastname'))
            values.append(contact.get_property('crm_p_firstname'))
            title = contact.get_property('title')
            if title:
                values.append(title)
        # Comment
        values.extend(self.get_property('comment'))
        document['text'] = u' '.join(values)
        return document


    #############################################
    # CRM API
    #############################################
    def get_last_comment(self):
        comments = self.metadata.get_property('comment') or []
        if comments:
            return comments[-1]
        return None



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


    def add_mission(self, **kw):
        names = self.get_names()
        name = generate_code(names, 'm%06d')
        return self.make_resource(name, Mission, **kw)
