=========
 exfalso
=========

----------------
audio tag editor
----------------

:Manual section: 1

SYNOPSIS
========

**exfalso** [ *directory* ]

DESCRIPTION
===========

Ex Falso displays and edits audio metadata tags. Supported formats include
MP3, Ogg Vorbis, FLAC, Musepack (MPC), WavPack, and MOD/XM/IT.

This manual page is only a short reference for Ex Falso. Complete
documentation is available at http://code.google.com/p/quodlibet/wiki/Guide.

OPTIONS
=======

Ex Falso may be given a directory to open on the command line.

TIED TAGS
=========

Many places in Ex Falso allow you to use "tied tags". Tied tags are two tag
names joined together with a "~" like "title~version" or "album~part". Tied
tags result in "nice" displays even when one of the tags is missing; for
example, "title~version" will result in Title - Version when a version tag
is present, but only Title when one isn't. You can tie any number of tags
together.

RENAMING FILES
==============

Ex Falso allows you to rename files based on their tags. In some cases you 
may wish to alter the filename depending on whether some tags are present 
or missing, in addition to their values. A common pattern might be

``<tracknumber>. <title~version>``

You can use a '|' to only text when a tag is present:

``<tracknumber|<tracknumber>. ><title~version>``

You can also specify literal text to use if the tag is missing by adding
another '|':

``<album|<album>|No Album> - <title>``

See http://code.google.com/p/quodlibet/wiki/Guide_Renaming.

BUGS
====

See http://code.google.com/p/quodlibet/issues/list for a list of all
currently open bugs and feature requests.

AUTHORS
=======

Joe Wreschnig and Michael Urman are the primary authors of Ex Falso.

SEE ALSO
========

| http://code.google.com/p/quodlibet/wiki/Guide,
| http://code.google.com/p/quodlibet/wiki/FAQ
