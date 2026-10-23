// Copyright (c) 2026 Kyle-Ye
//
// SPDX-License-Identifier: MIT
// See LICENSE for the full license text.

#if OpenSwiftUI
import OpenSwiftUI
#else
import SwiftUI
#endif

public struct Game: App {
    @State private var game = GameState()

    public init() {}

    public var body: some Scene {
        WindowGroup("2048") {
            GameView()
                .environment(game)
                #if os(macOS)
                .frame(
                    minWidth: 400, idealWidth: 560, maxWidth: 640,
                    minHeight: 540, idealHeight: 700, maxHeight: 800
                )
                #endif
        }
        #if os(macOS)
        .defaultSize(width: 560, height: 700)
        .windowResizability(.contentSize)
        #endif
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("New Game", systemImage: "arrow.clockwise") {
                    withAnimation(.snappy) {
                        game.newGame()
                    }
                }
                .keyboardShortcut("n", modifiers: .command)
            }
        }
    }
}
