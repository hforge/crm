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
from datetime import date

# Import from itools
from itools.core import merge_dicts, freeze
from itools.database import AndQuery, OrQuery, PhraseQuery
from itools.datatypes import Email, Integer
from itools.datatypes import String, Unicode
from itools.gettext import MSG
from itools.i18n import format_datetime, format_number
from itools.web import FormError

# Import from ikaaro
from ikaaro.autoform import MultilineWidget, RadioWidget, TextWidget
from ikaaro.autoform import timestamp_widget
from ikaaro.messages import MSG_NEW_RESOURCE
from ikaaro.resource_views import DBResource_Edit
from ikaaro.views import CompositeForm, SearchForm

# Import from crm
from base_views import monolingual_schema, m_status_icons
from base_views import Comments_View, CRMFolder_AddForm
from datatypes import CompanyName, MissionStatus, ContactStatus
from menus import MissionsMenu, ContactsByContactMenu, CompaniesMenu
from mission_views import mission_schema, mission_widgets
from mission_views import get_changes, send_notification
from utils import get_crm, get_crm_path_query
from widgets import EmailWidget, MultipleCheckboxWidget
from widgets import SelectCompanyWidget


contact_schema = freeze(merge_dicts(
    monolingual_schema,
    crm_p_company=CompanyName,
    crm_p_lastname=Unicode,
    crm_p_firstname=Unicode,
    crm_p_phone=Unicode,
    crm_p_mobile=Unicode,
    crm_p_email=Email,
    crm_p_description=Unicode,
    crm_p_position=Unicode,
    crm_p_status=ContactStatus,
    comment=Unicode))


contact_widgets = freeze([
    timestamp_widget,
    SelectCompanyWidget('crm_p_company', title=MSG(u'Company')),
    TextWidget('crm_p_lastname', title=MSG(u'Last name'), default='',
        size=30),
    TextWidget('crm_p_firstname', title=MSG(u'First name'), default='',
        size=30),
    TextWidget('crm_p_phone', title=MSG(u'Phone'), default='', size=15),
    TextWidget('crm_p_mobile', title=MSG(u'Mobile'), default='', size=15),
    EmailWidget('crm_p_email', title=MSG(u'Email'), default='', size=30),
    TextWidget('crm_p_position', title=MSG(u'Position'), default='', size=15),
    # TODO reuse description
    MultilineWidget('crm_p_description', title=MSG(u'Observations'),
        default=u'', rows=4),
    RadioWidget('crm_p_status', title=MSG(u'Status'), has_empty_option=False,
        is_inline=True),
    MultilineWidget('comment', title=MSG(u'New comment'), rows=3)])


class Contact_EditForm(DBResource_Edit):
    access = 'is_allowed_to_edit'
    title = MSG(u'Edit contact')
    submit_value = MSG(u'Update contact')
    styles = ['/ui/crm/style.css']


    def get_query_schema(self):
        return freeze(contact_schema)


    def _get_schema(self, resource, context):
        # crm_p_lastname and crm_p_status are mandatory
        return merge_dicts(contact_schema,
                crm_p_lastname=contact_schema['crm_p_lastname'](
                    mandatory=True),
                crm_p_status=contact_schema['crm_p_status'](mandatory=True))


    def _get_widgets(self, resource, context):
        return freeze(contact_widgets)


    def get_value(self, resource, context, name, datatype):
        if name == 'comment':
            return u''
        return DBResource_Edit.get_value(self, resource, context, name,
                datatype)


    def is_edit(self, context):
        return context.method == 'POST'


    def get_namespace(self, resource, context):
        # Build namespace
        namespace = DBResource_Edit.get_namespace(self, resource, context)

        # Modify widgets namespace to change template
        for widget in namespace['widgets']:
            # Reset comment
            if widget['name'] == 'comment' and self.is_edit(context):
                widget['value'] = u''
                comment_widget = MultilineWidget('comment',
                        title=MSG(u'Comment'), rows=3, datatype=Unicode,
                        value=u'')
                widget['widget'] = comment_widget.render()

        return namespace



class Contact_AddForm(CRMFolder_AddForm, Contact_EditForm):
    """ To add a new contact into the crm.
    """
    title = MSG(u'New contact')
    template = '/ui/crm/contact/new.xml'
    styles = ['/ui/crm/style.css']


    def get_query_schema(self):
        return freeze(merge_dicts(contact_schema, mission_schema))


    def _get_schema(self, resource, context):
        schema = merge_dicts(
                contact_schema,
                crm_p_lastname=contact_schema['crm_p_lastname'](
                    mandatory=True),
                crm_p_status=contact_schema['crm_p_status'](
                    mandatory=True))
        for name, datatype in mission_schema.iteritems():
            if name in ('title', 'description'):
                # Prefix double title and description
                schema['mission_%s' % name] = datatype
            elif name in ('crm_m_assigned', 'crm_m_cc'):
                schema[name] = datatype(resource=resource)
            else:
                schema[name] = datatype
        return freeze(schema)


    def _get_widgets(self, resource, context):
        widgets = contact_widgets[:]
        for widget in mission_widgets:
            if widget.name in ('timestamp', 'comment', 'crm_m_nextaction',
                    'attachment', 'alert_date', 'alert_time'):
                # Skip double timestamp and comment
                continue
            elif widget.name in ('title', 'description'):
                # Prefix double title and description
                widget.name = 'mission_%s' % widget.name
            widgets.append(widget)
        return freeze(widgets)


    def is_edit(self, context):
        return False


    def get_value(self, resource, context, name, datatype):
        if name == 'crm_m_deadline':
            value = context.query['crm_m_deadline']
            if value is None:
                year = date.today().year
                value = date(year, 12, 31)
            return value
        return CRMFolder_AddForm.get_value(self, resource, context, name,
                datatype)


    def _get_form(self, resource, context):
        form = DBResource_Edit._get_form(self, resource, context)

        # If title is defined, status is required
        language, title = form['mission_title'].popitem()
        m_status = form['crm_m_status']
        if title.strip() and m_status is None:
            raise FormError(invalid=['crm_m_status'])

        return form


    def get_namespace(self, resource, context):
        namespace = DBResource_Edit.get_namespace(self, resource, context)

        # Modify widgets namespace to change template
        widgets = {}
        for widget in namespace['widgets']:
            name = widget['name']
            widget['widget'] = widget['widgets'].pop(0)
            widgets[name] = widget
        namespace['widgets'] = widgets

        return namespace


    def action(self, resource, context, form):
        crm = get_crm(resource)
        contacts = crm.get_resource('contacts')
        missions = crm.get_resource('missions')
        # Split values contact/mission
        p_values = {}
        m_values = {}
        for key, value in form.iteritems():
            if key.startswith('crm_p_'):
                p_values[key] = value
            elif key.startswith('crm_m_'):
                m_values[key] = value
            elif key.startswith('mission_'):
                m_values[key[8:]] = value
        from pprint import pprint
        print "p_values"
        pprint(p_values)
        print "m_values"
        pprint(m_values)
        # Add contact
        contact = contacts.add_contact(**p_values)
        # Add mission if title is defined
        if m_values['title']:
            m_values['crm_m_contact'] = contact.name
            mission = missions.add_mission(**m_values)
            changes = get_changes(mission, context, form, new=True)
            send_notification(mission, context, form, changes, new=True)
            goto = context.get_link(mission)
        else:
            goto = context.get_link(contact)

        return context.come_back(MSG_NEW_RESOURCE, goto=goto)



class Contact_SearchMissions(SearchForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Missions')
    search_template = '/ui/crm/contact/search.xml'

    search_schema = freeze({
        'search_text': Unicode,
        'search_type': String,
        'crm_m_status': MissionStatus(multiple=True)})
    search_fields =  freeze([
        ('title', MSG(u'Title')),
        ('text', MSG(u'Text')) ])

    table_columns = freeze([
        ('icon', None, False),
        ('title', MSG(u'Title'), True),
        ('crm_m_nextaction', MSG(u'Next action'), True),
        ('crm_m_amount', MSG(u'Amount'), False),
        ('crm_m_probability', MSG(u'Prob.'), False),
        ('crm_m_deadline', MSG(u'Deadline'), False),
        ('mtime', MSG(u'Last Modified'), True)])

    batch_msg1 = MSG(u'1 mission.')
    batch_msg2 = MSG(u'{n} missions.')


    def get_query_schema(self):
        return freeze(merge_dicts(
            SearchForm.get_query_schema(self),
            sort_by=String(default='mtime')))


    def get_items(self, resource, context, *args):
        # Get the parameters from the query
        query = context.query
        search_text = query['search_text'].strip()
        field = query['search_type']
        m_status = query['crm_m_status']

        # Build the query
        args = list(args)
        args.append(PhraseQuery('format', 'mission'))
        args.append(PhraseQuery('crm_m_contact', resource.name))
        missions = resource.parent.parent.get_resource('missions')
        abspath = str(missions.get_canonical_path())
        args.append(PhraseQuery('parent_path', abspath))
        if search_text:
            args.append(PhraseQuery(field, search_text))
        # Insert status filter
        if m_status:
            status_query = []
            for s in m_status:
                status_query.append(PhraseQuery('crm_m_status', s))
            args.append(OrQuery(*status_query))
        if len(args) == 1:
            query = args[0]
        else:
            query = AndQuery(*args)

        # Ok
        crm = get_crm(resource)
        base_path_query = get_crm_path_query(crm)
        return context.root.search(AndQuery(query, base_path_query))


    def get_item_value(self, resource, context, item, column):
        item_brain, item_resource = item
        if column == 'checkbox':
            # checkbox
            return item_brain.name, False
        get_property = item_resource.get_property
        if column == 'icon':
            # Status
            value = get_property('crm_m_status')
            return m_status_icons[value]
        # FIXME
        elif column == 'title':
            # Title
            return get_property(column), context.get_link(item_resource)
        elif column == 'status':
            # Status
            return MissionStatus.get_value(get_property('crm_m_status'))
        elif column == 'mtime':
            # Last Modified
            accept = context.accept_language
            return format_datetime(item_brain.mtime, accept=accept)
        elif column == 'crm_m_amount':
            value = get_property(column)
            if value:
                accept = context.accept_language
                value = format_number(value, curr=u' €', accept=accept)
            return value
        elif column in ('crm_m_probability', 'crm_m_deadline'):
            return get_property(column)
        elif column == 'crm_m_nextaction':
            return item_resource.find_next_action()


    def sort_and_batch(self, resource, context, results):
        start = context.query['batch_start']
        size = context.query['batch_size']
        sort_by = context.query['sort_by']
        reverse = context.query['reverse']
        items = results.get_documents(sort_by=sort_by, reverse=reverse,
                                      start=start, size=size)
        return [(x, resource.get_resource(x.abspath)) for x in items]


    #######################################################################
    # The Search Form
    def get_search_namespace(self, resource, context):
        search_namespace = SearchForm.get_search_namespace(self, resource,
                                                           context)
        # Add status
        default_status = ['crm_p_opportunity', 'crm_p_project']
        m_status = context.query['crm_m_status']
        if not m_status:
            m_status = default_status
        widget = MultipleCheckboxWidget('crm_m_status', title=MSG(u'Status'),
                datatype=MissionStatus, value=m_status)
        search_namespace['crm_m_status'] = widget.render()

        return search_namespace



class Contact_ViewMissions(Contact_SearchMissions):

    search_template = None
    search_schema = freeze({})
    search_fields = freeze([])


    def get_search_namespace(self, resource, context):
        return {}


    def get_query_schema(self):
        return freeze(merge_dicts(
            Contact_SearchMissions.get_query_schema(self),
            batch_size=Integer(default=10)))


    def get_items(self, resource, context, *args):
        # Build the query
        args = list(args)
        args.append(PhraseQuery('crm_m_contact', resource.name))
        if len(args) == 1:
            query = args[0]
        else:
            query = AndQuery(*args)
        # Ok
        crm = get_crm(resource)
        base_path_query = get_crm_path_query(crm)
        return context.root.search(AndQuery(query, base_path_query))



class Contact_View(CompositeForm):
    access = 'is_allowed_to_edit'
    title = MSG(u'View contact')
    template = '/ui/crm/contact/view.xml'
    styles = ['/ui/crm/style.css']
    context_menus = [
            MissionsMenu(contact_menu=ContactsByContactMenu()),
            ContactsByContactMenu(),
            CompaniesMenu()]

    subviews = [
            Contact_EditForm(),
            Contact_ViewMissions(),
            Comments_View()]


    def get_namespace(self, resource, context):
        title = resource.get_title()
        edit = resource.edit_form.GET(resource, context)
        view_missions = resource.view_missions.GET(resource, context)
        view_comments = resource.view_comments.GET(resource, context)

        namespace = {
            'title': title,
            'edit': edit,
            'view_comments': view_comments,
            'view_missions': view_missions }
        return namespace
