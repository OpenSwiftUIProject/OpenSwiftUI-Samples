// swift-tools-version: 6.3

import PackageDescription

let env = Context.environment
let useLocalDeps = env["OPENSWIFTUI_USE_LOCAL_DEPS"].map { $0 == "1" } ?? false
let openSwiftUIBranch = env["OPENSWIFTUI_BRANCH"] ?? "android/dev"

let openSwiftUIDependency: Package.Dependency = useLocalDeps
    ? .package(path: "../../OpenSwiftUI")
    : .package(
        url: "https://github.com/OpenSwiftUIProject/OpenSwiftUI.git",
        branch: openSwiftUIBranch
    )

let sharedSwiftSettings: [SwiftSetting] = [
    .define("OpenSwiftUI"),
    .interoperabilityMode(.Cxx, .when(platforms: [.android])),
]

let package = Package(
    name: "OpenSwiftUISamplesAndroid",
    platforms: [.macOS(.v15)],
    products: [
        .library(name: "HelloWorldAndroid", type: .dynamic, targets: ["HelloWorldAndroid"]),
        .library(name: "Game2048Android", type: .dynamic, targets: ["Game2048Android"]),
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
            swiftSettings: sharedSwiftSettings
        ),
        .target(
            name: "HelloWorldAndroid",
            dependencies: [
                "HelloWorld",
                .product(name: "OpenSwiftUI", package: "OpenSwiftUI"),
                .product(
                    name: "OpenSwiftUIAndroidHost",
                    package: "OpenSwiftUI",
                    condition: .when(platforms: [.android])
                ),
            ],
            path: "App/HelloWorld",
            swiftSettings: sharedSwiftSettings
        ),
        .target(
            name: "Game2048",
            dependencies: [
                .product(name: "OpenSwiftUI", package: "OpenSwiftUI"),
            ],
            path: "Sources/Game2048",
            swiftSettings: sharedSwiftSettings
        ),
        .target(
            name: "Game2048Android",
            dependencies: [
                "Game2048",
                .product(name: "OpenSwiftUI", package: "OpenSwiftUI"),
                .product(
                    name: "OpenSwiftUIAndroidHost",
                    package: "OpenSwiftUI",
                    condition: .when(platforms: [.android])
                ),
            ],
            path: "App/Game2048",
            swiftSettings: sharedSwiftSettings
        ),
    ],
    swiftLanguageModes: [.v6],
    cxxLanguageStandard: .cxx20
)
