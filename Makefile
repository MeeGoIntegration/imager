COVERAGE := $(shell which python-coverage)

all: docs retest

docs:
	python3 setup.py build_sphinx

install: 
	python3 setup.py install --root=$(DESTDIR) --prefix=$(PREFIX)

	for participant in build_image build_ks make_vdi test_vm_image request_image update_symlinks; \
	do \
		install -D -m 755 src/img_boss/$${participant}.py         $(DESTDIR)/usr/share/boss-skynet/$${participant}.py; \
		install -D -m 644 src/img_boss/$${participant}.conf       $(DESTDIR)/etc/skynet/$${participant}.conf; \
		install -D -m 644 conf/supervisor/$${participant}.conf  $(DESTDIR)/etc/supervisor/conf.d/$${participant}.conf; \
	done

	install -D -m 755 src/img_boss/update_image_status.py $(DESTDIR)/usr/share/boss-skynet/update_image_status.py
	install -D -m 644 conf/supervisor/update_image_status.conf $(DESTDIR)/etc/supervisor/conf.d/update_image_status.conf

	install -D -m 755 src/scripts/img_test_vm.sh        $(DESTDIR)/usr/bin/img_test_vm.sh
	install -D -m 755 src/scripts/img_host_test.sh        $(DESTDIR)/usr/bin/img_host_test.sh
	install -D -m 755 src/scripts/img_vm_shutdown         $(DESTDIR)/usr/bin/img_vm_shutdown



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
