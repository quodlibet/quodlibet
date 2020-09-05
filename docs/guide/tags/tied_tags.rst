.. _TiedTags:

Tied Tags
=========

Tied tags are expressions to produce a readable formatted output of more 
than one tag. Tag values are outputted left to right, with the default 
output separator as ``-``. To combine multiple tags start the expression 
with ``~`` and separate each tag by ``~`` again.

Examples:

============================== ================================ =========================================================
Included Tags                  Tied Tag                         Result
============================== ================================ =========================================================
artist, title                  ``~artist~title``                *Bob Marley - Jammin'*
~#track, ~dirname              ``~~#track~~dirname``            *5 - /home/user/music/Reggae*
date, artist, album, ~filesize ``~date~artist~album~~filesize`` *2000 - Bob Marley - Songs of Freedom (Various) - 6.9 MB*
============================== ================================ =========================================================

Usage in Quod Libet
-------------------

Tied tags can be used in tag patterns and searches as if they were normal 
tags:

::

    ~artist~title=/AC.?DC/

::

    <tracknumber|<tracknumber>. ><title~version>
