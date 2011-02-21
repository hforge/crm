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
from itools.core import freeze, merge_dicts
from itools.datatypes import DateTime, Unicode

# Import from ikaaro
from ikaaro.registry import register_resource_class

# Import from crm
from mission import Mission


comment_datatype = Mission.class_schema['comment']


class MissionUpdate(Mission):
    class_schema = freeze(merge_dicts(
        Mission.class_schema,
        comment=comment_datatype(parameters_schema=merge_dicts(
            comment_datatype.parameters_schema,
            alert_datetime=DateTime,
            crm_m_nextaction=Unicode))))


    def update_20100927(self):
        comments = self.metadata.get_property('comment') or []
        # Migrate alert
        for comment in reversed(comments):
            alert = comment.get_parameter('alert_datetime')
            if alert:
                self.set_property('crm_m_alert', alert)
        # Migrate next action
        for comment in reversed(comments):
            nextaction = comment.get_parameter('crm_m_nextaction')
            if nextaction:
                self.set_property('crm_m_nextaction', nextaction)
        # Remove parameters
        for comment in comments:
            comment.set_parameter('alert_datetime', None)
            comment.set_parameter('crm_m_nextaction', None)
        # Save
        self.metadata.set_property('comment', comments)



register_resource_class(MissionUpdate)
