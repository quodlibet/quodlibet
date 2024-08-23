FROM fedora:39

RUN dnf -y install \
      poetry \
      cairo-devel \
      gcc \
      python3-devel \
      dbus-devel \
      gobject-introspection-devel \
      cairo-gobject-devel \
      libsoup3 \
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

# Create user (required for write access tests in 'tests/test_formats__audio.py' to pass)
ARG HOST_USER_ID=5555
ENV HOST_USER_ID ${HOST_USER_ID}
RUN useradd -u $HOST_USER_ID -ms /bin/bash user

# Required to prevent pytest from running into permissions errors when creating
# cache files in GITHUB_WORKSPACE as 'user'
ENV PYTHONDONTWRITEBYTECODE 1

# required for translation tests that use 'gettext'
ENV LANG C.UTF-8

# run tests
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
