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
from itools.core import get_abspath, merge_dicts
from itools.csv import Property
from itools.datatypes import Boolean, Date, DateTime, Decimal, Email, Integer
from itools.datatypes import PathDataType, String, Unicode
from itools.gettext import MSG
from itools.handlers import checkid, folder as FolderHandler
from itools.fs import FileName
from itools.uri import get_reference, Path
from itools.web import get_context

# Import from ikaaro
from ikaaro.access import RoleAware
from ikaaro.folder import Folder
from ikaaro.folder_views import Folder_BrowseContent, GoToSpecificDocument
from ikaaro.registry import get_resource_class
from ikaaro.resource_views import DBResource_Backlinks
from ikaaro.skins import register_skin
from ikaaro.utils import generate_name as igenerate_name

# Import from here
from crm_views import Company_AddForm, Company_AddImage, Company_EditForm
from crm_views import Company_View
from crm_views import Prospect_AddForm, Prospect_EditForm
from crm_views import Prospect_SearchMissions, Prospect_ViewMissions
from crm_views import Prospect_View
from crm_views import Mission_Add, Mission_AddForm, Mission_EditForm
from crm_views import Mission_View, Mission_ViewProspects
from crm_views import Mission_EditProspects, Mission_AddProspects
from crm_views import Mission_ViewProspect, Mission_EditAlerts
from crm_views import Comments_View, CRM_Alerts, CRM_SearchProspects
from crm_views import CancelAlert
from crm_views import CRM_ExportToCSV, CRM_SearchMissions
from datatypes import MissionStatus
from utils import generate_name, get_path_and_view


class CRMFolder(RoleAware, Folder):
    """ Base folder for Company, Prospect and Mission.
    """
    class_document_types = []

    class_schema = merge_dicts(
        Folder.class_schema,
        RoleAware.class_schema,
        comment=Unicode(source='metadata', mandatory=True, multiple=True),
        attachment=String(source='metadata', multiple=True))


    def init_resource(self, **kw):
        Folder.init_resource(self, **kw)
        RoleAware.init_resource(self, **kw)

        # Add current user as admin
        username = get_context().user.name
        admins = kw.get('admins', []) + [username]
        self.set_property('admins', tuple(admins))


    def get_value(self, name, record=None, context=None):
        # Get company values from current prospect
        if isinstance(self, Prospect) and name[:2] == 'crm_c_':
            company = self.get_property('crm_p_company')
            if company:
                company = self.get_resource('../../companies/%s' % company)
                value = company.get_value(name, None, context)
                return value
            return None
        # Return date or time only
        if name == 'alert_date':
            value = self.get_property('alert_datetime')
            return value.date() if value else None
        elif name == 'alert_time':
            value = self.get_property('alert_datetime')
            return value.time() if value else None
        # Return value
        return self.get_property(name)


    def _update(self, values, context=None):
        """ Update metadata. """
        if context is not None:
            context.database.change_resource(self)

        for key, value in values.iteritems():
            if key == 'attachment':
                # Manage attachement file
                file = values.get('attachment') or None
                if file is not None:
                    filename, mimetype, body = file
                    # Find a non used name
                    name = checkid(filename)
                    name, extension, language = FileName.decode(name)
                    name = igenerate_name(name, self.get_names())
                    # Add attachement
                    cls = get_resource_class(mimetype)
                    self.make_resource(name, cls, body=body,
                        filename=filename, extension=extension,
                        format=mimetype)
                    # Link
                    values['attachment'] = name
            elif key == 'comment':
                date = context.timestamp
                user = context.user
                author = user.name if user else None
                comment = Property(value, date=date, author=author)
            else:
                self.set_property(key, value)


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


    def get_links(self):
        links = Folder.get_links(self)
        base = self.get_canonical_path()

        # metadata
        schema = self.class_schema
        for key, datatype in schema.iteritems():
            if issubclass(datatype, PathDataType) is False:
                continue
            value = self.get_property(key)
            if not value:
                continue
            ref = get_reference(value)
            if ref.scheme:
                continue
            path, view = get_path_and_view(ref.path)
            links.append(str(base.resolve2(path)))

        # comments
        comments = self.metadata.get_property('comment') or []
        for comment in comments:
            # XXX hardcoded, not typed
            for key in ('file', 'crm_c_logo'):
                value = comment.get_parameter(key)
                if not value:
                    continue
                ref = get_reference(value)
                if ref.scheme:
                    continue
                path, view = get_path_and_view(ref.path)
                links.append(str(base.resolve2(path)))

        return links


    def update_links(self, source, target):
        Folder.update_links(self, source, target)

        base = self.get_canonical_path()
        resources_new2old = get_context().database.resources_new2old
        base = str(base)
        old_base = resources_new2old.get(base, base)
        old_base = Path(old_base)
        new_base = Path(base)

        # metadata
        schema = self.class_schema
        for key, datatype in schema.iteritems():
            if issubclass(datatype, PathDataType) is False:
                continue
            value = self.get_property(key)
            if not value:
                continue
            ref = get_reference(value)
            if ref.scheme:
                continue
            path, view = get_path_and_view(ref.path)
            path = str(old_base.resolve2(path))
            if path == source:
                # Hit the old name
                # Build the new path with the right path
                new_path = str(new_base.get_pathto(target)) + view
                self.set_property(key, Path(new_path))

        # comments
        comments = self.metadata.get_property('comment') or []
        for comment in comments:
            # XXX hardcoded, not typed
            for key in ('file', 'crm_c_logo'):
                value = comment.get_parameter(key)
                if not value:
                    continue
                ref = get_reference(value)
                if ref.scheme:
                    continue
                path, view = get_path_and_view(ref.path)
                path = str(old_base.resolve2(path))
                if path == source:
                    # Hit the old name
                    # Build the new path with the right path
                    new_path = str(new_base.get_pathto(target)) + view
                    comment.set_parameter(key, new_path)
                    # XXX set_property?

        get_context().database.change_resource(self)


    def update_relative_links(self, source):
        Folder.update_relative_links(self, source)

        target = self.get_canonical_path()
        resources_old2new = get_context().database.resources_old2new

        # metadata
        schema = self.class_schema
        for key, datatype in schema.iteritems():
            if issubclass(datatype, PathDataType) is False:
                continue
            value = self.get_property(key)
            if not value:
                continue
            ref = get_reference(value)
            if ref.scheme:
                continue
            path, view = get_path_and_view(ref.path)
            # Calcul the old absolute path
            old_abs_path = source.resolve2(path)
            # Check if the target path has not been moved
            new_abs_path = resources_old2new.get(old_abs_path,
                                                 old_abs_path)
            # Build the new path with the right path
            # Absolute path allow to call get_pathto with the target
            new_path = str(target.get_pathto(new_abs_path)) + view
            # Update the property
            self.set_property(key, Path(new_path))

        # comments
        comments = self.metadata.get_property('comment')
        for comment in comments:
            # XXX hardcoded, not typed
            for key in ('file', 'crm_c_logo'):
                value = comment.get_parameter(key)
                if not value:
                    continue
                ref = get_reference(value)
                if ref.scheme:
                    continue
                path, view = get_path_and_view(ref.path)
                # Calcul the old absolute path
                old_abs_path = source.resolve2(path)
                # Check if the target path has not been moved
                new_abs_path = resources_old2new.get(old_abs_path,
                                                     old_abs_path)
                # Build the new path with the right path
                # Absolute path allow to call get_pathto with the target
                new_path = str(target.get_pathto(new_abs_path)) + view
                # Update the record
                comment.set_parameter(key, new_path)
                # XXX set_property?


    def update_20100912(self):
        from itools.core import utc
        from obsolete import MissionTableFile, ProspectTableFile
        from obsolete import CompanyTableFile

        metadata = self.metadata
        attachments = []
        comments = self.get_resource('comments', soft=True)
        if not comments:
            print 'NO COMMENTS', self.get_abspath()
            return
        # Comments
        if isinstance(self, Mission):
            cls = MissionTableFile
        elif isinstance(self, Prospect):
            cls = ProspectTableFile
        elif isinstance(self, Company):
            cls = CompanyTableFile
        else:
            raise ValueError
        comments_handler = comments.parent.handler.get_handler('comments', cls)
        get_record_value = comments_handler.get_record_value
        item_comments = []
        for record in comments_handler.get_records():
            comment = get_record_value(record, 'comment')
            if comment:
                date = get_record_value(record, 'ts')
                if date is None:
                    raise ValueError
                date = date.replace(tzinfo=utc)
                comment = Property(comment, date=date)
                item_comments.append(comment)
            file = get_record_value(record, 'file')
            if file and file != '.':
                attachments.append(file)
        # Set comments
        metadata.set_property('comment', item_comments)
        # Attachments
        if attachments:
            metadata.set_property('attachment', attachments)

        # Other metadata
        record = comments_handler.get_record(-1)
        for key in self.class_schema.keys():
            if key in ('comment', 'file'):
                continue
            source_key = key
            if key[:4] == 'crm_':
                source_key = key[4:]
            value = get_record_value(record, source_key)
            if value is not None:
                metadata.set_property(key, value)
        # Set mtime
        ts = get_record_value(record, 'ts')
        if ts is not None:
            metadata.set_property('mtime', ts)

        # Remove table comments
        self.del_resource('comments')


###################################
# Mission                         #
###################################

class Mission(CRMFolder):
    """ A mission is a folder containing:
        - metadata (including comments)
        - documents related to comments
    """
    class_id = 'mission'
    class_title = MSG(u'Mission')
    class_version = '20100912'
    class_views = ['view', 'add_prospects', 'edit_prospects', 'edit_alerts']

    class_schema = merge_dicts(
        CRMFolder.class_schema,
        crm_m_title=Unicode(source='metadata', indexed=True, stored=True),
        crm_m_description=Unicode(source='metadata'),
        crm_m_nextaction=Unicode(source='metadata', stored=True),
        crm_m_prospect=String(source='metadata', indexed=True, multiple=True),
        crm_m_status=MissionStatus(source='metadata', indexed=True),
        crm_m_has_alerts=Boolean(indexed=True),
        alert_datetime=DateTime(source='metadata'),
        crm_m_amount=Decimal(source='metadata'),
        crm_m_probability=Integer(source='metadata'),
        crm_m_deadline=Date(source='metadata'))


    def get_catalog_values(self):
        document = CRMFolder.get_catalog_values(self)
        crm_m_title = self.get_property('crm_m_title')
        prospects = self.get_property('crm_m_prospect')
        crm_m_description = self.get_property('crm_m_description')
        crm_m_nextaction  = self.get_property('crm_m_nextaction')
        # Index all comments as 'text', and check any alert
        values = [crm_m_title or '',
                  crm_m_description or '',
                  crm_m_nextaction or '']
        crm = self.parent.parent
        for p in prospects:
            prospect = crm.get_resource('prospects/%s' % p)
            values.append(prospect.get_value('crm_p_lastname'))
            values.append(prospect.get_value('crm_p_firstname'))
            c_title = prospect.get_value('crm_c_title')
            if c_title:
                values.append(c_title)
        alert_datetime = self.get_property('alert_datetime')
        values.extend(self.get_property('comment'))
        document['text'] = u' '.join(values)
        # Index title
        document['crm_m_title'] = crm_m_title
        # Index m_nextaction
        document['crm_m_nextaction'] = crm_m_nextaction
        # Index prospect
        document['crm_m_prospect'] = prospects
        # Index alerts
        document['crm_m_has_alerts'] = alert_datetime is not None
        # Index status
        document['crm_m_status'] = self.get_property('crm_m_status')
        return document


    add_prospects = Mission_AddProspects()
    cancel_alert = CancelAlert()
    browse_content = Folder_BrowseContent(access=False)
    edit_alerts = Mission_EditAlerts()
    edit_form = Mission_EditForm()
    edit_prospects = Mission_EditProspects()
    preview_content = None
    view = Mission_View()
    view_comments = Comments_View()
    view_prospects = Mission_ViewProspects()


###################################
# Prospect                        #
###################################

class Prospect(CRMFolder):
    """ A prospect is a contact.
    """
    class_id = 'prospect'
    class_title = MSG(u'Prospect')
    class_version = '20100912'

    class_views = ['view']

    class_schema = merge_dicts(
        CRMFolder.class_schema,
        crm_p_company=String(source='metadata', indexed=True),
        crm_p_lastname=Unicode(source='metadata', stored=True),
        crm_p_firstname=Unicode(source='metadata'),
        crm_p_phone=Unicode(source='metadata'),
        crm_p_mobile=Unicode(source='metadata'),
        crm_p_email=Email(source='metadata'),
        crm_p_position=Unicode(source='metadata'),
        crm_p_description=Unicode(source='metadata'),
        crm_p_status=String(source='metadata', indexed=True),
        crm_p_assured=Decimal(source='metadata', stored=True),
        crm_p_probable=Decimal(source='metadata', stored=True),
        crm_p_opportunity=Integer(source='metadata', stored=True),
        crm_p_project=Integer(source='metadata', stored=True),
        crm_p_nogo=Integer(source='metadata', stored=True))


    def get_catalog_values(self):
        document = Folder.get_catalog_values(self)
        crm = self.parent
        if not isinstance(crm, CRM):
            crm = crm.parent
        get_value = self.get_value

        document['crm_p_lastname'] = get_value('crm_p_lastname')
        # Index company name and index company title as text
        company_name = get_value('crm_p_company')
        c_title = u''
        if company_name:
            company = crm.get_resource('companies/%s' % company_name)
            get_c_value = company.get_value
            document['crm_p_company'] = company_name
            try:
                c_title = get_c_value('crm_c_title')
            except AttributeError:
                pass
        # Index lastname, firstname, email and comment as text
        values = [c_title or '']
        values.append(get_value('crm_p_lastname') or '')
        values.append(get_value('crm_p_firstname') or '')
        values.append(get_value('crm_p_email') or '')
        values.append(get_value('crm_p_description') or '')
        values.append(get_value('crm_p_comment') or '')
        # Index all comments as 'text', and check any alert
        values.extend(self.get_property('comment'))
        document['text'] = u' '.join(values)
        # Index status
        document['crm_p_status'] = get_value('crm_p_status')

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
            if prospect not in get_value('crm_m_prospect'):
                continue
            status = get_value('crm_m_status')
            if status:
                key = 'crm_p_%s' % status
                document[key] += 1
            if status == 'nogo':
                continue
            # Get mission amount
            m_amount = (get_value('crm_m_amount') or 0)
            if status == 'project':
                p_assured += m_amount
            else:
                # Get mission probability
                m_probability = (get_value('crm_m_probability')or 0)
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
        lastname = self.get_value('crm_p_lastname')
        firstname = self.get_value('crm_p_firstname')
        company = self.get_value('crm_p_company') or ''
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

class Company(CRMFolder):
    """ A Company is a folder with metadata containing files related to it such
        as logo, images, ...
    """
    class_id = 'company'
    class_title = MSG(u'Company')
    class_version = '20100912'

    class_views = ['view', 'browse_content']

    class_schema = merge_dicts(
        CRMFolder.class_schema,
        crm_c_title=Unicode(source='metadata', stored=True, indexed=True),
        crm_c_address_1=Unicode(source='metadata'),
        crm_c_address_2=Unicode(source='metadata'),
        crm_c_zipcode=String(source='metadata'),
        crm_c_town=Unicode(source='metadata'),
        crm_c_country=Unicode(source='metadata'),
        crm_c_phone=Unicode(source='metadata'),
        crm_c_fax=Unicode(source='metadata'),
        crm_c_website=Unicode(source='metadata'),
        crm_c_description=Unicode(source='metadata'),
        crm_c_activity=Unicode(source='metadata'),
        crm_c_logo=PathDataType(source='metadata', default='.'))


    def get_catalog_values(self):
        document = Folder.get_catalog_values(self)
        crm_c_title = self.get_title()
        crm_c_description = self.get_value('crm_c_description')
        document['crm_c_title'] = crm_c_title
        values = [crm_c_title or '', crm_c_description or '']
        document['text'] = u' '.join(values)
        return document


    def get_title(self, language=None):
        return self.get_property('crm_c_title')


    add_logo = Company_AddImage()
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
        self.make_resource(name, Company, **values)
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
        self.make_resource(name, Prospect, **values)
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
        self.make_resource(name, Mission, **values)
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

    def init_resource(self, **kw):
        Folder.init_resource(self, **kw)
        folder = self.handler

        # Companies
        self.make_resource('companies', Companies,
            title={'en': u'Companies', 'fr': u'Sociétés'})
        handler = FolderHandler()
        folder.set_handler('companies', handler)
        # Prospects
        self.make_resource('prospects', Prospects,
            title={'en': u'Prospects', 'fr': u'Prospects'})
        folder.set_handler('prospects', handler)
        # Missions
        self.make_resource('missions', Missions,
            title={'en': u'Missions', 'fr': u'Missions'})
        folder.set_handler('missions', handler)


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


# Register crm skin
path = get_abspath('ui/crm')
register_skin('crm', path)

