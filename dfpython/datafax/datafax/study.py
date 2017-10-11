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

import os
import json
from datafax.style import Style
from datafax.module import Module
from datafax.plate import Plate
from datafax.visitmap import VisitMap
from datafax.pagemap import PageMap
from datafax.missingmap import MissingMap
from datafax.centers import Centers
from datafax.countries import Countries
from datafax.domainmap import DomainMap

class Study(object):
    def __init__(self):
        self._styles = {}
        self._modules = {}
        self._modulesById = {}
        self._nextModuleId = 0
        self._plates = {}
        self._visitmap = None
        self._pagemap = None
        self._missingmap = MissingMap()
        self._domainmap = DomainMap()
        self._centers = Centers()
        self._countries = Countries()
        self._config = {}
        self.setup_name = None
        self.number = None
        self.studydir = None

    ########################################################################
    # Style Related Functions
    ########################################################################
    def addStyle(self, name):
        """
        Add a style to the study if it doesn't already exist. Returns the
        Style object.
        """
        if name in self._styles:
            raise ValueError('Style already exists')
        style = Style(self);
        self._styles[name] = style
        return style

    def style(self, name):
        return self._styles.get(name)

    ########################################################################
    # Module Related Functions
    ########################################################################
    def addModule(self, name, id = None):
        """
        Add a module to the study if it doesn't already exist. Returns the
        Module object.
        """
        if id == None:
            id = self._nextModuleId
            self._nextModuleId += 1

        if name in self._modules:
            raise ValueError('Module name already exists')
        if id in self._modulesById:
            raise ValueError('Module ID already exists')

        module = Module(self, name, id);
        self._modules[name] = module
        self._modulesById[id] = module
        return module

    def moduleList(self):
        """
        Returns a sorted list of Module objects for the study
        """
        ml = self._modules.values()
        ml.sort(key=lambda x: x.name().lower())
        return ml

    ########################################################################
    # Plate Related Functions
    ########################################################################
    def addPlate(self, number):
        """
        Add a plate to the study if it doesn't already exist. Returns the
        Plate object.
        """
        if number in self._plates:
            raise ValueError('Plate number already exists')
        plate = Plate(self, number);
        self._plates[number] = plate
        return plate

    def plate(self, number):
        """
        Returns the Plate object for requested plate number or None if it
        doesn't exist.
        """
        return self._plates.get(number)

    def plateList(self):
        """
        Returns a sorted list of Plate objects for the study
        """
        pl = self._plates.values()
        pl.sort(key=lambda x: x.number())
        return pl

    def fieldsByUniqueID(self):
        '''
        Returns a dictionary of field unique ids
        '''
        fields={}
        for p in self._plates.values():
            field_list = p.fieldList()
            for f in field_list:
                fields[f.id()] = f

        return fields

    ########################################################################
    # Setup Related Functions
    ########################################################################
    def loadSetup(self, json_data):
        try:
            setup = json.loads(json_data)
        except ValueError:
            return False

        study = setup.get('study') or {}
        self.setup_name = study.get('name')
        self.number = study.get('number')

        ###################################################################
        # Load Styles
        ###################################################################
        for style in study.get('styles') or []:
            s = self.addStyle(style['styleName'])
            s.loadSetup(style)

        ###################################################################
        # Load Modules
        ###################################################################
        for module in study.get('modules') or []:
            m = self.addModule(module['name'], module['id'])
            m.description = module.get('description')
            for field in module.get('fields') or []:
                f = m.addField(field['id'])
                f.loadSetup(field)

            m.sortFields()

        ###################################################################
        # Load Plates
        ###################################################################
        for plate in study.get('plates') or []:
            p  = self.addPlate(plate['number'])
            p.description = plate.get('description')
            for moduleref in plate.get('moduleRefs') or []:
                mr = p.addModuleRef(moduleref['id'])
                mr.name = moduleref.get('name')
                mr.description = moduleref.get('description')
                mr.instance = moduleref.get('instance')
                mr.module = self._modulesById[moduleref.get('moduleId')]
                for fieldref in moduleref.get('fieldRefs') or []:
                    fr = mr.addFieldRef(fieldref['id'])
                    fr.loadSetup(fieldref)
                    fr.field = mr.module.fieldById(fieldref['fieldId'])

        return True

    ########################################################################
    # Visit Map Related Functions
    ########################################################################
    def loadVisitMap(self, visitmap_string):
        self._visitmap = VisitMap()
        return self._visitmap.load(visitmap_string)

    def visitLabel(self, visit):
        if self._visitmap == None:
            return "Visit {0}".format(visit)
        else:
            return self._visitmap.label(visit)
    def visitMap(self):
        return self._visitmap

    ########################################################################
    # Missing Map Related Functions
    ########################################################################
    def loadMissingMap(self, missingmap_string):
        return self._missingmap.load(missingmap_string)

    def missingValueLabel(self, code):
        return self._missingmap.label(code)

    ########################################################################
    # Centers Database Related Functions
    ########################################################################
    def loadCenters(self, centersdb_string):
        return self._centers.load(centersdb_string)

    def Centers(self):
        return self._centers

    ########################################################################
    # Countries Database Related Functions
    ########################################################################
    def loadCountries(self, countries_string):
        return self._countries.load(countries_string)

    def Countries(self):
        return self._countries

    ########################################################################
    # Domain Map Related Functions
    ########################################################################
    def loadDomainMap(self, domainmap_string):
        return self._domainmap.load(domainmap_string)

    def domainMap(self):
        return self._domainmap

    ########################################################################
    # Page Map Related Functions
    ########################################################################
    def loadPageMap(self, pagemap_string):
        self._pagemap = PageMap()
        return self._pagemap.load(pagemap_string)

    def pageLabel(self, visit, plate):
        label = None
        if self._pagemap != None:
            label = self._pagemap.label(visit, plate)
        if label == None:
            p = self.plate(plate)
            if p != None:
                label = p.description
            else:
                label = "Plate {0}".format(plate)
        return label

    ########################################################################
    # QC Related functions
    ########################################################################
    def qcType(self, value):
        if type(value) != int:
            value = int(value)

        if value == 1:
            return 'missing value'
        if value == 2:
            return 'illegal value'
        if value == 3:
            return 'inconsistent value'
        if value == 4:
            return 'illegible value'
        if value == 5:
            return 'fax noise'
        if value == 6:
            return 'other problem'
        if value == 21:
            return 'missing plate'
        if value == 22:
            return 'overdue visit'
        if value == 23:
            return 'EC missing plate'
        return 'unknown type'

    def qcStatus(self, value, simplify):
        if type(value) != int:
            value = int(value)

        if simplify:
            if value in [0,1,2,6,7]:
                return 'unresolved'
            else:
                return 'resolved'
        else:
            if value == 0:
                return 'unresolved(pending)'
            if value == 1:
                return 'unresolved(new)'
            if value == 2:
                return 'unresolved(in unsent report)'
            if value == 3:
                return 'resolved(NA)'
            if value == 4:
                return 'resolved(irrelevant)'
            if value == 5:
                return 'resolved(corrected)'
            if value == 6:
                return 'unresolved(in sent report)'
            if value == 7:
                return 'deleted'
        return 'unknown'

    ########################################################################
    # Reason Related functions
    ########################################################################
    def reasonStatus(self, value):
        if type(value) != int:
            value = int(value)

        if value == 1:
            return 'approved'
        if value == 2:
            return 'rejected'
        if value == 3:
            return 'pending'

    ########################################################################
    # Config Related Functions
    ########################################################################
    def loadServerConfig(self, config_string):
        self._config = {}
        server_config_lines = config_string.split('\n')
        for line in server_config_lines:
            config = line.split('=')
            if len(config) < 2:
                continue
            self._config[config[0]] = config[1]

    def studyName(self):
        name = self._config.get('STUDY_NAME')
        if name is None:
            name = self.setup_name
        return name

    ########################################################################
    # Load Configuration From Files
    ########################################################################
    def loadFromFiles(self, studydir):
        self.studydir = studydir
        try:
            self.loadServerConfig(
                open(os.path.join(studydir, 'lib/DFserver.cf'), 'r').read().decode('utf-8'))
        except IOError:
            pass
    
        try:
            self.loadSetup(
                open(os.path.join(studydir, 'lib/DFsetup'), 'r').read().decode('utf-8'))
        except IOError:
            pass

        try:
            self.loadVisitMap(
                open(os.path.join(studydir, 'lib/DFvisit_map'), 'r').read().decode('utf-8'))
        except IOError:
            pass

        try:
            self.loadPageMap(
                open(os.path.join(studydir, 'lib/DFpage_map'), 'r').read().decode('utf-8'))
        except IOError:
            pass

        try:
            self.loadMissingMap(
                open(os.path.join(studydir, 'lib/DFmissing_map'), 'r').read().decode('utf-8'))
        except IOError:
            pass

        try:
            self.loadCenters(
                open(os.path.join(studydir, 'lib/DFcenters'), 'r').read().decode('utf-8'))
        except IOError:
            pass

        try:
            self.loadCountries(
                open(os.path.join(studydir, 'lib/DFcountries'), 'r').read().decode('utf-8'))
        except IOError:
            pass

        try:
            self.loadDomainMap(
                open(os.path.join(studydir, 'lib/DFdomain_map'), 'r').read().decode('utf-8'))
        except IOError:
            pass
