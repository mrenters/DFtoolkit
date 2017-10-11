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
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders

#####################################################################
# Decode text as Unicode, and if that doesn't work, try Latin-1
#####################################################################
def to_unicode(s):
    try:
        u = s.decode('utf-8')
    except UnicodeDecodeError:
        u = s.decode('latin-1')
    return u

#####################################################################
# Load Priorities
#####################################################################
def load_priorities(studydir, name):
    priorities={}
    try:
        with open(os.path.join(studydir, 'lib', os.path.basename(name)), 'rU') as f:
            contents = f.read().decode('utf-8')
            for line in contents.split('\n'):
                rec = line.split('|')
                if len(rec) < 3:
                    continue
                if rec[0]=='Plate' and rec[1]=='Field' and rec[2]=='Priority':
                    continue
                try:
                    plate = int(rec[0])
                    field = int(rec[1])
                    priority = int(rec[2])
                    if priority < 1:
                        priority = 1
                    if priority > 5:
                        priority = 5
                    priorities[(plate,field)] = priority
                except ValueError:
                    print('Misformed priority record: ', line)
                    pass
    except IOError:
        print('Unable to open/read priorities file "{0}"'.format(name))
        sys.exit(2)
        pass
    return priorities

#####################################################################
# Convert QC data on stdin to Excel format
#####################################################################
def QC2Excel(config):
    priorities = {}
    studydir = config.get('studydir')
    if studydir == None:
        return
    centers_filter = config.get('centers')
    plates_filter = config.get('plates')
    visits_filter = config.get('visits')
    outstanding_only = config.get('outstanding')
    simplify = config.get('simplify')
    external = config.get('external')
    percent = config.get('percent')
    sitemode = config.get('sitemode')
    creation_date = config.get('creation_date')
    xlsx = config.get('xlsx')
    if xlsx is None:
        xlsx = 'qc.xlsx'

    priority_file = config.get('priority-file')
    if priority_file:
        priorities = load_priorities(studydir, priority_file)
    color_by_priority = config.get('color_by_priority')

    if simplify:
        status_labels = [ 'Pending',
            'Outstanding',
            'Resolved']
        problem_labels = ['Missing Value',
            'Illegal Value',
            'Inconsistent Value',
            'Illegible Value',
            'Fax Noise',
            'Other',
            'Missing Page',
            'Overdue Assessment']
    else:
        status_labels = [ 'Pending',
            'Outstanding(New)',
            'Outstanding(New, in report not sent)',
            'Resolved N/A',
            'Resolved Irrelevant',
            'Resolved Corrected',
            'Outstanding(New, in report sent)']
        problem_labels = ['Missing Value',
            'Illegal Value',
            'Inconsistent Value',
            'Illegible Value',
            'Fax Noise',
            'Other',
            'Missing Page',
            'Overdue Assessment',
            'EC Missing Page']

    agebin_labels = ['0-30 days', '31-60 days', '61-90 days', '91-120 days',
        '121-150 days', '151-180 days', '>180 days' ]
    priority_labels = [ 1, 2, 3, 4, 5 ]

    status_count = [ 0, 0, 0, 0, 0, 0, 0 ]
    problem_count = [ 0, 0, 0, 0, 0, 0, 0, 0, 0 ]
    agebin_count = [ 0, 0, 0, 0, 0, 0, 0 ]
    priority_count = [ 0, 0, 0, 0, 0 ]

    #####################################################################
    # Load Study information
    #####################################################################
    study = datafax.Study()
    print('Loading Study Configuration Files...')
    study.loadFromFiles(studydir)

    #####################################################################
    # Create spreadsheet and formatting information
    #####################################################################
    print('Creating Spreadsheet...')
    email = config.get('email')
    if email:
        output = StringIO.StringIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    else:
        workbook = xlsxwriter.Workbook(xlsx)

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
    normal_format_date = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'num_format': 'yyyy-mm-dd',
            'border': 1
        })
    normal_format_red = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'font_color': '#9c0006',
            'bg_color': '#ffc7ce',
            'text_wrap': True,
            'num_format': '0',
            'border': 1
        })
    normal_format_str_red = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'font_color': '#9c0006',
            'bg_color': '#ffc7ce',
            'text_wrap': True,
            'num_format': '@',
            'border': 1
        })
    normal_format_date_red = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'font_color': '#9c0006',
            'bg_color': '#ffc7ce',
            'text_wrap': True,
            'num_format': 'yyyy-mm-dd',
            'border': 1
        })
    normal_format_orange = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'font_color': '#3f3f76',
            'bg_color': '#ffcc99',
            'text_wrap': True,
            'num_format': '0',
            'border': 1
        })
    normal_format_str_orange = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'font_color': '#3f3f76',
            'bg_color': '#ffcc99',
            'text_wrap': True,
            'num_format': '@',
            'border': 1
        })
    normal_format_date_orange = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'font_color': '#3f3f76',
            'bg_color': '#ffcc99',
            'text_wrap': True,
            'num_format': 'yyyy-mm-dd',
            'border': 1
        })
    normal_format_yellow = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'font_color': '#9c6500',
            'bg_color': '#ffeb9c',
            'text_wrap': True,
            'num_format': '0',
            'border': 1
        })
    normal_format_str_yellow = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'font_color': '#9c6500',
            'bg_color': '#ffeb9c',
            'text_wrap': True,
            'num_format': '@',
            'border': 1
        })
    normal_format_date_yellow = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'font_color': '#9c6500',
            'bg_color': '#ffeb9c',
            'text_wrap': True,
            'num_format': 'yyyy-mm-dd',
            'border': 1
        })
    normal_format_green = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'font_color': '#006100',
            'bg_color': '#c6efce',
            'text_wrap': True,
            'num_format': '0',
            'border': 1
        })
    normal_format_str_green = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'font_color': '#006100',
            'bg_color': '#c6efce',
            'text_wrap': True,
            'num_format': '@',
            'border': 1
        })
    normal_format_date_green = workbook.add_format(
        {   'align': 'center',
            'valign': 'vcenter',
            'font_color': '#006100',
            'bg_color': '#c6efce',
            'text_wrap': True,
            'num_format': 'yyyy-mm-dd',
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

    sheet = workbook.add_worksheet('QCs')

    #####################################################################
    # Add title
    #####################################################################
    sheet.set_row(0,75)
    sheet.merge_range(0,0,0,17, 'QC Report for {0}'.format(study.studyName()),
           title_format)
    sheet.merge_range(1,0,1,17, 'Generated on {0}'.format(
        datetime.date.today().isoformat()), header_format)

    #####################################################################
    # Add space for charts
    #####################################################################
    sheet.set_row(2,230)
    sheet.merge_range(2,0,2,17, '', normal_format)

    #####################################################################
    # Add QC listing headers
    #####################################################################
    row = 3
    table_row = row
    #sheet.set_row(table_row, 36)

    hidden = {'hidden': 1}

    extra = 0

    if config.get('region'):
        sheet.set_column( 0, 0, 10)     # Region
    else:
        sheet.set_column( 0, 0, 10, options=hidden)     # Region
        extra += 12

    if config.get('country'):
        sheet.set_column( 1, 1, 10)     # Country
    else:
        sheet.set_column( 1, 1, 10, options=hidden)     # Country
        extra += 12
    
    if priority_file:
        sheet.set_column(10,10, 10)                    # Priority
    else:
        sheet.set_column(10,10, 10, options=hidden)    # Priority
        extra += 12

    if sitemode:
        sheet.set_column( 5, 5, 10, options=hidden)     # Visit
        sheet.set_column( 6, 6, 10, options=hidden)     # Plate
        sheet.set_column( 9, 9, 10, options=hidden)     # Field#
        if creation_date:
            sheet.set_column(11,11, 12, options=hidden)     # Creation date
        else:
            sheet.set_column(11,11, 10, options=hidden)     # Age
        extra += 50     # Gross up 25% bit
    else:
        sheet.set_column( 5, 5, 10)     # Visit
        sheet.set_column( 6, 6, 10)     # Plate
        sheet.set_column( 9, 9, 10)     # Field#
        if creation_date:
            sheet.set_column(11,11, 12) # Creation date
        else:
            sheet.set_column(11,11, 10) # Age

    sheet.set_column( 2, 2, 10)                 # Site
    sheet.set_column( 3, 3, 15)                 # Patient
    sheet.set_column( 4, 4, 25 + (extra/10))    # Assessment
    sheet.set_column( 7, 7, 25 + (extra/10))    # Page
    sheet.set_column( 8, 8, 25 + (extra/10))    # Field
    sheet.set_column(12,12, 10)                 # Age Bin
    sheet.set_column(13,13, 20)                 # Status
    sheet.set_column(14,14, 20)                 # Problem
    sheet.set_column(15,15, 20 + (extra/5))     # Value
    sheet.set_column(16,16, 20 + (extra/5))     # Query
    sheet.set_column(17,17, 20 + (extra/5))     # Reply

    row += 1
    start_table_row = row

    #####################################################################
    # Add QC listing
    #####################################################################
    today = datetime.date.today()
    print('Populating Data Table...')
    #stdin = codecs.getreader("utf-8")(sys.stdin)
    countries = study.Countries()
    for qc in sys.stdin:
        qc = to_unicode(qc)
        qcf = qc.split('|')

        center_num = int(qcf[8])
        visit_num = int(qcf[5])
        plate_num = int(qcf[4])

        plate = study.plate(plate_num)
        if plate == None:
            continue
        field = plate.fieldAt(int(qcf[7])+3)
        if field == None:
            continue

        fnum = field.number
        fname = field.description

        # If we have a plate/visit/center restrictions, enforce them now
        if centers_filter and not centers_filter.contains(center_num):
            continue
        if plates_filter and not plates_filter.contains(plate_num):
            continue
        if visits_filter and not visits_filter.contains(visit_num):
            continue

        # Check for external only
        if external and int(qcf[21]) == 2:
            continue

        status_code = int(qcf[0])

        # We don't count deleted records
        if status_code > 6:
            continue

        # Check whether this QC is resolved
        is_resolved = status_code >= 3 and status_code <= 5

        # If we're only interested in outstanding QCs
        if outstanding_only and is_resolved:
            continue
        if outstanding_only and sitemode and status_code == 0:
            continue

        problem_code = int(qcf[14])

        # Extract creation date
        cr_ts = qcf[18].split(' ')
        [year, month, day] = cr_ts[1].split('/')
        if int(year) > 90:
            year = int(year) + 1900
        else:
            year = int(year) + 2000
            
        cr_date = datetime.date(year, int(month), int(day))

        ######################################################
        # Calculate Age of QC
        ######################################################
        age = None
        agebin_str = None
        if not is_resolved:
            age = (today-cr_date).days
            agebin = int(age/30)
            if agebin > 6:
                agebin = 6

            agebin_count[agebin] += 1
            agebin_str = agebin_labels[agebin]

        ######################################################
        # Priority
        ######################################################
        priority = priorities.get((plate_num, fnum))
        if priority is None:
            priority = 5
        priority_count[priority-1] += 1
        (format_number, format_string, format_date) = \
                (normal_format, normal_format_str, normal_format_date)
        if color_by_priority and not is_resolved:
            if priority == 1:
                (format_number, format_string, format_date) = \
                (normal_format_red, normal_format_str_red,
                        normal_format_date_red)
            if priority == 2:
                (format_number, format_string, format_date) = \
                (normal_format_orange, normal_format_str_orange,
                        normal_format_date_orange)
            if priority == 3:
                (format_number, format_string, format_date) = \
                (normal_format_yellow, normal_format_str_yellow,
                        normal_format_date_yellow)
            if priority == 4:
                (format_number, format_string, format_date) = \
                (normal_format_green, normal_format_str_green,
                        normal_format_date_green)

        ######################################################
        # Problem code
        ######################################################
        if problem_code < 7:
            pname = problem_labels[problem_code-1]
            problem_count[problem_code-1] += 1
            value = qcf[13]
        else:
            # If simplify, map EC Missing Page -> Missing Page
            if simplify and problem_code == 23:
                problem_code = 21
            pname = problem_labels[problem_code-15]
            problem_count[problem_code-15] += 1
            value = None
            fnum = None         # Clear field number/name for output
            fname = None

        ######################################################
        # If simplify, map Outstanding* to Outstanding,
        # Resolved* to Resolved
        ######################################################
        if simplify and status_code != 0:
            if status_code in [1,2,6]:
                status_code = 1
            else:
                status_code = 2

        ######################################################
        # Output a row
        ######################################################
        sheet.write_string(row, 0, countries.region(center_num),
                format_string)
        sheet.write_string(row, 1, countries.country(center_num),
                format_string)
        sheet.write_number(row, 2, center_num, format_number)
        sheet.write_number(row, 3, int(qcf[6]), format_number)
        sheet.write_string(row, 4, study.visitLabel(int(qcf[5])),
            format_string)
        sheet.write_number(row, 5, visit_num, format_number)
        sheet.write_number(row, 6, plate_num, format_number)
        sheet.write(row, 7, study.pageLabel(visit_num, plate_num),
            format_string)
        sheet.write(row, 8, fname, format_string)
        sheet.write(row, 9, fnum, format_number)
        sheet.write(row, 10, priority, format_number)
        if creation_date:
            sheet.write_datetime(row, 11, cr_date, format_date)
        else:
            sheet.write(row, 11, age, format_number)
        sheet.write(row, 12, agebin_str, format_string)
        sheet.write_string(row, 13, status_labels[status_code], format_string)
        sheet.write_string(row, 14, pname, format_string)
        sheet.write(row, 15, value, format_string)
        sheet.write(row, 16, qcf[16], format_string)
        sheet.write(row, 17, qcf[11], format_string)

        status_count[status_code] += 1
        row += 1

    end_table_row = row
    # Make sure we have at least one row
    if start_table_row == end_table_row:
        end_table_row += 1
        row += 1
        sheet.merge_range(row,0,row,17, 'No Matching QC Records found',
           normal_format_str)
        row += 1

    if creation_date:
        creation_label = 'Created'
    else:
        creation_label = 'Days'
    sheet.add_table(start_table_row-1, 0, end_table_row-1, 17,
            {'autofilter': True, 'first_column': True, 'name': 'QC_Details',
                'columns': [
                {'header': 'Region', 'header_format': header_format},
                {'header': 'Country', 'header_format': header_format},
                {'header': 'Site', 'header_format': header_format},
                {'header': 'Patient', 'header_format': header_format},
                {'header': 'Assessment', 'header_format': header_format},
                {'header': 'Visit', 'header_format': header_format},
                {'header': 'Plate', 'header_format': header_format},
                {'header': 'Page', 'header_format': header_format},
                {'header': 'Field', 'header_format': header_format},
                {'header': 'Fld #', 'header_format': header_format},
                {'header': 'Priority', 'header_format': header_format},
                {'header': creation_label, 'header_format': header_format},
                {'header': 'Age', 'header_format': header_format},
                {'header': 'Status', 'header_format': header_format},
                {'header': 'Problem', 'header_format': header_format},
                {'header': 'Value', 'header_format': header_format},
                {'header': 'Query', 'header_format': header_format},
                {'header': 'Reply', 'header_format': header_format} ]})

    #####################################################################
    # Add data for charts
    #####################################################################
    print('Writing Charts...')
    row += 1

    # Totals
    sheet.merge_range(row,2,row,4, 'Total',
           header_format)
    row += 1
    sheet.write_formula(row, 3, '=SUBTOTAL(3,C{0}:C{1})'.format(
        start_table_row+1, end_table_row), shaded_format,
        end_table_row-start_table_row)
    sheet.write_string(row, 4, 'Selected Records', category_format)
    row +=2

    #####################################################################
    # Add charts
    #####################################################################
    charts = [
            { 'name': 'Status', 'column': 'N',
                'labels': status_labels, 'counts': status_count },
            { 'name': 'Problems', 'column': 'O',
                'labels': problem_labels, 'counts': problem_count },
            { 'name': 'Age', 'column': 'M',
                'labels': agebin_labels, 'counts': agebin_count },
            ]
    if priority_file:
            charts.append({ 'name': 'Priority', 'column': 'K',
                'labels': priority_labels, 'counts': priority_count })

    chart_width = 2000/len(charts)
    chart_x_offset = 5
    for chart in charts:
        sheet.merge_range(row,2,row,4, chart['name'],
           header_format)
        row += 1
        chart_start_row = row
        chart['start_row'] = chart_start_row
        sheet.write_column(row, 4, chart['labels'], category_format)
        column = chart['column']
        counts = chart['counts']
        for label in chart['labels']:
            l = label
            if type(label) is not int:
                l = '"'+label+'"'
            sheet.write_formula(row, 3,
                '=SUMPRODUCT(SUBTOTAL(3,OFFSET({0}{1}:{0}{2},ROW({0}{1}:{0}{2})-MIN(ROW({0}{1}:{0}{2})),,1)), --({0}{1}:{0}{2}={3}))'.format(column,
                start_table_row+1, end_table_row, l),
                shaded_format, counts[row-chart_start_row])
            if end_table_row - start_table_row == 0:
                value = 0
            else:
                value = counts[row-chart_start_row]/(end_table_row-start_table_row)

            sheet.write_formula(row, 2, '=IFERROR(D{0}/SUBTOTAL(3,D{1}:D{2}), 0)'.format(
                row+1,start_table_row+1, end_table_row),
                percent_format, value)
            row +=1

        chart_gap = 1000//len(chart['labels'])

        if percent:
            data_column = 'C'
        else:
            data_column = 'D'

        #####################################################################
        # Add chart to worksheet
        #####################################################################
        excel_chart = workbook.add_chart({'type': 'bar'})
        excel_chart.add_series({
            'values': '=QCs!${0}${1}:${0}${2}'.format(data_column,
                chart_start_row+1,
                chart_start_row+len(chart['labels'])),
            'categories': '=QCs!$E${0}:$E${1}'.format(chart_start_row+1,
                chart_start_row+len(chart['labels'])),
            'data_labels': {'value': True},
            'gap': chart_gap})
        excel_chart.set_title({'name': chart['name']})
        excel_chart.set_legend({'none': True})
        excel_chart.set_size({'width': chart_width, 'x_offset': chart_x_offset,
            'y_offset': 5})
        excel_chart.set_chartarea({'border': {'none': True}})
        sheet.insert_chart('A3', excel_chart)
        chart_x_offset += chart_width

        row += 1

    #####################################################################
    # Add print formatting setup
    #####################################################################
    sheet.set_header("&LQC Report&C{0}&R&P of &N".format(study.studyName().replace("&", "&&")))
    sheet.set_landscape()
    sheet.set_paper(5)
    sheet.fit_to_pages(1,0)
    sheet.repeat_rows(table_row)

    #####################################################################
    # Protect sheet from changes and save
    #####################################################################
    sheet.hide_gridlines(2)
    sheet.protect('',
        {   'autofilter': True,
            'sort': True,
            'select_locked_cells': True,
            'select_unlocked_cells': True
        })
    sheet.set_zoom(90)
    if xlsx and not email:
        print('Saving Spreadsheet to', xlsx, '...')

    workbook.close()

    if row >= 1048567:
        print('************************************************************')
        print('* WARNING: WORKSHEET HAS MORE THAN 1,048,567 ROWS WHICH')
        print('*          EXCEEDS EXCEL LIMIT. EXCEL WILL NOT RENDER')
        print('*          THIS SPREADSHEET CORRECTLY.')
        print('************************************************************')
        sys.exit(2)

    if email:
        emailfrom = config.get('emailfrom')
        if emailfrom is None:
            emailfrom = 'PHRI.donotreply@phri.ca'

        output.seek(0, os.SEEK_END)
        if output.tell() > 10*1024*1024:
            print('Excel file too large to email')
            return
        print('Emailing spreadsheet to:', email, '...')
        output.seek(0)
        msg = MIMEMultipart()
        msg['Subject'] = 'QC Report for {0}'.format(study.studyName())
        msg['From'] = emailfrom
        msg['To'] = email
        msg['Date'] = formatdate(localtime = True)
        msg.attach(MIMEText('QC Report for {0} is attached.\n'.format(study.studyName())))
        part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        part.set_payload(output.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="QC.xlsx"')
        msg.attach(part)

#        smtp = smtplib.SMTP('localhost', 25)
#        try:
#            smtp.sendmail('PHRI.donotreply@phri.ca', email, msg.as_string())
#        except:
#            print '*** EMAIL Could not be sent ***'
#        smtp.quit()

        sendmail = os.popen('/usr/sbin/sendmail -t', 'w')
        sendmail.write(msg.as_string())
        status = sendmail.close()
        if status is not None and status >> 8:
            print('*** EMAIL could not be sent ***', status)

#####################################################################
# Convert data on stdin to Excel format
#####################################################################
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:c:p:v:o",
            [ 'studydir=', 'centers=', 'plates=', 'visits=',
              'outstanding', 'simplify', 'external',
              'percent', 'site-mode', 'email=', 'email-to=', 'email-from=',
              'xlsx=', 'include-country', 'include-region',
              'priority-file=', 'color-by-priority', 'creation-date',
              'help'])
    except getopt.GetoptError, err:
        print(str(err))
        sys.exit(2)

    config = {}

    for o, a in opts:
        if o in ("-s", "--studydir"):
            if config.get('studydir'):
                print('Study directory previously specified, skipping')
            else:
                config['studydir'] = a
        if o in ("-c", "--centers"):
            rl = datafax.rangelist.RangeList(0, 21460)
            rl.fromString(a)
            config['centers'] = rl
        if o in ("-p", "--plates"):
            rl = datafax.rangelist.RangeList(0, 500)
            rl.fromString(a)
            config['plates'] = rl
        if o in ("-v", "--visits"):
            rl = datafax.rangelist.RangeList(0, 65535)
            rl.fromString(a)
            config['visits'] = rl
        if o in ("-o", "--outstanding"):
            config['outstanding'] = True
        if o == "--simplify":
            config['simplify'] = True
        if o == "--external":
            config['external'] = True
        if o == "--percent":
            config['percent'] = True
        if o == "--site-mode":
            config['sitemode'] = True
        if o == "--include-country":
            config['country'] = True
        if o == "--include-region":
            config['region'] = True
        if o == "--priority-file":
            config['priority-file'] = a
        if o == "--color-by-priority":
            config['color_by_priority'] = True
        if o == "--creation-date":
            config['creation_date'] = True
        if o in ("--email", "--email-to"):
            if config.get('email'):
                print('Email address previously specified, skipping')
            else:
                config['email'] = a
        if o == "--email-from":
            config['emailfrom'] = a
        if o == "--xlsx":
            if config.get('xlsx'):
                print('Output Excel previously specified, skipping')
            elif config.get('email'):
                print('Email previously selected, output Excel file name ignored')
            else:
                config['xlsx'] = a
        if o == "--help":
            print('QC2Excel Options')
            print('--centers range       Limit output to specified centers')
            print('--plates range        Limit output to specified plates')
            print('--visits range        Limit output to specified visits')
            print('--outstanding         Limit output to unresolved QCs')
            print('--simplify            Simplify QC states to pending/outstanding/resolved')
            print('                       and group Missing Page QCs (EC and QCupdate)')
            print('--external            Don\'t include internal QC notes')
            print('--percent             Show percentages in charts instead of counts')
            print('--site-mode           Simply for sites. Hides visit, plate, field')
            print('                       and age/creation date columns. If --outstanding')
            print('                       option also given, skip QCs in pending state')
            print('                       as those have been dealt with by site.')
            print('--include-country     Include country column based on DFcountries file')
            print('--include-region      Include region column based on DFcountries file')
            print('--priority-file name  Use file called name for field priority levels')
            print('--color-by-priority   Color the rows based on priority.')
            print('                       1=red, 2=orange, 3=yellow, 4=green, 5=blue')
            print('--creation-date       Replace QC age in days column with QC creation date')
            print('--email-to addr       Sets the email address to send report to.')
            print('--email-from addr     Sets the email address report will appear to come from.')

            # Flush stdin if it is coming from a file or pipe
            if not sys.stdin.isatty():
                for line in sys.stdin:
                    pass
            sys.exit(0)

    if not config.get('studydir'):
        print('--studydir not specified')
        sys.exit(2)

    if len(args):
        print('unexpected extraneous arguments found:', ' '.join(args))
        # Flush stdin if it is coming from a file or pipe
        if not sys.stdin.isatty():
            for line in sys.stdin:
                pass
        sys.exit(2)

    QC2Excel(config)

if __name__ == "__main__":
    main()
