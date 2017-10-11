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
# Country - An entry from the country database
#############################################################################
class Country:
    def __init__(self, name):
        self.name = name
        self.region = 'Unknown'
        self.centers = RangeList(1,21460)

#############################################################################
# Countries - Countries Database
#############################################################################
class Countries:
    def __init__(self):
        self.countries = []

    def load(self, countries_string):
        '''Load countries database string'''
        self.countries = []
        lines = countries_string.split('\n')
        for line in lines:
            fields = line.split('|')
            if len(fields) < 3:
                continue
            country = Country(fields[0])
            country.region = fields[1]
            country.centers.fromString(fields[2])
            self.countries.append(country)
        return True

    def region(self, center):
        '''Find the region for center'''
        country = self.entry(center)
        if country is not None:
            return country.region
        return 'Unknown' 

    def country(self, center):
        '''Find the country for center'''
        country = self.entry(center)
        if country is not None:
            return country.name
        return 'Unknown' 

    def entry(self, center):
        '''Find the Country entry for center'''
        for c in self.countries:
            if c.centers.contains(center):
                return c
        return None
