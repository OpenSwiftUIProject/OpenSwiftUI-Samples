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

Use `make macOS` or `make visionOS` for the other Apple platforms. Build targets
accept `CONFIGURATION` and `DESTINATION` overrides, for example:

```sh
make iOS CONFIGURATION=Release DESTINATION='generic/platform=iOS'
```

Use `make iOS_run`, `make macOS_run`, or `make visionOS_run` to build and launch
the app. Simulator runs prefer a booted device for the selected platform, then
fall back to an available device. Use `DEVICE=<simulator-UDID>` to select one.
Run targets accept `CONFIGURATION`; they choose their build destination from
the platform and device. `make apple_setup` generates without opening Xcode.

To reopen the workspace, fully quit Xcode, then launch it from the configured
terminal:

```sh
mise exec -- open -a "$(xcode-select -p)/../.." App/Game2048App.xcworkspace
```

An existing Xcode process keeps its original environment. Finder and Dock launches
do not load the mise configuration. Xcode needs these variables when it evaluates
the package manifests.
