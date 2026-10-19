// swift-tools-version: 6.3

import PackageDescription

// MARK: - OpenSwiftUI

let env = Context.environment
let useOpenSwiftUI = env["OPENSWIFTUI"].flatMap { $0 == "1" } ?? true
let openSwiftUIBinary = env["OPENSWIFTUI_BINARY"].flatMap({ $0 == "1" }) ?? false

let openSwiftUIDependency: Package.Dependency
let openSwiftUIPackageName: String

if openSwiftUIBinary {
    openSwiftUIDependency = .package(
        url: "https://github.com/OpenSwiftUIProject/OpenSwiftUI-spm.git",
        from: "0.24.1"
    )
    openSwiftUIPackageName = "OpenSwiftUI-spm"
} else {
    let useLocalDeps = env["OPENSWIFTUI_USE_LOCAL_DEPS"].flatMap({ $0 == "1" }) ?? false
    if useLocalDeps {
        openSwiftUIDependency = .package(path: "../OpenSwiftUI")
    } else {
        openSwiftUIDependency = .package(
            url: "https://github.com/OpenSwiftUIProject/OpenSwiftUI.git",
            branch: "main"
        )
    }
    openSwiftUIPackageName = "OpenSwiftUI"
}

// MARK: - package

let package = Package(
    name: "Game2048",
    platforms: [.iOS(.v18), .macOS(.v15), .visionOS(.v2)],
    products: [
        .library(name: "Game2048", targets: ["Game2048"]),
    ],
    traits: [
        .trait(name: "OpenSwiftUI", description: "Use OpenSwiftUI to render the game."),
        .default(enabledTraits: useOpenSwiftUI ? ["OpenSwiftUI"] : []),
    ],
    dependencies: [
        openSwiftUIDependency
    ],
    targets: [
        .target(
            name: "Game2048",
            dependencies: [
                .product(
                    name: "OpenSwiftUI",
                    package: openSwiftUIPackageName,
                    condition: .when(traits: ["OpenSwiftUI"])
                )
            ]
        ),
        .testTarget(name: "Game2048Tests", dependencies: ["Game2048"]),
    ]
)
