// Copyright (c) 2026 Kyle-Ye
//
// SPDX-License-Identifier: MIT
// See LICENSE for the full license text.

import Foundation

struct Tile: Identifiable, Equatable, Sendable {
    let id: UUID
    var value: Int

    init(id: UUID = UUID(), value: Int) {
        precondition(
            value >= 2 && value.nonzeroBitCount == 1,
            "A 2048 tile must contain a power of two."
        )
        self.id = id
        self.value = value
    }
}
