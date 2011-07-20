# -*- coding: UTF-8 -*-
# Copyright (C) 2011 Sylvain Taverne <sylvain@itaapy.com>
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

# Import from standard library
from datetime import date, datetime, time

# Import from itools
from itools.core import freeze
from itools.datatypes import Date, URI
from itools.gettext import MSG

# Import from ikaaro
from ikaaro.autoform import ImageSelectorWidget, DateWidget, TextWidget

# Import from itws
from itws.datatypes import TimeWithoutSecond
from itws.tags import TagsList
from itws.widgets import DualSelectWidget


class TagsAware_Edit(object):
    """Mixin to merge with the TagsAware edit view.
    """
    # Little optimisation not to compute the schema too often
    keys = ['tags', 'pub_datetime', 'pub_date', 'pub_time']
    # Publication datetime is not mandatory
    pub_datetime_mandatory = False

    def _get_schema(self, resource, context):
        pdm = self.pub_datetime_mandatory
        return freeze({
            'tags': TagsList(multiple=True, states=[]),
            'pub_date': Date(mandatory=pdm),
            'pub_time': TimeWithoutSecond(mandatory=pdm),
            'thumbnail': URI(multilingual=True)})


    def _get_widgets(self, resource, context):
        return freeze(
            [DualSelectWidget('tags', title=MSG(u'Tags'), is_inline=True,
                              has_empty_option=False),
             ImageSelectorWidget('thumbnail', title=MSG(u'Thumbnail')),
             DateWidget('pub_date',
                        title=MSG(u'Publication date (used by RSS and tags)')),
             TextWidget('pub_time', tip=MSG(u'hour:minute'), size=5,
                        maxlength=5,
                        title=MSG(u'Publication time (used by RSS and tags)'))])


    def get_value(self, resource, context, name, datatype):
        if name == 'tags':
            tags = resource.get_property('tags')
            # tuple -> list (enumerate.get_namespace expects list)
            return list(tags)
        elif name in ('pub_date', 'pub_time'):
            pub_datetime = resource.get_property('pub_datetime')
            if pub_datetime is None:
                return None
            pub_datetime = context.fix_tzinfo(pub_datetime)
            if name == 'pub_date':
                return date(pub_datetime.year, pub_datetime.month,
                            pub_datetime.day)
            else:
                return time(pub_datetime.hour, pub_datetime.minute)


    def set_value(self, resource, context, name, form):
        if name == 'tags':
            resource.set_property('tags', form['tags'])
        elif name in ('pub_date', 'pub_time'):
            pub_date = form['pub_date']
            pub_time = form['pub_time']
            if pub_date:
                dt_kw = {}
                if pub_time:
                    dt_kw = {'hour': pub_time.hour,
                             'minute': pub_time.minute}
                dt = datetime(pub_date.year, pub_date.month, pub_date.day,
                              **dt_kw)
                dt = context.fix_tzinfo(dt)
                resource.set_property('pub_datetime', dt)
            else:
                resource.del_property('pub_datetime')
        return False
