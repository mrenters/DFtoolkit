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

class Rect(object):
    """
    A Rectangle class that maintains the top left and height and width
    positions.
    """
    def __init__(self, left, top, width, height):
        """ Initial Rectangle """
        self.set(left, top, width, height)

    def set(self, left, top, width, height):
        """ Set Rectangle Points """
        self.left = left
        self.top = top
        self.width = width
        self.height = height

    def top_left(self):
        """ Returns top left coordinates """
        return (self.left, self.top)

    def bottom_right(self):
        """ Returns bottom right coordinates """
        return (self.left+self.width, self.top+self.height)

    def isAdjacentHorizontal(self, rect):
        right = self.left + self.width
        if self.top == rect.top and self.height == rect.height and \
            right >= rect.left-1 and right < (rect.left + rect.width):
            return True
        return False

    def splitHorizontal(self, n):
        if n < 1:
            return []

        width = self.width//n
        remainder = self.width - (width*n)
        left = self.left
        i = 1
        l = []
        while i<n:
            l.append(Rect(left, self.top, width, self.height))
            left += width
            i += 1

        l.append(Rect(left, self.top, width+remainder, self.height))
        return l

    def __str__(self):
        return '<Rect (%s,%s,%s,%s)>' % \
            (self.left, self.top, self.width, self.height)
