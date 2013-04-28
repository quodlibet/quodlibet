Frequently Asked Questions
==========================

Installation
------------

**Does Quod Libet require GNOME?**

    No, but we recommend you install the GNOME libraries and Python
    bindings when using Quod Libet. If they are installed, Quod Libet will
    use your default GNOME audio options.


**I'm running Gentoo, and...**

    We are not the first line of support for `Gentoo Linux
    <http://gentoo.org/>`_. If you are running Gentoo and experience
    problems, file a bug on the Gentoo bug tracking system at
    http://bugs.gentoo.org.


General
-------

**Why don't all my songs appear in the song list when I select their artist
/ album / genre or search for them?**

    Do you have a global filter in use? Check the *Browsers* tab in *Music*
    → *Preferences*.


**Why can't I double-click a song in GNOME to play in Quod Libet?**

    You can! File association is more to do with the file manager you're
    using. If you're using GNOME, right-click on the audio file in Nautilus
    and select 'Properties'. Go to the 'Open with' tab, then select the
    'Add' button. In the 'Use custom command' text field add the following:

        ``quodlibet --play-file %F``

    and then click 'add'. Now you can select 'quodlibet' from the list of
    programs to open that file. Double-click the file and Quod Libet will
    start to play it.

    Note this will *only work is Quod Libet is currently running*, though a
    workaround is to make a script that starts ``quodlibet`` first (only
    one instance is ever loaded unless in dev mode).


**My filenames with special characters (ú, ç, はあ, etc.) don't appear
properly**

    Unless told otherwise Quod Libet assumes your filesystem is using UTF-8
    filenames (this is a standard assumption for GTK+ applications). To
    tell it otherwise, ``export G_FILENAME_ENCODING="iso-8859-1"` (or
    whatever value you need) in your ``~/.bashrc`` or other appropriate
    place. You can also use the magic value `@locale` to use the default
    character encoding for your locale.


**Why do my MP3 files have the wrong length?**

    The ID3 standard defines the ``TLEN`` frame. If an MP3 has an ID3 tag
    which contains a ``TLEN`` frame, Quod Libet will use it. You can remove
    incorrect ``TLEN`` frames from your MP3 files by running:

    ::

        $ mid3v2 --delete-frames=TLEN filename.mp3


    If there are variable bit-rate (VBR) files, there may be errors in the
    frames themselves leading to an incorrectly computed length separate
    from any tags. You can fix this problem with various tools, e.g.
    `mp3val <http://mp3val.sourceforge.net/>`_:

    ::

        $ mp3val -f filename.mp3


**I want keyboard shortcuts to change browsers (or anything else)**

    Put ``gtk-can-change-accels = 1`` in ``~/.gtkrc-2.0`` (and restart Quod
    Libet). Then hover the mouse over the menu item you want to set an
    accelerator for, and press that key.

    When using GNOME this setting can be toggled in *Menus and Toolbars* in
    the GNOME settings.


**Whenever I type a space, Quod Libet pauses**

    Users of some keyboard layouts, including the popular French
    Alternative, may hit this bug. In these layouts, the spacebar sends a
    non-breaking space character, which GTK+ interprets as
    ``<control>space``. This is a `known bug in GTK
    <https://bugzilla.gnome.org/show_bug.cgi?id=541466>`__. You can work
    around it by changing your keyboard layout to send a regular space, or
    by changing the keybinding for play/pause using the method above.


Player
------

**How do I add the play count or skip count to the columns in the song list?**

    Add the ``~#playcount`` and/or ``~#skipcount`` tags to the song header
    list (in the "Others" field).


**How do I use a different soundcard with Quod Libet?**

    See the chapter on configuring the AudioBackends in the user's guide.


**Why does Quod Libet sort my songs out of order?**

    Music metadata, like music, comes in many languages, and sorting
    multi-language text is hard to do. It depends on your language as well
    as the text being sorted, and often is still not well-defined.
    `Unicode Technical Standard #10 <http://www.unicode.org/reports/tr10/>`_
    outlines an algorithm to sort multi-language text, but even then it
    needs ordinal data for each character for each language. We don't know
    of any Python implementations of it, and any implementation we use
    would have to be fast since we compare thousands of strings when sorting.


**I have two albums with the same name, and they sort out of order/get
merged in the Album List**

    Tag them with different ``labelid`` tags (it's best if you use the
    actual label catalog ID, but if you can't find it you can also just use
    any different values). You can also use ``musicbrainz_albumid`` tags,
    which several other taggers can write.


**I have two discs of the same album, and they don't get merged in the
Album List.**

    Make sure they have the same name (i.e. without "(disc x)" on the end).
    If they are still not merged, they have different `labelid` or
    ``musicbrainz_albumid`` tags. If they have different label ID tags,
    delete the incorrect one. If they have different MusicBrainz album ID
    tags, add a ``labelid`` tag that is the same for both albums.


**Can I show more than 0 to 4 notes when rating songs?**

    Close Quod Libet; in ``~/.quodlibet/config`` find the ``ratings = 4``
    line. Change it to ``ratings = however many ratings you want``. It's
    best if the value divides 100 evenly; multiples of 2 and 5 are good.
    You will need to use the ratings right-click menu to set ratings above 4.


**How can I hide incomplete albums from the Album View?**

    One way is to enter ``#(tracks > 5)`` into the search box above the
    album list - this will only show albums with greater than than 5 tracks.


**How can I list my tracks based on their ratings?**

    Right-click somewhere on the headers bar (below the search bar), select
    "Track Headers" from the menu and add "Ratings". Now if you click
    "Ratings" on the headers bar your tracks will be sorted based on their
    ratings.


**How is album art handled?**

    There are many ways users like to keep their album art, and Quod Libet
    supports graphics (primarily `.jpg` but `.gif` and `.png` also) in
    these ways:

     * Files in the *album* directory with fixed names eg ``folder.jpg``,
       ``cover.jpg``, ``front.png``
     * A file containing the ``labelid`` (eg *COCX-32760 cover.jpg*)
     * Files of certain other names linked to a
       given album in a shared directory:
       ``<musicbrainz_albumid>.ext`` or ``<artist> - <title>.ext``
     * Sub-folders of certain names (``covers/`` or ``<labelid>/``)
       with compatible images in them.
     * Embedded cover art in the file itself (incomplete support
       in some formats).

    There are fuzzy-matching algorithms to try to determine the most
    specific match if multiple of the above exist.

    If you're adding new album art, the *Album Art downloader* plugin
    allows you to do so easily and is compatible with the above.


**Why do songs disappear from my playlists?**

    This is due to the way the library works, and that playlists entries
    are based on filename. One of several things might have happened,
    before a re-scan of the library (on start-up or otherwise)

     * The songs have been renamed, moved, or their directory moved.
       Note this includes using *Rename Files* from the tag editor.
     * A removable (mounted) media device - USB disk, network share,
       internet folder or whatever is/was no longer available
       (at the time of refresh).

    Note if you're using the Auto Library Update this will happen
    immediately (There are ideas to improve this: Issue 961).


Tag Editing
-----------

**I have a lot of ID3 tags in euc-kr/cp1251/windows-1252/latin-1024/insert
favorite encoding here; can QL read them?**

    You can define a custom list of encodings to check. UTF-8 is always
    tried first, and Latin-1 is always tried last. To make your own list,
    close QL, open up ``~/.quodlibet/config``, and find the ``id3encoding``
    option. You can enter any valid encodings here, separated by spaces,
    and they will be tried in order. If you have files already imported
    into your library with incorrect tags, you'll need to reload them.

    Quod Libet saves ID3 tags in UTF-8 or UTF-16.


Other stuff
-----------

**What does the name mean?**

    *Quodlibet* or *Quod libet* is Latin for "whatever you please" or
    "whatever you want", which is the kind of attitude we want to convey
    with QL: you control how you fiddle with your music. A *quodlibet* is
    also a type of musical composition, an improvisation by several players
    or vocalists at once, which is a pretty accurate description of QL's
    development.

    *Ex falso quodlibet*, or "from a falsehood, whatever you please" is one
    of the properties of material implication (*if/then*) in classical
    logics; in standard notation it can be written as ``∀A (⊥ → A)``.

    Finally, the initial directory imported into Subversion was named `ql`,
    because I was experimenting with a syntax for a _q_uery _l_anguage.


**Where do the release names come from?**

    `Daily Dinosaur Comics <http://www.qwantz.com/>`_ at the time of the
    release.


**I like <my favorite player>, so I won't use Quod Libet!**

    Okay. We think Quod Libet beats other players in the areas where it
    counts (where exactly it does count is undecided; 'tag editing',
    'massive libraries', and 'regexp searching' have all been cited); we
    didn't like the other players. If you do, continue using them. You
    still might want to check out Ex Falso, since while there's an awful
    lot of media players out there, there are far fewer choices for tag
    editors. You could also :ref:`help us make Quod Libet better
    <Contribute>`.
