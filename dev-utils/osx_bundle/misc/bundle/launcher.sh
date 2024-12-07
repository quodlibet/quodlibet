#!/bin/bash

bundle=$(
    cd "$(dirname "$(dirname "$(dirname "$0")")")" || exit
    pwd
)
bundle_contents="$bundle"/Contents
bundle_res="$bundle_contents"/Resources
bundle_lib="$bundle_res"/lib
bundle_bin="$bundle_res"/bin
bundle_data="$bundle_res"/share
bundle_etc="$bundle_res"/etc

export DYLD_LIBRARY_PATH="$bundle_lib":"$bundle_lib/pulseaudio"

export XDG_CONFIG_DIRS="$bundle_etc"/xdg
export XDG_DATA_DIRS="$bundle_data"

export CHARSETALIASDIR="$bundle_lib"

export GTK_DATA_PREFIX="$bundle_res"
export GTK_EXE_PREFIX="$bundle_res"
export GTK_PATH="$bundle_res"
export GTK_IM_MODULE_FILE="$bundle_etc/gtk-3.0/gtk.immodules"

# comment following line and you won't see the quodlibet icon in the about dialog
export GDK_PIXBUF_MODULE_FILE="$bundle_lib/gdk-pixbuf-2.0/2.10.0/loaders.cache"

# gobject-introspection
export GI_TYPELIB_PATH="$bundle_lib/girepository-1.0"

# gstreamer
export GST_PLUGIN_SYSTEM_PATH="$bundle_lib/gstreamer-1.0"
export GST_PLUGIN_SCANNER="$bundle_contents/MacOS/gst-plugin-scanner"

# Strip out the argument added by the OS.
if /bin/expr "x$1" : '^x-psn_' >/dev/null; then
    shift 1
fi

#Set $PYTHON to point inside the bundle
PYTHON=$(echo "$bundle_contents/MacOS/python"*)
PYTHONHOME="$bundle_res"
export PYTHON PYTHONHOME

export GIO_MODULE_DIR="$bundle_lib/gio/modules"

# GTLS_SYSTEM_CA_FILE sets the path in the gnutls backend of glib-networking
# (the env var gets respected because we patch it.. not available upstream)
GTLS_SYSTEM_CA_FILE=$(echo "$bundle_lib/python"*"/site-packages/certifi/cacert.pem")
export GTLS_SYSTEM_CA_FILE
# Same for OpenSSL
export SSL_CERT_FILE="$GTLS_SYSTEM_CA_FILE"

# temporary disable tooltips
export QUODLIBET_NO_HINTS=yes

# select target based on our basename
# Beginning in MacOS 14.0, if the executable pointed to by an app's Info.plist
# is a symbolic link to a script, Finder passes the path of the script as
# $0, not the path of the symbolic link.  As a workaround, hardwire "quodlibet"
# as the app name.
APP=$(basename "$0")
if [ "$APP" = "_launcher" ]; then
    APP="quodlibet"
fi
if [ "$APP" = "run" ]; then
    "$PYTHON" "$@"
elif [ "$APP" = "gst-plugin-scanner" ]; then
    # Starting with 10.11 OSX will no longer pass DYLD_LIBRARY_PATH
    # to child processes. To work around use this launcher for the
    # GStreamer plugin scanner helper
    "$bundle_res/libexec/gstreamer-1.0/gst-plugin-scanner" "$@"
else
    "$PYTHON" "$bundle_bin/$APP" "$@"
fi
