# -*- coding: UTF-8 -*-
# Copyright (C) 2010 Nicolas Deram <nicolas@itaapy.com>
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

# Import from itools
from itools.core import merge_dicts, freeze
from itools.csv import Table as TableFile
from itools.datatypes import Date, DateTime, Decimal, Email, Integer
from itools.datatypes import PathDataType, String, Unicode
from itools.gettext import MSG

# Import from ikaaro
from ikaaro.registry import register_resource_class
from ikaaro.table import Table

# Import from crm
from mission import Mission
from contact import Contacts, Contact
from datatypes import CompanyName, MissionStatus, ContactStatus
from company import Company


def update_default_language(resource):
    site_root = resource.get_site_root()
    default_language = site_root.get_default_language()

    for name in ('title', 'description'):
        value = resource.get_property(name)
        resource.del_property(name)
        resource.set_property(name, value, language=default_language)



class CommentsTableFile(TableFile):
    """ Base comments table used by Company, Contact and Mission.
    """
    record_properties = {'comment': Unicode(mandatory=True),
                         'alert_datetime': DateTime,
                         'file': PathDataType }


    def _add_record(self, values):
        """ Get non set data from previous record.
        """
        last_record = self.get_record(-1)
        values_keys = values.keys()
        for key in self.record_properties.keys():
            if key in ('file', 'alert_datetime'):
                continue
            if key not in values_keys:
                values[key] = self.get_record_value(last_record, key)

        self.add_record(values)


###################################
# Mission                         #
###################################

class MissionTableFile(CommentsTableFile):

    record_properties = merge_dicts(CommentsTableFile.record_properties,
            # Mission title and description
            m_title=Unicode,
            m_description=Unicode,
            # Contact name
            m_prospect=String(multiple=True),
            # How many € ?
            m_amount=Decimal,
            m_probability=Integer,
            m_deadline=Date,
            # Opportunity/Project/NoGo
            m_status=MissionStatus,
            # Next action
            m_nextaction=Unicode)



class MissionTable(Table):

    class_id = 'mission-comments'
    class_title = MSG(u'Mission Comments')
    class_handler = MissionTableFile



class OldMission(Mission):
    class_schema = freeze(merge_dicts(
        Mission.class_schema,
        crm_m_prospect=String(source='metadata', indexed=True,
            multiple=True)))


    def update_20100926(self):
        update_default_language(self)



###################################
# Contact                        #
###################################

class ContactTableFile(CommentsTableFile):

    record_properties = merge_dicts(CommentsTableFile.record_properties,
        p_company=CompanyName,
        p_lastname=Unicode,
        p_firstname=Unicode,
        p_phone=Unicode,
        p_mobile=Unicode,
        p_email=Email,
        p_position=Unicode,
        p_description=Unicode,
        # Lead/Client/Dead
        p_status=ContactStatus)



class ContactTable(Table):

    class_id = 'prospect-comments'
    class_title = MSG(u'Contact Comments')
    class_handler = ContactTableFile



class Prospects(Contacts):
    class_id = 'prospects'



class Prospect(Contact):
    class_id = 'prospect'

    class_schema_extensible = True # CRM.update_20100920



class OldContact(Contact):

    def update_20100924(self):
        update_default_language(self)



###################################
# Company                         #
###################################

class CompanyTableFile(CommentsTableFile):

    record_properties = merge_dicts(CommentsTableFile.record_properties,
        c_title=Unicode, c_address_1=Unicode, c_address_2=Unicode,
        c_zipcode=String, c_town=Unicode, c_country=Unicode,
        c_phone=Unicode, c_fax=Unicode, c_website=Unicode,
        c_description=Unicode, c_activity=Unicode, c_logo=PathDataType)



class CompanyTable(Table):

    class_id = 'company-comments'
    class_title = MSG(u'Company Comments')
    class_handler = CompanyTableFile



class OldCompany(Company):
    class_schema = freeze(merge_dicts(
        Company.class_schema,
        c_address_1=Unicode(source='metadata'),
        c_address_2=Unicode(source='metadata'),
        c_zipcode=String(source='metadata'),
        c_town=Unicode(source='metadata'),
        c_country=Unicode(source='metadata'),
        c_phone=Unicode(source='metadata'),
        c_fax=Unicode(source='metadata'),
        c_website=Unicode(source='metadata'),
        c_activity=Unicode(source='metadata'),
        c_logo=PathDataType(source='metadata', default='.')))


    def update_20100913(self):
        """c_xxx -> crm_c_xxx"""
        for key in ('c_address_1', 'c_address_2', 'c_zipcode', 'c_town',
                'c_country', 'c_phone', 'c_fax', 'c_website', 'c_activity',
                'c_logo'):
            value = self.get_property(key)
            self.set_property('crm_%s' % key, value)
            self.del_property(key)


    def update_20100916(self):
        update_default_language(self)



register_resource_class(OldCompany)
register_resource_class(OldMission)
register_resource_class(OldContact)
register_resource_class(Prospects)
register_resource_class(Prospect)
