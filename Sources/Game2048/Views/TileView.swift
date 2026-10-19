// Copyright (c) 2026 Kyle-Ye
//
// SPDX-License-Identifier: MIT
// See LICENSE for the full license text.

#if OpenSwiftUI
import OpenSwiftUI
#else
import SwiftUI
#endif

struct TileView: View {
    let value: Int?

    var body: some View {
        let colors = TileColors.colors(for: value)

        RoundedRectangle(cornerRadius: 10, style: .continuous)
            .fill(colors.background)
            .overlay {
                if let value {
                    GeometryReader { proxy in
                        Text(value.formatted())
                            .font(
                                .system(
                                    size: fontSize(
                                        for: value,
                                        tileWidth: proxy.size.width
                                    ),
                                    weight: .heavy,
                                    design: .rounded
                                )
                            )
                            .foregroundStyle(colors.foreground)
                            .contentTransition(
                                .numericText(value: Double(value))
                            )
                            .minimumScaleFactor(0.35)
                            .lineLimit(1)
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                    }
                }
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(value.map(String.init) ?? "")
            .accessibilityHidden(value == nil)
    }

    private func fontSize(for value: Int, tileWidth: CGFloat) -> CGFloat {
        let scale: CGFloat
        switch value.formatted().count {
        case 0...2:
            scale = 0.42
        case 3:
            scale = 0.36
        case 4:
            scale = 0.30
        default:
            scale = 0.24
        }
        return max(tileWidth * scale, 12)
    }
}

private enum TileColors {
    static func colors(for value: Int?) -> (
        background: Color,
        foreground: Color
    ) {
        switch value {
        case nil:
            (.tileEmpty, .tileDarkText)
        case 2:
            (.tile2, .tileDarkText)
        case 4:
            (.tile4, .tileDarkText)
        case 8:
            (.tile8, .white)
        case 16:
            (.tile16, .white)
        case 32:
            (.tile32, .white)
        case 64:
            (.tile64, .white)
        case 128:
            (.tile128, .white)
        case 256:
            (.tile256, .white)
        case 512:
            (.tile512, .white)
        case 1024:
            (.tile1024, .white)
        case 2048:
            (.tile2048, .white)
        default:
            (.tileBeyond2048, .white)
        }
    }
}

extension Color {
    static let gameBackground = Color(
        red: 0.96,
        green: 0.94,
        blue: 0.90
    )
    static let boardBackground = Color(
        red: 0.72,
        green: 0.66,
        blue: 0.63
    )
    static let tileEmpty = Color(
        red: 0.78,
        green: 0.73,
        blue: 0.68
    )
    static let tileDarkText = Color(
        red: 0.42,
        green: 0.39,
        blue: 0.35
    )
    static let tile2 = Color(red: 0.91, green: 0.87, blue: 0.83)
    static let tile4 = Color(red: 0.90, green: 0.86, blue: 0.76)
    static let tile8 = Color(red: 0.93, green: 0.67, blue: 0.46)
    static let tile16 = Color(red: 0.94, green: 0.57, blue: 0.38)
    static let tile32 = Color(red: 0.95, green: 0.46, blue: 0.33)
    static let tile64 = Color(red: 0.94, green: 0.35, blue: 0.23)
    static let tile128 = Color(red: 0.91, green: 0.78, blue: 0.43)
    static let tile256 = Color(red: 0.91, green: 0.78, blue: 0.37)
    static let tile512 = Color(red: 0.90, green: 0.77, blue: 0.31)
    static let tile1024 = Color(red: 0.91, green: 0.75, blue: 0.24)
    static let tile2048 = Color(red: 0.91, green: 0.74, blue: 0.18)
    static let tileBeyond2048 = Color(
        red: 0.24,
        green: 0.22,
        blue: 0.20
    )
}

#Preview("Tiles") {
    VStack(spacing: 8) {
        ForEach([
            [2, 4, 8, 16],
            [32, 64, 128, 256],
            [512, 1024, 2048, 4096],
        ], id: \.self) { row in
            HStack(spacing: 8) {
                ForEach(row, id: \.self) { value in
                    TileView(value: value)
                        .frame(width: 76, height: 76)
                }
            }
        }
    }
    .padding()
    .background(Color.gameBackground)
}
