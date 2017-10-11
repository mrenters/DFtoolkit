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

##############################################################################
# Generate Signature PDFs
##############################################################################

from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, blue, green, cyan, yellow, \
    magenta, orange, purple, black, white, darkgrey, darkslategrey, \
    lightgrey, darkblue, HexColor
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import Paragraph, Frame, Table, TableStyle, \
    KeepTogether, Flowable, SimpleDocTemplate, PageBreak, CondPageBreak
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.platypus.tableofcontents import TableOfContents

from collections import namedtuple

import os
import getopt
import sys
import re
import datafax
import sqlite3


##############################################################################
# stylesheet - Stylesheet for document
##############################################################################
def stylesheet():
    styles= {
        'default': ParagraphStyle(
            'default',
            fontName='Helvetica',
            fontSize=10,
            leading=12,
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
    styles['rightheader'] = ParagraphStyle(
        'rightheader',
        parent=styles['default'],
        alignment=TA_RIGHT
    )
    styles['bold'] = ParagraphStyle(
        'bold',
        parent=styles['default'],
        fontName='Helvetica-Bold',
    )
    styles['title'] = ParagraphStyle(
        'title',
        parent=styles['default'],
        fontName='Helvetica-Bold',
        backColor=lightgrey,
        spaceBefore=12,
        spaceAfter=3,
        fontSize=14,
        leading=18
    )
    styles['header'] = ParagraphStyle(
        'header',
        parent=styles['default'],
        borderColor=black,
        borderWidth=1,
        borderPadding=5,
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
# DFsignaturePDF - PDF file of images, data and audit trail
##############################################################################
class DFsignaturePDF(object):

    def __init__(self, name, study_name):
        self.doc = BaseDocTemplate(name, title=name, showBoundary=0,
                pagesize=letter)
        template = PageTemplate('normal', [Frame(inch, inch, 6.5*inch, 8.4*inch)], onPageEnd=self.pageHeader)
        self.doc.addPageTemplates(template)
        #self.doc.setProgressCallBack(self.progressCB)
        self.styles = stylesheet()
        self.jobsize = 1
        self.headerId = 0
        self.headerVisitLabel = ''
        self.headerPlateLabel = ''
        self.studyName = study_name
        self.outlines = []
        self.outlineDesc = None
        self.outlineVisitLabel = None
        self.outlineID = 0
        self.content = [DFOutlines(self.outlines)]

    def close(self):
        self.doc.build(self.content)

    def setPageHeader(self, pid, visit_label, signature_label):
        self.headerId = pid
        self.headerVisitLabel = visit_label
        self.headerPlateLabel = signature_label

    def pageHeader(self, canvas, doc):
        if not self.headerId:
            return

        canvas.saveState()
        #canvas.rect(inch, 9.4*inch, 6.5*inch, 0.6*inch)

        canvas.setFillColor(black)
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(4.25*inch, 9.5*inch+24, 'eSignature Report')
        canvas.drawCentredString(4.25*inch, 9.5*inch+12, self.studyName)
        canvas.drawString(inch+6, 9.5*inch, 'Patient: {0}'.format(self.headerId))
        page_number = 'Page %s' % canvas.getPageNumber()

        canvas.setFont('Helvetica', 10)
        canvas.drawCentredString(4.25*inch, 0.75*inch, page_number)

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


    def outputTable(self, label, values):
        styleH = self.styles['title']
        styleN = self.styles['default']
        self.content.append(CondPageBreak(2*inch))
        self.content.append(Paragraph(label, styleH))

        if not values:
            self.content.append(Paragraph('No New or Changed Fields.', styleN))
            return

        fieldValueList = [[
                Paragraph('<para alignment="right"><b>Plate</b></para>', styleN),
                Paragraph('<para alignment="right"><b>Field</b></para>', styleN),
                Paragraph('<b>Description</b>', styleN),
                Paragraph('<b>Value</b>', styleN)]]

        for (plate, field, fdesc, fvalue) in values or []:
            list_value = self.escape_string(fvalue)
            if field < 0:
                field = '-'
            else:
                field = str(field)

            fieldValueList.append([
                    Paragraph('<para alignment="right">{0}.</para>'.format(plate), styleN),
                    Paragraph('<para alignment="right">{0}.</para>'.format(field), styleN),
                    Paragraph(fdesc, styleN),
                    Paragraph('<para>{0}</para>'.format(list_value), styleN)])


        table = Table(fieldValueList, colWidths=[
            0.1*6.3*inch,
            0.1*6.3*inch,
            0.3*6.3*inch,
            0.5*6.3*inch], splitByRow=1, repeatRows=1, hAlign='LEFT')
        tablestyle = TableStyle([
            ('VALIGN', (0,0), (-1, -1), 'TOP'),
            ('LINEBEFORE', (3,0), (3, -1), 1, lightgrey),
            ('LINEABOVE', (0,0), (-1, -1), 1, lightgrey)])
        table.setStyle(tablestyle)
        self.content.append(table)

    def outputSignatureData(self, visit, plate, desc, who, sdate, stime,
            fieldchanges, signaturevalues):
        styleH = self.styles['title']
        styleN = self.styles['default']
        styleR = self.styles['rightheader']
        styleB = self.styles['bold']
        sdate = sdate[0:4] + '/' + sdate[4:6] + '/' + sdate[6:8]
        stime = stime[0:2] + ':' + stime[2:4] + ':' + stime[4:6]

        if desc != self.outlineDesc:
            self.outlines.append([desc, 'o{0}'.format(self.outlineID), 0, True])
            self.outlineDesc = desc
            self.outlineVisitLabel = None

        if self.headerVisitLabel != self.outlineVisitLabel:
            self.outlines.append([self.headerVisitLabel, 'o{0}'.format(self.outlineID+1), 1, True])
            self.outlineVisitLabel = self.headerVisitLabel

        bookmark = '{0} {1} {2}'.format(sdate, stime, who)
        self.outlines.append([bookmark, 'o{0}'.format(self.outlineID+2), 2, True])
        self.content.append(Paragraph('<a name="o{0}"/><a name="o{1}"/><a name="o{2}"/>Signature Details'.format(self.outlineID, self.outlineID+1, self.outlineID+2), styleH))
        signatureDetailsList = []
        signatureDetailsList.append([Paragraph('Server Time', styleR),
            Paragraph('{0} {1}'.format(sdate, stime), styleB)])
        signatureDetailsList.append([Paragraph('Description', styleR),
            Paragraph(desc, styleB)])
        signatureDetailsList.append([Paragraph('Login', styleR),
            Paragraph(who, styleB)])
        signatureDetailsList.append([Paragraph('Visit', styleR),
            Paragraph('{0} ({1})'.format(visit, self.headerVisitLabel), styleB)])
        signatureDetailsList.append([Paragraph('Plate', styleR),
            Paragraph('{0} ({1})'.format(plate, self.headerPlateLabel), styleB)])
        table = Table(signatureDetailsList, colWidths=[
            0.2*6.3*inch,
            0.8*6.3*inch], splitByRow=1, repeatRows=1, hAlign='LEFT')
        tablestyle = TableStyle([
            ('VALIGN', (0,0), (-1, -1), 'TOP'),
            ('LINEBEFORE', (1,0), (1, -1), 1, lightgrey),
            ('LINEABOVE', (0,0), (-1, -1), 1, lightgrey)])
        table.setStyle(tablestyle)
        self.content.append(table)

        self.outputTable('New or Changed Data Values', fieldchanges)
        self.outputTable('Signature Field Values', signaturevalues)
        self.outlineID += 3

    def nextPage(self):
        self.content.append(PageBreak())

    ###########################################################################
    # escape_string - Escape special characters
    ###########################################################################
    def escape_string(self, s):
        s=s.replace('&', '&amp;')
        s=s.replace('<', '&lt;')
        s=s.replace('>', '&gt;')
        return s;

##############################################################################
# SignatureSQL
##############################################################################
class SQLSignatureLog(object):
    def __init__(self):
        self.patients = datafax.rangelist.RangeList(1, 281474976710656)
        self.plates = datafax.rangelist.RangeList(1, 500)
        self.visits = datafax.rangelist.RangeList(0, 65535)
        self.study = datafax.Study()
        self.db = None

    def setSQL(self, db):
        self.db = db

    def setStudyDir(self, studydir):
        self.study.loadFromFiles(studydir)

    def setPatients(self, v):
        self.patients.fromString(v)

    def setPlates(self, v):
        self.plates.fromString(v)

    def setVisits(self, v):
        self.visits.fromString(v)

    def getMatchingPatients(self):
        clauses = []
        pid_clause = self.patients.toSQL('pid')
        if pid_clause:
            clauses.append(pid_clause)
        visit_clause = self.visits.toSQL('visit')
        if visit_clause:
            clauses.append(visit_clause)
        plate_clause = self.plates.toSQL('plate')
        if plate_clause:
            clauses.append(plate_clause)
    
        if clauses:
            where_clause = 'where ' + ' and '.join(clauses)
        else:
            where_clause = ''

        # Get a list of unique patient IDs that match criteria
        return self.db.execute('''
            select distinct pid
            from signings ''' + where_clause + ''' order by pid''').fetchall()

    def getSigningsForPatient(self, pid):
        # Build Select statement for fetching records
        clauses = ['pid=?']
        visit_clause = self.visits.toSQL('visit')
        if visit_clause:
            clauses.append(visit_clause)
        plate_clause = self.plates.toSQL('plate')
        if plate_clause:
            clauses.append(plate_clause)

        signings_select = '''
            select txnid, sigid, visit, plate, sdesc, signer, sdate, stime
            from signings
            where ''' + ' and '.join(clauses) + '''
            order by sigid, visit, txnid'''
        return self.db.execute(signings_select, (pid,)).fetchall()

    def getFieldChangesForTxn(self, txnid, sigid):
        return self.db.execute('''
            select plate, field, fdesc, fvalue
            from data_values
            where txnid=? and sigid=?''', (txnid, sigid)).fetchall()

    def getSignatureValuesForTxn(self, txnid, sigid):
        return self.db.execute('''
            select plate, field, fdesc, fvalue
            from signature_values
            where txnid=? and sigid=?
            order by plate, field''', (txnid, sigid)).fetchall()

    def sortFieldChanges(self, visit_num, fieldvalues):
        visitentry = self.study.visitMap().entry(visit_num)
        sortedRecs=[]

        # For each record, get its plate display order
        for (plate_num, field, fdesc, fvalue) in fieldvalues:
            if visitentry is None:
                plateorder = 0
            else:
                plateorder = visitentry.plateOrder(plate_num)

            sortedRecs.append((plate_num, plateorder, field, fdesc, fvalue))

        # Sort by plate order, plate number, field number
        sortedRecs.sort(key=lambda x: (x[1], x[0], x[2]))
        fieldvalues = []
        for (plate_num, plateorder, field, fdesc, fvalue) in sortedRecs:
            fieldvalues.append((plate_num, field, fdesc, fvalue))
        return fieldvalues


    def createPDF(self):
        for (pid,) in self.getMatchingPatients():
            print('Patient',pid)
    	    pdf = DFsignaturePDF('{0}.pdf'.format(pid), self.study.studyName())
            for (txnid, sigid, visit, plate, sdesc, signer, sdate, stime) \
                    in self.getSigningsForPatient(pid):
                visitlabel = self.study.visitLabel(visit)
                platelabel = self.study.pageLabel(visit, plate)
                pdf.setPageHeader(pid, visitlabel, platelabel)

                fieldchanges = self.sortFieldChanges(visit, \
                        self.getFieldChangesForTxn(txnid, sigid))

                signature_values = self.getSignatureValuesForTxn(txnid, sigid)

                pdf.outputSignatureData(visit, plate, sdesc, signer, \
                        sdate, stime, fieldchanges, signature_values)
                pdf.nextPage()

            #pdf.generateSignatureLogs(db, clauses, pid)
    	    pdf.close()

############################################################################
# MAIN
############################################################################
def main():
    db = 'data.db'
    studydir = None

    siglog = SQLSignatureLog();

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'd:s:I:P:V:',
                ['db=', 'studydir=', 'ids=', 'plates=', 'visits=' ])
    except getopt.GetoptError, err:
        print(err)
        sys.exit(2)

    for o, a in opts:
        if o in ('-d', '--db'):
            db = a
        if o in ('-I', '--ids'):
            siglog.setPatients(a)
        if o in ('-P', '--plates'):
            siglog.setPlates(a)
        if o in ('-V', '--visits'):
            siglog.setVisits(a)
        if o in ('-s', '--studydir'):
            studydir = a
            
    if studydir is None:
        print('No --studydir specified')
        sys.exit(2)
    else:
        siglog.setStudyDir(studydir)

    siglog.setSQL(sqlite3.connect(db))

    siglog.createPDF()



if __name__ == '__main__':
    main()
