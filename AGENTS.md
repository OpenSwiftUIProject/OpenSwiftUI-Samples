# Game2048 agent guidance

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
- Xcode must inherit the selected environment when it starts. Scheme launch
  variables do not configure package manifest evaluation.

## Verification

- For configuration changes, check valid combinations, invalid combinations,
  and replacement of environment values left by a previous selection.
- To build only the package, use
  `mise exec -- swift build --target Game2048` when build verification is needed.
- With Xcode 27.0 / Swift 6.4, add `--build-system native` to `swift build` to
  work around the
  [SwiftBuild initialization error](https://github.com/swiftlang/swift-package-manager/issues/10561).
- A successful app build alone does not verify the OpenSwiftUI backend. Check
  that the build graph includes OpenSwiftUI and that Game2048 enables its
  `OpenSwiftUI` trait before reporting backend validation.
- For documentation-only changes, check the diff and relative links; do not
  regenerate or build the project.
