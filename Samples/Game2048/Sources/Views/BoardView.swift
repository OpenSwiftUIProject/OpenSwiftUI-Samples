// Copyright (c) 2026 Kyle-Ye
//
// SPDX-License-Identifier: MIT
// See LICENSE for the full license text.

#if OpenSwiftUI
import OpenSwiftUI
#else
import SwiftUI
#endif

struct BoardView: View {
    let board: Board
    let insertionEdge: Edge

    var body: some View {
        GeometryReader { proxy in
            let side = min(proxy.size.width, proxy.size.height)
            let spacing = min(max(side * 0.025, 6), 14)
            let tileSize = max(
                (side - spacing * CGFloat(Board.size + 1)) / CGFloat(Board.size),
                0
            )

            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color.boardBackground)

                ForEach(allPositions, id: \.self) { position in
                    TileView(value: nil)
                        .frame(width: tileSize, height: tileSize)
                        .offset(
                            offset(
                                for: position,
                                tileSize: tileSize,
                                spacing: spacing
                            )
                        )
                }

                ForEach(board.positionedTiles) { positionedTile in
                    TileView(value: positionedTile.tile.value)
                        .frame(width: tileSize, height: tileSize)
                        .offset(
                            offset(
                                for: positionedTile.position,
                                tileSize: tileSize,
                                spacing: spacing
                            )
                        )
                        .transition(
                            .asymmetric(
                                insertion: .move(edge: insertionEdge)
                                    .combined(with: .scale(scale: 0.5))
                                    .combined(with: .opacity),
                                removal: .scale(scale: 0.7)
                                    .combined(with: .opacity)
                            )
                        )
                        .zIndex(1)
                }
            }
            .frame(width: side, height: side)
            .position(x: proxy.size.width / 2, y: proxy.size.height / 2)
            .clipShape(.rect(cornerRadius: 14))
            .animation(
                .snappy(duration: 0.24, extraBounce: 0.04),
                value: board
            )
        }
        .aspectRatio(1, contentMode: .fit)
        .accessibilityLabel("2048 board")
    }

    private var allPositions: [Board.Position] {
        (0..<Board.size).flatMap { row in
            (0..<Board.size).map { column in
                Board.Position(column: column, row: row)
            }
        }
    }

    private func offset(
        for position: Board.Position,
        tileSize: CGFloat,
        spacing: CGFloat
    ) -> CGSize {
        CGSize(
            width: spacing + CGFloat(position.column) * (tileSize + spacing),
            height: spacing + CGFloat(position.row) * (tileSize + spacing)
        )
    }
}

#Preview("Board") {
    BoardView(
        board: Board(rows: [
            [2, 4, 8, 16],
            [32, 64, 128, 256],
            [512, 1024, 2048, nil],
            [nil, nil, nil, nil],
        ]),
        insertionEdge: .bottom
    )
    .frame(width: 420, height: 420)
    .padding()
    .background(Color.gameBackground)
}
