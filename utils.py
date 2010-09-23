# -*- coding: UTF-8 -*-
# Copyright (C) 2007-2008 Henry Obein <henry@itaapy.com>
# Copyright (C) 2008-2010 Nicolas Deram <nicolas@itaapy.com>
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

# Import from ikaaro
from ikaaro.registry import get_resource_class
from ikaaro.utils import get_base_path_query


def generate_code(names, strformat='%03d', index=None):
    """ Generate a codename with a prefix followed by an integer.
            generate_code(['c1', 'c3', 'c4'], 'c%03d') -> 'c005'
            generate_code(['c005'], 'c%03d') -> 'c001'
    """
    if index is None:
        index = len(names)
    name = strformat % index

    while name in names:
        index = index + 1
        name = strformat % index

    return name



def get_crm(resource):
    cls_crm = get_resource_class('crm')
    crm = resource
    while not isinstance(crm, cls_crm):
        crm = crm.parent
    return crm



def get_crm_path_query(crm_resource):
    crm_path = str(crm_resource.get_abspath())
    return get_base_path_query(crm_path, include_container=True)



# FIXME reuse itws one
def get_path_and_view(path):
    view = ''
    name = path.get_name()
    # Strip the view
    if name and name[0] == ';':
        view = '/' + name
        path = path[:-1]

    return path, view
