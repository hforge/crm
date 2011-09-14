# -*- coding: UTF-8 -*-
# Copyright (C) 2007-2008 Henry Obein <henry@itaapy.com>
# Copyright (C) 2008-2010 Nicolas Deram <nicolas@itaapy.com>
# Copyright (C) 2010 Hervé Cauwelier <herve@itaapy.com>
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
from itools.core import thingy_lazy_property

# Import from ikaaro
from ikaaro.autoform import CheckboxWidget, SelectWidget, TextWidget
from ikaaro.autoform import make_stl_template


class MultipleCheckboxWidget(CheckboxWidget):

    template = make_stl_template("""
        <stl:inline stl:repeat="item items">
          <input type="checkbox" name="${name}" value="${item/name}"
            checked="${item/selected}" />${item/value}</stl:inline>""")

    def items(self):
        items = []
        for option in self.datatype.get_options():
            name = option['name']
            items.append({
                'name': name,
                'value': option['value'],
                'selected': name in self.value})
        return items


class SelectCompanyWidget(SelectWidget):

    template = make_stl_template("""
        <select id="${id}" name="${name}" multiple="${multiple}" size="${size}"
            class="${css}">
          <option value="" stl:if="has_empty_option"></option>
          <option stl:repeat="option options" value="${option/name}"
            selected="${option/selected}">${option/value}</option>
        </select>""")


class EmailWidget(TextWidget):

    template = make_stl_template("""
           <input type="${type}" id="${id}" name="${name}" value="${value}"
             size="${size}" /><a stl:if="value" href="mailto:${value}">
             <img src="/ui/icons/16x16/mail.png" /></a>""")


class LinkWidget(TextWidget):

    template = make_stl_template("""
           <input type="${type}" id="${id}" name="${name}" value="${value}"
             size="${size}" /><a stl:if="value" href="${value}"
             target="_blank"><img src="/ui/icons/16x16/website.png" /></a> """)

    @thingy_lazy_property
    def value_(self):
        value = self.value
        if 'http://' not in value and 'https://' not in value:
            value = 'http://%s' % value
        return value


class NewCompanyWidget(TextWidget):

    template = make_stl_template("""<a href="${value}">New</a>""")


class TimeWidget(TextWidget):

    template = make_stl_template("""
        <input type="text" name="${name}" value="${value}" id="${name}"
          size="5" />
        <script type="text/javascript">
          $("#${name}").mask("99:99");
          $("#${name}").val("${value}");
        </script>""")
