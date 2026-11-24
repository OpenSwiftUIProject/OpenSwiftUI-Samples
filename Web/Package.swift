// swift-tools-version: 6.3

import PackageDescription

let env = Context.environment
let useLocalDeps = env["OPENSWIFTUI_USE_LOCAL_DEPS"].map { $0 == "1" } ?? false
let openSwiftUIBranch = env["OPENSWIFTUI_BRANCH"] ?? "wasi/dev"

let openSwiftUIDependency: Package.Dependency = useLocalDeps
    ? .package(path: "../../OpenSwiftUI")
    : .package(
        url: "https://github.com/OpenSwiftUIProject/OpenSwiftUI.git",
        branch: openSwiftUIBranch
    )

let sharedSwiftSettings: [SwiftSetting] = [
    .define("OpenSwiftUI"),
]

let sharedCSettings: [CSetting] = [
    .define("_WASI_EMULATED_SIGNAL", .when(platforms: [.wasi])),
    .define("_WASI_EMULATED_MMAN", .when(platforms: [.wasi])),
]

let package = Package(
    name: "OpenSwiftUISamplesWeb",
    platforms: [.macOS(.v15)],
    products: [
        .executable(name: "HelloWorldWeb", targets: ["HelloWorldWeb"]),
        .executable(name: "Game2048Web", targets: ["Game2048Web"]),
    ],
    dependencies: [
        openSwiftUIDependency,
    ],
    targets: [
        .target(
            name: "HelloWorld",
            dependencies: [
                .product(name: "OpenSwiftUI", package: "OpenSwiftUI"),
            ],
            path: "Sources/HelloWorld",
            cSettings: sharedCSettings,
            swiftSettings: sharedSwiftSettings
        ),
        .executableTarget(
            name: "HelloWorldWeb",
            dependencies: [
                "HelloWorld",
                .product(name: "OpenSwiftUI", package: "OpenSwiftUI"),
            ],
            path: "App/HelloWorld",
            cSettings: sharedCSettings,
            swiftSettings: sharedSwiftSettings
        ),
        .target(
            name: "Game2048",
            dependencies: [
                .product(name: "OpenSwiftUI", package: "OpenSwiftUI"),
            ],
            path: "Sources/Game2048",
            cSettings: sharedCSettings,
            swiftSettings: sharedSwiftSettings
        ),
        .executableTarget(
            name: "Game2048Web",
            dependencies: [
                "Game2048",
                .product(name: "OpenSwiftUI", package: "OpenSwiftUI"),
            ],
            path: "App/Game2048",
            cSettings: sharedCSettings,
            swiftSettings: sharedSwiftSettings
        ),
    ],
    swiftLanguageModes: [.v6]
)
