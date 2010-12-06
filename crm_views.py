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
from itools.core import merge_dicts
from itools.csv import CSVFile
from itools.database import AndQuery, OrQuery, PhraseQuery
from itools.datatypes import Boolean, Decimal, String
from itools.gettext import MSG
from itools.i18n import format_datetime, format_date
from itools.ical import Time
from itools.uri import resolve_uri
from itools.web import BaseView
from itools.web import ERROR

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



class CRM_SearchMissions(SearchForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Missions')
    search_template = '/ui/crm/crm/search.xml'
    styles = ['/ui/crm/style.css']

    search_schema = merge_dicts(SearchForm.search_schema,
        status=MissionStatus(multiple=True),
        with_no_alert=Boolean)
    search_fields =  [
        ('text', MSG(u'Text')), ]

    table_columns = [
        ('icon', None, False),
        ('title', MSG(u'Title'), True),
        ('crm_m_contacts', MSG(u'Contacts'), False),
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
        search_term = query['search_term'].strip()
        m_status = query['status']
        with_no_alert = query['with_no_alert']

        # Build the query
        args = list(args)
        abspath = str(resource.get_canonical_path())
        args.append(PhraseQuery('format', 'mission'))
        args.append(get_crm_path_query(crm))
        if search_term:
            args.append(PhraseQuery('text', search_term))
        # Insert status filter
        if m_status:
            status_query = []
            for s in m_status:
                status_query.append(PhraseQuery('crm_m_status', s))
            args.append(OrQuery(*status_query))
        # Insert with_no_alert filter
        if with_no_alert:
            args.append(PhraseQuery('crm_m_has_alerts', False))
        query = AndQuery(*args)

        # Ok
        return context.root.search(query)


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
        elif column == 'title':
            href = context.get_link(item_resource)
            return item_brain.title, href
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
        elif column == 'mtime':
            # Last Modified
            accept = context.accept_language
            return format_datetime(item_brain.mtime, accept=accept)
        elif column in ('crm_m_amount', 'crm_m_probability',
                'crm_m_deadline'):
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



class CRM_SearchContacts(SearchForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Contacts')
    search_template = '/ui/crm/crm/search.xml'
    template = '/ui/crm/crm/search_contacts.xml'
    styles = ['/ui/crm/style.css']

    search_schema = merge_dicts(SearchForm.search_schema,
        status=ContactStatus(multiple=True))
    search_fields =  [
        ('text', MSG(u'Text')), ]

    table_columns = [
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
        ('mtime', MSG(u'Last Modified'), True)]

    batch_msg1 = MSG(u'1 contact.')
    batch_msg2 = MSG(u'{n} contacts.')


    def get_items(self, resource, context, *args):
        crm = get_crm(resource)
        crm_path = str(crm.get_abspath())
        # Get the parameters from the query
        query = context.query
        search_term = query['search_term'].strip()
        p_status = query['status']

        # Build the query
        args = list(args)
        abspath = str(resource.get_canonical_path())
        args.append(PhraseQuery('format', 'contact'))
        args.append(get_crm_path_query(crm))
        if search_term:
            args.append(PhraseQuery('text', search_term))
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
            accept = context.accept_language
            return format_amount(value, accept)
        elif column == 'crm_p_probable':
            value = item_brain.crm_p_probable
            accept = context.accept_language
            return format_amount(value, accept)
        get_property = item_resource.get_property
        if column == 'icon':
            # Status
            value = get_property('crm_p_status')
            return p_status_icons[value]
        elif column == 'crm_p_company':
            company = get_property(column)
            if company:
                crm = get_crm(resource)
                company_resource = crm.get_resource('companies/%s' % company)
                href = context.get_link(company_resource)
                title = company_resource.get_title()
                return title, href
            else:
                return u''
        elif column == 'crm_p_lastname':
            href = '%s/' % context.get_link(item_resource)
            return get_property(column), href
        elif column == 'crm_p_firstname':
            href = '%s/' % context.get_link(item_resource)
            return get_property(column), href
        elif column in ('crm_p_phone', 'crm_p_mobile'):
            return get_property(column)
        elif column == 'crm_p_email':
            value = get_property(column)
            href = 'mailto:%s' % value
            return value, href
        elif column == 'mtime':
            # Last Modified
            accept = context.accept_language
            return format_datetime(item_brain.mtime, accept=accept)
        elif column in ('crm_p_opportunity', 'crm_p_project', 'crm_p_nogo'):
            return getattr(item_brain, column)


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



class CRM_ExportToCSV(BaseView):

    access = 'is_allowed_to_edit'
    title = MSG(u'Export to CSV')
    query_schema = {'editor': String(default='excel')}


    def get_mission_infos(self, resource, mission):
        infos = []
        contact = mission.get_property('crm_m_contact')[0]
        contact = resource.get_resource('contacts/%s' % contact)
        get_property = contact.get_property
        # Contact
        infos.append(get_property('crm_p_lastname'))
        infos.append(get_property('crm_p_firstname') or '')
        p_company = get_property('crm_p_company')
        if p_company:
            company = resource.get_resource('companies/%s' % p_company)
            infos.append(company.get_property('title'))
        infos.append(get_property('crm_p_status'))

        # Mission
        for name in ('title', 'crm_m_amount', 'crm_m_probability',
                'crm_m_status', 'crm_m_deadline'):
            value = mission.get_property(name) or u''
            infos.append(value)
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
            'lastname', 'firstname', 'company', "contact's status",
            "mission's title", 'amount', 'probability', "mission's status",
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
    template = '/ui/crm/crm/alerts.xml'
    styles = ['/ui/crm/style.css']

    schema = {'ids': String(multiple=True, mandatory=True)}

    table_columns = [
        ('checkbox', None, False),
        ('icon', None, False),
        ('alert_date', MSG(u'Date'), False),
        ('alert_time', MSG(u'Time'), False),
        ('crm_p_lastname', MSG(u'Last name'), False),
        ('crm_p_firstname', MSG(u'First name'), False),
        ('crm_p_company', MSG(u'Company'), False),
        ('title', MSG(u'Mission'), False),
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
        elif column in ('crm_p_lastname', 'crm_p_firstname'):
            contact_id = mission.get_property('crm_m_contact')[0]
            contact = resource.get_resource('contacts/%s' % contact_id)
            value = contact.get_property(column)
            if mission.is_allowed_to_edit(context.user, mission):
                href = context.get_link(contact)
                return value, href
            return value
        elif column == 'crm_p_company':
            contact = mission.get_property('crm_m_contact')[0]
            contact = resource.get_resource('contacts/%s' % contact)
            company_name = contact.get_property(column)
            company = mission.get_resource('../../companies/%s' % company_name)
            title = company.get_title()
            return title
        elif column == 'title':
            value = mission.get_property(column)
            if mission.is_allowed_to_edit(context.user, mission):
                href = context.get_link(mission)
                return value, href
            return value
        elif column == 'alert_date':
            alert_date = alert_datetime.date()
            accept = context.accept_language
            return format_date(alert_date, accept=accept)
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
