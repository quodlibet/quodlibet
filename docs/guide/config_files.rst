.. _ConfigFiles:

Configuration Files
===================

QL stores some of its configuration as plain text files, and in some cases
it may be convenient to edit these files directly, or to synchronize them
across different computers/ home directories.

Like many Linux applications, QL stores user configuration in a hidden
directory, in this case ``~/.quodlibet``. (Note that this may not always be
the case, see :ref:`the FAQ <MetadataLocation>` for details). Feel free to
explore; but maybe make a backup of the directory first.

Saved values for search, tagging and renaming patterns
------------------------------------------------------

For :ref:`searching your library <Searching>`, :ref:`editing tags from a
filename pattern <EditingTags>`, and :ref:`renaming files based on tags
<RenamingFiles>`, you can save the (search or pattern) values you enter for
later use. See the relevant section for how to do it using the GUI.

The patterns you create using "saved values" are in fact stored in simple
text files:

 * ``~/.quodlibet/lists/queries.saved``:
   Search patterns
 * ``~/.quodlibet/lists/tagpatterns.saved``:
   Patterns to tag files based on filename
 * ``~/.quodlibet/lists/renamepatterns.saved``:
   Patterns to rename files based on tags

You'll see that the format is very easy: Each saved pattern consists of two
lines, the first line contains the QL pattern, the second line its name.
The name may be identical to the pattern. The next saved "pattern -- name"
pair follows immediately on the next two lines.

Here's an example of what ``~/.quodlibet/lists/queries.saved`` might look
like::

    artist = schubert
    All by Schubert
    artist = radiohead
    All by Radiohead
    &(genre = classical, #(lastplayed > 3 days))
    &(genre = classical, #(lastplayed > 3 days))
    ~format = ogg
    All ogg files

Or an example of a ``~/.quodlibet/lists/renamepatterns.saved``::

    ~/music/<artist>/<album>/<tracknumber|<tracknumber>. ><title~version>
    Music from an album
    ~/music/misc/<artist> - <title>
    Stray song

Just edit these files or synchronize them across computers or home
directories (for different users) as needed.
