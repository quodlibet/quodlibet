# Flatpak packaging for Quod Libet

Add the Flathub repository and install the necessary SDK:

	$ make setup

To build the package, run:

    $ make BUILD=/path/to/build/dir

This builds both the Flatpak repo (in `<build>/repo`) and the bundles in
`dist/`. To install the package from the build repo:

    $ flatpak remote-add --no-gpg-verify --if-not-exists build /path/to/build/dir/repo
    $ flatpak install build io.github.quodlibet.QuodLibet

## Updating the Python dependencies
Run

    $ make python-modules

to re-generate the modules for the Python dependencies. The generated files
(`python-*-depends.json`) are kept in Git, so this target only needs to be built
after changing the list of dependencies or to update the versions.
