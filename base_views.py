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
from decimal import Decimal as dec

# Import from itools
from itools.core import freeze
from itools.datatypes import Decimal, Unicode, DateTime
from itools.gettext import MSG
from itools.i18n import format_datetime, format_number
from itools.web import STLView
from itools.web import get_context

# Import from ikaaro
from ikaaro.comments import indent
from ikaaro.popup import DBResource_AddImage

# Import from crm


p_status_icons = {
    'lead': '/ui/crm/images/status_yellow.gif',
    'client': '/ui/crm/images/status_green.gif',
    'dead': '/ui/crm/images/status_gray.gif' }
m_status_icons = {
    'opportunity': '/ui/crm/images/status_yellow.gif',
    'project': '/ui/crm/images/status_green.gif',
    'nogo': '/ui/crm/images/status_gray.gif' }

REMOVE_ALERT_MSG = MSG(u"""Are you sure you want to remove this alert?""")


monolingual_schema = freeze({
    'title': Unicode,
    'description': Unicode,
    'subject': Unicode(hidden_by_default=True),
    'timestamp': DateTime(readonly=True)})


def format_amount(str_value, accept):
    value = Decimal.decode(str_value)
    value = value / dec('1000')
    return format_number(value, curr=u' k€', accept=accept)


# TODO delete
def get_form_values(form):
    values = {}
    for key, value in form.iteritems():
        if not value:
            continue
        values[key] = value
    return values



############
# Comments #
############

class Comments_View(STLView):

    access = 'is_allowed_to_edit'
    title = MSG(u'Comments')
    template = '/ui/crm/comments/view.xml'

    def get_namespace(self, resource, context):
        ns_comments = []
        comments = resource.metadata.get_property('comment') or []
        accept = context.accept_language
        for i, comment in enumerate(comments):
            author = comment.get_parameter('author')
            if author:
                user = resource.get_resource('/users/' + author, soft=True)
                if user:
                    author = user.get_title()
            comment_datetime = comment.get_parameter('date')
            attachment = comment.get_parameter('attachment')
            alert_datetime = comment.get_parameter('alert_datetime')
            if alert_datetime:
                alert_datetime = format_datetime(alert_datetime,
                        accept=accept)
            # TODO Add diff (useful at creation without any comment)
            ns_comment = {
                'id': i,
                'author': author,
                'datetime': format_datetime(comment_datetime, accept=accept),
                'attachment': attachment,
                'alert_datetime': alert_datetime,
                'comment': indent(comment.value)}
            ns_comments.append(ns_comment)
        # Sort comments from newer to older
        ns_comments = list(reversed(ns_comments))

        path_to_resource = context.get_link(resource)
        namespace = {'comments': ns_comments,
                     'path_to_resource': path_to_resource,
                     'msg_alert': REMOVE_ALERT_MSG }
        return namespace



#############
# CRMFolder #
#############

class CRMFolder_AddImage(DBResource_AddImage):

    def get_root(self, context):
        return context.resource


    def get_start(self, resource):
        return self.get_root(get_context())



class CRMFolder_AddForm(object):
    access = 'is_allowed_to_add'


    def get_value(self, resource, context, name, datatype):
        query = context.query
        if not getattr(datatype, 'multilingual', False):
            return query.get(name) or datatype.get_default()

        value = {}
        for language in resource.get_edit_languages(context):
            value[language] = query.get(name) or datatype.get_default()
        return value


    def check_edit_conflict(self, resource, context, form):
        context.edit_conflict = False
