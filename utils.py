# -*- coding: UTF-8 -*-
# Copyright (C) 2007-2008 Henry Obein <henry@itaapy.com>
# Copyright (C) 2008 Nicolas Deram <nicolas@itaapy.com>
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
from itools.web import get_context
from itools.xml import XMLParser

# Import from ikaaro
from ikaaro.forms import CheckBoxWidget, SelectWidget, TextWidget
from ikaaro.forms import stl_namespaces


def generate_name(names, strformat='%03d', index=None):
    """ Generate a name with a prefix followed by an integer.
            generate_name(['c1', 'c3', 'c4'], 'c%03d') -> 'c005'
            generate_name(['c005'], 'c%03d') -> 'c001'
    """
    if index is None:
        index = len(names)
    name = strformat % index

    while name in names:
        index = index + 1
        name = strformat % index

    return name


############################################################
# Forms
############################################################
class MultipleCheckBoxWidget(CheckBoxWidget):

    template = list(XMLParser("""
        <stl:inline stl:repeat="item items">
          <input type="checkbox" name="${name}" value="${item/name}"
            checked="${item/selected}" />${item/value}</stl:inline>
        """, stl_namespaces))


    def get_namespace(self, datatype, value):
        items = []
        for option in datatype.get_options():
            name = option['name']
            items.append({
                'name': name,
                'value': option['value'],
                'selected': name in value})
        return {'name': self.name, 'items': items}


class SelectCompanyWidget(SelectWidget):

    template = list(XMLParser("""
        <select id="${id}" name="${name}" multiple="${multiple}" size="${size}"
            class="${css}">
          <option value="" stl:if="has_empty_option"></option>
          <option stl:repeat="option options" value="${option/name}"
            selected="${option/selected}">${option/value}</option>
        </select>
        """, stl_namespaces))


class EmailWidget(TextWidget):

    template = list(XMLParser(
        """<input type="${type}" id="${id}" name="${name}" value="${value}"
             size="${size}" /><a stl:if="value" href="mailto:${value}">
             <img src="/ui/icons/16x16/mail.png" /></a>
        """, stl_namespaces))


class LinkWidget(TextWidget):

    template = list(XMLParser(
        """<input type="${type}" id="${id}" name="${name}" value="${value}"
             size="${size}" /><a stl:if="value" href="${value}"
             target="_blank"><img src="/ui/icons/16x16/website.png" /></a>
        """, stl_namespaces))

    def get_namespace(self, datatype, value):
        namespace = TextWidget.get_namespace(self, datatype, value)
        value = namespace['value']
        if 'http://' not in value and 'https://' not in value:
            value = 'http://%s' % value
            namespace['value'] = value
        return namespace


class NewCompanyWidget(TextWidget):

    template = list(XMLParser("""
        <a href="${value}">New</a>
        """, stl_namespaces))


class TimeWidget(TextWidget):

    template = list(XMLParser("""
        <input type="text" name="${name}" value="${value}" id="${name}"
          size="5" />
        <script type="text/javascript">
          $("#${name}").mask("99:99");
          $("#${name}").val("${value}");
        </script>
        """, stl_namespaces))

    def get_namespace(self, datatype, value):
        scripts = get_context().scripts
        scripts.append('/ui/common/jquery.maskedinput-1.2.2.min.js')
        return TextWidget.get_namespace(self, datatype, value)

