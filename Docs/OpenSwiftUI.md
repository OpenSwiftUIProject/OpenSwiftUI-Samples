# OpenSwiftUI integration

Select a configuration from [`mise.toml`](../mise.toml) with `MISE_ENV`.
Combine options with commas. The default is remote OpenSwiftUI source with
AttributeGraph (`osui-source,ag`).

| Option | Effect |
| --- | --- |
| `sui` | Use system SwiftUI |
| `osui-source` | Use remote OpenSwiftUI source on `main` |
| `osui-binary` | Use prebuilt OpenSwiftUI from `OpenSwiftUI-spm` |
| `local` | Use `../OpenSwiftUI` and its sibling dependency checkouts |
| `ag` | Use the AttributeGraph backend (default for OpenSwiftUI source) |
| `compute` | Build Compute from source |

`sui`, `osui-source`, and `osui-binary` are mutually exclusive; omitting the
renderer selects `osui-source`. `ag` and `compute` are mutually exclusive;
omitting the backend selects `ag` for OpenSwiftUI source. `local`, `ag`, and
`compute` cannot be combined with `sui` or `osui-binary`. Unknown options produce
an error.

`compute` uses `../Compute` with `local`, or remote version `0.6.0-bugfix.2`
otherwise. Compute always builds from source.

## Generate and open

Run from the repository root. For example, to use local OpenSwiftUI and Compute:

```sh
export MISE_ENV=osui-source,local,compute
make apple_setup
make iOS
```

After changing the selection or its settings in `mise.toml`, clean and generate
again with `make apple_setup` in the selected environment. Use `export MISE_ENV=sui` for system SwiftUI,
or `unset MISE_ENV` to restore the default OpenSwiftUI source configuration.
The selection applies to the current terminal session; set it again in a new
terminal. For one command, use `mise --env osui-source exec -- <command>`.

Select an app with `SAMPLE=<name>`, where `<name>` is its directory under
`Samples/`. See the [sample list](../README.md#samples) for available names.
Changing the sample does not require regeneration. All samples use the same
renderer and backend configuration.

Use `make macOS` or `make visionOS` for the other Apple platforms. Build targets
accept `CONFIGURATION` and `DESTINATION` overrides, for example:

```sh
make iOS CONFIGURATION=Release DESTINATION='generic/platform=iOS'
```

Use `make <platform>_run` to build and launch the app. Build and run targets
accept the same `DESTINATION` syntax. Without an explicit destination, macOS
runs on this Mac; iOS and visionOS runs prefer a booted simulator for the selected
platform, then fall back to an available simulator. Run targets require a specific
device; `generic/platform=...` is only supported by build targets.
`make apple_setup` generates without opening Xcode.

The workspace stores DerivedData in a workspace-specific folder under the root
`.build` directory. Build the `.xcworkspace` without overriding `-derivedDataPath`
or `-clonedSourcePackagesDirPath`. The shared dependency helper reads the workspace
package state here so each sample references the same SDK stub checkout as native
SwiftPM.

If generation reports that remote SDK stubs are not resolved, run these commands
once more before building:

```sh
mise exec -- tuist clean
mise exec -- tuist generate --no-open
```

The first pass resolves the packages; the second adds the SDK stub references.
Cleaning is required because Tuist caches the evaluated manifest.
This can be needed with an empty cache or after switching from local to remote
source dependencies. No generated-project patch is required.

To reopen the workspace, fully quit Xcode, then launch it from the configured
terminal:

```sh
mise exec -- open -a "$(xcode-select -p)/../.." OpenSwiftUISamples.xcworkspace
```

An existing Xcode process keeps its original environment. Finder and Dock launches
do not load the mise configuration. Xcode needs these variables when it evaluates
the OpenSwiftUI dependency manifests.

## Run on a device

Use `DESTINATION` for both physical devices and simulators:

```text
make <platform>_run DESTINATION='platform=<platform>,id=<device-udid>' [DEVELOPMENT_TEAM=<team-id>]
make <platform>_run DESTINATION='platform=<platform> Simulator,id=<simulator-udid>'
```

Use `iOS` or `visionOS` for `<platform>`. Xcode also accepts `name=<device-name>`
instead of `id=<udid>`. List device identifiers with:

```sh
xcrun devicectl list devices
xcrun simctl list devices available
```

For a physical device, pair it with Xcode, enable Developer Mode, and unlock it.
Sign in to an Apple account in Xcode and set `DEVELOPMENT_TEAM=<team-id>` if the
project does not have a signing team. This option enables automatic signing;
the build can create or update provisioning profiles. The run script uses
`devicectl` to install and launch the signed app.
See Apple's [device setup guide](https://developer.apple.com/documentation/xcode/running-your-app-on-simulated-or-physical-devices)
and [command-line device guide](https://developer.apple.com/documentation/xcode/interacting-with-devices-using-the-command-line).

## Project configuration

The root `Workspace.swift` includes `Samples/*`. Run `mise exec -- tuist generate --no-open`
from the repository root to generate the workspace. Each sample owns its `Project.swift`.
The shared `Project.sample(...)` helper creates a source module, an app, and optional
unit tests. OpenSwiftUI selection and SDK stub references live in
`Tuist/ProjectDescriptionHelpers`.

The `sui` configuration uses system SwiftUI without an OpenSwiftUI package
reference. Other configurations add the selected OpenSwiftUI package and define
`OpenSwiftUI` for the sample sources. The samples do not use SwiftPM manifests.

After migrating from the previous SwiftPM sample layout, use Xcode's Clean Build
Folder once to remove old sample modules before building the new targets.
