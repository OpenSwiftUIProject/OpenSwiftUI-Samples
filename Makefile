.DEFAULT_GOAL := macOS_run

SAMPLE ?= HelloWorld
CONFIGURATION ?= Debug
SAMPLES := $(sort $(patsubst Samples/%/Project.swift,%,$(wildcard Samples/*/Project.swift)))
SIGNING_OPTIONS = $(if $(strip $(DEVELOPMENT_TEAM)),-allowProvisioningUpdates CODE_SIGN_STYLE=Automatic DEVELOPMENT_TEAM="$(DEVELOPMENT_TEAM)")

ifneq ($(words $(SAMPLE)),1)
$(error Select one SAMPLE from: $(SAMPLES).)
endif
ifeq ($(filter $(SAMPLES),$(SAMPLE)),)
$(error Unknown SAMPLE '$(SAMPLE)'. Select from: $(SAMPLES).)
endif

PORT ?= 8000
WEB_OUTPUT ?=

.PHONY: apple_setup iOS macOS visionOS iOS_run macOS_run visionOS_run web web_run android_setup android linux_setup linux

apple_setup:
	mise trust
	mise install
	mise exec -- tuist clean
	mise exec -- tuist generate --no-open

iOS: DESTINATION ?= generic/platform=iOS Simulator
macOS: DESTINATION ?= platform=macOS
visionOS: DESTINATION ?= generic/platform=visionOS Simulator

iOS macOS visionOS:
	mise exec -- xcodebuild \
		-workspace OpenSwiftUISamples.xcworkspace \
		-scheme "$(SAMPLE)App" \
		-configuration "$(CONFIGURATION)" \
		-destination "$(DESTINATION)" \
		$(SIGNING_OPTIONS) \
		build

iOS_run macOS_run visionOS_run:
	mise exec -- xcrun python3 Scripts/run-apple.py \
		"$(@:_run=)" --sample "$(SAMPLE)" --configuration "$(CONFIGURATION)" \
		--destination "$(DESTINATION)" --development-team "$(DEVELOPMENT_TEAM)"

web:
	mise exec -- python3 Scripts/build-web.py \
		--sample "$(SAMPLE)" --configuration "$(CONFIGURATION)" \
		$(if $(strip $(WEB_OUTPUT)),--output "$(WEB_OUTPUT)")

web_run:
	mise exec -- python3 Scripts/build-web.py \
		--sample "$(SAMPLE)" --configuration "$(CONFIGURATION)" \
		$(if $(strip $(WEB_OUTPUT)),--output "$(WEB_OUTPUT)") \
		--serve --port "$(PORT)"

android_setup android:
	@echo "Android is not supported yet."

linux_setup linux:
	@echo "Linux is not supported yet."
