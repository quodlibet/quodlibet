.. title:: A Music Library / Editor / Player

.. image:: images/paned.png
    :align: right
    :scale: 50 %

**Quod Libet** is a `GTK+ <https://www.gtk.org/>`__-based **audio player**
written in `Python <https://www.python.org/>`__, using the `Mutagen
<https://github.com/quodlibet/mutagen>`__ tagging library. It's designed
around the idea that you know how to organize your music better than we do.
It lets you make playlists based on :ref:`regular expressions <Searching>`
(don't worry, regular searches work too). It lets you display and edit any
tags you want in the file, for all the file formats it supports.

Unlike some, Quod Libet will scale to libraries with tens of thousands of
songs. It also supports most of the :ref:`features <Features>` you'd expect
from a modern media player: Unicode support, advanced tag editing, Replay
Gain, podcasts & Internet radio, album art support and all major audio
formats - see the :ref:`screenshots <Screenshots>`.

**Ex Falso** is a program that uses the same **tag editing** back-end as
Quod Libet, but isn't connected to an audio player. If you're perfectly
happy with your favorite player and just want something that can handle
tagging, Ex Falso is for you.


.. toctree::
    :maxdepth: 1
    :titlesonly:
    :hidden:

    screenshots
    changelog
    downloads
    features
    bugs_repo

    guide/index
    packaging
    translation/index
    development/index

    license
    contact
