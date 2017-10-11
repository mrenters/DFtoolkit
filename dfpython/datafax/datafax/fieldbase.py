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

from datafax.rect import Rect

##########################################################################
# FieldBase - Abstract base class for Styles, Fields and FieldRefs
##########################################################################
class FieldBase(object):
    def __init__(self):
        self.number = None
        self.name = None
        self.alias = None
        self.styleName = None
        self.description = None
        self.type = None
        self.legal = None
        self.format = None
        self.help = None
        self.constant = None
        self.prompt = None
        self.comment = None
        self.units = None
        self.fieldEnter = None
        self.fieldExit = None
        self.plateEnter = None
        self.plateExit = None
        self.skipNumber = None
        self.skipCondition = None
        self.inherited = None
        self.locked = None
        self.reason_level = None
        self.blinded = 'No'
        self.required = 'Optional'
        self.store = 1
        self.use = 'Standard'
        self.mapping = None
        self.yearCutoff = None
        self.dateRounding = None
        self.codes = []
        self.rects = []

    ##########################################################################
    # loadSetup - Initialize from JSON setup data
    ##########################################################################
    def loadSetup(self, object):
        self.number = object.get('number')
        self.name = object.get('name')
        self.styleName = object.get('styleName')
        self.alias = object.get('alias')
        self.description = object.get('description')
        self.type = object.get('type')
        self.legal = object.get('legal')
        self.format = object.get('format')
        self.help = object.get('help')
        self.constant = object.get('constant')
        self.prompt = object.get('prompt')
        self.comment = object.get('comment')
        self.units = object.get('units')
        self.fieldEnter = object.get('fieldEnter')
        self.fieldExit = object.get('fieldExit')
        self.plateEnter = object.get('plateEnter')
        self.plateExit = object.get('plateExit')
        self.skipNumber = object.get('skipTo')
        self.skipCondition = object.get('skipCondition')
        self.inherited = object.get('inheritedBitmap')
        self.locked = object.get('lockedBitmap')
        self.reason_level = object.get('level')
        self.blinded = object.get('blinded')
        self.required = object.get('required')
        self.store = object.get('store')
        self.use = object.get('use')
        self.mapping = object.get('mapping')
        self.yearCutoff = object.get('yearCutoff')
        self.dateRounding = object.get('dateRounding')
        self.codes = []
        for c in object.get('codes') or []:
            self.codes.append((c['number'], c['label']))
        self.rects = []
        rects = []
        for r in object.get('rects') or []:
            rects.append(Rect(r['x'], r['y'], r['w'], r['h']))

        c = None
        b = 0
        for r in rects:
            if c is None:
                c = r
                b = 1
            elif c.isAdjacentHorizontal(r):
                c.set(c.left, c.top, r.left + r.width - c.left, c.height)
                b += 1
            else:
                self.rects.extend(c.splitHorizontal(b))
                c = r
                b = 1
        if c is not None:
            self.rects.extend(c.splitHorizontal(b))

    ##########################################################################
    # isBlinded
    ##########################################################################
    def isBlinded(self):
        if self.blinded == 'Yes':
            return True
        return False

    ##########################################################################
    # decode
    ##########################################################################
    def decode(self, value):
        box = None
        if self.type == 'Choice' or self.type == 'Check':
            for code in self.codes:
                if str(code[0]) == str(value):
                    return (box, code[1])
                if box == None:
                    box = 0
                else:
                    box += 1
        return (None, value)

