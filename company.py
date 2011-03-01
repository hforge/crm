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
from itools.datatypes import PathDataType, String, Unicode
from itools.gettext import MSG

# Import from ikaaro
from ikaaro.folder import Folder
from ikaaro.folder_views import Folder_BrowseContent

# Import from crm
from base import CRMFolder
from base_views import CRMFolder_AddImage
from company_views import Company_AddForm, Company_EditForm
from company_views import Company_View
from utils import generate_code


class Company(CRMFolder):
    """ A Company is a folder with metadata containing files related to it such
        as logo, images, ...
    """
    class_id = 'company'
    class_version = '20100916'
    class_title = MSG(u'Company')
    class_icon16 = 'crm/icons/16x16/company.png'
    class_icon48 = 'crm/icons/48x48/company.png'
    class_sprite16 = 'company'
    class_views = ['view', 'goto_missions', 'goto_contacts',
            'goto_companies']

    class_schema = freeze(merge_dicts(
        CRMFolder.class_schema,
        crm_c_address_1=Unicode(source='metadata', stored=True),
        crm_c_address_2=Unicode(source='metadata', stored=True),
        crm_c_zipcode=String(source='metadata', stored=True),
        crm_c_town=Unicode(source='metadata', stored=True),
        crm_c_country=Unicode(source='metadata', stored=True),
        crm_c_phone=Unicode(source='metadata', stored=True),
        crm_c_fax=Unicode(source='metadata', stored=True),
        crm_c_website=Unicode(source='metadata', stored=True),
        crm_c_activity=Unicode(source='metadata', stored=True),
        crm_c_logo=PathDataType(source='metadata', default='.',
            stored=True)))

    # Views
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    edit = Company_EditForm()
    view = Company_View()


    #############################################
    # Ikaaro API
    #############################################
    def get_catalog_values(self):
        document = super(Company, self).get_catalog_values()
        title = self.get_title()
        description = self.get_property('description')
        values = [title or u'', description or u'']
        document['text'] = u' '.join(values)
        return document



###################################
# Container                       #
###################################
class Companies(Folder):
    """ Container of "company" resources. """
    class_id = 'companies'
    class_title = MSG(u'Companies')
    class_version = '20100304'
    class_views = ['new_company', 'browse_content']
    class_document_types = [Company]

    # Views
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    new_company = Company_AddForm()
    add_logo = CRMFolder_AddImage()


    def add_company(self, **values):
        names = self.get_names()
        name = generate_code(names, 'c%06d')
        return self.make_resource(name, Company, **values)
