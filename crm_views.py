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
from itools.core import merge_dicts, freeze
from itools.database import AndQuery, OrQuery, PhraseQuery
from itools.datatypes import Boolean, Decimal, String
from itools.gettext import MSG
from itools.handlers.utils import transmap
from itools.i18n import format_datetime
from itools.web import STLView, get_context

# Import from ikaaro
from ikaaro.autoform import TextWidget, SelectWidget
from ikaaro.views import SearchForm

# Import from itws
from itws.tags import TagsList

# Import from crm
from base_views import m_status_icons, p_status_icons, format_amount
from csv import CSV_Export
from datatypes import MissionStatus, MissionStatusShortened, ContactStatus
from datatypes import AssignedList
from utils import get_crm, get_crm_path_query
from widgets import MultipleCheckboxWidget


ALERT_ICON_PAST = '/ui/crm/icons/16x16/bell_notification.png'
ALERT_ICON_NOW = '/ui/crm/icons/16x16/bell_error.png'
ALERT_ICON_FUTURE = '/ui/crm/icons/16x16/bell_go.png'

TWO_LINES = MSG(u'{one}<br/>{two}', format='replace_html')

STATUS_ICON = MSG(u'<img src="{icon}" title="{title}"/>',
        format='replace_html')


def two_lines(one, two):
    return TWO_LINES.gettext(one=one, two=two)


phone_messages = {
    'crm_p_phone': MSG(u"{phone}"),
    'crm_p_mobile': MSG(u"Mobile:\u00a0{phone}"),
    'crm_c_phone': MSG(u"{phone}"),
    'crm_c_fax': MSG(u"Fax:\u00a0{phone}")}

def get_phones(brain, *fields):
    phones = []
    for field in fields:
        value = getattr(brain, field)
        if not value:
            continue
        message = phone_messages[field]
        phones.append(message.gettext(phone=value))
    if not phones:
        return None
    return MSG(u"<br/>".join(phones), format='html')


def merge_columns(brain, *fields):
    address = []
    for field in fields:
        value = getattr(brain, field)
        if not value:
            continue
        if field == 'crm_p_lastname':
            value = value.upper()
        address.append(value)
    if not address:
        return None
    return MSG(u"<br/>".join(address), format='html')


def get_name(brain):
    return merge_columns(brain, 'crm_p_lastname', 'crm_p_firstname')



class CRM_Search(CSV_Export, SearchForm):
    access = 'is_allowed_to_edit'
    query_schema = freeze(merge_dicts(
        SearchForm.query_schema,
        sort_by=String(default='mtime'),
        reverse=Boolean(default=True),
        tags=TagsList))
    styles = ['/ui/crm/style.css']
    template = '/ui/crm/crm/search.xml'

    search_fields = freeze([
        ('text', MSG(u'Text'))])


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
        # Full-text search
        namespace['search_term'] = TextWidget('search_term', size=20,
                value=context.query['search_term'])
        # Tags
        namespace['tags'] = SelectWidget('tags', title=MSG(u"Tag"),
                datatype=TagsList, value=context.query['tags'])
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
        elif column == 'icon':
            return item_resource.get_class_icon()
        elif column == 'title':
            href = context.get_link(item_resource)
            return item_brain.title, href
        elif column == 'mtime':
            accept = context.accept_language
            return format_datetime(item_brain.mtime, accept=accept)
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



class CRM_SearchMissions(CRM_Search):
    title = MSG(u'Missions')
    query_schema = freeze(merge_dicts(
        CRM_Search.query_schema,
        sort_by=String(default='icon'),
        reverse=Boolean(default=False)))

    search_template = '/ui/crm/crm/search_missions.xml'
    search_schema = freeze(merge_dicts(
        CRM_Search.search_schema,
        assigned=AssignedList,
        status=MissionStatus(multiple=True)))
    search_format = 'mission'

    table_columns = freeze([
        ('icon', MSG(u" "), True),
        ('crm_m_alert_datetime', MSG(u"Alert"), True),
        ('status', MSG(u" "), True),
        ('title', MSG(u'Mission'), True),
        ('crm_m_nextaction', MSG(u'Next Action'), True),
        ('contacts', MSG(u'Contacts'), True),
        ('company', MSG(u'Company'), True),
        ('assigned', MSG(u'Assigned To'), True),
        ('mtime', MSG(u'Last Modified'), True)])
    table_actions = freeze([])

    csv_columns = freeze([
        ('crm_m_alert_datetime', MSG(u"Alert")),
        ('crm_m_status', MSG(u"Status")),
        ('title', MSG(u'Mission')),
        ('crm_m_nextaction', MSG(u'Next Action')),
        ('contacts_csv', MSG(u'Contacts')),
        ('company', MSG(u'Company')),
        ('assigned', MSG(u'Assigned To')),
        ('mtime', MSG(u'Last Modified'))])
    csv_filename = 'missions.csv'

    batch_msg1 = MSG(u'1 mission.')
    batch_msg2 = MSG(u'{n} missions.')


    def get_search_namespace(self, resource, context):
        proxy = super(CRM_SearchMissions, self)
        namespace = proxy.get_search_namespace(resource, context)

        # Assigned
        datatype = self.search_schema['assigned'](resource=resource)
        namespace['assigned'] = SelectWidget('assigned', datatype=datatype,
                title=MSG(u"Assigned To"), value=context.query['assigned'])
        # Status
        default_status = ['opportunity', 'project']
        m_status = context.query['status']
        if not m_status:
            m_status = default_status
        namespace['status'] = MultipleCheckboxWidget('status',
                title=MSG(u'Status'), datatype=MissionStatusShortened,
                value=m_status)

        return namespace


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


    def get_key_sorted_by_icon(self):
        today = date.today()
        def key(item):
            alert_datetime = item.crm_m_alert_datetime
            # No alert
            if alert_datetime is None:
                return (3, None)
            alert_date = alert_datetime.date()
            # Present
            if alert_date == today:
                return (0, alert_datetime)
            # Future
            if alert_date > today:
                return (1, alert_datetime)
            # Past
            return (2, alert_datetime)
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
        if column == 'icon':
            alert_datetime = item_brain.crm_m_alert_datetime
            if alert_datetime is None:
                return None
            elif alert_datetime.date() < date.today():
                return ALERT_ICON_PAST
            elif alert_datetime < datetime.now():
                return ALERT_ICON_NOW
            return ALERT_ICON_FUTURE
        elif column == 'crm_m_alert_datetime':
            alert_datetime = item_brain.crm_m_alert_datetime
            if alert_datetime:
                return alert_datetime.date()
            return None
        elif column == 'status':
            # Status
            m_status = item_brain.crm_m_status
            icon = m_status_icons[m_status]
            title = MissionStatusShortened.get_value(m_status)
            return STATUS_ICON(icon=icon, title=title)
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



class CRM_SearchContacts(CRM_Search):
    title = MSG(u'Contacts')
    template = '/ui/crm/crm/contacts.xml'

    search_template = '/ui/crm/crm/search_contacts.xml'
    search_schema = freeze(merge_dicts(
        CRM_Search.search_schema,
        status=ContactStatus(multiple=True)))
    search_format = 'contact'

    table_columns = freeze([
        ('icon', None, False),
        ('title', MSG(u'Contact'), True),
        ('company', MSG(u'Company'), False),
        ('email', MSG(u'Email'), False),
        ('phones', MSG(u'Phone'), False),
        ('crm_p_position', MSG(u'Position'), False),
        ('crm_p_opportunity', MSG(u'Opp.'), True),
        ('crm_p_project', MSG(u'Proj.'), True),
        ('crm_p_nogo', MSG(u'NoGo'), True),
        ('crm_p_assured', MSG(u'Assured'), True),
        ('crm_p_probable', MSG(u'In pipe'), True),
        ('mtime', MSG(u'Last Modified'), True)])

    csv_columns = freeze([
        ('crm_p_lastname', MSG(u"Last Name")),
        ('crm_p_firstname', MSG(u"First Name")),
        ('company', MSG(u"Company")),
        ('crm_p_status', MSG(u"Status")),
        ('crm_p_email', MSG(u"E-mail")),
        ('crm_m_title', MSG(u"Mission")),
        ('crm_m_amount', MSG(u"Amount")),
        ('crm_m_probability', MSG(u"Probability")),
        ('crm_m_status', MSG(u"Status")),
        ('crm_m_deadline', MSG(u"Deadline"))])
    csv_filename = 'contacts.csv'

    batch_msg1 = MSG(u'1 contact.')
    batch_msg2 = MSG(u'{n} contacts.')


    def get_search_namespace(self, resource, context):
        proxy = super(CRM_SearchContacts, self)
        namespace = proxy.get_search_namespace(resource, context)

        # Add status
        default_status = ['lead', 'client']
        p_status = context.query['status']
        if not p_status:
            p_status = default_status
        namespace['status'] = MultipleCheckboxWidget('status',
                title=MSG(u'Status'), datatype=ContactStatus, value=p_status)

        return namespace


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
        if column == 'icon':
            # Status
            return p_status_icons[item_brain.crm_p_status]
        elif column == 'title':
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
            return get_phones(item_brain, 'crm_p_phone', 'crm_p_mobile')
        elif column == 'crm_p_assured':
            value = item_brain.crm_p_assured
            accept = context.accept_language
            return format_amount(value, accept)
        elif column == 'crm_p_probable':
            value = item_brain.crm_p_probable
            accept = context.accept_language
            return format_amount(value, accept)
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
            self.assured += Decimal.decode(brain.crm_p_assured)
            self.probable += Decimal.decode(brain.crm_p_probable)

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

        accept = context.accept_language
        namespace['assured'] = format_amount(self.assured, accept)
        namespace['probable'] = format_amount(self.probable, accept)
        namespace['total'] = format_amount(total, accept)
        namespace['crm-infos'] = True

        return namespace



class CRM_SearchCompanies(CRM_Search):
    title = MSG(u'Companies')

    search_template = '/ui/crm/crm/search_companies.xml'
    search_format = 'company'

    table_columns = [
        ('icon', None, False),
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
        if column == 'icon':
            logo = item_brain.crm_c_logo
            if not logo or logo == '.':
                return proxy.get_item_value(resource, context, item, column,
                        cache={})
            return context.get_link(item_resource.get_resource(logo))
        elif column == 'address':
            return merge_columns(item_brain, 'crm_c_address_1',
                    'crm_c_address_2', 'crm_c_zipcode', 'crm_c_town',
                    'crm_c_country')
        elif column == 'phones':
            return get_phones(item_brain, 'crm_c_phone', 'crm_c_fax')
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
