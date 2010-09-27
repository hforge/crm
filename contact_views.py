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
from itools.core import merge_dicts
from itools.database import AndQuery, OrQuery, PhraseQuery
from itools.datatypes import Email, Integer
from itools.datatypes import PathDataType, String, Unicode
from itools.gettext import MSG
from itools.i18n import format_datetime
from itools.web import FormError

# Import from ikaaro
from ikaaro.autoform import AutoForm
from ikaaro.autoform import MultilineWidget
from ikaaro.autoform import RadioWidget, TextWidget
from ikaaro.messages import MSG_NEW_RESOURCE, MSG_CHANGES_SAVED
from ikaaro.views import CompositeForm, SearchForm

# Import from crm
from base_views import get_form_values, m_status_icons, Comments_View
from datatypes import CompanyName, MissionStatus, ContactStatus
from mission_views import mission_schema, mission_widgets
from mission_views import get_changes, send_notification
from utils import get_crm, get_crm_path_query
from widgets import EmailWidget, MultipleCheckboxWidget
from widgets import NewCompanyWidget, SelectCompanyWidget


contact_schema = {
    'crm_p_company': CompanyName,
    'new_company_url': PathDataType,
    'crm_p_lastname': Unicode,
    'crm_p_firstname': Unicode,
    'crm_p_phone': Unicode,
    'crm_p_mobile': Unicode,
    'crm_p_email': Email,
    'crm_p_description': Unicode,
    'crm_p_position': Unicode,
    'crm_p_status': ContactStatus,
    'comment': Unicode }

contact_widgets = [
    SelectCompanyWidget('crm_p_company', title=MSG(u'Company')),
    NewCompanyWidget('new_company_url', title=MSG(u' ')),
    TextWidget('crm_p_lastname', title=MSG(u'Last name'), default='', size=30),
    TextWidget('crm_p_firstname', title=MSG(u'First name'), default='',
               size=30),
    TextWidget('crm_p_phone', title=MSG(u'Phone'), default='', size=15),
    TextWidget('crm_p_mobile', title=MSG(u'Mobile'), default='', size=15),
    EmailWidget('crm_p_email', title=MSG(u'Email'), default='', size=30),
    TextWidget('crm_p_position', title=MSG(u'Position'), default='', size=15),
    MultilineWidget('crm_p_description', title=MSG(u'Observations'),
        default='', rows=4),
    RadioWidget('crm_p_status', title=MSG(u'Status'), has_empty_option=False,
                is_inline=True),
    MultilineWidget('comment', title=MSG(u'New comment'), default='',
                    rows=3) ]


class Contact_AddForm(AutoForm):
    """ To add a new contact into the crm.
    """
    access = 'is_allowed_to_add'
    title = MSG(u'New contact')
    template = '/ui/crm/contact/new.xml'
    styles = ['/ui/crm/style.css']


    def get_query_schema(self):
        return merge_dicts(contact_schema, mission_schema)


    def get_schema(self, resource, context):
        # crm_p_lastname and crm_p_status are mandatory
        return merge_dicts(contact_schema, mission_schema,
                crm_p_lastname=contact_schema['crm_p_lastname'](
                    mandatory=True),
                crm_p_status=contact_schema['crm_p_status'](mandatory=True),
                crm_m_cc=mission_schema['crm_m_cc'](resource=resource))


    def get_widgets(self, resource, context):
        return contact_widgets + mission_widgets


    def get_value(self, resource, context, name, datatype):
        if name == 'new_company_url':
            value = '../companies/;new_company'
            return value
        if name in self.get_query_schema():
            value = context.query[name]
            if value is not None:
                return context.query[name]
        value = AutoForm.get_value(self, resource, context, name, datatype)

        if name == 'crm_m_deadline' and value is None:
            year = date.today().year
            return date(year, 12, 31)
        elif name == 'crm_m_status':
            print 'STATUS', repr(value)
            return value
        if value is None:
            return datatype.default
        return value


    def _get_form(self, resource, context):
        form = AutoForm._get_form(self, resource, context)

        # If title is defined, status is required
        m_title = form['crm_m_title'].strip()
        m_status = form['crm_m_status']
        if m_title and m_status is None:
            raise FormError(invalid=['crm_m_status'])

        return form


    def get_namespace(self, resource, context):
        namespace = AutoForm.get_namespace(self, resource, context)

        # Modify widgets namespace to change template
        for widget in namespace['widgets']:
            # XXX multilingual to monolingual
            widget['widget'] = widget['widgets'][0]
            namespace[widget['name']] = widget

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
        # Add contact
        p_name = contacts.add_contact(p_values)
        # Add mission if title is defined
        if m_values['crm_m_title']:
            m_values['crm_m_contact'] = p_name
            m_name = missions.add_mission(m_values)
            mission = missions.get_resource(m_name)
            changes = get_changes(mission, context, form, new=True)
            send_notification(mission, context, form, changes, new=True)
            goto = '%s/missions/%s/' % (context.get_link(crm), m_name)
        else:
            goto = '%s/contacts/%s/' % (context.get_link(crm), p_name)

        return context.come_back(MSG_NEW_RESOURCE, goto=goto)



class Contact_EditForm(AutoForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit contact')
    submit_value = MSG(u'Update contact')
    styles = ['/ui/crm/style.css']


    def get_query_schema(self):
        return contact_schema.copy()


    def get_schema(self, resource, context):
        # crm_p_lastname and crm_p_status are mandatory
        return merge_dicts(contact_schema,
                crm_p_lastname=contact_schema['crm_p_lastname'](
                    mandatory=True),
                crm_p_status=contact_schema['crm_p_status'](mandatory=True))


    def get_widgets(self, resource, context):
        widgets = contact_widgets[:]
        return widgets


    def get_value(self, resource, context, name, datatype):
        if name == 'new_company_url':
            value = '../../companies/;new_company'
            return value
        if name in self.get_query_schema():
            value = context.query[name]
            if value:
                return context.query[name]
        if name == 'comment':
            return u''
        value = resource.get_value(name)
        return value if value is not None else datatype.default


    def get_namespace(self, resource, context):
        # Build namespace
        namespace = AutoForm.get_namespace(self, resource, context)

        # Force reinitialization of comment field to '' after a POST.
        if (context.method != 'POST'):
            return namespace
        for index, widget in enumerate(namespace['widgets']):
            if widget['name'] == 'comment':
                comment_widget = MultilineWidget('comment',
                    title=MSG(u'New comment'), rows=3, datatype=Unicode,
                    value=u'')
                widget['widget'] = comment_widget.render()
        return namespace


    def action(self, resource, context, form):
        values = get_form_values(form)
        resource._update(values, context)
        context.message = MSG_CHANGES_SAVED



class Contact_SearchMissions(SearchForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Missions')
    search_template = '/ui/crm/contact/search.xml'

    search_schema = {
        'search_text': Unicode,
        'search_type': String,
        'crm_m_status': MissionStatus(multiple=True) }
    search_fields =  [
        ('title', MSG(u'Title')),
        ('text', MSG(u'Text')) ]

    table_columns = [
        ('icon', None, False),
        ('crm_m_title', MSG(u'Title'), True),
        ('crm_m_nextaction', MSG(u'Next action'), True),
        ('mtime', MSG(u'Last Modified'), True),
        ('crm_m_amount', MSG(u'Amount'), False),
        ('crm_m_probability', MSG(u'Prob.'), False),
        ('crm_m_deadline', MSG(u'Deadline'), False) ]

    batch_msg1 = MSG(u'1 mission.')
    batch_msg2 = MSG(u'{n} missions.')


    def get_query_schema(self):
        return merge_dicts(SearchForm.get_query_schema(self),
                           sort_by=String(default='mtime'))


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
        get_value = item_resource.get_value
        if column == 'icon':
            # Status
            value = get_value('crm_m_status')
            return m_status_icons[value]
        # FIXME
        elif column == 'crm_m_title':
            # Title
            return get_value(column), context.get_link(item_resource)
        elif column == 'status':
            # Status
            return MissionStatus.get_value(get_value('crm_m_status'))
        elif column == 'mtime':
            # Last Modified
            accept = context.accept_language
            return format_datetime(item_brain.mtime, accept=accept)
        elif column == 'crm_m_amount':
            value = get_value(column)
            if value:
                value = u'%02.02f €' % value
            return value
        elif column in ('crm_m_probability', 'crm_m_deadline',
                'crm_m_nextaction'):
            value = get_value(column)
            return value


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
    search_schema = {}
    search_fields = []

    def get_search_namespace(self, resource, context):
        return {}


    def get_query_schema(self):
        return merge_dicts(Contact_SearchMissions.get_query_schema(self),
                           batch_size=Integer(default=10))


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

    subviews = [Contact_EditForm(), Contact_ViewMissions(), Comments_View()]

    def get_namespace(self, resource, context):
        title = resource.get_title()
        edit = resource.edit_form.GET(resource, context)
        view_missions = resource.view_missions.GET(resource, context)
        view_comments = resource.view_comments.GET(resource, context)
        new_url = '../../missions/;new_mission?crm_m_contact=%s' % resource.name
        namespace = {
            'title': title,
            'edit': edit,
            'new_url': new_url,
            'view_comments': view_comments,
            'view_missions': view_missions }
        return namespace
