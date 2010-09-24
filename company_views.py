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
from itools.database import PhraseQuery
from itools.datatypes import PathDataType, String, Unicode
from itools.gettext import MSG

# Import from ikaaro
from ikaaro.autoform import AutoForm
from ikaaro.autoform import ImageSelectorWidget, MultilineWidget
from ikaaro.autoform import TextWidget
from ikaaro.messages import MSG_NEW_RESOURCE, MSG_CHANGES_SAVED
from ikaaro.views import CompositeForm

# Import from crm
from base_views import get_form_values
from crm_views import CRM_SearchContacts
from utils import get_crm
from widgets import LinkWidget


company_schema = {
    'crm_c_title': Unicode,
    'crm_c_address_1': Unicode,
    'crm_c_address_2': Unicode,
    # TODO Country should be CountryName (listed)
    'crm_c_zipcode': String,
    'crm_c_town': Unicode,
    'crm_c_country': Unicode,
    'crm_c_phone': Unicode,
    'crm_c_fax': Unicode,
    'crm_c_website': Unicode,
    'crm_c_description': Unicode,
    'crm_c_activity': Unicode,
    'crm_c_logo': PathDataType }

company_widgets = [
    TextWidget('crm_c_title', title=MSG(u'Title')),
    TextWidget('crm_c_address_1', title=MSG(u'Address')),
    TextWidget('crm_c_address_2', title=MSG(u'Address (next)')),
    TextWidget('crm_c_zipcode', title=MSG(u'Zip Code'), size=10),
    TextWidget('crm_c_town', title=MSG(u'Town')),
    TextWidget('crm_c_country', title=MSG(u'Country')),
    TextWidget('crm_c_phone', title=MSG(u'Phone'), size=15),
    TextWidget('crm_c_fax', title=MSG(u'Fax'), size=15),
    LinkWidget('crm_c_website', title=MSG(u'Website'), size=30),
    TextWidget('crm_c_activity', title=MSG(u'Activity'), size=30),
    ImageSelectorWidget('crm_c_logo', title=MSG(u'Logo'), action='add_logo'),
    MultilineWidget('crm_c_description', title=MSG(u'Observations'),
        default='', rows=4) ]


class Company_EditForm(AutoForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit company')
    styles = ['/ui/crm/style.css']


    def get_query_schema(self):
        return company_schema.copy()


    def get_schema(self, resource, context):
        # crm_c_title is mandatory
        return merge_dicts(company_schema,
                crm_c_title=company_schema['crm_c_title'](mandatory=True))


    def get_widgets(self, resource, context):
        return company_widgets[:]


    def get_value(self, resource, context, name, datatype):
        value = resource.get_value(name)
        return value if value is not None else datatype.default


    def action(self, resource, context, form):
        values = get_form_values(form)
        resource._update(values, context)
        context.message = MSG_CHANGES_SAVED



class Company_AddForm(Company_EditForm):

    access = 'is_allowed_to_add'
    title = MSG(u'New company')
    context_menus = []


    def get_value(self, resource, context, name, datatype):
        return context.query.get(name) or datatype.default


    def get_namespace(self, resource, context):
        namespace = AutoForm.get_namespace(self, resource, context)
        return namespace


    def action(self, resource, context, form):
        values = get_form_values(form)
        name = resource.add_company(values)
        crm = get_crm(resource)
        goto = context.get_link(crm)
        goto = '%s/contacts/;new_contact?crm_p_company=%s' % (goto, name)
        return context.come_back(MSG_NEW_RESOURCE, goto)



class Company_ViewContacts(CRM_SearchContacts):

    search_template = None

    def get_table_columns(self, resource, context):
        columns = []
        for column in self.table_columns:
            name, title, sort = column
            if name == 'crm_p_company':
                continue
            if name not in ('crm_p_email', 'crm_p_phone', 'crm_p_mobile'):
                columns.append(column)

        return columns


    def get_items(self, resource, context, *args):
        args = list(args)
        args.append(PhraseQuery('crm_p_company', resource.name))
        return CRM_SearchContacts.get_items(self, resource, context, *args)


    def get_namespace(self, resource, context):
        namespace = CRM_SearchContacts.get_namespace(self, resource, context)
        namespace['crm-infos'] = False
        namespace['export-csv'] = False
        return namespace



class Company_View(CompositeForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'View company')
    styles = ['/ui/crm/style.css']

    subviews = [Company_EditForm(), Company_ViewContacts()]