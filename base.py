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
from itools.datatypes import PathDataType, Unicode, String
from itools.gettext import MSG
from itools.uri import get_reference, Path
from itools.web import get_context

# Import from ikaaro
from ikaaro.access import RoleAware
from ikaaro.folder import Folder
from ikaaro.folder_views import GoToSpecificDocument

# Import from itws
from itws.tags import TagsAware

# Import from crm
from base_views import CRMFolder_AddImage
from utils import get_path_and_view


class CRMFolder(TagsAware, RoleAware, Folder):
    """ Base folder for Company, Contact and Mission.
    """
    class_version = '20100912'
    class_document_types = []
    class_schema = freeze(merge_dicts(
        Folder.class_schema,
        RoleAware.class_schema,
        TagsAware.class_schema,
        sprite16=String(stored=True),
        comment=Unicode(source='metadata', mandatory=True, multiple=True)))
    class_sprite16 = None
    class_views_shortcuts = ['goto_missions', 'goto_contacts',
            'goto_companies', 'goto_add_contact', 'goto_add_company']

    # Views
    add_logo = CRMFolder_AddImage()
    goto_missions = GoToSpecificDocument(
            title=MSG(u"Missions"),
            specific_document='../..',
            specific_view='missions',
            adminbar_icon='crm16 crm16-mission-go')
    goto_contacts = GoToSpecificDocument(
            title=MSG(u"Contacts"),
            specific_document='../..',
            specific_view='contacts',
            adminbar_icon='crm16 crm16-contact-go')
    goto_companies = GoToSpecificDocument(
            title=MSG(u"Companies"),
            specific_document='../..',
            specific_view='companies',
            adminbar_icon='crm16 crm16-company-go')
    goto_add_contact = GoToSpecificDocument(
            title=MSG(u"Add Contact"),
            specific_document='../../contacts',
            specific_view='new_contact',
            adminbar_icon='crm16 crm16-contact-add')
    goto_add_company = GoToSpecificDocument(
            title=MSG(u"Add Company"),
            specific_document='../../companies',
            specific_view='new_company',
            adminbar_icon='crm16 crm16-company-add')


    def init_resource(self, **kw):
        Folder.init_resource(self, **kw)

        # Add current user as admin
        username = get_context().user.name
        admins = kw.get('admins', []) + [username]
        self.set_property('admins', tuple(admins))


    def get_catalog_values(self):
        return merge_dicts(
            Folder.get_catalog_values(self),
            TagsAware.get_catalog_values(self),
            sprite16=self.class_sprite16)


    def get_edit_languages(self, context):
        """Make the CRM monolingual.
        """
        site_root = self.get_site_root()
        return [site_root.get_default_language()]


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
        links =  RoleAware.get_links(self) | TagsAware.get_links(self)
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
            links.add(str(base.resolve2(path)))

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
                links.add(str(base.resolve2(path)))

        return links


    def update_links(self, source, target):
        Folder.update_links(self, source, target)
        TagsAware.update_links(self, source, target)

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
        TagsAware.update_relative_links(self, source)

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
