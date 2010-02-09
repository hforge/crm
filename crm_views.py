# -*- coding: UTF-8 -*-
# Copyright (C) 2009 Nicolas Deram <nicolas@itaapy.com>
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
from itools.datatypes import Date, Decimal, Email, Integer
from itools.datatypes import PathDataType, String, Unicode
from itools.gettext import MSG
from itools.handlers import checkid
from itools.i18n import format_datetime, format_date
from itools.ical import Time
from itools.uri import resolve_uri
from itools.vfs import FileName
from itools.web import BaseView, STLForm, STLView, get_context
from itools.web import ERROR, FormError, MSG_MISSING_OR_INVALID
from itools.xapian import AndQuery, OrQuery, PhraseQuery

# Import from ikaaro
from ikaaro.buttons import RemoveButton
from ikaaro.forms import AutoForm, DateWidget, MultilineWidget, PathSelectorWidget
from ikaaro.forms import SelectRadio, SelectWidget, TextWidget
from ikaaro.messages import MSG_NEW_RESOURCE, MSG_CHANGES_SAVED
from ikaaro.registry import get_resource_class
from ikaaro.resource_views import DBResource_Edit
from ikaaro.utils import generate_name as igenerate_name, get_base_path_query
from ikaaro.views import CompositeForm, SearchForm
from ikaaro.views_new import NewInstance
from ikaaro.tracker.issue_views import indent

# Import from here
from datatypes import CompanyName, MissionStatus, ProspectStatus
from utils import generate_name, MultipleCheckBoxWidget, TimeWidget


ALERT_ICON_RED = '1240913145_preferences-desktop-notification-bell.png'
ALERT_ICON_ORANGE = '1240913150_bell_error.png'
ALERT_ICON_GREEN = '1240913156_bell_go.png'

REMOVE_ALERT_MSG = MSG(u"""Are you sure you want to remove this alert ?""")


prospect_schema = {
    'p_company': CompanyName(),
    'p_lastname': Unicode(mandatory=True),
    'p_firstname': Unicode,
    'p_phone': Unicode,
    'p_mobile': Unicode,
    'p_email': Email,
    'p_description': Unicode,
    'p_status': ProspectStatus(mandatory=True)}

company_schema = {
    'c_title': Unicode(mandatory=True),
    'c_address_1': Unicode,
    'c_address_2': Unicode,
    'c_zipcode': String,
    'c_town': Unicode,
    # XXX Country should be CountryName (listed)
    'c_country': Unicode,
    'c_phone': Unicode,
    'c_fax': Unicode}

prospect_widgets = [
    SelectWidget('p_company', title=MSG(u'Company')),
    TextWidget('p_lastname', title=MSG(u'Last name'), default='', size=30),
    TextWidget('p_firstname', title=MSG(u'First name'), default='',
               size=30),
    TextWidget('p_phone', title=MSG(u'Phone'), default='', size=15),
    TextWidget('p_mobile', title=MSG(u'Mobile'), default='', size=15),
    TextWidget('p_email', title=MSG(u'Email'), default='', size=30),
    MultilineWidget('p_description', title=MSG(u'Comment'), default='',
                    rows=3),
    SelectRadio('p_status', title=MSG(u'Status'), has_empty_option=False,
                is_inline=True),
    # New Company
    TextWidget('c_title', title=MSG(u'Company Name'), size=30),
    TextWidget('c_address_1', title=MSG(u'Address')),
    TextWidget('c_address_2', title=MSG(u'Address')),
    TextWidget('c_zipcode', title=MSG(u'Zip code'), size=10),
    TextWidget('c_town', title=MSG(u'Town'), size=30),
    # XXX Country should be listed
    TextWidget('c_country', title=MSG(u'Country'), size=30),
    TextWidget('c_phone', title=MSG(u'Phone'), size='15'),
    TextWidget('c_fax', title=MSG(u'Fax'), size='15')]


mission_schema = {
    # First mission
    'm_title': Unicode(mandatory=True),
    'm_description': Unicode(mandatory=True),
    'm_amount': Decimal,
    'm_probability': Integer,
    'm_deadline': Date,
    'm_status': MissionStatus(mandatory=True)}

mission_widgets = [
    # First mission
    TextWidget('m_title', title=MSG(u'Title')),
    MultilineWidget('m_description', title=MSG(u'Description'), rows=3),
    TextWidget('m_amount', title=MSG(u'Amount'), default='', size=8),
    TextWidget('m_probability', title=MSG(u'Probability'), default='',
               size=2),
    DateWidget('m_deadline', title=MSG(u'Deadline'), default='', size=8),
    SelectRadio('m_status', title=MSG(u'Status'), is_inline=True,
                has_empty_option=False)]

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


############
# Comments #
###########################################################################

class Comments_View(STLView):

    access = 'is_allowed_to_view'
    title = MSG(u'Comments')
    template = '/ui/crm/Comments_view.xml'


    def get_namespace(self, resource, context):
        # Load crm css
        context.add_style('/ui/crm/style.css')
        # Load tracker css
        context.add_style('/ui/tracker/style.css')

        comments_handler = resource.get_resource('comments').handler
        get_record_value = comments_handler.get_record_value

        ns_comments = []
        for record in comments_handler.get_records():
            id = record.id
            comment = get_record_value(record, 'comment')
            comment_datetime = get_record_value(record, 'ts')
            file = get_record_value(record, 'file') or ''
            alert_datetime = get_record_value(record, 'alert_datetime')
            if alert_datetime:
                alert_datetime = format_datetime(alert_datetime)
            ns_comment = {
                'id': id,
                'datetime': format_datetime(comment_datetime),
                'file': str(file),
                'alert_datetime': alert_datetime,
                'comment': indent(comment)}
            ns_comments.append((id, ns_comment))
        # Sort comments
        ns_comments.sort(reverse=True)
        ns_comments = [y for x, y in ns_comments]

        path_to_resource = context.get_link(resource)
        namespace = {'comments': ns_comments,
                     'path_to_resource': path_to_resource}
        return namespace



#######
# CRM #
###########################################################################
class CRM_SearchProspects(SearchForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Search')
    search_template = '/ui/crm/CRM_search.xml'
    template = '/ui/crm/CRM_search_prospects.xml'

    search_schema = {
        'search_field': String,
        'search_term': Unicode,
        'p_status': ProspectStatus(multiple=True),
    }
    search_fields =  [
        ('text', MSG(u'Text')),
    ]

    table_columns = [
        ('icon', None, False),
        ('p_lastname', MSG(u'Lastname'), True),
        ('p_firstname', MSG(u'Firstname'), False),
        ('p_company', MSG(u'Company'), False),
        ('p_email', MSG(u'Email'), False),
        ('p_phone', MSG(u'Phone'), False),
        ('p_mobile', MSG(u'mobile'), False),
        ('p_status', MSG(u'Status'), False),
        ('p_opportunity', MSG(u'Opp.'), True),
        ('p_project', MSG(u'Proj.'), True),
        ('p_nogo', MSG(u'NoGo'), True),
        ('mtime', MSG(u'Last Modified'), True),
        ('assured', MSG(u'Assured'), True),
        ('probable', MSG(u'In pipe'), True)]

    batch_msg1 = MSG(u'1 prospect.')
    batch_msg2 = MSG(u'{n} prospects.')


    def get_items(self, resource, context, *args):
        crm = get_crm(resource)
        crm_path = str(crm.get_abspath())
        # Get the parameters from the query
        query = context.query
        search_term = query['search_term'].strip()
        p_status = query['p_status']

        # Build the query
        args = list(args)
        abspath = str(resource.get_canonical_path())
        args.append(PhraseQuery('format', 'prospect'))
        args.append(get_crm_path_query(crm))
        if search_term:
            args.append(PhraseQuery('text', search_term))
        # Insert status filter
        if p_status:
            status_query = []
            for s in p_status:
                status_query.append(PhraseQuery('p_status', s))
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
        elif column == 'assured':
            value = item_brain.p_assured
            return format_amount(value)
        elif column == 'probable':
            value = item_brain.p_probable
            return format_amount(value)
        if column == 'icon':
            # icon
            path_to_icon = item_resource.get_resource_icon(16)
            if path_to_icon.startswith(';'):
                name = item_brain.name
                path_to_icon = resolve_uri('%s/' % name, path_to_icon)
            return path_to_icon
        get_value = item_resource.get_value
        crm = get_crm(resource)
        if column == 'p_company':
            company = get_value(column)
            company_resource = crm.get_resource('companies/%s' % company)
            href = context.get_link(company_resource)
            title = company_resource.get_title()
            return title, href
        elif column == 'p_lastname':
            href = '%s/' % context.get_link(item_resource)
            return get_value(column), href
        elif column == 'p_firstname':
            href = '%s/' % context.get_link(item_resource)
            return get_value(column), href
        elif column == 'p_phone':
            return get_value(column)
        elif column == 'p_mobile':
            return get_value(column)
        elif column == 'p_email':
            value = get_value(column)
            href = 'mailto:%s' % value
            return value, href
        elif column == 'p_status':
            # Status
            value = get_value(column)
            return ProspectStatus.get_value(value)
        elif column == 'mtime':
            # Last Modified
            accept = context.accept_language
            return format_datetime(item_brain.mtime, accept=accept)
        elif column in ('p_opportunity', 'p_project', 'p_nogo'):
            return getattr(item_brain, column)


    def sort_and_batch(self, resource, context, results):
        start = context.query['batch_start']
        size = context.query['batch_size']
        sort_by = context.query['sort_by']
        if sort_by in ('p_opportunity', 'p_project', 'p_nogo', 'assured',
                       'probable'):
            sort_by = 'p_%s' % sort_by
        reverse = context.query['reverse']

        # Calculate the probable and assured amount
        for brain in results.get_documents():
            self.assured += Decimal.decode(brain.p_assured)
            self.probable += Decimal.decode(brain.p_probable)

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
        p_status = context.query['p_status']
        if not p_status:
            p_status = default_status
        widget = MultipleCheckBoxWidget('p_status', title=MSG(u'Status'))
        ns_status = widget.to_html(ProspectStatus, p_status)
        search_namespace['p_status'] = ns_status

        return search_namespace


    def get_namespace(self, resource, context):
        # Load crm css
        context.add_style('/ui/crm/style.css')

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

class Company_EditForm(AutoForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit company')

    query_schema = schema = {
        'comment': Unicode, 'file': PathDataType,
        'alert_date': Date, 'alert_time': Time,
        'c_title': Unicode(mandatory=True),
        'c_address_1': Unicode, 'c_address_2': Unicode,
        'c_zipcode': String, 'c_town': Unicode,
        'c_country': Unicode,
        'c_phone': Unicode, 'c_fax': Unicode }

    widgets = [
        TextWidget('c_title', title=MSG(u'Title')),
        TextWidget('c_address_1', title=MSG(u'Address')),
        TextWidget('c_address_2', title=MSG(u'Address (next)')),
        TextWidget('c_zipcode', title=MSG(u'Zip Code'), size=10),
        TextWidget('c_town', title=MSG(u'Town')),
        TextWidget('c_country', title=MSG(u'Country')),
        TextWidget('c_phone', title=MSG(u'Phone'), size=15),
        TextWidget('c_fax', title=MSG(u'Fax'), size=15),
        MultilineWidget('comment', title=MSG(u'Comment')) ,
        PathSelectorWidget('file', title=MSG(u'Attachement')),
        DateWidget('alert_date', title=MSG(u'Alert date'), size=10),
        TimeWidget('alert_time', title=MSG(u'Alert time')) ]


    def get_query_schema(self):
        # c_title mandatory only into form
        return merge_dicts(self.query_schema, c_title=Unicode)


    def get_value(self, resource, context, name, datatype):
        # TODO Make alert_date&time empty if we want to use it more than 1 time
        if name == 'alert_date':
            value = resource.get_value('alert_datetime')
            return value.date() if value is not None else datatype.default
        elif name == 'alert_time':
            value = resource.get_value('alert_datetime')
            return value.time() if value is not None else datatype.default
        elif name == 'comment':
            return context.query.get('comment') or u''
        elif name == 'file':
            return context.query.get('file') or ''
        value = resource.get_value(name)
        return value if value is not None else datatype.default


    def action(self, resource, context, form):
        values = {}
        for key, value in form.iteritems():
            if value is None:
                continue
            if key == 'file' and str(value) == '.':
                continue
            if key == 'alert_date':
                value_time = form.get('alert_time', None) or time(9, 0)
                value = datetime.combine(value, value_time)
                values['alert_datetime'] = value
            elif key != 'alert_time':
                values[key] = value
        resource.update(values)



class Company_ViewProspects(CRM_SearchProspects):

    search_template = None

    def get_items(self, resource, context, *args):
        args = list(args)
        args.append(PhraseQuery('p_company', resource.name))
        return CRM_SearchProspects.get_items(self, resource, context, *args)


    def get_namespace(self, resource, context):
        namespace = CRM_SearchProspects.get_namespace(self, resource, context)
        namespace['crm-infos'] = False
        namespace['export-csv'] = False
        return namespace



class Company_View(CompositeForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'View company')
#    template = '/ui/crm/Company_view.xml'

    subviews = [Company_EditForm(), Company_ViewProspects(), Comments_View()]


#############
# Prospects #
###########################################################################

class Prospect_NewInstance(NewInstance):

    access = 'is_allowed_to_add'
    title = MSG(u'New prospect')
    template = '/ui/crm/Prospect_new_instance.xml'
    context_menus = []


    def get_schema(self, resource, context):
        return merge_dicts(prospect_schema, company_schema, mission_schema,
                           action_on_company=String, c_title=Unicode)


    def get_widgets(self, resource, context):
        widgets = prospect_widgets[:] + mission_widgets[:]
        return widgets


    def get_page_title(self, resource, context):
        return None


    def get_value(self, resource, context, name, datatype):
        value = NewInstance.get_value(self, resource, context, name,
                                          datatype)
        if name == 'm_deadline' and value is None:
            year = date.today().year
            return date(year, 12, 31)
        if value is None:
            return datatype.default
        return value


    def _get_form(self, resource, context):
        """ Use the STLForm method to avoid the call of get_new_resource_name
            in NewInstance._get_form
        """
        form = STLForm._get_form(self, resource, context)
        action_on_company = form.get('action_on_company', None)
        p_company = form.get('p_company')
        c_title = form.get('c_title')
        # The company has been selected and already exists
        if not action_on_company and not p_company:
            raise FormError(missing='p_company')
        # This is a new company
        if action_on_company == 'new' and not c_title:
            raise FormError(missing='p_company')
        return form


    def on_form_error(self, resource, context):
        message = format_error_message(context, self.get_widgets(resource,
                                                                 context))
        return context.come_back(message)


    def get_namespace(self, resource, context):
        # Inject specific javascript functions for CRM
        scripts = get_context().scripts
        scripts.append('/ui/crm/javascript.js')

        # Load crm css
        context.add_style('/ui/crm/style.css')

        namespace = NewInstance.get_namespace(self, resource, context)

        # Modify widgets namespace to change template
        for index, widget in enumerate(namespace['widgets']):
            name = self.get_widgets(resource, context)[index].name
            namespace[name] = widget

        return namespace


    def action(self, resource, context, form):
        crm = get_crm(resource)
        prospects = crm.get_resource('prospects')

        # Get approximation of index of current prospect
        results = resource.get_root().search(format='prospect',
                      parent_path=str(prospects.get_abspath()))
        index = len(results)
        names = prospects.get_names()
        name = generate_name(names, 'p%04d', index)

        # Create the resource
        cls_prospect = get_resource_class('prospect')
        child = cls_prospect.make_resource(cls_prospect, prospects, name)

        # Prospect data
        prospect_data = {}
        for key in ['p_company', 'p_lastname', 'p_firstname', 'p_phone',
                    'p_mobile', 'p_email', 'p_description', 'p_status']:
            prospect_data[key] = form.get(key, '')
            child.metadata.set_property(key, prospect_data[key])
        # Company data
        company_data = {}
        for key in ['c_title', 'c_address_1', 'c_address_2', 'c_zipcode',
                    'c_town', 'c_country', 'c_phone', 'c_fax']:
            company_data[key] = form.get(key, None)

        # Add/Update company
        action_on_company = form.get('action_on_company', '')
        if action_on_company == 'new':
            company_name = crm.add_company(company_data)
            child.set_property('p_company', company_name)

        # Add mission
        mission_data = {}
        for key in ['m_title', 'm_description', 'm_amount', 'm_probability',
                    'm_deadline', 'm_status']:
            mission_data[key] = form.get(key, None)
        child.add_mission(mission_data)

        goto = './prospects/%s/' % name
        return context.come_back(MSG_NEW_RESOURCE, goto=goto)



class PMission_NewInstanceForm(NewInstance):

    access = 'is_allowed_to_add'
    title = MSG(u'New mission')
    template = '/ui/crm/Mission_new_instance.xml'

    query_schema = {
        'm_title': Unicode,
        'm_description': Unicode,
        'm_amount': Decimal,
        'm_probability': Integer,
        'm_deadline': Date,
        'm_status': MissionStatus}

    def get_schema(self, resource, context):
        # m_title, m_description et m_status are mandatory
        return merge_dicts(self.query_schema,
                           m_title=Unicode(mandatory=True),
                           m_description=Unicode(mandatory=True),
                           m_status=MissionStatus(mandatory=True))

    widgets = [
        TextWidget('m_title', title=MSG(u'Title')),
        MultilineWidget('m_description', title=MSG(u'Description'), rows=3),
        TextWidget('m_amount', title=MSG(u'Amount'), default='', size=8),
        TextWidget('m_probability', title=MSG(u'Probability'), default='',
                   size=2),
        DateWidget('m_deadline', title=MSG(u'Deadline'), default='', size=8),
        SelectRadio('m_status', title=MSG(u'Status'), is_inline=True,
                    has_empty_option=False)]


    # XXX TODO should go on main or new mission depending on referrer if any
    def on_form_error(self, resource, context):
        """ Go to main view instead of staying on edit_form.
        """
        # FIXME hack to get default query values for view_missions
        query = context.query
        query['batch_start'] = query.get('batch_start', 0)
        query['batch_size'] = query.get('batch_size', 10)
        query['sort_by'] = query.get('sort_by', 'mtime')
        query['reverse'] = query.get('reverse', False)
        message = format_error_message(context, self.get_widgets(resource,
                                                                 context))
        context.message = message
        return resource.main.GET


    def get_value(self, resource, context, name, datatype):
        value = NewInstance.get_value(self, resource, context, name,
                                          datatype)
        if name == 'm_deadline' and value is None:
            year = date.today().year
            return date(year, 12, 31)
        if value is None:
            return datatype.default
        return value


    def _get_form(self, resource, context):
        """ Use the STLForm method to avoid the call of get_new_resource_name
            in NewInstance._get_form
        """
        return STLForm._get_form(self, resource, context)


    def get_namespace(self, resource, context):
        namespace = NewInstance.get_namespace(self, resource, context)

        # Modify widgets namespace to change template
        for index, widget in enumerate(namespace['widgets']):
            name = self.get_widgets(resource, context)[index].name
            namespace[name] = widget

        namespace['action'] = ';new_mission'
        return namespace


    def action(self, resource, context, form):
        title = form['m_title']
        description = form.get('m_description', '')
        amount = form.get('m_amount', '')
        probability = form.get('m_probability', '')
        deadline = form.get('m_deadline', '')
        status = form['m_status']

        resource.add_mission(form)
        # Reindex prospect
        context.server.change_resource(resource)

        goto = context.get_link(resource)
        return context.come_back(MSG_NEW_RESOURCE, goto=goto)



class Prospect_SearchMissions(SearchForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Missions')
    search_template = '/ui/crm/Prospect_search.xml'

    search_schema = {
        'search_field': String,
        'search_term': Unicode,
        'm_status': MissionStatus(multiple=True) }
    search_fields =  [
        ('title', MSG(u'Title')),
        ('text', MSG(u'Text')) ]

    table_columns = [
        ('icon', None, False),
        ('title', MSG(u'Title'), True),
        ('status', MSG(u'Status'), False),
        ('next_action', MSG(u'Next action'), False),
        ('mtime', MSG(u'Last Modified'), True),
        ('amount', MSG(u'Amount'), False),
        ('probability', MSG(u'Probability'), False),
        ('deadline', MSG(u'Deadline'), False) ]

    batch_msg1 = MSG(u'1 mission.')
    batch_msg2 = MSG(u'{n} missions.')


    def get_query_schema(self):
        return merge_dicts(SearchForm.get_query_schema(self),
                           sort_by=String(default='mtime'))


    def get_items(self, resource, context, *args):
        # Get the parameters from the query
        query = context.query
        search_term = query['search_term'].strip()
        field = query['search_field']
        m_status = query['m_status']

        # Build the query
        args = list(args)
        args.append(PhraseQuery('format', 'mission'))
        args.append(PhraseQuery('m_prospect', resource.name))
        missions = resource.parent.parent.get_resource('missions')
        abspath = str(missions.get_canonical_path())
        args.append(PhraseQuery('parent_path', abspath))
        if search_term:
            args.append(PhraseQuery(field, search_term))
        # Insert status filter
        if m_status:
            status_query = []
            for s in m_status:
                status_query.append(PhraseQuery('m_status', s))
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
        if column == 'icon':
            # icon
            path_to_icon = item_resource.get_resource_icon(16)
            if path_to_icon.startswith(';'):
                name = item_brain.name
                path_to_icon = resolve_uri('%s/' % name, path_to_icon)
            return path_to_icon
        # FIXME
        get_value = item_resource.get_value
        if column == 'title':
            # Title
            href = '%s/;main?mission=%s' % (context.get_link(resource),
                                            item_brain.name)
            return get_value('m_title'), href
        elif column == 'status':
            # Status
            return MissionStatus.get_value(get_value('m_status'))
        elif column == 'mtime':
            # Last Modified
            accept = context.accept_language
            return format_datetime(item_brain.mtime, accept=accept)
        elif column == 'amount':
            value = get_value('m_amount')
            if value:
                value = u'%02.02f €' % value
            return value
        elif column == 'probability':
            value = get_value('m_probability')
            return value
        elif column == 'deadline':
            deadline = get_value('m_deadline')
            return deadline
        elif column == 'next_action':
            value = get_value('next_action')
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
        default_status = ['p_opportunity', 'p_project']
        m_status = context.query['m_status']
        if not m_status:
            m_status = default_status
        widget = MultipleCheckBoxWidget('m_status', title=MSG(u'Status'))
        ns_status = widget.to_html(MissionStatus, m_status)
        search_namespace['m_status'] = ns_status

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
        args.append(PhraseQuery('m_prospect', resource.name))
        if len(args) == 1:
            query = args[0]
        else:
            query = AndQuery(*args)
        # Ok
        crm = get_crm(resource)
        base_path_query = get_crm_path_query(crm)
        return context.root.search(AndQuery(query, base_path_query))



class Prospect_EditForm(DBResource_Edit):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit prospect')
    template = '/ui/crm/Prospect_edit.xml'
    submit_value = MSG(u'Update prospect')


    def get_schema(self, resource, context):
        return merge_dicts(prospect_schema, company_schema,
                           action_on_company=String)


    def get_widgets(self, resource, context):
        widgets = prospect_widgets[:]
        return widgets


    def get_value(self, resource, context, name, datatype):
        value = resource.get_value(name)
        return value if value is not None else datatype.default


    def _get_form(self, resource, context):
        form = DBResource_Edit._get_form(self, resource, context)
        action_on_company = form.get('action_on_company', None)
        p_company = form.get('p_company')
        c_title = form.get('c_title')
        # Maybe the company has changed, the value mustn't be empty
        if not action_on_company and not p_company:
            raise FormError(missing='p_company')
        # Edit or New company
        if action_on_company in ('edit', 'new') and not c_title:
            raise FormError(missing='p_company')
        return form


    def on_form_error(self, resource, context):
        """ Go to main view instead of staying on edit_form.
        """
        # FIXME hack to get default query values for view_missions
        query = context.query
        query['batch_start'] = query.get('batch_start', 0)
        query['batch_size'] = query.get('batch_size', 10)
        query['sort_by'] = query.get('sort_by', 'mtime')
        query['reverse'] = query.get('reverse', False)

        message = format_error_message(context, self.get_widgets(resource,
                                                                 context))
        context.message = message
        return resource.main.GET


    def get_namespace(self, resource, context):
        # Inject specific javascript functions for CRM
        scripts = get_context().scripts
        scripts.append('/ui/crm/javascript.js')

        # Load crm css
        context.add_style('/ui/crm/style.css')

        namespace = DBResource_Edit.get_namespace(self, resource, context)

        # Modify widgets namespace to change template
        for index, widget in enumerate(namespace['widgets']):
            name = self.get_widgets(resource, context)[index].name
            namespace[name] = widget

        namespace['action'] = '%s/;edit_form' % context.get_link(resource)

        return namespace


    def action(self, resource, context, form):
        crm = get_crm(resource)

        # Prospect data
        prospect_data = {}
        for key in ['p_company', 'p_lastname', 'p_firstname', 'p_phone',
                    'p_mobile', 'p_email', 'p_description', 'p_status']:
            prospect_data[key] = form.get(key, '')
            # Update prospect
            resource.set_property(key, prospect_data[key])

        # FIXME
        # Company data
        company_data = {}
        for key in ['c_title', 'c_address_1', 'c_address_2', 'c_zipcode',
                    'c_town', 'c_country', 'c_phone', 'c_fax']:
            company_data[key] = form.get(key, None)

        # FIXME
        # Add/Update company
        action_on_company = form.get('action_on_company', None)
        if action_on_company == 'new':
            company_name = crm.add_company(company_data)
            resource.set_property('p_company', company_name)
        elif action_on_company == 'edit':
            path = 'companies/%s' % prospect_data['p_company']
            company = crm.get_resource(path)
            company.update_company(company_data)

        goto = context.get_link(resource)
        return context.come_back(MSG_CHANGES_SAVED, goto)



class Prospect_Main(CompositeForm):
    """ Display edit form and missions below of it.
    """
    access = 'is_allowed_to_edit'
    title = MSG(u'Prospect')
    template = '/ui/crm/Prospect_main.xml'

    subviews = [Prospect_EditForm(), Prospect_ViewMissions()]

    query_schema = {'mission': String}


    def get_page_title(self, resource, context):
        return None


    def get_query_schema(self):
        return merge_dicts(CompositeForm.get_query_schema(self),
                           self.query_schema)


    def get_prospect_title(self, resource, context):
        lastname = resource.get_property('p_lastname')
        firstname = resource.get_property('p_firstname')
        company = resource.get_property('p_company')
        company = resource.get_resource('../../companies/%s' % company,
                                        soft=True)
        if company is not None:
            company =  u'(%s)' % company.get_title()
        else:
            company = ''
        return '%s %s %s' % (lastname, firstname, company)


    def get_namespace(self, resource, context):
        title = self.get_prospect_title(resource, context)
        edit = Prospect_EditForm().GET(resource, context)
        view_missions = Prospect_ViewMissions().GET(resource, context)

        # Add selected mission view if any mission
        edit_mission = None
        mission = context.query.get('mission', None)
        if mission is None:
            mission = resource.get_first_mission(context)
        if mission:
            path_to_mission = '../../missions/%s' % mission
            mission_resource = resource.get_resource(path_to_mission, soft=True)
            if mission_resource is None:
                # FIXME infinite cycle
                return context.come_back(ERROR(u'Mission not found'), goto=';main')
            edit_mission = mission_resource.edit.GET(mission_resource, context)

        namespace = {
            'title': title,
            'edit': edit,
            'view_missions': view_missions,
            'edit_mission': edit_mission }
        return namespace



class PMission_NewInstance(Prospect_Main):
    """ Display edit form and missions below of it in addition to mission form.
    """
    title = MSG(u'New mission')
    template = '/ui/crm/Mission_new.xml'

    subviews = [Prospect_EditForm(),
                Prospect_ViewMissions(),
                PMission_NewInstanceForm()]

    query_schema = {}


    def get_namespace(self, resource, context):
        title = self.get_prospect_title(resource, context)
        edit = Prospect_EditForm().GET(resource, context)
        view_missions = Prospect_ViewMissions().GET(resource, context)
        new_mission = PMission_NewInstanceForm().GET(resource, context)

        return {
            'title': title,
            'edit': edit,
            'view_missions': view_missions,
            'new_mission': new_mission}


############
# Mission #
###########################################################################

class Mission_EditForm(AutoForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit mission')
#    template = '/ui/crm/Mission_edit_form.xml'
    required_msg = None

    query_schema = {
        'm_title': Unicode, 'm_description': Unicode,
        'm_amount': Decimal, 'm_probability': Integer,
        'm_deadline': Date, 'm_status': MissionStatus,
        'comment': Unicode, 'file': PathDataType,
        'alert_date': Date, 'alert_time': Time,
        'm_nextaction': Unicode}

    widgets = [
        TextWidget('m_title', title=MSG(u'Title')),
        MultilineWidget('m_description', title=MSG(u'Description'), rows=3),
        TextWidget('m_amount', title=MSG(u'Amount'), default='', size=8),
        TextWidget('m_probability', title=MSG(u'Probability'), default='',
                   size=2),
        DateWidget('m_deadline', title=MSG(u'Deadline'), default='', size=8),
        SelectRadio('m_status', title=MSG(u'Status'), is_inline=True,
            has_empty_option=False),
        MultilineWidget('comment', title=MSG(u'New comment'), default='',
                        rows=3),
        PathSelectorWidget('file', title=MSG(u'Attachement'), default=''),
        DateWidget('alert_date', title=MSG(u'Alert on'), size=8),
        TimeWidget('alert_time', title=MSG(u'at')),
        TextWidget('m_nextaction', title=MSG(u'Next action')) ]


    def get_schema(self, resource, context):
        # m_title is mandatory
        return merge_dicts(self.query_schema, m_title=Unicode(mandatory=True))


    def get_value(self, resource, context, name, datatype):
        # TODO Make alert_date&time empty if we want to use it more than 1 time
        if name == 'alert_date':
            value = resource.get_value('alert_datetime')
            return value.date() if value is not None else datatype.default
        elif name == 'alert_time':
            value = resource.get_value('alert_datetime')
            return value.time() if value is not None else datatype.default
        elif name == 'comment':
            return context.query.get('comment') or u''
        elif name == 'file':
            return context.query.get('file') or ''
        value = resource.get_value(name)
        return value if value is not None else datatype.default


    # TO CHECK
    ##def _get_form(self, resource, context):
    ##    """ Alert is valid only if date AND time are filled.
    ##    """
    ##    form = STLForm._get_form(self, resource, context)
    ##    alert_date = form.get('alert_date', None)
    ##    alert_time = form.get('alert_time', None)
    ##    # Alerts with time but without date are forbidden
    ##    if alert_time and not alert_date:
    ##        raise FormError, MSG_MISSING_OR_INVALID
    ##    return form


    # TO CHECK
    ##def on_form_error(self, resource, context):
    ##    """ Get back to prospect main view on current mission with error
    ##        message.
    ##    """
    ##    message = format_error_message(context, self.get_widgets(resource,
    ##                                                             context))
    ##    path_to_prospect = context.get_link(resource.parent)
    ##    goto = '%s/;main?mission=%s' % (path_to_prospect, resource.name)
    ##    return context.come_back(message, goto)


    # TO CHECK
    ##def get_namespace(self, resource, context):
    ##    """ Force reinitialization of comment field to '' after a POST.
    ##    """
    ##    namespace = DBResource_Edit.get_namespace(self, resource, context)
    ##    submit = (context.request.method == 'POST')

    ##    # Modify widgets namespace to change template
    ##    for index, widget in enumerate(namespace['widgets']):
    ##        name = self.get_widgets(resource, context)[index].name
    ##        # Reset comment
    ##        if submit and name == 'm_comment':
    ##            widget['value'] = ''
    ##            comment_widget = MultilineWidget('m_comment',
    ##                                 title=MSG(u'Comment'), rows=3)
    ##            widget['widget'] = comment_widget.to_html(Unicode, u'')
    ##        namespace[name] = widget
    ##    namespace['action'] = '%s/;edit_form' % context.get_link(resource)
    ##    return namespace


    def action(self, resource, context, form):
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
        resource.update(values)

        # Reindex prospects to update Opp/Proj/NoGo, p_assured and p_probable
        changed_keys = values.keys()
        if ('m_status' in changed_keys or 'm_probability' in changed_keys \
            or 'm_amount' in changed_keys):
            crm = get_crm(resource)
            prospects = resource.get_value('m_prospect')
            for prospect in prospects:
                prospect = crm.get_resource('prospects/%s' % prospect)
                context.server.change_resource(prospect)



class Mission_ViewProspects(CRM_SearchProspects):

    search_template = None

    def get_items(self, resource, context, *args):
        args = list(args)
        prospects = resource.get_value('m_prospect')
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



class Mission_View(CompositeForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'View mission')
#    template = '/ui/crm/Mission_view.xml'

    subviews = [Mission_EditForm(), Mission_ViewProspects(), Comments_View()]


############
# PMission #
###########################################################################

class PMission_EditForm(DBResource_Edit):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit mission')
    template = '/ui/crm/Mission_edit_form.xml'
    required_msg = None

    query_schema = {
        'm_title': Unicode,
        'm_description': Unicode,
        'm_amount': Decimal,
        'm_probability': Integer,
        'm_deadline': Date,
        'm_status': MissionStatus,
        'm_comment': Unicode,
        'file': String,
        'alert_date': Date,
        'alert_time': Time}

    def get_schema(self, resource, context):
        # m_title and m_comment are mandatory
        return merge_dicts(self.query_schema,
                           m_title=Unicode(mandatory=True),
                           m_comment=Unicode(mandatory=True))

    widgets = [
        TextWidget('m_title', title=MSG(u'Title')),
        MultilineWidget('m_description', title=MSG(u'Description'), rows=3),
        TextWidget('m_amount', title=MSG(u'Amount'), default='', size=8),
        TextWidget('m_probability', title=MSG(u'Probability'), default='',
                   size=2),
        DateWidget('m_deadline', title=MSG(u'Deadline'), default='', size=8),
        SelectRadio('m_status', title=MSG(u'Status'), is_inline=True,
            has_empty_option=False),
        MultilineWidget('m_comment', title=MSG(u'Comment'), default='',
                        rows=3),
        TextWidget('file', title=MSG(u'Attachement'), default=''),
        DateWidget('alert_date', title=MSG(u'Alert on'), size=8),
        TimeWidget('alert_time', title=MSG(u'at'))]


    def get_value(self, resource, context, name, datatype):
        # Always reset m_comment
        if name == 'm_comment':
            return ''
        value = resource.get_value(name)
        return value if value is not None else datatype.default


    def _get_form(self, resource, context):
        """ Alert is valid only if date AND time are filled.
        """
        form = STLForm._get_form(self, resource, context)
        alert_date = form.get('alert_date', None)
        alert_time = form.get('alert_time', None)
        # Alerts with time but without date are forbidden
        if alert_time and not alert_date:
            raise FormError, MSG_MISSING_OR_INVALID
        return form


    def on_form_error(self, resource, context):
        """ Get back to prospect main view on current mission with error
            message.
        """
        message = format_error_message(context, self.get_widgets(resource,
                                                                 context))
        path_to_prospect = context.get_link(resource.parent)
        goto = '%s/;main?mission=%s' % (path_to_prospect, resource.name)
        return context.come_back(message, goto)


    def get_namespace(self, resource, context):
        """ Force reinitialization of comment field to '' after a POST.
        """
        namespace = DBResource_Edit.get_namespace(self, resource, context)
        submit = (context.request.method == 'POST')

        # Modify widgets namespace to change template
        for index, widget in enumerate(namespace['widgets']):
            name = self.get_widgets(resource, context)[index].name
            # Reset comment
            if submit and name == 'm_comment':
                widget['value'] = ''
                comment_widget = MultilineWidget('m_comment',
                                     title=MSG(u'Comment'), rows=3)
                widget['widget'] = comment_widget.to_html(Unicode, u'')
            namespace[name] = widget
        namespace['action'] = '%s/;edit_form' % context.get_link(resource)
        return namespace


    def action(self, resource, context, form):
        title = form['m_title']
        description = form.get('m_description', '')
        amount = form.get('m_amount', '')
        probability = form.get('m_probability', '')
        deadline = form.get('m_deadline', '')
        status = form['m_status']
        comment = form['m_comment']
        alert_date = form.get('alert_date', None)
        alert_time = form.get('alert_time', None)

        # Attachement
        file = form.get('file', '')
        if file:
            # Upload
            filename, mimetype, body = file
            # Find a non used name
            name = checkid(filename)
            name, extension, language = FileName.decode(name)
            name = igenerate_name(name, resource.get_names())
            # Add attachement
            cls = get_resource_class(mimetype)
            cls.make_resource(cls, resource, name, body=body, filename=filename,
                            extension=extension, format=mimetype)
            file = name
        # Alert datetime
        alert_datetime = None
        if alert_date:
            # Default alert time: 9:00
            alert_time = alert_time or time(9,0)
            alert_datetime = datetime.combine(alert_date, alert_time)

        # FIXME
        # Save metadata
        resource.set_property('m_title', title)
        resource.set_property('m_description', description)
        resource.set_property('m_amount', amount)
        resource.set_property('m_probability', probability)
        resource.set_property('m_deadline', deadline)
        resource.set_property('m_status', status)

        # FIXME
        # Add first comment
        comments = resource.get_resource('comments')
        record = {'comment': comment}
        if file:
            record['file'] = file
        if alert_datetime:
            record['alert_datetime'] = alert_datetime
        comments.handler.add_record(record)

        # FIXME
        # Reindex prospect to update p_assured and p_probable
        context.server.change_resource(resource.parent)

        prospect = resource.get_property('m_prospect')
        mission = resource.name
        goto = '../../prospects/%s/;main?mission=%s' % (prospect, mission)
        return context.come_back(MSG_CHANGES_SAVED, goto)



class PMission_Edit(CompositeForm):
    """ Display edit form and comments below of it.
    """
    access = 'is_allowed_to_edit'
    title = MSG(u'Edit mission')
    template = '/ui/crm/Mission_edit.xml'

    subviews = [PMission_EditForm(), Comments_View()]

    def get_action_method(self, resource, context):
        return PMission_EditForm.action


    def get_namespace(self, resource, context):
        title = resource.get_property('m_title')
        edit = PMission_EditForm().GET(resource, context)
        view_comments = Comments_View().GET(resource, context)
        return {
            'title': title,
            'edit': edit,
            'view_comments': view_comments}



class CRM_ExportToCSV(BaseView):

    access = 'is_allowed_to_edit'
    title = MSG(u'Export to CSV')
    query_schema = {'editor': String(default='excel')}


    def get_mission_infos(self, resource, mission):
        infos = []
        prospect = mission.parent
        get_property = prospect.get_property
        # Prospect
        infos.append(get_property('p_lastname'))
        infos.append(get_property('p_firstname') or '')
        p_company = get_property('p_company')
        company = resource.get_resource('companies/%s' % p_company)
        infos.append(company.get_property('c_title'))
        infos.append(get_property('p_status'))

        # Mission
        l = ['m_title', 'm_amount', 'm_probability', 'm_status', 'm_deadline']
        for property in l:
            property = mission.get_property(property)
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
        response = context.response
        response.set_header('Content-Type', 'text/comma-separated-values')
        response.set_header('Content-Disposition',
                            'attachment; filename=export.csv')
        return csv.to_str(separator=separator)



class CRM_Alerts(SearchForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Alerts')
    template = '/ui/crm/CRM_alerts.xml'

    search_schema = {
        'search_field': String,
        'search_term': Unicode,
    }
    search_fields =  []

    schema = {'ids': String(multiple=True, mandatory=True)}

    table_columns = [
        ('checkbox', None, False),
        ('icon', None, False),
        ('alert_date', MSG(u'Date'), False),
        ('alert_time', MSG(u'Time'), False),
        ('p_lastname', MSG(u'Lastname'), False),
        ('p_firstname', MSG(u'Firstname'), False),
        ('p_company', MSG(u'Company'), False),
        ('m_title', MSG(u'Mission'), False),
        ('m_comment', MSG(u'Comment'), False)]

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
        args.append(PhraseQuery('m_has_alerts', True))
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
            prospect = mission.parent
            if not prospect.is_allowed_to_view(user, prospect):
                continue
            # Get alert
            comments_handler = mission.get_resource('comments').handler
            get_record_value = comments_handler.get_record_value
            for record in comments_handler.get_records():
                alert_datetime = get_record_value(record, 'alert_datetime')
                if not alert_datetime:
                    continue
                comment = get_record_value(record, 'comment')
                items.append((alert_datetime, comment, mission, record.id))

        return items


    def get_item_value(self, resource, context, item, column):
        alert_datetime, comment, mission, comment_id = item
        if column == 'checkbox':
            prospect_name = mission.parent.name
            alert_id = '%s__%s__%d' % (prospect_name, mission.name, comment_id)
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
            return path_to_icon
        elif column in ('p_lastname', 'p_firstname'):
            prospect = mission.parent
            value = prospect.get_property(column)
            if prospect.is_allowed_to_edit(context.user, mission):
                href = context.get_link(prospect)
                return value, href
            return value
        elif column == 'p_company':
            prospect = mission.parent
            company_name = prospect.get_property(column)
            company = resource.get_resource('companies/%s' % company_name)
            title = company.get_title()
            return title
        elif column == 'm_title':
            value = mission.get_property(column)
            prospect = mission.parent
            if prospect.is_allowed_to_edit(context.user, mission):
                href = context.get_link(prospect)
                href = '%s/;main?mission=%s' % (href, mission.name)
                return value, href
            return value
        elif column == 'alert_date':
            alert_date = alert_datetime.date()
            return format_date(alert_date)
        elif column == 'alert_time':
            alert_time = alert_datetime.time()
            return Time.encode(alert_time)
        elif column == 'm_comment':
            return comment


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


    def get_namespace(self, resource, context):
        # Load crm css
        context.add_style('/ui/crm/style.css')

        namespace = SearchForm.get_namespace(self, resource, context)
        return namespace


    def action_remove(self, resource, context, form):
        not_removed = []
        for alert_id in form.get('ids', []):
            try:
                prospect_name, mission_name, comment_id = alert_id.split('__')
                comment_id = int(comment_id)
            except ValueError:
                not_removed.append(alert_id)
                continue
            # Remove alert_datetime
            prospect = resource.get_resource(prospect_name)
            mission = prospect.get_resource(mission_name)
            comments_handler = mission.get_resource('comments').handler
            comments_handler.update_record(comment_id, alert_datetime=None)

        if not_removed:
            msg = ERROR(u'One or more alert could not have been removed.')
        else:
            msg = MSG_CHANGES_SAVED

        context.message = msg

