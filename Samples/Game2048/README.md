# Game2048

A modern, universal OpenSwiftUI implementation of 2048.

Swipe the board or press the arrow keys to move tiles.

Run from the repository root:

```sh
make apple_setup
make macOS_run SAMPLE=Game2048
```

Use `iOS_run` or `visionOS_run` for a simulator.

To run the board tests on macOS from the repository root:

```sh
mise exec -- xcodebuild test -workspace OpenSwiftUISamples.xcworkspace \
    -scheme Game2048App -destination 'platform=macOS' -only-testing:Game2048Tests
```

## Credits

Game2048 is inspired by [OpenSwiftUI-2048](https://github.com/OpenSwiftUIProject/OpenSwiftUI-2048).
