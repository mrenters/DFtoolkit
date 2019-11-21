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

import os
import getopt
import codecs
import datafax
import sys
import xlsxwriter
import datetime
import StringIO
import smtplib,ssl

#####################################################################
# ECList - Generate an Excel sheet with a list of all fields and
#   edit checks attached to each one.
#####################################################################

#####################################################################
# Parse edit check string
#####################################################################
def validIdent(c):
    if c >= 'A' and c <= 'Z':
        return True
    if c >= 'a' and c <= 'z':
        return True
    if c >= '0' and c <= '9':
        return True
    if c == '_' or c == '@':
        return True

    return False

def parseEC(s):
    i = 0
    s_len = len(s)
    ecs = []
    while i < len(s):
        # Skip whitespace and other garbage until we get to start of EC name
        while i < s_len and not validIdent(s[i]):
            i += 1

        if i >= s_len:
            break;

        start = i

        # Scan EC name
        while i < s_len and validIdent(s[i]):
            i += 1

        # Only have EC name, no params
        if i >= s_len:
            ecs.append(s[start:i])
            break

        # If no params, continue to next EC
        if s[i] != '(':
            ecs.append(s[start:i])
            continue

        i += 1

        # Look for ending )
        in_quote = False
        in_backslash = False
        while i < s_len:
            if s[i] == '\\' and not in_backslash:
                in_backslash = True
                i += 1
                continue
            if s[i] == '"' and not in_backslash:
                in_quote ^= True
                i += 1
                continue

            if s[i] == ')' and not in_quote:
                i += 1
                break

            in_backslash = False
            i += 1

        ecs.append(s[start:i])
    return ecs

#####################################################################
# Convert QC data on stdin to Excel format
#####################################################################
def EC2Excel(config):
    studydir = config.get('studydir')
    if studydir == None:
        return
    #####################################################################
    # Load Study information
    #####################################################################
    study = datafax.Study()
    study.loadFromFiles(studydir)

    #####################################################################
    # Create spreadsheet and formatting information
    #####################################################################
    print('Creating Spreadsheet')
    workbook = xlsxwriter.Workbook(config.get('xlsx'))

    title_format = workbook.add_format(
        {   'font_color': 'white',
            'bg_color': '#4f81bd',
            'font_size': 36,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'border': 1
        })
    header_format = workbook.add_format(
        {   'bold': True,
            'font_color': 'white',
            'bg_color': '#244062',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
    category_format = workbook.add_format(
        {   'font_color': 'white',
            'bg_color': '#4f81bd',
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'border': 1
        })
    percent_format = workbook.add_format(
        {   'font_color': 'black',
            'bg_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'num_format': '0.0%',
            'border': 1
        })
    normal_format = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'num_format': '0',
            'border': 1
        })
    normal_format_str = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'num_format': '@',
            'border': 1
        })
    shaded_format = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'num_format': '0',
            'border': 1
        })
    shaded_format_str = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'num_format': '@',
            'border': 1
        })

    sheet = workbook.add_worksheet('ECs')
    row = 0

    sheet.set_column( 0, 0, 30)     # Page
    sheet.set_column( 1, 1, 10)     # Plate
    sheet.set_column( 2, 2, 10)     # Field#
    sheet.set_column( 3, 3, 25)     # Field
    sheet.set_column( 4, 4, 25)     # Style
    sheet.set_column( 5, 5, 40)     # EC
    row += 1
    start_table_row = row

    for p in study.plateList():
        for f in p.fieldList():
            ecs = []

            if f.plateEnter is not None:
                ecs.extend(parseEC(f.plateEnter))
            if f.fieldEnter is not None:
                ecs.extend(parseEC(f.fieldEnter))
            if f.fieldExit is not None:
                ecs.extend(parseEC(f.fieldExit))
            if f.plateExit is not None:
                ecs.extend(parseEC(f.plateExit))

            if len(ecs) == 0:
                continue

            for ec in ecs:
                sheet.write(row, 0, p.description)
                sheet.write(row, 1, p.number())
                sheet.write(row, 2, f.number)
                sheet.write(row, 3, f.name)
                sheet.write(row, 4, f.field.styleName)
                sheet.write(row, 5, ec)
                row += 1

    if row == start_table_row:
        row += 1
        sheet.write(row,0,'No edit checks defined')

    end_table_row = row

    sheet.add_table(start_table_row-1, 0, end_table_row-1, 5,
            {'autofilter': True, 'name': 'EC_Details',
                'columns': [
                {'header': 'Page', 'header_format': header_format},
                {'header': 'Plate', 'header_format': header_format},
                {'header': 'Fld #', 'header_format': header_format},
                {'header': 'Field', 'header_format': header_format},
                {'header': 'Style', 'header_format': header_format},
                {'header': 'EC', 'header_format': header_format},
            ]})

    #####################################################################
    # Add print formatting setup
    #####################################################################
    sheet.set_header("&LEC Report&C{0}&R&P of &N".format(study.studyName().replace("&", "&&")))
    sheet.set_landscape()
    sheet.set_paper(5)
    sheet.fit_to_pages(1,0)
    sheet.repeat_rows(0)

    #####################################################################
    # Protect sheet from changes and save
    #####################################################################
    sheet.hide_gridlines(2)
    sheet.set_zoom(100)
    print('Saving Spreadsheet')
    workbook.close()

#####################################################################
# Convert data on stdin to Excel format
#####################################################################
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:x:",
            [ 'studydir=', 'xls=', 'version'])
    except getopt.GetoptError, err:
        print(str(err))
        sys.exit(2)

    config = {}

    for o, a in opts:
        if o in ("-s", "--studydir"):
            config['studydir'] = a
        if o in ("-x", "--xls"):
            config['xlsx'] = a
        if o == '--version':
            print(datafax.__version__)
            sys.exit(0)

    if not config.get('studydir'):
        print('--studydir not specified')
        sys.exit(2)
    if not config.get('xlsx'):
        config['xlsx'] = config['studydir'] + '/work/eclist.xlsx'

    EC2Excel(config)

if __name__ == "__main__":
    main()
