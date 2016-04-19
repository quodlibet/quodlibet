=====================
Maintainer Guidelines
=====================


Downstream Bug Trackers
-----------------------

Some bug reports never make it to us so check these once in a while.

  * `Fedora <https://apps.fedoraproject.org/packages/quodlibet/bugs>`_
  * `Debian <http://bugs.debian.org/cgi-bin/pkgreport.cgi?pkg=quodlibet>`_
  * `Arch Linux <https://bugs.archlinux.org/?project=1&string=quodlibet>`_
  * `Ubuntu <https://launchpad.net/ubuntu/+source/quodlibet/+bugs>`_
  * `Gentoo <https://bugs.gentoo.org/buglist.cgi?quicksearch=media-sound%2Fquodlibet>`_


Tags & Branches
---------------

At the point where no more functionality will be added to a release, a
new branch gets created. All bug fixes pushed to the master branch should
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
      |  <--- "master" branch
    3.4.-1
      |
     /|\


Release Checklist
-----------------

New Stable branch:

    * setup.py update_po
    * commit
    * branch quodlibet-x.y
    * checkout quodlibet-x.y
    * change branch name in const.py, commit
    * checkout master
    * version bump

New Stable release:

    * checkout quodlibet-x.y
    * cherry pick stuff from master
    * update NEWS, commit
    * test OSX/Windows/Ubuntu/Buildbots
    * setup.py distcheck
    * setup.py update_po, update version to (X, Y, Z), commit "release prep"
    * add tag "release-x.y.z"
    * push tag
    * update version to (X, Y, Z, -1), commit "version bump"
    * cherry pick NEWS commit onto master
    * create Windows builds; Create tarballs
    * create checksums / signature, upload everything
    * update downloads page on master
    * write release mail
    * update stable PPAs (ubuntu/debian/OBS)
