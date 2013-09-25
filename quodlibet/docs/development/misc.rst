Miscellaneous
=============

Working with PyCharm
--------------------

QL adds some commonly used functions to `__builtin__` which PyCharm can't
resolve. You can remove the resulting warnings by adding the function names
to the `Ignore references` list under `File > Settings > Project Settings >
Inspections > Python > Unresolved references`.

Add the following names to the list:

* `_`
* `Q_`
* `N_`
* `ngettext`
* `print_`
* `print_d`
* `print_w`
* `print_e`


Useful Specifications
---------------------

    * Code:
          * `PEP-8, style guidelines for Python code <http://www.python.org/dev/peps/pep-0008/>`_
          * `GNOME Human Interface Guidelines <http://developer.gnome.org/projects/gup/hig/2.0/>`_
    * File Formats:
          * `APEv2 tag specification <http://wiki.hydrogenaudio.org/index.php?title=APEv2_specification>`_
          * `MP3/ID3 <http://www.id3.org/>`_:
                * `MPEG audio header format <http://www.dv.co.yu/mpgscript/mpeghdr.htm>`_,
                  and the `Xing VBR header <http://www.codeproject.com/audio/MPEGAudioInfo.asp#XINGHeader>`_
                * `ID3v2.4 structure <http://www.id3.org/id3v2.4.0-structure.txt>`_,
                  `ID3v2.4 frame list <http://www.id3.org/id3v2.4.0-frames.txt>`_,
                  `ID3v2.3 <http://www.id3.org/id3v2.3.0.html>`_,
                  `ID3v2.2 <http://www.id3.org/id3v2-00.txt>`_, and
                  `ID3v1 <http://www.id3.org/id3v1.html>`_
                * `Lyrics3v2 <http://www.id3.org/lyrics3200.html>`_
          * `Xiph Formats <http://www.xiph.org/>`_:
                * `Ogg bitstream structure <http://www.xiph.org/ogg/doc/rfc3533.txt>`_
                * `Vorbis comment structure <http://www.xiph.org/vorbis/doc/v-comment.html>`_
                * `Ogg Vorbis embedding <http://www.xiph.org/vorbis/doc/Vorbis_I_spec.html>`_
                * `FLAC format <http://flac.sourceforge.net/format.html>`_, and
                  `Ogg FLAC embedding <http://flac.sourceforge.net/ogg_mapping.html>`_
                * `Ogg Theora embedding <http://theora.org/doc/Theora_I_spec.pdf>`_


Downstream Bug Trackers
-----------------------

  * `Fedora <https://admin.fedoraproject.org/pkgdb/acls/bugs/quodlibet>`_
  * `Debian <http://bugs.debian.org/cgi-bin/pkgreport.cgi?pkg=quodlibet>`_
  * `Arch Linux <https://bugs.archlinux.org/?project=1&string=quodlibet>`_
  * `Ubuntu <https://launchpad.net/ubuntu/+source/quodlibet/+bugs>`_


Translation Backport Braindump
------------------------------

given: translation update for default, branch possibly contains code that got removed in default.

::

    hg up default
    # (commit translations to default)
    hg update quodlibet-2.5
    ./setup.py build_mo
    msgcat --use-first brach.po default.po > branch.po
    ./setup.py test
    # (review changes..)
    hg up default
    hg merge --tool internal:local quodlibet-2.5


Release Checklist
-----------------

Stable Release:

  * Run test suite on karmic/arch
  * Update version
  * Run setup.py build_mo
  * Update NEWS
  * Commit (release prep)
  * hg tag quodlibet-x.y.z
  * Update version
  * Commit (version bump)
  * hg up default
  * hg merge --tool internal:local quodlibet-x.y

Files:

   * Run setup.py sdist
   * Create the plugin tarball

Windows:

   * hg up quodlibet-x.y.z
   * setup.py build_mo
   * win_installer_build.py quodlibet-x.y.z
   * copy MSVC files
   * reinstall / test
