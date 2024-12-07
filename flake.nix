{
  description = "Development Flake for Quod Libet";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.11";
    flake-parts.url = "github:hercules-ci/flake-parts";
    treefmt-nix.url = "github:numtide/treefmt-nix";
  };
  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        inputs.treefmt-nix.flakeModule
      ];

      flake = {
        # Put your original flake attributes here.
      };
      systems = [
        # systems for which you want to build the `perSystem` attributes
        "x86_64-linux"
        "aarch64-darwin"
      ];
      perSystem =
        { pkgs, ... }:
        let
          # 3.10 is now too far against the tide here to be worth it
          qlPython = pkgs.python311;
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
              # Respect editorconfig
              shfmt.indent_size = null;
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
            pkgs.mkShell {
              POETRY_VIRTUALENV_CREATE = 1;
              packages =
                [
                  qlPoetry
                  qlPython
                  adwaita-icon-theme
                  cairo
                  file
                  gdk-pixbuf
                  glib
                  glib-networking
                  glibcLocales
                  gobject-introspection
                  gtk3
                  libcanberra-gtk3
                  libappindicator-gtk3
                  libmodplug
                  libsoup_3
                  shared-mime-info
                  webkitgtk_4_0
                  xvfb-run
                ]
                ++ (with gst_all_1; [
                  gstreamer
                  gst-plugins-bad
                  gst-plugins-good
                  gst-plugins-ugly
                  gst-plugins-base
                  gstreamer
                  gst-libav
                ]);
            };
        };
    };
}
