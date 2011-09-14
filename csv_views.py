# -*- coding: UTF-8 -*-
# Copyright (C) 2009-2010 Nicolas Deram <nicolas@itaapy.com>
# Copyright (C) 2011 Hervé Cauwelier <herve@itaapy.com>
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

# Import from itools
from itools.core import freeze, is_thingy, merge_dicts, thingy, OrderedDict
from itools.core import guess_type
from itools.csv import CSVFile
from itools.datatypes import Enumerate, String
from itools.gettext import MSG
from itools.stl import stl
from itools.web import ERROR
from itools.xml import XMLParser, xml_to_text

# Import from ikaaro
from ikaaro.autoform import SelectWidget
from ikaaro.buttons import BrowseButton
from ikaaro.utils import make_stl_template

# Import from crm


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



class CSVColumn(thingy):
    datatype = String


    def __init__(cls, name=None, **kw):
        if name:
            cls.name = name


    def encode(cls, value):
        """Encode to a unicode or a Python value compatible with str().
        """
        # TODO in 0.70 read datatype from class_schema
        datatype = cls.datatype
        # Replace enumerate name by value
        if issubclass(datatype, Enumerate):
            value = datatype.get_value(value)
        if value is None:
            return ''
        # Default encoders
        value_type = type(value)
        if value_type is XMLParser or value_type is list:
            return xml_to_text(value)
        if is_thingy(value, MSG):
            value = value.gettext()
        return value



csv_writer_registry = OrderedDict()

def register_csv_writer(writer, name=None):
    if name is None:
        name = writer.name
    csv_writer_registry[name] = writer



class CSV_ODS_Writer(thingy):
    name = 'ooo'
    title = MSG(u"CSV for OpenOffice.org / LibreOffice")
    mimetype = 'text/comma-separated-values'
    extension = 'csv'
    encoding = 'UTF-8'
    separator = ","
    newline = "\n"


    def __init__(cls, columns, name):
        cls.columns = columns
        cls.csv = CSVFile()


    def get_nrows(cls):
        return cls.csv.get_nrows()


    def add_row(cls, row, is_header=False):
        values = []
        for i, value in enumerate(row):
            column = cls.columns[i]
            value = column.encode(value)
            if type(value) is unicode:
                value = value.encode(cls.encoding)
            else:
                value = str(value)
            values.append(value)
        cls.csv.add_row(values)


    def to_str(cls):
        return cls.csv.to_str(separator=cls.separator, newline=cls.newline)

register_csv_writer(CSV_ODS_Writer)



class CSV_XLS_Writer(CSV_ODS_Writer):
    name = 'excel'
    title = MSG(u"CSV for MS Excel")
    encoding = 'CP1252'
    separator = ";"
    newline = "\r\n"

register_csv_writer(CSV_XLS_Writer)



try:
    from lpod.document import odf_new_document
    from lpod.style import odf_create_style
    from lpod.table import odf_create_table, odf_create_row

    class ODSWriter(object):
        name = 'ods'
        title = MSG(u"OpenDocument Spreadsheet")
        mimetype = 'application/vnd.oasis.opendocument.spreadsheet'
        extension = 'ods'
        header_style = odf_create_style('table-cell', area='text', bold=True)


        def __init__(cls, columns, name):
            cls.columns = columns
            cls.document = document = odf_new_document('spreadsheet')
            cls.table = table = odf_create_table(name)
            document.get_body().append(table)
            document.insert_style(cls.header_style, automatic=True)


        def get_nrows(cls):
            return cls.table.get_height()


        def add_row(cls, row, is_header=False):
            if is_header is True:
                style = cls.header_style
            else:
                style = None
            values = []
            for i, value in enumerate(row):
                column = cls.columns[i]
                values.append(column.encode(value))
            row = odf_create_row()
            row.set_values(values, style=style)
            cls.table.append_row(row)


        def to_str(cls):
            body = StringIO()
            cls.document.save(body)
            return body.getvalue()

    register_csv_writer(ODSWriter)
except ImportError:
    pass



try:
    from xlwt import Workbook, easyxf
    from xlwt.Style import default_style

    class XLSWriter(object):
        name = 'xls'
        title = MSG(u"MS Excel")
        mimetype = 'application/vnd.ms-excel'
        extension = 'xls'
        header_style = easyxf('font: bold on')


        def __init__(cls, columns, name):
            cls.columns = columns
            cls.workbook = workbook = Workbook()
            # Taken from xlwt.Utils.valid_sheet_name
            # Sheet name limited to 31 chars
            if len(name) > 31:
                name = u"{sheetname}...".format(sheetname=name[:28])
            # XXX escape bug
            #   en.po locale/locale.pot:78:13: Séquence de contrôle invalide
            # msgmerge: 1 erreur fatale trouvée
            for c in ur"'[]:\\?/*\x00":
                name = name.replace(c, u".")
            cls.sheet = workbook.add_sheet(name)
            # XXX
            cls.y = 0


        def get_nrows(cls):
            return cls.y


        def add_row(cls, row, is_header=False):
            sheet = cls.sheet
            if is_header is True:
                style = cls.header_style
            else:
                style = default_style
            for x, value in enumerate(row):
                column = cls.columns[x]
                value = column.encode(value)
                sheet.write(cls.y, x, value, style)
            cls.y += 1


        def to_str(cls):
            body = StringIO()
            cls.workbook.save(body)
            return body.getvalue()

    register_csv_writer(XLSWriter)
except ImportError:
    pass



class CSVFormat(Enumerate):
    formats = csv_writer_registry.keys()


    def get_default(cls):
         return cls.formats[0]


    def get_options(cls):
        options = []
        for name in cls.formats:
            writer = csv_writer_registry[name]
            options.append({
                'name': name,
                'value': writer.title,
                'writer': writer})
        return options


    def get_writer(cls, name):
        for option in cls.get_options():
            if option['name'] == name:
                return option['writer']

        raise ValueError, name



class CSVExportButton(BrowseButton):
    access = 'is_allowed_to_view'
    name = 'csv_export'
    title = MSG(u"Export")
    css = 'button-csv'



class CSVExportFormatButton(SelectWidget, CSVExportButton):
    template = (make_stl_template("""
        ${label}:
        <select id="${id}-format" name="csv_format">
          <option stl:repeat="option options" value="${option/name}"
            selected="${option/selected}">${option/value}</option>
        </select>""")
        + CSVExportButton.template)
    label = MSG(u"Export to format")
    css = CSVExportButton.css
    datatype = CSVFormat

    def value(cls):
        return cls.datatype.get_default()



class CSV_Export(object):
    csv_schema = freeze({'csv_format': CSVFormat(mandatory=True)})
    csv_template = '/ui/crm/csv/format.xml'
    csv_columns = freeze([])
    csv_table_name = MSG(u"Sheet1")
    csv_filename = None
    csv_allow_empty = False


    def get_csv_namespace(self, resource, context):
        namespace = {}
        datatype = self.csv_schema['csv_format']
        namespace['format'] = SelectWidget('csv_format',
                value=datatype.get_default(), datatype=datatype,
                has_empty_option=False)
        namespace['action'] = CSVExportButton(resource=resource,
                context=context, items=[0])
        template = resource.get_resource(self.csv_template)
        return stl(template, namespace)


    def get_csv_table_name(self, resource, context):
        table_name = self.csv_table_name
        if is_thingy(table_name, MSG):
            table_name = table_name.gettext()
        return table_name


    def get_csv_filename(self, resource, context, writer):
        filename = self.csv_filename
        if filename is None:
            filename = resource.name
        if guess_type(filename) == (None, None):
            filename = "{0}.{1}".format(filename, writer.extension)
        return filename


    def csv_write_header(self, resource, context, writer):
        header = []
        for column in self.csv_columns:
            # TODO in 0.70 get title from class_schema
            header.append(column.title)
        writer.add_row(header, is_header=True)


    def csv_write_row(self, resource, context, writer, item):
        row = []
        for column in self.csv_columns:
            name = column.name
            try:
                value = getattr(item, name)
            except AttributeError:
                value = item.get_property(name)
            else:
                if callable(value):
                    value = value()
            row.append(value)
        writer.add_row(row)


    def get_csv_items(self, resource, context, form):
        raise NotImplementedError


    def action_csv_export(self, resource, context, form):
        datatype = self.get_schema(resource, context)['csv_format']
        writer_class = datatype.get_writer(form['csv_format'])

        # Get the items
        items = self.get_csv_items(resource, context, form)

        # Create the writer
        table_name = self.get_csv_table_name(resource, context)
        writer = writer_class(self.csv_columns, table_name)

        # Add the header
        self.csv_write_header(resource, context, writer)
        header_rows = writer.get_nrows()

        # Fill the CSV
        for item in items:
            self.csv_write_row(resource, context, writer, item)

        if writer.get_nrows() == header_rows and not self.csv_allow_empty:
            context.message = ERR_NO_DATA
            return

        # Set response type
        context.set_content_type(writer.mimetype)
        context.set_content_disposition('attachment; filename="{0}"'.format(
            self.get_csv_filename(resource, context, writer)))

        return writer.to_str()



class Folder_CSV_Export(CSV_Export):

    # Allow to export the whole list without checking any box
    action_csv_export_schema = freeze(merge_dicts(
        CSV_Export.csv_schema,
        ids=String(multiple=True, mandatory=False)))


    def csv_write_row(self, resource, context, writer, item):
        row = []
        for column in self.csv_columns:
            value = self.get_item_value(resource, context, item, column.name)
            if type(value) is tuple:
                value = value[0]
            # TODO in 0.70 read datatype from class_schema
            row.append(value)
        writer.add_row(row)


    def get_csv_items(self, resource, context, form):
        results = self.get_items(resource, context)
        if not len(results):
            return
        # Filter by selected ids or all
        ids = form.get('ids')
        # XXX
        batch_start = context.query['batch_start']
        batch_size = context.query['batch_size']
        context.query['batch_start'] = context.query['batch_size'] = 0
        for item in self.sort_and_batch(resource, context, results):
            if ids:
                item_id = self.get_item_value(resource, context, item,
                        'checkbox')
                if type(item_id) is tuple:
                    item_id = item_id[0]
                if item_id not in ids:
                    continue
            yield item
        # XXX
        context.query['batch_start'] = batch_start
        context.query['batch_size'] = batch_size
