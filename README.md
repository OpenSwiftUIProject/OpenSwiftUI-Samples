# OpenSwiftUI-Samples

Sample apps built with OpenSwiftUI for iOS, macOS, visionOS, and Web (WASI).

## Samples

| Sample | Description |
| --- | --- |
| [HelloWorld](Samples/HelloWorld) | A globe image and a greeting |
| [Game2048](Samples/Game2048) | A 2048 game with swipe and keyboard controls |

## Requirements

- Xcode 26.6+
- mise
- Tuist 4.206.0
- iOS 18, macOS 15, or visionOS 2

## Build and run

Uses OpenSwiftUI source by default. Set `MISE_ENV=sui` to use system SwiftUI.

```text
Usage:
  make apple_setup
  make <platform> [SAMPLE=<name>] [CONFIGURATION=<config>] [DESTINATION='<destination>'] [DEVELOPMENT_TEAM=<id>]
  make [<platform>_run] [SAMPLE=<name>] [CONFIGURATION=<config>] [DESTINATION='<destination>'] [DEVELOPMENT_TEAM=<id>]
  make web [SAMPLE=<name>] [CONFIGURATION=<config>] [WEB_OUTPUT=<dir>]
  make web_run [SAMPLE=<name>] [CONFIGURATION=<config>] [PORT=<port>]

Targets:
  apple_setup       Install tools, clean, and generate the workspace without opening Xcode.
  <platform>        Build for iOS, macOS, or visionOS.
  <platform>_run    Build and launch. Default: macOS_run.
  web               Build a deployable static Web bundle into Web/dist/<SAMPLE>.
  web_run           Build and serve the static Web bundle over local HTTP.

Options:
  SAMPLE            Sample directory name under Samples/. Default: HelloWorld.
  CONFIGURATION     Debug or Release. Default: Debug.
  DESTINATION       Xcode destination for build and run. Defaults to this Mac or a simulator.
  DEVELOPMENT_TEAM  Team ID for automatic signing. Uses project settings if omitted.
```

`<...>` marks a placeholder; `[...]` marks an optional argument. Run `make apple_setup`
before the first build and after changing `MISE_ENV`.

For a physical device, use `DESTINATION='platform=<platform>,id=<udid>'`.
For a specific simulator, use `DESTINATION='platform=<platform> Simulator,id=<udid>'`.
See [device setup](Docs/OpenSwiftUI.md#run-on-a-device) for signing and device discovery.

The root `Workspace.swift` generates `OpenSwiftUISamples.xcworkspace` for all samples.
Each sample has its own `Project.swift` and a `<SampleName>App` scheme. Shared Tuist
helpers configure OpenSwiftUI and the app targets. See [Samples](#samples) for available names.

See [OpenSwiftUI integration](Docs/OpenSwiftUI.md) for source, binary, and Compute configurations.

## License

MIT
