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
from datetime import date, datetime
from decimal import Decimal as dec

# Import from itools
from itools.core import freeze
from itools.datatypes import Decimal, Unicode
from itools.gettext import MSG
from itools.stl import STLTemplate
from itools.web import STLView, get_context

# Import from ikaaro
from ikaaro.autoform import MultilineWidget
from ikaaro.buttons import Button
from ikaaro.comments import indent
from ikaaro.popup import DBResource_AddImage
from ikaaro.utils import make_stl_template

# Import from crm
from datatypes import MissionStatus, MissionStatusShortened


DUMMY_COMMENT = u"_"


def format_amount(str_value, context):
    value = Decimal.decode(str_value)
    value = value / dec('1000')
    return context.format_number(value, curr=u' k€')


def monolingual_name(name):
    return name.split(':')[0]


def monolingual_widgets(namespace):
    widgets_namespace = {}
    for widget_namespace in namespace['widgets']:
        name = monolingual_name(widget_namespace['name'])
        if name in widgets_namespace:
            raise ValueError, "multiple languages detected in " + name
        widget = widget_namespace['widgets'][0]
        del widget_namespace['widgets']
        widget = widget(language=None)
        widget_namespace['widget'] = widget
        widgets_namespace[name] = widget_namespace
    namespace['widgets'] = widgets_namespace
    namespace['first_widget'] = monolingual_name(namespace['first_widget'])


def reset_comment(namespace, is_edit=False):
    for name, widget_namespace in namespace['widgets'].iteritems():
        if name == 'comment' and is_edit is True:
            widget_namespace['value'] = ''
            comment_widget = MultilineWidget('comment',
                    title=MSG(u'Comment'), rows=3, datatype=Unicode,
                    value=u'')
            widget_namespace['widget'] = comment_widget
            namespace['widgets'][name] = widget_namespace
            return


############################################################################
# Icons / Sprites
############################################################################

class Icon(STLTemplate):
    template = make_stl_template('''
        <img class="crm16 ${css} ${icon}" title="${title}"
            src="/ui/crm/images/1x1.gif" width="16" height="16"/>''')
    datatype = None
    icons = None
    css = None


    def __init__(cls, name, **kw):
        super(Icon, cls).__init__(**kw)
        cls.name = name


    def title(cls):
        if cls.datatype is None:
            return None
        return cls.datatype.get_value(cls.name)


    def icon(cls):
        if cls.icons is not None:
            return cls.icons.get(cls.name)
        return cls.name



class StatusIcon(Icon):
    datatype = MissionStatus
    icons = {
        'opportunity': "crm16-mission",
        'project': "crm16-project",
        'finished': "crm16-finished",
        'nogo': "crm16-nogo"}



class ShortStatusIcon(StatusIcon):
    datatype = MissionStatusShortened



class AlertIcon(Icon):
    icons = {
        'past': "crm16-bell-notification",
        'now': "crm16-bell-error",
        'future': "crm16-bell-go"}


class PhoneIcon(Icon):
    icons = {
        'crm_p_phone': "crm16-phone",
        'crm_p_mobile': "crm16-mobile",
        'crm_c_phone': "crm16-phone",
        'crm_c_fax': "crm16-fax"}


def get_alert_icon(alert):
    if alert is None:
        return None
    elif alert.date() < date.today():
        return AlertIcon('past')
    elif alert < datetime.now():
        return AlertIcon('now')
    return AlertIcon('future')



############################################################################
# Comments
############################################################################

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
            attachment = comment.get_parameter('attachment')
            value = comment.value
            if value == DUMMY_COMMENT:
                # Parameters displayed above the comment
                if not attachment:
                    continue
                else:
                    value = u""
            # TODO Add diff (useful at creation without any comment)
            ns_comment = {
                'id': i,
                'author': author,
                'datetime': context.format_datetime(comment_datetime),
                'attachment': attachment,
                'comment': indent(value)}
            ns_comments.append(ns_comment)
        # Sort comments from newer to older
        ns_comments = list(reversed(ns_comments))

        path_to_resource = context.get_link(resource)
        namespace = {
            'comments': ns_comments,
            'path_to_resource': path_to_resource}
        return namespace



############################################################################
# CRMFolder
############################################################################

class CRMFolder_AddImage(DBResource_AddImage):

    def get_root(self, context):
        return context.resource


    def get_start(self, resource):
        return self.get_root(get_context())



class ButtonAdd(Button):
    access = 'is_allowed_to_add'
    css = 'button-ok'
    title = MSG(u"Add")



class CRMFolder_AddForm(object):
    access = 'is_allowed_to_add'
    actions = freeze([
        ButtonAdd])


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
