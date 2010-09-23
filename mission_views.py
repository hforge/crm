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
from itools.database import OrQuery, PhraseQuery
from itools.datatypes import Date, Decimal, Integer
from itools.datatypes import String, Unicode
from itools.gettext import MSG
from itools.ical import Time
from itools.web import BaseForm, ERROR

# Import from ikaaro
from ikaaro.buttons import RemoveButton
from ikaaro.autoform import AutoForm, DateWidget
from ikaaro.autoform import MultilineWidget
from ikaaro.autoform import FileWidget, RadioWidget, TextWidget
from ikaaro.datatypes import FileDataType
from ikaaro.messages import MSG_NEW_RESOURCE, MSG_CHANGES_SAVED
from ikaaro.views import CompositeForm

# Import from crm
from crm_views import ButtonUpdate, ButtonAddContact, get_form_values
from crm_views import CRM_SearchContacts, CRM_Alerts, Comments_View
from datatypes import MissionStatus, ContactName
from utils import TimeWidget, get_crm


mission_schema = {
    # First mission
    'crm_m_title': Unicode,
    'crm_m_description': Unicode,
    'crm_m_amount': Decimal,
    'crm_m_probability': Integer,
    'crm_m_deadline': Date,
    'crm_m_status': MissionStatus,
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
    MultilineWidget('comment', title=MSG(u'New comment'), default='',
                    rows=3),
    FileWidget('attachment', title=MSG(u'Attachment'), size=35, default=''),
    DateWidget('alert_date', title=MSG(u'Alert on'), size=8),
    TimeWidget('alert_time', title=MSG(u'at')),
    TextWidget('crm_m_nextaction', title=MSG(u'Next action')) ]


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
                mission_schema['crm_m_title'](mandatory=True),
                mission_schema['crm_m_status'](mandatory=True))


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
        values = get_form_values(form)
        resource._update(values, context)

        # Reindex contacts to update Opp/Proj/NoGo, p_assured and p_probable
        crm = get_crm(resource)
        contacts = resource.get_value('crm_m_contact')
        for contact in contacts:
            contact = crm.get_resource('contacts/%s' % contact)
            context.database.change_resource(contact)
        context.message = MSG_CHANGES_SAVED



class CancelAlert(BaseForm):
    """ Form accessed from Mission_View.
    """
    access = 'is_allowed_to_edit'
    schema = {'id': Integer(mandatory=True)}

    def action(self, resource, context, form):
        comment_id = form['id']
        # Remove alert_datetime
        crm = get_crm(resource)
        mission = resource
        comments = mission.get_property('comment')
        comments[comment_id].set_parameter(alert_datetime=None)
        # XXX set_property?
        context.database.change_resource(resource)

        return context.come_back(MSG_CHANGES_SAVED, './')



class Mission_AddForm(Mission_EditForm):

    title = MSG(u'New mission')

    def get_query_schema(self):
        # Add mandatory crm_m_contact to query schema
        return merge_dicts(mission_schema,
                           crm_m_contact=ContactName(mandatory=True))


    def get_schema(self, resource, context):
        # crm_m_title and crm_m_status are mandatory
        return merge_dicts(mission_schema,
                mission_schema['crm_m_title'](mandatory=True),
                mission_schema['crm_m_status'](mandatory=True))


    def get_value(self, resource, context, name, datatype):
        return context.query.get(name) or datatype.default


    def action(self, resource, context, form):
        # Get crm_m_contact from the query
        form['crm_m_contact'] = context.query['crm_m_contact']
        values = get_form_values(form)
        name = resource.add_mission(values)

        # Reindex contacts to update Opp/Proj/NoGo, p_assured and p_probable
        crm = get_crm(resource)
        contact = values.get('crm_m_contact')
        contact = crm.get_resource('contacts/%s' % contact)
        context.database.change_resource(contact)

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
                    'crm_p_company', 'crm_p_position', 'mtime'):
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
        alert_datetime, m_nextaction, mission, comment_id = item
        if column == 'comment':
            comments = mission.get_property('comment')
            return comments[comment_id]
        return CRM_Alerts.get_item_value(self, resource, context, item, column)
