#
# Copyright 2017, Population Health Research Institute
# Copyright 2017, Martin Renters
#
# This file is part of the DataFax Toolkit.
#
# The DataFax Toolkit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The DataFax Toolkit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with The DataFax Toolkit.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from datafax.fieldbase import FieldBase

##############################################################################
# Field Class - Fields of a Module
##############################################################################
class Field(FieldBase):
    def __init__(self, module, id = None):
        self._module = module
        self._id = id
        super(Field, self).__init__()

    def id(self):
        return self._id

##############################################################################
# Module Class
##############################################################################
class Module(object):
    def __init__(self, study, name, id):
        self._study = study
        self._name = name
        self._id = id
        self.description = ""
        self._fields = []

    def id(self):
        return self._id

    def name(self):
        return self._name

    def addField(self, id):
        field = Field(self, id)
        self._fields.append(field)
        return field

    def fieldById(self, id):
        for f in self._fields:
            if f.id() == id:
                return f
        return None

    def sortFields(self):
        self._fields.sort(key=lambda x: x.name.lower())
