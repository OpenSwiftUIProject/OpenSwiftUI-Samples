.DEFAULT_GOAL := macOS_run

CONFIGURATION ?= Debug

.PHONY: apple_setup iOS macOS visionOS iOS_run macOS_run visionOS_run android_setup android linux_setup linux

apple_setup:
	mise trust
	mise install
	mise exec -- tuist clean --path App
	mise exec -- tuist generate --path App --no-open

iOS: DESTINATION ?= generic/platform=iOS Simulator
macOS: DESTINATION ?= platform=macOS
visionOS: DESTINATION ?= generic/platform=visionOS Simulator

iOS macOS visionOS:
	mise exec -- xcodebuild \
		-workspace App/Game2048App.xcworkspace \
		-scheme Game2048App \
		-configuration "$(CONFIGURATION)" \
		-destination "$(DESTINATION)" \
		build

iOS_run macOS_run visionOS_run:
	mise exec -- xcrun python3 Scripts/run-apple.py \
		"$(@:_run=)" --configuration "$(CONFIGURATION)" --device "$(DEVICE)"

android_setup android:
	@echo "Android is not supported yet."

linux_setup linux:
	@echo "Linux is not supported yet."
