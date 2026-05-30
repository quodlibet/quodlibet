{
  description = "Development Flake for Quod Libet";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
    flake-parts.url = "github:hercules-ci/flake-parts";
    treefmt-nix.url = "github:numtide/treefmt-nix";
  };
  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        inputs.treefmt-nix.flakeModule
      ];

      systems = [
        # systems for which you want to build the `perSystem` attributes
        "x86_64-linux"
        "aarch64-darwin"
      ];
      perSystem =
        { pkgs, ... }:
        let
          # 3.11 is now too far against the tide here to be worth it
          qlPython = pkgs.python312;
          qlPoetry = pkgs.poetry.override { python3 = qlPython; };
        in
        {
          treefmt = {
            # Used to find the project root
            projectRootFile = "flake.nix";

            programs = {
              nixfmt.enable = pkgs.lib.meta.availableOn pkgs.stdenv.buildPlatform pkgs.nixfmt-rfc-style.compiler;

              nixfmt.package = pkgs.nixfmt-rfc-style;
              shellcheck.enable = true;
              shfmt.enable = true;
              # TODO: migrate on next release (https://github.com/numtide/treefmt-nix/pull/443)
              # shfmt.useEditorConfig = true;
              shfmt.indent_size = 4;
              statix.enable = true;
              deadnix.enable = true;
              prettier.enable = true;
              taplo.enable = true;
            };
            settings = {
              global.excludes = [
                "*.lock"
                "*.rst"
                "*.md"
                "*.png"
                "*.po"
                "*.mp3"
                # Handled within Python venv tooling
                "*.py"
              ];
              formatter = {
                # Doesn't support setext headers amongst other things
                prettier.excludes = [ "*.md" ];
                shellcheck = {
                  excludes = [
                    ".envrc"
                    "quodlibet.bash"
                  ];
                };
              };
            };
          };
          devShells.default =
            with pkgs;
            mkShell {
              POETRY_VIRTUALENV_CREATE = 1;
              # GI typelib loader needs these libs on LD_LIBRARY_PATH to resolve symbols
              LD_LIBRARY_PATH = lib.makeLibraryPath [
                glib.out
                gtk4
                pango.out
                fontconfig.lib
                cairo
                gdk-pixbuf
                librsvg
              ];
              GIO_MODULE_DIR = "${glib-networking}/lib/gio/modules/";
              packages = [
                qlPoetry
                qlPython
                adwaita-icon-theme
                cairo
                fontconfig
                file
                gdk-pixbuf
                glib
                glib-networking
                glibcLocales
                gobject-introspection
                gtk4
                gtksourceview5
                kakasi
                # keybinder3 and libappindicator are GTK3-only
                libmodplug
                libnotify
                librsvg
                libsoup_3
                pcre2
                shared-mime-info
                pkg-config
              ]
              ++ lib.optionals stdenv.isLinux [
                libappindicator-gtk3
                xorg.xvfb
              ]
              ++ (with gst_all_1; [
                gstreamer
                gst-plugins-bad
                gst-plugins-base
                gst-plugins-good
                gst-plugins-ugly
                gst-libav
              ]);
            };
        };
    };
}
