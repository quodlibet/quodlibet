========
 operon
========

-------------------------
command line music tagger
-------------------------

:Manual section: 1

SYNOPSIS
========

| **operon** [--version] [--help] [-v | --verbose] <*command*> [<*argument*>...]
| **operon help** <*command*>

OPTIONS
=======

-h | --help
    Display help and exit

--version
    Print the program version

-v, --verbose
    Verbose mode

COMMAND-OVERVIEW
================

Edit Tags
---------

|   *add*         Add a tag value
|   *remove*      Remove a tag value
|   *set*         Set a tag and remove existing values
|   *clear*       Remove tags
|   *copy*        Copy tags from one file to another
|   *dump*        Print all tags to stdout

Show file metadata
------------------

|   *list*        List tags
|   *info*        List file information
|   *print*       Print tags based on the given pattern

Edit Embedded Images
--------------------

|   *image-extract*    Extract embedded images

Miscellaneous
-------------

|   *tags*        List all common tags
|   *help*        Display help information

EDIT TAGS
=========

add
---

Add a new tag ``<tag>`` with the value ``<value>`` to all files.

operon add [-h] <tag> <value> <file>...

-h | --help
    Display help and exit

Example:
    operon add artist 'The Beatles' song1.ogg song2.ogg

remove
------

Remove all values from the tag ``<tag>`` that match either ``<value>`` or 
the regular expression ``<pattern>`` from all files.

operon remove [-h] [--dry-run] <tag> (-e <pattern> | <value>) <file>...

-h | --help
    Display help and exit

--dry-run
    Print the results without changing any files

-e | --regexp <regexp>
    Remove all tag values that match the given regular expression

Example:
    operon remove artist 'The Beatles' song.ogg

set
---

Replace all values of the tag ``<tag>`` by ``<value>`` in all files.

operon set [-h] [--dry-run] <tag> <value> <file>...

-h | --help
    Display help and exit

--dry-run
    Print the results without changing any files

Example:
    operon set artist 'The Beatles' song.ogg

clear
-----

Remove all tags that match ``<tag>`` or the regular expression ``<pattern>``
from all files. If `--all` is specified, all known tags will be removed.

operon clear [-h] [--dry-run] (-a | -e <pattern> | <tag>) <file>...

-h | --help
    Display help and exit

--dry-run
    Print the results without changing any files

-a | --all
    Remove all tags

-e | --regexp <regexp>
    Remove all tags that match the given regular expression

Example:
    operon clear -a song.ogg

    operon clear -e 'musicbrainz\_.*' song.ogg

    operon clear date song.ogg

copy
----

Copy all tags from the file *<source>* to *<dest>*. All tags in ``<dest>`` 
will be preserved. In case the destination format doesn't support setting a 
tag from source, no tags will be copied. To ignore tags that aren't 
supported by the destination format pass *--ignore-errors*.

operon copy [-h] [--dry-run] [--ignore-errors] <source> <dest>

-h | --help
    Display help and exit

--dry-run
    Print the results without changing any files

--ignore-errors
    Skip tags which the target file does not support

Example:
    operon copy song.flac song.ogg

dump
----

Print all tags to stdout. The format is not specified. The data can be 
loaded again using *operon load*, given the same version was used to create 
the data.

operon dump [-h] <src-file>

-h | --help
    Display help and exit

Example:
    operon dump song.flac > backup.tags

SHOW FILE METADATA
==================

list
----

Lists all tags, values and a description of each tag in a table.

operon list [-h] [-a] [-t] [-c <c1>,<c2>...] <file>

-h | --help
    Display help and exit

-a | --all
    Also list programmatic tags

-t | --terse
    Output is terse and suitable for script processing

-c | --columns <name>,...
    Defines which columns should be printed and in which order

Example:
    operon list -a song.flac

    operon list -t -c tag,value song.ogg

info
----

Lists non-tag metadata like length, size and format.

operon info [-h] [-t] [-c <c1>,<c2>...] <file>

-h | --help
    Display help and exit

-t | --terse
    Output is terse and suitable for script processing

-c | --columns <name>,...
    Defines which columns should be printed and in which order

Example:
    operon info a.ogg

print
-----

Prints information per file built from tag values. The pattern can be 
customized by passing a pattern string (See ``quodlibet``\(1) for the 
pattern format)

operon print [-h] [-p <pattern>] <file>...

-h | --help
    Display help and exit

-p | --pattern <pattern>
    Use a custom pattern

Example:
    operon print -p "<album> - <artist>" a.ogg


EDIT EMBEDDED IMAGES
====================

image-extract
-------------

Extract all embedded images to the current working directory or the specified
destination directory.

operon image-extract [-h] [--dry-run] [--primary] [-d <destination>] <file>...

-h | --help
    Display help and exit

--dry-run
    Print the found images and resulting file paths but don't save them

--primary
    Only extract the primary images for each file

-d | --destination <destination>
    Save all images to the specified destination

COMMANDS
========

help
----

operon help [<command>]

Example:
    operon help list


SEE ALSO
========

| ``regex``\(7)
| ``exfalso``\(1)
| ``quodlibet``\(1)
