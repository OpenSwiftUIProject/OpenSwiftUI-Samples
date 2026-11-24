// Copyright (c) 2026 Kyle-Ye
//
// SPDX-License-Identifier: MIT
// See LICENSE for the full license text.

#if OpenSwiftUI
import OpenSwiftUI

// App-local no-op fallbacks for APIs missing from OpenSwiftUI 0.24.
// Remove these as the corresponding APIs become available upstream.

// MARK: - Accessibility

extension View {
    @_disfavoredOverload
    nonisolated func accessibilityLabel<S: StringProtocol>(_: S) -> some View {
        self
    }

    @_disfavoredOverload
    nonisolated func accessibilityElement(
        children _: AccessibilityChildBehavior = .ignore
    ) -> some View {
        self
    }

    @_disfavoredOverload
    nonisolated func accessibilityHidden(_: Bool) -> some View {
        self
    }
}

// MARK: - Content transitions

extension View {
    @_disfavoredOverload
    nonisolated func contentTransition(_: ContentTransition) -> some View {
        self
    }
}

extension ContentTransition {
    @_disfavoredOverload
    static func numericText(value _: Double) -> ContentTransition {
        .identity
    }
}

// MARK: - Window title

extension WindowGroup {
    nonisolated init(_: LocalizedStringKey, @ViewBuilder content: () -> Content) {
        self.init(content: content)
    }
}

// MARK: - Window sizing

struct WindowResizability: Sendable {
    static let contentSize = WindowResizability()
}

extension Scene {
    nonisolated func defaultSize(width _: CGFloat, height _: CGFloat) -> some Scene {
        self
    }

    nonisolated func windowResizability(_: WindowResizability) -> some Scene {
        self
    }
}

// MARK: - Commands

struct CommandGroupPlacement: Sendable {
    static let newItem = CommandGroupPlacement()
}

struct CommandGroup<Content: View>: Commands {
    nonisolated init(
        replacing _: CommandGroupPlacement,
        @ViewBuilder addition _: () -> Content
    ) {}

    nonisolated var body: EmptyCommands {
        EmptyCommands()
    }

    nonisolated static func _makeCommands(
        content: _GraphValue<Self>,
        inputs: _CommandsInputs
    ) -> _CommandsOutputs {
        EmptyCommands._makeCommands(content: content[\.body], inputs: inputs)
    }
}

extension Scene {
    // Do not evaluate command content or create unsupported menu graph nodes.
    nonisolated func commands<Content: View>(
        @CommandsBuilder content _: () -> CommandGroup<Content>
    ) -> some Scene {
        self
    }
}
#endif
