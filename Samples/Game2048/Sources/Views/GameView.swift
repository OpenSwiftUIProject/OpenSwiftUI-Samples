// Copyright (c) 2026 Kyle-Ye
//
// SPDX-License-Identifier: MIT
// See LICENSE for the full license text.

#if OpenSwiftUI
import OpenSwiftUI
#else
import SwiftUI
#endif

struct GameView: View {
    @Environment(GameState.self) private var game
    @Environment(\.scenePhase) private var scenePhase
    @FocusState private var isBoardFocused: Bool

    var body: some View {
        ZStack {
            Color.gameBackground
                .ignoresSafeArea()

            GeometryReader { proxy in
                #if os(macOS) || os(WASI)
                // Reserve room for the header, footer, and stack spacing so
                // the entire column stays aligned with the square board.
                let columnWidth = max(
                    min(proxy.size.width, proxy.size.height - 140, 520),
                    0
                )
                #else
                let columnWidth = min(proxy.size.width, 520)
                #endif

                content
                    .frame(width: columnWidth)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .safeAreaPadding(.horizontal, 20)
            .safeAreaPadding(.vertical, 24)
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active {
                isBoardFocused = true
            }
        }
    }

    private var content: some View {
        VStack(spacing: 20) {
            header

            BoardView(
                board: game.board,
                insertionEdge: game.lastMoveDirection.insertionEdge
            )
            .overlay {
                if game.isGameOver {
                    gameOverOverlay
                }
            }
            .contentShape(.rect)
            .highPriorityGesture(swipeGesture)
            .focusable(interactions: .edit)
            .focused($isBoardFocused)
            .focusEffectDisabled()
            .onKeyPress(
                keys: [.upArrow, .downArrow, .leftArrow, .rightArrow],
                phases: [.down, .repeat],
                action: handleKeyPress
            )
            .onAppear {
                isBoardFocused = true
            }
            .onTapGesture {
                isBoardFocused = true
            }

            footer
        }
    }

    private var header: some View {
        HStack(alignment: .center, spacing: 12) {
            Text("2048")
                .font(.system(size: 54, weight: .black, design: .rounded))
                .foregroundStyle(Color.tileDarkText)
                .accessibilityAddTraits(.isHeader)

            Spacer(minLength: 8)

            VStack(spacing: 2) {
                Text("SCORE")
                    .font(.caption2.weight(.bold))
                Text(game.score.formatted())
                    .font(.title3.monospacedDigit().weight(.black))
                    .contentTransition(
                        .numericText(value: Double(game.score))
                    )
            }
            .foregroundStyle(.white)
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .background(Color.boardBackground, in: .rect(cornerRadius: 10))
            .accessibilityElement(children: .combine)

            Button("New Game", systemImage: "arrow.clockwise") {
                restart()
            }
            .labelStyle(.iconOnly)
            .font(.title3.weight(.bold))
            .buttonStyle(.borderedProminent)
            .buttonBorderShape(.circle)
            .tint(Color.tileDarkText)
            .accessibilityLabel("New Game")
        }
    }

    @ViewBuilder
    private var footer: some View {
        if game.hasReached2048 {
            Label("You reached 2048 — keep going!", systemImage: "trophy.fill")
                .foregroundStyle(Color.tileDarkText)
                .font(.headline)
        } else {
            Label(
                "Swipe or use arrow keys",
                systemImage: "arrow.up.and.down.and.arrow.left.and.right"
            )
            .foregroundStyle(Color.tileDarkText.secondary)
            .font(.callout)
        }
    }

    private var gameOverOverlay: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(Color.gameBackground.opacity(0.9))

            VStack(spacing: 14) {
                Text("Game Over")
                    .font(
                        .system(
                            .largeTitle,
                            design: .rounded,
                            weight: .black
                        )
                    )
                    .foregroundStyle(Color.tileDarkText)

                Button("Try Again", systemImage: "arrow.clockwise") {
                    restart()
                }
                .buttonStyle(.borderedProminent)
                .tint(Color.tileDarkText)
            }
        }
        .transition(.opacity)
    }

    private var swipeGesture: some Gesture {
        DragGesture(minimumDistance: 24)
            .onEnded { value in
                let translation = value.predictedEndTranslation
                guard max(
                    abs(translation.width),
                    abs(translation.height)
                ) >= 36 else {
                    return
                }

                if abs(translation.width) > abs(translation.height) {
                    performMove(translation.width > 0 ? .right : .left)
                } else {
                    performMove(translation.height > 0 ? .down : .up)
                }
            }
    }

    private func handleKeyPress(_ press: KeyPress) -> KeyPress.Result {
        guard press.modifiers.intersection([.command, .control, .option, .shift]).isEmpty else {
            return .ignored
        }

        let direction: MoveDirection
        switch press.key {
        case .upArrow:
            direction = .up
        case .downArrow:
            direction = .down
        case .leftArrow:
            direction = .left
        case .rightArrow:
            direction = .right
        default:
            return .ignored
        }

        performMove(direction)
        return .handled
    }

    private func performMove(_ direction: MoveDirection) {
        isBoardFocused = true
        withAnimation(.snappy(duration: 0.24, extraBounce: 0.04)) {
            game.move(direction)
        }
    }

    private func restart() {
        withAnimation(.snappy) {
            game.newGame()
        }
        isBoardFocused = true
    }
}

private extension MoveDirection {
    var insertionEdge: Edge {
        switch self {
        case .left:
            .trailing
        case .right:
            .leading
        case .up:
            .bottom
        case .down:
            .top
        }
    }
}

#Preview {
    GameView()
        .environment(GameState())
}
