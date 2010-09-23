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
from datetime import datetime, time
from decimal import Decimal as decimal

# Import from itools
from itools.datatypes import Decimal
from itools.gettext import MSG
from itools.i18n import format_datetime
from itools.web import STLView
from itools.web import get_context

# Import from ikaaro
from ikaaro.buttons import Button
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


def format_amount(str_value):
    value = Decimal.decode(str_value)
    value = value / decimal('1000')
    if float(value).is_integer():
        return '%d k€' % value
    return '%s k€' % str(value)


def get_form_values(form):
    values = {}
    for key, value in form.iteritems():
        if not value:
            continue
        if key == 'alert_date':
            value_time = form.get('alert_time', None) or time(9, 0)
            value = datetime.combine(value, value_time)
            values['alert_datetime'] = value
        elif key != 'alert_time':
            values[key] = value
    # Commit empty comment with attachment
    if values.get('comment') is None and values.get('attachment') is not None:
        values['comment'] = u"_"
    return values



class ButtonAddContact(Button):
    name = 'add_contact'
    access = 'is_allowed_to_edit'
    title = MSG(u'Add contact')



class ButtonUpdate(Button):
    name = 'update_mission'
    access = 'is_allowed_to_edit'
    title = MSG(u"Update mission")



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
        for i, comment in enumerate(comments):
            author = comment.get_parameter('author')
            if author:
                user = resource.get_resource('/users/' + author, soft=True)
                if user:
                    author = user.get_title()
            comment_datetime = comment.get_parameter('date')
            attachment = (comment.get_parameter('attachment') or [''])[0]
            alert_datetime = comment.get_parameter('alert_datetime')
            if alert_datetime:
                alert_datetime = format_datetime(alert_datetime)
            # TODO Add diff (useful at creation without any comment)
            ns_comment = {
                'id': i,
                'author': author,
                'datetime': format_datetime(comment_datetime),
                'attachment': str(attachment),
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
