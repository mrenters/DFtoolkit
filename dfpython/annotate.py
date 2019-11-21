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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division

import random
import getpass

from reportlab.platypus import (
    BaseDocTemplate, 
    PageTemplate, 
    Frame, 
    FrameBreak,
    NextPageTemplate,
    PageBreak,
    Flowable,
    Paragraph,
    LongTable,
    Table,
    TableStyle,
    Spacer
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import (
        red, green, blue, cyan, magenta, yellow, black, white,
        darkblue, lightgrey, darkgrey, grey, darkorange, gold,
        HexColor
        )
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.utils import ImageReader
from PIL import Image
from StringIO import StringIO

import os
import getopt
import sys
import datafax
from datetime import date

###########################################################################
# escape_string - Escape special characters
###########################################################################
def escape_string(s):
    s=s.replace('&', '&amp;')
    s=s.replace('<', '&lt;')
    s=s.replace('>', '&gt;')
    return s;

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
            ecs.append(escape_string(s[start:i]))
            break

        # If no params, continue to next EC
        if s[i] != '(':
            ecs.append(escape_string(s[start:i]))
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

        ecs.append(escape_string(s[start:i]))
    return ecs

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

##############################################################################
# stylesheet - Stylesheet for document
##############################################################################
def stylesheet():
    styles= {
        'default': ParagraphStyle(
            'default',
            fontName='Helvetica',
            fontSize=8,
            leading=10,
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
    styles['title'] = ParagraphStyle(
            'title',
            parent=styles['default'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=14,
            textColor=grey
     )
    return styles

###########################################################################
# XRefBegin
###########################################################################
class XRefBegin(Flowable):
    def wrap(self, availWidth, availHeight):
        return (0,0)

    def draw(self):
        key = 'XRef'
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry('Variable Cross-Reference', key, 0)
        self.canv.showOutline()

###########################################################################
# PlateBegin
###########################################################################
class PlateBegin(Flowable):
    def __init__(self, doc, plate):
        self.doc = doc
        self.plate = plate

    def wrap(self, availWidth, availHeight):
        return (0,0)

    def draw(self):
        print('Plate:', self.plate.number())
        key = 'P{0}'.format(self.plate.number())
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry('{0}: {1}'.format(self.plate.number(),
            self.plate.description), key, 0)
        self.canv.showOutline()
        self.doc.setPlate(self.plate)

###########################################################################
# FieldBegin
###########################################################################
class FieldBegin(Paragraph):
    def __init__(self, doc, field_num, text, style):
        Paragraph.__init__(self, text, style)
        self.doc = doc
        self.field_num = field_num

    def draw(self):
        bookmark='P{0}F{1}'.format(self.doc.plate.number(), self.field_num)
        self.canv.bookmarkPage(bookmark)
        self.doc.fieldStarting(self.field_num)
        Paragraph.draw(self)

############################################################################
# AnnotatedCRF
############################################################################
class AnnotatedCRF(object):
    def __init__(self, study):
        self.doc = None
        self.study = study
        self.bkgd = None
        self.bkgd_width, self.bkgd_height = (1728, 2200)
        self.plate = None
        self.firstField = 0
        self.lastField = 0
        self.plateFilter = None
        self.enable_lut = False
        self.lowres_only = False
        self.extra_detail = 'legalrange'
        self.preferred_background = None
        self.priorities = {}
        self.colors = [
                (HexColor(0xB21616), white, HexColor(0xF39d9d), HexColor(0x505050), HexColor(0xFAD2D2)),
                (HexColor(0xED7D31), black, HexColor(0xF8CBAD), HexColor(0x505050), HexColor(0xFCE4D6)),
                (HexColor(0xFFC000), black, HexColor(0xFFE699), HexColor(0x505050), HexColor(0xFFF2CC)),
                (HexColor(0x70AD47), white, HexColor(0xC6E0B4), HexColor(0x505050), HexColor(0xE2EFDA)),
                (HexColor(0x4472C4), white, HexColor(0xB4C6E7), HexColor(0x505050), HexColor(0xD9E1F2))]

    def setPriorityFile(self, priority_file):
        if priority_file:
            self.priorities = load_priorities(self.study.studydir,
                    priority_file)

    def setExtraDetail(self, extra_detail):
        self.extra_detail = extra_detail

    def enableLUT(self, enable_lut):
        self.enable_lut = enable_lut

    def setLowResOnly(self, lowres):
        self.lowres_only = lowres

    def setPreferredBackground(self, background):
        self.preferred_background = background

    def filterPlates(self, r):
        self.plateFilter = r

    def buildXRef(self):
        fields=[]
        for plate in self.study.plateList():
            if self.plateFilter and \
                not self.plateFilter.contains(plate.number()):
                continue
            for field in plate.fieldList():
                bb = field.boundingBox()
                if bb is None:
                    continue
                fields.append((field, plate))
        fields.sort(key=lambda x: (x[0].name.lower(), x[1].number(), x[0].number))
        styles = stylesheet()
        styleN = styles['default']
        styleT = styles['title']
        cols = []
        xrefs = []
        firstChar=None
        tablestyle = TableStyle([
            ('VALIGN', (0,0), (-1, -1), 'TOP'),
            ('LINEABOVE', (0,0), (-1, -1), 1, lightgrey)])

        for field,plate in fields:
            if firstChar != field.name[0]:
                if firstChar is not None:
                    table = LongTable(cols, colWidths=[65,90,32,32],
                        splitByRow=1, repeatRows=2,hAlign='LEFT')
                    table.setStyle(tablestyle)
                    xrefs.append(table)
                    xrefs.append(Spacer(0,20))
                cols = []
                cols.append([
                    Paragraph('{0}'.format(field.name[0].upper()), styleT),
                    Paragraph('', styleN),
                    Paragraph('', styleN),
                    Paragraph('', styleN)
                ])
                cols.append([
                    Paragraph('<b>Name</b>', styleN),
                    Paragraph('<b>Description</b>', styleN),
                    Paragraph('<para alignment="right"><b>Plate</b></para>', styleN),
                    Paragraph('<para alignment="right"><b>Field</b></para>', styleN)
                ])
                firstChar = field.name[0]

            description = field.description
            if description is None:
                description = ''
            bookmark = '#P{0}F{1}'.format(plate.number(),field.number)
            cols.append([
                Paragraph('<a href="{0}" color="blue">{1}</a>'.format(bookmark, field.name), styleN),
                Paragraph(description, styleN),
                Paragraph('<para alignment="right">{0}</para>'.format(plate.number()), styleN),
                Paragraph('<para alignment="right">{0}</para>'.format(field.number), styleN)]),
        if len(cols):
            table = LongTable(cols, colWidths=[65,90,32,32],
                splitByRow=1, repeatRows=2,hAlign='LEFT')
            table.setStyle(tablestyle)
            xrefs.append(table)
        return xrefs

    def buildFields(self, plate):
        str_plate = '{0:03d}'.format(plate.number())
        str_rplate = '{0}'.format(plate.number())
        styleN = stylesheet()['default']
        cols = [Paragraph('<para alignment="right"><b>Field</b></para>', styleN),
            Paragraph('<b>Name/Alias</b>', styleN),
            Paragraph('<b>Type</b>', styleN),
            Paragraph('<b>Description</b>', styleN),
            Paragraph('<b>Format</b>', styleN),
            Paragraph('<b>Coding</b>', styleN)]
        if self.extra_detail == 'legalrange':
            cols.append(Paragraph('<b>Legal Range</b>', styleN))
        else:
            cols.append(Paragraph('<b>Edit Checks</b>', styleN))

        rows = [cols]

        for field in plate.fieldList():
            str_field = '{0}'.format(field.number)
            bb = field.boundingBox()
            if bb is None:
                continue
            description = field.description
            if description is None:
                description = ''
            styleName = field.styleName
            if styleName is None:
                styleName = 'None'
            format = field.format
            if format is None:
                format = ''
    
            codes = []
            for code in field.codes or []:
                label = code[1]
                if label is None or label == '':
                    label = code[0]
                codes.append('<b>{0}</b>: {1}'.format(code[0],
                    escape_string(code[1])[0:40]))
            codestr = '<br/>'.join(codes)
    
            # Look for *LUT* field enter edit check
            if self.enable_lut and not codes and field.fieldEnter is not None:
                ecs = []
                ecs.extend(parseEC(field.fieldEnter))
                for e in ecs:
                    if "LUT" in e:
                        codestr = e
                        break

            if self.extra_detail == 'legalrange':
                detail = escape_string(field.legal)
            else:
                ecs = []

                if field.plateEnter is not None:
                    ecs.extend(parseEC(field.plateEnter))
                if field.fieldEnter is not None:
                    ecs.extend(parseEC(field.fieldEnter))
                if field.fieldExit is not None:
                    ecs.extend(parseEC(field.fieldExit))
                if field.plateExit is not None:
                    ecs.extend(parseEC(field.plateExit))

                detail = '<br/>'.join(ecs)

            bookmark = 'P{0}F{1}'.format(plate.number(), field.number)
            alias = field.alias.replace('$(plate)', str_plate);
            alias = alias.replace('$(rplate)', str_rplate)
            alias = alias.replace('$(field)', str_field)

            rows.append([
                #FieldBegin(self, field.number, '<para alignment="right"><a name="{0}"/>{1}</para>'.format(bookmark, field.number), styleN),
                FieldBegin(self, field.number, '<para alignment="right">{0}</para>'.format(field.number), styleN),
                Paragraph(field.name + '<br/><i>' + alias + '</i>', styleN),
                Paragraph(field.type, styleN),
                Paragraph(escape_string(description), styleN),
                Paragraph(escape_string(format), styleN),
                Paragraph(codestr, styleN),
                Paragraph(detail, styleN)])
#        table = Table(rows, colWidths=[36,66,76,50,120,72,120],
#                splitByRow=1, repeatRows=1,hAlign='LEFT')
        table = Table(rows, colWidths=[32,65,42,95,60,95,105],
                splitByRow=1, repeatRows=1,hAlign='LEFT')
        tablestyle = TableStyle([
            ('ALIGN', (0,0), (-1, -1), 'LEFT'),
            ('VALIGN', (0,0), (-1, -1), 'TOP'),
            ('LINEABOVE', (0,0), (-1, -1), 1, lightgrey)])
        table.setStyle(tablestyle)
        return table
    
    def setPlate(self, plate):
        bkgds = []
        self.firstField = 0
        self.lastField = 0
        self.field_scale = 2
        self.bkgd_width, self.bkgd_height = (1728, 2000)
        self.bkgd_img_height = self.bkgd_height

        if not self.lowres_only:
            if self.preferred_background:
                for bkgd in self.preferred_background.split(','):
                    bkgds.append('DFbkgd%03d_all_%s.png' % (plate.number(),
                        bkgd))

            bkgds.append('DFbkgd%03d.png' % plate.number())

        bkgds.append('plt%03d.png' % plate.number())
        bkgds.append('plt%03d' % plate.number())

        for bkgd in bkgds:
            path = os.path.join(self.study.studydir, 'bkgd', bkgd)
            try:
                self.bkgd = StringIO()
                img = Image.open(path).convert('L').point(lambda p: p*0.5+128)
                self.bkgd_width = img.size[0]
                self.bkgd_height = img.size[1]
                self.bkgd_img_height = img.size[1]

                if self.bkgd_width < 900:
                    self.field_scale = 1

                img.save(self.bkgd, 'PNG')
                #print(plate.number(),'->', path, self.bkgd_width, self.bkgd_height)
                break
            except IOError:
                self.bkgd = None
                pass

        for field in plate.fieldList():
            bb = field.boundingBox()
            if bb is None:
                continue
            if self.bkgd_width < self.field_scale*bb[2]+10:
                self.bkgd_width = self.field_scale*bb[2]+10
            if self.bkgd_height < self.field_scale*bb[3]+10:
                self.bkgd_height = self.field_scale*bb[3]+10
    
        self.plate = plate

    def fieldStarting(self, field_num):
        if self.firstField == 0:
            self.firstField = field_num
        if self.lastField < field_num:
            self.lastField = field_num

    def XRefpageHeader(self, canvas, doc):
        canvas.setViewerPreference('FitWindow', 'true')
        canvas.setViewerPreference('CenterWindow', 'true')

        # Draw out headers
        canvas.setStrokeColor(black)
        canvas.setFillColor(black)
        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(self.doc.leftMargin+self.doc.width*0.25,
                self.doc.height+self.doc.bottomMargin+8,
                self.study.studyName())
        canvas.drawCentredString(self.doc.leftMargin+self.doc.width*0.75,
                self.doc.height+self.doc.bottomMargin+8,
                'Variable Cross-Reference')
        canvas.drawString(self.doc.leftMargin, self.doc.bottomMargin-20,
                date.today().isoformat())
        canvas.drawRightString(self.doc.leftMargin+self.doc.width,
                self.doc.bottomMargin-20,
                'Page {0}'.format(canvas.getPageNumber()))

    def CRFpageHeader(self, canvas, doc):
        if not self.plate:
            return
        canvas.setViewerPreference('FitWindow', 'true')
        canvas.setViewerPreference('CenterWindow', 'true')

        # Draw out headers
        canvas.setStrokeColor(black)
        canvas.setFillColor(black)
        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(self.doc.leftMargin+self.doc.width*0.25,
                self.doc.height+self.doc.bottomMargin+8,
                self.study.studyName())
        canvas.drawCentredString(self.doc.leftMargin+self.doc.width*0.75,
                self.doc.height+self.doc.bottomMargin+8,
                'Plate {0}: {1}'.format(self.plate.number(),
                    self.plate.description))
        canvas.drawString(self.doc.leftMargin, self.doc.bottomMargin-20,
                date.today().isoformat())
        canvas.drawRightString(self.doc.leftMargin+self.doc.width,
                self.doc.bottomMargin-20,
                'Page {0}'.format(canvas.getPageNumber()))

        if self.priorities:
            canvas.drawRightString(self.doc.leftMargin+self.doc.width*0.5-55,
                self.doc.bottomMargin-20, 'Priority:')
            canvas.setFont('Helvetica', 8)
            canvas.drawString(self.doc.leftMargin+self.doc.width*0.5+5,
                self.doc.bottomMargin-15, 'detailed on this page')
            canvas.drawString(self.doc.leftMargin+self.doc.width*0.5+5,
                self.doc.bottomMargin-25, 'detailed on another page')
            for i in range(0,5):
                canvas.setFillColor(self.colors[i][0])
                canvas.rect(
                    self.doc.leftMargin+self.doc.width*0.5+(i-5)*10,
                    self.doc.bottomMargin-17, 10, 10, fill=1)
                canvas.setFillColor(self.colors[i][1])
                canvas.drawCentredString(self.doc.leftMargin+
                    self.doc.width*0.5+(i-5)*10+5,
                    self.doc.bottomMargin-15, '{0}'.format(i+1))
                canvas.setFillColor(self.colors[i][2])
                canvas.rect(
                    self.doc.leftMargin+self.doc.width*0.5+(i-5)*10,
                    self.doc.bottomMargin-27, 10, 10, fill=1)
                canvas.setFillColor(black)
                canvas.drawCentredString(self.doc.leftMargin+
                    self.doc.width*0.5+(i-5)*10+5,
                    self.doc.bottomMargin-25, '{0}'.format(i+1))

        # Calculate size of CRF image
        width = (self.doc.width*0.47)-self.gutter/2
        height = self.doc.height
        x_scale = float(width)/self.bkgd_width
        y_scale = float(height)/self.bkgd_height
        scale = x_scale
        if x_scale > y_scale:
            scale = y_scale

        translate_x = (width-(self.bkgd_width*scale))/2
        translate_y = (height-(self.bkgd_height*scale))
        canvas.translate(self.doc.leftMargin + self.gutter/4 + translate_x,
                self.doc.bottomMargin+translate_y)
        #canvas.translate(self.doc.leftMargin, self.doc.bottomMargin+translate_y)
        canvas.scale(scale, scale)

        if self.bkgd:
            canvas.drawImage(ImageReader(self.bkgd),
                    0, self.bkgd_height-self.bkgd_img_height)

        # Draw bounding box around CRF image
        canvas.rect(0,0,self.bkgd_width,self.bkgd_height,fill=0)

        # Set up coordinates for CRF fields
        canvas.translate(0, self.bkgd_height)
        canvas.scale(self.field_scale,self.field_scale)

        # Blank out existing boxes on CRF
        canvas.setStrokeColor(white)
        canvas.setFillColor(white)
        for field in self.plate.fieldList():
            for r in field.rects or []:
                canvas.rect(r.left-2, -r.top+2, r.width+4, -(r.height+4), fill=1)

        # Now draw new boxes
        for field in self.plate.fieldList():
            priority = self.priorities.get((self.plate.number(), field.number))
            if priority is None:
                priority = 5
            if field.number < self.firstField or field.number > self.lastField:
                color = (self.colors[priority-1][2],HexColor(0x333333))
                #color = (grey,white)
            else:
                color = (self.colors[priority-1][0],self.colors[priority-1][1])

            bb = field.boundingBox()
            if bb is None:
                continue
            canvas.setStrokeColor(color[0])
            canvas.rect(bb[0]-2, -bb[1]+2, bb[2]-bb[0]+4, -(bb[3]-bb[1]+4))
            bookmark = 'P{0}F{1}'.format(self.plate.number(), field.number)
            canvas.linkRect(bookmark, bookmark,
                    (bb[0], -bb[1], bb[2], -bb[3]), relative=1)
            canvas.setStrokeColor(black)
            for r in field.rects or []:
                canvas.rect(r.left, -r.top, r.width, -r.height)

            r = field.rects[0]
            canvas.setFillColor(color[0])
            canvas.rect(r.left-2, -r.top+2, r.width+4, -(r.height+4), fill=1)
            canvas.setFillColor(color[1])
            field_str = str(field.number)
            for s in [20,10,8,7]:
                fmp = s/3
                bmp = r.height/2
                if s != 7 and canvas.stringWidth(field_str, 'Helvetica-Bold', s) > r.width:
                    continue
                canvas.setFont('Helvetica-Bold', s)
                canvas.drawCentredString(r.left+(r.width/2), -(r.top+bmp+fmp), str(field.number))
                break

        # Reset range of fields on this page
        self.firstField = 0
        self.lastField = 0

    def build_pdf(self, filename):
        self.doc = BaseDocTemplate(filename, leftMargin=36, rightMargin=36,
                bottomMargin=54, topMargin=54,
                pagesize=landscape((8.5*72,14*72)))
        
        self.gutter = 0.2 * inch
        
        self.doc.addPageTemplates(
            [
                PageTemplate(
                    id='crf',
                    frames=[
                        Frame(
                            self.doc.leftMargin + self.doc.width*0.47,
                            self.doc.bottomMargin,
                            self.doc.width*0.53,
                            self.doc.height,
                            id='right',
                            #leftPadding=0,
                            leftPadding=self.gutter/2,
                            showBoundary=0
                        ),
                    ], onPageEnd=self.CRFpageHeader
                ),
                PageTemplate(
                    id='listing',
                    frames=[
                        Frame(
                            self.doc.leftMargin,
                            self.doc.bottomMargin,
                            self.doc.width/4,
                            self.doc.height,
                            id='col1',
                            rightPadding=self.gutter/2,
                            showBoundary=0
                        ),
                        Frame(
                            self.doc.leftMargin + self.doc.width/4,
                            self.doc.bottomMargin,
                            self.doc.width/4,
                            self.doc.height,
                            id='col2',
                            leftPadding=self.gutter/2,
                            rightPadding=self.gutter/2,
                            showBoundary=0
                        ),
                        Frame(
                            self.doc.leftMargin + 2*self.doc.width/4,
                            self.doc.bottomMargin,
                            self.doc.width/4,
                            self.doc.height,
                            id='col3',
                            leftPadding=self.gutter/2,
                            rightPadding=self.gutter/2,
                            showBoundary=0
                        ),
                        Frame(
                            self.doc.leftMargin + 3*self.doc.width/4,
                            self.doc.bottomMargin,
                            self.doc.width/4,
                            self.doc.height,
                            id='col4',
                            leftPadding=self.gutter/2,
                            rightPadding=self.gutter/2,
                            showBoundary=0
                        ),
                    ], onPageEnd=self.XRefpageHeader
                ),
            ]
        )
        flowables = []
        print('Generating CRFs')

        firstPage = True

        for plate in self.study.plateList():
            if self.plateFilter and \
                not self.plateFilter.contains(plate.number()):
                continue
            if not firstPage:
                flowables.append(PageBreak())
            firstPage = False
            flowables.append(PlateBegin(self, plate))
            flowables.append(self.buildFields(plate))

        flowables.append(NextPageTemplate('listing'))
        if not firstPage:
            flowables.append(PageBreak())
        flowables.append(XRefBegin())
        flowables.extend(self.buildXRef())
        
        self.doc.title = 'Annotated CRF for ' + self.study.studyName()
        self.doc.author = getpass.getuser()
        self.doc.subject = 'Annotated CRF for ' + self.study.studyName()
        try:
            self.doc.build(flowables)
        except IOError:
            print('Unable to create "{0}"'.format(filename))
            sys.exit(2)

#########################################################################
# MAIN
#########################################################################
def main():
    studydir = None
    output = None
    priority_file = None
    enable_lut = False
    lowresonly = False
    extradetail = 'legalrange'
    preferred_background = None
    plates = datafax.rangelist.RangeList(1,500)
    plates.fromString('*')
    try:
        opts, args = getopt.getopt(sys.argv[1:], 's:o:p:',
                ['studydir=', 'output=', 'plates=', 'priority-file=',
                 'prefer-background=', 'legal', 'editchecks', 'lut',
                 'help', 'lowres'])
    except getopt.GetoptError, err:
        print(err)
        sys.exit(2)

    for o, a in opts:
        if o in ('-s', '--studydir'):
            studydir = a
        if o in ('-o', '--output'):
            output = a
        if o in ('-p', '--plates'):
            plates.fromString(a)
        if o == '--priority-file':
            priority_file = a
        if o == '--legal':
            extradetail = 'legalrange'
        if o == '--editchecks':
            extradetail = 'editchecks'
        if o == '--lut':
            enable_lut = True
        if o == '--lowres':
            lowresonly = True
        if o == '--prefer-background':
            preferred_background = a
        if o == '--help':
            print('Annotation Options:')
            print('--plates range                Limit output to the specified plate range')
            print('--priority-file file          Use file for field priority information')
            print('--legal                       Show legal range information (default)')
            print('--editchecks                  Show Edit check information')
            print('--lut                         List first "LUT" field enter EC in coding column')
            print('--prefer-background bkgd(s)   Prefer listed backgrounds (comma separated)')
            print('--lowres                      Use low res backgrounds only (for old studies)')
            sys.exit(0)

    if not studydir:
        print('No --studydir specified')
        sys.exit(2)

    if not output:
        user = os.getenv('DFUSER')
        if user:
            output = os.path.join(studydir, 'work',
                    'annotated-{0}.pdf'.format(user))
        else:
            output = os.path.join(studydir, 'work', 'annotated.pdf')

    if os.path.isfile(output) and not os.access(output, os.W_OK):
        print('Unable to write to:', output)
        sys.exit(2)

    if os.path.isdir(output):
        print('Specified path', output, 'is a directory')
        sys.exit(2)

    study = datafax.Study()
    study.loadFromFiles(studydir)
    a = AnnotatedCRF(study)
    a.setPriorityFile(priority_file)
    a.setExtraDetail(extradetail)
    a.setLowResOnly(lowresonly)
    a.enableLUT(enable_lut)
    a.setPreferredBackground(preferred_background)
    a.filterPlates(plates)

    a.build_pdf(output)
    print('Annotated PDF file is:', output)

if __name__ == '__main__':
    main()
