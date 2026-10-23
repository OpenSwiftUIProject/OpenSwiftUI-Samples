import ProjectDescription

extension Project {
    public static func sample(
        name: String,
        displayName: String,
        category: String = "public.app-category.developer-tools",
        tests: Bool = false
    ) throws -> Project {
        let configuration = try OpenSwiftUIConfiguration()
        let destinations: Destinations = [.iPhone, .iPad, .mac, .appleVision]
        let deploymentTargets: DeploymentTargets = .multiplatform(
            iOS: "18.0", macOS: "15.0", visionOS: "2.0"
        )
        var targets: [Target] = [
            .target(
                name: name,
                destinations: destinations,
                product: .staticFramework,
                bundleId: "org.OpenSwiftUIProject.\(name)",
                deploymentTargets: deploymentTargets,
                buildableFolders: ["Sources"],
                dependencies: configuration.dependencies
            ),
            .target(
                name: "\(name)App",
                destinations: destinations,
                product: .app,
                bundleId: "org.OpenSwiftUIProject.\(name)App",
                deploymentTargets: deploymentTargets,
                infoPlist: .dictionary([
                    "CFBundleDevelopmentRegion": "$(DEVELOPMENT_LANGUAGE)",
                    "CFBundleDisplayName": .string(displayName),
                    "CFBundleExecutable": "$(EXECUTABLE_NAME)",
                    "CFBundleIdentifier": "$(PRODUCT_BUNDLE_IDENTIFIER)",
                    "CFBundleInfoDictionaryVersion": "6.0",
                    "CFBundleName": "$(PRODUCT_NAME)",
                    "CFBundlePackageType": "$(PRODUCT_BUNDLE_PACKAGE_TYPE)",
                    "CFBundleShortVersionString": "$(MARKETING_VERSION)",
                    "CFBundleVersion": "$(CURRENT_PROJECT_VERSION)",
                    "LSApplicationCategoryType": .string(category),
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
                buildableFolders: ["Apple"],
                dependencies: [.target(name: name)] + configuration.dependencies + configuration.appDependencies
            ),
        ]
        if tests {
            targets.append(.target(
                name: "\(name)Tests",
                destinations: destinations,
                product: .unitTests,
                bundleId: "org.OpenSwiftUIProject.\(name)Tests",
                deploymentTargets: deploymentTargets,
                buildableFolders: ["Tests"],
                dependencies: [.target(name: name)] + configuration.dependencies + configuration.appDependencies
            ))
        }
        return Project(
            name: name,
            organizationName: "OpenSwiftUIProject",
            options: .options(automaticSchemesOptions: .disabled),
            packages: configuration.packages,
            settings: .settings(base: [
                "CURRENT_PROJECT_VERSION": "1",
                "ENABLE_USER_SCRIPT_SANDBOXING": "YES",
                "MARKETING_VERSION": "1.0.0",
                "SWIFT_STRICT_CONCURRENCY": "complete",
                "SWIFT_VERSION": "6.0",
                "SWIFT_ACTIVE_COMPILATION_CONDITIONS": configuration.enabled
                    ? "$(inherited) OpenSwiftUI" : "$(inherited)",
            ]),
            targets: targets,
            schemes: [
                .scheme(
                    name: "\(name)App",
                    buildAction: .buildAction(targets: ["\(name)App"]),
                    testAction: tests ? .targets(["\(name)Tests"]) : nil,
                    runAction: .runAction(executable: "\(name)App")
                ),
            ]
        )
    }
}
