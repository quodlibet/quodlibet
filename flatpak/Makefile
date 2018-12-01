CORE_DEPENDS := \
	mutagen \
	sgmllib3k \
	feedparser
PLUGINS_DEPENDS := \
	pyinotify \
	musicbrainzngs \
	dbus-python \
	paho-mqtt

APP_ID := io.github.quodlibet.QuodLibet

BUILD := build
DIST := dist
REPO := $(BUILD)/repo

all: $(REPO) dist-flatpaks

install: $(BUILD)/$(APP_ID).flatpak
	flatpak install $(BUILD)/$(APP_ID).flatpak

$(REPO): *.yaml
	flatpak-builder --force-clean --repo=$@ $(BUILD)/build --state-dir=$(BUILD)/.flatpak-builder $(APP_ID).yaml
	flatpak build-update-repo $(REPO)

$(BUILD)/$(APP_ID).flatpak: $(REPO)
	flatpak build-bundle $(REPO) $@ $(APP_ID)

$(BUILD)/$(APP_ID).Locale.flatpak: $(REPO)
	flatpak build-bundle $(REPO) $@ $(APP_ID).Locale --runtime

$(DIST):
	mkdir -p $(DIST)

$(DIST)/%.flatpak: $(BUILD)/%.flatpak $(DIST)
	cp $< $@

dist-flatpaks: $(DIST)/$(APP_ID).flatpak $(DIST)/$(APP_ID).Locale.flatpak

python-modules:
	python3 flatpak-builder-tools/pip/flatpak-pip-generator \
		--cleanup=scripts \
		--output=python-modules.json \
		$(CORE_DEPENDS) \
		$(PLUGINS_DEPENDS)
	python3 flatpak-builder-tools/flatpak-json2yaml.py python-modules.json -o python-modules.yaml && rm python-modules.json

setup:
	flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
	flatpak install flathub org.gnome.Sdk//3.30
	flatpak install flathub org.gnome.Platform//3.30
