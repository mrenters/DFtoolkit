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
# VisitMapEntry - An entry from the visit map
#############################################################################
class VisitMapEntry:
    def __init__(self):
        self.visits = RangeList(0,65535)
        self.visit_type = None
        self.label = None
        self.date_plate = None
        self.date_field = None
        self.due_date = 0
        self.overdue_allowance = 0
        self.missed_visit_notification = None
        self.termination_window = None
        self.required_plates = RangeList(0,500)
        self.optional_plates = RangeList(0,500)
        self.display_order = RangeList(0,500)

    def plateOrder(self, plate):
        '''Returns the plate sort order position'''
        return self.display_order.position(plate)

#############################################################################
# VisitMap - Visit Map class
#############################################################################
class VisitMap:
    def __init__(self):
        self.entries = []

    def load(self, vmap_string):
        '''Load a visit map string'''
        self.entries = []
        vmap_lines = vmap_string.split('\n')
        for line in vmap_lines:
            fields = line.split('|')
            if len(fields) < 7 or fields[1] == 'C':
                continue
            entry = VisitMapEntry()
            entry.visits.fromString(fields[0])
            entry.required_plates.fromString(fields[7])
            if len(fields) >= 8:
                entry.optional_plates.fromString(fields[8])
            if len(fields) >= 11 and fields[11] != '':
                entry.display_order.fromString(fields[11])
            else:
                entry.display_order.fromString(fields[7]+" "+fields[8])
            entry.visit_type = fields[1]
            entry.label = fields[2]
            entry.date_plate = fields[3]
            entry.date_field = fields[4]
            if fields[5]:
                entry.due_date = int(fields[5])
            if fields[6]:
                entry.overdue_allowance = int(fields[6])
            if fields[9]:
                entry.missed_visit_notification = int(fields[9])
            if fields[10]:
                entry.termination_window = fields[10]
            self.entries.append(entry)
        return True

    def label(self, visit):
        '''Find the label for the visit'''
        entry = self.entry(visit)
        if entry is not None:
            label = entry.label
            visit_str = str(visit).zfill(5)
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
            return label
        return "Visit {0}".format(visit)

    def entry(self, visit):
        '''Find the visit map entry for visit'''
        for e in self.entries:
            if e.visits.contains(visit):
                return e
        return None
