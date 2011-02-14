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

# Import from itools
from itools.core import freeze
from itools.csv import CSVFile
from itools.datatypes import Enumerate
from itools.stl import stl
from itools.web import ERROR

# Import from ikaaro
from ikaaro.autoform import SelectWidget
from ikaaro.registry import get_resource_class

# Import from crm
from datatypes import CSVEditor


ERR_NO_DATA = ERROR(u"No data to export.")


class CSV_Export(object):
    schema = freeze({
        'editor': CSVEditor})

    csv_template = '/ui/crm/crm/csv.xml'
    csv_columns = freeze([])
    csv_filename = None


    def get_csv_namespace(self, resource, context):
        namespace = {}
        namespace['editor'] = SelectWidget('editor', value='excel',
                datatype=CSVEditor, has_empty_option=False)
        return namespace


    def get_namespace(self, resource, context):
        namespace = {}
        if self.csv_columns:
            csv_template = resource.get_resource(self.csv_template)
            csv_namespace = self.get_csv_namespace(resource, context)
            namespace['csv'] = stl(csv_template, csv_namespace)
        else:
            namespace['csv'] = None
        return namespace


    def action_csv(self, resource, context, form):
        encoding, separator = CSVEditor.get_parameters(form['editor'])

        results = self.get_items(resource, context)
        if not len(results):
            context.message = ERR_NO_DATA
            return
        # XXX
        context.query['batch_start'] = context.query['batch_size'] = 0
        items = self.sort_and_batch(resource, context, results)

        # Create the CSV
        csv = CSVFile()

        # Add the header
        csv.add_row([title.gettext().encode(encoding)
            for name, title in self.csv_columns])

        # Fill the CSV
        resource_class = get_resource_class(self.search_format)
        class_schema = resource_class.class_schema
        cache = {}
        for item in items:
            row = []
            for name, title in self.csv_columns:
                value = self.get_item_value(resource, context, item, name,
                        cache=cache)
                if type(value) is tuple:
                    value, href = value
                if type(value) is str:
                    value = value.decode('utf_8')
                if value is None:
                    data = ''
                elif type(value) is unicode:
                    data = value.encode(encoding)
                else:
                    datatype = class_schema.get(name)
                    if (datatype is not None
                            and issubclass(datatype, Enumerate)):
                        value = datatype.get_value(value)
                        data = value.encode(encoding)
                    else:
                        data = str(value)
                row.append(data)
            csv.add_row(row)

        # Set response type
        context.set_content_type('text/comma-separated-values')
        context.set_content_disposition('attachment; filename="{0}"'.format(
            self.csv_filename))

        return csv.to_str(separator=separator)
