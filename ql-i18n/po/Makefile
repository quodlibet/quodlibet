messages.pot: quodlibet.glade.h ../quodlibet.py ../library.py
	xgettext --from-code=utf-8 -k_ -kN_ -o $@ quodlibet.glade.h ../quodlibet.py ../library.py

quodlibet.glade.h: ../quodlibet.glade
	intltool-extract --type=gettext/glade ../quodlibet.glade
	mv ../quodlibet.glade.h .

%.mo: %.po
	msgfmt -o $@ $<

clean:
	rm -f messages.pot quodlibet.glade.h *.mo
