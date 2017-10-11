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
# PageMapEntry - An entry from the page map
#############################################################################
class PageMapEntry:
    def __init__(self):
        self.visits = RangeList(0,65535)
        self.plates = RangeList(0, 500)
        self.label = None

#############################################################################
# PageMap - Page Map class
#############################################################################
class PageMap:
    def __init__(self):
        self.entries = []

    def load(self, pmap_string):
        self.entries = []
        pmap_lines = pmap_string.split('\n')
        for line in pmap_lines:
            fields = line.split('|')
            if len(fields) < 3 or fields[0] == "S":
                continue
            entry = PageMapEntry()
            entry.plates.fromString(fields[0])
            entry.visits.fromString(fields[1])
            entry.label = fields[2]
            self.entries.append(entry)
        return True

    def label(self, visit, plate):
        for entry in self.entries:
            if entry.visits.contains(visit) and entry.plates.contains(plate):
                label = entry.label
                visit_str = str(visit).zfill(5)
                plate_str = str(plate).zfill(3)
                label = label.replace('%{1.S}', visit_str[:1])
                label = label.replace('%{2.S}', visit_str[:2])
                label = label.replace('%{3.S}', visit_str[:3])
                label = label.replace('%{4.S}', visit_str[:4])
                label = label.replace('%{5.S}', visit_str[:5])
                label = label.replace('%{S.1}', visit_str[-1:])
                label = label.replace('%{S.2}', visit_str[-2:])
                label = label.replace('%{S.3}', visit_str[-3:])
                label = label.replace('%{S.4}', visit_str[-4:])
                label = label.replace('%{S.5}', visit_str[-5:])
                label = label.replace('%S', str(visit))
                label = label.replace('%{1.P}', plate_str[:1])
                label = label.replace('%{2.P}', plate_str[:2])
                label = label.replace('%{3.P}', plate_str[:3])
                label = label.replace('%{P.1}', plate_str[-1:])
                label = label.replace('%{P.2}', plate_str[-2:])
                label = label.replace('%{P.3}', plate_str[-3:])
                label = label.replace('%P', str(plate))
                return label
        return None
