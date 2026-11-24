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

ANDROID_AVD ?=
ANDROID_SERIAL ?=
ANDROID_OUTPUT ?=
ANDROID_INSTALL_SDK ?=
MISE_EXEC = $(if $(shell command -v mise 2>/dev/null),mise exec --,)

.PHONY: apple_setup iOS macOS visionOS iOS_run macOS_run visionOS_run android_setup android android_run linux_setup linux

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

android_setup:
	@if command -v mise >/dev/null 2>&1; then mise trust; fi
	$(MISE_EXEC) python3 Scripts/build-android.py --prepare \
		$(if $(filter 1 true YES yes,$(ANDROID_INSTALL_SDK)),--install-sdk)

android:
	@if command -v mise >/dev/null 2>&1; then mise trust; fi
	$(MISE_EXEC) python3 Scripts/build-android.py \
		--sample "$(SAMPLE)" --configuration "$(CONFIGURATION)" \
		$(if $(strip $(ANDROID_OUTPUT)),--output "$(ANDROID_OUTPUT)")

android_run:
	@if command -v mise >/dev/null 2>&1; then mise trust; fi
	$(MISE_EXEC) python3 Scripts/build-android.py \
		--sample "$(SAMPLE)" --configuration "$(CONFIGURATION)" \
		$(if $(strip $(ANDROID_OUTPUT)),--output "$(ANDROID_OUTPUT)") \
		$(if $(strip $(ANDROID_AVD)),--avd "$(ANDROID_AVD)") \
		$(if $(strip $(ANDROID_SERIAL)),--serial "$(ANDROID_SERIAL)") \
		--run

linux_setup linux:
	@echo "Linux is not supported yet."
