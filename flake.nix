{
  description = "Development Flake for Quod Libet";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-23.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      qlPython = pkgs.python310;
      qlPoetry = pkgs.poetry.override {python3 = qlPython;};
    in {
      # A shell for `nix develop`
      devShells.default = pkgs.mkShell {
        packages = [
          qlPython
          qlPoetry

          # See https://github.com/NixOS/nixpkgs/blob/nixos-23.05/pkgs/applications/audio/quodlibet/default.nix

          # build time
          pkgs.gettext
          pkgs.gobject-introspection
          pkgs.wrapGAppsHook

          ## runtime
          pkgs.gnome.adwaita-icon-theme  # Note new name
          pkgs.gdk-pixbuf
          pkgs.glib
          pkgs.glib-networking
          pkgs.gtk3
          pkgs.gtksourceview
          pkgs.kakasi
          pkgs.keybinder3
          pkgs.libappindicator-gtk3
          pkgs.libmodplug
          pkgs.librsvg
          pkgs.libsoup_3
          pkgs.webkitgtk

          # tests
          pkgs.dbus
          pkgs.glibcLocales
          pkgs.hicolor-icon-theme
          pkgs.xvfb-run

          # Linters etc
          pkgs.shellcheck
          pkgs.alejandra
        ];
      };

      # Allow `nix fmt` to "just work"
      formatter = pkgs.alejandra;

      # Nix run .#foo
      apps = {
        poetry = flake-utils.lib.mkApp {drv = qlPoetry;};
      };

      # Allow `nix flake check` to "just work"
      checks = {
        shellcheck =
          pkgs.runCommand
          "shellcheck"
          {buildInputs = [pkgs.shellcheck];}
          ''
            find ${./.} -iname "*.sh" -exec shellcheck {} \+
            # We *must* create some output
            mkdir -p "$out"
          '';
      };
    });
}
