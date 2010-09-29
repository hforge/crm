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
from datetime import datetime

# Import from itools
from itools.core import merge_dicts
from itools.database import OrQuery, PhraseQuery
from itools.datatypes import Date, Decimal, Integer
from itools.datatypes import String, Unicode
from itools.gettext import MSG
from itools.i18n import format_datetime, format_date
from itools.ical import Time
from itools.web import BaseForm, ERROR

# Import from ikaaro
from ikaaro.buttons import Button, BrowseButton, RemoveButton
from ikaaro.autoform import AutoForm, DateWidget, MultilineWidget
from ikaaro.autoform import FileWidget, RadioWidget, TextWidget, SelectWidget
from ikaaro.cc import UsersList
from ikaaro.datatypes import FileDataType
from ikaaro.messages import MSG_NEW_RESOURCE, MSG_CHANGES_SAVED
from ikaaro.views import CompositeForm

# Import from crm
from base_views import get_form_values
from base_views import Comments_View
from crm_views import CRM_SearchContacts, CRM_Alerts
from datatypes import MissionStatus, ContactName
from utils import get_crm
from widgets import TimeWidget


CHANGES_LINE = MSG(u"{what:>19}|{removed:<28}|{added:<27}")
COMMENT_LINE = MSG(u"--- Comment {n} from {user_title} <{user_email}> {date} ---")
BODY = MSG(u'''DO NOT REPLY TO THIS EMAIL. To comment on this mission, please visit:
{mission_uri}

#{mission_name} {mission_title}

{user_title} <{user_email}> changed:

{changes}

{comment}

-- 
You are receiving this e-mail because you are in CC.''')


mission_schema = {
    # First mission
    'crm_m_title': Unicode,
    'crm_m_description': Unicode,
    'crm_m_amount': Decimal,
    'crm_m_probability': Integer,
    'crm_m_deadline': Date,
    'crm_m_status': MissionStatus,
    # XXX must add resource in "get_schema"
    'crm_m_cc': UsersList(multiple=True),
    'comment': Unicode,
    'attachment': FileDataType,
    'alert_date': Date,
    'alert_time': Time,
    'crm_m_nextaction': Unicode}


mission_widgets = [
    # First mission
    TextWidget('crm_m_title', title=MSG(u'Title')),
    MultilineWidget('crm_m_description', title=MSG(u'Description'), rows=4),
    TextWidget('crm_m_amount', title=MSG(u'Amount'), default='', size=8),
    TextWidget('crm_m_probability', title=MSG(u'Probability'), default='',
               size=2),
    DateWidget('crm_m_deadline', title=MSG(u'Deadline'), default='', size=8),
    RadioWidget('crm_m_status', title=MSG(u'Status'), is_inline=True,
                has_empty_option=False),
    SelectWidget('crm_m_cc', title=MSG(u"CC"), multiple=True, size=5,
        has_empty_option=False),
    MultilineWidget('comment', title=MSG(u'New comment'), default='',
                    rows=3),
    FileWidget('attachment', title=MSG(u'Attachment'), size=35, default=''),
    DateWidget('alert_date', title=MSG(u'Alert on'), size=8),
    TimeWidget('alert_time', title=MSG(u'at')),
    TextWidget('crm_m_nextaction', title=MSG(u'Next action')) ]


def get_changes(resource, context, form, new=False):
    root = context.root
    changes = []
    for key in mission_schema:
        # Comment is treated separately
        if key == 'comment':
            continue
        new_value = form[key]
        if new:
            old_value = mission_schema[key].get_default()
        else:
            old_value = resource.get_value(key)
        if new_value == old_value:
            continue
        # Find widget title
        for widget in mission_widgets:
            if widget.name == key:
                break
        else:
            raise ValueError, key
        title = widget.title.gettext()
        # Special cases for complex objects
        if key == 'crm_m_cc':
            what = title
            for removed in (set(old_value) - set(new_value)):
                user = root.get_user(removed)
                if user is not None:
                    removed = user.get_title()
                changes.append(CHANGES_LINE.gettext(what=what,
                    removed=removed, added=u""))
                # Show title only once
                what = u""
            what = title
            for added in (set(new_value) - set(old_value)):
                user = root.get_user(added)
                if user is not None:
                    added = user.get_title()
                changes.append(CHANGES_LINE.gettext(what=what,
                    removed=u"", added=added))
                # Show title only once
                what = u""
        elif key == 'crm_m_status':
            if old_value is None:
                removed = u""
            else:
                removed = MissionStatus.get_value(old_value)
            added = MissionStatus.get_value(new_value)
            changes.append(CHANGES_LINE.gettext(what=title,
                removed=removed, added=added))
        elif key == 'attachment':
            if new_value is not None:
                # Filename
                added = new_value[0]
                changes.append(CHANGES_LINE.gettext(what=title,
                    removed=u"", added=added))
        elif key == 'alert_date' or key == 'crm_m_deadline':
            accept = context.accept_language
            removed = u""
            if old_value:
                removed = format_date(old_value, accept=accept)
            added = u""
            if new_value:
                added = format_date(new_value, accept=accept)
            changes.append(CHANGES_LINE.gettext(what=title,
                removed=removed, added=added))
        elif key == 'alert_time':
            removed = mission_schema['alert_time'].encode(old_value)
            added = mission_schema['alert_time'].encode(new_value)
            changes.append(CHANGES_LINE.gettext(what=title,
                removed=removed, added=added))
        else:
            if old_value is None:
                old_value = u""
            changes.append(CHANGES_LINE.gettext(what=title,
                removed=old_value, added=new_value))
    return changes


def send_notification(resource, context, form, changes, new=False):
    # From
    user = context.user
    user_title = user.get_title()
    user_email = user.get_property('email')
    # To
    to_addrs = form['crm_m_cc']
    to_addrs = set(form['crm_m_cc'])
    # Except sender
    if user.name in to_addrs:
        to_addrs.remove(user.name)
    if not to_addrs:
        return
    # Subject
    crm_title = get_crm(resource).get_title() or u"CRM"
    mission_name = resource.name
    mission_title = resource.get_property('crm_m_title')
    subject = u"[%s #%s] %s" % (crm_title, mission_name, mission_title)
    # Body
    mission_uri = '%s/;view' % context.get_link(resource)
    # Changes
    changes.insert(0, u"-" * 76)
    header = CHANGES_LINE.gettext(what=u"What", removed=u"Removed",
            added=u"Added")
    changes.insert(0, header)
    changes = u"\n".join(changes)
    # New comment
    comment = u""
    if form['comment']:
        n = len(resource.get_property('comment')) - 1
        accept = context.accept_language
        date = format_datetime(datetime.now(), accept=accept)
        comment = [COMMENT_LINE.gettext(n=n, user_title=user_title,
            user_email=user_email, date=date)]
        comment.extend(form['comment'].splitlines())
        comment = u"\n".join(comment)
    body = BODY.gettext(mission_uri=mission_uri,
            mission_name=mission_name, mission_title=mission_title,
            user_title=user_title, user_email=user_email, changes=changes,
            comment=comment)
    # Send
    root = context.root
    for to_addr in to_addrs:
        user = root.get_user(to_addr)
        if not user:
            continue
        to_addr = user.get_property('email')
        root.send_email(to_addr, subject, text=body)



class ButtonAddContact(BrowseButton):
    name = 'add_contact'
    access = 'is_allowed_to_edit'
    title = MSG(u'Add contact')



class ButtonUpdate(Button):
    name = 'update_mission'
    access = 'is_allowed_to_edit'
    title = MSG(u"Update mission")



class Mission_EditForm(AutoForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit mission')
    template = '/ui/crm/mission/edit.xml'
    actions = [ButtonUpdate()]

    def get_query_schema(self):
        return mission_schema.copy()


    def get_schema(self, resource, context):
        # crm_m_title and crm_m_status are mandatory
        return merge_dicts(mission_schema,
                crm_m_title=mission_schema['crm_m_title'](mandatory=True),
                crm_m_status=mission_schema['crm_m_status'](mandatory=True),
                crm_m_cc=mission_schema['crm_m_cc'](resource=resource))


    def get_widgets(self, resource, context):
        return mission_widgets[:]


    def get_value(self, resource, context, name, datatype):
        if name in ('alert_date', 'alert_time'):
            return datatype.default
        elif name == 'comment':
            return context.query.get(name) or u''
        elif name == 'attachment':
            return context.query.get(name) or ''
        value = resource.get_value(name)
        return value if value is not None else datatype.default


    def get_namespace(self, resource, context):
        # Build namespace
        namespace = AutoForm.get_namespace(self, resource, context)
        submit = (context.method == 'POST')

        # Modify widgets namespace to change template
        for index, widget in enumerate(namespace['widgets']):
            name = self.get_widgets(resource, context)[index].name
            # XXX multilingual to monolingual
            widget['widget'] = widget['widgets'][0]
            # Reset comment
            if submit and name == 'comment':
                widget['value'] = ''
                comment_widget = MultilineWidget('comment',
                        title=MSG(u'Comment'), rows=3, datatype=Unicode,
                        value=u'')
                widget['widget'] = comment_widget.render()
            namespace[name] = widget
        return namespace


    def action(self, resource, context, form):
        # First compute differences
        changes = get_changes(resource, context, form)

        # Save changes
        values = get_form_values(form)
        resource._update(values, context)

        # Reindex contacts to update Opp/Proj/NoGo, p_assured and p_probable
        crm = get_crm(resource)
        contacts = resource.get_value('crm_m_contact')
        for contact in contacts:
            contact = crm.get_resource('contacts/%s' % contact)
            context.database.change_resource(contact)

        context.message = MSG_CHANGES_SAVED

        # Send notification to CC
        send_notification(resource, context, form, changes)



class CancelAlert(BaseForm):
    """ Form accessed from Mission_View.
    """
    access = 'is_allowed_to_edit'
    schema = {'id': Integer(mandatory=True)}

    def action(self, resource, context, form):
        # Remove alert_datetime
        resource.set_property('alert_datetime', None)
        context.database.change_resource(resource)

        return context.come_back(MSG_CHANGES_SAVED, './')



class Mission_AddForm(Mission_EditForm):

    title = MSG(u'New mission')

    def get_query_schema(self):
        # Add mandatory crm_m_contact to query schema
        return merge_dicts(mission_schema,
                           crm_m_contact=ContactName(mandatory=True))


    def get_value(self, resource, context, name, datatype):
        return context.query.get(name) or datatype.default


    def action(self, resource, context, form):
        # Get crm_m_contact from the query
        form['crm_m_contact'] = context.query['crm_m_contact']
        values = get_form_values(form)
        name = resource.add_mission(values)
        mission = resource.get_resource(name)

        # Reindex contacts to update Opp/Proj/NoGo, p_assured and p_probable
        crm = get_crm(resource)
        contact = values.get('crm_m_contact')
        contact = crm.get_resource('contacts/%s' % contact)
        context.database.change_resource(contact)

        # First compute differences
        changes = get_changes(mission, context, form, new=True)
        # Send notification to CC
        send_notification(mission, context, form, changes, new=True)

        goto = './%s' % name
        return context.come_back(MSG_NEW_RESOURCE, goto=goto)



class Mission_ViewContacts(CRM_SearchContacts):

    search_template = None
    batch_msg1 = MSG(' ')
    batch_msg2 = MSG(' ')

    def get_table_columns(self, resource, context):
        columns = []
        for column in self.table_columns:
            name, title, sort = column
            if name in ('icon', 'crm_p_lastname', 'crm_p_firstname',
                    'crm_p_company', 'crm_p_position', 'crm_p_phone',
                    'crm_p_mobile'):
                columns.append(column)
        return columns


    def get_items(self, resource, context, *args):
        args = list(args)
        contacts = resource.get_value('crm_m_contact')
        if len(contacts) == 1:
            args.append(PhraseQuery('name', contacts[0]))
        elif len(contacts) > 1:
            args.append(OrQuery(*[PhraseQuery('name', x) for x in contacts]))
        return CRM_SearchContacts.get_items(self, resource, context, *args)


    def get_namespace(self, resource, context):
        namespace = CRM_SearchContacts.get_namespace(self, resource, context)
        namespace['crm-infos'] = False
        namespace['export-csv'] = False
        return namespace



class Mission_ViewContact(Mission_ViewContacts):

    def get_items(self, resource, context, *args):
        args = list(args)
        contact = context.query['crm_m_contact']
        args.append(PhraseQuery('name', contact))
        return CRM_SearchContacts.get_items(self, resource, context, *args)



class Mission_EditContacts(Mission_ViewContacts):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit contacts')

    schema = {'ids': String(multiple=True, mandatory=True)}

    table_actions = [
            RemoveButton(name='remove', title=MSG(u'Remove contact')) ]

    def get_table_columns(self, resource, context):
        columns = Mission_ViewContacts.get_table_columns(self, resource,
                                                          context)
        columns = list(columns) # do not alter parent columns
        columns.insert(0, ('checkbox', None))
        return columns


    def action_remove(self, resource, context, form):
        contacts = resource.get_value('crm_m_contact')

        for contact_id in form.get('ids', []):
            try:
                contacts.remove(contact_id)
            except:
                pass

        if len(contacts) == 0:
            msg = ERROR(u'At least one contact is required')
        else:
            # Apply change
            resource._update({'crm_m_contact': contacts})
            msg = MSG_CHANGES_SAVED

        context.message = msg



class Mission_AddContacts(CRM_SearchContacts):

    access = 'is_allowed_to_edit'
    title = MSG(u'Add contacts')

    schema = {'ids': String(multiple=True, mandatory=True)}

    table_actions = [ButtonAddContact]

    def get_table_columns(self, resource, context):
        columns = CRM_SearchContacts.get_table_columns(self, resource, context)
        columns = list(columns) # do not alter parent columns
        columns.insert(0, ('checkbox', None))
        return columns


    def get_namespace(self, resource, context):
        namespace = CRM_SearchContacts.get_namespace(self, resource, context)
        namespace['crm-infos'] = False
        namespace['export-csv'] = False
        return namespace


    def action_add_contact(self, resource, context, form):
        contacts = resource.get_value('crm_m_contact')

        for contact_id in form.get('ids', []):
            contacts.append(contact_id)

        contacts = list(set(contacts))
        # Apply change
        resource._update({'crm_m_contact': contacts})
        msg = MSG_CHANGES_SAVED



class Mission_View(CompositeForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'View mission')
    template = '/ui/crm/mission/view.xml'
    styles = ['/ui/crm/style.css', '/ui/tracker/style.css']
    scripts = ['/ui/crm/jquery.maskedinput-1.2.2.min.js']

    subviews = [Mission_EditForm(), Mission_ViewContacts(), Comments_View()]

    def get_namespace(self, resource, context):
        title = resource.get_value('crm_m_title')
        edit = resource.edit_form.GET(resource, context)
        view_comments = resource.view_comments.GET(resource, context)
        view_contacts = resource.view_contacts.GET(resource, context)
        namespace = {
            'title': title,
            'edit': edit,
            'view_comments': view_comments,
            'view_contacts': view_contacts }
        return namespace



class Mission_Add(Mission_View):

    title = MSG(u'New mission')
    subviews = [Mission_ViewContact(), Mission_AddForm()]


    def on_query_error(self, resource, context):
        msg = u'Please select a valid contact before creating a mission.'
        return context.come_back(ERROR(msg), goto='..')


    def get_namespace(self, resource, context):
        add = resource.add_form.GET(resource, context)
        view_contact = resource.view_contact.GET(resource, context)
        namespace = {
            'title': MSG(u'New mission'),
            'edit': add,
            'view_comments': None,
            'view_contacts': view_contact}
        return namespace



class Mission_EditAlerts(CRM_Alerts):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit alerts')
    search_template = None

    # Table
    table_columns = [
        ('checkbox', None),
        ('icon', None, False),
        ('alert_date', MSG(u'Date'), False),
        ('alert_time', MSG(u'Time'), False),
        ('comment', MSG(u'Comment'), False),
        ('crm_m_nextaction', MSG(u'Next action'), False)]


    def get_items(self, resource, context, *args):
        args = list(args)
        abspath = resource.get_canonical_path()
        args.append(PhraseQuery('abspath', str(abspath)))
        return CRM_Alerts.get_items(self, resource, context, *args)


    def get_item_value(self, resource, context, item, column):
        alert_datetime, m_nextaction, mission = item
        if column == 'comment':
            comments = mission.get_property('comment')
            if not comments:
                return None
            return comments[-1]
        return CRM_Alerts.get_item_value(self, resource, context, item, column)
