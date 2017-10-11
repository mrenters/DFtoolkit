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
# Center - An entry from the centers database
#############################################################################
class Center:
    def __init__(self, number):
        self.number = number
        self.is_error_monitor = False
        self.contact = ''
        self.affiliation = ''
        self.address = ''
        self.primary_fax = ''
        self.secondary_fax = ''
        self.phone = ''
        self.investigator = ''
        self.investigator_phone = ''
        self.reply_address = ''
        self.patients = RangeList(1,281474976710656)

#############################################################################
# Centers - Centers Database
#############################################################################
class Centers:
    def __init__(self):
        self.centers = []

    def load(self, centersdb_string):
        '''Load centers database string'''
        self.centers = []
        lines = centersdb_string.split('\n')
        for line in lines:
            fields = line.split('|')
            if len(fields) < 11:
                continue
            center = Center(int(fields[0]))
            center.contact = fields[1]
            center.affiliation = fields[2]
            center.address = fields[3]
            center.primary_fax = fields[4]
            center.secondary_fax = fields[5]
            center.phone = fields[6]
            center.investigator = fields[7]
            center.investigator_phone = fields[8]
            center.reply_address = fields[9]
            if fields[10] == 'ERROR MONITOR':
                center.is_error_monitor = True
            else:
                for i in range(10, len(fields)):
                    r = fields[i].split(' ')
                    if len(r) == 2:
                        center.patients.append(int(r[0]), int(r[1]))

            self.centers.append(center)
        return True

    def centerNumber(self, pid):
        '''Find the center number for patient'''
        center = self.center(pid)
        if center is not None:
            return center.number
        return 0

    def center(self, pid):
        '''Find the Center entry for patient'''
        error_monitor = None
        for c in self.centers:
            if c.patients.contains(pid):
                return c
            if c.is_error_monitor:
                error_monitor = c
        return error_monitor
