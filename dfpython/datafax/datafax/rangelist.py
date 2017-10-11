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

import re

class RangeList(object):
    def __init__(self, min, max):
        '''Initialize a Rangelist'''
        self.min = min
        self.max = max
        self.values = []

    def fromString(self, range_string):
        '''Convert a range list string to a rangelist item'''
        self.values = []
        # Remove beginning and trailing
        range_string = range_string.strip()
        range_string = range_string.replace('~', '-')
        range_string = re.sub(r'[ ]+-', '-', range_string)
        range_string = re.sub(r'-[ ]+', '-', range_string)
        range_string = re.sub(r'[ ]+', ',', range_string)
        range_string = re.sub(r',+', ',', range_string)
        range_items = range_string.split(',')
        for range_item in range_items:
            if range_item == '':
                continue
            if range_item == '*':
                self.values.append((self.min, self.max))
                continue

            range_item_list = range_item.split('-')
            if len(range_item_list) == 2:
                self.values.append((int(range_item_list[0]),
                    int(range_item_list[1])))
            else:
                self.values.append((int(range_item_list[0]),
                    int(range_item_list[0])))

    def append(self, lo, hi):
        if lo > hi:
            self.values.append((hi, lo))
        else:
            self.values.append((lo, hi))

    def contains(self, value):
        '''Returns whether value appears in the list'''
        for r in self.values:
            if value >= r[0] and value <= r[1]:
                return True
        return False

    def position(self, value):
        '''Returns the position in the list where value is located'''
        pos = 0
        for r in self.values:
            if value >= r[0] and value <= r[1]:
                return pos
            pos += 1
        return pos

    def toString(self):
        l = []
        for r in self.values:
            if r[0] == r[1]:
                l.append('{0}'.format(r[0]))
            else:
                l.append('{0}-{1}'.format(r[0], r[1]))
        return ', '.join(l)

    def toSQL(self, fieldName):
        ''' Generate an SQL clause from the rangelist '''
        if not self.values:
            return None
        clause = ''
        for r in self.values:
            if clause:
                clause += ' or '
            if r[0] == r[1]:
                clause += fieldName + '=' + str(r[0])
            else:
                clause += fieldName + ' between ' + str(r[0]) + ' and ' + str(r[1])
        return '(' + clause + ')'
