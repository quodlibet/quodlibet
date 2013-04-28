Paned Browser
=============

Overview
--------

.. image:: http://wiki.quodlibet.googlecode.com/hg/images/paned.png
    :target: http://wiki.quodlibet.googlecode.com/hg/images/paned.png
    :width: 450px
    :align: right

ThePaned Browser offers a convenient way to quickly drill down into a large 
music collection, by narrowing  selections in several stages. Some users 
mayh find this reminiscent of `RhythmBox <http://www.rhythmbox.org>`_ or, 
to some extent, `iTunes 
<http://www.apple.com/uk/itunes/what-is/player.html>`_.

In Quod Libet though, you can have as many panes as you want, grouped by 
any tags you want, for example the popular ''genre/artist/album'' and 
''artist/album'', or ''artist/album/part'', or  ''artist/album/artist'' in 
case you have a lot of multi-artist albums.

The songlist is presented at the bottom, and the panes, which run from left 
to right, are above. Clicking on an item (or items) in a pane will restrict 
it to just songs matching those (e.g those artists, or dates, genres etc). 
This will update the counts and choices on the next pane, and the filtered 
results will be updated automatically in the song list.


Pane Configuration
------------------

To change the panes, click the *Preferences* button all the way to the 
right of the search bar. There you can choose between some popular setups 
or set up custom ones using the add and remove buttons. You can change the 
order of the panes by dragging them to the desired place.

Besides normal tags, each pane also supports tied tags, tag patterns, and a 
per-entry display pattern.


Example
-------

==================================== ================================
Pattern                              Result
==================================== ================================
``~~year~album``                     2011 - This is an album title
``<~year|<~year>. <album>|<album>>`` 2011\. This is an album title
==================================== ================================

Unlike when using patterns for renaming files, songs with multiple values 
per tag will be split up in multiple entries. For a song with two 
performers, the pattern

================================================= ======================
Pattern                                           Result
================================================= ======================
``<~year|<~performers> - <~year>|<~performers>>`` Performer 1 - 2011
..
                                                  Performer 2 - 2011
================================================= ======================

Using Markup
^^^^^^^^^^^^

Also it's possible to change text emphasis using the `Pango markup language 
<http://library.gnome.org/devel/pango/unstable/PangoMarkupFormat.html>`_


=========================================================== =================================
Pattern                                                     Result
=========================================================== =================================
``<~year|\<b\>\<i\><~year>\</i\>\</b\> - <album>|<album>>`` **2011** - This is an album title
=========================================================== =================================


Aggregation
^^^^^^^^^^^

On the right side of each pane you can see the number of songs of each 
entry. This can be configured as well by adding a pattern/tag separated by 
``:`` (In case you want to use ``:`` in your pattern it has to be escaped using 
``\:``)

============================ ===========================
Pattern                      Result
============================ ===========================
``~~year~album:(<~rating>)`` 2011 - Album title     (♪♪)
============================ ===========================
