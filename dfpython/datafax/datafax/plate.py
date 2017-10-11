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
# FieldRef Class - FieldRefs of a ModuleRef
##############################################################################
class FieldRef(FieldBase):
    def __init__(self, moduleref, id = None):
        self._moduleRef = moduleref
        self._id = id
        super(FieldRef, self).__init__()

    def id(self):
        return self._id

    ######################################################################
    # boundingBox - Returns bounding box for field
    ######################################################################
    def boundingBox(self):
        bb = []
        for r in self.rects:
            if len(bb) == 0:
                bb = [ r.left, r.top, r.left+r.width, r.top+r.height ]
            else:
                if r.left < bb[0]:
                    bb[0] = r.left
                if r.top < bb[1]:
                    bb[1] = r.top
                if r.left + r.width > bb[2]:
                    bb[2] = r.left + r.width
                if r.top + r.height > bb[3]:
                    bb[3] = r.top + r.height
        if len(bb) == 0:
            return None
        else:
            return (bb[0], bb[1], bb[2], bb[3])

##############################################################################
# ModuleRef Class - ModuleRefs of a Plate
##############################################################################
class ModuleRef(object):
    def __init__(self, plate, id):
        self._plate = plate
        self._id = id
        self._fieldRefs = {}
        self.description = None
        self.name = None
        self.instance = 0

    ##########################################################################
    # addFieldRef - Add a new FieldRef to a ModuleRef
    ##########################################################################
    def addFieldRef(self, id):
        fr = FieldRef(self, id)
        self._fieldRefs[id] = fr
        self._plate.fieldChange()
        return fr

class Plate(object):
    def __init__(self, study, number):
        self._study = study
        self._number = number
        self._fields = None
        self._moduleRefs = {}
        self.description = None

    def number(self):
        return self._number

    ##########################################################################
    # addModuleRef - Add a new ModuleRef to a Plate
    ##########################################################################
    def addModuleRef(self, id):
        mr = ModuleRef(self, id)
        self._moduleRefs[id] = mr
        return mr

    ##########################################################################
    # fieldChange - notify Plate that a field change has happened
    ##########################################################################
    def fieldChange(self):
        self._fields = None

    ##########################################################################
    # fieldList - Get a sorted list of fields for a plate
    ##########################################################################
    def fieldList(self):
        # If the field list exists and is current, simply return it
        if self._fields != None:
            return self._fields

        # We need to build a new field list as it has never been created
        # or a field change invalidated it
        fl = []
        for moduleref in self._moduleRefs.values():
            fl.extend(moduleref._fieldRefs.values())
        fl.sort(key=lambda x: x.number)
        self._fields = fl

        return self._fields

    ##########################################################################
    # fieldAt - Return the FieldRef at position field_num on plate
    ##########################################################################
    def fieldAt(self, field_num):
        fl = self.fieldList()
        if field_num > 0 and field_num <= len(fl):
            return fl[field_num-1]
        else:
            return None
