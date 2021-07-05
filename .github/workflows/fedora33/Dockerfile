FROM fedora:33

# DNF dependencies required before poetry can install virtualenv dependencies
RUN dnf -y install \
      poetry \
      cairo-devel \
      gcc \
      python3-devel \
      dbus-devel \
      gobject-introspection-devel \
      cairo-gobject-devel

# Dependencies for tests
RUN dnf -y install \
      Xvfb \
      # Contains 'GdkPixbuf' namespace (used by 'gi') \
      gtk3 \
      # Contains 'Gst' module \
      gstreamer1 \
      # Contains GStreamer replaygain plugin \
      gstreamer1-plugins-good \
      # SVG support (for 'Timage_support.test_create_pixbuf' test) \
      librsvg2 \
      dbus-x11

RUN dnf clean all

# required for translation tests that use 'gettext'
ENV LANG C.UTF-8

# run tests
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
