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
from itools.csv import Property
from itools.datatypes import PathDataType, Unicode, DateTime
from itools.handlers import checkid
from itools.fs import FileName
from itools.uri import get_reference, Path
from itools.web import get_context

# Import from ikaaro
from ikaaro.access import RoleAware
from ikaaro.folder import Folder
from ikaaro.registry import get_resource_class
from ikaaro.utils import generate_name

# Import from crm
from base_views import CRMFolder_AddImage
from utils import get_path_and_view


class CRMFolder(RoleAware, Folder):
    """ Base folder for Company, Contact and Mission.
    """
    class_version = '20100912'
    class_document_types = []

    class_schema = merge_dicts(
        Folder.class_schema,
        RoleAware.class_schema,
        comment=Unicode(source='metadata', mandatory=True, multiple=True))

    # Views
    add_logo = CRMFolder_AddImage()


    def init_resource(self, **kw):
        Folder.init_resource(self, **kw)

        # Add current user as admin
        username = get_context().user.name
        admins = kw.get('admins', []) + [username]
        self.set_property('admins', tuple(admins))


    def get_value(self, name, record=None, context=None):
        cls_contact = get_resource_class('contact')
        # Get company values from current contact
        if isinstance(self, cls_contact) and name.startswith('crm_c_'):
            company = self.get_property('crm_p_company')
            if company:
                company = self.get_resource('../../companies/%s' % company)
                value = company.get_value(name, None, context)
                return value
            return None
        # Return date or time only
        if name == 'alert_date':
            alert_datetime = self.find_alert_datetime()
            if alert_datetime:
                return alert_datetime.date()
            return None
        elif name == 'alert_time':
            alert_datetime = self.find_alert_datetime()
            if alert_datetime:
                return alert_datetime.time()
            return None
        # Return value
        return self.get_property(name)


    def _update(self, values, context=None):
        """ Update metadata. """
        for key in self.class_schema:
            value = values.get(key)
            if value is None:
                continue
            if key == 'comment':
                # Date
                date = context.timestamp
                # Attachment
                attachment = values.get('attachment') or None
                if attachment is not None:
                    filename, mimetype, body = attachment
                    # Find a non used name
                    name = checkid(filename)
                    name, extension, language = FileName.decode(name)
                    name = generate_name(name, self.get_names())
                    # Add attachment
                    cls = get_resource_class(mimetype)
                    self.make_resource(name, cls, body=body,
                        filename=filename, extension=extension,
                        format=mimetype)
                    # Link
                    attachment = name
                # Author
                user = context.user
                author = user.name if user else None
                value = Property(value, date=date, author=author,
                        attachment=attachment)
            self.metadata.set_property(key, value)

        if context is not None:
            context.database.change_resource(self)



    def is_allowed_to_edit(self, user, resource):
        # Anonymous can touch nothing
        if user is None:
            return False

        site_root = self.get_site_root()
        # Any one who can edit parent, can edit any child
        if site_root.is_allowed_to_edit(user, site_root):
            return True

        # Current contact reviewers and admins can edit it
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

        # Current contact reviewers and admins can edit it
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
            for key in ('attachment',):
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
            for key in ('attachment',):
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

        self.set_property('comment', comments)


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
        comments = self.metadata.get_property('comment') or []
        for comment in comments:
            # XXX hardcoded, not typed
            for key in ('attachment',):
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

        self.set_property('comment', comments)


    def update_20100912(self):
        from itools.core import utc
        from mission import Mission
        from contact import Contact
        from company import Company
        from obsolete import MissionTableFile, ContactTableFile
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
        elif isinstance(self, Contact):
            cls = ContactTableFile
        elif isinstance(self, Company):
            cls = CompanyTableFile
        else:
            raise ValueError
        comments_handler = comments.parent.handler.get_handler('comments',
                cls)
        get_record_value = comments_handler.get_record_value
        item_comments = []
        for record in comments_handler.get_records():
            comment = get_record_value(record, 'comment')
            if comment:
                # mtime
                date = get_record_value(record, 'ts')
                if date is None:
                    raise ValueError, self.get_abspath()
                date = date.replace(tzinfo=utc)
                # attachment
                attachment = get_record_value(record, 'file')
                if not attachment or attachment == '.':
                    attachment = None
                comment = Property(comment, date=date, attachment=attachment)
                if cls is MissionTableFile:
                    # alert_datetime
                    alert_datetime = get_record_value(record,
                            'alert_datetime')
                    comment.set_parameter('alert_datetime', alert_datetime)
                    # next action
                    m_nextaction = get_record_value(record, 'm_nextaction')
                    comment.set_parameter('crm_m_nextaction', m_nextaction)
                item_comments.append(comment)
        metadata.set_property('comment', item_comments)

        # Other metadata
        record = comments_handler.get_record(-1)
        for key in self.class_schema.iterkeys():
            if key in ('comment', 'attachment'):
                continue
            source_key = key
            if key[:4] == 'crm_':
                source_key = key[4:]
            if source_key not in cls.record_properties:
                continue
            value = get_record_value(record, source_key)
            if value is not None:
                metadata.set_property(key, value)
        # Set mtime
        ts = get_record_value(record, 'ts')
        if ts is not None:
            metadata.set_property('mtime', ts)

        # Remove table comments
        self.del_resource('comments')
