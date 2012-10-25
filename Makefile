COVERAGE := $(shell which python-coverage)

all: docs retest

docs:
	python setup.py build_sphinx

install:
	python setup.py -q install --root=$(DESTDIR) --prefix=$(PREFIX)
	install -D -m 755 src/img_boss/build_image.py         $(DESTDIR)/usr/share/boss-skynet/build_image.py
	install -D -m 755 src/img_boss/build_ks.py            $(DESTDIR)/usr/share/boss-skynet/build_ks.py
	install -D -m 755 src/img_boss/test_vm_image.py       $(DESTDIR)/usr/share/boss-skynet/test_vm_image.py
	install -D -m 755 src/scripts/img_test_vm.sh          $(DESTDIR)/usr/bin/img_test_vm.sh
	install -D -m 755 src/scripts/img_vm_shutdown         $(DESTDIR)/usr/bin/img_vm_shutdown
	install -D -m 644 src/img_boss/build_image.conf       $(DESTDIR)/etc/skynet/build_image.conf
	install -D -m 644 src/img_boss/build_ks.conf          $(DESTDIR)/etc/skynet/build_ks.conf
	install -D -m 644 src/img_boss/test_vm_image.conf     $(DESTDIR)/etc/skynet/test_vm_image.conf
	install -D -m 755 src/img_boss/update_image_status.py $(DESTDIR)/usr/share/boss-skynet/update_image_status.py
	install -D -m 755 src/img_boss/request_image.py       $(DESTDIR)/usr/share/boss-skynet/request_image.py
	install -D -m 644 src/img_boss/request_image.conf     $(DESTDIR)/etc/skynet/request_image.conf
	install -D -m 644 conf/supervisor/request_image.conf  $(DESTDIR)/etc/supervisor/conf.d/request_image.conf
	install -D -m 644 conf/supervisor/build_ks.conf       $(DESTDIR)/etc/supervisor/conf.d/build_ks.conf
	install -D -m 644 conf/supervisor/test_vm_image.conf  $(DESTDIR)/etc/supervisor/conf.d/test_vm_image.conf
	install -D -m 644 conf/supervisor/build_image.conf    $(DESTDIR)/etc/supervisor/conf.d/build_image.conf
	install -D -m 644 conf/supervisor/update_image_status.conf $(DESTDIR)/etc/supervisor/conf.d/update_image_status.conf
	install -D -m 644 conf/supervisor/img_web.conf    $(DESTDIR)/etc/supervisor/conf.d/img_web.conf

clean:
	python setup.py clean
	rm -rf docs/_build
	rm -f test_results.txt code_coverage.txt .coverage

test_results.txt:
	PYTHONPATH=src/img_boss:$$PYTHONPATH \
	  nosetests -v -w src -e img_web --with-coverage --cover-erase --cover-package=img,img_boss 2> $@ \
	  && cat $@ || (cat $@; exit 1)

code_coverage.txt: test_results.txt
ifdef COVERAGE
	$(COVERAGE) -rm src/img/*.py src/img_boss/*.py 2>&1 | tee code_coverage.txt
else
	@echo "Coverage not available" > code_coverage.txt
endif

retest:
	@rm -f test_results.txt code_coverage.txt .coverage
	$(MAKE) code_coverage.txt

.PHONY: docs retest
