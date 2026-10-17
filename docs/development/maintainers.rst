=====================
Maintainer Guidelines
=====================


Downstream Bug Trackers
=======================

Some bug reports never make it to us so check these once in a while.

* `Fedora <https://bugzilla.redhat.com/buglist.cgi?component=quodlibet&query_format=advanced&product=Fedora&bug_status=NEW&bug_status=ASSIGNED&bug_status=REOPENED>`_
* `Debian <https://bugs.debian.org/cgi-bin/pkgreport.cgi?pkg=quodlibet>`_
* `Arch Linux <https://bugs.archlinux.org/?project=1&string=quodlibet>`_
* `Ubuntu <https://launchpad.net/ubuntu/+source/quodlibet/+bugs>`_
* `Gentoo <https://bugs.gentoo.org/buglist.cgi?quicksearch=media-sound%2Fquodlibet>`_


Tags & Branches
===============

At the point where no more functionality will be added to a release,
a new branch gets created.
All bug fixes pushed to the default branch should
be cherry-picked to the respective stable branches and vice versa.

::

      .       .
     /|\     /|\
      |       |
      |       |
    3.6.-1   /   <--- "quodlibet-3.5" branch
      |_____/  .
      |       /|\
      |        |
      |      3.4.1  <--- "release-3.4.1" tag
      |        |
      |      3.4.0.-1
      |        |
      |      3.4  <--- "release-3.4.0" tag
      |        |
    3.5.-1    /
      |______/   <--- "quodlibet-3.4" branch
      |
      |  <--- default branch
    3.4.-1
      |
     /|\


Release Checklist
=================

New stable branch
-----------------

You can now use the ``dev-utils/new-branch.sh`` script to help do this.

New stable release
------------------

First, check out the branch (``git checkout quodlibet-x.y``), then

On the branch
^^^^^^^^^^^^^

* Cherry-pick stuff from default branch
* Grab a title from `Daily Dinosaur Comics <https://qwantz.com/archive.php/>`_
* Update :ref:`News` with a list of all bugfixes and features since last release
* ``git commit -m "update NEWS"``
* TODO: Set the version: ``dev-utils/set-version.sh X.Y.Z``
  (``pyproject.toml``, ``const.py`` and ``appdata.xml.in`` files)
* ``git commit -m "release prep"``
* ``git tag release-x.y.z``
* ``git push origin release-x.y.z``

The tag push then runs the ``release`` workflow, which:

* TODO: checks the tag matches the version in the source
* builds the source dist, Windows installer and portable build, and macOS DMG
* TODO: adds a ``.sha256`` for each (sdist only so far)
* creates a **draft** `GitHub release <https://github.com/quodlibet/quodlibet/releases/>`_
  with all of them attached

Then:

* TODO: decide how to sign the artifacts.
  Until then: ``gpg -b quodlibet-x.y.z.tar.gz`` etc., and attach the ``.sig`` files
* Check the draft, and publish it


On default branch
^^^^^^^^^^^^^^^^^

* TODO: Set the next version: ``dev-utils/set-version.sh X.Y.Z-pre``
* ``git commit -m "version bump"``
* Cherry-pick ``NEWS`` commit


External
--------

Publishing the release then:

* TODO: updates the website appcast from the GitHub releases.
  Until then: update ``release_db/make.py`` and run ``./release_db/update.sh``
* TODO: opens a PR on the `Flathub repo <https://github.com/flathub/io.github.quodlibet.QuodLibet/>`_
* TODO: triggers the stable PPAs (ubuntu/debian/OBS)

Finally, announce on IRC / Discord / Mastodon etc.
