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

from datafax.rangelist import RangeList

#############################################################################
# DomainEntry - An entry from the domain map
#############################################################################
class DomainMapEntry:
    def __init__(self):
        self.plates = RangeList(0,500)
        self.label = None

    def plateOrder(self, plate):
        '''Returns the plate sort order position'''
        return self.plates.position(plate)

#############################################################################
# DomainMap - Domain Map class
#############################################################################
class DomainMap:
    def __init__(self):
        self.entries = []

    def load(self, dmap_string):
        '''Load a domain map string'''
        self.entries = []
        dmap_lines = dmap_string.split('\n')
        for line in dmap_lines:
            fields = line.split('|')
            if len(fields) < 2:
                continue
            entry = DomainMapEntry()
            entry.label = fields[0]
            entry.plates.fromString(fields[1])
            self.entries.append(entry)
        return True

    def label(self, plate):
        '''Find the domain label for the plate'''
        entry = self.entry(plate)
        if entry is not None:
            return entry.label
        return 'Other'

    def entry(self, plate):
        '''Find the domain map entry for visit'''
        for e in self.entries:
            if e.plates.contains(plate):
                return e
        return None
