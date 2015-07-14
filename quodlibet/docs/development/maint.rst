Maintainer Resources
====================

Useful Specifications
---------------------

    * Code:
          * `PEP-8, style guidelines for Python code <http://www.python.org/dev/peps/pep-0008/>`_
          * `GNOME Human Interface Guidelines <http://developer.gnome.org/hig-book/>`_
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


Tags & Branches
---------------

At the point where no more functionality will be added to a release, a
new branch gets created. All bugfix changes should get committed there and
merged back in the default branch where new functionality can be added. In 
case a bugfix was committed to the default branch or an unplanned stable
release is needed, use Git's `cherry-pick` features to copy those changes to
the stable branch(es).

::

     /|\     /|\
      |       |
      |    2.4.91
    2.5.-1   /   <--- quodlibet-2.5 branch
      |_____/
      |       /|\
      |        |
      |      2.4.1  <--- quodlibet-2.4.1 tag
      |        |
      |      2.4.0.-1
      |        |
      |      2.4  <--- quodlibet-2.4.0 tag
      |        |
      |      2.3.91.-1
      |        |
      |      2.3.91
    2.4.-1    /
      |______/   <--- quodlibet-2.4 branch
      |
      |  <--- default branch
    2.3.-1
      |
     /|\



Translation Backport Braindump
------------------------------

given: translation update for default, branch possibly contains code that got removed in default.

**TODO: needs updating for Git.**

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

**TODO: needs updating for Git.**

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
