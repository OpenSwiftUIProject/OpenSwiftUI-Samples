# OpenSwiftUI-Samples

Sample apps built with OpenSwiftUI for iOS, macOS, visionOS, and Android.

## Samples

| Sample | Description |
| --- | --- |
| [HelloWorld](Samples/HelloWorld) | A globe image and a greeting |
| [Game2048](Samples/Game2048) | A 2048 game with swipe and keyboard controls |

## Requirements

- Apple platforms: Xcode 26.6+, `mise`, Tuist 4.206.0, and iOS 18 / macOS 15 / visionOS 2
- Android: swift.org Swift 6.3.2 toolchain, `swift-6.3.2-RELEASE_android` Swift SDK, Android NDK r27d (`27.3.13750724`), Android SDK Platform 35, JDK 17+, and Python 3 (`mise` optional; Xcode and Tuist are not required on Linux)

## Build and run

Uses OpenSwiftUI source by default. Set `MISE_ENV=sui` to use system SwiftUI on Apple platforms.

```text
Usage:
  make apple_setup
  make <platform> [SAMPLE=<name>] [CONFIGURATION=<config>] [DESTINATION='<destination>'] [DEVELOPMENT_TEAM=<id>]
  make [<platform>_run] [SAMPLE=<name>] [CONFIGURATION=<config>] [DESTINATION='<destination>'] [DEVELOPMENT_TEAM=<id>]
  make android_setup [ANDROID_INSTALL_SDK=1]
  make android [SAMPLE=<name>] [CONFIGURATION=<config>] [ANDROID_OUTPUT=<dir>]
  make android_run [SAMPLE=<name>] [CONFIGURATION=<config>] [ANDROID_AVD=<avd>] [ANDROID_SERIAL=<serial>]

Targets:
  apple_setup       Install tools, clean, and generate the workspace without opening Xcode.
  <platform>        Build for iOS, macOS, or visionOS.
  <platform>_run    Build and launch. Default: macOS_run.
  android_setup     Verify/configure the Swift 6.3.2 Android SDK and resolve Android SwiftPM dependencies.
  android           Build an arm64-v8a Android APK into Android/dist/<SAMPLE>.
  android_run       Build, install, and launch the Android APK on an arm64 device or emulator.

Options:
  SAMPLE               Sample directory name under Samples/. Default: HelloWorld.
  CONFIGURATION        Debug or Release. Default: Debug.
  DESTINATION          Xcode destination for build and run. Defaults to this Mac or a simulator.
  DEVELOPMENT_TEAM     Team ID for automatic signing. Uses project settings if omitted.
  ANDROID_INSTALL_SDK  Set to 1 with android_setup to download and link swift-6.3.2-RELEASE_android automatically.
  ANDROID_AVD          AVD name to boot or reuse for android_run.
  ANDROID_SERIAL       adb device serial for android_run.
```

`<...>` marks a placeholder; `[...]` marks an optional argument. Run `make apple_setup`
before the first Apple build and after changing `MISE_ENV`; run `make android_setup`
(or `make android_setup ANDROID_INSTALL_SDK=1`) before the first Android build.

For a physical device, use `DESTINATION='platform=<platform>,id=<udid>'`.
For a specific simulator, use `DESTINATION='platform=<platform> Simulator,id=<udid>'`.
See [device setup](Docs/OpenSwiftUI.md#run-on-a-device) for signing and device discovery.

The root `Workspace.swift` generates `OpenSwiftUISamples.xcworkspace` for all samples.
Each sample has its own `Project.swift` and a `<SampleName>App` scheme. Shared Tuist
helpers configure OpenSwiftUI and the app targets. See [Samples](#samples) for available names.

See [OpenSwiftUI integration](Docs/OpenSwiftUI.md) for source, binary, Compute, and Android configurations.

## License

MIT
