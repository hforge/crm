# -*- coding: UTF-8 -*-
# Copyright (C) 2007 J. David Ibanez <jdavid@itaapy.com>
# Copyright (C) 2007-2009 Henry Obein <henry@itaapy.com>
# Copyright (C) 2010-2011 Hervé Cauwelier <herve@itaapy.com>
# Copyright (C) 2010-2011 Nicolas Deram <nicolas@itaapy.com>
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
from sys import argv

# Import from itools
from itools.core import get_abspath, get_version
from itools.gettext import register_domain

# Import from ikaaro
from ikaaro.registry import register_document_type
from ikaaro.website import WebSite

# Import from crm
from crm import CRM

# Make the product version available to Python code
__version__ = get_version()

# Register the crm domain
path = get_abspath('locale')
register_domain('crm', path)

# Import obsolete if command is icms-update.py
if argv[0].endswith('icms-update.py'):
    import obsolete
    print 'Imported', obsolete.__name__

# Activate crm as an itws website's document type
#register_document_type(CRM, WebSite.class_id)

# Silent pyflakes
CRM, WebSite, register_document_type

