#!/usr/bin/python
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
from __future__ import unicode_literals
from __future__ import print_function

import getopt
import json
import sys
import xlsxwriter

##############################################################################
# DataFax Setup File Difference Tool
#
# Author: Martin Renters, March 2016
##############################################################################

##############################################################################
# Setup Differences XLS handler
##############################################################################
class XLSX(object):
    """
    Writes an XLSX worksheet with setup differences
    """
    def __init__(self, name):
        self.detail_offset = 0
        self.name = name
        self.workbook = xlsxwriter.Workbook(self.name)
        self.header_format = self.workbook.add_format( \
            {   'bold': True, \
                'font_color': 'white', \
                'bg_color': 'gray', \
                'align': 'center', \
                'valign': 'vcenter', \
                'border': 1 \
            })
        self.low_format = self.workbook.add_format( \
            {   'font_color': 'black', \
                'bg_color': 'white', \
                'valign': 'vcenter', \
                'text_wrap': True, \
                'border': 1 \
            })
        self.med_format = self.workbook.add_format( \
            {   'font_color': '#9c6500', \
                'bg_color': '#ffeb9c', \
                'valign': 'vcenter', \
                'text_wrap': True, \
                'border': 1 \
            })
        self.high_format = self.workbook.add_format( \
            {   'font_color': '#9c0006', \
                'bg_color': '#ffc7ce', \
                'valign': 'vcenter', \
                'text_wrap': True, \
                'border': 1 \
            })

        self.global_sheet = self.workbook.add_worksheet('Globals')
        self.global_sheet.set_column( 0, 0, 30)
        self.global_sheet.set_column( 1, 1, 50)
        self.global_sheet.set_column( 2, 2, 50)
        self.global_sheet.set_column( 3, 3, 16)
        self.global_sheet.set_column( 4, 4, 50)
        self.global_sheet.set_column( 5, 5, 8)
        self.global_sheet.set_column( 6, 6, 40)

        self.global_sheet.write_row( 0, 0, ['Attribute',
            'Old Value', 'New Value', 'Impact', 'Impact Reason', 'nRec',
            'Plan'], self.header_format)


        self.globalFirstRow = 1

        self.style_sheet = self.workbook.add_worksheet('Styles')

        self.style_sheet.set_column( 0, 0, 16)
        self.style_sheet.set_column( 1, 1, 30)
        self.style_sheet.set_column( 2, 2, 50)
        self.style_sheet.set_column( 3, 3, 50)
        self.style_sheet.set_column( 4, 4, 16)
        self.style_sheet.set_column( 5, 5, 50)
        self.style_sheet.set_column( 6, 6, 8)
        self.style_sheet.set_column( 7, 7, 40)

        self.style_sheet.write_row( 0, 0, ['Style name', 'Operation',
            'Old Value', 'New Value', 'Impact', 'Impact Reason', 'nRec',
            'Plan'], self.header_format)

        self.styleFirstRow = 1

        self.module_sheet = self.workbook.add_worksheet('Modules')

        self.module_sheet.set_column( 0, 0, 16)
        self.module_sheet.set_column( 1, 1, 16)
        self.module_sheet.set_column( 2, 2, 30)
        self.module_sheet.set_column( 3, 3, 50)
        self.module_sheet.set_column( 4, 4, 50)
        self.module_sheet.set_column( 5, 5, 16)
        self.module_sheet.set_column( 6, 6, 50)
        self.module_sheet.set_column( 7, 7, 8)
        self.module_sheet.set_column( 8, 8, 40)

        self.module_sheet.write_row( 0, 0, ['Module name', 'Field Name',
            'Operation', 'Old Value', 'New Value', 'Impact', 'Impact Reason',
            'nRec', 'Plan'], self.header_format)

        self.moduleFirstRow = 1

        self.plate_sheet = self.workbook.add_worksheet('Plates')

        self.plate_sheet.set_column( 0, 0, 35)
        self.plate_sheet.set_column( 1, 1, 8)
        self.plate_sheet.set_column( 2, 2, 8)
        self.plate_sheet.set_column( 3, 3, 16)
        self.plate_sheet.set_column( 4, 4, 30)
        self.plate_sheet.set_column( 5, 5, 50)
        self.plate_sheet.set_column( 6, 6, 50)
        self.plate_sheet.set_column( 7, 7, 16)
        self.plate_sheet.set_column( 8, 8, 50)
        self.plate_sheet.set_column( 9, 9, 8)
        self.plate_sheet.set_column(10,10, 40)

        self.plate_sheet.write_row( 0, 0, [ 'Plate Description', 'Plate',
            'Field', 'Field Name', 'Operation', 'Old Value', 'New Value',
            'Impact', 'Impact Reason', 'nRec', 'Plan'], self.header_format)

        self.plate_sheet.activate()

        self.plateFirstRow = 1
        self.fieldFirstRow = 1

        self.fieldImpact = 0
        self.current_sheet = self.plate_sheet;
        self.plateRow = 1
        self.styleRow = 1
        self.moduleRow = 1
        self.globalRow = 1

    def close(self):
        self.plate_sheet.autofilter(0, 0, self.plateRow-1, 10)
        self.plate_sheet.freeze_panes(1,0)

        self.style_sheet.autofilter(0, 0, self.styleRow-1, 10)
        self.style_sheet.freeze_panes(1,0)

        self.module_sheet.autofilter(0, 0, self.moduleRow-1, 10)
        self.module_sheet.freeze_panes(1,0)

        self.global_sheet.autofilter(0, 0, self.globalRow-1, 10)
        self.global_sheet.freeze_panes(1,0)

        try:
            self.workbook.close()
            return 0
        except IOError as e:
            print('I/O error({0}): {1}: {2}'.format(e.errno, self.name, e.strerror))
            return -1

    def setPrintOptions(self, src_file, dst_file, dst_setup):
        for ws in [self.global_sheet, self.style_sheet,
                self.module_sheet, self.plate_sheet]:
            ws.set_landscape()
            ws.set_paper(5)
            ws.fit_to_pages(1,0)
            ws.repeat_rows(0)
            ws.set_header("&L{1}&C{0}&R&P of &N".format(dst_setup.get("name"), \
                ws.get_name()))
            ws.set_footer("&L{0}&C&D &T&R{1}".format(src_file.replace("&", "&&"), \
                dst_file.replace("&", "&&")))

    def format(self, impact):
        format = self.low_format
        if impact >= 5:
            format = self.med_format
        if impact >= 10:
            format = self.high_format
        return format

    def addedStyle(self, style):
        self.beginStyle(style)
        self.change('Style Added')
        self.endStyle()

    def deletedStyle(self, style):
        self.beginStyle(style)
        self.change('Style Deleted')
        self.endStyle()

    def addedModule(self, module):
        self.beginModule(module)
        self.change('Module Added')
        self.endModule()

    def deletedModule(self, module):
        self.beginModule(module)
        self.change('Module Deleted')
        self.endModule()

    def addedPlate(self, plate):
        self.beginPlate(plate)
        self.beginFieldRef(None)
        self.change('Plate Added');
        self.endFieldRef()
        self.endPlate()

    def deletedPlate(self, plate):
        self.beginPlate(plate)
        self.beginFieldRef(None)
        self.change('Plate Deleted', 10, reason='Data Loss');
        self.endFieldRef()
        self.endPlate()

    def change(self, op, impact=0, old=None, new=None, reason=None):
        format = self.format(impact)
        impact_text = "Low"
        if (impact >= 5):
            impact_text = "Med"
        if (impact >= 10):
            impact_text = "High"

        self.fieldImpact = max(self.fieldImpact, impact)

        # Cast to strings
        if old:
            old = '{0}'.format(old)
        if new:
            new = '{0}'.format(new)

        self.current_sheet.write(self.row, self.detail_offset, op, format)
        self.current_sheet.write(self.row, self.detail_offset+1, old, format)
        self.current_sheet.write(self.row, self.detail_offset+2, new, format)
        self.current_sheet.write(self.row, self.detail_offset+3, impact_text, format)
        self.current_sheet.write(self.row, self.detail_offset+4, reason, format)
        self.current_sheet.write(self.row, self.detail_offset+5, None, format)
        self.current_sheet.write(self.row, self.detail_offset+6, None, format)
        self.row += 1

    def compareNE(self, key, src, dst, op, impact, reason):
        if dst.get(key) != src.get(key):
            self.change(op, impact, src.get(key), dst.get(key), reason)

    def compareLT(self, key, src, dst, op, impact, reason):
        if dst.get(key) < src.get(key):
            self.change(op, impact, src.get(key), dst.get(key), reason)

    def compareGT(self, key, src, dst, op, impact, reason):
        if dst.get(key) > src.get(key):
            self.change(op, impact, src.get(key), dst.get(key), reason)

    def beginGlobals(self):
        self.row = self.globalRow
        self.current_sheet = self.global_sheet
        self.fieldImpact = 0
        self.detail_offset = 0

    def endGlobals(self):
        self.globalRow = self.row

    def beginStyle(self, style):
        self.style = style
        self.row = self.styleRow
        self.styleFirstRow = self.row
        self.current_sheet = self.style_sheet
        self.fieldImpact = 0
        self.detail_offset = 1

    def endStyle(self):
        style_name = self.style['styleName']
        self.style = None
        format = self.format(self.fieldImpact)

        # Write out field information, merging cells if necessary
        if self.row > self.styleFirstRow:
            if self.row > self.styleFirstRow + 1:
                self.style_sheet.merge_range(self.styleFirstRow, 0, \
                    self.row-1, 0, style_name, format)
            for r in range(self.styleFirstRow, self.row):
                self.style_sheet.write(r, 0, style_name, format)
        self.styleRow = self.row

    def beginModule(self, module):
        self.module = module
        self.row = self.moduleRow;
        self.moduleFirstRow = self.row
        self.moduleImpact = 0
        self.current_sheet = self.module_sheet
        self.detail_offset = 2

    def endModule(self):
        module_name = self.module['name']
        self.module = None
        format = self.format(self.moduleImpact)

        # Write out field information, merging cells if necessary
        if self.row > self.moduleFirstRow:
            if self.row > self.moduleFirstRow + 1:
                self.module_sheet.merge_range(self.moduleFirstRow, 0, \
                    self.row-1, 0, module_name, format)
            for r in range(self.moduleFirstRow, self.row):
                self.module_sheet.write(r, 0, module_name, format)
        self.moduleRow = self.row

    def beginField(self, field):
        self.field = field
        self.fieldFirstRow = self.row
        self.fieldImpact = 0

    def endField(self):
        if self.field:
            field_name = self.field['name']
        else:
            field_name = ""

        self.field = None
        format = self.format(self.fieldImpact)

        # Write out field information, merging cells if necessary
        if self.row > self.fieldFirstRow:
            if self.row > self.fieldFirstRow + 1:
                self.module_sheet.merge_range(self.fieldFirstRow, 1, \
                    self.row-1, 1, field_name, format)
            for r in range(self.fieldFirstRow, self.row):
                self.module_sheet.write(r, 1, field_name, format)

        self.moduleImpact = max(self.moduleImpact, self.fieldImpact)

    def beginPlate(self, plate):
        self.plate = plate
        self.row = self.plateRow;
        self.plateFirstRow = self.row
        self.plateImpact = 0
        self.current_sheet = self.plate_sheet
        self.detail_offset = 4

    def endPlate(self):
        plate_desc = self.plate['description']
        plate_num = self.plate['number']
        self.plate = None
        format = self.format(self.plateImpact)

        # Write out field information, merging cells if necessary
        if self.row > self.plateFirstRow:
            if self.row > self.plateFirstRow + 1:
                self.plate_sheet.merge_range(self.plateFirstRow, 0, \
                    self.row-1, 0, plate_desc, format)
                self.plate_sheet.merge_range(self.plateFirstRow, 1, \
                    self.row-1, 1, plate_num, format)
            for r in range(self.plateFirstRow, self.row):
                self.plate_sheet.write(r, 0, plate_desc, format)
                self.plate_sheet.write(r, 1, plate_num, format)
        self.plateRow = self.row

    def beginFieldRef(self, field):
        self.field = field
        self.fieldFirstRow = self.row
        self.fieldImpact = 0

    def endFieldRef(self):
        if self.field:
            field_name = self.field['name']
            field_number = self.field['number']
        else:
            field_name = ""
            field_number = None

        self.field = None
        format = self.format(self.fieldImpact)

        # Write out field information, merging cells if necessary
        if self.row > self.fieldFirstRow:
            if self.row > self.fieldFirstRow + 1:
                self.plate_sheet.merge_range(self.fieldFirstRow, 2, \
                    self.row-1, 2, field_number, format)
                self.plate_sheet.merge_range(self.fieldFirstRow, 3, \
                    self.row-1, 3, field_name, format)
            for r in range(self.fieldFirstRow, self.row):
                self.plate_sheet.write(r, 2, field_number, format)
                self.plate_sheet.write(r, 3, field_name, format)

        self.plateImpact = max(self.plateImpact, self.fieldImpact)

##############################################################################
# Resolve references to Fields and Styles from FieldRefs
##############################################################################
def resolveReferences(study):
    """
    Resolved references from FieldRefs to Fields/Styles in a Setup
    """
    fields = {}

    # Build a hash of the fields
    for m in study.get('modules'):
        for f in m.get('fields'):
            fields[f['id']] = f

    # Resolve missing tags from fields to fieldRefs
    for p in study.get('plates'):
        mrs = p.get('moduleRefs')
        if mrs:
            for m in mrs:
                frs = m.get('fieldRefs')
                if frs:
                    for fr in m.get('fieldRefs'):
                        fid = fr.get('fieldId')
                        for f in fields[fid]:
                            if f not in fr:
                                fr[f] = fields[fid][f]
    return study

##############################################################################
# Load a DataFax Setup File
##############################################################################
def loadSetup(name):
    """
    Loads a DataFax JSON format setup file
    """
    try:
        setup_file = open(name)
    except IOError as e:
        print('I/O error({0}): {1} {2}'.format(e.errno, name, e.strerror))
        return None

    try:
        setup = json.load(setup_file)
    except ValueError:
        return None

    if 'study' in setup:
        return resolveReferences(setup['study'])

    return None


##############################################################################
# Get a List of Modules from a Study
##############################################################################
def modules(study, user_only=True):
    """
    Returns a sorted list of Modules in a study
    """
    moduleList = [];
    if 'modules' in study:
        for module in study['modules']:
            if user_only and module.get('name') == "DFSYSTEM":
                continue;
            moduleList.append(module)

    moduleList.sort(cmp=lambda x,y: cmp(x['name'].lower(), y['name'].lower()))
    return moduleList

##############################################################################
# Get a List of Fields from a Module
##############################################################################
def fields(module):
    """
    Returns a sorted list of Fields in a module
    """
    fieldList = [];
    if 'fields' in module:
        for field in module['fields']:
            fieldList.append(field)

    fieldList.sort(cmp=lambda x,y: cmp(x['name'].lower(), y['name'].lower()))
    return fieldList

##############################################################################
# Get a List of FieldRefs from a Plate
##############################################################################
def fieldRefs(plate, user_only):
    """
    Returns a sorted list of FieldRefs in a plate
    """
    fieldList = [];
    if 'moduleRefs' in plate:
        for moduleRef in plate['moduleRefs']:
            if user_only and moduleRef.get('name') == "DFSYSTEM":
                continue;
            if 'fieldRefs' in moduleRef:
                for fieldRef in moduleRef['fieldRefs']:
                    fieldRef['moduleName'] = moduleRef.get('name')
                    fieldRef['moduleInstance'] = moduleRef.get('instance')
                    fieldList.append(fieldRef)

    fieldList.sort(cmp=lambda x,y: cmp(x['number'], y['number']))
    return fieldList

##############################################################################
# Get Coding String
##############################################################################
def coding(codes, i):
    s = "option: " + str(i) + ", code: " + str(codes[i]['number']) + ", label: " + \
            codes[i]['label']
    return s

##############################################################################
# Get Boxes String
##############################################################################
def boxes(rects, i):
    s = "box: " + str(i) + ", x: " + str(rects[i]['x']) + ", y: " + \
            str(rects[i]['y']) + ", w: " + str(rects[i]['w']) + ", h: " + \
            str(rects[i]['h'])
    return s

##############################################################################
# Compare two fields
##############################################################################
def compareField(xls, fs, f, is_plate):
    xls.compareNE('moduleName', fs, f, 'Module Name', 5, \
            "Review Edit Checks and SAS Exports")
    xls.compareNE('moduleInstance', fs, f, 'Module Instance', 5, \
            "Review Edit Checks and SAS Exports")
    if is_plate:
        xls.compareNE('number', fs, f, 'Field Number', 5, \
            "Review Edit Checks and SAS Exports")
    xls.compareNE('name', fs, f, 'Field Name', 5, \
            "Review Edit Checks and SAS Exports")
    xls.compareNE('alias', fs, f, 'Field Alias', 5,
            "Review SAS Exports")
    xls.compareNE('description', fs, f, 'Description', 5, "")
    xls.compareNE('type', fs, f, 'Data Type', 10, \
            "Potential Data Loss, Review EC/SAS")
    xls.compareNE('styleName', fs, f, 'Style Change', 0, "")
    xls.compareNE('required', fs, f, 'Required/Optional/Essential', 5, \
            "Potential Data Meaning Change")
    xls.compareNE('legal', fs, f, 'Legal Range', 5, "")
    xls.compareNE('format', fs, f, 'Format', 5, \
            "Potential Data Loss, Review SAS exports")
    xls.compareNE('help', fs, f, 'Field Help', 0, "")
    xls.compareNE('prompt', fs, f, 'Prompt', 0, "")
    xls.compareNE('comment', fs, f, 'Comment', 0, "")
    xls.compareNE('units', fs, f, 'Units', 0, "")
    xls.compareNE('constant', fs, f, 'Constant Value', 10,
            "Potential Data Loss, Review Edit Checks/SAS")
    xls.compareNE('constantValue', fs, f, 'Constant Value', 10,
            "Potential Data Loss, Review Edit Checks/SAS")
    xls.compareNE('yearCutoff', fs, f, 'Cutoff Year', 10, \
            "Potential Data Meaning Change")
    xls.compareNE('dateRounding', fs, f, 'Date Imputation', 10, \
            "Potential Data Meaning Change")
    xls.compareNE('use', fs, f, 'Field Use', 10, \
            "Potential Data Meaning Change")
    xls.compareNE('blinded', fs, f, 'Hidden/Blinded', 0, "")
    xls.compareNE('level', fs, f, 'Reason Level', 0, "")
    xls.compareNE('reasonIfNonBlank', fs, f, 'Reason if non Blank', 0,
            "")
    xls.compareNE('mapping', fs, f, 'Field Mapping', 10, "May invalidate Data")
    xls.compareNE('display', fs, f, 'Display Length', 0, "")
    xls.compareLT('store', fs, f, 'Store Length', 10, \
            "Field Store Length Reduced, Potential Data Loss, Review SAS Exports")
    xls.compareGT('store', fs, f, 'Store Length', 0, \
            "Field Store Length Increased")
    xls.compareNE('skipTo', fs, f, 'Skip Pattern', 0, "")
    xls.compareNE('plateEnter', fs, f, 'Plate Enter EC', 0, "")
    xls.compareNE('fieldEnter', fs, f, 'Field Enter EC', 0, "")
    xls.compareNE('fieldExit', fs, f, 'Field Exit EC', 0, "")
    xls.compareNE('plateExit', fs, f, 'Plate Exit EC', 0, "")

    # Check Coding
    s_len = 0
    d_len = 0
    if 'codes' in fs:
        s_len = len(fs['codes'])
    if 'codes' in f:
        d_len = len(f['codes'])
    for i in range(0, min(s_len, d_len)):
        src = coding(fs['codes'], i)
        dst = coding(f['codes'], i)
        if src != dst:
            xls.change("Coding Change", 10, src, dst,
                   "May invalidate Data. Review EC/SAS")
    for i in range(d_len, s_len):
        src = coding(fs['codes'], i)
        xls.change("Coding Deleted", 10, src, "",
               "May invalidate Data. Review EC/SAS")
    for i in range(s_len, d_len):
        dst = coding(f['codes'], i)
        xls.change("Coding Added", 0, "", dst, "")

    # Check Boxes
    s_len = 0
    d_len = 0
    if 'rects' in fs:
        s_len = len(fs['rects'])
    if 'rects' in f:
        d_len = len(f['rects'])
    for i in range(0, min(s_len, d_len)):
        src = boxes(fs['rects'], i)
        dst = boxes(f['rects'], i)
        if src != dst:
            xls.change("Field Boxes Changed", 0, src, dst,
                   "Review all backgrounds to ensure they match")
    for i in range(d_len, s_len):
        src = boxes(fs['rects'], i)
        xls.change("Field Box Deleted", 0, src, "",
               "Review all backgrounds to ensure they match")
    for i in range(s_len, d_len):
        dst = boxes(f['rects'], i)
        xls.change("Field Box Added", 0, "", dst,
               "Review all backgrounds to ensure they match")

##############################################################################
# Compare two modules
##############################################################################
def compareModule(xls, src, dst):
    """
    Compares two modules
    """
    src_fields = fields(src)
    dst_fields = fields(dst)
    # Make src/dst hashes based on id
    src_hash = {}
    dst_hash = {}
    for f in src_fields:
        src_hash[f['id']] = f
    for f in dst_fields:
        dst_hash[f['id']] = f

    # Module level differences
    xls.beginField(None)
    xls.compareNE('description', src, dst, 'Module Description Changed', 0, "")
    xls.endField()

    # Find fields that were deleted
    for f in src_fields:
        if f['id'] not in dst_hash:
            xls.beginField(f)
            xls.change("Field Deleted", impact=10, old=f['name'], \
                reason="Possible Data Loss")
            xls.endField()

    # Find fields that were added/changed
    for f in dst_fields:
        xls.beginField(f)
        fs = src_hash.get(f['id'])
        if fs:
            compareField(xls, fs, f, True)
        else:
            xls.change("Field Added", impact=0, new=f['name'])

        xls.endField()

##############################################################################
# Compare two plates
##############################################################################
def comparePlate(xls, src, dst, user_only=True):
    """
    Compares two plates
    """
    src_fields = fieldRefs(src, user_only)
    dst_fields = fieldRefs(dst, user_only)
    # Make src/dst hashes based on id
    src_hash = {}
    dst_hash = {}
    for f in src_fields:
        src_hash[f['id']] = f
    for f in dst_fields:
        dst_hash[f['id']] = f

    # Plate level differences
    xls.beginFieldRef(None)
    xls.compareNE('description', src, dst, 'Plate Description Changed', 0, "")
    xls.compareNE('arrivalTrigger', src, dst, 'Arrival Trigger Changed', 0, "")
    xls.compareNE('termPlate', src, dst, 'Termination Plate State', 5, "")
    xls.compareNE('icr', src, dst, 'ICR State', 0, "")
    xls.compareNE('eligibleForSigning', src, dst, 'Signing Eligibility', 0, "")
    xls.compareNE('sequenceCoded', src, dst, 'Sequence Number location', 10, "")
    xls.endFieldRef()

    # Find fields that were deleted
    for f in src_fields:
        if f['id'] not in dst_hash:
            xls.beginFieldRef(f)
            xls.change("Field Deleted", impact=10, old=f['name'], \
                reason="Data Loss")
            xls.endFieldRef()

    # Find fields that were added/changed
    for f in dst_fields:
        xls.beginFieldRef(f)
        fs = src_hash.get(f['id'])
        if fs:
            compareField(xls, fs, f, True)
        else:
            xls.change("Field Added", impact=5, new=f['name'], \
                    reason="Review Edit Checks, Ask Sites for Data")

        xls.endFieldRef()


##############################################################################
# Get a list of plates from a Study
##############################################################################
def plates(study):
    if study and 'plates' in study:
        return study['plates']
    else:
        return []

##############################################################################
# Get a sorted list of styles from a Study
##############################################################################
def styles(study):
    if study and 'styles' in study:
        styles = []
        for s in study['styles']:
            styles.append(s)
        styles.sort(cmp=lambda x,y: cmp(x['styleName'].lower(), y['styleName'].lower()))
        return styles
    else:
        return []

##############################################################################
# Compare two studies
##############################################################################
def compareStudies(xls, src, dst, user_only=True):
    """
    Compares two studies
    """
    ################################################
    # Compare Globals
    ################################################
    xls.beginGlobals()
    xls.compareNE('number', src, dst, 'Study Number', 0, "")
    xls.compareNE('name', src, dst, 'Study Name', 0, "")
    xls.compareNE('created', src, dst, 'Setup File Save Date', 0, "")
    xls.compareNE('creator', src, dst, 'File Creator', 0, "")
    xls.compareNE('version', src, dst, 'File Format Version', 0, "")
    xls.compareNE('createVersion', src, dst, 'Original Setup Creation Version', 0, "")
    xls.compareNE('modifyVersion', src, dst, 'Saving DFsetup tool version', 0, "")
    xls.compareNE('developmentStudy', src, dst, 'Development Study', 0, "")
    xls.compareNE('productionStudy', src, dst, 'Production Study', 0, "")
    xls.compareNE('startYear', src, dst, 'Study Start Year', 0, "")
    xls.compareNE('yearCutoff', src, dst, 'Default Pivot Year', 5, "Possible Meaning Change")
    xls.compareNE('dateRounding', src, dst, 'Date Rounding', 5, "Possible Meaning Change")

    xls.compareNE('autoReason', src, dst, 'Reasons', 0, "")
    xls.compareNE('crfGuides', src, dst, 'CRF Guides', 0, "")
    xls.compareNE('uniqueFieldNames', src, dst, 'Unique Field Names', 0, "")
    xls.compareNE('boxHeight', src, dst, 'Box Height', 0, "")
    xls.compareNE('addPidEnabled', src, dst, 'Add Patient Enabled', 0, "")
    xls.compareNE('snap', src, dst, 'Box Snap', 0, "")
    xls.compareNE('varGuides', src, dst, 'Variable Guides', 0, "")
    xls.compareNE('pidCount', src, dst, 'Extra Patients to Show', 0, "")
    xls.compareNE('viewModeEc', src, dst, 'Execute Edit Checks in View-Only Mode', 0, "")
    xls.compareNE('descriptionLen', src, dst, 'Description Length', 0, "")
    xls.compareNE('autoHelp', src, dst, 'Auto Help', 0, "")
    try:
        src_levels = src['levels']
        dst_levels = dst['levels']
        for i in range(8):
            if src_levels[i]['label'] != dst_levels[i]['label']:
                xls.change('Label for Validation Level ' + str(i), 0,
                        src_levels[i]['label'], dst_levels[i]['label'])
    except:
        pass
    xls.endGlobals()

    ################################################
    # Compare Styles
    ################################################
    src_idx = 0
    src_styles = styles(src)
    src_len = len(src_styles)

    dst_idx = 0
    dst_styles = styles(dst)
    dst_len = len(dst_styles)

    # Compare styles until one list ends
    while src_idx < src_len and dst_idx < dst_len:
        src_name = src_styles[src_idx]['styleName']
        dst_name = dst_styles[dst_idx]['styleName']
        if src_name < dst_name:
            xls.deletedStyle(src_styles[src_idx])
            src_idx += 1
        elif src_name > dst_name:
            xls.addedStyle(dst_styles[dst_idx])
            dst_idx += 1
        else:
            xls.beginStyle(dst_styles[dst_idx])
            compareField(xls, src_styles[src_idx], dst_styles[dst_idx], False)
            xls.endStyle()
            src_idx += 1
            dst_idx += 1

    # If we still have src styles, then they were deleted
    for i in range(src_idx, src_len):
        xls.deletedStyle(src_styles[i])

    # If we still have dst styles, then they were added
    for i in range(dst_idx, dst_len):
        xls.addedStyle(dst_styles[i])

    ################################################
    # Compare Modules
    ################################################
    src_idx = 0
    src_modules = modules(src, user_only)
    src_len = len(src_modules)

    dst_idx = 0
    dst_modules = modules(dst, user_only)
    dst_len = len(dst_modules)

    # Compare plates until one list ends
    while src_idx < src_len and dst_idx < dst_len:
        src_num = src_modules[src_idx]['name']
        dst_num = dst_modules[dst_idx]['name']
        if src_num < dst_num:
            xls.deletedModule(src_modules[src_idx])
            src_idx += 1
        elif src_num > dst_num:
            xls.addedModule(dst_modules[dst_idx])
            dst_idx += 1
        else:
            xls.beginModule(dst_modules[dst_idx])
            compareModule(xls, src_modules[src_idx], dst_modules[dst_idx])
            xls.endModule()
            src_idx += 1
            dst_idx += 1

    # If we still have src modules, then they were deleted
    for i in range(src_idx, src_len):
        xls.deletedModule(src_modules[i])

    # If we still have dst modules, then they were added
    for i in range(dst_idx, dst_len):
        xls.addedModule(dst_modules[i])

    ################################################
    # Compare Plates
    ################################################
    src_idx = 0
    src_plates = plates(src)
    src_len = len(src_plates)

    dst_idx = 0
    dst_plates = plates(dst)
    dst_len = len(dst_plates)

    # Compare plates until one list ends
    while src_idx < src_len and dst_idx < dst_len:
        src_num = src_plates[src_idx]['number']
        dst_num = dst_plates[dst_idx]['number']
        if src_num < dst_num:
            xls.deletedPlate(src_plates[src_idx])
            src_idx += 1
        elif src_num > dst_num:
            xls.addedPlate(dst_plates[dst_idx])
            dst_idx += 1
        else:
            xls.beginPlate(dst_plates[dst_idx])
            comparePlate(xls, src_plates[src_idx], dst_plates[dst_idx], \
                user_only)
            xls.endPlate()
            src_idx += 1
            dst_idx += 1

    # If we still have src plates, then they were deleted
    for i in range(src_idx, src_len):
        xls.deletedPlate(src_plates[i])

    # If we still have dst plates, then they were added
    for i in range(dst_idx, dst_len):
        xls.addedPlate(dst_plates[i])


##############################################################################
# Do a Setup Difference
##############################################################################
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "o:c:x:u",
                [ "original=", "current=", "xlsx=", "useronly" ])
    except getopt.GetoptError, err:
        print(str(err))
        sys.exit(2)

    src = None
    dst = None
    excel = "setupdiff.xlsx"
    user_only = False

    for o, a in opts:
        if o in ("-o", "--original"):
            src = a
        elif o in ("-c", "--current"):
            dst = a
        elif o in ("-x", "--xlsx"):
            excel = a
        elif o in ("-u", "--useronly"):
            user_only = True

    # Make sure we have at least the two DFsetup files
    if not src:
        print('--original not specified')
        sys.exit(2)
    if not dst:
        print('--current not specified')
        sys.exit(2)

    print('Opening XLSX file')
    xls = XLSX(excel);
    print('Loading src setup file')
    src_setup = loadSetup(src)
    print('Loading dst setup file')
    dst_setup = loadSetup(dst)
    print('Comparing setups')
    compareStudies(xls, src_setup, dst_setup, user_only)
    print('Closing XLSX file')
    xls.setPrintOptions(src, dst, dst_setup)
    xls.close()

if __name__ == "__main__":
    main()
