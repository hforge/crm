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
from datetime import date, time, datetime, timedelta
from decimal import Decimal as dec

# Import from itools
from itools.core import merge_dicts, freeze, thingy_property
from itools.database import AndQuery, OrQuery, PhraseQuery
from itools.datatypes import Boolean, String, Integer, Date
from itools.gettext import MSG
from itools.handlers.utils import transmap
from itools.stl import STLTemplate
from itools.web import STLView, get_context, INFO

# Import from ikaaro
from ikaaro.autoform import TextWidget, SelectWidget, DateWidget
from ikaaro.buttons import Button, BrowseButton
from ikaaro.utils import make_stl_template
from ikaaro.views import SearchForm

# Import from itws
from itws.tags import TagsList

# Import from crm
from base_views import Icon, ShortStatusIcon, AlertIcon, PhoneIcon
from base_views import format_amount
from csv import CSV_Export
from datatypes import MissionStatusShortened, ContactStatus
from datatypes import AssignedList
from utils import get_crm, get_crm_path_query
from widgets import MultipleCheckboxWidget


MSG_MISSIONS_POSTPONED = INFO(u"Missions postponed to {postpone}: "
        u"{missions}.", format='replace_html')


class Phones(STLTemplate):
    template = make_stl_template('''
        <div stl:repeat="phone phones">${phone/icon}${phone/value}</div>''')
    
    def __init__(cls, brain, *fields):
        cls.brain = brain
        cls.fields = fields


    def phones(cls):
        phones = []
        for field in cls.fields:
            value = getattr(cls.brain, field)
            if not value:
                continue
            phones.append({
                'icon': PhoneIcon(field, css="nofloat"),
                'value': value.replace(u" ", u"\u00a0")})
        return phones



class SplitLines(STLTemplate):
    template = make_stl_template('''
        <stl:block stl:repeat="line address">${line}<br/></stl:block>''')

    def __init__(cls, brain, *fields):
        cls.brain = brain
        cls.fields = fields


    def address(cls):
        address = []
        for field in cls.fields:
            value = getattr(cls.brain, field)
            if not value:
                continue
            if field == 'crm_p_lastname':
                value = value.upper()
            address.append(value)
        return address



def get_name(brain):
    return SplitLines(brain, 'crm_p_lastname', 'crm_p_firstname')



class SearchButton(Button):
    access = 'is_allowed_to_view'
    css = 'button-search'



class CRM_Search(CSV_Export, SearchForm):
    access = 'is_allowed_to_edit'
    query_schema = freeze(merge_dicts(
        SearchForm.query_schema,
        sort_by=String(default='mtime'),
        reverse=Boolean(default=True),
        tags=TagsList))
    styles = ['/ui/crm/style.css']
    template = '/ui/crm/crm/search.xml'

    search_template = '/ui/crm/crm/search_tabular.xml'
    search_fields = freeze([
        ('text', MSG(u'Text'))])
    search_schema = freeze(merge_dicts(
        SearchForm.search_schema,
        tags=TagsList))
    search_widgets = freeze([
        TextWidget('search_term', title=MSG(u"Search Term"), size=20),
        SelectWidget('tags', title=MSG(u"Tag"))])
    search_action = SearchButton


    def _get_query(self, resource, context, *args):
        crm = get_crm(resource)
        search_term = context.query['search_term'].strip()
        tags = context.query['tags']

        # Build the query
        args = list(args)
        args.append(PhraseQuery('format', self.search_format))
        args.append(get_crm_path_query(crm))
        if search_term:
            args.append(PhraseQuery('text', search_term))
        if tags:
            args.append(PhraseQuery('tags', tags))

        return AndQuery(*args)


    def get_search_namespace(self, resource, context):
        namespace = {}
        widgets = []
        for widget in self.search_widgets:
            name = widget.name
            widget = widget(datatype=self.search_schema[name],
                    value=context.query[name])
            widgets.append(widget)
        namespace['widgets'] = widgets
        namespace['action'] = self.search_action(resource=resource,
                context=context)
        return namespace


    def get_namespace(self, resource, context):
        return merge_dicts(
            SearchForm.get_namespace(self, resource, context),
            CSV_Export.get_namespace(self, resource, context))


    def get_items(self, resource, context, *args):
        query = self._get_query(resource, context, *args)
        return context.root.search(query)


    def get_item_value(self, resource, context, item, column, cache={}):
        item_brain, item_resource = item
        if column == 'checkbox':
            return item_brain.name, False
        elif column == 'sprite':
            return Icon(name=item_brain.sprite16)
        elif column == 'title':
            href = context.get_link(item_resource)
            return item_brain.title, href
        elif column == 'mtime':
            return context.format_datetime(item_brain.mtime)
        try:
            return getattr(item_brain, column)
        except AttributeError:
            return item_resource.get_property(column)


    def sort_and_batch(self, resource, context, results):
        start = context.query['batch_start']
        size = context.query['batch_size']
        sort_by = context.query['sort_by']
        reverse = context.query['reverse']

        if sort_by is None:
            get_key = None
        else:
            get_key = getattr(self, 'get_key_sorted_by_' + sort_by, None)
        if get_key is not None:
            items = results.get_documents()
            items.sort(key=get_key(), reverse=reverse)
            if size:
                items = items[start:start+size]
            elif start:
                items = items[start:]
        else:
            items = results.get_documents(sort_by=sort_by, reverse=reverse,
                    start=start, size=size)

        return [(x, resource.get_resource(x.abspath)) for x in items]


    def get_table_titles(self, resource, context):
        table_columns = self.get_table_columns(resource, context)
        titles = {}
        for name, title, sortable in table_columns:
            if title is None:
                title = name
            else:
                title = title.gettext()
            titles[name] = title
        return titles



class PostponeAlerts(DateWidget, BrowseButton):
    access = 'is_allowed_to_edit'
    template = (make_stl_template('''
        Postpone selected alerts to''')
        + DateWidget.template
        + BrowseButton.template)
    name = 'postpone'
    title = MSG(u"Postpone")
    css = 'button-calendar'
    confirm = MSG(u"Are you sure you want to postpone the selected alerts?")


    @thingy_property
    def value_(cls):
        return str(date.today() + timedelta(days=1))



class CRM_SearchMissions(CRM_Search):
    title = MSG(u'Missions')
    query_schema = freeze(merge_dicts(
        CRM_Search.query_schema,
        batch_size=Integer(default=100),
        sort_by=String(default='alert'),
        reverse=Boolean(default=False)))

    search_schema = freeze(merge_dicts(
        CRM_Search.search_schema,
        assigned=AssignedList,
        status=MissionStatusShortened(multiple=True,
            default=['opportunity', 'project'])))
    search_widgets = freeze(
            CRM_Search.search_widgets[:1]
            + [SelectWidget('assigned', title=MSG(u"Assigned To")),
                MultipleCheckboxWidget('status', title=MSG(u'Status'))]
            + CRM_Search.search_widgets[1:])
    search_format = 'mission'

    table_columns = freeze([
        ('checkbox', None, False),
        ('alert', MSG(u" "), True),
        ('crm_m_alert', MSG(u"Alert"), True),
        ('status', MSG(u" "), True),
        ('title', MSG(u'Mission'), True),
        ('crm_m_nextaction', MSG(u'Next Action'), True),
        ('contacts', MSG(u'Contacts'), True),
        ('company', MSG(u'Company'), True),
        ('assigned', MSG(u'Assigned To'), True),
        ('mtime', MSG(u'Last Modified'), True)])
    table_actions = freeze([
        PostponeAlerts])

    action_postpone_schema = freeze({
        'ids': String(multiple=True, mandatory=False),
        'postpone': Date(mandatory=False)})

    csv_columns = freeze([
        ('crm_m_alert', MSG(u"Alert")),
        ('crm_m_status', MSG(u"Status")),
        ('crm_m_amount', MSG(u"Amount")),
        ('crm_m_probability', MSG(u"Probability")),
        ('title', MSG(u'Mission')),
        ('crm_m_nextaction', MSG(u'Next Action')),
        ('contacts_csv', MSG(u'Contacts')),
        ('company', MSG(u'Company')),
        ('assigned', MSG(u'Assigned To')),
        ('mtime', MSG(u'Last Modified'))])
    csv_filename = 'missions.csv'

    batch_msg1 = MSG(u'1 mission.')
    batch_msg2 = MSG(u'{n} missions.')


    def get_items(self, resource, context, *args):
        query = self._get_query(resource, context, *args)
        # Assigned to
        assigned = context.query['assigned']
        if assigned:
            if assigned == AssignedList.NOT_ASSIGNED:
                assigned = ''
            query = AndQuery(query, PhraseQuery('crm_m_assigned', assigned))
        # Insert status filter
        m_status = context.query['status']
        if m_status:
            status_query = []
            for s in m_status:
                status_query.append(PhraseQuery('crm_m_status', s))
            query = AndQuery(query, OrQuery(*status_query))
        # Ok
        return context.root.search(query)


    def get_key_sorted_by_alert(self):
        today = date.today()
        def key(item):
            alert = item.crm_m_alert
            # No alert
            if alert is None:
                return (3, None)
            alert_date = alert.date()
            # Present
            if alert_date == today:
                return (0, alert)
            # Future
            if alert_date > today:
                return (1, alert)
            # Past
            return (2, alert)
        return key


    def get_key_sorted_by_status(self):
        def key(item):
            return item.crm_m_status
        return key


    def get_key_sorted_by_title(self):
        def key(item):
            return item.title.lower().translate(transmap)
        return key


    def get_key_sorted_by_nextaction(self):
        def key(item):
            return item.crm_m_nextaction.lower().translate(transmap)
        return key


    def get_key_sorted_by_contacts(self):
        context = get_context()
        contacts = context.resource.get_resource('contacts')
        def key(item, cache={}):
            m_contacts = tuple(item.crm_m_contact)
            if m_contacts not in cache:
                value = None
                for m_contact in m_contacts:
                    contact = contacts.get_resource(m_contact)
                    value = contact.get_title().lower().translate(transmap)
                    break
                cache[m_contacts] = value
            return cache[m_contacts]
        return key


    def get_key_sorted_by_company(self):
        context = get_context()
        contacts = context.resource.get_resource('contacts')
        companies = context.resource.get_resource('companies')
        def key(item, cache={}):
            m_contacts = tuple(item.crm_m_contact)
            if m_contacts not in cache:
                value = None
                for m_contact in m_contacts:
                    contact = contacts.get_resource(m_contact)
                    p_company = contact.get_property('crm_p_company')
                    company = companies.get_resource(p_company)
                    value = company.get_title().lower().translate(transmap)
                    break
                cache[m_contacts] = value
            return cache[m_contacts]
        return key


    def get_key_sorted_by_assigned(self):
        context = get_context()
        get_user_title = context.root.get_user_title
        def key(item, cache={}):
            assigned = item.crm_m_assigned
            if assigned not in cache:
                cache[assigned] = get_user_title(assigned)
            return cache[assigned]
        return key


    def get_item_value(self, resource, context, item, column, cache={}):
        item_brain, item_resource = item
        if column == 'checkbox':
            parent = item_resource.parent
            if parent is None:
                return None
            if item_resource.name in parent.__fixed_handlers__:
                return None
            id = resource.get_canonical_path().get_pathto(item_brain.abspath)
            id = str(id)
            return id, False
        elif column == 'alert':
            alert = item_brain.crm_m_alert
            if alert is None:
                return None
            elif alert.date() < date.today():
                return AlertIcon(name='past')
            elif alert < datetime.now():
                return AlertIcon(name='now')
            return AlertIcon(name='future')
        elif column == 'crm_m_alert':
            alert = item_brain.crm_m_alert
            if alert:
                return alert.date()
            return None
        elif column == 'status':
            # Status
            return ShortStatusIcon(name=item_brain.crm_m_status)
        elif column in ('contacts', 'contacts_csv'):
            m_contacts = item_brain.crm_m_contact
            query = [PhraseQuery('name', name) for name in m_contacts]
            if len(query) == 1:
                query = query[0]
            else:
                query = OrQuery(*query)
            crm = get_crm(resource)
            query = AndQuery(get_crm_path_query(crm), query)
            query = AndQuery(PhraseQuery('format', 'contact'), query)
            results = context.root.search(query)
            if column == 'contacts':
                pattern = u'<a href="{link}">{lastname}<br/>{firstname}</a>'
            else:
                pattern = u"{lastname} {firstname}"
            names = []
            for brain in results.get_documents(sort_by='crm_p_lastname'):
                link = context.get_link(brain)
                lastname = brain.crm_p_lastname.upper()
                firstname = brain.crm_p_firstname
                names.append(pattern.format(link=link, lastname=lastname,
                    firstname=firstname))
            if column == 'contacts':
                return MSG(u"<br/>".join(names), format='html')
            return u"\n".join(names)
        elif column == 'company':
            contact_id = item_brain.crm_m_contact[0]
            contact = resource.get_resource('contacts/' + contact_id)
            p_company = contact.get_property('crm_p_company')
            if not p_company:
                return u""
            company = resource.get_resource('companies/' + p_company)
            title = company.get_title()
            href = context.get_link(company)
            return title, href
        elif column == 'assigned':
            user_id = item_brain.crm_m_assigned
            return context.root.get_user_title(user_id)
        return super(CRM_SearchMissions, self).get_item_value(resource,
                context, item, column, cache=cache)


    def action_postpone(self, resource, context, form):
        postpone = form['postpone']
        alert = datetime.combine(postpone, time(9, 0))
        pattern = MSG(u'<a href="{path}">{title}</a>', format='replace')
        missions = []
        for path in form['ids']:
            mission = resource.get_resource(path)
            mission.set_property('crm_m_alert', alert)
            missions.append(pattern.gettext(path=path,
                title=mission.get_title()))

        postpone = context.format_date(postpone)
        missions = u", ".join(missions)
        context.message = MSG_MISSIONS_POSTPONED(postpone=postpone,
                missions=missions)



class CRM_SearchContacts(CRM_Search):
    title = MSG(u'Contacts')
    template = '/ui/crm/crm/contacts.xml'

    search_template = '/ui/crm/crm/search_linear.xml'
    search_schema = freeze(merge_dicts(
        CRM_Search.search_schema,
        status=ContactStatus(multiple=True, default=['lead', 'client'])))
    search_widgets = freeze(
            CRM_Search.search_widgets[:1]
            + [MultipleCheckboxWidget('status', title=MSG(u'Status'))]
            + CRM_Search.search_widgets[1:])
    search_format = 'contact'

    table_columns = freeze([
        ('sprite', None, False),
        ('title', MSG(u'Contact'), True),
        ('company', MSG(u'Company'), False),
        ('email', MSG(u'E-mail Address'), False),
        ('phones', MSG(u'Phone'), False),
        ('crm_p_position', MSG(u'Position'), False),
        ('crm_p_opportunity', MSG(u'Opp.'), True),
        ('crm_p_project', MSG(u'Proj.'), True),
        ('crm_p_nogo', MSG(u'NoGo'), True),
        ('crm_p_assured', MSG(u'Assured'), True),
        ('crm_p_probable', MSG(u'In pipe'), True),
        ('mtime', MSG(u'Last Modified'), True)])

    csv_columns = freeze([
        # Not translated for Gmail
        ('crm_p_lastname', u"Last Name"),
        ('crm_p_firstname', u"First Name"),
        ('company', u"Company"),
        ('crm_p_email', u"E-mail Address"),
        ('crm_p_phone', u"Business Phone"),
        ('crm_p_mobile', u"Mobile Phone"),
        ('crm_m_title', MSG(u"Mission")),
        ('crm_m_amount', MSG(u"Amount")),
        ('crm_m_probability', MSG(u"Probability")),
        ('crm_m_status', MSG(u"Status")),
        ('crm_m_deadline', MSG(u"Deadline"))])
    csv_filename = 'contacts.csv'

    batch_msg1 = MSG(u'1 contact.')
    batch_msg2 = MSG(u'{n} contacts.')


    def get_items(self, resource, context, *args):
        query = self._get_query(resource, context, *args)
        # Insert status filter
        p_status = context.query['status']
        if p_status:
            status_query = []
            for s in p_status:
                status_query.append(PhraseQuery('crm_p_status', s))
            query = AndQuery(query, OrQuery(*status_query))
        # Ok
        return context.root.search(query)


    def get_item_value(self, resource, context, item, column, cache={}):
        item_brain, item_resource = item
        if column == 'title':
            value = get_name(item_brain)
            href = '%s/' % context.get_link(item_resource)
            return value, href
        elif column == 'company':
            p_company = item_brain.crm_p_company
            if not p_company:
                return u''
            crm = get_crm(resource)
            company = crm.get_resource('companies/' + p_company)
            href = context.get_link(company)
            title = company.get_title()
            return title, href
        elif column == 'email':
            value = item_brain.crm_p_email
            href = 'mailto:%s' % value
            return value, href
        elif column == 'phones':
            return Phones(item_brain, 'crm_p_phone', 'crm_p_mobile')
        elif column == 'crm_p_assured':
            value = item_brain.crm_p_assured
            return format_amount(value, context)
        elif column == 'crm_p_probable':
            value = item_brain.crm_p_probable
            return format_amount(value, context)
        elif column.startswith('crm_m_'):
            # CSV export
            contact_name = item_brain.name
            mission_brain = cache.get(contact_name)
            if mission_brain is None:
                crm = get_crm(resource)
                query = AndQuery(
                        get_crm_path_query(crm),
                        PhraseQuery('format', 'mission'),
                        PhraseQuery('crm_m_contact', item_brain.name))
                results = context.root.search(query)
                last_missions = results.get_documents(sort_by='mtime',
                        reverse=True, size=1)
                if not last_missions:
                    return None
                mission_brain = cache[contact_name] = last_missions[0]
            if column == 'crm_m_title':
                column = 'title'
            return getattr(mission_brain, column)
        proxy = super(CRM_SearchContacts, self)
        return proxy.get_item_value(resource, context, item, column,
                cache=cache)


    def sort_and_batch(self, resource, context, results):
        # Calculate the probable and assured amount
        for brain in results.get_documents():
            self.assured += brain.crm_p_assured
            self.probable += brain.crm_p_probable

        proxy = super(CRM_SearchContacts, self)
        return proxy.sort_and_batch(resource, context, results)


    def get_namespace(self, resource, context):
        self.assured = dec('0.0')
        self.probable = dec('0.0')
        proxy = super(CRM_SearchContacts, self)
        namespace = proxy.get_namespace(resource, context)
        # Add infos about assured and probable amount
        # TODO Filter by year or semester
        total = self.assured + self.probable

        namespace['assured'] = format_amount(self.assured, context)
        namespace['probable'] = format_amount(self.probable, context)
        namespace['total'] = format_amount(total, context)
        namespace['crm-infos'] = True

        return namespace



class CRM_SearchCompanies(CRM_Search):
    title = MSG(u'Companies')

    search_template = '/ui/crm/crm/search_linear.xml'
    search_format = 'company'

    table_columns = [
        ('sprite', None, False),
        ('title', MSG(u'Company'), True),
        ('address', MSG(u'Address'), True),
        ('phones', MSG(u'Phone'), True),
        ('website', MSG(u'Website'), True),
        ('crm_c_activity', MSG(u'Activity'), True),
        ('mtime', MSG(u'Last Modified'), True)]

    csv_columns = freeze([
        ('title', MSG(u"Company")),
        ('crm_c_address_1', MSG(u"Address 1")),
        ('crm_c_address_2', MSG(u"Address 2")),
        ('crm_c_zipcode', MSG(u"Zip Code")),
        ('crm_c_town', MSG(u"Town")),
        ('crm_c_country', MSG(u"Country")),
        ('crm_c_phone', MSG(u"Phone")),
        ('crm_c_fax', MSG(u"Fax")),
        ('crm_c_website', MSG(u"Website")),
        ('crm_c_activity', MSG(u"Activity"))])
    csv_filename = 'companies.csv'

    batch_msg1 = MSG(u'1 company.')
    batch_msg2 = MSG(u'{n} companies.')


    def get_item_value(self, resource, context, item, column, cache={}):
        proxy = super(CRM_SearchCompanies, self)
        item_brain, item_resource = item
        if column == 'address':
            return SplitLines(item_brain, 'crm_c_address_1',
                    'crm_c_address_2', 'crm_c_zipcode', 'crm_c_town',
                    'crm_c_country')
        elif column == 'phones':
            return Phones(item_brain, 'crm_c_phone', 'crm_c_fax')
        elif column == 'website':
            value = item_brain.crm_c_website
            if value == 'http://':
                return None
            return value, value
        return proxy.get_item_value(resource, context, item, column,
                cache=cache)



class CRM_Test(STLView):
    access = 'is_admin'
    template = '/ui/crm/crm/test.xml'


    def test_contact_without_companies(self, resource, context):
        root = context.root
        query = AndQuery(get_crm_path_query(resource),
                PhraseQuery('format', 'contact'),
                PhraseQuery('crm_p_company', ''))
        results_ = root.search(query)
        results = []
        for brain in results_.get_documents(sort_by='name'):
            contact = root.get_resource(brain.abspath)
            results.append({
                'title': contact.get_title(),
                'href': context.get_link(contact)})
        return {'title': u"Contacts sans société",
                'results': results}


    def test_mission_without_contact(self, resource, context):
        root = context.root
        query = AndQuery(get_crm_path_query(resource),
                PhraseQuery('format', 'mission'),
                PhraseQuery('crm_m_contact', ''))
        results_ = root.search(query)
        results = []
        for brain in results_.get_documents(sort_by='name'):
            mission = root.get_resource(brain.abspath)
            results.append({
                'title': mission.get_title(),
                'href': context.get_link(mission)})
        return {'title': u"Missions sans contact",
                'results': results}


    def get_namespace(self, resource, context):
        namespace = {}

        tests = []
        # FIXME introspect self
        for name in ('test_contact_without_companies',
                'test_mission_without_contact'):
            if name.startswith('test_'):
                test = getattr(self, name)(resource, context)
                test['name'] = name
                test['size'] = len(test['results'])
                tests.append(test)
        namespace['tests'] = tests

        return namespace
