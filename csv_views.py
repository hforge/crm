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
from cStringIO import StringIO
import csv
from decimal import Decimal as dec

# Import from itools
from itools.core import freeze, is_thingy
from itools.csv import CSVFile
from itools.datatypes import Enumerate, String
from itools.gettext import MSG
from itools.stl import stl
from itools.web import ERROR

# Import from ikaaro
from ikaaro.autoform import SelectWidget

# Import from crm
from datatypes import CSVEditor


ERR_NO_DATA = ERROR(u"No data to export.")

sniffer = csv.Sniffer()


def cleanup_gmail_csv(body):
    # Sniff dialect
    dialect = sniffer.sniff(body)
    dialect.doublequote = True
    if dialect.delimiter == '' or dialect.delimiter == ' ':
        dialect.delimiter = ','
    # Reader
    reader = csv.reader(StringIO(body), dialect)
    # Reformated CSV
    output = StringIO()
    writer = csv.writer(output, dialect='excel', quoting=csv.QUOTE_ALL)
    # Read header and number of columns
    header = reader.next()
    writer.writerow(header)
    n_columns = len(header)
    # Align columns to that number XXX not solid
    for row in reader:
        n_row = len(row)
        if n_row < n_columns:
            row += [''] * (n_columns - n_row)
        elif n_row > n_columns:
            row = row[:n_columns]
        writer.writerow([value.decode('cp1252').encode('utf_8')
            for value in row])
    return output.getvalue()



def find_value_by_column(header, row, title, cache={}):
    if title in cache:
        return unicode(row[cache[title]], 'utf_8')
    for i, column in enumerate(header):
        if column == title:
            cache[title] = i
            return unicode(row[i], 'utf_8')



class CSV_Export(object):
    schema = freeze({
        'editor': CSVEditor})

    csv_template = '/ui/crm/generic/csv.xml'
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
        self.assured = dec('0.0')
        self.probable = dec('0.0')
        items = self.sort_and_batch(resource, context, results)

        # Create the CSV
        csv = CSVFile()

        # Add the header
        row = []
        for name, title in self.csv_columns:
            if is_thingy(title, MSG):
                title = title.gettext()
            row.append(title.encode(encoding))
        csv.add_row(row)

        # Fill the CSV
        cache = {}
        for item in items:
            item_brain, item_resource = item
            row = []
            for name, title in self.csv_columns:
                value = self.get_item_value(resource, context, item, name,
                        cache=cache)
                if type(value) is tuple:
                    value, href = value
                if value is None:
                    data = ''
                elif type(value) is unicode:
                    data = value.encode(encoding, 'replace')
                else:
                    try:
                        datatype = resource.get_property_datatype(name)
                    except ValueError:
                        datatype = String
                    if issubclass(datatype, Enumerate):
                        value = datatype.get_value(value)
                        if is_thingy(value, MSG):
                            value = value.gettext()
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
