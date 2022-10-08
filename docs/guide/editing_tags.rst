.. _EditingTags:

Editing Tags
============

.. image:: ../images/tagedit.png
    :scale: 45%
    :align: right

You can edit a song's tags by right clicking on it and selecting *Edit Tags*.

In addition to manually entering the tags, if the song's filename contains
information about all or some of the tags, you can use the *Edit tags from
path* tab to populate these tags automatically. Please see
:ref:`editing tags from path <tags-from-path>` below describing the
process for several songs (the process is the same).


Editing tags for several songs at once
--------------------------------------

To edit tags for several songs at once, select those songs (using Ctrl or
Shift), then right click and "Edit Tags".

Note that in the tag-editing window that opens, you have several tabs
available. The default *Edit tags* tab will apply the same tags to all
marked songs, so it only makes sense for tags that are common to all songs,
e.g. album or genre. However, the tabs *Tags from Path* and *Track Numbers*
let you edit tags that differ across songs:

.. _tags-from-path:


Editing tags from path
^^^^^^^^^^^^^^^^^^^^^^

The tab *Tags from Path* lets you batch edit tags that differ across songs,
such as title, by using the filename as input. Note that you can customize
the pattern that the tag editor uses to extract the tags from the filename:
just imitate the pattern you see for your files, putting the relevant tag
name in angular brackets.

Example:

 * Your file names have a pattern like this:
   ``01 - The Beatles - Yellow Submarine.ogg``
 * Edit the pattern to show: ``<tracknumber> - <artist> - <title>``
 * Note that you can omit the file extension in your pattern.
 * Click on *Preview* to see how your pattern would be interpreted for
   each song.

The preview is shown to the right of the current value; you may have to
scroll right to see it.

You can even include information from the entire path in this pattern
matching:

 * You have files like this
   ``~/home/username/music/favourites/the_beatles/yellow_submarine/01 - Yellow Submarine.ogg``
 * Use pattern: ``<artist>/<album>/<tracknumber> - <title>``
 * In that case, you probably want to check the boxes for
   *Replace underscores with spaces* and *Title-case tags*.
 * Note that QL automatically digs as far upwards in the folder hierarchy as
   it needs to given the pattern you put in, so you don't need to enter any
   (potentially complex) folder structure that is above the needed info.

You can see recent patterns you used by clicking on the drop down arrow to
the right of the pattern input field. Additionally, clicking on *Edit saved
values* in the drop-down that opens will let you save patterns and
optionally name them. Use this for patterns that you apply frequently. If
you leave the *Name* field blank for your pattern, the name will be
identical to the pattern.


Batch edit track numbers
^^^^^^^^^^^^^^^^^^^^^^^^

The *Track Numbers* tab in the tag editing window lets you batch edit track
numbers ascending across the files. If your files are in the correct order,
you simply check that you like the *Start from* and *Total tracks* values.
If you put in any value greater than one for *Total tracks*, QL will use a
tracknumber pattern `tracknumber/totaltracks`, e.g. ``2/12`` for *Total
tracks* = ``12``. If you only want a single number for the track number,
set *Total tracks* to zero.

If your files are not in the correct order, for example because they are
sorted alphabetically, you can drag and drop them into the desired order in
the *File* field inside the *Track numbers* tab of the tag editing window
before (optionally) clicking preview and then save.


Rename Files Based on Tags
--------------------------

QL also lets you rename the files of songs based on tags, either for one
song or for several songs. Edit patterns the same way you would for *Edit
tags from path* (see above). This feature even lets you move them to a
different directory; for more info see the :ref:`renaming files
guide <RenamingFiles>`.

Splitting Tags
--------------

If a tag contains a value that can be regarded as multiple tag values, it is
often possible to split the tag. This can be done by right-clicking on the tag
and then selecting the appropriate split in the ``Split Tag`` menu. 

There are in general two types of tag splitting possible: splitting on a single
character and *subtag* splitting (extracting values in enclosures). The
separating characters for both can be configured in the *Tags* tab in the
preferences.
(Note that the "Split on" values in the configure dialog are space-separated)
separated).

Splitting on a single character - like ``,`` or ``&`` - will split a tag into
multiple tags of the same type, but with different values. An example of this
can be an artist tag with the value ``Foo, Bar``, that can be split into two
separate tags *artist* = ``Foo`` and *artist* = ``Bar``.

With *subtag* splitting, the end of the tag value must contain a value enclosed
in some pair of characters - like ``()`` or ``[]``. Depending on the type of
tag, the enclosed value can then be extracted and put in a new tag. An example
of this can be an album tag with the value ``Album (CD 1)``, which can be split
into *album* = ``Album`` and *discnumber* = ``1``. The enclosure can also
contain multiple values separated by a single-character separator as explained
above, like *artist* = ``Foo (Bar, Baz)``, which can be split into *artist* =
``Foo``, *performer* = ``Bar`` and *performer* = ``Baz``.
