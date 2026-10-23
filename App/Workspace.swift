import ProjectDescription

let workspace = Workspace(
    name: "OpenSwiftUISamples",
    projects: ["../Samples/*"],
    // Keep DerivedData and remote SwiftPM checkouts under App/.build.
    // The shared dependency helper reads this workspace's package state so all
    // sample projects reference the same SDK stubs as SwiftPM.
    generationOptions: .options(derivedDataPath: .custom(".build"))
)
