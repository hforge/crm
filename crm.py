# -*- coding: UTF-8 -*-
# Copyright (C) 2009 Nicolas Deram <nicolas@itaapy.com>
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
from itools.core import get_abspath, merge_dicts
from itools.csv import Table as TableFile
from itools.datatypes import Date, DateTime, Decimal, Email, Integer, String
from itools.datatypes import Unicode, Boolean
from itools.gettext import MSG
from itools.web import get_context

# Import from ikaaro
from ikaaro.access import RoleAware
from ikaaro.folder import Folder
from ikaaro.folder_views import Folder_BrowseContent
from ikaaro.forms import TextWidget
from ikaaro.registry import get_resource_class, register_resource_class
from ikaaro.registry import register_field
from ikaaro.skins import register_skin
from ikaaro.table import Table

# Import from here
from datatypes import CompanyName
from crm_views import Prospect_EditForm, Prospect_NewInstance
from crm_views import Prospect_SearchMissions, Prospect_ViewMissions
from crm_views import Company_View, Prospect_Main
from crm_views import Mission_Edit, Mission_EditForm, Mission_NewInstance
from crm_views import Mission_NewInstanceForm
from crm_views import Mission_ViewComments, CRM_Alerts, CRM_SearchProspects
from crm_views import CRM_ExportToCSV
from datatypes import MissionStatus, ProspectStatus
from utils import generate_name


class CRMAddresses(TableFile):

    record_schema = {
      'c_title': Unicode(is_indexed=True, mandatory=True),
      'c_address_1': Unicode,
      'c_address_2': Unicode,
      'c_zipcode': String,
      'c_town': Unicode,
      'c_country': Unicode}


class Addresses(Table):

    class_id = 'crm_addresses'
    class_handler = CRMAddresses
    form = [
        TextWidget('c_title', title=MSG(u'Title')),
        TextWidget('c_address_1', title=MSG(u'Address')),
        TextWidget('c_address_2', title=MSG(u'Address (next)')),
        TextWidget('c_zipcode', title=MSG(u'Zip Code')),
        TextWidget('c_town', title=MSG(u'Town')),
        TextWidget('c_country', title=MSG(u'Country')),
    ]


class CommentsTableFile(TableFile):

    record_schema = {'comment': Unicode(mandatory=True),
                     'alert_datetime': DateTime,
                     'file': String}



class Comments(Table):

    class_id = 'mission-comments'
    class_title = MSG(u'Mission comments')
    class_handler = CommentsTableFile



class Mission(Folder):
    """ A mission is a folder containing:
        - a table of comments
        - documents related to comments
    """
    class_id = 'mission'
    class_title = MSG(u'Mission')
    class_views = []

    __fixed_handlers__ = Folder.__fixed_handlers__ + ['comments']


    @staticmethod
    def _make_resource(cls, folder, name, *args, **kw):
        Folder._make_resource(cls, folder, name, **kw)
        # Comments
        Comments._make_resource(Comments, folder, '%s/comments' % name,
                                title={'en': u'Comments',
                                       'fr': u'Commentaires'})


    @classmethod
    def get_metadata_schema(cls):
        schema = {
            'm_title': Unicode,
            'm_description': Unicode,
            # How many € ?
            'm_amount': Decimal,
            # Probability ?
            'm_probability': Integer,
            # The deadline
            'm_deadline': Date,
            # Opportunity/Project/NoGo
            'm_status': MissionStatus}
        return schema


    def _get_catalog_values(self):
        document = Folder._get_catalog_values(self)

        # Index all comments as 'text'
        comments_handler = self.get_resource('comments').handler
        get_value = comments_handler.get_record_value
        values = []
        has_alerts = False
        for record in comments_handler.get_records():
            # comment
            values.append(get_value(record, 'comment'))
            # alert
            if has_alerts is False and get_value(record, 'alert_datetime'):
                has_alerts = True

        document['text'] = u' '.join(values)
        # Index alerts
        document['m_has_alerts'] = has_alerts
        # Index status
        document['m_status'] = self.get_property('m_status')
        return document


    browse_content = Folder_BrowseContent(access=False)
    edit = Mission_Edit()
    edit_form = Mission_EditForm()
    new_instance = Mission_NewInstance()
    preview_content = None
    view_comments = Mission_ViewComments()



class Prospect(Folder, RoleAware):
    """ A prospect is a contact.
    """
    class_id = 'prospect'
    class_title = MSG(u'Prospect')

    class_views = ['main', 'search_missions', 'browse_users', 'add_user']
    class_document_types = [Mission]


    @classmethod
    def get_metadata_schema(cls):
        schema = RoleAware.get_metadata_schema()
        prospect_schema = {
            'p_company': CompanyName,
            'p_lastname': Unicode,
            'p_firstname': Unicode,
            'p_phone': Unicode,
            'p_mobile': Unicode,
            'p_email': Email,
            'p_comment': Unicode,
            # Lead/Client/Dead
            'p_status': ProspectStatus}
        return merge_dicts(schema, prospect_schema)


    @classmethod
    def _make_resource(cls, container, name, *args, **kw):
        # Add current user as admin
        username = get_context().user.name
        kw['admins'] = kw.get('admins', []) + [username]
        Folder._make_resource(container, name, *args, **kw)


    def _get_catalog_values(self):
        document = Folder._get_catalog_values(self)

        document['p_lastname'] = self.get_property('p_lastname')
        # Index company name and index company title as text
        company_name = self.get_property('p_company')
        company = self.get_resource('../companies/%s' % company_name)
        document['p_company'] = company_name
        # Index lastname, firstname, email and comment as text
        c_title = company.get_property('c_title') or ''
        values = [c_title]
        values.append(self.get_property('p_lastname'))
        values.append(self.get_property('p_firstname'))
        values.append(self.get_property('p_email'))
        values.append(self.get_property('p_comment'))
        document['text'] = u' '.join(values)
        # Index status
        document['p_status'] = self.get_property('p_status')

        # Index assured amount (sum projects amounts)
        # Index probable amount (average missions amount by probability)
        p_assured = p_probable = decimal('0.0')
        cent = decimal('100.0')
        missions = self.search_resources(format='mission')
        document['p_opportunity'] = 0
        document['p_project'] = 0
        document['p_nogo'] = 0
        for mission in missions:
            status = mission.get_property('m_status')
            if status:
                key = 'p_%s' % status
                document[key] += 1
            if status == 'nogo':
                continue
            # Get mission amount
            m_amount = (mission.get_property('m_amount') or 0)
            if status == 'project':
                p_assured += m_amount
            else:
                # Get mission probability
                m_probability = (mission.get_property('m_probability') or 0)
                value = (m_probability * m_amount) / cent
                p_probable += value

        document['p_assured'] = p_assured
        document['p_probable'] = p_probable

        return document


    def is_allowed_to_edit(self, user, resource):
        # Anonymous can touch nothing
        if user is None:
            return False

        site_root = self.get_site_root()
        # Any one who can edit parent, can edit any child
        if site_root.is_allowed_to_edit(user, site_root):
            return True

        # Current prospect reviewers and admins can edit it
        if self.has_user_role(user.name, 'admins'):
            return True
        if self.has_user_role(user.name, 'reviewers'):
            return True

        return False


    def is_allowed_to_add(self, user, resource):
        return self.is_allowed_to_edit(user, resource)


    def is_allowed_to_view(self, user, resource):
        # Anonymous can touch nothing
        if user is None:
            return False

        # Any one who can edit, can view as well
        if self.is_allowed_to_edit(user, resource):
            return True

        # Current prospect reviewers and admins can edit it
        if self.has_user_role(user.name, 'members'):
            return True

        return False


    def get_first_mission(self):
        root = self.get_root()
        results = root.search(format='mission',
                              parent_path=str(self.get_abspath()))
        if not results.get_n_documents():
            return None
        mission = results.get_documents(sort_by='mtime', reverse=True)
        return mission[0].name


    def add_mission(self, data):
        names = self.get_names()
        name = generate_name(names, 'm%03d')

        # Create the resource
        cls_mission = get_resource_class('mission')
        child = cls_mission.make_resource(cls_mission, self, name)
        # The metadata
        metadata = child.metadata
        for key, value in data.iteritems():
            metadata.set_property(key, value)

        # Add first comment
        comments = child.get_resource('comments')
        record = {'comment': data['m_description']}
        comments.handler.add_record(record)


    edit_mission = Mission_EditForm()
    edit_form = Prospect_EditForm()
    main = Prospect_Main()
    new_instance = Prospect_NewInstance()
    new_mission = Mission_NewInstanceForm()
    search_missions = Prospect_SearchMissions()
    view_missions = Prospect_ViewMissions()



class Company(Folder):
    """ A Company is a folder with metadata containing files related to it such
        as logo, images, ...
    """
    class_id = 'company'
    class_title = MSG(u'Company')

    class_views = ['view', 'edit', 'browse_content']


    @classmethod
    def get_metadata_schema(cls):
        return merge_dicts(Folder.get_metadata_schema(), c_title=Unicode,
                           c_address=Integer, c_phone=Unicode, c_fax=Unicode)


    def _get_catalog_values(self):
        document = Folder._get_catalog_values(self)
        document['c_title'] = self.get_property('c_title')
        return document


    def get_title(self, language=None):
        return self.get_property('c_title', language=language)


    def update_company(self, company_data):
        self.set_property('c_title', company_data['c_title'])
        self.set_property('c_phone', company_data['c_phone'])
        self.set_property('c_fax', company_data['c_fax'])

        # Update address
        c_address_1 = company_data['c_address_1'] or None
        c_address_2 = company_data['c_address_2'] or None
        if self.get_property('c_address_1') != c_address_1 or \
           self.get_property('c_address_2') != c_address_2:
            addresses = self.get_resource('../../addresses')
            record = {}
            record['c_title'] = company_data['c_title']
            record['c_address_1'] = company_data['c_address_1']
            record['c_address_2'] = company_data['c_address_2']
            record['c_zipcode'] = company_data['c_zipcode']
            record['c_town'] = company_data['c_town']
            record['c_country'] = company_data['c_country']
            record = addresses.handler.add_record(record)
            self.set_property('c_address', record.id)


    view = Company_View()



class Companies(Folder):
    """ Container of "company" resources. """
    class_id = 'companies'
    class_title = MSG(u'Companies')

    class_views = ['browse_content']
    class_document_types = [Company]



class CRM(Folder):
    """ A CRM contains:
        - companies
        - prospects, fed by missions.
        - addresses (companies and prospects)
    """
    class_id = 'crm'
    class_version = '20091230'
    class_title = MSG(u'CRM')
    class_icon16 = 'crm/icons/16x16/crm.png'
    class_icon48 = 'crm/icons/48x48/crm.png'
    class_views = ['search', 'alerts', 'new_resource?type=prospect',
                   'new_resource?type=company', 'browse_content', 'edit']
    class_document_types = [Company, Prospect]

    __fixed_handlers__ = Folder.__fixed_handlers__ + ['addresses']


    @staticmethod
    def _make_resource(cls, folder, name, *args, **kw):
        Folder._make_resource(cls, folder, name, **kw)
        # Addresses
        Addresses._make_resource(Addresses, folder, '%s/addresses' % name,
                                 title={'en': u'Addresses', 'fr': u'Adresses'})


    def add_company(self, company_data):
        # Add address to /addresses
        addresses = self.get_resource('addresses')
        record = {}
        metadata = {}
        for name in ['c_title', 'c_address_1', 'c_address_2', 'c_zipcode',
                     'c_town', 'c_country']:
            record[name] = company_data[name]
        record = addresses.handler.add_record(record)
        for name in ['c_title', 'c_phone', 'c_fax']:
            metadata[name] = company_data[name]
        metadata['c_address'] = record.id
        # Get approximate index of new company
        companies = self.get_resource('companies')
        companies_names = companies.get_names()
        index = len(companies_names)
        name = generate_name(companies_names, 'c%03d', index)
        Company.make_resource(Company, companies, name, **metadata)
        return name


    def update_20090724(self):
        addresses = self.get_resource('addresses')
        if addresses.metadata.format != 'crm_addresses':
            addresses.metadata.format = 'crm_addresses'
            addresses.metadata.set_changed()


    def update_20091230(self):
        """ Move companies into new folder "companies". """
        Companies.make_resource(Companies, self, 'companies')

        companies = self.get_root().search(format='company',
                                           parent_path=str(self.get_abspath()))
        for company in companies.get_documents():
            name = company.name
            self.move_resource(name, 'companies/%s' % name)


    alerts = CRM_Alerts()
    search = CRM_SearchProspects()
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    export_to_csv = CRM_ExportToCSV()


register_resource_class(Addresses)
register_resource_class(Comments)
register_resource_class(Company)
register_resource_class(Companies)
register_resource_class(CRM)
register_resource_class(Mission)
register_resource_class(Prospect)
# Mission fields
register_field('m_status', String(is_indexed=True))
register_field('m_has_alerts', Boolean(is_indexed=True))
# Prospect fields
register_field('p_lastname', Unicode(is_stored=True))
register_field('p_status', String(is_indexed=True))
register_field('p_company', String(is_indexed=True))
register_field('p_assured', Decimal(is_stored=True))
register_field('p_probable', Decimal(is_stored=True))
register_field('p_opportunity', Integer(is_stored=True))
register_field('p_project', Integer(is_stored=True))
register_field('p_nogo', Integer(is_stored=True))
# Company fields
register_field('c_title', Unicode(is_stored=True, is_indexed=True))

# Register crm skin
path = get_abspath('ui/crm')
register_skin('crm', path)

