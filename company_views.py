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
from itools.core import merge_dicts, freeze, is_thingy
from itools.database import PhraseQuery
from itools.datatypes import PathDataType, String, Unicode
from itools.gettext import MSG
from itools.web import INFO, ERROR

# Import from ikaaro
from ikaaro.autoform import ImageSelectorWidget, MultilineWidget
from ikaaro.autoform import TextWidget
from ikaaro.datatypes import Multilingual
from ikaaro.resource_views import DBResource_Edit
from ikaaro.views import CompositeForm

# Import from crm
from base_views import CRMFolder_AddForm
from crm_views import CRM_SearchContacts
from menus import MissionsMenu, ContactsByCompanyMenu, CompanyMenu
from utils import get_crm
from views import TagsAware_Edit
from widgets import LinkWidget


MSG_NEW_COMPANY = INFO(u"Company added. You can now add a contact from "
        u"this company.")


company_schema = freeze(merge_dicts(
    DBResource_Edit.schema,
    description=Multilingual(hidden_by_default=False),
    crm_c_address_1=Unicode,
    crm_c_address_2=Unicode,
    crm_c_zipcode=String,
    crm_c_town=Unicode,
    # TODO Country should be CountryName (listed)
    crm_c_country=Unicode,
    crm_c_phone=Unicode,
    crm_c_fax=Unicode,
    crm_c_website=Unicode,
    crm_c_activity=Unicode,
    crm_c_logo=PathDataType))


company_widgets = freeze(
    DBResource_Edit.widgets[:2] + [
        TextWidget('crm_c_address_1', title=MSG(u'Address')),
        TextWidget('crm_c_address_2', title=MSG(u'Address (next)')),
        TextWidget('crm_c_zipcode', title=MSG(u'Zip Code'), size=10),
        TextWidget('crm_c_town', title=MSG(u'Town')),
        TextWidget('crm_c_country', title=MSG(u'Country')),
        TextWidget('crm_c_phone', title=MSG(u'Phone'), size=15),
        TextWidget('crm_c_fax', title=MSG(u'Fax'), size=15),
        LinkWidget('crm_c_website', title=MSG(u'Website'), size=30),
        TextWidget('crm_c_activity', title=MSG(u'Activity'), size=30),
        ImageSelectorWidget('crm_c_logo', title=MSG(u'Logo'),
            action='add_logo'),
        MultilineWidget('description', title=MSG(u'Observations'), rows=4)])



class Company_EditForm(TagsAware_Edit, DBResource_Edit):
    template = '/ui/crm/generic/auto_form.xml'
    title = MSG(u'Edit Company')
    styles = ['/ui/crm/style.css']
    context_menus = []
    query_schema = company_schema


    def _get_schema(self, resource, context):
        tags_schema = TagsAware_Edit._get_schema(self, resource, context)
        return freeze(merge_dicts(
            company_schema,
            # title is mandatory
            title=company_schema['title'](mandatory=True),
            # Tags
            tags=tags_schema['tags']))


    def _get_widgets(self, resource, context):
        tags_widgets = TagsAware_Edit._get_widgets(self, resource, context)
        return freeze(
                company_widgets
                + [tags_widgets[0]])


    def get_value(self, resource, context, name, datatype):
        if name == 'tags':
            return TagsAware_Edit.get_value(self, resource, context, name,
                    datatype)
        return DBResource_Edit.get_value(self, resource, context, name,
                datatype)


    def set_value(self, resource, context, name, form):
        if name == 'tags':
            return TagsAware_Edit.set_value(self, resource, context, name,
                    form)
        return DBResource_Edit.set_value(self, resource, context, name, form)



class Company_AddForm(CRMFolder_AddForm, Company_EditForm):
    title = MSG(u'New Company')
    context_menus = []


    def action(self, resource, context, form):
        company = resource.add_company()

        Company_EditForm.action(self, company, context, form)
        if is_thingy(context.message, ERROR):
            return

        crm = get_crm(resource)
        goto = '%s/contacts/;new_contact?crm_p_company=%s' % (
                context.get_link(crm), company.name)
        return context.come_back(MSG_NEW_COMPANY, goto)



class Company_ViewContacts(CRM_SearchContacts):
    search_template = None
    csv_columns = None

    columns_to_keep = ('sprite', 'title', 'email', 'phones', 'crm_p_position',
            'crm_p_opportunity', 'crm_p_project', 'crm_p_nogo',
            'crm_p_assured', 'crm_p_probable')


    def get_table_columns(self, resource, context):
        proxy = super(Company_ViewContacts, self)
        columns = proxy.get_table_columns(resource, context)
        to_keep = self.columns_to_keep
        return [column for column in columns if column[0] in to_keep]


    def get_items(self, resource, context, *args):
        args = list(args)
        args.append(PhraseQuery('crm_p_company', resource.name))
        proxy = super(Company_ViewContacts, self)
        return proxy.get_items(resource, context, *args)


    def get_namespace(self, resource, context):
        proxy = super(Company_ViewContacts, self)
        namespace = proxy.get_namespace(resource, context)
        namespace['crm-infos'] = False
        namespace['export-csv'] = False
        return namespace



class Company_View(CompositeForm):
    access = 'is_allowed_to_edit'
    title = MSG(u'View Company')
    styles = ['/ui/crm/style.css']
    context_menus = [
            MissionsMenu(contact_menu=ContactsByCompanyMenu()),
            ContactsByCompanyMenu(),
            CompanyMenu()]
    subviews = [
            Company_EditForm(),
            Company_ViewContacts()]
