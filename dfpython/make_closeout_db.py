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

import os
import codecs
import getopt
import sys
import sqlite3
import shlex
import subprocess

#####################################################################
# Decode text as Unicode, and if that doesn't work, try Latin-1
#####################################################################
def to_unicode(s):
    try:
        u = s.decode('utf-8')
    except UnicodeDecodeError:
        u = s.decode('latin-1')
    return u

def main():
    sstrings = {}
    ssid_seq = 0
    study_num = None
    patients = None
    db = 'data.db'

    try:
        opts, args = getopt.getopt(sys.argv[1:], 's:d:I:',
            ['study=', 'db=', 'ids='])
    except getopt.GetoptError, err:
        print(err)
        sys.exit(2)

    for o,a in opts:
        if o in ('-s', '--study'):
            study_num = int(a)
        if o in ('-d', '--db'):
            db = a
        if o in ('-I', '--ids'):
            patients = a

    if study_num is None:
        print('No study specified')
        sys.exit(2)

    sql = sqlite3.connect(db)
    sql.execute('''pragma page_size=4096''')
    sql.execute('''pragma cache_size=40000''')
    sql.execute('''pragma locking_mode=EXCLUSIVE''')
    sql.execute('''pragma synchronous=OFF''')
    sql.execute('''drop table if exists data''')
    sql.execute('''drop table if exists audit''')
    sql.execute('''drop table if exists shared_strings''')
    sql.execute('''create table data (
        pid int not null,
        visit int not null,
        plate int not null,
        level int not null,
        data text)''')
    sql.execute('''create table audit (
        pid int not null,
        visit int not null,
        plate int not null,
        op text not null,
        tdate text not null,
        ttime text not null,
        who text not null,
        type text not null,
        status int not null,
        level int not null,
        code text,
        reason text,
        metafnum int not null,
        funiqueid int not null,
        fnum int not null,
        fdescid int not null,
        oldval text,
        newval text,
        oldvaldec text,
        newvaldec text
        )''')
    sql.execute('''create table shared_strings (
        id int not null primary key,
        string text)''')
    print('Reading data...')

    # Get a list of plate numbers
    proc = subprocess.Popen(['DFlistplates.rpc', '-s', str(study_num)],
            stdout=subprocess.PIPE)
    plates = proc.stdout.read().split()
    proc.wait()

    # Read data records
    for p in plates:
        print('  ', p)
        if patients:
            params = ['DFexport.rpc', '-s', 'primary', '-I', patients,
                    str(study_num), p, '-']
        else:
            params = ['DFexport.rpc', '-s', 'primary', str(study_num), p, '-']
        proc = subprocess.Popen(params, stdout=subprocess.PIPE)
        for data in proc.stdout:
            data = to_unicode(data)
            data = data.rstrip('\n')
            fields = data.split('|')

            id = int(fields[6])
            visit = int(fields[5])
            plate = int(fields[4])
            level = int(fields[1])

            sql.execute('''insert into data values(?, ?, ?, ?, ?)''', \
                (id, visit, plate, level, data))
        sql.commit()
    proc.wait()

    print('Reading audit information...')
    if patients:
        params = ['DFaudittrace', '-s', str(study_num),
            '-I', patients, '-d', '19900101-today', '-N', '-q', '-r']
    else:
        params = ['DFaudittrace', '-s', str(study_num),
            '-d', '19900101-today', '-N', '-q', '-r']
    proc = subprocess.Popen(params, stdout=subprocess.PIPE)
    for data in proc.stdout:
        data = to_unicode(data)
        data = data.rstrip('\n')
        (op, date, time, who, id, visit, plate, uniqueid, metafnum, \
                status, level, maxlevel, codevalue, codetext, oldval, newval, \
                fnum, fdesc, dec_oldval, dec_newval) = data.split('|')

        type = 'd'
        uniqueid = int(uniqueid)
        if uniqueid > 0:
            type = 'q'        # QC
        elif uniqueid < 0:
            uniqueid = -uniqueid
            type = 'r'        # Reason


        if type == 'd':     # Reset meta field number for data fields
            uniqueid = int(metafnum)
            metafnum = '0'

        # Used shared strings for field descriptions to reduce size of DB
        ssid = sstrings.get(fdesc)
        if ssid == None:
            sstrings[fdesc] = ssid_seq
            sql.execute('''insert into shared_strings values(?, ?)''',
                    (ssid_seq, fdesc))
            ssid = ssid_seq
            ssid_seq += 1

        sql.execute('''insert into audit values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', \
                (id, visit, plate, op, date, time, who, type, status, level, \
                codevalue, codetext, metafnum, uniqueid, fnum, ssid, oldval, newval,\
                dec_oldval, dec_newval))
    sql.commit()
    proc.wait()

    print('Creating index on data...')
    sql.execute('''create index data_keys on data(pid, visit, plate)''')
    print('Creating index on audit table...')
    sql.execute('''create index audit_keys on audit(pid, visit, plate)''')
    sql.close()
    print('Done.')

if __name__ == "__main__":
    main()
