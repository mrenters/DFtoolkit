all:	3rdparty/libxlsxwriter/lib/libxlsxwriter.a
	mkdir -p dist/PHRI dist/reports dist/modules
	cd sigtrack; make
	cd dfpython/datafax; ../python27 setup.py sdist
	cd dfpython; cp python27 annotate.py closeout.py  eclist.py  make_closeout_db.py \
	   qc2excel.py  schemadiff.py  signature.py \
	   ../dist/PHRI
	cd reports; cp annotateCRF EClist ESIG QC2Excel QC2ExcelEmail \
		QC2ExcelSiteEmail schema2excel schemadiff ../dist/reports
	cp dfpython/datafax/dist/* dist/modules

clean:
	cd 3rdparty/libxlsxwriter; make clean
	rm -rf dist

3rdparty/libxlsxwriter/lib/libxlsxwriter.a:
	cd 3rdparty/libxlsxwriter; make
