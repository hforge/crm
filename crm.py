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
from itools.core import get_abspath
from itools.gettext import MSG
from itools.handlers import folder as FolderHandler

# Import from ikaaro
from ikaaro.folder import Folder
from ikaaro.folder_views import Folder_BrowseContent, GoToSpecificDocument
from ikaaro.resource_views import DBResource_Backlinks
from ikaaro.skins import register_skin

# Import from crm
from company import Companies
from contact import Contacts
from crm_views import CRM_Alerts, CRM_SearchContacts
from crm_views import CRM_ExportToCSV, CRM_SearchMissions
from mission import Missions


class CRM(Folder):
    """ A CRM contains:
        - companies
        - contacts, fed by missions.
        - addresses (companies and contacts)
    """
    class_id = 'crm'
    class_version = '20100920'
    class_title = MSG(u'CRM')
    class_icon16 = 'crm/icons/16x16/crm.png'
    class_icon48 = 'crm/icons/48x48/crm.png'
    class_views = ['alerts', 'missions', 'contacts', 'goto_contacts',
                   'goto_companies', 'browse_content', 'edit']

    __fixed_handlers__ = Folder.__fixed_handlers__ + ['companies', 'contacts',
            'missions']

    # Views
    alerts = CRM_Alerts()
    contacts = CRM_SearchContacts()
    missions = CRM_SearchMissions()
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    preview_content = Folder_BrowseContent(access='is_allowed_to_edit')
    backlinks = DBResource_Backlinks(access='is_allowed_to_edit')
    export_to_csv = CRM_ExportToCSV()
    goto_contacts = GoToSpecificDocument(specific_document='contacts',
        title=MSG(u'New contact'), access='is_allowed_to_edit')
    goto_companies = GoToSpecificDocument(specific_document='companies',
        title=MSG(u'New company'), access='is_allowed_to_edit')


    def init_resource(self, **kw):
        Folder.init_resource(self, **kw)
        folder = self.handler

        # Companies
        self.make_resource('companies', Companies,
            title={'en': u'Companies', 'fr': u'Sociétés'})
        handler = FolderHandler()
        folder.set_handler('companies', handler)
        # Contacts
        self.make_resource('contacts', Contacts,
            title={'en': u'Contacts', 'fr': u'Contacts'})
        folder.set_handler('contacts', handler)
        # Missions
        self.make_resource('missions', Missions,
            title={'en': u'Missions', 'fr': u'Missions'})
        folder.set_handler('missions', handler)


    def update_20100920(self):
        """Rename prospect to contact
        """
        self.move_resource('prospects', 'contacts')



# Register crm skin
path = get_abspath('ui')
register_skin('crm', path)
