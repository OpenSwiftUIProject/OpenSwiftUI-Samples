// Copyright (c) 2026 Kyle-Ye
//
// SPDX-License-Identifier: MIT
// See LICENSE for the full license text.

#if OpenSwiftUI
import OpenObservation
#else
import Observation
#endif

@MainActor
@Observable
final class GameState {
    private(set) var board = Board()
    private(set) var score = 0
    private(set) var lastMoveDirection = MoveDirection.up
    private(set) var hasReached2048 = false
    private(set) var isGameOver = false

    @ObservationIgnored
    private var randomGenerator = SystemRandomNumberGenerator()

    init() {
        newGame()
    }

    func newGame() {
        board = Board()
        score = 0
        lastMoveDirection = .up
        hasReached2048 = false
        isGameOver = false

        board.insertRandomTile(using: &randomGenerator)
        board.insertRandomTile(using: &randomGenerator)
    }

    func move(_ direction: MoveDirection) {
        lastMoveDirection = direction

        let result = board.move(direction)
        guard result.moved else {
            isGameOver = !board.canMove
            return
        }

        score += result.scoreGained
        board.insertRandomTile(using: &randomGenerator)
        hasReached2048 = hasReached2048 || board.highestValue >= 2048
        isGameOver = !board.canMove
    }
}
