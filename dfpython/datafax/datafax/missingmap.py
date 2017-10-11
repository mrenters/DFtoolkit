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
# MissingMapEntry - An entry from the missing map
#############################################################################
class MissingMapEntry:
    def __init__(self, code, label):
        self.code = code
        self.label = label

#############################################################################
# MissingMap - Missing Map class
#############################################################################
class MissingMap:
    def __init__(self):
        self.entries = [MissingMapEntry('*', 'Missing Value')]

    def load(self, mmap_string):
        self.entries = []
        mmap_lines = mmap_string.split('\n')
        for line in mmap_lines:
            fields = line.split('|')
            if len(fields) < 2:
                continue
            self.entries.append(MissingMapEntry(fields[0], fields[1]))

        return True

    def label(self, code):
        for entry in self.entries:
            if entry.code == code:
                return entry.label
        return None
