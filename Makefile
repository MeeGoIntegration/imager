docs:
	python setup.py build_sphinx

install:
	python setup.py -q install --root=$(DESTDIR) --prefix=$(PREFIX)
	install -D -m 755 src/img_boss/build_image.py         $(DESTDIR)/usr/share/boss-skynet/build_image.py
	install -D -m 755 src/img_boss/build_ks.py            $(DESTDIR)/usr/share/boss-skynet/build_ks.py
	install -D -m 644 src/img_boss/build_image.conf       $(DESTDIR)/etc/skynet/build_image.conf
	install -D -m 644 src/img_boss/build_ks.conf          $(DESTDIR)/etc/skynet/build_ks.conf
	install -D -m 755 src/img_boss/update_image_status.py $(DESTDIR)/usr/share/boss-skynet/update_image_status.py
	install -D -m 755 src/img_boss/request_image.py       $(DESTDIR)/usr/share/boss-skynet/request_image.py
	install -D -m 644 src/img_boss/request_image.conf     $(DESTDIR)/etc/skynet/request_image.conf

clean:
	python setup.py clean
	rm -rf docs/_build

.PHONY: docs
all: docs
