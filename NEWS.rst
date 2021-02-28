.. _release-4.4.0:

4.4.0 (2021-02-28) - TBC
------------------------

Packaging Changes:
 * One ``quodlibet/`` subdirectory has been removed - e.g. ``quodlibet/tests/`` -> ``tests/`` (#3238)
 * Move to Python 3.7 (#3433) :pr:`3438` (:user:`Nick Boultbee <declension>`)
 * macos: bundle.sh: clone from ../.. rather than .., fixing #3393. :pr:`3394` (:user:`smammy`)
 * win_installer: pass options to build script on env switch :pr:`3328` (:user:`gkarsay`)
 * Depend on musicbrainzngs>=0.6 (:user:`Christoph Reiter`)


General:
 * Switch to XSPF for Playlists (#1122) (#3242) (:user:`Nick Boultbee`
 * Renamed "Search Library" to "Track List" browser (:user:`CreamyCookie`)
 * Support moving library folders (scandirs) (#3506) (:user:`Nick Boultbee`)
 * Support JACK via Gstreamer (#3511) (:user:`Nick Boultbee`)
 * Make ID3 Replaygain ALL_CAPS (#3475) (:user:`Nick Boultbee`)
 * MP4: Support description tag (:user:`Nick Boultbee`)
 * Advanced prefs: use checkboxes (:user:`Nick Boultbee`)
 * Add comment to track headers (:user:`Nick Boultbee`)
 * Change None to empty string to fix TypeError in missing.py (#3548) (:user:`Ironbalden`)
 * Plugin window: don't appear on top (:user:`Nick Boultbee`)
 * Info Area: Allow space to play / pause (:user:`Nick Boultbee`)
 * Allow ctrl-[shift]-tab in Notebook windows (Edit Tags, Song Info, Prefs etc) (#3496) (:user:`Nick Boultbee`)
 * Playlists: don't clear on deletion (#3491) (:user:`Nick Boultbee`)
 * IRadio - do station updates in background (#3310) (:user:`Nick Boultbee`)
 * Improve plugin window style (#3481) (:user:`Nick Boultbee`)
 * Query: allow validation from extensions :up: (:user:`Nick Boultbee`)
 * Plugins: improve query plugins (#3485) (:user:`Nick Boultbee`)
 * Saved list editor: improve style (:user:`Nick Boultbee`)
 * Tag Editor: Add smart replacer for colon delimiters (#3456) (:user:`Nick Boultbee`)
 * Improve local cover art detection (#3454) (#3459) (:user:`Nick Boultbee`)
 * Add support for TKEY 'Initial Key' column (#3420) (:user:`Cole Robinson`)
 * add ability to sort by date added to Album List Browser (#3410) (:user:`Uriel Zajaczkovski`)
 * Add originalartistsort (:user:`Nick Boultbee`)
 * add check to Missing.py, fix #3336 (#3382) (:user:`Ironbalden`)
 * Add support for ~elapsed and ~#elapsed (#3379) (:user:`Nick Boultbee`)
 * Format date panes (#3346) (#3349) (:user:`Nick Boultbee`)
 * Update song order in song list when modified (#2509) (:user:`Thomas Leberbauer`)
 * Restyle the search query :pr:`3517` (:user:`Nick Boultbee <declension>`)
 * Fix non-splitter EditTags plugins (#3468) :pr:`3470` (:user:`Nick Boultbee <declension>`)
 * Support feedparser 6.0 :pr:`3464` (:user:`Christoph Reiter <lazka>`)
 * formats: Don't return lyrics with embedded nulls :pr:`3402` (:user:`Christoph Reiter <lazka>`)
 * Fix setting pane mode :pr:`3365` (:user:`michaelkuhn`)
 * windows: Fix playing files on network shares (#3361) :pr:`3371` (:user:`d10n`)
 * Restarting :pr:`3211` (:user:`blimmo`)
 * Closes #946: Rename cover filename option :pr:`3235` (:user:`CreamyCookie`)
 * Closes #1769: Allow multiple entries for cover files :pr:`3236` (:user:`CreamyCookie`)

Plugins:
 * Add listenbrainz scrobbling plugin. (#3528) (:user:`Ian Campbell`)
 * First version of Musicbrainz Sync plugin that sends ratings (#3180) (:user:`LoveIsGrief`)
 * add plugin 'synchronize to device' (#2636) (:user:`Jan`)
 * Fix weighted shuffle not shuffling when total rating is zero. :pr:`3397` (:user:`blimmo`)
 * ext/inhibit: Add option to inhibit suspend :pr:`3309` (:user:`antigone-xyz`)
 * trayicon: only check for org.kde.StatusNotifierWatcher for the appindicator :pr:`3313` (:user:`Christoph Reiter <lazka>`)
 * MQTT authentication :pr:`3391` (:user:`Jeroen7V`)
 * Add "Rate" to D-Bus API :pr:`3455` (:user:`LoveIsGrief`)
 * Prettier sync lyrics (:user:`Nick Boultbee`)
 * Synchronizedlyrics: Rewrite lyrics parsing, supporting >60min songs (:user:`Nick Boultbee`)
 * Add Sonos playlist export plugin (#3487) (:user:`Nick Boultbee`)
 * Plugin: fix Cover Art window persistence (:user:`Nick Boultbee`)
 * Skip songs: rename & naming / text updates (:user:`Nick Boultbee`)
 * Cover Art Downloader: remove failing downloads from results (:user:`Nick Boultbee`)
 * Cover Art: Improve Musicbrainz downloader (:user:`Nick Boultbee`)
 * Cover Art download: only trigger plugin if `album` tag available (:user:`Nick Boultbee`)
 * Added AutoUpdateTagsInFiles plugin (#3200) (:user:`Joschua Gandert`)

Translations:
 * Update Polish translation :pr:`3323`
 * Update italian translation :pr:`3405` (:user:`dprimon`)
 * Updated Dutch translation :pr:`3441` (:user:`Vistaus`)
 * Update British English translation (#3483) (:user:`Nick Boultbee`)

Documentation:
 * Update plugin development page (:user:`Nick Boultbee`)
 * Update plugins.rst to include locations on MacOS. (#3562) (:user:`BraveSentry`)
 * Fixed documentation URLs :pr:`3425` (:user:`TehPsychedelic`)
 * Fix link to contributing guide :pr:`3416` (:user:`remvee`)
 * Various docs updates / improvements (:user:`Nick Boultbee`)
 * Docs: Improve / tidy renaming files examples (:user:`Nick Boultbee`)
 * docs: fix the windows dev environ instructions (:user:`Christoph Reiter`)

Developer:
 * Various Python 2 leftovers and updates :pr:`3440` (:user:`Nick Boultbee <declension>`)
 * poetry: update deps :pr:`3546` (:user:`Christoph Reiter <lazka>`)
 * tests/operon: make argument names meaningful :pr:`3294` (:user:`jtojnar`)
 * gettextutil: warn on gettext warnings instead of erroring out :pr:`3545` (:user:`Christoph Reiter <lazka>`)
 * CI: re-enable flatpak tests :pr:`3501` (:user:`Christoph Reiter <lazka>`)
 * CI: install MSYS2 packages via the GHA :pr:`3458` (:user:`Christoph Reiter <lazka>`)
 * Tests: improve source scanning (:user:`Nick Boultbee`)
 * Refactor: tidy Gstreamer player code (#3489) (:user:`Nick Boultbee`)
 * Add .editorconfig that agrees with PEP-008 and our Flake8 config (:user:`Nick Boultbee`)
 * Refactor ID3 tag writing for readability (#3476) (:user:`Nick Boultbee`)
 * More type hints (:user:`Christoph Reiter`)
 * CI: Port more things to github actions (:user:`Christoph Reiter`)
 * Switch from pycodestyle/pyflakes to flake8 (:user:`Christoph Reiter`)
 * Move the main sources into the repo root (:user:`Christoph Reiter`)
 * Remove pipenv support (:user:`Christoph Reiter`)


.. _release-4.3.0:

4.3.0 (2020-02-22) - Smaug-like figures, lurking on our planet filled with hoarded data
---------------------------------------------------------------------------------------

Packaging Changes:
  * Various installed files have been renamed
    ("exfalso" -> "io.github.quodlibet.ExFalso") to work better with Flatpak
  * zsh completion file installation location changed to site-functions :pr:`3300`
  * Installs a new bash completion file :pr:`3126` :pr:`3128`
  * Windows: Moved everything from 32 bit to 64 bit. This means QL will no longer work with 32 bit Windows.

Translations:
  * Update brazilian portuguese translations :pr:`3123` (:user:`Hugo Gualandi <hugomg>`)
  * Bulgarian translation fixes :pr`3147` (:user:`cybercop-montana`)
  * Update Hebrew translation :pr:`3164` :pr:`3274` (:user:`Avi Markovitz <avma>`)
  * French translation update :pr:`3183` (:user:`Bundy01`)
  * Update German translation (:user:`Till Berger <Mellthas>`)
  * Various translation related spelling/formatting/text improvements :pr:`3208` :pr:`3207` :pr:`3206` :pr:`3214` :pr:`3215` :pr:`3218` :pr:`3219` (:user:`Till Berger <Mellthas>`)
  * New Serbian translation :pr:`3245` (:user:`leipero`)
  * Update Finnish translation :pr:`3199` (:user:`Kristian Laakkonen <krisse7>`)

General:
  * Simplify launcher for macOS :pr:`3101` (:user:`a-vrma`)
  * Add original date sort option to album browser :pr:`3103` (:user:`Ruud van Asseldonk <ruuda>`)
  * Option for multiple queries in Search Browser :pr:`3082` (:user:`blimmo`)
  * Improved `VGM` Metadata Tag Parsing (GD3 Support) :pr:`3100` (:user:`Eoin O'Neill <Eoin-ONeill-Yokai>`)
  * cover: Always scale down to parent window size :pr:`3114` (:user:`Fredrik Strupe <frestr>`)
  * tags: Support loading lyrics from 'unsyncedlyrics' tag :bug:`3115` (:user:`Fredrik Strupe <frestr>`)
  * browsers: Focus album list on album filtering :bug:`3122` (:user:`Fredrik Strupe <frestr>`)
  * Add bash completion :pr:`3126` :pr:`3128` (:user:`Arnaud Rebillout <elboulangero>`)
  * Docs fixes :pr:`3133` :pr:`3192` (:user:`Petko Ditchev <petko10>`, :user:`CreamyCookie`)
  * player: Make external volume cubic by default :pr:`3151` (:user:`Fredrik Strupe <frestr>`)
  * desktop: Accept all selected files when opened from file browser :bug:`3159` (:user:`Fredrik Strupe <frestr>`)
  * Tracks without track number are now sorted before first track :pr:`3196` (:user:`CreamyCookie`)
  * Add option for ignoring characters in queries :pr:`3221` (:user:`blimmo`)
  * Disable the file trash support under flatpak for now :bug:`3093`
  * zsh completion improvements :pr:`3300` (:user:`Matthew Martin <phy1729>`)
  * Add poetry support :pr:`3306` (:user:`Nick Boultbee <declension>`)

Plugins:
  * Import metadata plugin: Fix file renaming :bug:`3071` (:user:`Fredrik Strupe <frestr>`)
  * Scale player volume properly in mpris2 API :pr:`3098` (:user:`luk1337`)
  * mpris: Drop MPRIS1 support :pr:`3102`
  * Add new Banshee import plugin :pr:`3141` (:user:`Phidica`)
  * Library update plugin: Update on file modifications :bug:`3168` (:user:`Fredrik Strupe <frestr>`)
  * Add "Record Stream" to default custom commands plugin :bug:`1617` (:user:`CreamyCookie`)
  * Custom Commands: Don't modify command when using parameters :bug:`3185` :pr:`3232` (:user:`CreamyCookie`)
  * Import/export plugin: accept full filenames when renaming :pr:`3282` (:user:`Fredrik Strupe <frestr>`)
  * acoustid: fix queries always returning "unknown" :bug:`3269`
  * Fix embed images plugin submenu not showing sometimes :pr`3303` (:user:`Nick Boultbee <declension>`)


.. _release-4.2.1:

4.2.1 (2018-12-26) - DO NOT WEAR THE HAT UNDER ANY CIRCUMSTANCES
----------------------------------------------------------------

Translations:
  * Hebrew translation update :bug:`3027` (:user:`Avi Markovitz <avma>`)
  * German translation update :pr:`3036` (:user:`Till Berger <Mellthas>`)

Fixes:
  * Fix freezes when opening the shortcuts window with i3wm
    :bug:`3055` (:user:`Fredrik Strupe <frestr>`)
  * xinebe: Fix error when pausing a non-local stream :bug:`3057`
  * Fix mmkeys error (preventing QL to start) when mate-settings-daemon is
    running outside of a mate session :bug:`3056`
  * Fix some panels/docks not being able to match the app with the desktop
    file :bug:`3029`
  * Migrate metadata plugin fixes
    :bug:`3070` (:user:`Fredrik Strupe <frestr>`)


.. _release-4.2.0:

4.2.0 (2018-10-31) - staffed by the living
------------------------------------------

Packaging Changes:
  * **gettext 0.19.8** required (was 0.15)
  * **intltool** no longer required

Translations:
  * Finnish translation update
    :pr:`2894` (:user:`Kristian Laakkonen <krisse7>`)
  * Russian translation update :pr:`2965` (:user:`Arkadiy Illarionov <qarkai>`)
  * Danish translation update :pr:`2983` (:user:`scootergrisen`)
  * Polish translation update :pr:`3015` (:user:`Piotr Drąg <piotrdrag>`)

Codebase:
  * Port lots of dbus related code from python-dbus to GDBus
    :pr:`2876` :pr:`2879` :pr:`2885` :pr:`2887` :pr:`2886` :pr:`2901`
    :pr:`2903` :pr:`2904` :pr:`2905` :pr:`2917` :pr:`2918` :pr:`2925`
    (:user:`Arkadiy Illarionov <qarkai>`)
  * Ported from intltool to gettext
  * CI: moved from appveyor to azure-pipelines for Windows testing
  * CI: Add junit test reporting :pr:`2960`
    (:user:`Nick Boultbee <declension>`)
  * Various test suite fixes for NixOS :bug:`2820`
    (:user:`Jan Tojnar <jtojnar>`)
  * Removed most Python 2 compatibility code :pr:`2957`
  * Add a Pipefile for pipenv :pr:`2977`
  * Various minor Python 3.7 compatibility fixes

General:
  * queue: Add option to keep songs after playing them
    :pr:`2865` (:user:`Fredrik Strupe <frestr>`)
  * queue: Add option to not play songs from the queue
    :pr:`2865` (:user:`Fredrik Strupe <frestr>`)
  * Fix non-deterministic ordering of album list and cover grid browsers
    :pr:`2945` (:user:`dpitch40`)
  * multimedia keys: add support for forward/rewind/repeat/shuffle keys
    :pr:`2954` (:user:`Druette Ludovic <LudoBike>`)
  * tag editor: Fix a context menu crash
    :pr:`2968` (:user:`Eoin O'Neill <TheYokai>`)
  * Remove GNOME app menu :bug:`2846`
  * cli: ``--add-location`` for adding a file/directory to the library
    :pr:`2970` (:user:`Fredrik Strupe <frestr>`)
  * cli: Remove deprecated ``--song-list`` option
    (:user:`Fredrik Strupe <frestr>`)
  * Update the big cover window on song changes
    :pr:`2972` (:user:`Eoin O'Neill <TheYokai>`)
  * wayland: Fix the application window icon under Plasma :bug:`2974`
  * Various man page updates for missing commands etc
    :pr:`2971` (:user:`Fredrik Strupe <frestr>`)
  * Add support for importing m3u8 playlists (:user:`Fredrik Strupe <frestr>`)
  * tags: Don't show generic Performance role description for ~performer:roles
    :pr:`2994` (:user:`zsau`)
  * themes: Work around redraw issues with the Breeze gtk theme :bug:`2997`
  * tag editor: Remember filelist scroll position on tag save
    :pr:`3005` (:user:`Olli Helin <ohel>`)
  * Windows: use SetDllDirectoryW to prevent loading clashing DLLs not
    shipped by us :bug:`2817`
  * cover display: Fix the cover window size on multi monitor systems
    :pr:`2915` (:user:`Fredrik Strupe <frestr>`)
  * session: Add an XSMP session management backend to improve (but not fix)
    save on shutdown behavior under XFCE :bug:`2897`
  * monkeysaudio: handle missing bits_per_sample for older format versions
    :bug:`2882`
  * Various other fixes and improvements:
    :pr:`2998` (:user:`Olli Helin <ohel>`), :pr:`2909` (:user:`zsau`)

Plugins:
  * waveformseekbar: Mouse scroll seeking
    :pr:`2930` (:user:`Peter Strulo <blimmo>`)
  * waveformseekbar: Add option to hide time labels
    :pr:`2929` (:user:`CreamyCookie`)
  * waveformseekbar: Fix freezes while playing streams
    :pr:`2987` (:user:`Olli Helin <ohel>`)
  * animocd: Add more preset positions
    :pr:`2937` (:user:`Fredrik Strupe <frestr>`)
  * New query plugin to match missing tags
    :pr:`2936` (:user:`Peter Strulo <blimmo>`)
  * pitch: Add spin buttons for finer control
    :pr:`2950` (:user:`Druette Ludovic <LudoBike>`)
  * wikipedia: Unify Wikipedia plugins
    :pr:`2953` (:user:`Fredrik Strupe <frestr>`)
  * equalizer: Add option to save custom presets
    :pr:`2995` (:user:`Olli Helin <ohel>`)
  * mediaserver: Point out required rygel config adjustment in the plugin
    settings :pr:`3004` (:user:`Fredrik Strupe <frestr>`)
  * custom commands: Fix menu order
    :bug:`2659` (:user:`Fredrik Strupe <frestr>`)
  * random album: Make it Python 3 compatible
    :pr:`2922` (:user:`Stephan Helma <sphh>`)


.. _release-4.1.0:

4.1.0 (2018-06-03) - Trapped in a holodeck that won't take commands
-------------------------------------------------------------------

Packaging Changes:
  * No dependency changes compared to 4.0
  * Various installed files have been renamed
    ("quodlibet" -> "io.github.quodlibet.QuodLibet") to work better with
    Flatpak
  * We've added some new icon resolutions

Translations:
  * Update Norwegian (bokmål) translation :pr:`2833`
    (:user:`Åka Sikrom <akrosikam>`)
  * Update German translation :pr:`2860` (:user:`Till Berger <Mellthas>`)
  * Update Polish translation :pr:`2857` (:user:`Piotr Drąg <piotrdrag>`)
  * Some Russian translation improvements :pr:`2670`
    (:user:`Kirill Romanov <Djaler>`)

* Various improvements and fixes to make Quod Libet ready for Flatpak/Flathub
  :pr:`2842` :pr:`2851` (:user:`Felix Krull <fkrull>`)
* Show confirmation dialog when removing songs from playlists :pr:`2667`
  (:user:`zsau`)
* Map bare performer tags to a "Performance" role in ``~people:roles``
  :pr:`2674` (:user:`zsau`)
* Add wildcard support to albumart filename preferences :pr:`2814`
  (:user:`zsau`)
* Fix various typos :pr:`2786` (:user:`luzpaz`) :pr:`2750`
  (:user:`Tom McCleery <rakuna>`)
* waveformseekbar: Improve hover time indication :pr:`2690` (:user:`Eyenseo`)
* Add shuffle-by-grouping plugin :pr:`2788` (:user:`archy3`)
* Album List - sorting by album average playcount :pr:`2794`
  (:user:`Uriel Zajaczkovski <urielz>`)
* Recognize rating/playcount tags in vorbis comments :pr:`2761`
  (:user:`Thomas Leberbauer <slosd>`)
* Handle error when writing empty replaygain tag :pr:`2838`
  (:user:`Thomas Leberbauer <slosd>`)
* waveformseekbar: Clamp seek time to valid range :pr:`2729`
  (:user:`Peter Simonyi <psimonyi>`)
* tag editor: don't use inline separators when changing multiple tag values
  :pr:`2684` (:user:`Peter F. Patel-Schneider <pfps>`)
* Improve the lyrics file search :pr:`2567`
  (:user:`Pete Beardmore <elbeardmorez>`)
* Added advanded_preferences config for scrollbar visibility :pr:`2697`
  (:user:`Meriipu`)
* cli: Allow floating point arguments for volume :pr:`2661`
  (:user:`Jonas Platte <jplatte>`)
* code quality: Fix raising NotImplementedError :pr:`2772`
  (:user:`Jakub Wilk <jwilk>`)
* paned browser: Add shortcut Ctrl-Return to the searchbar :pr:`2745`
  (:user:`Felician Nemeth <nemethf>`)
* Fix translations on systems with translations spread across multiple
  directories like with NixOS/Flatpak. :bug:`2819`
* Fix setting the process name on Linux to "quodlibet" (4.0 regression)
  :bug:`2826`
* Fix a case where a deadlocked QL would prevent new instances from being
  started :bug:`2754`
* Directory browser: fix not showing Gnome bookmarks
* Various Python 3.7 compatibility fixes
* id3: always ignore TLEN frames :bug:`2758`
* wayland: fix errors when showing the seek popup widget :bug:`2644`
* Add cli options for setting repeat and shuffle type :pr:`2799`
  (:user:`Fredrik Strupe <frestr>`)
* Queue stop once empty: do check at end of song instead :pr:`2801`
  (:user:`Fredrik Strupe <frestr>`)
* searchbar: Don't save indeterminate search queries in the history :pr:`2871`
  (:user:`Fredrik Strupe <frestr>`)
* browsers/playlist: Make the side pane take up less space :bug:`2765`
  (:user:`Fredrik Strupe <frestr>`)
* Make songs menu key accels work across all browsers :bug:`2863`
  (:user:`Fredrik Strupe <frestr>`)
* shuffle: fix shuffle no longer working after one complete run :bug:`2864`
  (:user:`Fredrik Strupe <frestr>`)
* tag editor: Allow saving tag if present in all songs but value differ
  :bug:`2686` (:user:`Fredrik Strupe <frestr>`)
* iradio: assume http if no protocol specified :bug:`2731`
  (:user:`Nick Boultbee <declension>`)
* tag split: Allow non-word characters around tag separators :bug:`1088`
  :bug:`2678` (:user:`Nick Boultbee <declension>`)
* Various improvements to the cover source plugin system
  (:user:`Nick Boultbee <declension>`)
* gstreamer: Disable gapless for .mod files :bug:`2780`
* gstreamer: Store the GStreamer registry/cache in our own cache directory
  to avoid conflicts with the system cache :bug:`2839`
* macOS: Fix cannot re-order playlist songs with DnD :pr:`2867`
  (:user:`David Morris <othalan>`)

Plugins:
  * Add a new cover download plugin using the cover sources :pr:`2812`
    (:user:`Nick Boultbee <declension>`)
  * headphonemon: fix headphone detection (4.0 regression) :bug:`2868`
  * plugin search: handle search for multiple words better
  * importexport: pass a default value for ~#track when sorting. :bug:`2694`
  * equalizer: Fix scales in the preferences not showing the initial values
    :bug:`2722`
  * randomalbum: Various Python3 fixes :bug:`2721` :bug:`2726`
  * trayicon: hide the (useless) scrolling preferences on Windows. :bug:`2718`
  * Move the app/system/dependency info from the about dialog into a plugin.
  * Tap BPM plugin: Handle non-numeric BPMs :bug:`2824`
    (:user:`Fredrik Strupe <frestr>`)
  * plugins: Make random album work on non-album browsers again :pr:`2844`
    (:user:`Fredrik Strupe <frestr>`)
  * alarm plugin: Port to Python 3 :bug:`2735`
    (:user:`Nick Boultbee <declension>`)
  * Website search: support ~filename :bug:`2762`
    (:user:`Nick Boultbee <declension>`)
  * Move Browse Files to core (fully) :bug:`2835` :bug:`1859`
    (:user:`Nick Boultbee <declension>`)
  * qlscrobble: Fix a potential error when upgrading from 3.9 and older
    :bug:`2768`

Windows:
  * Fix sys.argv not being set by exe launchers (4.0 regression) :bug:`2781`
  * The portable app now uses a local cache directory instead of the system one
    in more cases.
  * Always show the scrollbars like we do on macOS :bug:`2717`


.. _release-4.0.2:

4.0.2 (2018-01-17) - So it goes!
--------------------------------

Bug fixes:  :bug:`2723` :bug:`2721` :bug:`2722` :bug:`2726` :bug:`2717`
:bug:`2694`


.. _release-4.0.1:

4.0.1 (2018-01-13) - Water as far as the eye can see!
-----------------------------------------------------

Translation updates by :user:`Kirill Romanov <Djaler>` and :user:`Honza Hejzl
<welblaud>`

Bug fixes: :bug:`2677` :bug:`2672` :bug:`2671` :bug:`2680` :bug:`2687`
:bug:`2669` :bug:`2699` :bug:`2698` :bug:`2704` :bug:`2703` :bug:`2683`
:pr:`2706` :bug:`2705` :bug:`2710` :bug:`2718` :bug:`2719` :bug:`2713`
:bug:`2668` :pr:`2715` (:user:`CreamyCookie`, :user:`Nick Boultbee
<declension>`, …)


.. _release-4.0.0:

4.0.0 (2017-12-26) - Speculative fiction where everything's the same, except for one chilling difference
--------------------------------------------------------------------------------------------------------

Packaging Changes:
  * **Python 3.5** required (was 2.7)

    * All Python dependencies need to be switched to their Python 3 variants.
      In case there is a "py" in the package name it likely needs to be
      changed.

  * **Mutagen 1.34** required (was 1.32)
  * **GTK+ 3.18** required (was 3.14)
  * **PyGObject 3.18** required (was 3.14)
  * **GStreamer 1.8** required (was 1.4)
  * **media-player-info** no longer required
  * **udisks2** no longer required
  * **python-futures** no longer required
  * **python-faulthandler** no longer required

Project:
  * Ported from Python 2 to Python 3 :bug:`1580` :bug:`2467`
  * Relicensed all code under "GPLv2 only" to "GPLv2 or later" :bug:`2276`

Translations:
  * Update German translation :pr:`2651` (:user:`Till Berger <Mellthas>`)
  * Update Polish translation :pr:`2646` (:user:`Piotr Drąg <piotrdrag>`)
  * Update Norwegian (bokmål) translation :pr:`2506` :pr:`2621`
    (:user:`Åka Sikrom <akrosikam>`)
  * Russian translation fixes :pr:`2608` :user:`Kirill Romanov <Djaler>`
  * Update Finnish translation :pr:`2606` :user:`Kristian Laakkonen <krisse7>`

Various:
  * Allow cover image pop-up to scale up to maximum size :pr:`2634`
    (:user:`Peter F. Patel-Schneider <pfps>`)
  * Draw a drag handle for the pane separator with newer GTK+ :pr:`2402`
  * Soundcloud: Add "my tracks" category (:user:`Nick Boultbee <declension>`)
  * Workaround Ubuntu theme bug which results in drawing artefacts with
    treeview separators. :bug:`2541`
  * Added support for custom date column timestamp formats (advanced prefs)
    :pr:`2366` (:user:`Meriipu`)
  * Fix filter function (e.g. max, min) doesn't work correctly with lastplayed
    :pr:`2504` (:user:`Thomas Leberbauer <slosd>`)
  * Multimeida keys: make "previous" always go to the previous song
    :bug:`2494`
  * Prefer userdir in XDG_CONFIG_HOME :bug:`138` :pr:`2466`
    (:user:`Sauyon Lee <sauyon>`)
  * Fix error on start under LXDE with its "org.gnome.SessionManager"
    re-implementation
  * Improve visibility of the active state of toggle buttons in the
    bottom bar :bug:`2430`
  * Remove device support :bug:`2415`
  * Filesystem browser: Allow selecting multiple folders :bug:`2399`
    (:user:`Nick Boultbee <declension>`)
  * CLI: Allow floating point arguments for ``--volume`` :pr:`2661`
    (:user:`Jonas Platte <jplatte>`)
  * Windows: SIGINT handling support
  * Sentry.io error reporting now available on all platforms

Playback:
  * GStreamer: Fix gain adjustments are not applied during the first split
    second of a song on macOS/Windows. :bug:`1905`
  * GStreamer: Seeking performance improvements :bug:`2420`

Tagging:
  * Add option for moving album art when renaming :pr:`2560`
    (:user:`Pete Beardmore <elbeardmorez>`)
  * Add DSF tagging support :bug:`2491`

Plugins:
  * Add support for sidebar plugins :bug:`152`
    (:user:`Nick Boultbee <declension>`)
  * LyricsWindow: convert to a sidebar plugin :bug:`2553`
    (:user:`Nick Boultbee <declension>`)
  * Fix synchronized lyrics window not showing :bug:`1743` :pr:`2492`
    (:user:`elfalem`)
  * Add more preferences for the album cover search :pr:`2511`
    (:user:`Pete Beardmore <elbeardmorez>`)
  * Waveform seekbar hoover time indication :bug:`2419` :pr:`2550`
    (:user:`Muges`)
  * New automatic seekpoint plugin (seeking based on bookmarks)
    :pr:`2437` (:user:`Meriipu`:)

CI:
  * Run Windows tests on appveyor :pr:`2619`
  * Submit coverage reports to codecov.io
  * Move to circleci for Docker tests :pr:`2443`
  * Dockerize Windows-under-Wine tests :pr:`2444`

Various improvements, fixes and Python 3 porting fixes, thanks to:
  * :user:`Kristian Laakkonen <krisse7>`: :pr:`2607` :pr:`2605` :pr:`2593`
    :pr:`2586` :pr:`2578` :pr:`2576` :pr:`2521`
  * :user:`Emanuele Baldino <Ironbalden>`: :pr:`2622`
  * :user:`CreamyCookie`: :pr:`2574`
  * :user:`Muges`: :bug:`2425`
  * :user:`Till Berger <Mellthas>`: :pr:`2531` :pr:`2530` :pr:`2474`
  * :user:`Meriipu`: :pr:`2486` :pr:`2449` :pr:`2616`
  * :user:`Fredrik Strupe <frestr>`: :pr:`2476`


.. _release-3.9.1:

3.9.1 (2017-06-06) - CHECK AND MATE, FAILING BODY AND MIND
----------------------------------------------------------

  * Danish translation update :pr:`2394` (:user:`scootergrisen`)
  * Various bug fixes: :bug:`2409` :bug:`2364` :bug:`2406` :bug:`2401`
    :bug:`2410` :bug:`2414` :bug:`2387` :bug:`2411` :bug:`2386` :bug:`2400`
    :bug:`2404` (:user:`Nick Boultbee <declension>` et al.)


.. _release-3.9.0:

3.9.0 (2017-05-24) - If you can whistle, you can do this too
------------------------------------------------------------

Packaging Changes:
  * **python-zeitgeist** no longer used
  * **python-feedparser** required (no longer optional)
  * **python-faulthandler** required
  * **GTK+ 3.14** required (was 3.10)
  * **PyGObject 3.14** required (was 3.12)
  * **GStreamer 1.4** required (was 1.2)
  * No longer installs icons to "/usr/share/pixmaps"
  * Installs more icons into "/usr/share/icons/hicolor/" theme

Translation Updates:
  * Czech :pr:`2175` (:user:`Marek Suchánek <mrksu>`)
  * Danish :pr:`2185` (:user:`scootergrisen`)
  * French :pr:`2206` (:user:`Olivier Humbert <trebmuh>`)
  * Czech :bug:`2209` (:user:`Honza Hejzl <welblaud>`)
  * Norwegian Bokmål :pr:`2232` :pr:`2354` (:user:`Åka Sikrom <akrosikam>`)
  * French :pr:`2240` (:user:`Jean-Michel Pouré <ffries>`)
  * German :pr:`2388` (:user:`Till Berger <Mellthas>`)
  * Polish :pr:`2391` (:user:`Piotr Drąg <piotrdrag>`)

General:
  * Windows: Use native file choosers :pr:`2324`
  * operon: add "--all" option for the "tags" command. :bug:`2335`
  * Queue: Add checkbox to stop after queue is empty :pr:`2340`
    (:user:`Fredrik Strupe <frestr>`)
  * Opt-in online crash reporting using sentry.io :pr:`2313`
  * Allow resizing of panes in PanedBrowser :pr:`2301`
    (:user:`Fredrik Strupe <frestr>`)
  * Plugins: Add UI for plugin type filtering :pr:`2218`
    (:user:`Nick Boultbee <declension>`)
  * Add accelerators for "Open Browser" Menu :pr:`2305`
    (:user:`Uriel Zajaczkovski <urielz>`)
  * replaygain: save selected replaygain profiles to config :pr:`2279`
    (:user:`Didier Villevalois <ptitjes>`)
  * Allow ``!=`` in queries :bug:`2056` (:user:`Nick Boultbee <declension>`)
  * Add ``~#channels`` :bug:`1686`
  * songlist: make "space" trigger play/pause. See :bug:`1288`
  * Add ``--start-hidden`` and remove visibility restoring from the tray icon
    :bug:`814`
  * Add non-python crash reporting on the next start :bug:`1853`
  * mp3: include lame preset in ``~encoding``

Fixes:
  * Fix queue height not getting restored in some cases :pr:`2330`
    (:user:`Fredrik Strupe <frestr>`)
  * macOS: Fix URL launching from labels :bug:`2306`
  * Windows: Fix crash when the 65001 code page is used :bug:`2333`
  * Windows: Fix crash with French locale in some cases. :bug:`2364`
  * MPRIS: Fix metadata changes not getting emitted :pr:`2359`
    (:user:`IBBoard`)
  * Tray icon: Fix rating menu :pr:`2355` (:user:`IBBoard`)
  * Player: Fix "previous" not working with radio streams :bug:`2198`
  * gstbe: increase default buffer duration. :bug:`2191`
  * macOS: Fix meta key for accelerators not working :bug:`2271`
  * Fix error in case stdout gets closed before QL :bug:`2205`
  * Fix icon size of app menu embedded in gnome-shell decoration :bug:`2320`
    :pr:`2334` (:user:`Vimalan Reddy <redvimo>`)

Plugins:
  * Windows: Enable crossfeed plugin
  * Add a plugin to export a playlist to a folder :pr:`2307`
    (:user:`Didier Villevalois <ptitjes>`)
  * Add skip by rating plugin :pr:`2201` (:user:`Jason Heard <101100>`)
  * Advanced Prefs: add a configuration for the window title pattern :pr:`2272`
    (:user:`Didier Villevalois <ptitjes>`)
  * waveformseekbar: add hidpi detection :pr:`2261`
    (:user:`Didier Villevalois <ptitjes>`)
  * waveformseekbar: smoother drawing updates :pr:`2289`
    (:user:`Didier Villevalois <ptitjes>`)
  * Add a tap bpm plugin :pr:`2264` (:user:`Didier Villevalois <ptitjes>`)
  * Add plugin for changing the user interface language :pr:`2154`
  * Add external visualisations plugin :bug:`737`
    (:user:`Nick Boultbee <declension>`)
  * EQ Plugin: various improvements :bug:`1913`
    (:user:`Nick Boultbee <declension>`)
  * Add a plugin to toggle the menubar's visibility using "alt" :pr:`2263`
    :pr:`2267` (:user:`Didier Villevalois <ptitjes>`)

Further Contributions:
  :pr:`2282` (:user:`David Pérez Carmona <DavidPerezIngeniero>`) :pr:`2284`
  (:user:`Jakub Wilk <jwilk>`) :pr:`2294` :pr:`2326` (:user:`Fredrik Strupe
  <frestr>`), :pr:`2270` :pr:`2302` :pr:`2280` :pr:`2385` (:user:`Didier
  Villevalois <ptitjes>`) :pr:`2308` :pr:`2314` (:user:`Uriel Zajaczkovski
  <urielz>`) :pr:`2331` (:user:`CreamyCookie`)

Development:
  * tests: use xvfbwrapper if available :pr:`2287`
  * gdist: relicense to modern style MIT
  * Use docker on travis-ci :pr:`2269` :pr:`2290`


.. _release-3.8.1:

3.8.1 (2017-01-23) - LET'S TALK ABOUT BIRDS
-------------------------------------------

* GStreamer: increase default buffer duration. :bug:`2191`
* Fix acoustid plugin :bug:`2192`
* Fix new playlists from menu :bug:`2183` (:user:`Nick Boultbee <declension>`)
* mpdserver: Make it work with the M.A.L.P Android client :bug:`2179`
* Waveform plugin fixes :bug:`2195` (:user:`Nick Boultbee <declension>`)
* Covergrid context menu fixes :pr:`2197` (:user:`Joel Ong <darthoctopus>`)

Translations:
  * Norwegian Bokmål :pr:`2194` (:user:`Åka Sikrom <akrosikam>`)
  * German :pr:`2188` (:user:`Till Berger <Mellthas>`)


.. _release-3.8.0:

3.8.0 (2016-12-29) - Maybe it'll land somewhere cool eventually
---------------------------------------------------------------

Packaging Changes:
  * `concurrent.futures <https://pypi.org/project/futures/>`__ required
    (usually called python-futures, python-concurrent.futures or
    python2-futures in distros)
  * **libgpod4** is no longer used
  * Testing now requires py.test
  * Installs a new zsh completion file

General:
  * Preferences: Add option for changing the duration display format
    :pr:`2021` :bug:`1727` :bug:`1967` (:user:`Nick Boultbee <declension>`)
  * Locale-dependent number formatting :bug:`2018`
    (:user:`Nick Boultbee <declension>`)
  * Fix updates across browsers on changes to ~playlists :bug:`2017`
    (:user:`Nick Boultbee <declension>`)
  * Don't wake up when idle :pr:`2068` :bug:`2067`
  * Covergrid Browser :bug:`241` :pr:`2071` :pr:`2115` :pr:`2125` :bug:`2110`
    :pr:`2130` (:user:`brunob`, :user:`Joel Ong <darthoctopus>`, :user:`qwhex`)
  * Play order (shuffle / repeat) rewrite to be more modularised / powerful
    :pr:`2043` :bug:`2059` :bug:`2121` :bug:`2123` :pr:`2125`
    (:user:`Nick Boultbee <declension>`)
  * Improvements / additions to Information window :pr:`2119` :bug:`1558`
    (:user:`Nick Boultbee <declension>`)
  * Search: Fix error when query divides by 0 :pr:`2025` (:user:`faubi`)
  * Fix crash on tag edit abort :bug:`2081`
  * Library scan: ignore hidden files :bug:`2074`
  * Remove iPod support
  * Log the filename in case something crashes :bug:`2143`
  * MP4: Handle empty trkn/disk :bug:`2143`
  * Library: support autofs mounts :bug:`2146`
  * Various small GTK+/Ubuntu theme related updates
  * Fix crash when parsing feeds :pr:`2144`
    (:user:`Peter Schwede <pschwede>`)
  * Song list: ctrl+drag will now force a song copy :bug:`1952`
  * MP4: round bpm to nearest int. :bug:`2028`
    (:user:`Nick Boultbee <declension>`)
  * Songsmenu icons improved (:user:`Nick Boultbee <declension>`)
  * Basic zsh completion

Translation Updates:
  * Polish :pr:`2141` (:user:`Piotr Drąg <piotrdrag>`)
  * Norwegian Bokmål :pr:`2031` :pr:`2064` (:user:`Åka Sikrom <akrosikam>`)
  * Danish :pr:`2169` (:user:`scootergrisen`)
  * Czech :pr:`2173` (:user:`Marek Suchánek <mrksu>`)

Plugins:
  * Discogs Cover Source :pr:`2136` (:user:`qwhex`)
  * Add register-date filter to lastfmsync plugin :pr:`2127`
    (:user:`qwhex`)
  * Wikipedia plugin - search instead of direct URL :pr:`2112` (:user:`urielz`)
  * Notification plugin: add option to mask 'Next' :bug:`2026` :pr:`2045`
    (:user:`Corentin Néau <weyfonk>`)
  * Waveform seek bar :pr:`2046` (:user:`0x1777`),
    related performance improvements (:user:`Nick Boultbee <declension>`)
  * Add playlists to tray menu :bug:`2006` (:user:`Nick Boultbee <declension>`)
  * Random album plugin fixes :pr:`2085` (:user:`draxil`)
  * Custom commands: minor improvements (:user:`Nick Boultbee <declension>`)
  * Some Auto Library Update plugin fixes :bug:`1315`
    (:user:`Nick Boultbee <declension>`)
  * Seek bar plugin: invert scrolling directions :pr:`2052`
    (:user:`Corentin Néau <weyfonk>`)

Windows:
  * Switch to msys2 :bug:`1718`
  * Allow opening audio files with quodlibet.exe :bug:`1607`
  * Enable pitch plugin again :bug:`1534`
  * Windows regressions: crossfeed plugin missing (will be back in the
    next version)

macOS:
  * Allow opening audio files with the bundle
  * Really (really..) fix TLS :pr:`2108` :bug:`2107`

Development:
  * Tests: switch to `pytest <https://docs.pytest.org/en/latest/>`__
    as the main test runner
  * Tests: ``setup.py quality`` speedups
  * Tests: All tests pass now on Python 3 under Linux and Windows
  * All magic builtins gone :pr:`2044`
  * macOS bundle and Windows installer include everything required for running
    the test suite.


.. _release-3.7.1:

3.7.1 (2016-09-25) - And then you're doomed. Doomed to to have not ill effects, that is!
----------------------------------------------------------------------------------------

* tests: Use dbus-daemon instead of dbus-launch for creating a session bus. :bug:`2022`
* Fix 100% CPU when no song column is expanded. :bug:`2030`
* Fix SoundCloud login with Ubuntu 14.04 :bug:`2034`
* MP4: Fix crash when saving certain bpm tags :bug:`2028` (:user:`Nick Boultbee <declension>`)
* Windows: Make lastfmsync plugin work :bug:`1777`


.. _release-3.7.0:

3.7.0 (2016-08-27) - Yeah, this is like one of those scammy "name a star" sites!
--------------------------------------------------------------------------------

Packaging Changes:
  * **Mutagen 1.32** required
  * **udisks1** support removed
  * **PyGObject 3.12** required

* Add Soundcloud browser :bug:`1828` :pr:`1990` (:user:`Nick Boultbee <declension>`)
* Make F11 toggle fullscreen mode
* Add ``--refresh`` to the man page. :bug:`1914`
* Add ``--stop-after``. :bug:`1909`
* Remove support for loading browsers from ``~/.quodlibet/browsers`` :bug:`1919`
* Added shortcut of ``<Primary>Delete`` for moving files to trash :pr:`1921` (:user:`Victoria Hayes <victoriahayes>`)
* gstbe: always use pulsesink if pulseaudio is running. :bug:`1926`
* Remove udisks1 support
* Add a "Check for Updates" dialog
* Windows: Port mmkeys support from pyhook to ctypes.
  Fixes accents not working when QL is running. :bug:`1168`
* OSX: Enable multimedia key handling by default :bug:`1817`
* Add selection tick (check) for rating(s) that are selected :bug:`1891` (:user:`Nick Boultbee <declension>`)
* Support composersort :bug:`1795` (:user:`Nick Boultbee <declension>`)
* Rework application menu :bug:`1598` (:user:`Nick Boultbee <declension>`)
* Add a ~#playcount equalizer play order plugin :pr:`1626` (:user:`Ryan Turner <ZDBioHazard>`)
* Fix too large cover art border radius with Ubuntu themes
* songlist columns: handle font size changes at runtime. :bug:`1420`
* Fix song list column label fade out in RTL mode
* Fix seek bar getting stuck when releasing the button outside of the widget. :bug:`1953`
* Add default keyboard shortcuts for browsers/views :bug:`1540`
* Restore queue state. :bug:`1605`
* Add a queue toggle button to the status bar and remove the view menu
* docs: Clarified function of the queue :pr:`2004` (:user:`Bernd Wechner <bernd-wechner>`)

Translations:
  * Updated Polish translation :pr:`2009` (:user:`Piotr Drąg <piotrdrag>`)
  * French translation update :pr:`1932` (:user:`Ludovic Druette <LudoBike>`)
  * Fully update British English "translation" (:user:`Nick Boultbee <declension>`)

Tagging:
  * AIFF support :bug:`1801`
  * Support musicbrainz_releasetrackid :pr:`1992`
  * Support musicbrainz_releasegroupid :bug:`1896`
  * operon: Fix image-set when passing multiple files. :bug:`1729`
  * ASF: add WM/AlbumArtistSortOrder :bug:`1936`
  * MP4: Support saving replaygain tags :pr:`1916` (:user:`bp0`)
  * MP4: support replaygain_reference_loudness. :pr:`1928`

Plugins:
  * lyricswindow: Restart WebKit when crashed :pr:`1923` (:user:`CreamyCookie`)
  * lyricswindow: Prevent alert windows. :bug:`1927` (:user:`CreamyCookie`)
  * tray icon: Improve unity detection :bug:`1999`
  * musicbrainz: Add option to write labelid. :bug:`1929`
  * musicbrainz: Write musicbrainz release track ids :pr:`1992`
  * Rename Force Write plugin to "update tags in files" :bug:`1938` (:user:`Nick Boultbee <declension>`)
  * tray icon: Use App indicator when running under Enlightenment :pr:`1941` (:user:`Jakob Gahde <J5lx>`)
  * replaygain: delete tags written by bs1770gain. :bug:`1942`

Development:
  * py.test support
  * Some Python 3 porting progress: 47% tests passing :bug:`1580`
  * OSX: build dmgs


.. _release-3.6.2:

3.6.2 (2016-05-24) - It seemed like there was a lesson here, but nobody was sure what it was
--------------------------------------------------------------------------------------------

* Fix queue not expanding with GTK+ 3.20 :bug:`1915`
* Tag editor: Fix error message for unrooted patterns :bug:`1937`


.. _release-3.6.1:

3.6.1 (2016-04-05) - GOOD LUCK OUT THERE
----------------------------------------

* Tray icon: Don't use the app indicator for Ubuntu GNOME and KDE 4.
  :bug:`1904`
* Tray icon: Present the window when showing the window through the app
  indicator menu item. :bug:`1904`
* Paned browser: Fix crash with numeric tags in patterns :bug:`1903`
* Paned browser: Fix missing "Unknown" entry for patterns
* OS X: Fix TLS for real
* Lyrics window: Also support webkitgtk2 3.0 (for Ubuntu 14.04)


.. _release-3.6.0:

3.6.0 (2016-03-24) - It is altogether fitting and proper that we should do this
-------------------------------------------------------------------------------

Packaging Changes:
  * **Mutagen 1.30** required
  * **GTK+ 3.10** required
  * **PyGObject 3.10** required
  * **webkitgtk-3.0** → **webkit2gtk-4.0** (Lyrics Window plugin)
  * **sphinx 1.3** required for building the documentation
  * New optional plugin dependency: **libappindicator-gtk3** + **typelibs**:
    for the Tray Icon plugin under Ubuntu Unity and KDE Plasma
  * **python-musicbrainzngs** (>= 0.5) instead of **python-musicbrainz2**
  * **python-cddb** no longer needed
  * **libsoup** (>= 2.44) + **typelibs** required

* Add a keyboard shortcut window. :bug:`1837`
* Add ~language, which shows the language name for iso639 codes
* Allow cross-device moves to trash. :pr:`1782` :bug:`1339` (Andrew Chadwick)
* CLI: allow backslash-escaped commas in --enqueue-files. :bug:`1773`
  (Nick Boultbee)
* Fix custom accels read from ``~/.quodlibet/accels`` :bug:`1726` :pr:`1818`
* Fix determination of tag patterns in songlist :pr:`1830`
  (Peter F. Patel-Schneider)
* Fix ratings not being stored if they are the same as the default :bug:`1461`
  :pr:`1846`
* ID3: read lyrics from USLT frame, make ~lyrics read lyrics and form files
  :pr:`1810` (Ivan Shapovalov)
* Make test suite run (and fail) under Python 3 :bug:`1580`
* MP4: support conductor, discsubtitle, language & mood :bug:`323`
  (Nick Boultbee)
* Paned browser: Allow filters to be reset by clicking heading. :bug:`1284`
* Paned browser: use sort tags :bug:`1785`, :pr:`1796`
  (Peter F. Patel-Schneider)
* Patterns: Allow proper escaping in nested queries.
  (``<~filename=/^\/bla\/foo/|match|no-match>``)
* Player controls: use a normal button with two icons instead of a toggle
  button. :bug:`1814`
* Playlist browser: implement scroll to playing song :bug:`1426`
* Playlist browser: Make display configurable :bug:`1780` (Nick Boultbee)
* Playlist browser: Improve usability when creating a new playlist :bug:`1839`
  (Nick Boultbee)
* Playlist browser: Fix bug when deleting playlists :bug:`1882` (Nick Boultbee)
* Remove rounded cover preference and make border radius depend on theme.
  :bug:`1864`
* Search: make "ae" match "æ" and "ss" match "ß" etc.
* Search: numeric expressions and query plugins :pr:`1799`
* Song info display: show delete option to context menu. :bug:`1869`
* Songlist: Highlight the current song. See :bug:`1809`
* Support sort tags in song list patterns :pr:`1783` (Peter F. Patel-Schneider)
* Various GTK+ 3.20 related fixes

Translations:
  * Updated Dutch and Norwegian Bokmål translation :pr:`1784` (Nathan Follens)
  * Updated Polish translation :pr:`1898` (Piotr Drąg)

Plugins:
  * Update icons for most plugins: more and (mostly) better chosen.
    :bug:`1894` (Nick Boultbee)
  * Make songsmenu plugins only enabled if it makes sense for them
    :bug:`1858` (Nick Boultbee)
  * Remove cddb plugin; it's broken
  * Remove Send To plugin, in favour of Browse Folders and k3b plugins.
  * New plugin: Pause on headphone unplug. :bug:`1753`
  * New events plugin: Shows synchronized lyrics from .lrc file with same name
    as the track :pr:`1723`
  * Add a seekbar plugin. See :bug:`204`
  * lyricwiki: port to WebKit2
  * tray icon: support Ubuntu Unity and KDE Plasma (using libappindicator)
    :bug:`1756`
  * musicbrainz: port to musicbrainzngs. This fixes tagging of multi disc
    releases. :bug:`829`
  * Make LyricsWindow an events plugin; Add zoom level preference :pr:`1709`
  * Add authentication for MPDServer plugin :pr:`1789`
  * Custom Commands: add support for playlist name. :bug:`1685` (Nick Boultbee)
  * Playlist Export: convert to being a playlist plugin as well as songsmenu.
    (Nick Boultbee)

OS X:
  * Add a simple dock menu
  * TLS support (https streams..) :bug:`1895`
  * Add option to enable experimental mmkeys support in the advanced
    prefs plugin. :bug:`1817`

Wayland:
  * Fix seek bar window position (needs gtk+ 3.20)


.. _release-3.5.3:

3.5.3 (2016-01-16) - Uh, I GUESS that'd be good too??
-----------------------------------------------------

* Fix crash when opening new windows under some DEs (Linux only) :bug:`1788`


.. _release-3.5.2:

3.5.2 (2016-01-13) - This is because dates are arbitrary and friendship can be whatever we want it to be!
---------------------------------------------------------------------------------------------------------

* Polish translation update (Piotr Drąg)
* ID3: don't write albumartistsort twice :bug:`1732`
* Use the stream song for ``--print-playing``. :bug:`1742`
* Fix background color of some context menus with the Ubuntu 12.04 theme
* Fix adding new tags failing in some cases :bug:`1757`
* OSX: make cmd+w close windows :bug:`1715`
* Fix a crash with numerics in tag pattern conditionals :bug:`1762` (Nick Boultbee)
* Fix tests with newer Perl (through intltool)


.. _release-3.5.1:

3.5.1 (2015-10-14) - HOW TO SUCCEED AT SMALLTALK
------------------------------------------------

* Fix volume / mute state resetting on song change with some configurations
  :bug:`1703`
* Fix crash when G_FILENAME_ENCODING is set :bug:`1699`


.. _release-3.5.0:

3.5.0 (2015-10-07) - BETTER ANSWERS TO "HEY HOW ARE YOU?" THAN "I'M FINE"
-------------------------------------------------------------------------

Packaging Changes:
  * **Mutagen 1.27** required

General:
 * Add --print-query-text to get the current query for browsers that support
   it :bug:`1634`
 * Support conditional patterns with QL Query syntax :bug:`1604`
   (Nick Boultbee)
 * Playlist content search in the playlist browser :pr:`1593` (Nick Boultbee)
 * Disable app menu under Unity :bug:`1599`
 * Allow users to optionally bypass the trash even if it is available on their
   operating system (Eric Casteleijn) :pr:`1573`
 * Try to prevent fifo timeouts for slow operations :bug:`1616`
 * Fix border drawing with CSD/wayland
 * Use float for ~#length :bug:`1483`
 * Add a setting to enable/disable rating hotkeys :pr:`1625` (Ryan Turner)
 * Display all tags in tag list editor not just the non-default ones
   :bug:`1660`
 * Add a new ~codec and ~encoding tag (library reload needed) :bug:`9`
 * Add ~bitrate tag including the unit
 * Asymmetric search improvements e.g. 'o' now matches 'ø'
 * Various custom column header dialog improvements :bug:`1660` (Nick Boultbee)
 * Prefer txxx replaygain over rva2 :bug:`1587`
 * Support reading RG when ID3 tag key is in uppercase :bug:`1502`

Playback:
 * Implement direct sink volume control (e.g. for pulsesink, directsoundsink).
   Changing volume will now control the PA stream volume and result in less
   delay :bug:`1389` :bug:`1512`
 * Allow muting by middle clicking the volume button. Controls the
   pulseaudio stream mute property directly.
 * Increased GStreamer pipeline buffer size to reduce CPU usage :bug:`1687`
 * Hide seek slider when not seekable

OSX:
 * Replace "Ctrl" with "Command" in all keyboard shortcuts :bug:`1677`
 * (already in 3.4.1-v2 build) HIDPI support
 * (already in 3.4.1-v2 build) Support for more audio formats

Plugins:
 * Add a plugin for editing ~#playcount and ~#skipcount. :pr:`1624`
   (Ryan Turner)
 * Advanced preferences plugin :bug:`1050` (Bruno Bergot)
 * Allow to configure cover size in animosd plugin :bug:`1049` (Bruno Bergot)
 * Add plugin for removing TLEN frames from ID3 based files. :bug:`1655`
 * mpd: fix state sync with mpdroid 0.8. :bug:`1636`
 * Fix screensaver inhibit plugin. :bug:`1692`
 * qlscrobbler: fix offline mode check box. :bug:`1688`
 * lyrics window: use mobile wikia version

Translations:
 * Update Dutch translation :pr:`1618` (Nathan Follens)
 * Updated greek translation :bug:`1684` (Dimitris Papageorgiou)
 * setup.py: add a new create_po command for starting new translations


.. _release-3.4.1:

3.4.1 (2015-05-24) - Apparently, MY problem is a poisonous basement
-------------------------------------------------------------------

Fixes:
 * setup.py: respect --install-data :bug:`1575`
 * Suppress deprecation warnings with newer glib

Regressions:
 * Fix error when invoking a plugin with many songs/albums :bug:`1578`
 * Fix main window sometimes not showing under Ubuntu 12.04
 * Fix search not working with non-ASCII text in some cases


.. _release-3.4.0:

3.4.0 (2015-04-09) - She knew every of the things
-------------------------------------------------

Packaging Changes:
  * The main repo moved from Mercurial (Google Code) to Git (GitHub)
  * The build should now be reproducible
  * **gtk-update-icon-cache** is no longer a build dependency
  * **gettext >= 0.15** is required now at build time
  * A complete **icon theme** is now required (this was also partly the case
    with 3.3) and an icon theme including symbolic icons is recommended.
    **adwaita-icon-theme** provides both for example.
  * **Mutagen 1.22** required, **Mutagen 1.27** recommended
  * New files installed to ``/usr/share/icons/hicolor/scalable/apps/``
  * **quodlibet.desktop** now contains a **MimeType** entry, which means
    calling **update-desktop-database** is needed after package installation.

* Improved Gnome 3.16 compatibility

 * Fixes for the list tooltips in combination with GTK 3.16 scrollbars
 * Include symbolic icons for gnome-shell 3.16

* Album browser: faster cover loading
* Devices: fix detection of Sansa Clip+ with some setups :bug:`1523`
* Prefs: restore active tab
* Songlist: support patterns in the filter song list menu
* New shortcut ``ctrl+shift+j``, like ``ctrl+j`` but refilters the browser
  always
* Make build reproducible :bug:`1524`
* MP4: include codec information in ``~format``
  (needs a library reload) :bug:`1505`
* GStreamer: fix a deadlock when seeking right at a song change
* Queue: don't decide the next song too early :bug:`1496`
* Song info widget: provide the full song context menu :bug:`1527`
* CLI: ``--run`` to make QL start if it isn't already.
  Useful for pairing with other commands like ``--play-file``. :bug:`67`
* Add supported mime types to desktop file :bug:`67`
* CLI: ``--play-file`` doesn't add songs to the library anymore :bug:`1537`
* Fix QL starting twice if started in quick succession
* Tooltips: don't span multiple monitors :bug:`1554`
* MPD-Server: Fix a crash when changing the port number :bug:`1559`
* Fix short hang on shutdown with GStreamer plugins active :bug:`1567`
* Fix setting an embedded image in case the file doesn't have tags :bug:`1531`
* OSX: add a menu bar for Ex Falso
* Fifo: Fix commands failing in case QL is busy :bug:`1542`
* ...

Translations:
 * Use msgctx for message contexts


.. _release-3.3.1:

3.3.1 (2015-01-10) - Reduce, reuse, recycle, RESUBMIT
-----------------------------------------------------

Regressions:
 * Fix occasional errors when closing menus
   (with the plugin menu in Ex Falso for example) :bug:`1515`
 * Fix operon info :bug:`1514`
 * Fix operon fill error in case a tag doesn't match :bug:`1520`

Fixes:
 * Fix HiDPI DnD images when dragging multiple rows


.. _release-3.3.0:

3.3.0 (2014-12-31) - PARALLEL UNIVERSES. Travel there and THEN go back in time, and you can mess things up as much as you want.
-------------------------------------------------------------------------------------------------------------------------------

Packaging Changes:
  * New optional plugin dependency: **webkitgtk-3.0 + typelibs**
  * **Mutagen 1.27** recommended

General:
 * Support ``--query`` with all browsers that have a search entry. :bug:`1437`
 * Songlist: Scroll to playing song when replacing the list. :bug:`568`
 * Songlist: Scroll to first selected song and restore selection for
   it on re-sort. :bug:`568`
 * Consider all songs in an album for finding (embedded) album art.
   :bug:`924`
 * Support ``month`` (30 days) in time queries (``#(lastplayed < 1 month)``.
   :bug:`706`
 * Support playing a song that is not in the song list. :bug:`1358`
 * Support numeric date search e.g. ``#(2004-01 < date < 2004-05)``
   :bug:`1455`
 * Playlists browser: make delete key remove the selected songs from
   the current playlist :bug:`1481` (Nick Boultbee)
 * File tree: Show XDG desktop/downloads/music folders if available
 * File tree: List mountpoints on linux
 * Show the filter menu in secondary browser windows (filter shortcuts
   work there as well now)
 * Add ``alt+[1-9]`` shortcut for notebook widgets to jump the a specific page
 * Support loading ADTS/ADIF files (\*.aac). Needs mutagen 1.27.
 * Search: New regex modifier ``"d"`` which makes all letters match
   variants with diacritic marks (accents etc.). Enabled by default for normal
   text searches. ``Sigur Ros`` will now find songs containing ``Sigur Rós``.
   For regex and exact searches use ``/Sigur Ros/d`` and ``"Sigur Ros"d``
   to enable.
   :bug:`133`
 * New ~people:real tag which filters out "Various Artists" values
   (Nick Boultbee) :bug:`1034`
 * Prefer artist over albumartist for single songs in ~people (Nick Boultbee)
   :bug:`1034`

Fixes:
 * Update for theming changes in gtk3.15
 * Fix seek slider not working with newer gtk+ and some themes :bug:`1477`
 * Fix playing song not restoring on start with radio/filesystem browser

Translations:
 * Russian translation update (Anton Shestakov) :bug:`1441`
 * Updated Greek translation (Dimitris Papageorgiou). :bug:`1491`

Tagger:
 * WMA: support multiple values for producer, conductor, artist, lyricist,
   albumartist, composer, genre and mood (needs mutagen 1.26)
 * APEv2: Support reading/writing embedded album art for APEv2 based formats
   (Wavpack, Musepack, Monkey's Audio)
 * Allow removing and renaming from tag names which not all selected
   formats support.
 * Allow toggling of programmatic tags in the tagging UI

Plugins:
 * Various translation related fixes (Anton Shestakov) :bug:`1442` :bug:`1445`
 * New simple lyricwiki plugin using a WebKitGtk webview
 * New Rhythmbox import plugin. :bug:`1463`
 * MPD server: make work again with newer MPDroid (MPDroid crashed on start)
 * Trayicon: add option to quit when closing the main window instead of hiding
   :bug:`619`
 * Theme switcher: add option to enable/disable client side decorations
 * ReplayGain: add option to skip albums with existing ReplayGain values
   (Nick Boultbee) :bug:`1471`
 * Notifications: Make cover art display work under e19 :bug:`1504`

Operon:
 * new 'edit' command for editing tags with a text editor
   (``VISUAL=vi operon edit song.flac``) :bug:`1084`
 * new 'fill' command for filling tags using parts of the file path
   (``operon fill --dry-run "<tracknumber>. <title>" *.flac``)

OSX:
 * Multimedia key support (Eric Le Lay)
 * Global menu support / OSX integration. (Eric Le Lay)
 * Various fixes / improvements

Windows:
 * Newer mutagen (1.27)
 * Newer GTK+/Gstreamer (Tumagonx)
 * Fix loading cover art from non-ansi paths
 * Starting QL will now focus the first instance if one exists
 * quodlibet.exe now passes command arguments to the running instance
   (quodlibet.exe --next) :bug:`635`
 * New quodlibet-cmd.exe which is the same as quodlibet.exe but
   can be executed in the Windows console with visible stdout :bug:`635`


.. _release-3.2.2:

3.2.2 (2014-10-03) - ENJOY, THERE'S NO GOING BACK
-------------------------------------------------

Fixes
 * Fix a crash when seeking streams in some cases :bug:`1450`
 * Fix a crash in case Windows Explorer favourites link to a non ASCII path :bug:`1464`
 * Fix playback stopping when playing chained ogg streams :bug:`1454`
 * Fix context menus not showing sometimes with GTK+3.14.1

Translations
 * Russian translation update (Anton Shestakov)


.. _release-3.2.1:

3.2.1 (2014-08-16) - BAKE HIM AWAY, TOYS
----------------------------------------

Fixes
 * Fix Ex Falso not starting in some cases. :bug:`1448`
 * Album art download plugin: Fix image file extension (Nick Boultbee)
   :bug:`1435`

Translations
 * Russian translation update (Anton Shestakov) :bug:`1441`


.. _release-3.2.0:

3.2.0 (2014-08-01) - WHAT KIND OF GOD MADE IT SO LIONS HUG BACK TOO HARD
------------------------------------------------------------------------

Packaging Changes:
  * **Plugins got merged** into Quod Libet. This means the quodlibet-plugins
    tarball is gone and plugins will be installed by ``setup.py install``. For
    distros that used to include the plugins in the main package this means all
    plugin related packaging code can simply be removed. For distros that
    offered separate packages the installation can be split by packaging
    ``quodlibet/ext`` in a separate package. Quod Libet can run without it.
  * **UDisks2** is supported, in addition to UDisks1
  * **Python 2.7** required instead of 2.6 (might still work, but not tested)

Tags:
 * ~people and ~performer don't show roles anymore, which makes them more
   useful in the paned browser for example. Instead ~people:roles and
   ~performer:roles will include roles and merge roles like "Artist (Role1,
   Role2)". Furthermore composer, lyricist, arranger and conductor will be
   merged with performer roles in ~people:roles. so "performer:role1=Foo,
   composer=Foo" will result in "Foo (Role1, Composition)". (qjh)
 * ~#rating in the song list is now a numeric column, ~rating shows the stars
   (Jan Path) :bug:`1381`

UI:
 * HiDPI support (start with GDK_SCALE=2, needs cairo trunk)
 * Various display fixes for GTK+ 3.13 and non-Adwaita based themes
 * Seek slider width scales with song length to some extend
 * Seek slider shows remaining time
 * Play order plugins are now split in random/non-random and
   the UI was replaced by a toggle button + menu. :bug:`1411`
 * Removing of songs from a playlist through the context menu (Nick Boultbee)
 * Song list columns now remember their width/state (qjh)
 * Song list columns provide an option to toggle if they expand.
 * The multi sort dialog is gone, instead it's now possible to sort
   by multiple tags by holding down ctrl and clicking on multiple columns.

Plugins:
 * New MPD Server plugin to remote control QL, e.g. through MPDroid :bug:`1377`
 * New acoustid.org fingerprint tagger (basic functionality, but works)
 * "Show File" merged into "Browse Folders", it will now try to
   select the files if the interfaces allows it.
 * Exact rating plugin (Jan Path) :bug:`1383`

Player:
 * Improved GStreamer error reporting.
 * Error recording is gone, since it was just annoying. :bug:`1400`

Windows:
 * Fix slow startup :bug:`1389`
 * Windows Explorer folder context menu entry for Ex Falso

Misc:
 * Keyboard shortcuts are now documented:
   https://quodlibet.readthedocs.io/en/latest/guide/shortcuts.html

Developers:
 * Due to the inclusion of the plugins into the core, the symlink from
   ~/.quodlibet/plugins is no longer needed.

Fixes:
 * Fix tray icon crashing or not showing under Gnome Shell 3.12 :bug:`1429`

Packaging:
 * UDisks2 supported, in addition to UDisks1
 * Plugins are now included in the main tarball and will be installed by
   setup.py, the quodlibet-plugins tarball is gone. (Load path switched from
   quodlibet/plugins to quodlibet/ext for system wide plugins, loading from
   ~/.quodlibet/plugins is the same) :bug:`1396`
 * For BSDs: setup.py has a new "--mandir" to select the man page location
 * Packaging guide: https://quodlibet.readthedocs.io/en/latest/packaging.html


.. _release-3.1.91:

3.1.91 [beta] (2014-07-22) - Pumps, powerheads, lights and filters!
-------------------------------------------------------------------

See :ref:`final release <release-3.2.0>`


.. _release-3.1.2:

3.1.2 (2014-06-20) - Dang it
----------------------------

* Fix 3.1.1 regression causing folders in the file browser to show up in reverse order :bug:`1390`


.. _release-3.1.1:

3.1.1 (2014-04-28) - I've shown that you're dealing with an Alpha here, baby, not some weak Beta!
-------------------------------------------------------------------------------------------------

* Fix a crash with GTK+ 3.12 :bug:`1384`
* Handle invalid flac picture blocks :bug:`1385`
* Fix "setup.py install --record" :bug:`1373`


.. _release-3.1.0:

3.1.0 (2014-04-10) - Olden times, man! NEVER LIVE THERE.
--------------------------------------------------------

* Windows is supported again. And it should be in better shape than with 2.6
  in many aspects. Embedded images work now, newer GStreamer with more
  codecs, operon is included etc. The file browser and EF now show the
  favorite folders from the Windows Explorer. The installer will
  now uninstall any existing installation first and as with 2.6.3 there
  is a portable version available.

  There is still an unsolved problem regarding miss-placed context menus
  with multiple monitors :bug:`1319`.

  Thanks goes to Bakhtiar Hasmanan for providing a working PyGObject stack.

* Initial Wayland support is here (only tested under weston). This was mostly
  fixing weird usage of GTK+ that just happened to work under X11 and not
  using the screen size for calculations since there is no real screen under
  Wayland.

* Piotr Drąg, Rüdiger Arp, Diego Beraldin and Dimitris Papageorgiou worked
  on improving the translations.

* Nick Boultbee worked on a plugin system for playlist plugins and moved
  the duplication/shuffle actions to it. He also moved the rating
  configuration from the plugin into the core.

* Simonas Kazlauskas worked on a plugin system for cover art sources currently
  supporting last.fm and musicbrainz (exposed as two plugins). If active it
  will fetch covers in case no local cover is found. In the future we might
  implement the album art downloader on top of that.

* Thomas Vogt made transparency work again with GTK+3 in the OSD plugin.
  (fake transparency now also works again, which was the last known
  regression from the PyGObject port)

* operon gained new commands (image-extract, image-set, image-clear) for
  manipulating and extracting embedded images for all formats supporting
  embedded images in QL (id3, ogg, flac, wma, mp4). See the manpage [0]
  for examples. There is also a QL plugin which allows removing all
  embedded images and embed the active one. This should get better
  integrated into the tag editor at some point.

* Display patterns now support specifying the markup using square brackets to
  not need escaping in the common case. "\<b\><artist>\</b\>" can now be
  written as "[b]<artist>[/b]" (the old way still works).

* In the radio browser the radio list now contains icecast and shoutcast2
  stations in addition to shoutcast1 ones and only one additional mirror is
  included for each station. QL now shows ~4100 stations of ~30000 we know
  about. Use "Update stations" to get the new list.

Other changes:

* QL now remembers additional open browsers and reopens them on start.
* The main tool bar is better integrated with GTK+ themes.
* We use symbolic icons in many places.
* Added a simple GNOME app menu.
* 'albumartist' is now used for album identification.
* <shift>space enables "stop after the current song".
* Warning before opening too many plugin windows (Nick Boultbee) :bug:`1231`
* New --unqueue-all command :bug:`1234`

Fixes:

* Config gets saved atomically and handle a corrupted one :bug:`1042`
* editing:id3encoding option was ignored :bug:`1290`
* album browser: Fix sorting by rating :bug:`1352`
* search: Fix results for "&(foo, !bar)" :bug:`1327`
* Various crashes caused by code not being ported to PyGObject properly.

Dependencies & Packaging:

* No dependency changes compared to 3.0
* We now install appdata.xml files
* We now install a dbus service file
* ``setup.py build_sphinx`` builds the html user guide


.. _release-3.0.91:

3.0.91 [beta] (2014-02-28) - You'd have to be in space for that to work.
------------------------------------------------------------------------

See :ref:`final release <release-3.1.0>`


2.6.3 (2013-09-25) - The one that can't even go naked into space without dying!
-------------------------------------------------------------------------------

This is a Windows only bug fix release.

Windows:
 * Fix library saving [1230] (Sebastian Thürrschmidt)


.. _release-3.0.2:

3.0.2 (2013-07-22) - LATER, THE OCEANS BOIL AS THE EARTH TURNS TO FIRE
----------------------------------------------------------------------

General
 * Device backend: Correctly detect udisks1 if it isn't running [1200]
 * mmkeys: Really make libkeybinder work again [1203] (Hans Scholze)
 * Fix play button not starting playback if no song is active [863]
 * Don't forget newly created bookmarks in some cases
 * Fix "Refresh" in the file tree browser [1201]
 * Fix menu separator drawing with PyGObject 3.2 (Ubuntu 12.04)
 * Various fixes

Plugins
 * Forward library events to event plugins again
 * Fix bookmarks plugin, playlist export plugin, HTML export plugin
 * animosd: Handle multiple monitors (Nick Boultbee)

2.6.2 (2013-07-22) - 256 Pictures of Cool Bugs
----------------------------------------------

2.6.1 skipped to keep in sync with the 3.0 branch.

General
 * Device backend: Correctly detect udisks1 if it isn't running [1200]
 * Fix play button not starting playback if no song is active [863]
 * Don't forget newly created bookmarks in some cases
 * Various fixes

Plugins
 * Fix HTML export plugin
 * Fix Bookmarks plugin


.. _release-3.0.1:

3.0.1 (2013-07-08) - *gasp*
---------------------------

 * Fix a crasher with some PyGObject versions [1211]


.. _release-3.0.0:

3.0.0 (2013-06-15) - THE NEMESIS HYPOTHESIS
-------------------------------------------

Requirements & Packaging Changes
 * Python 2.6+
 * GTK+ 3.2+ & GIR (instead of 2.x)
 * GStreamer 1.0+ & GIR (instead of 0.10)
 * PyGObject 3.2+ (3.4 highly recommended) (instead of PyGTK)
 * PyGObject cairo support
 * libgpod 0.5+ (instead of python-gpod)
 * libkeybinder-3.0 & GIR (instead of python-keybinder)
 * HAL support removed
 * New `operon` script + man page
 * New .ini file for registering QL as a GNOME Shell Search Provider

Translations
 * New: Czech translation (Honza Hejzl)
 * Russian translation update (Anton Shestakov)
 * Lithuanian translation update [1079] (Naglis Jonaitis)
 * Swedish translation update [1117] (Daniel Nyberg)
 * Spanish, Basque and Galician translation update (Johám-Luís Miguéns Vila)
 * Greek translation update [1175] (Dimitris Papageorgiou)

General
 * Improved rating visibility [1070] (Nick Boultbee)
 * File system view: DnD directories to external targets (Nick Boultbee)
 * Support GNOME Notification Sources
 * Bayesian averaging for set (album) ratings [1085] (Nick Boultbee)
 * New command line tagger: operon (see `man operon`)
 * Hide songs on not-mounted drives on start without library refresh [984]
 * Preferences UI for managing masked mount points [984]
 * Support all patterns as song list headers [507, 1121] (Nick Boultbee)
 * Save/restore queue position
 * Documentation is now Sphinx/reST based and hosted on readthedocs.org

Fixes
 * Fix unwanted re-filtering of all open browsers if the search history changes
 * Fix crash when re-adding devices while QL is running [1120]
 * Remove EF directory mime type again (too many problems with file managers)

Tagging
 * APEv2: Add disc<->discnumber mapping

Plugins
 * New: Custom Commands plugin (Nick Boultbee)
 * New: GNOME Shell Search Provider plugin [1147]
 * ReplayGain plugin: Parallel processing [807]
 * CD burn plugin: Add Xfburn support [1173]

Known Regressions
 * GStreamer output device selection is no longer supported.
   (GStreamer 1.0 has removed the property probing interface)
 * No multimedia keys support with non-GNOME DEs in some distributions
   due to missing packaging:

   * https://bugzilla.redhat.com/show_bug.cgi?id=963476
   * https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=710254

 * Animated On-Screen Display plugin is missing transparency support
 * No Windows build (work in progress)


2.6.0 (2013-06-15) - Someone's attacking us from... space?
----------------------------------------------------------

 2.6 is the last PyGTK/GTK+2 based release of Quod Libet / Ex Falso. It
 contains most of the changes that went into 3.0 and will only receive
 bugfix releases from here on out.

Requirements & Packaging
 * Python 2.6+
 * PyGTK 2.16+

Everything else
 * See 3.0.0 NEWS with a few exceptions


2.9.92 [beta] (2013-06-05) - alternatetimelinemetarhyme
-------------------------------------------------------

General
 * Fix the main song list resetting while working with multiple browsers
 * Fix various widget redraw/positioning/jumping problems
 * Various fixes regarding GTK+3.6+ (seek slider, tv hints)
 * Nicer about dialog
 * Fix one-click ratings [1170]
 * Fix various crashes with PyGObject3.2 [1172]

Plugins
 * New GNOME Shell Search Provider plugin [1147]
 * Support Xfburn in the CD burn plugin [1173]
 * viewlyrics plugin: Fix key handling [1171]
 * Fix musicbrainz plugin [1162]
 * Fix replaygain plugin in Ex Falso [1163]
 * Fix fingerprint plugin [1174]

2.9.91 [beta] (2013-05-13) - welcome to a place where incredibly terrible things can happen to you and your friends for no reason!
----------------------------------------------------------------------------------------------------------------------------------

General
 * Spanish, Basque and Galician translation updates (Johám-Luís Miguéns Vila)
 * Tag editor: Fix context menu not showing
 * Album collection: Fix crash with PyGObject 3.2
 * Fix search bar text color
 * Fix DnD to closed queue
 * Fix hangs during unix signal handling
 * Fix 100% CPU in some cases
 * Fix library refresh pause/stop handling
 * Some speed improvements and fixes

Plugins
 * ReplayGain plugin now processes albums in parallel
 * New dark theme option in the theme switcher plugin
 * Fix GStreamer equalizer
 * Fix theme switcher plugin
 * Fix GStreamer mono plugin

2.9.82 [alpha] (2013-05-02) - One day Marty McFly got bit by a werewolf!
------------------------------------------------------------------------

PyGObject/Gtk+3.0/Gstreamer1.0 Port - Alpha 2 release:
 * Fix lyricsview plugin (Nick Boultbee)
 * Fix replaygain album gain/peak writing.
 * Fix crash on one-click ratings in the song list.
 * Fix crash when playing a song while editing its tags.
 * gstbe: Increase operation timeouts (for spinning up disks etc.)

2.9.81 [alpha] (2013-04-27) - Because my hypothesis is: it's rad
----------------------------------------------------------------

PyGObject/Gtk+3.0/Gstreamer1.0 Port - Alpha 1 release

2.5.1 (2013-04-23) - Yes: MY COMPUTER IS A PERSON.
--------------------------------------------------

 * Fix various widgets not showing with pygtk/pygobject trunk
 * Fix QL refusing to start in some cases [1131]
 * Improve web browser discovery and fix on Windows
 * Fix various problems with playlists + masked files [1095]
 * Reduce debug output if loading a file fails [1080]
 * Plugins:

   * notify: Don't set notifications to transient [1103]
   * lastfmsync: Fix loading/saving of cache [1093]

2.5 (2012-12-19) - Reading on the floor: literature!
----------------------------------------------------

 * Greek translation update (Dimitris Papageorgiou) [1064]
 * Russian translation update (Anton Shestakov) [1072]
 * Lithuanian translation update (Naglis Jonaitis)[1079]

2.4.91 [beta] (2012-11-23) - hello and thank you for installing an internet!
----------------------------------------------------------------------------

News for packagers
 * setup.py will install png and svg icons into hicolor and a png icon into
   pixmaps. It will also try to call gtk-update-icon-cache if it's in the
   target prefix/root (make sure the icon cache gets updated on package
   install)
 * C extensions removed. QL is now Python only.
 * PyGTK 2.16+
 * Python 2.6+
 * Support for libudev.so.1 (>= 183)
 * New: python-keybinder needed for multimedia keys
 * New plugin directory: gstreamer
 * Optional plugin dependencies:

   * Removed: python-indicate (Ubuntu sound menu),
     lastfmsubmitd (old last.fm plugin)
   * New: rygel (DBus UPnP MediaServer), python-zeitgeist (Zeitgeist)

News for translators
 * QUODLIBET_TEST_TRANS=xxx will append/prepend "xxx" to all translations so
   you see what is translatable and for devs to check how, long translations
   will affect the UI.
 * "setup.py po_stats" to see how much is translated for each po file.
 * "setup.py check_pot" to see if a file containing translatable strings is
   missing from POTFILES.in

General
 * Search: Handle non-ascii values for filesystem tags
   (~filename, ~dirname..) [227]
 * New internal tags:  ~originalyear ~#originalyear. [966]
 * New internal tag: ~playlists (Nick Boultbee)
 * Shortcut: alt + left/right -> seek +/- 10 seconds [981]
 * Support startup notification spec
 * Support newest thumbnail spec (v0.8.0)
 * Basic Unity quicklist
 * New --stop switch to stop and release the audio device [1018]
 * List tooltips: work with gnome shell, never shift left, support trees [778]
 * New --no-plugins switch to start without plugins
 * No wakeups if nothing is playing.
 * Directory mimetype for Ex Falso
 * Shortcut: ctrl+left/right, left/right for treeview navigation
 * Some UI cleanup, less padding in the main window
 * Remember window size & position for properties, info, browsers [106]
 * Device selection for the gstreamer back-end
 * Use lyricist for finding lyrics if available
 * Click on default cover icon launches album art plugin [2] (Nick Boultbee)
 * Fix: Work with Compiz window placement plugin [871]
 * Fix: Queue widgets not clickable in some cases
 * Fix: Double-click on album will plays song from queue [231]
 * Fix: Filter on album in album browser now uses the album key
 * New: PluginConfigMixin added to core to simplify plugin prefs (Nick Boultbee)
 * Fix: --status (carlo.teubner) [1045]

Formats
 * New: Monkey's Audio
 * New: Ogg Opus (needs mutagen 0.21) [1012]
 * New: MIDI
 * Basic SPC tag parsing [282] (David Schneider)
 * Add m4v to valid mp4 extensions

Tagging
 * Limit path sections to 255 chars instead of tags to 100 [915]
 * ID3: Write foobar style replaygain tags. [1027]
 * VORBISCOMMENT: Write totaltracks/totaldiscs [929] (Michael Ball)
 * Shortcut: ctrl-s for saving changes, and configurable standard accels
   per locale [697] (alex.geoffrey.smith, Nick Boultbee)
 * Updates to tag splitting (originalartist, performer) (Nick Boultbee)

Translations
 * New: Greek translation (Dimitris Papageorgiou)
 * German translation update (Rüdiger Arp)
 * British English translation update (Nick Boultbee)
 * French translation partial update (Nick Boultbee)

Plugins
 * Removed: lastfmsubmitd
 * Removed: DBus mmkeys (moved to core)
 * Removed: Ubuntu Sound Menu (no longer needed)
 * New: UPnP AV Media Server plugin (needs rygel)
 * New: ViewLyrics plugin (Vasiliy Faronov)
 * New: Filter on directory [922]
 * New: Zeitgeist plugin [717]
 * New: Mac OS X mmkeys plugin (Martijn Pieters) [967]
 * New: Telepathy/Empathy status plugin [478] (Nick Boultbee)
 * New GStreamer plugins: Compressor, Crossfeed, Pitch, Mono
 * New: Filter on multiple tags [1014]
 * New: Squeezebox Playlist Export (Nick Boultbee)
 * Browse Folders: Use the default file browser [983]
 * Equalizer: add presets
 * MPRIS: various fixes (for the GS plugin)
 * Notify: Dismiss notifications after some time
 * Duplicate Browser: expand/unexpand all button
 * CD burn: now menu-based
 * Updated: Auto Library Updater (Nick Boultbee)

Browsers
 * New: Album Collection - provides a tree-like view of albums similar to Paned.
 * Playlists:

   * Delete shortcut [942] (Johannes Marbach)
   * Shuffle playlist (Nick Boultbee)
   * Remove duplicates [685] (Nick Boultbee)

 * Album list: more filters

Windows
 * Make Browse folder plugin work [993]
 * Multimedia keys support

2.4.1 (2012-07-27) - Man! If I were a robot, a lot of things would be different
-------------------------------------------------------------------------------

 * Fixes:

   * Fix skipping one song during a song change [987]
     (This also broke the random album plugin in some cases)
   * Windows: Crash in file system view if 'My Music' folder is missing [1008]
   * Fix --quit [958]
   * Fix playing of files that don't match the file system encoding [989]
   * Workaround for mutagen ID3v2.3 update bug [mutagen 97]
   * Various fixes [1013, 1002, 962]

 * Plugin fixes:

   * lastfmsync crashes [957]
   * Various Duplicate browser fixes [999, 954]
   * Notification crash [975]

2.4 (2012-03-18) - He decides he must become... Abe Atman!
----------------------------------------------------------

 * Fixes:

   * Support xinelib 1.2 [904]
   * MP3/ID3: fix some rare crashes; prefer main embedded cover
   * Vorbiscomment:

     * Ignore coverart and use it as cover art source [910]
     * Fix deletion of metadata_block_picture

   * album art: update coverparadise, disable discogs (API changed)
   * squeezebox fixes (Nick Boultbee)
   * German translation update (Rüdiger Arp)
   * Various fixes [890, 909, 899]

 * Fixed regressions:

   * Python 2.5 / PyGTK 2.12 compatibility
   * Restore saved play order [891]

2.3.91/92 [beta] (2012-01-16) - Players only love you when they're playing
--------------------------------------------------------------------------

 * Fixes:

   * Don't remove periods from tag values in patterns [368]
   * Don't jump to playing song on stream changes
   * Fix wrong path encoding in the exfalso file selector under Windows
   * Fix error when controlling playback during startup [810]
   * Handle invalid header patterns
   * Don't lose the radio library randomly [645]
   * Handle non utf-8 and invalid filenames in the song list [798]
   * Fix a crash when the song list changed during a gapless transition [799]
   * Tray icon doesn't appear in KDE panel [881]
   * xine backend: Fix equalizer value range

 * Plugin Fixes:

   * Fix "&amp;" in notifications (xfce4-notifyd) (Anton Shestakov)
   * Fix animosd config again
   * Fix Amazon cover search (API change)

 * General

   * Improved startup speed
   * GNOME session shutdown fixes
   * Hide all windows on shutdown
   * Handle signals during startup
   * Correctly push signals into the gtk+ mainloop (no more segfaults)
   * Cyclic saving of all libraries not just the main one
   * Rename the process to "quodlibet" or "exfalso" [736] (Nick Boultbee)
   * Queue keyboard shortcut is now Ctrl+Return not just Q [747]
   * Add new songs that match the active filter to the song list
   * Focus search entry with ctrl+l [666]
   * Fix reverse sort (sort by album first)
   * Custom sort dialog [820] (Philipp Müller, Joschka Fischer)
   * Make the paned browser the default one
   * Focus the first row in all automatic list selections [835]
   * Select next song in the song list after song removal [785]
   * Speed up song removal in long lists [785]
   * Delete keyboard shurtcut in the queue
   * Add menu entry to rate current playing song (Nick Boultbee)
   * Make it possible to override quodlibet/exfalso icon,
     by placing an icon in the current icon theme [614]
   * Close buttons in all dialogs (since GNOME 3 has no close button in
     the window decorations for dialogs by default) [772]
   * Make main window resizeable with only the queue showing [657]
     (Florian Demmer)
   * Make the paned browser prefs resizable
   * Search bar: No delays for any keyboard/mouse actions except typing
   * Estimate FLAC bitrate using the filesize [342] (Nick Boultbee)
   * New ~#filesize tag: requires library reload (Nick Boultbee)
   * Enhancements to the ways album art is detected (Nick Boultbee):
     new tab in prefs,
     new option for forcing art filename [328],
     new option for preferring embedded image over external ones
   * Allow numeric ~#replaygain_xxx tags (Nick Boultbee)
   * album browser: Restore search on start
   * album browser: Move sort order in the preference button sub menu
   * album browser: Load all visible covers before showing the album list
   * album browser: Fewer redraws after filtering
   * album browser: Add sort by genre option [340]
   * radio browser: Genre filter list
   * radio browser: Use the default search bar (with history)
   * radio browser: Remote station list with 4000 stations
   * radio browser: Properly sync the song list play icon with song changes
   * radio browser: Prefill new station dialog with last URL in the clipboard
   * radio browser: title falls back to organization and artist to website
     (for the song list)
   * radio browser: Buffer process shown in status bar
   * search: Stricter numeric value parsing (only allow valid units)
   * search: Don't require a space between number and unit: #(added<1day)
   * search: Support GB/KB/MB/B units for ~#filesize

 * Gstreamer:

   * Fully support playbin1 again (QUODLIBET_PLAYBIN1 env var)
   * Allow setting of stream buffer duration [696]
   * Sync replaygain volume change with track change [652]
     (use track-changed signal in newer gstreamer)
     this needed the removal of the 500ms queue. Can be enabled if there
     are problems with gapless (QUODLIBET_GSTBE_QUEUE env var)
   * Don't add equalizer if the plugin is disabled:
     No unnecessary conversions to float (flac, mp3 decoder), less CPU
   * Don't use the fluendo mp3 decoder if mad is available, less CPU
   * No video decoding/playing (mp4 files for example)
   * Properly emit song-started/ended for radio stream songs
     (so they get counted as auto started by the new notify plugin)
   * Add button in the prefs to print the currently used pipeline
     including format conversions (only in --debug mode)
   * No more jumping of the position slider during song changes
   * Better parsing of stream metadata [750]

 * Translations:

   * Russian translation update (Anton Shestakov)
   * German translation update (Rüdiger Arp)
   * Italian translation update (Luca Baraldi)

 * Tagging/Ex Falso:

   * Improve support for language tag, with ISO 639-2 suggestions
     (Nick Boultbee)
   * ID3: handle TLAN [439] (Nick Boultbee)
   * Ignore zero TLEN id3 frame [222]
   * Allow performer to be split out of title (Nick Boultbee)
   * Ogg Theora support
   * Ex Falso about dialog

 * CLI:

   * --debug (colored output, yay)
   * --enqueue-files=file,file [716] (Nick Boultbee)
   * --print-query=query [716] (Nick Boultbee)
   * --force-previous [441] (go to previous not depending on the
     current position)

 * Plugins:

   * Removed old plugin import fallback code: In case loading
     a third party plugin fails, set the QUODLIBET_OLDIMPORT env var.
   * Show an error message instead of the stack trace for common
     plugin loading errors (import errors)
   * Improved notification plugin [588] (Felix Krull)
   * Improved scrobbler preferences with account data verification
   * Trayicon: Use custom theme icons [614]
     Prevent the main window from showing on startup
   * Musicbrainz: Only write sort tags that are different
   * Titlecase: New prefs switch to allow all caps in tags (Nick Boultbee)
   * NEW: Website Search (Nick Boultbee)
   * NEW: Inhibit Screensaver while playing (GNOME)
   * NEW: Pause while the screensaver is active (GNOME)
   * NEW: Acoustid.org fingerprint plugin (only for submitting atm)
   * NEW: Duplicates browser (Nick Boultbee)
   * NEW: Mute radio advertisements (di.fm only atm)
   * NEW: Watch directories for file changes (using pyinotify) [270]
     (Nick Boultbee, Joe Higton)
   * NEW: Theme switcher plugin
   * NEW: Squeezebox plugin (Nick Boultbee)

2.3.2 (2011-10-17) - It doesn't matter! My beats are great!
-----------------------------------------------------------


    * Fix crash in album browser [781]
    * Plugins:

      * DBus multimedia keys: Make it work with gnome-settings-daemon 3.x
      * Album art: Remove darktown, fix discogs.
      * MPRIS: Various fixes [776, 817, 827]

    * Translation Updates:

      * Lithuanian (Naglis Jonaitis)

2.3.1 (2011-07-16) - YES It works in BOTH temporal directions
-------------------------------------------------------------

    * Absolute path renaming on Windows [506]
    * Fix dynamic song removal of songs not matching the query [713]
    * Fix "--print-playing <~#rating>" [730]
    * Fix search not working with an active pattern column
    * Fix hang with newer GStreamer versions and sinkless pipelines
    * Some minor fixes [682, 724, 704]
    * Plugins:

      * Fix MPRIS not handling invalid dates (Nick Boultbee)
      * Some OSD fixes (Nick Boultbee)

    * Translations:

      * German (Rüdiger Arp)
      * Italian (Luca Baraldi)
      * Lithuanian (Naglis Jonaitis)

2.3 (2011-04-01) - I THOUGHT THAT WAS PRETTY CLEAR
---------------------------------------------------

    * Various minor bug fixes
    * Some small translation updates (Anton Shestakov)
    * Update of the 2.2.99 news entry

2.2.99 [beta] (2011-03-13) - I can imagine that one day there could be aperson who would read that
--------------------------------------------------------------------------------------------------

    * Quod Libet now needs Python >=2.5
    * Drag and drop in paned browser
    * Speed up adding many songs to the queue
    * Smaller volume, seek controls
    * Ask for playlist name on creation
    * Output playing progress when using --status
    * Use current icon theme icons everywhere (for DAPs etc.)
    * Floating point custom tags
    * Audio streaming fixes (buffering etc.) (Andreas Bombe)
    * Treeview hints in paned browser
    * Cover art now only uses the available space
    * Support embedded covers art in WMA/Vorbis files
    * Set composer, albumartist, sort tags when copying to an iPod
    * Natural sorting in the song list
    * Many song list speedups (sorting, filling, scrolling)
    * Split up pattern results in paned browser with multi-value tags
    * Only consider a song played after half has elapsed
    * Undo/Redo support for all text entries
    * New framework for showing running tasks, notifications in the status bar
    * Text markup in the paned browser
    * Restore maximized state
    * Restore window position (Felix Krull)
    * Make size of the queue adjustable (Florian Demmer)
    * Mouse scrolling over the play button now changes songs
    * Support alternate home directory using $QUODLIBET_USERDIR (jkohen)
    * Make the default rating changeable (library reload needed)
    * Drag and scroll in the song list
    * Faster context menu opening
    * Display playlist size (library reload needed) (Nick Boultbee)
    * Support queries without specifying a tag name
    * All queries in the album browser use a standard operation (avg, sum etc.)
    * Support ~rating, ~#bitrate in the album pattern
    * Support separate song collection patterns in the paned browser
    * Don't jump to a playing song if it was selected from the songlist
    * Faster local cover search
    * Support FreeDesktop trash spec
    * Lower case option for file renaming (Nick Boultbee)
    * Various bug fixes, speed improvements (Jacob Lee, Johannes Rohrer,
      Tshepang Lekhonkhobe)
    * Bug fixes:

      * Treeview hints now work with GTK+ >= 2.20
      * Search history now gets properly shared between browsers
      * Fix udev crashes
      * Paned browser leaks
      * Respect global filter in all browsers/filters
      * Don't lose tag values with differently cased tag names (APEv2)
      * Fix --set-browser (Carlo Teubner)
      * Properly handle the case where a playing song gets deleted
      * Fix redraw errors using compiz
      * FSync on library save
      * Fix crash when ~/.gtk-bookmarks contains empty lines (Felix Krull)
      * Correctly identify rockboxed iPods

    * Windows (Uninstall any previously installed version!):

      * Fix translation under Win 7
      * Fix cover art plugin saving
      * Add all partitions to the file selector
      * Fix various crashes with wide char user names
      * Fix icon under Win 7
      * Support multi-user installations
      * Fix freezes after opening certain folders

    * New plugins:

      * Follow cursor play order plugin
      * Equalizer plugin
      * MPRIS 1.0/2.0 plugin
      * Ubuntu sound menu plugin
      * Rating reset plugin
      * Track repeat plugin (Nick Boultbee)

    * Plugins:

      * Go to bookmark plugin now menu based
      * Fix some album art plugin backends (Aymeric Mansoux, ..)
      * Improved "human" title casing (Nick Boultbee)
      * Fix queue only plugin stopping the current song.
      * Only use allowed HTML in the notify plugin.
      * musicbrainz: allow writing sort tags (Michaël Ball)

    * Translations:

      * new Latvian translation (Einars Sprugis)
      * new Basque translation (Piarres Beobide)
      * French translation updates (Nick Boultbee)
      * Brazilian/Portuguese translation updates (Djavan Fagundes)
      * Russian translation updates (Anton Shestakov)

2.2.1 (2010-03-27) - Fewer than four out of ten people respect my promises -- and possibly more!
------------------------------------------------------------------------------------------------

 * Fix for importing some mp3 files. [220]
 * More fixes for the device backend (iPod, multi partition DAPs). [410, 412]
 * Fix editing keys with multiple values. [440]
 * Fix weighted playorder algorithm.
 * Save songlist column patterns. [447]
 * Some small fixes here and there.
 * Plugin fixes:

   * Title case: Improved title casing for English text. (Nick Boultbee)
   * Random Album: Algorithm improvements.
   * QLScrobbler: Fix preference pane ordering.
   * Album art: Some images weren't displayed. (Tomasz Miasko) [429]
   * Last.fm Sync, Musicbrainz: Minor fixes.

 * Translations:

   * Galician, Spanish (Johám-Luís Miguéns Vila).
   * German (Rüdiger Arp).

2.2 (2010-02-02) - I know you are enjoying that song but a woman DIED
---------------------------------------------------------------------

 * Saved searches extended to Album and Paned browsers [41].
 * Human sorting is now used in Album and Paned browsers [190].
 * Windows is now supported (for real this time).
 * foobar2000's broken TXXX:DATE now supported [220].
 * Warnings are now printed for many missing dependencies.
 * Fixes for device backends.
 * Lyric downloading disabled until it can be fixed [273].
 * Editing both key and value with multiple keys fixed (extruded) [393].
 * Plugin changes:

   * AnimOSD: major update (Andreas Bombe, Christine Spang) [387].
   * MusicBrainz: major update.
   * Random Album: Changed algorithm to increase fairness.
   * QLScrobbler: Custom patterns for title and artist.
   * Last.fm Sync: new plugin to sync stats from Last.fm.
   * Notify OSD, Album Art: Minor fixes.

 * Translations:

   * Galician, Spanish (Johám-Luís Miguéns Vila).
   * French (Bastien Gorissen).

2.1.98 [beta] (2010-01-04) - How are you going to convince people to use it?
----------------------------------------------------------------------------

 * Christoph Reiter is now a maintainer.
 * The GStreamer backend is now gapless [49].
 * Win32 is once again supported [248].
 * ID3 tags are removed from FLAC files upon saving [124].
 * File extensions are converted to lowercase upon renaming [66].
 * Thumbnails are now generated for artwork [140].
 * Inline searches in the album list can now match people [239].
 * Embedded album art is now supported in FLAC files [255].
 * Bitrates are now reported in kbps. Library reload required [79].
 * Additional ReplayGain settings (Nick Boultbee) [132].
 * Tag splitting setting is now order-sensitive [74].
 * Paned browser now supports patterns for panes [45].
 * Numeric columns have been given a few tweaks (Johan Hovold) [81].
 * New ratings column options (Johan Hovold, Bastien Gorissen) [82, 83].
 * Renaming when symlinks present no longer raises error (Philipp Weis) [353].
 * Xine backend uses software volume control (Markus Koller) [370].
 * Song positions are now saved and restored when quitting [218].
 * DeviceKit-Disks (UDisks) supported for device discovery [252].
 * Plugin changes:

   * New playlist export plugin [30].
   * New queue only playorder plugin [43].
   * New Python console plugin. [229]
   * Updated trayicon plugin [158].
   * Updated album art plugin (Eduardo Gonzalez) [139].
   * Updated qlscrobbler plugin (Nicholas J. Michalek) [376].
   * Updated lastfmsubmit plugin [292].

 * Translations:

   * Russian (Anton Shestakov) [274].
   * Turkish (Türerkan İnce).
   * German (Rüdiger Arp).

 * Many bug fixes and performance improvements.

2.1 (2009-07-04) - My God, Utahraptor, that's THE PERFECT SOLUTION.
-------------------------------------------------------------------

 * Bug fixes:

   * Installer fixes [15, 27, 88]
   * Right-click on menu causes crash [14]
   * Removing a pane from the paned browser causes segfault [131]
   * Null bytes in tags are now stripped on load [177, 242]
   * zh_CN translation updated [156]

 * Support .oga file extension for Ogg Vorbis files [52]
 * Support libre.fm scrobbling in qlscrobbler plugin
 * Get Internet Radio channel listing from yp.icecast.org [18]
 * Ignore errors during playback for ~#skipcount [37]
 * URIs supported for --play-file and --enqueue [17]
 * Many minor fixes and enhancements.

2.0 (2008-09-14) - Once upon a time there was a radical guy!
------------------------------------------------------------

 * Make Escape a synonym for Ctrl+W in QLTK Windows. (I#8)
 * Actually fix playlist error.
 * Fix Xine backend "Stop" behavior.

1.999 [beta] (2008-09-09) - It has been a memorable day
-------------------------------------------------------

 * Fix playlist error when loading songs.
 * Unlock device when "stop" mmkey is pressed. (Javier Kohen, I#6)
 * Restart song when rewinding and > 0.5s in. (Javier Kohen, I#7)
 * Updated Galician and Spanish translations. (Johám-Luís Miguéns Vila)
 * Make requirements consistent across all documentation.

1.99 [beta] (2008-09-08) - It is impossible to know if my dream came true
-------------------------------------------------------------------------

 * New distutils-based build/test/install system.
 * Multiple audio backend support.

   * Xine-based audio backend.
   * "Null" backend for Ex Falso.

 * Tag Editing:

   * Tags From Path: "<~>" will eat a string but not save it.
   * Track Numbers: Allow numbering up to 999.

 * Show image files in Ex Falso.
 * Direct output to console and to a debugging window.

   * Functions are accessible to plugins as print_d, print_e, and print_w.

 * default_rating configuration option. (Robert Muth)
 * Many bug fixes and performance improvements.

1.0 (2007-05-05) - Yeah they just showed up one day -- staring.
---------------------------------------------------------------

 * Use Mutagen for ASF/WMA and MP4 support.
 * Add IsPlaying and GetPosition to the D-Bus API. (Mickael Royer)
 * Default "No Cover" image. (Jakub Steiner)
 * Add --unfilter to reset browser filters.
 * Sort --enqueued files, and add --unqueue.
 * Basic SPC (SNES ROM audio) support.
 * Paned Browser speed improvements. (Robert Muth)
 * Errors when playing a song are now logged to a special ~errors tag.
   It is visible from the Information screen, and can be reset.
 * APEv2 tags can now override Musepack stream Replay Gain settings.
 * Numerous bug fixes, especially in media device handling.
 * Translation Updates:

   * Hungarian. (SZERVÁC Attila)
   * Finnish. (Jari Rahkonen)
   * Galician and Spanish. (Johám-Luís Miguéns Vila)
   * French. (Guillaume Ayoub)
   * Dutch. (Hans van Dok)
   * Japanese. (Yasushi Iwata)

0.24 (2006-11-19) - One wonders if our conversation today would be an appropriate epitaph.
------------------------------------------------------------------------------------------

 * Media device (iPod and UMS so far) support. (Markus Koller)
 * Delete removes songs from the queue. (sciyoshi)
 * Per-browser window memory.
 * Use Mutagen for WavPack and Musepack support.
 * Keep filenames when given invalid patterns. (Markus Koller)
 * Don't duplicate performers in ~performers. (Martin Bergström)
 * Python 2.5 and GTK+ 2.10 compatibility.
 * Fix Rename Files support on MP4 files.
 * New Romanian translation, by Mugurel Tudor.
 * New Slovak translation, by Lukáš Lalinský.
 * Updated translations:

   * Traditional Chinese, by Hsin-lin Cheng.
   * Japanese, by Yasushi Iwata.
   * Galician and Spanish, by Johám-Luís Miguéns Vila.
   * Finnish, by Jari Rahkonen.
   * Hebrew, by Roee Haimovich.
   * Polish, by Tomasz Torcz
   * French, by Guillaume Ayoub.
   * German, by Rüdiger Arp.

0.23.1 (2006-08-28) - UNPOPULAR LIFE GOALS
------------------------------------------

 * Multivalued tag renaming.
 * Fix crash when ~/.gtk-bookmarks is not present.
 * Disable 'title' completion. (hopefully temporarily)
 * Parse "performer:role" tags and offer a ~performers synthetic tag.
 * Updated Swedish translation, by Erik Christiansson.

0.23 (2006-08-14) - THE NARRATIVE OF LIFE.
------------------------------------------

 * Bug Fixes:

   * Updated files no longer incorrectly appear in the paned browser.
   * Disambiguate 'filename' string for translation.
   * Hide unreadable files in Ex Falso.
   * Avoid (harmless) race condition when filling album list.

 * "Select All Subfolders" menu item when browsing directories.
   (thanks to Alexandre Passos).
 * Scan the library in the background when starting.
 * Ogg FLAC and Speex files can be loaded.
 * Plugin configuration IDs can be different from their names.
 * Rewritten library code, many resulting UI improvements.
 * Scan directories are used as File System roots.
 * Replay Gain mode is chosen based on browser/play order.
 * Internet Radio M3U support.
 * Ex Falso runs on Win32 (thanks to Ben Zeigler).
 * Song list headers can be changed via a context menu.
 * True Audio (TTA) support.
 * New Japanese translation, by Yasushi Iwata.
 * New Traditional Chinese translation, by Hsin-lin Cheng.
 * Updated Translations:

   * German, by Rüdiger Arp.
   * Polish, by Tomasz Torcz
   * French, by Guillaume Ayoub.
   * Galician and Spanish, by Johám-Luís Miguéns Vila and Javier Kohen.
   * Korean, by Byung-Hee HWANG and ChangBom Yoon.
   * Hebrew, by Roee Haimovich.
   * Portuguese, by Alexandre Passos.
   * Dutch, by Hans van Dok.
   * Hungarian, by SZERVÁC Attila.
   * Swedish, by Fredrik Olofsson.

0.22 (2006-07-06) - Man, forget television, books, films, short films, to a lesser extent plays and other theatre, and the remaining popular media!
---------------------------------------------------------------------------------------------------------------------------------------------------

 * The tray icon is now an optional plugin.
 * A D-BUS interface is available. (thanks to Federico Pelloni)
 * Tag editing values are autocompleted.
 * Library Browser windows have more useful titles.
 * New "~lyrics" synthetic tag.
 * Python 2.4 is now required.
 * Updated Translations:

   * Galician and Spanish, by Johám-Luís Miguéns Vila.
   * Italian, by Filippo Pappalardo.
   * Hebrew, by Roee Haimovich.
   * Finnish, by Jari Rahkonen.
   * Dutch, by Hans van Dok.
   * Polish, by Tomasz Torcz
   * Portuguese, by Alexandre Passos.
   * French, by Guillaume Ayoub.
   * Bulgarian, by Rostislav Raykov.
   * Hungarian, by SZERVÁC Attila.
   * Korean, by Byung-Hee HWANG and ChangBom Yoon.

0.21.1 (2006-07-02) - Dude! It's not like you can't just make your own!
-----------------------------------------------------------------------

 * MP3s with POPM can be loaded again (Thanks, Hans van Dok)

0.21 (2006-06-10) - Faith, AND the possibility of weaponized kissing??
----------------------------------------------------------------------

 * Bug Fixes:

   * Queue behaves correctly when randomizing two songs.
   * GStreamer error messages are properly localized.
   * Tray icon is more resiliant to panel crashes.
   * "Jump..." distinguishes between identically-named albums.
   * application/ogg is recognized in audio feeds.
   * .pyo files are removed on clean.
   * util.unexpand caches the value of $HOME.
   * Fix plugin function call ordering.

 * UI Changes:

   * Improved tooltips in Preferences.
   * The Paned Browser shows song totals, and has a button to
     reset all selections.
   * Saving play count / rating tags can be turned off, or adjusted
     to a different email address.
   * The last-entered directory is used for Scan Directories
     configuration.

 * pyvorbis is no longer required if you use Mutagen 1.3.
 * Event plugins were redesigned, incompatibly.
 * Test coverage data can be generated using trace.py.
 * New Simplified Chinese translation by Emfox Zhou.
 * New Hungarian translation by SZERVÁC Attila.
 * Updated translations:

   * Finnish, by Jari Rahkonen.
   * Korean, by Byung-Hee HWANG and ChangBom Yoon.
   * Galician and Spanish, by Johám-Luís Miguéns Vila.
   * Norwegian Bokmål, by Andreas Bertheussen.
   * Italian, by Filippo Pappalardo.
   * Polish, by Tomasz Torcz
   * Lithuanian, by Jonas Slivka.
   * Dutch, by Hans van Dok.

0.20.1 (2006-05-02) - Thanks for the eye-opener, dinosaur zombies!
------------------------------------------------------------------

 * Vorbis/FLAC tag editing works again.

0.20 (2006-05-01) - Feelings are boring. Kissing is awesome!
------------------------------------------------------------

 * Bug Fixes:

   * --play-file will use the queue.
   * Audio Feeds remember download locations.
   * Song changes don't revert tag edits.
   * Browser song activation takes precedence over the queue.
   * Albums drag-and-drop in listed order.
   * Only reset relevant parts of Information windows on song change.
   * Deleting files not in the library removes them.
   * Non-numeric disc/track numbers sort properly.
   * Paned Browser no longer adds incorrect entries. (Debian bug )
   * Ex Falso no longer loads WAV or MOD files.
   * Allow more headers in Internet Radio and Audio Feeds.
   * New process launching method, util.spawn.

 * UI Changes:

   * Indicator to show when songs come from the queue.
   * Rating submenu always appears in the song list.
   * Album covers hide when clicked again.
   * Select current song when jumping to it.

 * New translations:

   * Norwegian Bokmål, by Andreas Bertheussen.
   * Swedish, by Erik Christiansson.

 * Updated translations:

   * Polish, by Tomasz Torcz.
   * Dutch, by Hans van Dok.
   * Finnish, by Jari Rahkonen.
   * French, by Olivier Gambier.
   * Galician and Spanish, by Johám-Luís Miguéns Vila.
   * Hebrew, by Roee Haimovich.
   * Portuguese, by Alexandre Passos.

0.19.1 (2006-04-04) - It's our secret! Our secret IDENTITY!
-----------------------------------------------------------

 * Work around broken Fedora/Mandrive GNOME bindings.
 * Fix global plugin directory scanning.
 * Add originalartist to ~people.
 * Updated Italian translation, by Filippo Pappalardo.
 * Updated Korean translation, by Byung-Hee HWANG and ChangBom Yoon.

0.19 (2006-04-01) - i'm really thirsty you guys
-----------------------------------------------

 * Simple X session management.
 * Require Mutagen 1.0; drops Pymad.
 * WAV support.
 * New plugin types can be enabled/disabled.
 * Album List can search and display any tags.
 * "Bookmark" time offsets within songs.
 * Song menu plugins require minor but incompatible updates.
 * Searches, tagging patterns, and file renaming patterns can be given
   aliases and saved.
 * Tag Editing:

   * MusicBrainz TXXX, artist/album/albumartist support.
   * Added albumartist, originalartist, originalalbum, originaldate,
     recordingdate.
   * Ratings, playcount Ogg Vorbis format changed.
   * COMM tags in Ex Falso are deleted properly.

 * UI Changes:

   * Drops from e.g. Nautilus add to playlists/queue.
   * Clear button in Album List.
   * Horizontal scrollbar when absolutely necessary for the song list.
   * "Random" options use filtered lists.
   * Album sort is once again and forever default.
   * 'Add to Playlist' resorts playlist properly.
   * Enter in 'Add a Tag' moves from tag to value. (Debian bug )
   * Standard context menu for all browsers.
   * 'Delete' key works in Edit Tags.
   * Type-ahead search works in the Album List.

 * Bug fixes:

   * Double-appearances in the filesystem view.
   * FIFO misses some commands.
   * Stupid 'refresh' signal finally gone.
   * Error when seeking and keyboard can't be grabbed.

 * Updated translations:

   * Finnish, by Jari Rahkonen.
   * Galician and Spanish, by Johám-Luís Miguéns Vila.
   * Polish, by Tomasz Torcz.
   * Dutch, by Hans van Dok.
   * German, by Rüdiger Arp.
   * Lithuanian, by Jonas Slivka.
   * Hebrew, by Roee Haimovich.

0.18 (2006-03-03) - "Babies Sporting Monocles"?
-----------------------------------------------

 * MP4 iTunes metadata can be written.
 * Alt+s switches between search entry and song list.
 * GStreamer 0.10 port.
 * Album covers can be switched off in the Album List.
 * The Album List text can be changed with a pattern.
 * "Limit" in the Search view can take ratings into account.
 * UI Changes:

   * Alt+Enter / Ctrl+I shows tags/information for selected songs.
   * DnD to playlists/the queue from the File System view.
   * F2 renames playlists.
   * "Add a Tag" autocompletes tag names.
   * RSS links can be dragged to the Audio Feeds sidebar.

 * Bug Fixes:

   * ID3v1 tags no longer interfere with APEv2 tags.
   * Playing albums with one song no longer skips forwards.
   * 'totaltracks' Vorbis tags are read properly.
   * Adding songs to a playlist doesn't unsort it.
   * "Tags From Path" patterns are no longer greedy. (thanks to
     Decklin Foster)
   * Internet Radio supports the ~people tag.
   * Word-wrap in lyrics pane works properly.
   * Ex Falso properly opens an initial directory. (thanks to ch.trassl)
   * '~format' is usable from --print-playing. ([2810])

 * Plugin errors are captured in a dialog. ([2817])
 * New synthetic numeric tags, ~#tracks and ~#discs. ([2828])
 * Ex Falso no longer depends on GStreamer. ([2837])
 * New Lithuanian translation by Jonas Slivka. ([2780])
 * Updated translations:

   * Bulgarian, by Rostislav Raykov.
   * Finnish, by Jari Rahkonen.
   * Korean, by Byung-Hee HWANG and ChangBom Yoon.
   * Galician and Spanish, by Johám-Luís Miguéns Vila.
   * Hebrew, by Roee Haimovich.
   * German, by Rüdiger Arp.
   * Polish, by Tomasz Torcz.
   * Russian, by Sergey Fedoseev.
   * French, by Joshua Kwan.

0.17.1 (2006-01-19) - I'd like to have some nightmares, please!
---------------------------------------------------------------

 * Updated German translation, by Rüdiger Arp.
 * Updated Russian translation, by Sergey Fedoseev.

0.17 (2006-01-18) - the grizzly icing on the prospector cake!
-------------------------------------------------------------

 * Lyrics plugin merged into Information dialog.
 * "Edit Tags" now correctly removes all copies of multiple values,
   and displays "(missing from...)" for all missing values.
 * More FIFO commands (song list and queue visibility).
 * FLAC support no longer depends on pyflac.
 * Load audio feeds without author information.
 * ~#year, ~year internal tags.
 * Numeric searches are rounded to two decimal places.
 * New plugin architecture for tag editing dialogs.
 * Korean translation, by ChangBom Yoon and Byung-Hee HWANG.
 * Updated translations:

   * Russian, by Sergey Fedoseev.
   * Finnish, by Jari Rahkonen.
   * Portuguese, by Alexandre Passos.
   * Italian, by Filippo Pappalardo.
   * Dutch, by Hans van Dok.
   * Galician, by Johám-Luís Miguéns Vila.
   * French, by Joshua Kwan.
   * Polish, by Tomasz Torcz.

0.16 (2005-12-19) - would it make a difference if it never really came up often?
--------------------------------------------------------------------------------

 * Context menu plugins can make themselves insensitive.
 * More command-line and FIFO options.
 * Read-only M4A support. (thanks to Alexey Bobyakov)
 * Wavpack support.
 * Audio Feed (Podcast) support (requires https://pythonhosted.org/feedparser/).
 * "One Song" (and repeat) play mode.
 * Improved and configurable tray icon.
 * New install system that is more FHS-compliant.
 * ~laststarted internal tag.
 * Accents are stripped when renaming to ASCII filenames.
 * UI improvements:

   * Ex Falso lists are searchable in GTK 2.8.8+.
   * ^W closes transient windows.
   * More DnD support.
   * HIG-compliance for strings.
   * Double-click files in browsers to enqueue them.
   * Rename Files error dialog has a "Continue" button.
   * Ctrl-Left/Right changed to Ctrl-,/..
   * Playlist imports have a progress bar.
   * New icon that is not all black. (thanks to Tobias and Fabien)
   * Paned Browser entries have context menus.
   * Volume icons follow GTK+/GNOME theme.

 * More memory and CPU optimizations.
 * GStreamer error handling. (thanks to Zack Weinberg and Bastian Kleineidam)
 * Musepack, MOD support migrated to Mutagen/ctypes modules.
 * Updated translations:

   * Galician and Spanish, by Johám-Luís Miguéns Vila.
   * Italian, by Filippo Pappalardo.
   * Dutch, by Hans van Dok.
   * Finnish, by Jari Rahkonen.
   * Portuguese, by Alexandre Passos.
   * French, by Joshua Kwan.
   * Polish, by Tomasz Torcz.
   * German, by Rüdiger Arp.
   * Hebrew, by Roee Haimovich.

0.15 (2005-11-14) - Maybe I will.
---------------------------------

 * An 'artist' tag can be stored in the library for MODs.
 * 'All Albums' remains on the album list after a search.
 * The Play Queue displays its total time and has a clear button.
 * Songs can be enqueued multiple times.
 * '~people' includes more people.
 * Files can be added from remote URIs (e.g. HTTP).
 * "Dumb" searches match any visible tags.
 * Ratings are now searched with values of 0.0 to 1.0, and the number of
   visible notes is configurable.
 * Useless columns are not displayed in Internet Radio.
 * A single album cover can be refreshed in the Album List.
 * Playlists have been rewritten:

   * Songs may now be in a playlist multiple times.
   * Playlists can be reordered directly, without a special window.
   * Songs can be added to playlists directly from the context menu.
   * M3U and PLS playlists (along with their songs) can be imported.
   * The interface is much more attractive.

 * Drag-and-drop is generally more usable, faster, and attractive.
 * Many optimizations, especially during startup.
 * Updated translations:

   * Russian, by Sergey Fedoseev.
   * Galician, by Johám-Luís Miguéns Vila.
   * Dutch, by Hans van Dok.
   * French, by Joshua Kwan and Fabien Devaux.
   * Hebrew, by Roee Haimovich.
   * Finnish, by Jari Rahkonen.
   * Polish, by Tomasz Torcz.
   * Italian, by Filippo Pappalardo.

 * New translations:

   * Spanish and Portuguese, by Johám-Luís Miguéns Vila.

0.14 (2005-10-22) - I'm almost certain!
---------------------------------------

 * Internet radio / Shoutcast browser.
 * Album List separates albums with different labelids.
 * Ex Falso displays all available plugins in its menu.
 * Useful ~#lastplayed/~#added/~#mtime display thanks to Lalo Martins.
 * New Album List search keys and sorting options.
 * New translations:

   * Galician, by Johám-Luís Miguéns Vila.
   * Italian, by Filippo Pappalardo.

 * Updated translations:

   * Finnish, by Jari Rahkonen.
   * Polish, by Tomasz Torcz.
   * Dutch, by Hans van Dok.
   * Hebrew, by Roee Haimovich.
   * German, by Rüdiger Arp.
   * Russian, by Nikolai Prokoschenko.

 * Many bug fixes.

0.13.1 (2005-09-15) - People will fall for this for sure!
---------------------------------------------------------

 * Fix playlist creation.
 * Unplay when no song is playing.

0.13 (2005-09-11) - So, um... let's- fletcherize?
-------------------------------------------------

 * The GStreamer backend is cleaned up, and is now the only backend.
   This results in lower background CPU usage and many fixes to
   our audio processing. Gapless playback is gone.
 * A play queue was added.
 * A file system browser has been added. This can view, edit, and play
   files outside of your library.
 * The Paned Browser has a search entry.
 * Search Library lets you limit the number of results.
 * ``~/.quodlibet/browsers`` is now scanned for custom browsers.
 * Synthetic tags ('''~dirname''', '''~basename''', &c.) can be searched.
 * Similarly, synthetic tags can be used in the Paned Browser.
 * New synthetic tags, '''~people''' and '''~playlist'''.
 * If the tray icon is visible, closing QL's main window will minimize it.
   To actually quit, choose '''Quit''' from the Music menu or icon.
 * Search Library and the Album List search entry have tag completion.
 * Ex Falso supports plugins.
 * Updated Russian translation by Nikolai Prokoschenko and Sergey Fedoseev.
 * Updated French translation by Joshua Kwan.
 * Updated Finnish translation by Jari Rahkonen.
 * Updated Dutch translation by Hans van Dok.
 * Updated Hebrew translation by Roee Haimovich.

0.12 (2005-07-31) - focus ENTIRELY on the sexy bits.
----------------------------------------------------

 * New Mutagen ID3 reader/writer.
 * Experimental GStreamer backend.
 * Drag-and-drop to playlists.
 * Weighted random playback.
 * MP3 and Musepack ReplayGain support.
 * Larger plugin manager window.
 * Automatic mount point detection.
 * Support for multiple soundcards.
 * Localization enhancements.
 * Translation updates:

   * Dutch, thanks to Hans van Dok.
   * Finnish, thanks to Jari Rahkonen.
   * French, thanks to Joshua Kwan.
   * German, thanks to Rüdiger Arp.
   * Hebrew, thanks to Roee Haimovich.
   * Russian, thanks to Sergey Fedoseev and Nikolai Prokoschenko.
   * Polish, thanks to Witold Kieraś.

 * The usual round of interface tweaks and bug fixes.

0.11 (2005-05-10) - spicy burnsauce with a side of ZING!
--------------------------------------------------------

 * Plugins (either appearing in the right-click menu, or triggered on a
   player event)
 * Browse songs by album, with a cover display.
 * "Library Browser" added to search/edit files without disturbing your
   playlist.
 * Played songs are automatically removed from dynamic playlists.
 * "Background filters" for the paned browser and search entry.
 * Create/remove empty folders from within Ex Falso.
 * '0' to '4' keys or mouse clicks can set song ratings.
 * Depends on PyGTK 2.6 (as well as GTK 2.6).
 * --status to print the player's status.
 * Russian translation, thanks to Sergey and Andrey Fedoseev.
 * Partial French translation, thanks to Joshua Kwan.
 * OSD moved to a plugin.

0.10.1 (2005-04-04) - What if I said I'm not really kidding?
------------------------------------------------------------

 * The main window stays hidden when the song changes.

0.10 (2005-04-02) - As it turns out, my life is NOT THAT INTERESTING!
---------------------------------------------------------------------

 * --seek supports +/- prefix to seek relative to the current position.
 * Added Ex Falso, a tag editor based on QL (without audio playback).
 * Switched MP3 genres from TIT1 to TCON.
 * The library is saved automatically every 15 minutes.
 * Tag by Pattern/Rename Files save patterns used.
 * Adding tags with specific formats ('date') is less prone to error.
 * Several display bugs and non-HIG windows were fixed.
 * Pane-based (Rhythmbox/iTunes-style) library browser.
 * Tag by Pattern/Rename Files previews can be manually edited before saving.
 * Kind of browser (none, search, playlists, paned), song list sort order,
   and what you were browsing are remembered when you exit.
 * At least one lockup-causing bug was fixed.
 * Song ratings, on a 0 to 4 scale.
 * Masked directories work again.
 * No more dependency on Glade.
 * A new icon and website.

0.9 (2005-03-04) - I don't want any trouble, cephalopods!
---------------------------------------------------------

 * Major updates to the Properties dialog:

   - A new detailed 'Information' tab was added.
   - Middle click pastes current PRIMARY clipboard text in 'Edit Tags'.
   - Text in the 'Rename Files' dialog can be conditionalized.

 * Non-UTF-8 filesystem encodings support (via CHARSET/G_BROKEN_FILENAMES).
 * New numeric keys "added" and "skipcount" can be searched on.
 * The --print-playing format string syntax has changed to match the one
   now used in 'Rename Files'.
 * New query language enhancements (ternary relation operators, string
   comparisons, and Lynx-like case-sensitivity).
 * The tray icon now pauses/unpauses on middle click, adjusts volume with
   the scroll wheel, and skips forward/backward on buttons 6/7.
 * This release depends on GTK 2.6 for its new media icons.
 * PMP support was removed.
 * Updated German translation (thanks, Bastian!)

0.8.1 (2005-02-06) - Our story takes a sudden dive...
-----------------------------------------------------

 * Fix a crash when encoding information is not available.

0.8 (2005-02-04) - I make jokes about whomever I please!
--------------------------------------------------------

 * New/reloaded libraries take 20% less disk space.
 * Double-clicking an album cover displays it in a larger window.
 * --shuffle, --repeat, and --volume (--volume-up and --volume-down are
   deprecated and will be removed).
 * Any tag name can be written to (and read from) an MP3 file.
 * Playlists containing arbitrary songs can be created.
 * The libmodplug Python wrapper must be downloaded separately.
 * The MPC/MP+ format is supported (with a separate wrapper).
 * FLAC supports ReplayGain.
 * Internal changes made some things faster and others slower.
 * Polish translation, thanks to Michal Nowikowski.
 * German translation, thanks to Bastian Kleineidam.

0.7 (2004-12-18) - I'm going to ho-ho-hoard all these nuts!
------------------------------------------------------------

 * Default to proper 'alsa09' driver (rather than 'alsa').
 * "Random Foo" searches are now anchored with ^...$.
 * Tag By Pattern values can be edited before being saved.
 * Right-clicking on the status icon brings up a menu.
 * --play, --pause, --seek-to, --query, --play-file.
 * OSD (gosd) support, thanks to Iñigo Serna and Gustavo J. A. M. Carneiro.
   A library reload is needed to use it.
 * FreeDesktop-style .folder.png files supported for album covers.
 * Playlist/search UI elements can be hidden.
 * Dragging playlist columns reorders them.
 * Library rebuilds no longer lose play counts.
 * Configurable menu accelerators when gtk-can-change-accels is set.
 * Delete songs (or move them to the trash) from the player.

0.6 (204-12-02) - People laugh at typos in heaven?!
---------------------------------------------------

 * Many new filtering options (top 40, not played in X days).
 * Mass-set track numbers.
 * Tag by Pattern can replace or add new tags.
 * Maskable mount points. This lets you add files from an NFS share or
   portable device and not have to readd them if you unmount and remount it.
 * Support for sending files to PMPs from the context menu.
 * --next, --previous, --play-pause, --volume-up, --volume-down.
 * MOD/IT/XM/etc. support, using libmodplug and an included C extension.
 * Right-clicking the status icon will pause/unpause.
 * Seeking in FLACs.
 * Bug fixes (including at least one crash).

0.5 (2004-11-18) - Everything's fine, CEPT YOU GOT NO LEGS!
-----------------------------------------------------------

 * The ao audio backend is back; see the "AUDIO BACKENDS" section in the
   manual page for instructions on using it. This should let ALSA users
   use software mixing.
 * ID3 APIC (embedded picture) support.
 * VorbisGain (https://sjeng.org/vorbisgain.html) support.
 * A context menu for common operations was added to the properties dialog.
 * Tag values can be set from filename patterns, or vice-versa.
 * Dates can be saved in MP3s now.
 * --print-playing option, with a format string.
 * More UI tweaks.
 * Translation template update.
 * Many bug fixes; please reload your library. You can now reload your
   library from the "Music" menu.

0.4 (2004-11-09) - The Power of Language
----------------------------------------

 * Many bug fixes, primarily due to unit testing.
 * Tweaks to cover detection to pick 'frontcover' over 'backcover'.
 * Tweaks to song display, including proper support for the 'author' tag.
 * Remember size between invocations.
 * A freedesktop.org-compatible system tray icon, using the Egg status
   icon code by Anders Carlsson and Sun.
 * Multimedia key support, provided they're mapped (e.g. by Acme), using
   the MmKeys object from Muine by Lee Willis and Jan Arne Petersen.
 * UI tweaks to the main window.
 * Button to link to a song's website, or a Google search.
 * Infrastructure is in place for i18n/l10n, but I'm totally new to
   this, so I could've done something horribly wrong.

0.3 (2004-11-01)
----------------

 * Handle mono MP3s correctly.
 * Crash less, especially when editing tags.
 * Many smaller bug fixes.

0.2 (2004-10-30)
----------------

 * Song properties dialog, featuring mass tag editing/addition/removal.
 * Build/installation scripts.
 * Interface tweaks for HIG compliance and accessibility.
 * Try to save the library when ^C is pressed.
 * ~/.quodlibet/current interface to currently-playing song.
 * Save current query and song on exit.
 * An icon.
 * FLAC support. Writing to FLAC tags could be *very* buggy, so if you
   value your tags, please back them up.

0.1 (2004-10-30)
----------------

 * Initial release.
