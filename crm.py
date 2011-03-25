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

# Import from ikaaro
from ikaaro.folder import Folder
from ikaaro.folder_views import Folder_BrowseContent, GoToSpecificDocument
from ikaaro.resource_views import DBResource_Backlinks, DBResource_Edit
from ikaaro.skins import register_skin

# Import from crm
from company import Companies
from contact import Contacts
from crm_views import CRM_SearchMissions, CRM_SearchContacts
from crm_views import CRM_SearchCompanies, CRM_Test, CRM_ImportContacts
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
    class_views = ['alerts', 'missions', 'contacts', 'companies',
            'goto_contacts', 'goto_companies', 'import_contacts']

    __fixed_handlers__ = Folder.__fixed_handlers__ + ['companies',
            'contacts', 'missions']

    # Hide itws sidebar
    display_sidebar = False

    # Views
    missions = CRM_SearchMissions()
    contacts = CRM_SearchContacts()
    companies = CRM_SearchCompanies()
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    preview_content = Folder_BrowseContent(access='is_allowed_to_edit')
    edit = DBResource_Edit(styles=['/ui/crm/style.css'])
    backlinks = DBResource_Backlinks(access='is_allowed_to_edit')
    goto_contacts = GoToSpecificDocument(specific_document='contacts',
        adminbar_icon='crm16 crm16-contact-add',
        title=MSG(u'New contact'), access='is_allowed_to_edit')
    goto_companies = GoToSpecificDocument(specific_document='companies',
        adminbar_icon='crm16 crm16-company-add',
        title=MSG(u'New company'), access='is_allowed_to_edit')
    import_contacts = CRM_ImportContacts()
    test = CRM_Test()


    def init_resource(self, **kw):
        Folder.init_resource(self, **kw)
        # Companies
        self.make_resource('companies', Companies,
            title={'en': u'Companies', 'fr': u'Sociétés'})
        # Contacts
        self.make_resource('contacts', Contacts,
            title={'en': u'Contacts', 'fr': u'Contacts'})
        # Missions
        self.make_resource('missions', Missions,
            title={'en': u'Missions', 'fr': u'Missions'})



# Register crm skin
path = get_abspath('ui')
register_skin('crm', path)
