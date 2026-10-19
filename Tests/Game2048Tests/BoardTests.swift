import Testing
@testable import Game2048

@Suite("2048 board rules")
struct BoardTests {
    @Test("A row merges each tile at most once")
    func mergesEachTileOnce() {
        var board = Board(rows: [
            [2, 2, 2, 2],
            [nil, nil, nil, nil],
            [nil, nil, nil, nil],
            [nil, nil, nil, nil],
        ])

        let result = board.move(.left)

        #expect(result == .init(moved: true, scoreGained: 8))
        #expect(board.values[0] == [4, 4, nil, nil])
    }

    @Test("Merged tiles do not merge again during the same move")
    func mergedTilesDoNotMergeTwice() {
        var board = Board(rows: [
            [2, 2, 4, nil],
            [nil, nil, nil, nil],
            [nil, nil, nil, nil],
            [nil, nil, nil, nil],
        ])

        let result = board.move(.left)

        #expect(result == .init(moved: true, scoreGained: 4))
        #expect(board.values[0] == [4, 4, nil, nil])
    }

    @Test("Movement works in the reverse direction")
    func movesRight() {
        var board = Board(rows: [
            [2, 2, nil, nil],
            [nil, nil, nil, nil],
            [nil, nil, nil, nil],
            [nil, nil, nil, nil],
        ])

        let result = board.move(.right)

        #expect(result == .init(moved: true, scoreGained: 4))
        #expect(board.values[0] == [nil, nil, nil, 4])
    }

    @Test("Columns merge in movement order")
    func movesUp() {
        var board = Board(rows: [
            [2, nil, nil, nil],
            [2, nil, nil, nil],
            [4, nil, nil, nil],
            [4, nil, nil, nil],
        ])

        let result = board.move(.up)

        #expect(result == .init(moved: true, scoreGained: 12))
        #expect(board.values.map { $0[0] } == [4, 8, nil, nil])
    }

    @Test("A move that changes nothing is reported as a no-op")
    func detectsNoOp() {
        var board = Board(rows: [
            [2, nil, nil, nil],
            [nil, nil, nil, nil],
            [nil, nil, nil, nil],
            [nil, nil, nil, nil],
        ])

        let result = board.move(.left)

        #expect(result == .init(moved: false, scoreGained: 0))
        #expect(board.tileCount == 1)
    }

    @Test("A tile can be inserted into the final empty cell")
    func fillsFinalEmptyCell() {
        var board = Board(rows: [
            [2, 4, 2, 4],
            [4, 2, 4, 2],
            [2, 4, 2, 4],
            [4, 2, 4, nil],
        ])
        var generator = SeededRandomNumberGenerator()

        let inserted = board.insertRandomTile(using: &generator)

        #expect(inserted)
        #expect(board.tileCount == 16)
        #expect(
            board.values[3][3] == 2
                || board.values[3][3] == 4
        )
    }

    @Test("A full board without adjacent equals is game over")
    func detectsGameOver() {
        let board = Board(rows: [
            [2, 4, 2, 4],
            [4, 2, 4, 2],
            [2, 4, 2, 4],
            [4, 2, 4, 2],
        ])

        #expect(!board.canMove)
    }
}

private struct SeededRandomNumberGenerator: RandomNumberGenerator {
    private var state: UInt64 = 0x4D59_5DF4_D0F3_3173

    mutating func next() -> UInt64 {
        state = state &* 6_364_136_223_846_793_005
            &+ 1_442_695_040_888_963_407
        return state
    }
}
