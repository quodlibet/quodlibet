Overview
========

This page contains information on contributing code and patches to Quod 
Libet. If you want to contribute in another way please see the 
[ContributingGuide Contribution Guide] for many ways to help.


Getting started
---------------

Quod Libet now provides its code through Google Code's Mercurial hosting
service. Click the "Source" tab at the top of the screen to view the current
history, or pull a copy using the
`checkout instructions <http://code.google.com/p/quodlibet/source/checkout>`_.

If you have a recent GTK+ version installed and don't need translations you
can simply run QL directly from source without building/installing.
All you need are the [Requirements required dependencies]. Since QL does not
depend on recent versions of them, the ones shipping with your
distribution should work.

See [Downloads#Running_from_Source the instructions] on how to get started.


Code Guidelines
---------------

We try to keep Quod Libet's code in pretty good shape; when submitting a
patch, it's much easier to get it included quickly if you run through this
checklist of common-sense code quality items. Make sure your patch:

  * is `PEP 8 <http://www.python.org/dev/peps/pep-0008/>`_ compliant.
    Yes, this means an 80-character line length.
  * passes existing tests, and includes new ones if at all possible.
  * is commented.
  * adds your name to the copyright header of every file you touch.
    This helps you get credit and helps us keep track of authorship.


Development Workflow
--------------------


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


Branches:

    At the point where no new functionality will be added before a release, 
    a new branch gets created. All bugfix changes should get commited there 
    and merged back in the default branch where new functionality can be 
    added. In case a bugfix was commited to the default branch or an 
    unplanned stable release is needed use the transplant extension to copy 
    those changes to the stable branch(es).

Add changes to the stable branch::

    hg up quodlibet-2.4
    hg commit
    hg commit
       ...
    hg up default
    hg merge quodlibet-2.4
    hg commit -m "Merge stable"


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
          * `Xiph Formats http://www.xiph.org/>`_:
                * `Ogg bitstream structure <http://www.xiph.org/ogg/doc/rfc3533.txt>`_
                * `Vorbis comment structure <http://www.xiph.org/vorbis/doc/v-comment.html>`_
                * `Ogg Vorbis embedding <http://www.xiph.org/vorbis/doc/Vorbis_I_spec.html>`_
                * `FLAC format <http://flac.sourceforge.net/format.html>`_, and
                  `Ogg FLAC embedding <http://flac.sourceforge.net/ogg_mapping.html>`_
                * `Ogg Theora embedding <http://theora.org/doc/Theora_I_spec.pdf>`_
                * [Specs_Ogg Problems in the Ogg specification]
          * [Specs_VorbisComments Special Vorbis comment fields used by QL]
          * [Specs_ID3 Notes on ID3 frame storage]
          * [Specs_Deviations Other deviations from the above specifications ]


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
