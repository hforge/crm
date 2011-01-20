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

# Import from itools
from itools.core import merge_dicts, freeze, is_thingy
from itools.csv import Property
from itools.database import OrQuery, PhraseQuery
from itools.datatypes import Date, Decimal, Integer
from itools.datatypes import String, Unicode, Boolean
from itools.gettext import MSG
from itools.handlers import checkid
from itools.fs import FileName
from itools.i18n import format_datetime, format_date
from itools.ical import Time
from itools.web import BaseForm, ERROR, get_context

# Import from ikaaro
from ikaaro.buttons import Button, BrowseButton, RemoveButton
from ikaaro.autoform import DateWidget, MultilineWidget, CheckboxWidget
from ikaaro.autoform import FileWidget, RadioWidget, TextWidget, SelectWidget
from ikaaro.cc import UsersList
from ikaaro.datatypes import FileDataType, Multilingual
from ikaaro.messages import MSG_NEW_RESOURCE, MSG_CHANGES_SAVED
from ikaaro.registry import get_resource_class
from ikaaro.resource_views import DBResource_Edit
from ikaaro.utils import generate_name
from ikaaro.views import CompositeForm

# Import from crm
from base_views import monolingual_widgets, reset_comment
from base_views import Comments_View, CRMFolder_AddForm
from crm_views import CRM_SearchContacts, CRM_Alerts
from datatypes import MissionStatus, ContactName
from menus import MissionsMenu, ContactsByMissionMenu
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


mission_schema = freeze(merge_dicts(
    DBResource_Edit.schema,
    description=Multilingual(hidden_by_default=False),
    comment=Unicode,
    crm_m_nextaction=Unicode,
    attachment=FileDataType,
    alert_date=Date,
    alert_time=Time,
    remove_previous_alerts=Boolean,
    # XXX must add resource in "_get_schema"
    crm_m_assigned=UsersList,
    crm_m_cc=UsersList(multiple=True),
    crm_m_status=MissionStatus,
    crm_m_deadline=Date,
    crm_m_amount=Decimal,
    crm_m_probability=Integer))


mission_widgets = freeze(
    DBResource_Edit.widgets[:3] + [
        MultilineWidget('comment', title=MSG(u'New comment'), default='',
                        rows=3),
        TextWidget('crm_m_nextaction', title=MSG(u'Next action')),
        FileWidget('attachment', title=MSG(u'Attachment'), size=35,
            default=''),
        DateWidget('alert_date', title=MSG(u'Alert on'), size=8),
        TimeWidget('alert_time', title=MSG(u'at')),
        CheckboxWidget('remove_previous_alerts', default=True,
            title=MSG(u"Remove previous alerts")),
        SelectWidget('crm_m_assigned', title=MSG(u"Assigned To"),
            has_empty_option=True),
        SelectWidget('crm_m_cc', title=MSG(u"CC"), multiple=True, size=5,
            has_empty_option=False),
        RadioWidget('crm_m_status', title=MSG(u'Status'), is_inline=True,
                    has_empty_option=False),
        DateWidget('crm_m_deadline', title=MSG(u'Deadline'), default='',
            size=8),
        TextWidget('crm_m_amount', title=MSG(u'Amount'), default='', size=8),
        TextWidget('crm_m_probability', title=MSG(u'Probability'), default='',
            size=2)])


def get_changes(resource, context, form, new=False):
    root = context.root
    changes = []
    last_comment = resource.get_last_comment()
    for key, datatype in mission_schema.iteritems():
        # Comment is treated separately
        if key in ('comment', 'remove_previous_alerts', 'subject',
                'timestamp'):
            continue
        new_value = form[key]
        if type(new_value) is dict:
            language = resource.get_edit_languages(context)[0]
            new_value = new_value[language]
        if new:
            old_value = datatype.get_default()
        else:
            if key in ('alert_date', 'alert_time', 'attachment',
                    'crm_m_nextaction'):
                if last_comment is None:
                    old_value = None
                else:
                    old_value = last_comment.get_parameter(key)
                    if key == 'alert_date':
                        if old_value is not None:
                            old_value = old_value.date()
                    elif key == 'alert_time':
                        if old_value is not None:
                            old_value = old_value.time()
            else:
                old_value = resource.get_property(key)
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
        if key == 'crm_m_assigned':
            if old_value:
                removed = old_value
                user = root.get_user(old_value)
                if user is not None:
                    removed = user.get_title()
            else:
                removed = u""
            if new_value:
                added = new_value
                user = root.get_user(new_value)
                if user is not None:
                    added = user.get_title()
            else:
                added = u""
            changes.append(CHANGES_LINE.gettext(what=title, removed=removed,
                added=added))
        elif key == 'crm_m_cc':
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
            removed = datatype.encode(old_value)
            added = datatype.encode(new_value)
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
    to_addrs = set(form['crm_m_cc'])
    if form['crm_m_assigned']:
        to_addrs.add(form['crm_m_assigned'])
    # Except sender
    if user.name in to_addrs:
        to_addrs.remove(user.name)
    if not to_addrs:
        return
    # Subject
    crm_title = get_crm(resource).get_title() or u"CRM"
    mission_name = resource.name
    mission_title = resource.get_property('title')
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



class ButtonAddMission(Button):
    name = 'add_mission'
    access = 'is_allowed_to_edit'
    title = MSG(u'Add mission')



class ButtonUpdate(Button):
    name = 'update_mission'
    access = 'is_allowed_to_edit'
    title = MSG(u"Update mission")



class Mission_EditForm(DBResource_Edit):
    title = MSG(u'Edit mission')
    template = '/ui/crm/mission/edit.xml'
    query_schema = mission_schema
    widgets = mission_widgets

    actions = freeze([
        ButtonUpdate()])


    def _get_schema(self, resource, context):
        return freeze(merge_dicts(
            mission_schema,
            # title and crm_m_status are mandatory
            title=mission_schema['title'](mandatory=True),
            crm_m_status=mission_schema['crm_m_status'](mandatory=True),
            # resource needed
            crm_m_assigned=mission_schema['crm_m_assigned'](
                resource=resource),
            crm_m_cc=mission_schema['crm_m_cc'](resource=resource)))


    def get_value(self, resource, context, name, datatype):
        if name in ('alert_date', 'alert_time'):
            return datatype.get_default()
        elif name in ('comment', 'attachment'):
            return context.query.get(name) or datatype.get_default()
        elif name == 'crm_m_nextaction':
            return resource.find_next_action()
        elif name == 'remove_previous_alerts':
            return True
        proxy = super(Mission_EditForm, self)
        return proxy.get_value(resource, context, name, datatype)


    def is_edit(self, context):
        return context.method == 'POST'


    def get_namespace(self, resource, context):
        # Build namespace
        proxy = super(Mission_EditForm, self)
        namespace = proxy.get_namespace(resource, context)
        monolingual_widgets(namespace)
        reset_comment(namespace, is_edit=self.is_edit(context))
        return namespace


    def action(self, resource, context, form):
        # First compute differences
        changes = get_changes(resource, context, form)

        # Save changes
        super(Mission_EditForm, self).action(resource, context, form)
        if is_thingy(context.message, ERROR):
            return

        # Reindex contacts to update Opp/Proj/NoGo, p_assured and p_probable
        crm = get_crm(resource)
        contacts = crm.get_resource('contacts')
        for contact_id in resource.get_property('crm_m_contact'):
            contact = contacts.get_resource(contact_id)
            context.database.change_resource(contact)

        # Send notification to CC
        send_notification(resource, context, form, changes)


    def set_value(self, resource, context, name, form):
        if name in ('attachment', 'crm_m_nextaction', 'alert_date',
                'alert_time', 'remove_previous_alerts'):
            return False
        elif name == 'comment':
            # Attachment
            attachment = form['attachment']
            if attachment is not None:
                filename, mimetype, body = attachment
                # Find a non used name
                attachment = checkid(filename)
                attachment, extension, language = FileName.decode(attachment)
                attachment = generate_name(attachment, resource.get_names())
                # Add attachment
                cls = get_resource_class(mimetype)
                resource.make_resource(attachment, cls, body=body,
                    filename=filename, extension=extension,
                    format=mimetype)
            # Next action
            m_nextaction = form['crm_m_nextaction'] or None
            # Alert
            alert_date = form['alert_date']
            if alert_date:
                alert_time = form['alert_time'] or time(9, 0)
                alert_datetime = datetime.combine(alert_date, alert_time)
            else:
                alert_datetime = None
            # Value
            value = form[name]
            if not value:
                if attachment or m_nextaction or alert_datetime:
                    value = u"_"
                else:
                    return False
            # Reset alerts?
            if form['remove_previous_alerts'] and form['alert_date']:
                resource.remove_alerts()
            user = context.user
            author = user.name if user else None
            value = Property(value, date=context.timestamp, author=author,
                    attachment=attachment, crm_m_nextaction=m_nextaction,
                    alert_datetime=alert_datetime)
            resource.metadata.set_property(name, value)
            return False
        proxy = super(Mission_EditForm, self)
        return proxy.set_value(resource, context, name, form)



class CancelAlert(BaseForm):
    """ Form accessed from Mission_View.
    """
    access = 'is_allowed_to_edit'
    schema = freeze({
        'id': Integer(mandatory=True)})


    def action(self, resource, context, form):
        comment_id = form['id']
        # Remove alert_datetime
        mission = resource
        comments = mission.metadata.get_property('comment')
        comments[comment_id].set_parameter('alert_datetime', None)
        resource.set_property('comment', comments)

        return context.come_back(MSG_CHANGES_SAVED, './')



class Mission_AddForm(CRMFolder_AddForm, Mission_EditForm):
    title = MSG(u'New mission')
    query_schema = freeze(merge_dicts(
        mission_schema,
        # Add mandatory crm_m_contact to query schema
        crm_m_contact=ContactName(mandatory=True, multiple=True)))

    actions = freeze([
        ButtonAddMission()])


    def is_edit(self, context):
        return False


    def action(self, resource, context, form):
        m_values = {'crm_m_contact': context.query['crm_m_contact']}
        mission = resource.add_mission(**m_values)

        Mission_EditForm.action(self, mission, context, form)
        if is_thingy(context.message, ERROR):
            return

        goto = context.get_link(mission)
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
                    'crm_p_company', 'crm_p_email', 'crm_p_phone',
                    'crm_p_mobile', 'crm_p_position'):
                columns.append(column)
        return columns


    def get_items(self, resource, context, *args):
        args = list(args)
        m_contact = resource.get_property('crm_m_contact')
        if len(m_contact) == 1:
            args.append(PhraseQuery('name', m_contact[0]))
        elif len(m_contact) > 1:
            query = [PhraseQuery('name', c) for c in m_contact]
            args.append(OrQuery(*query))
        return CRM_SearchContacts.get_items(self, resource, context, *args)


    def get_namespace(self, resource, context):
        namespace = CRM_SearchContacts.get_namespace(self, resource, context)
        namespace['crm-infos'] = False
        namespace['export-csv'] = False
        return namespace



class Mission_ViewContact(Mission_ViewContacts):

    def get_items(self, resource, context, *args):
        args = list(args)
        contact = context.query['crm_m_contact'][0]
        args.append(PhraseQuery('name', contact))
        return CRM_SearchContacts.get_items(self, resource, context, *args)



class Mission_EditContacts(Mission_ViewContacts):
    access = 'is_allowed_to_edit'
    title = MSG(u'Edit contacts')

    schema = freeze({
        'ids': String(multiple=True, mandatory=True)})

    table_actions = freeze([
        RemoveButton(name='remove', title=MSG(u'Remove contact')) ])


    def get_table_columns(self, resource, context):
        columns = Mission_ViewContacts.get_table_columns(self, resource,
                context)
        columns = list(columns) # do not alter parent columns
        columns.insert(0, ('checkbox', None))
        return columns


    def action_remove(self, resource, context, form):
        m_contact = resource.get_property('crm_m_contact')

        for contact_id in form.get('ids', []):
            if contact_id in m_contact:
                m_contact.remove(contact_id)

        if len(m_contact) == 0:
            context.message = ERROR(u'At least one contact is required')
            return

        # Apply change
        resource.set_property('crm_m_contact', m_contact)
        context.message = MSG_CHANGES_SAVED



class Mission_AddContacts(CRM_SearchContacts):
    access = 'is_allowed_to_edit'
    title = MSG(u'Add contacts')

    schema = freeze({
        'ids': String(multiple=True, mandatory=True)})

    table_actions = freeze([
        ButtonAddContact])


    def get_query_schema(self):
        # Filter by same company
        search_term = u""
        resource = get_context().resource
        m_contact = resource.get_property('crm_m_contact')
        if m_contact:
            crm = get_crm(resource)
            contact = crm.get_resource('contacts/' + m_contact[0])
            p_company = contact.get_property('crm_p_company')
            company = crm.get_resource('companies/' + p_company)
            search_term = company.get_property('title')
        return freeze(merge_dicts(
            CRM_SearchContacts.get_query_schema(self),
            search_term=Unicode(default=search_term)))


    def get_table_columns(self, resource, context):
        columns = CRM_SearchContacts.get_table_columns(self, resource,
                context)
        columns = list(columns) # do not alter parent columns
        columns.insert(0, ('checkbox', None))
        return columns


    def get_namespace(self, resource, context):
        namespace = CRM_SearchContacts.get_namespace(self, resource, context)
        namespace['crm-infos'] = False
        namespace['export-csv'] = False
        return namespace


    def action_add_contact(self, resource, context, form):
        # Save changes
        m_contact = resource.get_property('crm_m_contact')
        m_contact = list(set(m_contact + form['ids']))
        resource.set_property('crm_m_contact', m_contact)

        # Reindex contacts so they know about the mission
        crm = get_crm(resource)
        contacts = crm.get_resource('contacts')
        for contact_id in form['ids']:
            contact = contacts.get_resource(contact_id)
            context.database.change_resource(contact)

        context.message = MSG_CHANGES_SAVED



class Mission_View(CompositeForm):
    access = 'is_allowed_to_edit'
    title = MSG(u'View mission')
    template = '/ui/crm/mission/view.xml'
    styles = [
            '/ui/crm/style.css',
            '/ui/tracker/style.css']
    scripts = [
            '/ui/crm/javascript.js',
            '/ui/crm/jquery.maskedinput-1.2.2.min.js']
    context_menus = [
            MissionsMenu(contact_menu=ContactsByMissionMenu()),
            ContactsByMissionMenu()]
    subviews = [
            Mission_EditForm(),
            Mission_ViewContacts(),
            Comments_View()]


    def get_namespace(self, resource, context):
        title = resource.get_property('title')
        edit = resource.edit_form.GET(resource, context)
        view_comments = resource.view_comments.GET(resource, context)
        view_contacts = resource.view_contacts.GET(resource, context)
        return {
            'title': title,
            'edit': edit,
            'view_comments': view_comments,
            'view_contacts': view_contacts}



class Mission_Add(Mission_View):
    title = MSG(u'New mission')
    context_menus = []
    subviews = [
            Mission_ViewContact(),
            Mission_AddForm()]


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
    table_columns = freeze([
        ('checkbox', None),
        ('icon', None, False),
        ('alert_date', MSG(u'Date'), False),
        ('alert_time', MSG(u'Time'), False),
        ('comment', MSG(u'Comment'), False),
        ('crm_m_nextaction', MSG(u'Next action'), False)])


    def get_items(self, resource, context, *args):
        args = list(args)
        abspath = resource.get_canonical_path()
        args.append(PhraseQuery('abspath', str(abspath)))
        return CRM_Alerts.get_items(self, resource, context, *args)


    def get_item_value(self, resource, context, item, column):
        alert_datetime, m_nextaction, mission, comment_id = item
        if column == 'comment':
            comments = mission.get_property('comment')
            return comments[comment_id]
        return CRM_Alerts.get_item_value(self, resource, context, item, column)
