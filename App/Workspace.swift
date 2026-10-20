import ProjectDescription

let workspace = Workspace(
    name: "Game2048App",
    projects: ["."],
    // Tuist emits absolute references for precompiled dependencies under .build.
    // Keep Xcode's remote SwiftPM checkouts here so the explicit SDK stub
    // XCFramework references match SwiftPM's paths and avoid duplicate build tasks.
    generationOptions: .options(derivedDataPath: .custom(".build"))
)
