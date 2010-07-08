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
from itools.datatypes import Boolean, Date, DateTime, Decimal, Email, Integer
from itools.datatypes import PathDataType, String, Unicode
from itools.gettext import MSG
from itools.handlers import checkid
from itools.fs import FileName
from itools.web import get_context

# Import from ikaaro
from ikaaro.access import RoleAware
from ikaaro.folder import Folder
from ikaaro.folder_views import Folder_BrowseContent, GoToSpecificDocument
from ikaaro.registry import get_resource_class, register_field
from ikaaro.resource_views import DBResource_Backlinks
from ikaaro.skins import register_skin
from ikaaro.table import Table
from ikaaro.utils import generate_name as igenerate_name

# Import from here
from datatypes import CompanyName
from crm_views import Company_AddForm, Company_EditForm, Company_View
from crm_views import Prospect_AddForm, Prospect_EditForm
from crm_views import Prospect_SearchMissions, Prospect_ViewMissions
from crm_views import Prospect_View
from crm_views import Mission_Add, Mission_AddForm, Mission_EditForm
from crm_views import Mission_View, Mission_ViewProspects
from crm_views import Mission_ViewProspect
from crm_views import Comments_View, CRM_Alerts, CRM_SearchProspects
from crm_views import CRM_SearchMissions
from crm_views import CRM_ExportToCSV
from datatypes import MissionStatus, ProspectStatus
from utils import generate_name


class CommentsTableFile(TableFile):
    """ Base comments table used by Company, Prospect and Mission.
    """
    record_properties = {'comment': Unicode(mandatory=True),
                         'alert_datetime': DateTime,
                         'file': PathDataType }


    def _add_record(self, values):
        """ Get non set data from previous record.
        """
        last_record = self.get_record(-1)
        values_keys = values.keys()
        for key in self.record_properties.keys():
            if key in ('file', 'alert_datetime'):
                continue
            if key not in values_keys:
                values[key] = self.get_record_value(last_record, key)

        self.add_record(values)



class CRMFolder(Folder, RoleAware):
    """ Base folder for Company, Prospect and Mission.
    """
    class_document_types = []
    class_comments = None
    __fixed_handlers__ = Folder.__fixed_handlers__ + ['comments']


    @staticmethod
    def make_resource(cls, container, name, *args, **kw):
        if cls.class_comments is None:
            raise NotImplementedError
        # Split kw data into metadata and record data
        values = {}
        metadata = {}
        record_keys = cls.class_comments.class_handler.record_properties.keys()
        for key, value in kw.iteritems():
            if key in record_keys:
                values[key] = value
            else:
                metadata[key] = value

        # Add current user as admin
        username = get_context().user.name
        metadata['admins'] = kw.get('admins', []) + [username]
        resource = Folder.make_resource(cls, container, name, *args,
                                           **metadata)
        # Comments and data table
        cls_comments = cls.class_comments
        comments = cls_comments.make_resource(cls_comments, resource,
            'comments', title={'en': u'Comments', 'fr': u'Commentaires'})
        comments.handler.add_record(values)

        return name


    @classmethod
    def get_metadata_schema(cls):
        schema = RoleAware.get_metadata_schema()
        return merge_dicts(Folder.get_metadata_schema(), schema)


    def get_value(self, name, record=None, context=None):
        comments_handler = self.get_resource('comments').handler
        if record is None:
            record = comments_handler.get_record(-1)
        # Get company values from current prospect
        if isinstance(self, Prospect) and name[:2] == 'c_':
            company = comments_handler.get_record_value(record, 'p_company')
            if company:
                company = self.get_resource('../../companies/%s' % company)
                value = company.get_value(name, None, context)
                return value
            return None
        if name == 'alert_date':
            value = comments_handler.get_record_value(record, 'alert_datetime')
            return value.date() if value else None
        elif name == 'alert_time':
            value = comments_handler.get_record_value(record, 'alert_datetime')
            return value.time() if value else None
        value = comments_handler.get_record_value(record, name)
        return value


    def _update(self, values, context=None):
        """ Add a new record with new comment or update the last record."""
        if context is not None:
            context.server.change_resource(self)

        comments_handler = self.get_resource('comments').handler
        comment = values.get('comment') or None
        # Manage attachement file
        file = values.get('file') or None
        if file is not None:
            filename, mimetype, body = file
            # Find a non used name
            name = checkid(filename)
            name, extension, language = FileName.decode(name)
            name = igenerate_name(name, self.get_names())
            # Add attachement
            cls = get_resource_class(mimetype)
            cls.make_resource(cls, self, name, body=body,
                filename=filename, extension=extension,
                format=mimetype)
            # Link
            values['file'] = name
        # If no comment, only update fields
        if comment is None:
            last_record = comments_handler.get_record(-1)
            comments_handler.update_record(last_record.id, **values)
        # Add a new comment
        else:
            comments_handler._add_record(values)


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


###################################
# Mission                         #
###################################

class MissionTableFile(CommentsTableFile):

    record_properties = merge_dicts(CommentsTableFile.record_properties,
            # Mission title and description
            m_title=Unicode, m_description=Unicode,
            # Prospect name
            m_prospect=String(multiple=True),
            # How many € ?
            m_amount=Decimal,
            m_probability=Integer,
            m_deadline=Date,
            # Opportunity/Project/NoGo
            m_status=MissionStatus,
            # Next action
            m_nextaction=Unicode)



class MissionTable(Table):

    class_id = 'mission-comments'
    class_title = MSG(u'Mission comments')
    class_handler = MissionTableFile



class Mission(CRMFolder):
    """ A mission is a folder containing:
        - a table of comments
        - documents related to comments
    """
    class_id = 'mission'
    class_title = MSG(u'Mission')
    class_version = '20100204'
    class_views = ['view']
    class_comments = MissionTable


    def _get_catalog_values(self):
        document = Folder._get_catalog_values(self)

        comments_handler = self.get_resource('comments').handler
        get_record_value = comments_handler.get_record_value
        last_record = comments_handler.get_record(-1)
        crm_m_title = get_record_value(last_record, 'm_title')
        prospects = get_record_value(last_record, 'm_prospect')
        crm_m_description = get_record_value(last_record, 'm_description')
        crm_m_nextaction  = get_record_value(last_record, 'm_nextaction')
        # Index all comments as 'text', and check any alert
        values = [crm_m_title or '',
                  crm_m_description or '',
                  crm_m_nextaction or '']
        crm = self.parent.parent
        for p in prospects:
            prospect = crm.get_resource('prospects/%s' % p)
            values.append(prospect.get_value('p_lastname'))
            values.append(prospect.get_value('p_firstname'))
            c_title = prospect.get_value('c_title')
            if c_title:
                values.append(c_title)
        has_alerts = False
        for record in comments_handler.get_records():
            # comment
            values.append(u' '.join(get_record_value(record, 'comment')))
            # alert
            if has_alerts is False and \
              get_record_value(record, 'alert_datetime'):
                has_alerts = True
        document['text'] = u' '.join(values)
        # Index title
        document['crm_m_title'] = crm_m_title
        # Index m_nextaction
        document['crm_m_nextaction'] = crm_m_nextaction
        # Index prospect
        document['crm_m_prospect'] = prospects
        # Index alerts
        document['crm_m_has_alerts'] = has_alerts
        # Index status
        document['crm_m_status'] = get_record_value(last_record, 'm_status')
        return document


    browse_content = Folder_BrowseContent(access=False)
    edit_form = Mission_EditForm()
    preview_content = None
    view_comments = Comments_View()
    view_prospects = Mission_ViewProspects()
    view = Mission_View()


###################################
# Prospect                        #
###################################

class ProspectTableFile(CommentsTableFile):

    record_properties = merge_dicts(CommentsTableFile.record_properties,
        p_company=CompanyName, p_lastname=Unicode, p_firstname=Unicode,
        p_phone=Unicode, p_mobile=Unicode, p_email=Email,
        p_position=Unicode, p_description=Unicode,
        # Lead/Client/Dead
        p_status=ProspectStatus)



class ProspectTable(Table):

    class_id = 'prospect-comments'
    class_title = MSG(u'Prospect comments')
    class_handler = ProspectTableFile



class Prospect(CRMFolder):
    """ A prospect is a contact.
    """
    class_id = 'prospect'
    class_title = MSG(u'Prospect')
    class_version = '20100204'

    class_views = ['view']
    class_comments = ProspectTable


    def _get_catalog_values(self):
        document = Folder._get_catalog_values(self)
        crm = self.parent
        if not isinstance(crm, CRM):
            crm = crm.parent
        comments_handler = self.get_resource('comments').handler
        get_value = self.get_value

        document['crm_p_lastname'] = get_value('p_lastname')
        # Index company name and index company title as text
        company_name = get_value('p_company')
        c_title = u''
        if company_name:
            company = crm.get_resource('companies/%s' % company_name)
            get_c_value = company.get_value
            document['crm_p_company'] = company_name
            try:
                c_title = get_c_value('c_title')
            except AttributeError:
                pass
        # Index lastname, firstname, email and comment as text
        values = [c_title or '']
        values.append(get_value('p_lastname') or '')
        values.append(get_value('p_firstname') or '')
        values.append(get_value('p_email') or '')
        values.append(get_value('p_description') or '')
        values.append(get_value('p_comment') or '')
        # Index all comments as 'text', and check any alert
        has_alerts = False
        for record in comments_handler.get_records():
            # comment
            value = get_value('comment', record)
            if value:
                values.append(value)
            # alert
            if has_alerts is False and \
              get_value('alert_datetime', record):
                has_alerts = True
        document['text'] = u' '.join(values)
        # Index status
        document['crm_p_status'] = get_value('p_status')

        # Index assured amount (sum projects amounts)
        # Index probable amount (average missions amount by probability)
        p_assured = p_probable = decimal('0.0')
        cent = decimal('100.0')
        document['crm_p_opportunity'] = 0
        document['crm_p_project'] = 0
        document['crm_p_nogo'] = 0
        missions = crm.get_resource('missions')
        prospect = self.name
        for mission in missions.get_resources():
            get_value = mission.get_value
            if prospect not in get_value('m_prospect'):
                continue
            status = get_value('m_status')
            if status:
                key = 'crm_p_%s' % status
                document[key] += 1
            if status == 'nogo':
                continue
            # Get mission amount
            m_amount = (get_value('m_amount') or 0)
            if status == 'project':
                p_assured += m_amount
            else:
                # Get mission probability
                m_probability = (get_value('m_probability')or 0)
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
        lastname = self.get_value('p_lastname')
        firstname = self.get_value('p_firstname')
        company = self.get_value('p_company') or ''
        if company:
            company = self.get_resource('../../companies/%s' % company,
                                            soft=True)
            company =  u' (%s)' % company.get_title() if company else ''
        return '%s %s%s' % (lastname, firstname, company)


    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    edit_mission = Mission_EditForm()
    edit_form = Prospect_EditForm()
    view = Prospect_View()
    view_comments = Comments_View()
    search_missions = Prospect_SearchMissions()
    view_missions = Prospect_ViewMissions()


###################################
# Company                         #
###################################

class CompanyTableFile(CommentsTableFile):

    record_properties = merge_dicts(CommentsTableFile.record_properties,
        c_title=Unicode, c_address_1=Unicode, c_address_2=Unicode,
        c_zipcode=String, c_town=Unicode, c_country=Unicode,
        c_phone=Unicode, c_fax=Unicode, c_website=Unicode,
        c_description=Unicode, c_activity=Unicode)



class CompanyTable(Table):

    class_id = 'company-comments'
    class_title = MSG(u'Company comments')
    class_handler = CompanyTableFile



class Company(CRMFolder):
    """ A Company is a folder with metadata containing files related to it such
        as logo, images, ...
    """
    class_id = 'company'
    class_title = MSG(u'Company')
    class_version = '20100204'

    class_views = ['view', 'browse_content']
    class_comments = CompanyTable


    def _get_catalog_values(self):
        document = Folder._get_catalog_values(self)
        crm_c_title = self.get_title()
        crm_c_description = self.get_value('c_description')
        document['crm_c_title'] = crm_c_title
        values = [crm_c_title or '', crm_c_description or '']
        document['text'] = u' '.join(values)
        return document


    def get_title(self, language=None):
        comments_handler = self.get_resource('comments').handler
        get_record_value = comments_handler.get_record_value
        last_record = comments_handler.get_record(-1)
        return get_record_value(last_record, 'c_title', language)


    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    edit = Company_EditForm()
    view = Company_View()


###################################
# Containers                      #
###################################
class Companies(Folder):
    """ Container of "company" resources. """
    class_id = 'companies'
    class_title = MSG(u'Companies')
    class_version = '20100304'
    class_views = ['new_company', 'browse_content']
    class_document_types = [Company]

    def add_company(self, values):
        names = self.get_names()
        index = len(names)
        name = generate_name(names, 'c%06d', index)
        Company.make_resource(Company, self, name, **values)
        return name


    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    new_company = Company_AddForm()



class Prospects(Folder):
    """ Container of "prospect" resources. """
    class_id = 'prospects'
    class_title = MSG(u'Prospects')
    class_views = ['new_prospect', 'browse_content']
    class_document_types = [Prospect]

    def add_prospect(self, values):
        names = self.get_names()
        index = len(names)
        name = generate_name(names, 'p%06d', index)
        Prospect.make_resource(Prospect, self, name, **values)
        return name

    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    new_prospect = Prospect_AddForm()


class Missions(Folder):
    """ Container of "mission" resources. """
    class_id = 'missions'
    class_title = MSG(u'Missions')

    class_views = ['new_mission', 'browse_content']
    class_document_types = [Mission]

    def add_mission(self, values):
        names = self.get_names()
        index = len(names)
        name = generate_name(names, 'm%06d', index)
        Mission.make_resource(Mission, self, name, **values)
        return name

    add_form = Mission_AddForm()
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    new_mission = Mission_Add()
    view_prospect = Mission_ViewProspect()


###################################
# CRM                             #
###################################

class CRM(Folder):
    """ A CRM contains:
        - companies
        - prospects, fed by missions.
        - addresses (companies and prospects)
    """
    class_id = 'crm'
    class_version = '20100201'
    class_title = MSG(u'CRM')
    class_icon16 = 'crm/icons/16x16/crm.png'
    class_icon48 = 'crm/icons/48x48/crm.png'
    class_views = ['alerts', 'missions', 'prospects', 'goto_prospects',
                   'goto_companies', 'browse_content', 'edit']

    __fixed_handlers__ = Folder.__fixed_handlers__ + ['companies', 'prospects',
                                                      'missions']

    @staticmethod
    def _make_resource(cls, folder, name, *args, **kw):
        Folder._make_resource(cls, folder, name, **kw)
        # Companies
        Companies._make_resource(Companies, folder, '%s/companies' % name,
                                 title={'en': u'Companies', 'fr': u'Sociétés'})
        # Prospects
        Prospects._make_resource(Prospects, folder, '%s/prospects' % name,
                                 title={'en': u'Prospects', 'fr': u'Prospects'})
        # Missions
        Missions._make_resource(Missions, folder, '%s/missions' % name,
                                 title={'en': u'Missions', 'fr': u'Missions'})


    alerts = CRM_Alerts()
    prospects = CRM_SearchProspects()
    missions = CRM_SearchMissions()
    browse_content = Folder_BrowseContent(access='is_allowed_to_edit')
    preview_content = Folder_BrowseContent(access='is_allowed_to_edit')
    backlinks = DBResource_Backlinks(access='is_allowed_to_edit')
    export_to_csv = CRM_ExportToCSV()
    goto_prospects = GoToSpecificDocument(specific_document='prospects',
        title=MSG(u'New prospect'), access='is_allowed_to_edit')
    goto_companies = GoToSpecificDocument(specific_document='companies',
        title=MSG(u'New company'), access='is_allowed_to_edit')


# Mission fields
register_field('crm_m_title', Unicode(is_indexed=True, is_stored=True))
register_field('crm_m_nextaction', Unicode(is_stored=True))
register_field('crm_m_prospect', String(is_indexed=True, multiple=True))
register_field('crm_m_status', String(is_indexed=True))
register_field('crm_m_has_alerts', Boolean(is_indexed=True))
# Prospect fields
register_field('crm_p_lastname', Unicode(is_stored=True))
register_field('crm_p_status', String(is_indexed=True))
register_field('crm_p_company', String(is_indexed=True))
register_field('crm_p_assured', Decimal(is_stored=True))
register_field('crm_p_probable', Decimal(is_stored=True))
register_field('crm_p_opportunity', Integer(is_stored=True))
register_field('crm_p_project', Integer(is_stored=True))
register_field('crm_p_nogo', Integer(is_stored=True))
# Company fields
register_field('crm_c_title', Unicode(is_stored=True, is_indexed=True))

# Register crm skin
path = get_abspath('ui/crm')
register_skin('crm', path)

