// Copyright (c) 2026 Kyle-Ye
//
// SPDX-License-Identifier: MIT
// See LICENSE for the full license text.

struct Board: Equatable, Sendable {
    static let size = 4

    struct Position: Hashable, Sendable {
        let column: Int
        let row: Int
    }

    struct PositionedTile: Identifiable, Equatable, Sendable {
        let position: Position
        let tile: Tile

        var id: Tile.ID { tile.id }
    }

    struct MoveResult: Equatable, Sendable {
        let moved: Bool
        let scoreGained: Int
    }

    private var cells: [Tile?]

    init() {
        cells = Array(repeating: nil, count: Self.size * Self.size)
    }

    init(rows: [[Int?]]) {
        precondition(
            rows.count == Self.size && rows.allSatisfy { $0.count == Self.size },
            "A 2048 board must be 4 by 4."
        )
        cells = rows.flatMap { row in
            row.map { value in value.map { Tile(value: $0) } }
        }
    }

    subscript(position: Position) -> Tile? {
        get {
            cells[offset(for: position)]
        }
        set {
            cells[offset(for: position)] = newValue
        }
    }

    var positionedTiles: [PositionedTile] {
        cells.enumerated().compactMap { offset, tile in
            guard let tile else { return nil }
            return PositionedTile(
                position: Position(
                    column: offset % Self.size,
                    row: offset / Self.size
                ),
                tile: tile
            )
        }
    }

    var values: [[Int?]] {
        (0..<Self.size).map { row in
            (0..<Self.size).map { column in
                self[Position(column: column, row: row)]?.value
            }
        }
    }

    var tileCount: Int {
        cells.compactMap { $0 }.count
    }

    var highestValue: Int {
        cells.compactMap { $0?.value }.max() ?? 0
    }

    var canMove: Bool {
        guard !cells.contains(where: { $0 == nil }) else {
            return true
        }

        for row in 0..<Self.size {
            for column in 0..<Self.size {
                let value = self[Position(column: column, row: row)]?.value
                if column + 1 < Self.size,
                   self[Position(column: column + 1, row: row)]?.value == value {
                    return true
                }
                if row + 1 < Self.size,
                   self[Position(column: column, row: row + 1)]?.value == value {
                    return true
                }
            }
        }
        return false
    }

    mutating func move(_ direction: MoveDirection) -> MoveResult {
        let originalCells = cells
        var scoreGained = 0

        for line in 0..<Self.size {
            let positions = positions(in: line, moving: direction)
            let tiles = positions.compactMap { self[$0] }
            let collapsed = Self.collapse(tiles)
            scoreGained += collapsed.scoreGained

            for (index, position) in positions.enumerated() {
                self[position] = index < collapsed.tiles.count
                    ? collapsed.tiles[index]
                    : nil
            }
        }

        return MoveResult(
            moved: cells != originalCells,
            scoreGained: scoreGained
        )
    }

    @discardableResult
    mutating func insertRandomTile<R: RandomNumberGenerator>(
        using generator: inout R
    ) -> Bool {
        let emptyPositions = cells.indices.compactMap { offset -> Position? in
            guard cells[offset] == nil else { return nil }
            return Position(
                column: offset % Self.size,
                row: offset / Self.size
            )
        }

        guard let position = emptyPositions.randomElement(using: &generator) else {
            return false
        }

        let value = Int.random(in: 0..<10, using: &generator) == 0 ? 4 : 2
        self[position] = Tile(value: value)
        return true
    }

    private func offset(for position: Position) -> Int {
        precondition(
            (0..<Self.size).contains(position.column)
                && (0..<Self.size).contains(position.row),
            "Board position is outside the 4 by 4 grid."
        )
        return position.row * Self.size + position.column
    }

    private func positions(
        in line: Int,
        moving direction: MoveDirection
    ) -> [Position] {
        (0..<Self.size).map { offset in
            switch direction {
            case .left:
                Position(column: offset, row: line)
            case .right:
                Position(column: Self.size - 1 - offset, row: line)
            case .up:
                Position(column: line, row: offset)
            case .down:
                Position(column: line, row: Self.size - 1 - offset)
            }
        }
    }

    private static func collapse(
        _ input: [Tile]
    ) -> (tiles: [Tile], scoreGained: Int) {
        var output: [Tile] = []
        var scoreGained = 0
        var index = 0

        while index < input.count {
            if index + 1 < input.count,
               input[index].value == input[index + 1].value {
                var mergedTile = input[index]
                mergedTile.value *= 2
                output.append(mergedTile)
                scoreGained += mergedTile.value
                index += 2
            } else {
                output.append(input[index])
                index += 1
            }
        }

        return (output, scoreGained)
    }
}
