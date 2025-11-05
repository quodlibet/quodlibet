CORE_DEPENDS := \
	mutagen \
	sgmllib3k \
	feedparser
PLUGINS_DEPENDS := \
	musicbrainzngs \
	dbus-python \
	pypresence \
	regex \
	soco \
	paho-mqtt

QL_ID := io.github.quodlibet.QuodLibet
EF_ID := io.github.quodlibet.ExFalso

BUILD := build
DIST := dist
REPO := $(BUILD)/repo

all: $(REPO) dist-flatpaks

install: $(BUILD)/$(QL_ID).flatpak $(BUILD)/$(EF_ID).flatpak
	flatpak install --reinstall --assumeyes $(BUILD)/$(QL_ID).flatpak
	flatpak install --reinstall --assumeyes $(BUILD)/$(EF_ID).flatpak

$(REPO): *.yaml
	flatpak-builder --force-clean --repo=$@ $(BUILD)/build --state-dir=$(BUILD)/.flatpak-builder $(QL_ID).yaml
	flatpak-builder --force-clean --repo=$@ $(BUILD)/build --state-dir=$(BUILD)/.flatpak-builder $(EF_ID).yaml
	flatpak build-update-repo $(REPO)

$(BUILD)/$(QL_ID).flatpak: $(REPO)
	flatpak build-bundle $(REPO) $@ $(QL_ID)

$(BUILD)/$(EF_ID).flatpak: $(REPO)
	flatpak build-bundle $(REPO) $@ $(EF_ID)

$(BUILD)/$(QL_ID).Locale.flatpak: $(REPO)
	flatpak build-bundle $(REPO) $@ $(QL_ID).Locale --runtime

$(BUILD)/$(EF_ID).Locale.flatpak: $(REPO)
	flatpak build-bundle $(REPO) $@ $(EF_ID).Locale --runtime

$(DIST):
	mkdir -p $(DIST)

$(DIST)/%.flatpak: $(BUILD)/%.flatpak $(DIST)
	cp $< $@

dist-flatpaks: $(DIST)/$(QL_ID).flatpak $(DIST)/$(QL_ID).Locale.flatpak $(DIST)/$(EF_ID).flatpak $(DIST)/$(EF_ID).Locale.flatpak

python-modules:
	python3 flatpak-builder-tools/pip/flatpak-pip-generator \
		--cleanup=scripts \
		--output=python-modules.json \
		$(CORE_DEPENDS) \
		$(PLUGINS_DEPENDS)
	python3 flatpak-builder-tools/flatpak-json2yaml.py python-modules.json -o python-modules.yaml && rm python-modules.json

setup:
	flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
	flatpak install flathub org.gnome.Sdk//3.34
	flatpak install flathub org.gnome.Platform//3.34
