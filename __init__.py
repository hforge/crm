# -*- coding: UTF-8 -*-
# Copyright (C) 2007 J. David Ibanez <jdavid@itaapy.com>
# Copyright (C) 2007-2008 Henry Obein <henry@itaapy.com>
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

# Import from itws
from itws.skin import register_not_allowed_cls_for_sidebar_view
from itws.skin import register_not_allowed_view_for_sidebar_view

# Import from crm
from crm import CRM
from mission import Mission

# Make the product version available to Python code
__version__ = get_version()

############################################################################
# DOMAIN
############################################################################

# Register the crm domain
path = get_abspath('locale')
register_domain('crm', path)

# Special for obsolete
# Import obsolete if command is icms-update.py
if argv[0].endswith('icms-update.py'):
    import obsolete
    # Silent pyflakes
    obsolete

# Hide sidebar in crm root
register_not_allowed_cls_for_sidebar_view(CRM)
# Hide sidebar in mission add contacts
register_not_allowed_view_for_sidebar_view(Mission.add_contacts)
