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
from datetime import datetime, date, time
from decimal import Decimal as decimal

# Import from itools
from itools.core import merge_dicts
from itools.csv import CSVFile
from itools.database import AndQuery, OrQuery, PhraseQuery
from itools.datatypes import Boolean, Date, Decimal, Email, Integer
from itools.datatypes import PathDataType, String, Unicode
from itools.gettext import MSG
from itools.i18n import format_datetime, format_date
from itools.ical import Time
from itools.uri import resolve_uri
from itools.web import get_context, BaseView, STLView
from itools.web import BaseForm, FormError, ERROR

# Import from ikaaro
from ikaaro.buttons import Button, RemoveButton
from ikaaro.autoform import AutoForm, CheckboxWidget, DateWidget
from ikaaro.autoform import ImageSelectorWidget, MultilineWidget
from ikaaro.autoform import PathSelectorWidget, RadioWidget, TextWidget
from ikaaro.messages import MSG_NEW_RESOURCE, MSG_CHANGES_SAVED
from ikaaro.popup import DBResource_AddImage
from ikaaro.registry import get_resource_class
from ikaaro.comments import indent
from ikaaro.utils import get_base_path_query
from ikaaro.views import CompositeForm, SearchForm

# Import from here
from datatypes import CompanyName, MissionStatus, ProspectName, ProspectStatus
from utils import EmailWidget, MultipleCheckboxWidget
from utils import LinkWidget, NewCompanyWidget, SelectCompanyWidget, TimeWidget


ALERT_ICON_RED = '1240913145_preferences-desktop-notification-bell.png'
ALERT_ICON_ORANGE = '1240913150_bell_error.png'
ALERT_ICON_GREEN = '1240913156_bell_go.png'

REMOVE_ALERT_MSG = MSG(u"""Are you sure you want to remove this alert ?""")

company_schema = {
    'crm_c_title': Unicode,
    'crm_c_address_1': Unicode,
    'crm_c_address_2': Unicode,
    # TODO Country should be CountryName (listed)
    'crm_c_zipcode': String,
    'crm_c_town': Unicode,
    'crm_c_country': Unicode,
    'crm_c_phone': Unicode,
    'crm_c_fax': Unicode,
    'crm_c_website': Unicode,
    'crm_c_description': Unicode,
    'crm_c_activity': Unicode,
    'crm_c_logo': PathDataType }

company_widgets = [
    TextWidget('crm_c_title', title=MSG(u'Title')),
    TextWidget('crm_c_address_1', title=MSG(u'Address')),
    TextWidget('crm_c_address_2', title=MSG(u'Address (next)')),
    TextWidget('crm_c_zipcode', title=MSG(u'Zip Code'), size=10),
    TextWidget('crm_c_town', title=MSG(u'Town')),
    TextWidget('crm_c_country', title=MSG(u'Country')),
    TextWidget('crm_c_phone', title=MSG(u'Phone'), size=15),
    TextWidget('crm_c_fax', title=MSG(u'Fax'), size=15),
    LinkWidget('crm_c_website', title=MSG(u'Website'), size=30),
    TextWidget('crm_c_activity', title=MSG(u'Activity'), size=30),
    ImageSelectorWidget('crm_c_logo', title=MSG(u'Logo'), action='add_logo'),
    MultilineWidget('crm_c_description', title=MSG(u'Observations'),
        default='', rows=4) ]

prospect_schema = {
    'crm_p_company': CompanyName,
    'new_company_url': PathDataType,
    'crm_p_lastname': Unicode,
    'crm_p_firstname': Unicode,
    'crm_p_phone': Unicode,
    'crm_p_mobile': Unicode,
    'crm_p_email': Email,
    'crm_p_description': Unicode,
    'crm_p_position': Unicode,
    'crm_p_status': ProspectStatus,
    'comment': Unicode }

prospect_widgets = [
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


mission_schema = {
    # First mission
    'crm_m_title': Unicode,
    'crm_m_description': Unicode,
    'crm_m_amount': Decimal,
    'crm_m_probability': Integer,
    'crm_m_deadline': Date,
    'crm_m_status': MissionStatus,
    'comment': Unicode,
    'file': PathDataType,
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
    PathSelectorWidget('file', title=MSG(u'Attachement'), default=''),
    DateWidget('alert_date', title=MSG(u'Alert on'), size=8),
    TimeWidget('alert_time', title=MSG(u'at')),
    TextWidget('crm_m_nextaction', title=MSG(u'Next action')) ]


p_status_icons = {
    'lead': '/ui/crm/images/status_yellow.gif',
    'client': '/ui/crm/images/status_green.gif',
    'dead': '/ui/crm/images/status_gray.gif' }
m_status_icons = {
    'opportunity': '/ui/crm/images/status_yellow.gif',
    'project': '/ui/crm/images/status_green.gif',
    'nogo': '/ui/crm/images/status_gray.gif' }


def get_crm(resource):
    cls_crm = get_resource_class('crm')
    crm = resource
    while not isinstance(crm, cls_crm):
        crm = crm.parent
    return crm


def get_crm_path_query(crm_resource):
    crm_path = str(crm_resource.get_abspath())
    return get_base_path_query(crm_path, include_container=True)


def format_amount(str_value):
    value = Decimal.decode(str_value)
    value = value / decimal('1000')
    if float(value).is_integer():
        return '%d k€' % value
    return '%s k€' % str(value)


def format_error_message(context, widgets):
    """ Get an explicit message with missing and invalid fields.
    """
    form_error = context.form_error
    invalid = form_error.invalid
    missing = form_error.missing
    invalids = []
    missings = []
    for widget in widgets:
        name = widget.name
        if name in invalid:
            invalids.append(widget.title.message)
        if name in missing:
            missings.append(widget.title.message)

    message = msg1 = ''
    if missings:
        msg1 = u'1 or more fields are missing: %s' % u', '.join(missings)
    if invalids:
        msg2 = u'1 or more fields are invalid: %s' % u', '.join(invalids)

        if missings:
            message = u'%s ; %s' % (msg1, msg2)
        else:
            message = msg2
    else:
        message = msg1
    return ERROR(message)


def get_form_values(form):
    values = {}
    for key, value in form.iteritems():
        if not value:
            continue
        if key == 'file' and str(value) == '.':
            continue
        if key == 'alert_date':
            value_time = form.get('alert_time', None) or time(9, 0)
            value = datetime.combine(value, value_time)
            values['alert_datetime'] = value
        elif key != 'alert_time':
            values[key] = value
    return values


class ButtonAddProspect(Button):
    name = 'add_prospect'
    access = 'is_allowed_to_edit'
    title = MSG(u'Add prospect')



class ButtonUpdate(Button):
    name = 'update_mission'
    access = 'is_allowed_to_edit'
    title = MSG(u"Update mission")



############
# Comments #
###########################################################################

class Comments_View(STLView):

    access = 'is_allowed_to_edit'
    title = MSG(u'Comments')
    template = '/ui/crm/Comments_view.xml'

    def get_namespace(self, resource, context):

        ns_comments = []
        comments = resource.metadata.get_property('comment') or []
        for i, comment in enumerate(comments):
            comment_datetime = comment.get_parameter('date')
            file = comment.get_parameter('file') or ''
            alert_datetime = comment.get_parameter('alert_datetime')
            if alert_datetime:
                alert_datetime = format_datetime(alert_datetime)
            # TODO Add diff (useful at creation without any comment)
            ns_comment = {
                'id': i,
                'datetime': format_datetime(comment_datetime),
                'file': str(file),
                'alert_datetime': alert_datetime,
                'comment': indent(comment.value)}
            ns_comments.append((id, ns_comment))
        # Sort comments
        ns_comments.sort(reverse=True)
        ns_comments = [y for x, y in ns_comments]

        path_to_resource = context.get_link(resource)
        namespace = {'comments': ns_comments,
                     'path_to_resource': path_to_resource,
                     'msg_alert': REMOVE_ALERT_MSG }
        return namespace


#######
# CRM #
###########################################################################
class CRM_SearchMissions(SearchForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Missions')
    search_template = '/ui/crm/CRM_search.xml'
    styles = ['/ui/crm/style.css']

    search_schema = {
        'search_text': Unicode,
        'search_type': String,
        'status': MissionStatus(multiple=True),
        'with_no_alert': Boolean }
    search_fields =  [
        ('text', MSG(u'Text')), ]

    table_columns = [
        ('icon', None, False),
        ('crm_m_title', MSG(u'Title'), True),
        ('crm_m_prospects', MSG(u'Prospects'), False),
        ('crm_m_nextaction', MSG(u'Next action'), True),
        ('mtime', MSG(u'Last Modified'), True),
        ('crm_m_amount', MSG(u'Amount'), False),
        ('crm_m_probability', MSG(u'Prob.'), False),
        ('crm_m_deadline', MSG(u'Deadline'), False) ]

    batch_msg1 = MSG(u'1 mission.')
    batch_msg2 = MSG(u'{n} missions.')

    # The Search Form
    def get_search_namespace(self, resource, context):
        search_namespace = SearchForm.get_search_namespace(self, resource,
                                                           context)
        # Add status
        default_status = ['opportunity', 'project']
        m_status = context.query['status']
        if not m_status:
            m_status = default_status
        widget = MultipleCheckboxWidget('status', title=MSG(u'Status'),
                    datatype=MissionStatus, value=m_status)
        search_namespace['status'] = widget.render()
        # Add with_no_alert
        with_no_alert = context.query['with_no_alert']
        widget = CheckboxWidget('with_no_alert',
            title=MSG(u'With no alert only'), datatype=Boolean,
            value=with_no_alert)
        search_namespace['with_no_alert'] = widget.render()

        return search_namespace


    def get_items(self, resource, context, *args):
        crm = get_crm(resource)
        crm_path = str(crm.get_abspath())
        # Get the parameters from the query
        query = context.query
        search_text = query['search_text'].strip()
        m_status = query['status']
        with_no_alert = query['with_no_alert']

        # Build the query
        args = list(args)
        abspath = str(resource.get_canonical_path())
        args.append(PhraseQuery('format', 'mission'))
        args.append(get_crm_path_query(crm))
        if search_text:
            args.append(PhraseQuery('text', search_text))
        # Insert status filter
        if m_status:
            status_query = []
            for s in m_status:
                status_query.append(PhraseQuery('crm_m_status', s))
            args.append(OrQuery(*status_query))
        # Insert with_no_alert filter
        if with_no_alert:
            args.append(PhraseQuery('crm_m_has_alerts', False))
        if len(args) == 1:
            query = args[0]
        else:
            query = AndQuery(*args)

        # Ok
        return context.root.search(query)


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
        elif column == 'crm_m_title':
            href = context.get_link(item_resource)
            return item_brain.crm_m_title, href
        elif column == 'crm_m_prospects':
            values = get_value('crm_m_prospect')
            query = [PhraseQuery('name', name) for name in values]
            if len(query) == 1:
                query = query[0]
            else:
                query = OrQuery(*query)
            crm = get_crm(resource)
            query = AndQuery(get_crm_path_query(crm), query)
            query = AndQuery(PhraseQuery('format', 'prospect'), query)
            values = context.root.search(query).get_documents()
            return u' '.join([x.crm_p_lastname for x in values])
        elif column == 'mtime':
            # Last Modified
            accept = context.accept_language
            return format_datetime(item_brain.mtime, accept=accept)
        elif column in ('crm_m_nextaction', 'crm_m_amount',
                'crm_m_probability', 'crm_m_deadline'):
            return get_value(column)


    def sort_and_batch(self, resource, context, results):
        start = context.query['batch_start']
        size = context.query['batch_size']
        sort_by = context.query['sort_by']
        reverse = context.query['reverse']
        if sort_by in ('crm_m_title', 'crm_m_nextaction'):
            sort_by = 'crm_%s' % sort_by

        items = results.get_documents(sort_by=sort_by, reverse=reverse,
                                      start=start, size=size)
        return [(x, resource.get_resource(x.abspath)) for x in items]



class CRM_SearchProspects(SearchForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Prospects')
    search_template = '/ui/crm/CRM_search.xml'
    template = '/ui/crm/CRM_search_prospects.xml'
    styles = ['/ui/crm/style.css']

    search_schema = {
        'search_text': Unicode,
        'search_type': String,
        'status': ProspectStatus(multiple=True), }
    search_fields =  [
        ('text', MSG(u'Text')), ]

    table_columns = [
        ('icon', None, False),
        ('crm_p_lastname', MSG(u'Lastname'), True),
        ('crm_p_firstname', MSG(u'Firstname'), False),
        ('crm_p_company', MSG(u'Company'), False),
        ('crm_p_email', MSG(u'Email'), False),
        ('crm_p_phone', MSG(u'Phone'), False),
        ('crm_p_mobile', MSG(u'mobile'), False),
        ('crm_p_position', MSG(u'Position'), False),
        ('crm_p_opportunity', MSG(u'Opp.'), True),
        ('crm_p_project', MSG(u'Proj.'), True),
        ('crm_p_nogo', MSG(u'NoGo'), True),
        ('mtime', MSG(u'Last Modified'), True),
        ('crm_p_assured', MSG(u'Assured'), True),
        ('crm_p_probable', MSG(u'In pipe'), True)]

    batch_msg1 = MSG(u'1 prospect.')
    batch_msg2 = MSG(u'{n} prospects.')


    def get_items(self, resource, context, *args):
        crm = get_crm(resource)
        crm_path = str(crm.get_abspath())
        # Get the parameters from the query
        query = context.query
        search_text = query['search_text'].strip()
        p_status = query['status']

        # Build the query
        args = list(args)
        abspath = str(resource.get_canonical_path())
        args.append(PhraseQuery('format', 'prospect'))
        args.append(get_crm_path_query(crm))
        if search_text:
            args.append(PhraseQuery('text', search_text))
        # Insert status filter
        if p_status:
            status_query = []
            for s in p_status:
                status_query.append(PhraseQuery('crm_p_status', s))
            args.append(OrQuery(*status_query))
        if len(args) == 1:
            query = args[0]
        else:
            query = AndQuery(*args)

        # Ok
        return context.root.search(query)


    def get_item_value(self, resource, context, item, column):
        item_brain, item_resource = item
        if column == 'checkbox':
            # checkbox
            return item_brain.name, False
        elif column == 'crm_p_assured':
            value = item_brain.crm_p_assured
            return format_amount(value)
        elif column == 'crm_p_probable':
            value = item_brain.crm_p_probable
            return format_amount(value)
        get_value = item_resource.get_value
        if column == 'icon':
            # Status
            value = get_value('crm_p_status')
            return p_status_icons[value]
        elif column == 'crm_p_company':
            company = get_value(column)
            if company:
                crm = get_crm(resource)
                company_resource = crm.get_resource('companies/%s' % company)
                href = context.get_link(company_resource)
                title = company_resource.get_title()
                return title, href
            else:
                return ''
        elif column == 'crm_p_lastname':
            href = '%s/' % context.get_link(item_resource)
            return get_value(column), href
        elif column == 'crm_p_firstname':
            href = '%s/' % context.get_link(item_resource)
            return get_value(column), href
        elif column == 'crm_p_phone':
            return get_value(column)
        elif column == 'crm_p_mobile':
            return get_value(column)
        elif column == 'crm_p_email':
            value = get_value(column)
            href = 'mailto:%s' % value
            return value, href
        elif column == 'mtime':
            # Last Modified
            accept = context.accept_language
            return format_datetime(item_brain.mtime, accept=accept)
        elif column in ('crm_p_opportunity', 'crm_p_project', 'crm_p_nogo'):
            return getattr(item_brain, 'crm_%s' % column)


    def sort_and_batch(self, resource, context, results):
        start = context.query['batch_start']
        size = context.query['batch_size']
        sort_by = context.query['sort_by']
        reverse = context.query['reverse']

        # Calculate the probable and assured amount
        for brain in results.get_documents():
            self.assured += Decimal.decode(brain.crm_p_assured)
            self.probable += Decimal.decode(brain.crm_p_probable)

        items = results.get_documents(sort_by=sort_by, reverse=reverse,
                                      start=start, size=size)
        return [(x, resource.get_resource(x.abspath)) for x in items]


    #######################################################################
    # The Search Form
    def get_search_namespace(self, resource, context):
        search_namespace = SearchForm.get_search_namespace(self, resource,
                                                           context)
        # Add status
        default_status = ['lead', 'client']
        p_status = context.query['status']
        if not p_status:
            p_status = default_status
        widget = MultipleCheckboxWidget('status', title=MSG(u'Status'),
                datatype=ProspectStatus, value=p_status)
        search_namespace['status'] = widget.render()
        # Add *empty* with_no_alert
        search_namespace['with_no_alert'] = None

        return search_namespace


    def get_namespace(self, resource, context):
        self.assured = decimal('0.0')
        self.probable = decimal('0.0')
        namespace = SearchForm.get_namespace(self, resource, context)

        # Add infos about assured and probable amount
        # TODO Filter by year or semester
        total = self.assured + self.probable

        namespace['assured'] = format_amount(self.assured)
        namespace['probable'] = format_amount(self.probable)
        namespace['total'] = format_amount(total)
        namespace['crm-infos'] = True
        namespace['export-csv'] = True
        return namespace


###########
# Company #
###########################################################################

class Company_AddImage(DBResource_AddImage):

    def get_root(self, context):
        return context.resource


    def get_start(self, resource):
        return self.get_root(get_context())



class Company_EditForm(AutoForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit company')
    styles = ['/ui/crm/style.css']

    def get_query_schema(self):
        return company_schema.copy()


    def get_schema(self, resource, context):
        # c_title mandatory into form
        return merge_dicts(company_schema, c_title=Unicode(mandatory=True))


    def get_widgets(self, resource, context):
        return company_widgets[:]


    def get_value(self, resource, context, name, datatype):
        value = resource.get_value(name)
        return value if value is not None else datatype.default


    def action(self, resource, context, form):
        values = get_form_values(form)
        resource._update(values, context)
        context.message = MSG_CHANGES_SAVED



class Company_AddForm(Company_EditForm):

    access = 'is_allowed_to_add'
    title = MSG(u'New company')
    context_menus = []

    def get_value(self, resource, context, name, datatype):
        return context.query.get(name) or datatype.default


    def get_namespace(self, resource, context):
        namespace = AutoForm.get_namespace(self, resource, context)
        return namespace


    def action(self, resource, context, form):
        values = get_form_values(form)
        name = resource.add_company(values)
        crm = get_crm(resource)
        goto = context.get_link(crm)
        goto = '%s/prospects/;new_prospect?p_company=%s' % (goto, name)
        return context.come_back(MSG_NEW_RESOURCE, goto)



class Company_ViewProspects(CRM_SearchProspects):

    search_template = None

    def get_table_columns(self, resource, context):
        columns = []
        for column in self.table_columns:
            name, title, sort = column
            if name == 'crm_p_company':
                continue
            if name not in ('crm_p_email', 'crm_p_phone', 'crm_p_mobile'):
                columns.append(column)

        return columns


    def get_items(self, resource, context, *args):
        args = list(args)
        args.append(PhraseQuery('crm_p_company', resource.name))
        return CRM_SearchProspects.get_items(self, resource, context, *args)


    def get_namespace(self, resource, context):
        namespace = CRM_SearchProspects.get_namespace(self, resource, context)
        namespace['crm-infos'] = False
        namespace['export-csv'] = False
        return namespace



class Company_View(CompositeForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'View company')
    styles = ['/ui/crm/style.css']

    subviews = [Company_EditForm(), Company_ViewProspects()]


#############
# Prospects #
###########################################################################

class Prospect_AddForm(AutoForm):
    """ To add a new prospect into the crm.
    """
    access = 'is_allowed_to_add'
    title = MSG(u'New prospect')
    template = '/ui/crm/Prospect_new_instance.xml'
    styles = ['/ui/crm/style.css']


    def get_query_schema(self):
        return merge_dicts(prospect_schema, mission_schema)


    def get_schema(self, resource, context):
        # p_lastname, p_status, m_title, m_status are mandatory
        schema = {
            'crm_p_lastname': Unicode(mandatory=True),
            'crm_p_status': ProspectStatus(mandatory=True),
            'crm_m_title': Unicode(),
            'crm_m_status': MissionStatus() }
        return merge_dicts(prospect_schema, mission_schema, schema)


    def get_widgets(self, resource, context):
        widgets = prospect_widgets[:] + mission_widgets[:]
        return widgets


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


    def on_form_error(self, resource, context):
        message = format_error_message(context, self.get_widgets(resource,
                                                                 context))
        return context.come_back(message)


    def get_namespace(self, resource, context):
        namespace = AutoForm.get_namespace(self, resource, context)

        # Modify widgets namespace to change template
        for widget in namespace['widgets']:
            namespace[widget['name']] = widget

        return namespace


    def action(self, resource, context, form):
        crm = get_crm(resource)
        prospects = crm.get_resource('prospects')
        missions = crm.get_resource('missions')
        # Split values prospect/mission
        p_values = {}
        m_values = {}
        for key, value in form.iteritems():
            if key[:2] == 'crm_p_':
                p_values[key] = value
            elif key[:2] == 'crm_m_':
                m_values[key] = value
        # Add prospect
        p_name = prospects.add_prospect(p_values)
        # Add mission if title is defined
        if m_values['crm_m_title']:
            m_values['crm_m_prospect'] = p_name
            m_name = missions.add_mission(m_values)
            goto = '%s/missions/%s/' % (context.get_link(crm), m_name)
        else:
            goto = '%s/prospects/%s/' % (context.get_link(crm), p_name)

        return context.come_back(MSG_NEW_RESOURCE, goto=goto)



class Prospect_EditForm(AutoForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit prospect')
    submit_value = MSG(u'Update prospect')
    styles = ['/ui/crm/style.css']


    def get_query_schema(self):
        return prospect_schema.copy()


    def get_schema(self, resource, context):
        # p_lastname, p_status, are mandatory
        schema = {
            'crm_p_lastname': Unicode(mandatory=True),
            'crm_p_status': ProspectStatus(mandatory=True) }
        return merge_dicts(prospect_schema, schema)


    def get_widgets(self, resource, context):
        widgets = prospect_widgets[:]
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



class Prospect_SearchMissions(SearchForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Missions')
    search_template = '/ui/crm/Prospect_search.xml'

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
        args.append(PhraseQuery('crm_m_prospect', resource.name))
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



class Prospect_ViewMissions(Prospect_SearchMissions):

    search_template = None
    search_schema = {}
    search_fields = []

    def get_search_namespace(self, resource, context):
        return {}


    def get_query_schema(self):
        return merge_dicts(Prospect_SearchMissions.get_query_schema(self),
                           batch_size=Integer(default=10))


    def get_items(self, resource, context, *args):
        # Build the query
        args = list(args)
        args.append(PhraseQuery('crm_m_prospect', resource.name))
        if len(args) == 1:
            query = args[0]
        else:
            query = AndQuery(*args)
        # Ok
        crm = get_crm(resource)
        base_path_query = get_crm_path_query(crm)
        return context.root.search(AndQuery(query, base_path_query))



class Prospect_View(CompositeForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'View prospect')
    template = '/ui/crm/Prospect_view.xml'
    styles = ['/ui/crm/style.css']

    subviews = [Prospect_EditForm(), Prospect_ViewMissions(), Comments_View()]

    def get_namespace(self, resource, context):
        title = resource.get_title()
        edit = resource.edit_form.GET(resource, context)
        view_missions = resource.view_missions.GET(resource, context)
        view_comments = resource.view_comments.GET(resource, context)
        new_url = '../../missions/;new_mission?m_prospect=%s' % resource.name
        namespace = {
            'title': title,
            'edit': edit,
            'new_url': new_url,
            'view_comments': view_comments,
            'view_missions': view_missions }
        return namespace


############
# Mission #
###########################################################################

class Mission_EditForm(AutoForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit mission')
    template = '/ui/crm/Mission_edit_form.xml'
    actions = [ButtonUpdate()]

    def get_query_schema(self):
        return mission_schema.copy()


    def get_schema(self, resource, context):
        # m_title, m_status are mandatory
        schema = {
            'crm_m_title': Unicode(mandatory=True),
            'crm_m_status': MissionStatus(mandatory=True) }
        return merge_dicts(mission_schema, schema)


    def get_widgets(self, resource, context):
        return mission_widgets[:]


    def get_value(self, resource, context, name, datatype):
        if name in ('alert_date', 'alert_time'):
            return datatype.default
        elif name == 'comment':
            return context.query.get(name) or u''
        elif name == 'file':
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

        # Reindex prospects to update Opp/Proj/NoGo, p_assured and p_probable
        crm = get_crm(resource)
        prospects = resource.get_value('crm_m_prospect')
        for prospect in prospects:
            prospect = crm.get_resource('prospects/%s' % prospect)
            context.database.change_resource(prospect)
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
        # Add mandatory m_prospect to query schema
        return merge_dicts(mission_schema,
                           m_prospect=ProspectName(mandatory=True))


    def get_schema(self, resource, context):
        # m_title, m_status are mandatory
        schema = {
            'crm_m_title': Unicode(mandatory=True),
            'crm_m_status': MissionStatus(mandatory=True) }
        return merge_dicts(mission_schema, schema)


    def get_value(self, resource, context, name, datatype):
        return context.query.get(name) or datatype.default


    def action(self, resource, context, form):
        # Get m_prospect from the query
        form['crm_m_prospect'] = context.query['crm_m_prospect']
        values = get_form_values(form)
        name = resource.add_mission(values)

        # Reindex prospects to update Opp/Proj/NoGo, p_assured and p_probable
        crm = get_crm(resource)
        prospect = values.get('crm_m_prospect')
        prospect = crm.get_resource('prospects/%s' % prospect)
        context.database.change_resource(prospect)

        goto = './%s' % name
        return context.come_back(MSG_NEW_RESOURCE, goto=goto)



class Mission_ViewProspects(CRM_SearchProspects):

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
        prospects = resource.get_value('crm_m_prospect')
        if len(prospects) == 1:
            args.append(PhraseQuery('name', prospects[0]))
        elif len(prospects) > 1:
            args.append(OrQuery(*[PhraseQuery('name', x) for x in prospects]))
        return CRM_SearchProspects.get_items(self, resource, context, *args)


    def get_namespace(self, resource, context):
        namespace = CRM_SearchProspects.get_namespace(self, resource, context)
        namespace['crm-infos'] = False
        namespace['export-csv'] = False
        return namespace



class Mission_ViewProspect(Mission_ViewProspects):

    def get_items(self, resource, context, *args):
        args = list(args)
        prospect = context.query['crm_m_prospect']
        args.append(PhraseQuery('name', prospect))
        return CRM_SearchProspects.get_items(self, resource, context, *args)



class Mission_EditProspects(Mission_ViewProspects):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit prospects')

    schema = {'ids': String(multiple=True, mandatory=True)}

    table_actions = [
            RemoveButton(name='remove', title=MSG(u'Remove prospect')) ]

    def get_table_columns(self, resource, context):
        columns = Mission_ViewProspects.get_table_columns(self, resource,
                                                          context)
        columns = list(columns) # do not alter parent columns
        columns.insert(0, ('checkbox', None))
        return columns


    def action_remove(self, resource, context, form):
        prospects = resource.get_value('crm_m_prospect')

        for prospect_id in form.get('ids', []):
            try:
                prospects.remove(prospect_id)
            except:
                pass

        if len(prospects) == 0:
            msg = ERROR(u'At least one prospect is required')
        else:
            # Apply change
            resource._update({'crm_m_prospect': prospects})
            msg = MSG_CHANGES_SAVED

        context.message = msg



class Mission_AddProspects(CRM_SearchProspects):

    access = 'is_allowed_to_edit'
    title = MSG(u'Add prospects')

    schema = {'ids': String(multiple=True, mandatory=True)}

    table_actions = [ButtonAddProspect]

    def get_table_columns(self, resource, context):
        columns = CRM_SearchProspects.get_table_columns(self, resource, context)
        columns = list(columns) # do not alter parent columns
        columns.insert(0, ('checkbox', None))
        return columns


    def get_namespace(self, resource, context):
        namespace = CRM_SearchProspects.get_namespace(self, resource, context)
        namespace['crm-infos'] = False
        namespace['export-csv'] = False
        return namespace


    def action_add_prospect(self, resource, context, form):
        prospects = resource.get_value('crm_m_prospect')

        for prospect_id in form.get('ids', []):
            prospects.append(prospect_id)

        prospects = list(set(prospects))
        # Apply change
        resource._update({'crm_m_prospect': prospects})
        msg = MSG_CHANGES_SAVED



class Mission_View(CompositeForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'View mission')
    template = '/ui/crm/Mission_view.xml'
    styles = ['/ui/crm/style.css', '/ui/tracker/style.css']
    scripts = ['/ui/crm/jquery.maskedinput-1.2.2.min.js']

    subviews = [Mission_EditForm(), Mission_ViewProspects(), Comments_View()]

    def get_namespace(self, resource, context):
        title = resource.get_value('crm_m_title')
        edit = resource.edit_form.GET(resource, context)
        view_comments = resource.view_comments.GET(resource, context)
        view_prospects = resource.view_prospects.GET(resource, context)
        namespace = {
            'title': title,
            'edit': edit,
            'view_comments': view_comments,
            'view_prospects': view_prospects }
        return namespace



class Mission_Add(Mission_View):

    title = MSG(u'New mission')
    subviews = [Mission_ViewProspect(), Mission_AddForm()]


    def on_query_error(self, resource, context):
        msg = u'Please select a valid prospect before creating a mission.'
        return context.come_back(ERROR(msg), goto='..')


    def get_namespace(self, resource, context):
        add = resource.add_form.GET(resource, context)
        view_prospect = resource.view_prospect.GET(resource, context)
        namespace = {
            'title': MSG(u'New mission'),
            'edit': add,
            'view_comments': None,
            'view_prospects': view_prospect}
        return namespace



class CRM_ExportToCSV(BaseView):

    access = 'is_allowed_to_edit'
    title = MSG(u'Export to CSV')
    query_schema = {'editor': String(default='excel')}


    def get_mission_infos(self, resource, mission):
        infos = []
        prospect = mission.get_value('crm_m_prospect')[0]
        prospect = resource.get_resource('prospects/%s' % prospect)
        get_value = prospect.get_value
        # Prospect
        infos.append(get_value('crm_p_lastname'))
        infos.append(get_value('crm_p_firstname') or '')
        p_company = get_value('crm_p_company')
        if p_company:
            company = resource.get_resource('companies/%s' % p_company)
            infos.append(company.get_value('crm_c_title'))
        infos.append(get_value('crm_p_status'))

        # Mission
        for property in ('crm_m_title', 'crm_m_amount', 'crm_m_probability',
                'crm_m_status', 'crm_m_deadline'):
            property = mission.get_value(property)
            infos.append(property or '')
        return infos


    def GET(self, resource, context):
        query = PhraseQuery('format', 'mission')
        crm = get_crm(resource)
        base_path_query = get_crm_path_query(crm)
        results = context.root.search(AndQuery(query, base_path_query))
        missions = results.get_documents()
        if len(missions) == 0:
            context.message = ERROR(u"No data to export.")
            return

        # Get CSV encoding and separator (OpenOffice or Excel)
        editor = context.query['editor']
        if editor == 'oo':
            separator = ','
            encoding = 'utf-8'
        else:
            separator = ';'
            encoding = 'cp1252'

        # Create the CSV
        csv = CSVFile()
        # Add the header
        csv.add_row([
            'lastname', 'firstname', 'company', 'prospect\'s status',
            'mission\'s title', 'amount', 'probability', 'mission\'s status',
            'deadline'])
        # Fill the CSV
        for mission in missions:
            mission = resource.get_resource(mission.abspath)
            infos = self.get_mission_infos(resource, mission)
            row = []
            for value in infos:
                if isinstance(value, unicode):
                    value = value.encode(encoding)
                else:
                    value = str(value)
                row.append(value)
            csv.add_row(row)

        # Set response type
        context.set_content_type('text/comma-separated-values')
        context.set_content_disposition('attachment; filename="export.csv"')
        return csv.to_str(separator=separator)



class CRM_Alerts(SearchForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Alerts')
    template = '/ui/crm/CRM_alerts.xml'
    styles = ['/ui/crm/style.css']

    search_schema = {
        'search_text': Unicode,
        'search_type': String,
    }
    search_fields =  []

    schema = {'ids': String(multiple=True, mandatory=True)}

    table_columns = [
        ('checkbox', None, False),
        ('icon', None, False),
        ('alert_date', MSG(u'Date'), False),
        ('alert_time', MSG(u'Time'), False),
        ('crm_p_lastname', MSG(u'Lastname'), False),
        ('crm_p_firstname', MSG(u'Firstname'), False),
        ('crm_p_company', MSG(u'Company'), False),
        ('crm_m_title', MSG(u'Mission'), False),
        ('crm_m_nextaction', MSG(u'Next action'), False)]

    batch_msg1 = MSG(u'1 alert.')
    batch_msg2 = MSG(u'{n} alerts.')

    table_actions = [RemoveButton(name='remove', title=MSG(u'Remove alert'),
                                  confirm=REMOVE_ALERT_MSG)]


    def get_page_title(self, resource, context):
        user = context.user
        if user:
            return u'CRM: Alerts (%s)' % user.get_title()
        return u'CRM'


    def get_table_columns(self, resource, context):
        return self.table_columns


    def get_items(self, resource, context, *args):
        user = context.user

        # Build the query
        args = list(args)
        args.append(PhraseQuery('format', 'mission'))
        args.append(PhraseQuery('crm_m_has_alerts', True))
        if len(args) == 1:
            query = args[0]
        else:
            query = AndQuery(*args)

        items = []
        # Check each mission to get only alerts
        crm = get_crm(resource)
        base_path_query = get_crm_path_query(crm)
        results = context.root.search(AndQuery(query, base_path_query))
        documents = results.get_documents()
        for doc in documents:
            mission = resource.get_resource(doc.abspath)
            # Check access FIXME should be done in catalog
            if not mission.is_allowed_to_view(user, mission):
                continue
            # Get alert
            comments = mission.metadata.get_property('comment') or []
            for i, comment in enumerate(comments):
                alert_datetime = comment.get_parameter('alert_datetime')
                if not alert_datetime:
                    continue
                m_nextaction = comment.get_parameter('crm_m_nextaction')
                items.append((alert_datetime, m_nextaction, mission, i))

        return items


    def get_item_value(self, resource, context, item, column):
        alert_datetime, m_nextaction, mission, comment_id = item
        if column == 'checkbox':
            alert_id = '%s__%d' % (mission.name, comment_id)
            # checkbox
            return alert_id, False
        if column == 'icon':
            if alert_datetime.date() < date.today():
                icon_name = ALERT_ICON_RED
            elif alert_datetime < datetime.now():
                icon_name = ALERT_ICON_ORANGE
            else:
                icon_name = ALERT_ICON_GREEN
            # icon #resource.get_resource_icon(16)
            path_to_icon = '/ui/crm/images/%s' % icon_name
            if path_to_icon.startswith(';'):
                name = resource.name
                path_to_icon = resolve_uri('%s/' % name, path_to_icon)
            href = 'missions/%s' % mission.name
            return path_to_icon
        elif column in ('crm_p_lastname', 'crm_p_firstname'):
            prospect = mission.get_value('crm_m_prospect')[0]
            prospect = resource.get_resource('prospects/%s' % prospect)
            value = prospect.get_value(column)
            if mission.is_allowed_to_edit(context.user, mission):
                href = context.get_link(prospect)
                return value, href
            return value
        elif column == 'crm_p_company':
            prospect = mission.get_value('crm_m_prospect')[0]
            prospect = resource.get_resource('prospects/%s' % prospect)
            company_name = prospect.get_value(column)
            company = mission.get_resource('../../companies/%s' % company_name)
            title = company.get_title()
            return title
        elif column == 'crm_m_title':
            value = mission.get_value(column)
            if mission.is_allowed_to_edit(context.user, mission):
                href = context.get_link(mission)
                return value, href
            return value
        elif column == 'alert_date':
            alert_date = alert_datetime.date()
            return format_date(alert_date)
        elif column == 'alert_time':
            alert_time = alert_datetime.time()
            return Time.encode(alert_time)
        elif column == 'crm_m_nextaction':
            return m_nextaction


    def sort_and_batch(self, resource, context, results):
        results.sort()

        items, past, future = [], [], []
        today = date.today()
        for result in results:
            alert_date = result[0].date()
            if alert_date < today:
                # Past alerts at the bottom
                past.append(result)
            elif alert_date == today:
                # Today alerts at the top
                items.append(result)
            else:
                # Future alerts between
                items.append(result)
        items.extend(future)
        items.extend(past)
        return items


    def action_remove(self, resource, context, form):
        not_removed = []
        for alert_id in form.get('ids', []):
            try:
                mission_name, comment_id = alert_id.split('__')
                comment_id = int(comment_id)
            except ValueError:
                not_removed.append(alert_id)
                continue
            # Remove alert_datetime
            crm = get_crm(resource)
            mission = crm.get_resource('missions/%s' % mission_name)
            comments = mission.metadata.get_property('comment')
            comments[comment_id].set_parameter(alert_datetime=None)
            # XXX set_property?
            context.database.change_resource(mission)

        if not_removed:
            msg = ERROR(u'One or more alert could not have been removed.')
        else:
            msg = MSG_CHANGES_SAVED

        context.message = msg



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
