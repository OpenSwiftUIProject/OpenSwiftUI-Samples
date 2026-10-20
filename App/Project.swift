import Foundation
import ProjectDescription

let env = ProcessInfo.processInfo.environment
let useOpenSwiftUI = env["OPENSWIFTUI"].flatMap { $0 == "1" } ?? true
let openSwiftUIBinary = env["OPENSWIFTUI_BINARY"].flatMap { $0 == "1" } ?? false
let useLocalDeps = env["OPENSWIFTUI_USE_LOCAL_DEPS"].flatMap({ $0 == "1" }) ?? false

var packages: [Package.Dependency] = [
    .package(path: ".."),
]
var appDependencies: [TargetDependency] = [.package(product: "Game2048")]

if useOpenSwiftUI {
    if openSwiftUIBinary {
        packages.append(
            .package(
                url: "https://github.com/OpenSwiftUIProject/OpenSwiftUI-spm.git",
                from: "0.24.1"
            )
        )
        appDependencies.append(.package(product: "OpenSwiftUI"))
    } else {
        let resolvedFrameworksPath: String?
        if useLocalDeps {
            resolvedFrameworksPath = "../../DarwinPrivateFrameworks"
        } else {
            resolvedFrameworksPath = try remotePrivateFrameworksPath()
        }
        if let frameworksPath = resolvedFrameworksPath {
            // Direct references let Xcode process the SDK stubs as XCFrameworks.
            appDependencies += [
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
            // Native packages resolve after Tuist evaluates this manifest.
            print("Remote SDK stubs are not resolved. After package resolution, run tuist clean and tuist generate again before building.")
        }
    }
}

let destinations: Destinations = [.iPhone, .iPad, .mac, .appleVision]
let deploymentTargets: DeploymentTargets = .multiplatform(
    iOS: "18.0",
    macOS: "15.0",
    visionOS: "2.0"
)

let project = Project(
    name: "Game2048App",
    organizationName: "OpenSwiftUIProject",
    packages: packages,
    settings: .settings(base: [
        "CURRENT_PROJECT_VERSION": "1",
        "ENABLE_USER_SCRIPT_SANDBOXING": "YES",
        "MARKETING_VERSION": "1.0.0",
        "SWIFT_STRICT_CONCURRENCY": "complete",
        "SWIFT_VERSION": "6.0",
    ]),
    targets: [
        .target(
            name: "Game2048App",
            destinations: destinations,
            product: .app,
            bundleId: "org.OpenSwiftUIProject.Game2048App",
            deploymentTargets: deploymentTargets,
            infoPlist: .dictionary([
                "CFBundleDevelopmentRegion": "$(DEVELOPMENT_LANGUAGE)",
                "CFBundleDisplayName": "2048",
                "CFBundleExecutable": "$(EXECUTABLE_NAME)",
                "CFBundleIdentifier": "$(PRODUCT_BUNDLE_IDENTIFIER)",
                "CFBundleInfoDictionaryVersion": "6.0",
                "CFBundleName": "$(PRODUCT_NAME)",
                "CFBundlePackageType": "$(PRODUCT_BUNDLE_PACKAGE_TYPE)",
                "CFBundleShortVersionString": "$(MARKETING_VERSION)",
                "CFBundleVersion": "$(CURRENT_PROJECT_VERSION)",
                "LSApplicationCategoryType": "public.app-category.puzzle-games",
                "LSMinimumSystemVersion": "$(MACOSX_DEPLOYMENT_TARGET)",
                "LSRequiresIPhoneOS": true,
                "NSPrincipalClass": "NSApplication",
                "UIApplicationSceneManifest": [
                    "UIApplicationSupportsMultipleScenes": false,
                    "UISceneConfigurations": [:],
                ],
                "UILaunchScreen": [:],
                "UISupportedInterfaceOrientations": [
                    "UIInterfaceOrientationPortrait",
                    "UIInterfaceOrientationLandscapeLeft",
                    "UIInterfaceOrientationLandscapeRight",
                ],
                "UISupportedInterfaceOrientations~ipad": [
                    "UIInterfaceOrientationPortrait",
                    "UIInterfaceOrientationPortraitUpsideDown",
                    "UIInterfaceOrientationLandscapeLeft",
                    "UIInterfaceOrientationLandscapeRight",
                ],
            ]),
            sources: ["main.swift"],
            dependencies: appDependencies
        ),
    ]
)

// Xcode owns native SwiftPM checkouts. Match this workspace before reading its package state.
private func remotePrivateFrameworksPath() throws -> String? {
    if let path = env["OPENSWIFTUI_DARWIN_PRIVATE_FRAMEWORKS_PATH"] {
        return path
    }

    let workspace = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .appendingPathComponent("Game2048App.xcworkspace")
    let derivedData = workspace.deletingLastPathComponent().appendingPathComponent(".build")
    guard FileManager.default.fileExists(atPath: derivedData.path) else {
        return nil
    }
    let directories = try FileManager.default.contentsOfDirectory(atPath: derivedData.path)
    for name in directories.sorted() {
        guard name.hasPrefix("Game2048App-") else {
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
