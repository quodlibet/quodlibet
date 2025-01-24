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

On the branch
^^^^^^^^^^^^^

* ``git checkout quodlibet-x.y``
* Cherry-pick stuff from default branch
* Grab a title from `Daily Dinosaur Comics <http://www.qwantz.com/>`_
* Update :ref:`News` with a list of all bugfixes and features since last release
* ``git commit -m "update NEWS"``
* Create a source dist: ``git clean && poetry run ./setup.py distcheck``
* Update version to ``(X, Y, Z)`` in ``const.py``
* Update version to ``(X, Y, Z)`` in ``appdata.xml.in``
* ``git commit -m "release prep"``
* ``git tag release-x.y.z``
* ``git push origin release-x.y.z``
* `Create Windows builds <https://github.com/quodlibet/quodlibet/tree/main/dev-utils/win_installer#creating-an-installer>`_
* `Create macOS DMGs <https://github.com/quodlibet/quodlibet/tree/main/dev-utils/osx_bundle#creating-a-bundle>`_
* Create checksums: ``sha256sum dist/quodlibet-x.y.z.tar.gz``
* Create PGP signature: ``gpg -b dist/quodlibet-x.y.z.tar.gz``
* Attach everything to the `Github release <https://github.com/quodlibet/quodlibet/releases/>`_ tag.


On default branch
^^^^^^^^^^^^^^^^^

* Update version to ``(X, Y, Z, -1)``
* ``git commit -m "version bump"``
* Cherry-pick ``NEWS`` commit
* Update ``release_db/make.py``; run ``./release_db/update.sh``


External
--------

* Update stable PPAs (ubuntu/debian/OBS)
* Make a PR on the `Flathub repo <https://github.com/flathub/io.github.quodlibet.QuodLibet/>`_
* Announce on IRC / Discord / Mastodon etc
