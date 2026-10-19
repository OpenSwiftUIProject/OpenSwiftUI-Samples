# Game2048

A modern, universal OpenSwiftUI implementation of 2048.

Swipe the board or press the arrow keys to move tiles.

## Requirements

- Xcode 26.6+
- mise
- Tuist 4.206.0
- iOS 18, macOS 15, or visionOS 2

## Generate the project

Uses OpenSwiftUI source by default. Set `MISE_ENV=sui` to use SwiftUI on Apple platform.

```sh
mise trust
mise install
mise exec -- tuist clean --path App
mise exec -- tuist generate --path App
```

## OpenSwiftUI integration

See [OpenSwiftUI integration](Docs/OpenSwiftUI.md) for source, binary, and Compute configurations.

## Credits

Game2048 is inspired by [OpenSwiftUI-2048](https://github.com/OpenSwiftUIProject/OpenSwiftUI-2048)

## License

MIT
