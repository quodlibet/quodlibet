=====================
Maintainer Guidelines
=====================


Downstream Bug Trackers
-----------------------

Some bug reports never make it to us so check these once in a while.

* `Fedora <https://apps.fedoraproject.org/packages/quodlibet/bugs>`_
* `Debian <https://bugs.debian.org/cgi-bin/pkgreport.cgi?pkg=quodlibet>`_
* `Arch Linux <https://bugs.archlinux.org/?project=1&string=quodlibet>`_
* `Ubuntu <https://launchpad.net/ubuntu/+source/quodlibet/+bugs>`_
* `Gentoo <https://bugs.gentoo.org/buglist.cgi?quicksearch=media-sound%2Fquodlibet>`_


Tags & Branches
---------------

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
-----------------

New stable branch
^^^^^^^^^^^^^^^^^

* ``git checkout -b quodlibet-x.y``
* ``git commit -m "new stable branch"``
* ``git push``
* ``git checkout master``
* Update version in ``const.py`` to ``(X, Y + 1, -1)``
* ``git commit -m "version bump"``

New stable release
^^^^^^^^^^^^^^^^^^

* ``git checkout quodlibet-x.y``
* Cherry-pick stuff from default branch
* Grab title from `Daily Dinosaur Comics <http://www.qwantz.com/>`_
* Update :ref:`News` with a list of all bugfixes and features since last release
* ``git commit -m "update NEWS"``
* ``setup.py distcheck``
* Update version to ``(X, Y, Z)`` in ``const.py``
* Update version to ``(X, Y, Z)`` in ``appdata.xml.in``
* ``git commit -m "release prep"``
* ``git tag release-x.y.z``
* ``git push origin release-x.y.z``
* Update version to ``(X, Y, Z, -1)``
* ``git commit -m "version bump"``
* Cherry-pick ``NEWS`` commit onto default branch
* Create Windows builds / tarballs / macOS DMGs
* Create checksums / signature, attach everything to the github tag
* Update ``release_db/make.py``; run ``./release_db/update.sh``
* Update stable PPAs (ubuntu/debian/OBS)
* Update the flathub repo
* Announce on IRC / Discord / Twitter etc
