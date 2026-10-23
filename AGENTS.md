# OpenSwiftUI-Samples agent guidance

## Layout

- Keep each sample's sources, tests, and Apple entry point under
  `Samples/<Name>/Sources`, `Tests`, and `Apple`.
- Each sample declares a `Project.swift` with `Project.sample(...)`. Keep shared
  project and dependency logic in `Tuist/ProjectDescriptionHelpers`, the workspace
  in `App/`, and shared environment selections in `mise.toml`.
- `SAMPLE` selects an app; `MISE_ENV` selects its renderer and dependencies.
- `DESTINATION` uses Xcode syntax for both build and run targets. Use `simctl`
  for simulators and `devicectl` for physical devices; keep signing teams configurable.
- The Makefile and run script discover samples from `Samples/*/Project.swift`.
  Match the directory name to the project name and use `<Name>App` for its scheme.
- When adding a sample, add its `Project.swift` and update the README sample list.

## Configuration and generation

- Keep all environment selections in `mise.toml`. See
  [OpenSwiftUI integration](Docs/OpenSwiftUI.md) for supported combinations.
- The default mise configuration is remote OpenSwiftUI source with AttributeGraph.
  `sui`, `osui-source`, and `osui-binary` are mutually exclusive, as are `ag`
  and `compute`. Only `osui-source` accepts backend and `local` options.
- Select modes with `MISE_ENV`, rather than exporting individual `OPENSWIFTUI*`
  flags. The templates set the renderer, local dependencies, AttributeGraph,
  and Compute flags, and reject invalid combinations. Compute always builds
  from source.
- Run commands from the repository root with `mise exec --`. Interactive shells
  configured with `eval "$(mise activate zsh)"` can omit this prefix.
- After changing dependency configuration, run `tuist clean --path App` followed
  by `tuist generate --path App --no-open` in the same mise environment.
  `mise install` installs tools; it does not clear Tuist state or resolve Swift
  packages. `tuist generate` resolves package dependencies.
- Use the workspace's `App/.build` DerivedData location so explicit SDK stub
  references match native SwiftPM paths. If generation reports unresolved stubs,
  clean and generate again after package resolution, before building.
- Xcode must inherit the selected environment when it starts. Scheme launch
  variables do not configure package manifest evaluation.

## Verification

- For configuration changes, check valid combinations, invalid combinations,
  and replacement of environment values left by a previous selection.
- A successful app build alone does not verify the OpenSwiftUI backend. Check
  that the build graph includes OpenSwiftUI and that the selected sample defines the
  `OpenSwiftUI` compilation condition before reporting backend validation.
- For documentation-only changes, check the diff and relative links; do not
  regenerate or build the project.
- For Apple run script changes, run `python3 -B -m unittest discover -s Scripts/tests`.
