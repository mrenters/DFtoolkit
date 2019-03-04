#!/opt/datafax/PHRI/python27
#
# Copyright 2017-2019, Population Health Research Institute
# Copyright 2017-2019, Martin Renters
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

##############################################################################
# Generate study closeout PDFs from an SQL database
##############################################################################

from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, blue, green, cyan, yellow, \
    magenta, orange, purple, black, white, darkgrey, darkslategrey, \
    lightgrey, darkblue, dimgrey, HexColor
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import Paragraph, Frame, Table, TableStyle, \
    KeepTogether, Flowable, SimpleDocTemplate, PageBreak
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, \
    LayoutError
from reportlab.platypus.tableofcontents import TableOfContents

from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl

from collections import namedtuple

import os
import time
import getopt
import sys
import re
import datafax
import sqlite3
import getpass
from PIL import Image


##############################################################################
# formatPID - Format a patient ID
##############################################################################
def formatPID(format_pid, pid_num):
    if format_pid is None:
        return str(pid_num)
    n = 0
    for i in range(0, len(format_pid)):
        if format_pid[i] == '#':
            n += 1
    pid_zero = str(pid_num).zfill(n)
    n = 0
    pid_str = ''
    for i in range(0, len(format_pid)):
        if format_pid[i] == '#':
            pid_str += pid_zero[n]
            n += 1
        else:
            pid_str += format_pid[i]

    # If there are still digits left, tack them on the end.
    if len(pid_zero) > n:
        pid_str += pid_zero[n:]
    return pid_str

##############################################################################
# stylesheet - Stylesheet for document
##############################################################################
def stylesheet(fontsize, leading):
    styles= {
        'default': ParagraphStyle(
            'default',
            fontName='Helvetica',
            fontSize=fontsize,
            leading=leading,
            leftIndent=0,
            rightIndent=0,
            firstLineIndent=0,
            alignment=TA_LEFT,
            spaceBefore=0,
            spaceAfter=0,
            bulletFontName='Helvetica',
            bulletFontSize=10,
            bulletIndent=0,
            textColor= black,
            backColor=None,
            wordWrap=None,
            borderWidth= 0,
            borderPadding= 0,
            borderColor= None,
            borderRadius= None,
            allowWidows= 1,
            allowOrphans= 0,
            textTransform=None,  # 'uppercase' | 'lowercase' | None
            endDots=None,         
            splitLongWords=1,
        ),
    }
    styles['indented'] = ParagraphStyle(
        'indented',
        parent=styles['default'],
        firstLineIndent = -10,
        leftIndent = 10,
    )
    styles['title'] = ParagraphStyle(
        'title',
        parent=styles['default'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        #textColor=darkblue,
        textColor=black,
    )
    styles['header'] = ParagraphStyle(
        'header',
        parent=styles['default'],
        borderColor=black,
        borderWidth=1,
        borderPadding=5,
    )
    styles['audit_header'] = ParagraphStyle(
        'audit_header',
        parent=styles['default'],
        fontName='Helvetica-Bold',
        #textColor=darkblue,
        textColor=black,
        fontSize=12,
        leading=16,
        spaceBefore=10,
    )
    styles['alert'] = ParagraphStyle(
        'alert',
        parent=styles['default'],
        leading=14,
        backColor=yellow,
        borderColor=black,
        borderWidth=1,
        borderPadding=5,
        borderRadius=2,
        spaceBefore=10,
        spaceAfter=10,
    )
    return styles

##############################################################################
# DFOutlines - Outlines
##############################################################################
class DFOutlines(Flowable):
    def __init__(self, outlines):
        self.outlines = outlines

    def wrap(self, *args):
        return (0,0)

    def draw(self):
        canvas = self.canv
        for o in self.outlines:
            canvas.addOutlineEntry(o[0], o[1], o[2], o[3])

        canvas.showOutline()

##############################################################################
# DFimage - DataFax Image Representation
##############################################################################
class DFimage(Flowable):
    def __init__(self, size, path, label):
        if size is None:
            size = (6.3*inch, 8.2*inch)
        self.size = size
        self.path = path
        self.label = label

    def wrap(self, *args):
        return self.size

    def draw(self):
        where = (0, 0, self.size[0], self.size[1]-0.25)
        canvas = self.canv

        canvas.setStrokeColor(black)
        canvas.setFillColor(black)
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(where[2]/2, 0*inch, self.label)

        try:
            img = Image.open(self.path)
        except IOError:
            print('image {0} unsupported format'.format(self.path))
            return

        if img is None:
            i_w, i_h = (864, 1100)
        else:
            i_w, i_h = img.size

        # Calculate scaling and translation for background image
        window_width = where[2]
        window_height = where[3]
        x_scale = float(where[2])/i_w
        y_scale = float(where[3]-25)/i_h

        scale = x_scale
        if x_scale > y_scale:
            scale = y_scale

        translate_x = (where[2]-(i_w*scale))/2
        translate_y = (where[3]-(i_h*scale))
        canvas.translate(where[0]+translate_x, where[1]+translate_y)
        canvas.scale(scale, scale)

        # If we have a background image, draw it now
        if img:
            try:
                canvas.drawImage(self.path, 0, 0)
            except IOError:
                print('unable to draw', self.path)

        canvas.setStrokeColor(black)

        # Draw image bounding box
        canvas.rect(0, 0, i_w, i_h)


##############################################################################
# DFXObj - PDF XObj page
##############################################################################
class DFXObj(Flowable):
    def __init__(self, size, page, label):
        if size is None:
            size = (6.3*inch, 8.2*inch)
        self.size = size
        self.page = page
        self.label = label

    def wrap(self, *args):
        return self.size

    def draw(self):
        where = (0, 0, self.size[0], self.size[1]-0.25)
        canvas = self.canv

        canvas.setStrokeColor(black)
        canvas.setFillColor(black)
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(where[2]/2, 0*inch, self.label)

        i_w, i_h = self.page.BBox[2], self.page.BBox[3]

        # Calculate scaling and translation for background image
        window_width = where[2]
        window_height = where[3]
        x_scale = float(where[2])/i_w
        y_scale = float(where[3]-25)/i_h

        scale = x_scale
        if x_scale > y_scale:
            scale = y_scale

        translate_x = (where[2]-(i_w*scale))/2
        translate_y = (where[3]-(i_h*scale))
        canvas.translate(where[0]+translate_x, where[1]+translate_y)
        canvas.scale(scale, scale)
        canvas.doForm(makerl(canvas, self.page))

        canvas.setStrokeColor(black)

        # Draw image bounding box
        canvas.rect(0, 0, i_w, i_h)

##############################################################################
# DFcrf - DataFax CRF Representation
##############################################################################
class DFcrf(Flowable):
    def __init__(self, size, study, datarec, hide_blinded, redaction_dict,
            prefer_background, header_callback):
        if size is None:
            size = (6.3*inch, 8.2*inch)
        self.size = size
        self.study = study
        self.datarec = datarec
        self.font = 'Helvetica'
        self.font_size = 20
        self.hide_blinded = hide_blinded
        self.redaction_dict = redaction_dict
        self.prefer_background = prefer_background
        self.header_callback = header_callback

    def wrap(self, *args):
        return self.size

    def drawBackground(self, where, visit_num, plate):
        canvas = self.canv
        plate_num = plate.number()
        img = None
        path = None
        bkgds = []
        # If we have a prefered background, try that first
        if self.prefer_background:
            for bkgd in self.prefer_background.split(','):
                bkgds.append('bkgd/DFbkgd%03d_%d_%s.png' % \
                    (plate_num, visit_num, bkgd))
                bkgds.append('bkgd/DFbkgd%03d_all_%s.png' % \
                    (plate_num, bkgd))

        # Regular background names
        bkgds.append('bkgd/DFbkgd%03d_%d.png' % (plate_num, visit_num))
        bkgds.append('bkgd/DFbkgd%03d.png' % plate_num)

        # Look for correct background image
        for bkgd in bkgds:
            path = os.path.join(self.study.studydir, bkgd)
            try:
                img = Image.open(path)
            except IOError:
                continue

            break

        if img is None:
            i_w, i_h = (1728, 2200)
        else:
            i_w, i_h = img.size

        # Find field bounding box if biggen than background
        p_w = i_w
        p_h = i_h
        for field in plate.fieldList():
            bb = field.boundingBox()
            if bb:
                if bb[2]*2+5 > p_w:
                    p_w = bb[2]*2+5
                if bb[3]*2+5 > p_h:
                    p_h = bb[3]*2+5

        # Calculate scaling and translation for background image
        window_width = where[2]
        window_height = where[3]
        x_scale = float(where[2])/p_w
        y_scale = float(where[3]-50)/p_h

        scale = x_scale
        if x_scale > y_scale:
            scale = y_scale

        translate_x = (where[2]-(p_w*scale))/2
        translate_y = (where[3]-(p_h*scale))
        canvas.translate(where[0]+translate_x, where[1]+translate_y)
        canvas.scale(scale, scale)

        # If we have a background image, draw it now
        if img:
            canvas.drawImage(path, 0, p_h-i_h)

        canvas.setStrokeColor(black)

        # Draw image bounding box
        canvas.rect(0, 0, p_w, p_h)

        # Set up translation and scaling for field drawing
        canvas.translate(0, p_h)

        # Adjust scaling for field positions. DFbkgd images are double
        # the resolution of the field coordinates
        canvas.scale(2, 2)

        canvas.setFont(self.font, self.font_size)

    def drawBoxes(self, field, stroke, fill):
        '''Draw and fill boxes in specified colors'''
        canvas = self.canv
        canvas.setStrokeColor(stroke)
        canvas.setFillColor(fill)
        for r in field.rects or []:
            canvas.rect(r.left, -r.top, r.width, -r.height, fill=1)

    def blankFieldBackground(self, field):
        '''Blank boxes slightly larger than actual size to overwrite
        printed boxes on CRF form.'''
        canvas = self.canv
        canvas.setFillColor(white)
        canvas.setStrokeColor(white)
        for r in field.rects or []:
            canvas.rect(r.left-2, -r.top+2, r.width+4, -(r.height+4), fill=1)

    def drawMissingField(self, field):
        self.drawBoxes(field, blue, orange)

    def drawField(self, field, value, decoded_value, box):
        canvas = self.canv

        # Draw outline of box
        self.drawBoxes(field, blue, white)

        # Fill in Data
        canvas.setFillColor(blue)

        # Choice multiple boxes, or check
        if (field.type == "Choice" and \
            len(field.rects) > 1) or \
            field.type == "Check":
            if box is not None:
                r = field.rects[box]
                canvas.saveState()
                canvas.setLineWidth(3)
                path = canvas.beginPath()
                path.moveTo(r.left, -r.top)
                path.lineTo(r.left+r.width, -r.top-r.height)
                path.moveTo(r.left+r.width, -r.top)
                path.lineTo(r.left, -r.top-r.height)
                path.close()
                canvas.drawPath(path)
                canvas.restoreState()
        # Date
        elif field.type == 'Date' and len(field.rects) > 1:
            clean_value = re.sub('[^0-9A-Za-z]','', value)
            i = 0
            for r in field.rects:
                if i < len(clean_value):
                    canvas.drawCentredString(r.left+(r.width/2),
                        -(r.top+(4*r.height/5)), clean_value[i])
                i += 1
        elif field.type == 'Number' and len(field.rects) == 2 and \
                field.format == 'nn:nn' and (':' in value or value == ''):
            if value == '':
                value = '  :  ';
            clean_value = value.split(':')
            i = 0
            for r in field.rects:
                if i < len(clean_value):
                    canvas.drawCentredString(r.left+(r.width/2),
                        -(r.top+(4*r.height/5)), clean_value[i])
                i += 1
        elif field.type == 'Number' and len(field.rects) > 1:
            try:
                format_decimal = field.format.index('.')
            except ValueError:
                format_decimal = len(field.format)

            try:
                value_decimal = value.index('.')
            except ValueError:
                value_decimal = len(value)

            truncated = False
            if field.format and format_decimal < value_decimal:
                    print('WARNING: VALUE TRUNCATED value_decimal=', value_decimal, 'format_decimal=', format_decimal, 'value=[',value,'] format=', field.format, 'field=',field.description,'number=', field.number)
                    value = value[value_decimal - format_decimal]
                    truncated = True
            if format_decimal > value_decimal:
                    value = (' ' * (format_decimal - value_decimal)) + value

            clean_value = value.replace('.', '')

            # Check for case where store len > number of boxes
            if len(field.rects) < len(clean_value):
                print('WARNING: NOT ENOUGH BOXES value=', clean_value, 'len=', len(clean_value), 'boxes=', len(field.rects))
                truncated = True
                clean_value = clean_value[len(clean_value)-len(field.rects):]

            i = 0
            for r in field.rects:
                if truncated:
                    canvas.setFillColor(red)
                    canvas.rect(r.left, -r.top, r.width, -r.height, fill=1)
                    canvas.setFillColor(blue)
                if i < len(clean_value):
                    canvas.drawCentredString(r.left+(r.width/2),
                        -(r.top+(4*r.height/5)), clean_value[i])
                i += 1

        # Other values shorter than number of boxes
        elif field.type != 'Choice' and len(value) <= len(field.rects):
            i = 0
            for r in field.rects:
                if i < len(value):
                    canvas.drawCentredString(r.left+(r.width/2),
                        -(r.top+(4*r.height/5)), value[i])
                i += 1
        elif canvas.stringWidth(decoded_value, self.font, self.font_size) < field.rects[0].width:
            r = field.rects[0]
            canvas.drawCentredString(r.left+(r.width/2),
                -(r.top+(4*r.height/5)), decoded_value)
        elif canvas.stringWidth(decoded_value, self.font, 2*self.font_size/3) < field.rects[0].width:
            r = field.rects[0]
            canvas.setFont(self.font, 2*self.font_size/3)
            canvas.drawCentredString(r.left+(r.width/2),
                -(r.top+(4*r.height/5)), decoded_value)
            canvas.setFont(self.font, self.font_size)
        else:
            # Draw outline of box for which field value is too large
            canvas.setStrokeColor(blue)
            for r in field.rects:
                canvas.setFillColor(cyan)
                canvas.rect(r.left, -r.top, r.width, -r.height, fill=1)
                canvas.setFillColor(blue)
                canvas.drawCentredString(r.left+(r.width/2),
                    -(r.top+(4*r.height/5)), '>')

    def draw(self):
        canvas = self.canv

        # Draw legend at bottom of CRF page
        canvas.setLineWidth(0.2)
        canvas.setStrokeColor(black)
        canvas.setFillColor(orange)
        canvas.rect(0, 14, 10, 10, fill=1)
        canvas.setFillColor(cyan)
        canvas.rect(0, 0, 10, 10, fill=1)
        canvas.setFillColor(red)
        canvas.rect(1.5*inch, 14, 10, 10, fill=1)
        canvas.setFillColor(black)
        canvas.rect(1.5*inch, 0, 10, 10, fill=1)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(0*inch, 0*inch+30, 'Legend:')
        canvas.setFont('Helvetica', 8)
        canvas.drawString(0*inch+12, 0*inch+16, 'Missing Value')
        canvas.drawString(0*inch+12, 0*inch+2, 'Value too Long for Box')
        canvas.drawString(1.5*inch+12, 0*inch+16, 'Truncated Numeric Value')
        canvas.drawString(1.5*inch+12, 0*inch+2, 'Internal/Administrative Data')

        where = (0, 0, self.size[0], self.size[1]-0.5)
        field_values = self.datarec.split('|')
        pid_num = int(field_values[6])
        visit_num = int(field_values[5])
        plate_num = int(field_values[4])
        is_lost = field_values[0] == '0'

        self.header_callback(pid_num, visit_num, plate_num)

        for i in range(8):
            bookmark = '{0}_{1}_{2}B{3}'.format(pid_num, visit_num, plate_num, i)
            canvas.bookmarkHorizontal(bookmark, -12, self.size[1]+inch)

        plate = self.study.plate(plate_num)
        if plate is None:
            print('Plate ', plate_num, ' does not exist in study.')
            return

        self.drawBackground(where, visit_num, plate)

        for field in plate.fieldList():
            self.blankFieldBackground(field)

        for field in plate.fieldList():
            bb = field.boundingBox()
            if bb is None:
                continue

            # skip bookmarks on lost records
            if not is_lost:

                bookmark = '{0}_{1}_{2}_{3}'.format(pid_num, visit_num, plate_num, field.number)
                canvas.linkRect(bookmark, bookmark,
                    (bb[0], -bb[1], bb[2], -bb[3]), relative=1)

            if field.number > len(field_values):
                value = ''
            else:
                value = field_values[field.number-1]

            # If we're blinded to internal fields, don't display them
            if (self.redaction_dict and \
                    self.redaction_dict.get((plate_num, field.number))) or \
                    (self.hide_blinded and field.isBlinded()):
                self.drawBoxes(field, black, black)
            else:
                if is_lost:
                    self.drawBoxes(field, darkslategrey, white)
                else:
                    missingLabel = self.study.missingValueLabel(value)
                    if missingLabel is not None:
                        self.drawMissingField(field)
                    else:
                        (box, decoded_value) = field.decode(value)
                        self.drawField(field, value, decoded_value, box)


##############################################################################
# DFpdf - PDF file of images, data and audit trail
##############################################################################
class DFpdf(object):

    lost_codes = {
            '1': 'Patient Missed Visit',
            '2': 'Exam or Test Not Performed',
            '3': 'Data Not Available',
            '4': 'Patient Refused',
            '5': 'Patient Moved Away',
            '6': 'Patient Lost to Follow-up',
            '7': 'Patient Died',
            '8': 'Patient Terminated due to Study Illness',
            '9': 'Patient Terminated due to Other Illness',
            '10': 'Other Reason'
    }

    def __init__(self, path, name, sql, study, hide_internal, redaction_dict, \
            include_attached_images, prefer_background, shadow_pages, \
            format_pid, \
            include_chronological_audit, \
            include_field_audit, fontsize, leading, include_secondaries):
        self.path = path
        self.name = name
        self.study = study
        self.hide_internal = hide_internal
        self.redaction_dict = redaction_dict
        self.include_attached_images = include_attached_images
        self.prefer_background = prefer_background
        self.shadow_pages = shadow_pages
        self.include_chronological_audit = include_chronological_audit
        self.include_field_audit = include_field_audit
        self.include_secondaries = include_secondaries
        self.sql = sql
        self.doc = BaseDocTemplate(os.path.join(path, name)+'.pdf', showBoundary=1, pagesize=letter)
        template = PageTemplate('normal', [Frame(inch, inch, 6.5*inch, 8.4*inch)], onPageEnd=self.pageHeader)
        self.doc.addPageTemplates(template)
        self.styles = stylesheet(fontsize, leading)
        self.outlines = []
        #self.content = [TableOfContents(), PageBreak(), DFOutlines(self.outlines)]
        self.content = [DFOutlines(self.outlines)]
        self.jobsize = 1
        self.headerId = 0
        self.headerVisitNum = 0
        self.headerPlateNum = 0
        self.headerVisitLabel = ''
        self.headerPlateLabel = ''
        self.format_pid = format_pid

    def close(self, quiet):
        if not quiet:
            self.doc.setProgressCallBack(self.progressCB)
        self.doc.title = 'Closeout PDF {0}'.format(self.name)
        self.doc.author = getpass.getuser()
        self.doc.subject = 'Closeout PDF {0}'.format(self.name)
        self.doc.build(self.content)

    def setPageHeader(self, pid_num, visit_num, plate_num):
        self.headerId = pid_num
        self.headerVisitNum = visit_num
        self.headerPlateNum = plate_num
        self.headerVisitLabel = self.study.visitLabel(visit_num)
        self.headerPlateLabel = self.study.pageLabel(visit_num, plate_num)

    def pageHeader(self, canvas, doc):
        if not self.headerId:
            return

        canvas.saveState()
        canvas.rect(inch, 9.4*inch, 6.5*inch, 0.6*inch)

        canvas.setLineWidth(1)
        path = canvas.beginPath()
        path.moveTo(6*inch, 9.5*inch)
        path.lineTo(6*inch, 9.9*inch)
        path.close()
        canvas.drawPath(path)

        canvas.setFillColor(black)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(4.25*inch, 9.5*inch+24, self.study.studyName())
        page_number = 'Page %s' % canvas.getPageNumber()

        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(4.25*inch, 0.75*inch, page_number)
        canvas.drawString(inch+6, 9.5*inch+24, formatPID(self.format_pid, self.headerId))
        canvas.drawString(inch+6, 9.5*inch+12, self.headerVisitLabel)
        canvas.drawString(inch+6, 9.5*inch, self.headerPlateLabel)

        bookmark = '{0}_{1}_{2}'.format(self.headerId, self.headerVisitNum, self.headerPlateNum)

        canvas.setFillColor(white)
        canvas.setStrokeColor(blue)

        # CRF box
        canvas.rect(6.1*inch, 9.725*inch, 0.6*inch, 0.175*inch, fill=1)
        canvas.linkAbsolute(bookmark+'B0', bookmark+'B0',
            (6.1*inch, 9.725*inch, 6.1*inch+0.6*inch, 9.725*inch+0.175*inch))

        # Data box
        canvas.rect(6.8*inch, 9.725*inch, 0.6*inch, 0.175*inch, fill=1)
        canvas.linkAbsolute(bookmark+'_DA', bookmark+'_DA',
            (6.8*inch, 9.725*inch, 6.8*inch+0.6*inch, 9.725*inch+0.175*inch))

        # Chronological audit box
        if self.include_chronological_audit:
            canvas.rect(6.1*inch, 9.5*inch, 0.6*inch, 0.175*inch, fill=1)
            canvas.linkAbsolute(bookmark+'_AU', bookmark+'_AU',
                (6.1*inch, 9.5*inch, 6.1*inch+0.6*inch, 9.5*inch+0.175*inch))
            canvas.drawCentredString(6.4*inch, 9.5*inch+3, 'Audit')

        # Field audit box
        if self.include_field_audit:
            canvas.rect(6.8*inch, 9.5*inch, 0.6*inch, 0.175*inch, fill=1)
            canvas.linkAbsolute(bookmark+'_FA', bookmark+'_FA',
                (6.8*inch, 9.5*inch, 6.8*inch+0.6*inch, 9.5*inch+0.175*inch))
            canvas.drawCentredString(7.1*inch, 9.5*inch+3, 'ByField')

        canvas.setFillColor(blue)

        # Draw Labels
        canvas.drawCentredString(6.4*inch, 9.725*inch+3, 'CRF')
        canvas.drawCentredString(7.1*inch, 9.725*inch+3, 'Data')
        if self.include_chronological_audit:
            canvas.drawCentredString(6.4*inch, 9.5*inch+3, 'Audit')

        # Field audit box
        if self.include_field_audit:
            canvas.drawCentredString(7.1*inch, 9.5*inch+3, 'ByField')

        canvas.restoreState()

    def progressCB(self, typ, value):
        if typ == 'SIZE_EST':
            self.jobsize = value
            self.lastjobdone = 0
        if typ == 'PROGRESS':
            jobdone = 50*value//self.jobsize
            if self.lastjobdone < jobdone:
                print('Progress: [{0}{1}]'.format('*' * jobdone, ' ' * (50-jobdone)))
                self.lastjobdone = jobdone

    #########################################################################
    # Output Outlines (Bookmarks)
    #########################################################################
    def generateBookmarksForPatient(self, records):
        domains = {}
        domainmap = self.study.domainMap()
        lastID = None
        lastVisit = None
        lastPlate = None

        # Build and output by visit
        for (pid_num, visit_num, plate_num, plateorder, datarec) in records:
            visit_label = self.study.visitLabel(visit_num)
            page_label = self.study.pageLabel(visit_num, plate_num)
            bookmark = '{0}_{1}_{2}'.format(pid_num, visit_num, plate_num)
            if lastID is None:
                lastVisit = None
                lastID = pid_num
                self.outlines.append([formatPID(self.format_pid, pid_num), bookmark+'B0', 0, True])
                self.outlines.append(['By Visit', bookmark+'B1', 1, True])
            if lastVisit != visit_num:
                lastVisit = visit_num
                self.outlines.append([visit_label, bookmark+'B2', 2, True])
            self.outlines.append([page_label, bookmark+'B3', 3, True])
            self.outlines.append(['Data Fields', bookmark+'_DA', 4, True])
            if self.include_chronological_audit:
                self.outlines.append(['Audit by Time', bookmark+'_AU', 4, True])
            if self.include_field_audit:
                self.outlines.append(['Audit by Field', bookmark+'_FA', 4, True])

            domain = domainmap.label(plate_num)
            if domain not in domains:
                domains[domain] = []
            domains[domain].append((pid_num, visit_num, plate_num,
                page_label, visit_label))

        # Output by Domains
        domainlist = domains.items()
        domainlist.sort(key=lambda x: (x[0]))
        lastDomain = None
        for (domain, items) in domainlist:
            lastVisit = None
            for (pid_num, visit_num, plate_num, page_label, visit_label) in items:
                bookmark = '{0}_{1}_{2}'.format(pid_num, visit_num, plate_num)
                if lastDomain is None:
                    self.outlines.append(['By Domain', bookmark+'B4', 1, True])
                if lastDomain != domain:
                    self.outlines.append([domain, bookmark+'B5', 2, True])
                    lastDomain = domain
                    lastPlate = None
                if lastVisit != visit_num:
                    self.outlines.append([visit_label, bookmark+'B6', 3, True])
                    lastVisit = visit_num
                self.outlines.append([page_label, bookmark+'B7', 4, True])
                self.outlines.append(['Data Fields', bookmark+'_DA', 5, True])
                if self.include_chronological_audit:
                    self.outlines.append(['Audit by Time', bookmark+'_AU', 5, True])
                if self.include_field_audit:
                    self.outlines.append(['Audit by Field', bookmark+'_FA', 5, True])


    #########################################################################
    # Output Field Audit
    #########################################################################
    def outputFieldAudit(self, width, pid_num, visit_num, plate_num, auditOps):
        styleH = self.styles['title']
        styleA = self.styles['audit_header']
        styleN = self.styles['default']
        styleI = self.styles['indented']
        plate = self.study.plate(plate_num)
        bookmark = '{0}_{1}_{2}_FA'.format(pid_num, visit_num, plate_num)
        title = Paragraph('<a name="{0}"/>Audit by Field'.format(bookmark), styleH)
        for field in plate.fieldList():
            if (self.redaction_dict and \
                    self.redaction_dict.get((plate_num, field.number))) or \
                    (self.hide_internal and field.isBlinded()):
                description = 'Internal Use Only Field'
            else:
                description = field.description

            if field.boundingBox() is None:
                continue
            auditList = [[
                Paragraph('<b>Date</b>', styleN),
                Paragraph('<b>Time</b>', styleN),
                Paragraph('<b>User</b>', styleN),
                Paragraph('<b>Operation</b>', styleN)]]
            for rec in auditOps:
                if field.id() != rec.funiqueid and rec.funiqueid != 0:
                    continue
                changes = []
                for o in rec.ops:
                    changes.append(Paragraph(o, styleI))
                auditList.append([
                    Paragraph('{0}'.format(rec.tdate), styleN),
                    Paragraph('{0}'.format(rec.ttime), styleN),
                    Paragraph(rec.who, styleN),
                    changes])

            table = Table(auditList, colWidths=[
                0.14*width,
                0.12*width,
                0.15*width,
                0.58*width], splitByRow=1, repeatRows=1, hAlign='RIGHT')
            tablestyle = TableStyle([
                ('VALIGN', (0,0), (-1, -1), 'TOP'),
                ('LINEABOVE', (0,0), (-1, -1), 1, lightgrey)])
            table.setStyle(tablestyle)
            bookmark = '{0}_{1}_{2}_{3}_audit'.format(pid_num, visit_num, plate_num, field.number)
            if title:
                self.content.append(KeepTogether([title, Paragraph('<para><a name="{0}"/>{1}. {2}<para>'.format(bookmark, field.number, description), styleA), table]))
            else:
                self.content.append(KeepTogether([Paragraph('<para><a name="{0}"/>{1}. {2}<para>'.format(bookmark, field.number, description), styleA), table]))

            title = None

        self.content.append(PageBreak())

    #########################################################################
    # Chronological Audit
    #########################################################################
    def outputAudit(self, width, pid_num, visit_num, plate_num, auditRecs):
        styleH = self.styles['title']
        styleA = self.styles['audit_header']
        styleN = self.styles['default']
        styleI = self.styles['indented']
        bookmark = '{0}_{1}_{2}_AU'.format(pid_num, visit_num, plate_num)
        title = Paragraph('<a name="{0}"/>Chronological Audit'.format(bookmark), styleH)
        last = None
        auditList = []
        for rec in auditRecs:
            if last is None or last.who != rec.who or last.tdate != rec.tdate \
                    or last.ttime != rec.ttime:
                if auditList:
                    table = Table(auditList, colWidths=[
                        0.1*width,
                        0.3*width,
                        0.6*width], splitByRow=1, repeatRows=1, hAlign='LEFT')
                    tablestyle = TableStyle([
                        ('VALIGN', (0,0), (-1, -1), 'TOP'),
                        ('LINEABOVE', (0,0), (-1, -1), 1, lightgrey)])
                    table.setStyle(tablestyle)
                    if title:
                        self.content.append(KeepTogether([ title, \
                        Paragraph('{0} {1} {2}'.format(last.tdate, last.ttime, last.who), styleA), table]))
                    else:
                        self.content.append(KeepTogether([ \
                        Paragraph('{0} {1} {2}'.format(last.tdate, last.ttime, last.who), styleA), table]))
                    title = None

                last = rec

                auditList = [[
                    Paragraph('<para alignment="right"><b>Field</b></para>', styleN),
                    Paragraph('<b>Description</b>', styleN),
                    Paragraph('<b>Operation</b>', styleN)]]

            changes = []
            for o in rec.ops:
                changes.append(Paragraph(o, styleI))
            if rec.fnum < 0:
                auditList.append([
                    Paragraph('<para alignment="right">- .</para>', styleN),
                    Paragraph('{0}'.format(rec.desc), styleN),
                    changes])
            else:
                auditList.append([
                    Paragraph('<para alignment="right">{0}.</para>'.format(rec.fnum), styleN),
                    Paragraph('{0}'.format(rec.desc), styleN),
                    changes])

        # If we still have remaining audit records, output them now.
        if auditList:
            table = Table(auditList, colWidths=[
                0.1*width,
                0.3*width,
                0.6*width], splitByRow=1, repeatRows=1, hAlign='LEFT')
            tablestyle = TableStyle([
                ('VALIGN', (0,0), (-1, -1), 'TOP'),
                ('LINEABOVE', (0,0), (-1, -1), 1, lightgrey)])
            table.setStyle(tablestyle)
            if title:
                self.content.append(KeepTogether([ title, \
                Paragraph('{0} {1} {2}'.format(last.tdate, last.ttime, last.who), styleA), table]))
            else:
                self.content.append(KeepTogether([ \
                Paragraph('{0} {1} {2}'.format(last.tdate, last.ttime, last.who), styleA), table]))
            title = None

        # Even if we had no audit records, always output title
        if title:
            self.content.append(title)

        #self.content.append(PageBreak())

    #########################################################################
    # Output CRF Image
    #########################################################################
    def outputCRFImage(self, record):
        self.content.append(DFcrf(None, self.study, record, self.hide_internal,\
                self.redaction_dict, self.prefer_background, self.setPageHeader))
        self.content.append(PageBreak())

    #########################################################################
    # Output Attached Image
    #########################################################################
    def outputAttachedImage(self, rasters, pid_num, visit_num, plate_num):
        rasters.sort()
        for doc_num, (raster, is_primary) in enumerate(rasters, 1):
            doc_type = 'Primary' if is_primary else 'Secondary'
            paths = []
            if self.shadow_pages:
                paths.append(os.path.join(self.shadow_pages, raster))
            paths.append(os.path.join(self.study.studydir, 'pages', raster))
            for path in paths:
                if os.path.isfile(path) and os.access(path, os.R_OK):
                    break
            else:
                print(' {0},{1},{2} image {3} not found or is not a readable file'.format(pid_num, visit_num, plate_num, path))
                return

            # Try to determine if this is a PDF file
            with open(path, 'rb') as f:
                mtime = time.strftime('%Y/%m/%d %H:%M:%S',
                        time.localtime(os.path.getmtime(path)))
                if f.read(4) == str('%PDF'):
                    pages = PdfReader(path).pages
                    try:
                        pages = [pagexobj(x) for x in pages]
                        for page_num, page in enumerate(pages, 1):
                            label = 'Attached Document {0} ({1}, PDF, Page {2} of {3}) dated {4}'.format(doc_num, doc_type, page_num, len(pages), mtime)
                            self.content.append(DFXObj(None, page, label))
                            self.content.append(PageBreak())
                    except:
                        print(' {0},{1},{2} image {3} is incompatible PDF'.format(pid_num, visit_num, plate_num, path))
                else:
                    label = 'Attached Document {0} ({1}, Single Image) dated {2}'.format(doc_num, doc_type, mtime)
                    self.content.append(DFimage(None, path, label))
                    self.content.append(PageBreak())

    #########################################################################
    # Output Field Values
    #########################################################################
    def outputFieldValues(self, width, record):
        styleH = self.styles['title']
        styleN = self.styles['default']
        field_values = record.split('|')
        pid_num = int(field_values[6])
        visit_num = int(field_values[5])
        plate_num = int(field_values[4])
        is_lost = field_values[0] == '0'

        plate = self.study.plate(plate_num)
        if plate is None:
            print('Plate ', plate_num, ' does not exist in study.')
            return

        if not is_lost:
            fieldValueList = [[
                Paragraph('<para alignment="right"><b>Field</b></para>', styleN),
                Paragraph('<b>Description</b>', styleN),
                Paragraph('<b>Value</b>', styleN)]]
            for field in plate.fieldList():
                bb = field.boundingBox()
                if bb is None:
                    continue

                if field.number > len(field_values):
                    value = ''
                else:
                    value = field_values[field.number-1]

                if (self.redaction_dict and \
                    self.redaction_dict.get((plate_num, field.number))) or \
                    (self.hide_internal and field.isBlinded()):
                    description = 'Internal Use Only Field'
                    list_value = 'Internal Use Only Field'
                else:
                    description = self.escape_string(field.description)
                    missingLabel = self.study.missingValueLabel(value)
                    if missingLabel is not None:
                        list_value = '[' + value + ', ' + missingLabel + ']'
                    else:
                        (box, decoded_value) = field.decode(value)
                        if field.type == 'Choice' or field.type == 'Check':
                            list_value = value + ', ' + decoded_value
                        else:
                            list_value = value

                    if not list_value:
                        list_value = '[blank]'

                    # Make sure we protect data value characters like <, >, &
                    list_value = self.escape_string(list_value)

                bookmark = '{0}_{1}_{2}_{3}'.format(pid_num, visit_num, plate_num, field.number)
                if self.include_field_audit:
                    fieldValueList.append([
                        Paragraph('<para alignment="right"><a name="{0}"/>{1}.</para>'.format(bookmark, field.number), styleN),
                        Paragraph(description, styleN),
                        Paragraph('<para><a href="{0}_audit" color="blue">{1}</a></para>'.format(bookmark, list_value), styleN)])
                else:
                    fieldValueList.append([
                        Paragraph('<para alignment="right"><a name="{0}"/>{1}.</para>'.format(bookmark, field.number), styleN),
                        Paragraph(description, styleN),
                        Paragraph('<para>{0}</para>'.format(list_value), styleN)])

        bookmark = '{0}_{1}_{2}_DA'.format(pid_num, visit_num, plate_num)
        self.content.append(Paragraph('<a name="{0}"/>Data Field Values'.format(bookmark), styleH))

        if is_lost:
            reason = self.lost_codes.get(field_values[7], 'Other')
            if field_values[8]:
                reason = reason + ' [' + field_values[8] + ']'
            self.content.append(Paragraph('Record Marked Lost: {0}'.format(reason), styleN))
        else:
            table = Table(fieldValueList, colWidths=[
                0.1*width,
                0.3*width,
                0.6*width], splitByRow=1, repeatRows=1, hAlign='LEFT')
            tablestyle = TableStyle([
                ('VALIGN', (0,0), (-1, -1), 'TOP'),
                ('LINEABOVE', (0,0), (-1, -1), 1, lightgrey)])
            table.setStyle(tablestyle)
            self.content.append(table)
        #self.content.append(PageBreak())

    ###########################################################################
    # outputPatientRecord - Output a patient record, including CRF,
    # list of data values, chronological audit and field based audit
    ###########################################################################
    def outputPatientRecord(self, pid_num, visit_num, plate_num, datarec):
        self.outputCRFImage(datarec)
        raster = datarec[4:16]
        if self.include_attached_images.contains(plate_num) and \
                raster[4:5] == '/':
            rasters = [(raster, True)]
            if self.include_secondaries:
                rasters.extend([(r, False) for r in \
                        self.find_secondaries(pid_num, visit_num, plate_num)])
            self.outputAttachedImage(rasters, pid_num, visit_num, plate_num)
        self.outputFieldValues(6.4*inch, datarec)
        if self.include_chronological_audit or self.include_field_audit:
            auditOps = self.parseAudit(pid_num, visit_num, plate_num)
        if self.include_chronological_audit:
            self.outputAudit(6.4*inch, pid_num, visit_num, plate_num, auditOps)
        if self.include_field_audit:
            self.outputFieldAudit(6.4*inch, pid_num, visit_num, plate_num, auditOps)

    ###########################################################################
    # escape_string - Escape special characters
    ###########################################################################
    def escape_string(self, s):
        s=s.replace('&', '&amp;')
        s=s.replace('<', '&lt;')
        s=s.replace('>', '&gt;')
        return s;

    ###########################################################################
    # find_secondaries - Get a list of secondary raster images for keys
    ###########################################################################
    def find_secondaries(self, pid_num, visit_num, plate_num):
        secondaries_cursor = self.sql.execute('''
            select raster from secondaries
            where pid=? and visit=? and plate=?''',
            (pid_num, visit_num, plate_num))
        return [r[0] for r in secondaries_cursor.fetchall()]

    ###########################################################################
    # parseAudit: Convert Audit to human readable form
    ###########################################################################
    def parseAudit(self, pid_num, visit_num, plate_num):
        auditRec = namedtuple('auditRec', '''who, tdate, ttime, status, op,
            type, funiqueid, fnum, metafnum, code, reason, desc, oldval, newval,
            oldvaldec, newvaldec''')
        audit_cursor = self.sql.execute('''
            select
		        a.who, a.tdate, a.ttime, a.status, a.op, a.type, a.funiqueid, a.fnum,
                a.metafnum, a.code, a.reason, s.string, a.oldval, a.newval, a.oldvaldec,
		        a.newvaldec
            from audit a join shared_strings s
            on a.fdescid = s.id
            where a.pid=? and a.visit=? and a.plate=?
            order by a.tdate, a.ttime''', \
            (pid_num, visit_num, plate_num))
        auditRecs = map(auditRec._make, audit_cursor.fetchall())

        # Group audit records into data/reason/qc transactions. Sometimes
        # data/reason/qc records have slightly different timestamps because
        # of how the server writes them out.
        groupedAuditRecs = []
        last = None
        lastTime = 0
        for rec in auditRecs:
            thisTime = int(rec.ttime[0:2])*3600 + int(rec.ttime[2:4])*60 + \
                    int(rec.ttime[4:6])
            if last is None or last.who != rec.who or last.tdate != rec.tdate \
                    or (lastTime != thisTime and lastTime != (thisTime-1)):
                    last = rec
                    lastTime = thisTime

            if rec.fnum is None or rec.fnum == '':
                fnum = 0
            else:
                fnum = int(rec.fnum)

            groupedAuditRecs.append(auditRec(rec.who, \
                    rec.tdate[0:4]+'/'+rec.tdate[4:6]+'/'+rec.tdate[6:8], \
                    last.ttime[0:2]+':'+last.ttime[2:4]+':'+last.ttime[4:6], \
                    rec.status, rec.op, rec.type, rec.funiqueid, fnum, \
                    rec.metafnum, rec.code, rec.reason, rec.desc, rec.oldval, \
                    rec.newval, rec.oldvaldec, rec.newvaldec))

        auditRecs = sorted(groupedAuditRecs, key=lambda x: \
                (x.tdate, x.ttime, abs(x.fnum), x.type, x.metafnum))

        # Now group operations by fields
        auditOpRec = namedtuple('auditOpRec', '''who, tdate, ttime,
                funiqueid, fnum, desc, ops''')
        auditOps = []
        field_dict = self.study.fieldsByUniqueID()
        last = None
        desc = ''
        blind = False
        # Process each audit record and group them into transactions
        for rec in auditRecs:
            if last is None or last.who != rec.who or last.tdate != rec.tdate or \
                    last.ttime != rec.ttime or last.funiqueid != rec.funiqueid:
                if last is not None and ops:
                    auditOps.append(auditOpRec(last.who, last.tdate, last.ttime, \
                            last.funiqueid, last.fnum, desc, ops))
                last = rec
                blind = False
                field = field_dict.get(rec.funiqueid)
                # Check whether this is an internal field
                if field and ((self.redaction_dict and \
                    self.redaction_dict.get((plate_num, field.number))) or \
                    (self.hide_internal and field.isBlinded())):
                    blind = True
                    desc = 'Internal Use Only Field'
                else:
                    blind = False
                    desc = self.escape_string(last.desc)
                ops = []
    
            # Skip system fields
            if rec.funiqueid >0 and rec.funiqueid < 10000:
                continue
    
            # Skip blinded fields
            if blind:
                continue

            ###############################################################
            # DATA RECORDS
            ###############################################################
            if rec.type == 'd':
                missingLabel = self.study.missingValueLabel(rec.oldval)
                if missingLabel is not None:
                    oldval = '[' + rec.oldval + ', ' + missingLabel + ']'
                else:
                    if rec.oldval != '' and rec.oldvaldec != '':
                        oldval = rec.oldval + ', ' + rec.oldvaldec
                    else:
                        oldval = rec.oldval
    
                    if oldval == "":
                        oldval = '[blank]'
    
    
                missingLabel = self.study.missingValueLabel(rec.newval)
                if missingLabel is not None:
                    newval = '[' + rec.newval + ', ' + missingLabel + ']'
                else:
                    if rec.newval != '' and rec.newvaldec != '':
                        newval = rec.newval + ', ' + rec.newvaldec
                    else:
                        newval = rec.newval
    
                    if newval == "":
                        newval = '[blank]'
    
                if rec.op == 'N':
                    if rec.status == 0:
                        reason = self.lost_codes.get(rec.code, 'Other')
                        if rec.reason:
                            reason = reason + ' [' + rec.reason + ']'
                        ops.append('Data Record marked Lost: {0}'.format(reason))
                    else:
                        newval = self.escape_string(newval)
                        ops.append('Initial Value: <b>{0}</b>'.format(newval))
                elif rec.op == 'C':
                    oldval = self.escape_string(oldval)
                    newval = self.escape_string(newval)
                    if len(oldval) > 100 or len(newval) > 100:
                        ops.append('Changed Value: <b>{0}</b>'.format(newval))
                    else:
                        ops.append('Changed Value: <b>{0} \u2192 {1}</b>'.format(oldval, newval))
                elif rec.op == 'D':
                    ops.append('Data Record Deleted')
    
            ###############################################################
            # QC RECORDS
            ###############################################################
            if rec.type == 'q':
                if rec.metafnum not in [0,1,12,17,18]:
                    continue
                qctype = self.study.qcType(rec.code)
                qcstatus = self.study.qcStatus(rec.status, False)
                label = ''
                value = self.escape_string(rec.newval)
                if rec.metafnum == 1:
                    label = "Status"
                    value = qcstatus
                    if rec.status in [2, 6]:
                        continue
                elif rec.metafnum == 12:
                    label = "Reply"
                    if rec.op == 'N' and not rec.newval:
                        continue
                elif rec.metafnum == 17:
                    label = "Query"
                elif rec.metafnum == 18:
                    if rec.op == 'N' and not rec.newval:
                        continue
                    label = "Note"
                if rec.op == 'N' or rec.op == 'C':
                    ops.append('QC {0} ({1}): <i>{2}</i>'.format(label, qctype, \
                            value))
                elif rec.op == 'D':
                    ops.append('QC Deleted ({0})'.format(qctype))
    
            ###############################################################
            # REASON RECORDS
            ###############################################################
            if rec.type == 'r':
                if rec.metafnum not in [1, 10]:
                    continue
                if rec.op == 'N' or rec.op == 'C':
                    s = self.study.reasonStatus(rec.status)
                    if rec.metafnum == 1:
                        ops.append('Reason Status: <i>{0}</i>'.format(s))
                    if rec.metafnum == 10:
                        newval = self.escape_string(rec.newval)
                        ops.append('Reason Text: <i>{0}</i>'.format(newval))
                elif rec.op == 'D':
                    ops.append('Reason Deleted')
    
        # Add last transaction to list
        if last is not None and ops:
            auditOps.append(auditOpRec(last.who, last.tdate, last.ttime, \
                last.funiqueid, last.fnum, desc, ops))
    
        return auditOps

############################################################################
# loadRedactionFile
############################################################################
def loadRedactionFile(filename):
    redaction_dict = {}
    try:
        with open(filename, 'rU') as f:
            contents = f.read().decode('utf-8')
            for line in contents.split('\n'):
                rec = line.split('|')
                if len(rec) < 2:
                    print('Bad redaction line:', line)
                    continue
                if rec[0]=='Plate' and rec[1]=='Field':
                    continue
                try:
                    plate = int(rec[0])
                    field = int(rec[1])
                except ValueError:
                    print('Bad redaction line:', line)
                    continue
                redaction_dict[(plate,field)] = True
    except:
        pass

    return redaction_dict

############################################################################
# MAIN
############################################################################
def main():
    retcode = 0
    quiet = False
    blinded = False
    include_chronological_audit = True
    include_field_audit = True
    db = 'data.db'
    domains = None
    redaction = None
    redaction_dict = {}
    prefer_background = None
    shadow_pages = None
    centers = None
    patients = datafax.rangelist.RangeList(1, 281474976710656)
    plates = datafax.rangelist.RangeList(1, 500)
    visits = datafax.rangelist.RangeList(0, 65535)
    levels = datafax.rangelist.RangeList(1, 7)
    include_attached_images = datafax.rangelist.RangeList(1, 500)
    include_secondaries = False
    studydir = None
    format_pid = None
    pid_list_only = False
    fontsize = 10
    leading = 12

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'bd:s:I:P:V:L:D:',
                ['blinded', 'db=', 'studydir=', 'ids=', 'plates=', 'visits=',
                 'levels=', 'centers=', 'domains=', 'quiet',
                 'include-attached-images=', 'exclude-chronological-audit',
                 'exclude-field-audit', 'pid-list-only',
                 'prefer-background=', 'shadow-pages=', 'redaction=',
                 'format-pid=', 'fontsize=', 'leading=', 'include-secondaries'])
    except getopt.GetoptError, err:
        print(err)
        sys.exit(2)

    for o, a in opts:
        if o in ('-b', '--blinded'):
            blinded = True
        if o in ('-d', '--db'):
            db = a
        if o in ('--centers'):
            centers = datafax.rangelist.RangeList(0, 21460)
            centers.fromString(a)
        if o in ('-I', '--ids'):
            patients.fromString(a)
        if o in ('-P', '--plates'):
            plates.fromString(a)
        if o in ('-V', '--visits'):
            visits.fromString(a)
        if o in ('-L', '--levels'):
            levels.fromString(a)
        if o in ('-s', '--studydir'):
            studydir = a
        if o in ('-D', '--domains'):
            domains = a
        if o == '--redaction':
            redaction = a
        if o == '--exclude-chronological-audit':
            include_chronological_audit = False
        if o == '--exclude-field-audit':
            include_field_audit = False
        if o == '--include-attached-images':
            if a == 'ALL':
                include_attached_images.fromString('*')
            else:
                include_attached_images.fromString(a)
        if o == '--prefer-background':
            prefer_background = a
        if o == '--shadow-pages':
            shadow_pages = a
        if o == '--format-pid':
            format_pid = a
        if o == '--fontsize':
            fontsize = int(a)
        if o == '--leading':
            leading = int(a)
        if o == '--quiet':
            quiet = True
        if o == '--pid-list-only':
            pid_list_only = True
        if o == '--include-secondaries':
            include_secondaries = True
            
    # Make sure we have a study specified
    if not studydir:
        print('No --studydir specified')
        sys.exit(2)

    study = datafax.Study()
    study.loadFromFiles(studydir)
    if domains is not None:
        study.loadDomainMap(open(domains, 'r').read().decode('utf-8'))
    if redaction is not None:
        redaction_dict = loadRedactionFile(redaction)
        if not redaction_dict:
            print('Unable to load redaction file')
            sys.exit(2)

    centerdb = study.Centers()

    sql = sqlite3.connect(db)
    if include_secondaries:
        cursor = sql.execute('select name from sqlite_master where type=\'table\' and name=\'secondaries\'')
        if len(cursor.fetchall()) == 0:
            print('WARNING: --include-secondaries specified, but intermediate database does not')
            print('         contain any secondary image data')
            include_secondaries = False

    clauses = []
    pid_clause = patients.toSQL('pid')
    if pid_clause:
        clauses.append(pid_clause)
    visit_clause = visits.toSQL('visit')
    if visit_clause:
        clauses.append(visit_clause)
    plate_clause = plates.toSQL('plate')
    if plate_clause:
        clauses.append(plate_clause)
    level_clause = levels.toSQL('level')
    if level_clause:
        clauses.append(level_clause)

    if clauses:
        where_clause = 'where ' + ' and '.join(clauses)
    else:
        where_clause = ''

    # Get a list of unique patient IDs that match criteria
    pid_cursor = sql.execute('''
        select distinct pid
        from data ''' + where_clause + ''' order by pid''')

    # Build Select statement for fetching records
    clauses = ['pid=?']
    if plate_clause:
        clauses.append(plate_clause)
    if visit_clause:
        clauses.append(visit_clause)
    if level_clause:
        clauses.append(level_clause)
    rec_select = '''
        select pid, visit, plate, data
        from data
        where ''' + ' and '.join(clauses)

    # Now loop through each patient and generate output pages for them
    for pid in pid_cursor:
        center_number = centerdb.centerNumber(pid[0])
        if centers and not centers.contains(center_number):
            continue
        if pid_list_only:
            print(pid[0])
            continue

        print('Site {0} Patient {1}'.format(center_number, pid[0]))
        try:
            os.mkdir('{0}'.format(center_number))
        except OSError:
            pass

        pdf = DFpdf(str(center_number), formatPID(format_pid, pid[0]),
                sql, study, blinded, redaction_dict,
            include_attached_images, prefer_background, shadow_pages, format_pid,
            include_chronological_audit, include_field_audit, fontsize,
            leading, include_secondaries)

        rec_cursor = sql.execute(rec_select, (pid))
        dataRecs = rec_cursor.fetchall()
        visitmap = study.visitMap()
        sortedRecs=[]

        # For each record, get its plate display order
        for (pid_num, visit_num, plate_num, datarec) in dataRecs:
            # Skip secondaries
            if datarec[0] > '3':
                continue
            visitentry = visitmap.entry(visit_num)
            if visitentry is None:
                plateorder = 0
            else:
                plateorder = visitentry.plateOrder(plate_num)

            sortedRecs.append((pid_num, visit_num, plate_num, plateorder, datarec))

        # Sort by visit, plate display order
        sortedRecs.sort(key=lambda x: (x[1], x[3], x[2])) # Visit, order, plate

        pdf.generateBookmarksForPatient(sortedRecs)

        # Now traverse sorted list and output records
        for (pid_num, visit_num, plate_num, plateorder, datarec) in sortedRecs:
            if not quiet:
                print("  ", pid_num, visit_num, plate_num)
            pdf.outputPatientRecord(pid_num, visit_num, plate_num, datarec)

        # Actually build the PDF file based on the content generated above
        print('Writing out PDF file...')
        try:
            pdf.close(quiet)
        except LayoutError as e:
            print('****** ERROR: Unable to layout page for',
                    pdf.headerId, 'Visit', pdf.headerVisitNum,
                    '({0})'.format(pdf.headerVisitLabel),
                    'Plate', pdf.headerPlateNum,
                    '({0})'.format(pdf.headerPlateLabel))
            if not quiet:
                print('    ',e)
            print('****** Try using a smaller font using --font-size and --leading options')
            retcode = 1

    sys.exit(retcode)

if __name__ == '__main__':
    main()
