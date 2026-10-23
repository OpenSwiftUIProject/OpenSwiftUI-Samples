import Foundation
import ProjectDescription

struct OpenSwiftUIConfiguration {
    let enabled: Bool
    let packages: [Package.Dependency]
    let dependencies: [TargetDependency]
    let appDependencies: [TargetDependency]

    init() throws {
        let environment = ProcessInfo.processInfo.environment
        enabled = environment["OPENSWIFTUI"].map { $0 == "1" } ?? true
        guard enabled else {
            packages = []
            dependencies = []
            appDependencies = []
            return
        }

        let binary = environment["OPENSWIFTUI_BINARY"].map { $0 == "1" } ?? false
        let local = environment["OPENSWIFTUI_USE_LOCAL_DEPS"].map { $0 == "1" } ?? false
        dependencies = [.package(product: "OpenSwiftUI")]
        if binary {
            packages = [.package(
                url: "https://github.com/OpenSwiftUIProject/OpenSwiftUI-spm.git",
                from: "0.24.3"
            )]
            appDependencies = []
            return
        }

        packages = local
            ? [.package(path: .relativeToRoot("../OpenSwiftUI"))]
            : [.package(url: "https://github.com/OpenSwiftUIProject/OpenSwiftUI.git", branch: "main")]
        let localFrameworks = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("DarwinPrivateFrameworks")
        let frameworksPath = local
            ? localFrameworks.path
            : try remotePrivateFrameworksPath(environment: environment)
        if let frameworksPath {
            // Match SwiftPM's SDK stub paths so Xcode does not embed them twice.
            appDependencies = [
                .xcframework(path: .path("\(frameworksPath)/AG/2024/AttributeGraph.xcframework")),
                .xcframework(path: .path("\(frameworksPath)/RB/2024/RenderBox.xcframework")),
                .xcframework(path: .path("\(frameworksPath)/CoreUI/2024/CoreUI.xcframework")),
                .xcframework(path: .path("\(frameworksPath)/CoreSVG/2024/CoreSVG.xcframework")),
                .xcframework(path: .path("\(frameworksPath)/SFSymbols/2024/SFSymbols.xcframework")),
                .xcframework(path: .path("\(frameworksPath)/FeatureFlags/2024/FeatureFlags.xcframework")),
                .xcframework(
                    path: .path("\(frameworksPath)/BLS/2024/BacklightServices.xcframework"),
                    condition: .when([.ios, .visionos])
                ),
            ]
        } else {
            appDependencies = []
            print("Remote SDK stubs are not resolved. After package resolution, run tuist clean and tuist generate again before building.")
        }
    }
}

// Xcode owns native SwiftPM checkouts. Match this workspace before reading its package state.
private func remotePrivateFrameworksPath(environment: [String: String]) throws -> String? {
    if let path = environment["OPENSWIFTUI_DARWIN_PRIVATE_FRAMEWORKS_PATH"] {
        return path
    }

    let workspace = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("App/OpenSwiftUISamples.xcworkspace")
    let derivedData = workspace.deletingLastPathComponent().appendingPathComponent(".build")
    guard FileManager.default.fileExists(atPath: derivedData.path) else {
        return nil
    }
    let directories = try FileManager.default.contentsOfDirectory(atPath: derivedData.path)
    for name in directories.sorted() {
        guard name.hasPrefix("OpenSwiftUISamples-") else {
            continue
        }
        let directory = derivedData.appendingPathComponent(name)
        // Package resolution can create checkouts before Xcode writes info.plist.
        if let infoData = try? Data(contentsOf: directory.appendingPathComponent("info.plist")) {
            guard let info = try? PropertyListSerialization.propertyList(from: infoData, format: nil) as? [String: Any],
                  let workspacePath = info["WorkspacePath"] as? String,
                  URL(fileURLWithPath: workspacePath).resolvingSymlinksInPath() == workspace.resolvingSymlinksInPath() else {
                continue
            }
        }
        let sourcePackages = directory.appendingPathComponent("SourcePackages")
        guard let stateData = try? Data(contentsOf: sourcePackages.appendingPathComponent("workspace-state.json")),
              let state = try? JSONSerialization.jsonObject(with: stateData) as? [String: Any],
              let object = state["object"] as? [String: Any],
              let dependencies = object["dependencies"] as? [[String: Any]] else {
            continue
        }
        for dependency in dependencies {
            guard let reference = dependency["packageRef"] as? [String: Any],
                  reference["identity"] as? String == "darwinprivateframeworks",
                  let subpath = dependency["subpath"] as? String else {
                continue
            }
            let checkout = sourcePackages.appendingPathComponent("checkouts").appendingPathComponent(subpath)
            if FileManager.default.fileExists(atPath: checkout.appendingPathComponent("Package.swift").path) {
                return checkout.path
            }
        }
    }
    return nil
}
