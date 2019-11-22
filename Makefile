all:	sigtrack-dir python-dir reports-dir doc-dir

sigtrack-dir: 3rdparty/libxlsxwriter/lib/libxlsxwriter.a
	mkdir -p dist/bin
	cd sigtrack; make

doc-dir:
	mkdir -p dist/doc
	cp doc/* dist/doc

python-dir:
	mkdir -p dist/packages dist/modules dist/bin dist/python
	cd dfpython/datafax; ../python27 setup.py sdist --dist-dir ../../dist/modules
	for prog in annotate.py closeout.py eclist.py make_closeout_db.py \
           qc2excel.py schemadiff.py signature.py ;\
	do \
		EXEC=`basename $$prog .py`; \
		pyinstaller --paths `pwd`/dfpython/datafax \
			--distpath dist/packages \
			--noconfirm \
			--specpath tmp \
			--hidden-import=datafax \
			--hidden-import=pdfrw dfpython/$$prog; \
		cp dfpython/wrapper dist/bin/$$EXEC; \
		cp dfpython/$$prog dist/python; \
	done

reports-dir:
	mkdir -p dist/reports
	for report in annotateCRF EClist ESIG QC2Excel QC2ExcelEmail \
		QC2ExcelSiteEmail schema2excel schemadiff ;\
	do \
		cp reports/$$report  dist/reports; \
	done
	
clean:
	cd 3rdparty/libxlsxwriter; make clean
	cd sigtrack; make clean
	rm dfpython/datafax/datafax/*.pyc
	rm -rf dist tmp build

3rdparty/libxlsxwriter/lib/libxlsxwriter.a: 3rdparty/libxlsxwriter/.git
	cd 3rdparty/libxlsxwriter; make

3rdparty/libxlsxwriter/.git:
	git submodule init
	git submodule update
