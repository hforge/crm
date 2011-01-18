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
from datetime import datetime, date
from decimal import Decimal as decimal

# Import from itools
from itools.core import merge_dicts, freeze
from itools.csv import CSVFile
from itools.database import AndQuery, OrQuery, PhraseQuery
from itools.datatypes import Boolean, Decimal, String, Integer
from itools.gettext import MSG
from itools.i18n import format_datetime, format_date
from itools.ical import Time
from itools.uri import resolve_uri
from itools.web import BaseView, STLView, ERROR

# Import from ikaaro
from ikaaro.autoform import CheckboxWidget
from ikaaro.buttons import RemoveButton
from ikaaro.messages import MSG_CHANGES_SAVED
from ikaaro.views import SearchForm

# Import from crm
from base_views import m_status_icons, p_status_icons, format_amount
from base_views import REMOVE_ALERT_MSG
from datatypes import MissionStatus, ContactStatus
from utils import get_crm, get_crm_path_query
from widgets import MultipleCheckboxWidget


ALERT_ICON_RED = '1240913145_preferences-desktop-notification-bell.png'
ALERT_ICON_ORANGE = '1240913150_bell_error.png'
ALERT_ICON_GREEN = '1240913156_bell_go.png'

TWO_LINES = MSG(u'{one}<br/>{two}', format='replace_html')


def two_lines(one, two):
    return TWO_LINES.gettext(one=one, two=two)



class CRM_Search(SearchForm):
    access = 'is_allowed_to_edit'
    search_template = '/ui/crm/crm/search.xml'
    styles = ['/ui/crm/style.css']

    search_fields = [
        ('text', MSG(u'Text'))]


    def _get_query(self, resource, context, *args):
        crm = get_crm(resource)
        search_term = context.query['search_term'].strip()

        # Build the query
        args = list(args)
        args.append(PhraseQuery('format', self.format))
        args.append(get_crm_path_query(crm))
        if search_term:
            args.append(PhraseQuery('text', search_term))

        return AndQuery(*args)


    def get_items(self, resource, context, *args):
        query = self._get_query(resource, context, *args)
        return context.root.search(query)


    def get_item_value(self, resource, context, item, column):
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

        items = results.get_documents(sort_by=sort_by, reverse=reverse,
                                      start=start, size=size)
        return [(x, resource.get_resource(x.abspath)) for x in items]



class CRM_SearchMissions(CRM_Search):
    title = MSG(u'Missions')
    search_template = '/ui/crm/crm/search_missions.xml'
    format = 'mission'

    search_schema = freeze(merge_dicts(
        SearchForm.search_schema,
        status=MissionStatus(multiple=True),
        with_no_alert=Boolean))

    table_columns = freeze([
        ('icon', None, False),
        ('title', MSG(u'Title'), True),
        ('crm_m_contacts', MSG(u'Contacts'), False),
        ('crm_m_nextaction', MSG(u'Next action'), True),
        ('mtime', MSG(u'Last Modified'), True),
        ('crm_m_amount', MSG(u'Amount'), False),
        ('crm_m_probability', MSG(u'Prob.'), False),
        ('crm_m_deadline', MSG(u'Deadline'), False)])

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
            value=with_no_alert, oneline=True)
        search_namespace['with_no_alert'] = widget.render()

        return search_namespace


    def get_items(self, resource, context, *args):
        query = self._get_query(resource, context, *args)
        # Insert status filter
        m_status = context.query['status']
        if m_status:
            status_query = []
            for s in m_status:
                status_query.append(PhraseQuery('crm_m_status', s))
            query = AndQuery(query, OrQuery(*status_query))
        # Insert with_no_alert filter
        with_no_alert = context.query['with_no_alert']
        if with_no_alert:
            query = AndQuery(query, PhraseQuery('crm_m_has_alerts', False))
        # Ok
        return context.root.search(query)


    def get_item_value(self, resource, context, item, column):
        item_brain, item_resource = item
        get_property = item_resource.get_property
        if column == 'icon':
            # Status
            value = get_property('crm_m_status')
            return m_status_icons[value]
        elif column == 'crm_m_contacts':
            values = get_property('crm_m_contact')
            query = [PhraseQuery('name', name) for name in values]
            if len(query) == 1:
                query = query[0]
            else:
                query = OrQuery(*query)
            crm = get_crm(resource)
            query = AndQuery(get_crm_path_query(crm), query)
            query = AndQuery(PhraseQuery('format', 'contact'), query)
            values = context.root.search(query).get_documents()
            return u' '.join([x.crm_p_lastname for x in values])
        elif column == 'crm_m_nextaction':
            return item_resource.find_next_action()
        return super(CRM_SearchMissions, self).get_item_value(resource,
                context, item, column)



class CRM_SearchContacts(CRM_Search):
    title = MSG(u'Contacts')
    template = '/ui/crm/crm/search_contacts.xml'
    format = 'contact'

    search_schema = freeze(merge_dicts(
        SearchForm.search_schema,
        status=ContactStatus(multiple=True)))

    table_columns = freeze([
        ('icon', None, False),
        ('crm_p_lastname', MSG(u'Last name'), True),
        ('crm_p_firstname', MSG(u'First name'), False),
        ('crm_p_company', MSG(u'Company'), False),
        ('crm_p_email', MSG(u'Email'), False),
        ('crm_p_phone', MSG(u'Phone'), False),
        ('crm_p_mobile', MSG(u'Mobile'), False),
        ('crm_p_position', MSG(u'Position'), False),
        ('crm_p_opportunity', MSG(u'Opp.'), True),
        ('crm_p_project', MSG(u'Proj.'), True),
        ('crm_p_nogo', MSG(u'NoGo'), True),
        ('crm_p_assured', MSG(u'Assured'), True),
        ('crm_p_probable', MSG(u'In pipe'), True),
        ('mtime', MSG(u'Last Modified'), True)])

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


    def get_item_value(self, resource, context, item, column):
        item_brain, item_resource = item
        get_property = item_resource.get_property
        if column == 'icon':
            # Status
            value = get_property('crm_p_status')
            return p_status_icons[value]
        elif column == 'crm_p_lastname':
            href = '%s/' % context.get_link(item_resource)
            return get_property(column), href
        elif column == 'crm_p_firstname':
            href = '%s/' % context.get_link(item_resource)
            return get_property(column), href
        elif column == 'crm_p_company':
            company = get_property(column)
            if not company:
                return u''
            crm = get_crm(resource)
            company_resource = crm.get_resource('companies/%s' % company)
            href = context.get_link(company_resource)
            title = company_resource.get_title()
            return title, href
        elif column == 'crm_p_email':
            value = get_property(column)
            href = 'mailto:%s' % value
            return value, href
        elif column == 'crm_p_assured':
            value = item_brain.crm_p_assured
            accept = context.accept_language
            return format_amount(value, accept)
        elif column == 'crm_p_probable':
            value = item_brain.crm_p_probable
            accept = context.accept_language
            return format_amount(value, accept)
        return super(CRM_SearchContacts, self).get_item_value(resource,
                context, item, column)


    def sort_and_batch(self, resource, context, results):
        # Calculate the probable and assured amount
        for brain in results.get_documents():
            self.assured += Decimal.decode(brain.crm_p_assured)
            self.probable += Decimal.decode(brain.crm_p_probable)

        return super(CRM_SearchContacts, self).sort_and_batch(resource,
                context, results)


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
                datatype=ContactStatus, value=p_status)
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

        accept = context.accept_language
        namespace['assured'] = format_amount(self.assured, accept)
        namespace['probable'] = format_amount(self.probable, accept)
        namespace['total'] = format_amount(total, accept)
        namespace['crm-infos'] = True
        namespace['export-csv'] = True
        return namespace



class CRM_SearchCompanies(CRM_Search):
    title = MSG(u'Companies')
    format = 'company'

    table_columns = [
        ('icon', None, False),
        ('title', MSG(u'Title'), True),
        ('address', MSG(u'Address'), True),
        ('phones', MSG(u'Phones'), True),
        ('website', MSG(u'Website'), True),
        ('crm_c_activity', MSG(u'Activity'), True),
        ('mtime', MSG(u'Last Modified'), True)]

    batch_msg1 = MSG(u'1 company.')
    batch_msg2 = MSG(u'{n} companies.')


    def get_item_value(self, resource, context, item, column):
        proxy = super(CRM_SearchCompanies, self)
        item_brain, item_resource = item
        get_property = item_resource.get_property
        if column == 'icon':
            logo = get_property('crm_c_logo')
            if not logo or logo == '.':
                return proxy.get_item_value(resource, context, item, column)
            return context.get_link(item_resource.get_resource(logo))
        elif column == 'address':
            address = []
            for field in ('crm_c_address_1', 'crm_c_address_2',
                    'crm_c_zipcode', 'crm_c_town', 'crm_c_country'):
                value = get_property(field)
                if value:
                    address.append(value)
            if not address:
                return None
            address = u"<br/>".join(address)
            return MSG(address, format='html')
        elif column == 'phones':
            phones = []
            for message, field in [
                    (u"Phone:\u00a0{0}", 'crm_c_phone'),
                    (u"Fax:\u00a0{0}", 'crm_c_fax')]:
                value = get_property(field).replace(u" ", u"\u00a0")
                if value:
                    phones.append(message.format(value))
            if not phones:
                return None
            phones = u"<br/>".join(phones)
            return MSG(phones, format='html')
        elif column == 'website':
            website = get_property('crm_c_website')
            if website == 'http://':
                return None
            return website, website
        return proxy.get_item_value(resource, context, item, column)



class CRM_ExportToCSV(BaseView):

    access = 'is_allowed_to_edit'
    title = MSG(u'Export to CSV')
    query_schema = freeze({
        'editor': String(default='excel')})


    def get_contact_infos(self, resource, contact):
        infos = []
        get_property = contact.get_property
        # Contact
        infos.append(get_property('crm_p_lastname'))
        infos.append(get_property('crm_p_firstname') or u"")
        p_company = get_property('crm_p_company')
        if p_company:
            company = resource.get_resource('companies/%s' % p_company)
            infos.append(company.get_property('title'))
        else:
            infos.append(u"")
        infos.append(get_property('crm_p_status'))
        infos.append(get_property('crm_p_email'))
        return infos


    def get_mission_infos(self, resource, mission):
        contact = mission.get_property('crm_m_contact')[0]
        contact = resource.get_resource('contacts/%s' % contact)
        infos = self.get_contact_infos(resource, contact)
        # Mission
        l = ['title', 'crm_m_amount', 'crm_m_probability', 'crm_m_status',
                'crm_m_deadline']
        for property in l:
            property = mission.get_property(property)
            infos.append(property or u'')
        else:
            infos.append(u'')
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
            'lastname', 'firstname', 'company', 'contact status', 'email',
            'mission title', 'amount', 'probability', 'mission status',
            'deadline'])
        missions = [resource.get_resource(m.abspath) for m in missions]
        # Contacts without mission
        contacts_names = set(
                m.get_property('crm_m_contact')[0] for m in missions)
        query = PhraseQuery('format', 'contact')
        results = context.root.search(AndQuery(query, base_path_query))
        contacts = results.get_documents()
        contacts = [p for p in contacts if p.name not in contacts_names]

        infos = [self.get_mission_infos(resource, m) for m in missions]
        infos.extend(self.get_contact_infos(resource,
                resource.get_resource(p.abspath))
            for p in contacts)

        # Fill the CSV
        for info in infos:
            row = []
            for value in info:
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
    template = '/ui/crm/crm/alerts.xml'
    styles = ['/ui/crm/style.css']

    query_schema = freeze(merge_dicts(
        SearchForm.query_schema,
        batch_size=Integer(default=0)))
    schema = freeze({
        'ids': String(multiple=True, mandatory=True)})

    table_columns = freeze([
        ('checkbox', None, False),
        ('icon', None, False),
        ('alert_datetime', MSG(u'Date'), False),
        ('contact', MSG(u'Contact'), False),
        ('company', MSG(u'Company'), False),
        ('mission', MSG(u'Mission'), False),
        ('nextaction', MSG(u'Next action'), False),
        ('assigned', MSG(u'Assigned to'), False)])

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
        query = AndQuery(*args)

        items = []
        # Check each mission to get only alerts
        crm = get_crm(resource)
        base_path_query = get_crm_path_query(crm)
        results = context.root.search(AndQuery(query, base_path_query))
        for doc in results.get_documents():
            mission = resource.get_resource(doc.abspath)
            # Check access FIXME should be done in catalog
            if not mission.is_allowed_to_view(user, mission):
                continue
            # Get alert
            comments = mission.metadata.get_property('comment') or []
            for comment_id, comment in enumerate(comments):
                alert_datetime = comment.get_parameter('alert_datetime')
                if not alert_datetime:
                    continue
                m_nextaction = comment.get_parameter('crm_m_nextaction')
                items.append((alert_datetime, m_nextaction, mission,
                    comment_id))

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
        elif column == 'alert_datetime':
            alert_date = alert_datetime.date()
            accept = context.accept_language
            alert_date = format_date(alert_date, accept=accept)
            alert_time = alert_datetime.time()
            alert_time = Time.encode(alert_time)
            return two_lines(alert_date, alert_time)
        elif column == 'contact':
            contact_id = mission.get_property('crm_m_contact')[0]
            contact = resource.get_resource('contacts/' + contact_id)
            lastname = contact.get_property('crm_p_lastname').upper()
            firstname = contact.get_property('crm_p_firstname')
            value = two_lines(lastname, firstname)
            if mission.is_allowed_to_edit(context.user, mission):
                href = context.get_link(contact)
                return value, href
            return value
        elif column == 'company':
            contact_id = mission.get_property('crm_m_contact')[0]
            contact = resource.get_resource('contacts/' + contact_id)
            company_id = contact.get_property('crm_p_company')
            if not company_id:
                return u""
            company = mission.get_resource('../../companies/' + company_id)
            title = company.get_title()
            href = context.get_link(company)
            return title, href
        elif column == 'mission':
            value = mission.get_property('title')
            if mission.is_allowed_to_edit(context.user, mission):
                href = context.get_link(mission)
                return value, href
            return value
        elif column == 'nextaction':
            return m_nextaction
        elif column == 'assigned':
            user_id = mission.get_property('crm_m_assigned')
            return context.root.get_user_title(user_id)
        raise ValueError, column


    def sort_and_batch(self, resource, context, results):
        results.sort()

        items, past, future = [], [], []
        today = date.today()
        for result in results:
            alert_datetime, m_nextaction, mission, comment_id = result
            alert_date = alert_datetime.date()
            if alert_date < today:
                # Past alerts at the bottom
                past.append(result)
            elif alert_date == today:
                # Today alerts at the top
                items.append(result)
            else:
                # Future alerts between
                future.append(result)
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
            comments[comment_id].set_parameter('alert_datetime', None)
            mission.set_property('comment', comments)

        if not_removed:
            msg = ERROR(u'One or more alert could not have been removed.')
        else:
            msg = MSG_CHANGES_SAVED

        context.message = msg



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
