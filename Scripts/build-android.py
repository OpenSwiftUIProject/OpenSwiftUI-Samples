#!/usr/bin/env python3

from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time


DISPLAY_NAMES = {
    "HelloWorld": "Hello World",
    "Game2048": "2048",
}

REQUIRED_NDK_REVISION = "27.3.13750724"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and optionally run an OpenSwiftUI sample APK for Android (arm64-v8a, API 28+)."
    )
    parser.add_argument(
        "--sample",
        default="HelloWorld",
        help="Sample name under Samples/ (default: HelloWorld).",
    )
    parser.add_argument(
        "--configuration",
        default="Debug",
        help="Build configuration: Debug or Release (default: Debug).",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output directory for the packaged APK (default: Android/dist/<Sample>).",
    )
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Resolve Android SwiftPM dependencies only (also prepares Android Studio).",
    )
    parser.add_argument(
        "--install-sdk",
        action="store_true",
        help="Automatically download and configure the matching swift.org Android Swift SDK if missing.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Install and launch the built APK on an arm64 Android device or emulator.",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip building and launch the existing APK when --run is set.",
    )
    parser.add_argument(
        "--avd",
        default="",
        help="Start or reuse this installed arm64 Android Virtual Device when --run is set.",
    )
    parser.add_argument(
        "--serial",
        default="",
        help="Target this adb device serial when --run is set (defaults to ANDROID_SERIAL).",
    )
    parser.add_argument(
        "--print-tree",
        action="store_true",
        help="Capture DisplayList output in the app's files/display-list.log when --run is set.",
    )
    return parser.parse_args()


def validate_environment(env: dict[str, str]) -> None:
    if env.get("OPENSWIFTUI") == "0":
        raise SystemExit("Android builds require OpenSwiftUI source (osui-source), not sui.")
    if env.get("OPENSWIFTUI_BINARY") == "1":
        raise SystemExit("Android builds require OpenSwiftUI source (osui-source), not osui-binary.")


def ensure_sample_symlinks(repo_root: Path, android_dir: Path) -> list[str]:
    samples_dir = repo_root / "Samples"
    android_sources_dir = android_dir / "Sources"
    android_sources_dir.mkdir(parents=True, exist_ok=True)

    discovered: list[str] = []
    for project_file in sorted(samples_dir.glob("*/Project.swift")):
        sample_name = project_file.parent.name
        discovered.append(sample_name)
        link_path = android_sources_dir / sample_name
        relative_target = Path("../../Samples") / sample_name / "Sources"
        if link_path.is_symlink():
            if Path(os.readlink(link_path)) == relative_target:
                continue
            link_path.unlink()
        elif link_path.exists():
            continue
        link_path.symlink_to(relative_target)
    return discovered


def default_android_sdk_url(swift_release: str) -> str:
    return (
        f"https://download.swift.org/swift-{swift_release}-release/android-sdk/"
        f"swift-{swift_release}-RELEASE/swift-{swift_release}-RELEASE_android.artifactbundle.tar.gz"
    )


def candidate_swift_sdk_homes(system: str, home: Path, env: dict[str, str]) -> list[Path]:
    if system == "Darwin":
        return [home / "Library/org.swift.swiftpm/swift-sdks"]
    xdg_data = Path(env.get("XDG_DATA_HOME", str(home / ".local/share")))
    return [
        xdg_data / "org.swift.swiftpm/swift-sdks",
        home / ".swiftpm/swift-sdks",
        xdg_data / "swiftpm/swift-sdks",
        home / ".local/share/swiftpm/swift-sdks",
    ]


def discover_swift_android_sdk_path(
    system: str,
    home: Path,
    env: dict[str, str],
    swift_release: str,
) -> str:
    if env.get("SWIFT_ANDROID_SDK_PATH"):
        return env["SWIFT_ANDROID_SDK_PATH"]
    bundle_name = f"swift-{swift_release}-RELEASE_android.artifactbundle"
    sdk_homes = candidate_swift_sdk_homes(system, home, env)
    for sdk_home in sdk_homes:
        candidate = sdk_home / bundle_name / "swift-android"
        if (candidate / "swift-sdk.json").is_file():
            return str(candidate)
    return str(sdk_homes[0] / bundle_name / "swift-android")


def discover_java_home(system: str, home: Path, env: dict[str, str]) -> str:
    if env.get("JAVA_HOME"):
        return env["JAVA_HOME"]
    if system == "Darwin":
        for jbr in (
            Path("/Applications/Android Studio.app/Contents/jbr/Contents/Home"),
            home / "Applications/Android Studio.app/Contents/jbr/Contents/Home",
        ):
            if jbr.is_dir():
                return str(jbr)
        java_home_tool = Path("/usr/libexec/java_home")
        if java_home_tool.is_file() and os.access(java_home_tool, os.X_OK):
            res = subprocess.run(
                [str(java_home_tool), "-v", "17+"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
    elif system == "Linux":
        for jbr in (
            Path("/opt/android-studio/jbr"),
            home / "android-studio/jbr",
            home / ".local/share/JetBrains/Toolbox/apps/android-studio/jbr",
        ):
            if jbr.is_dir():
                return str(jbr)
    return ""


def prepare_build_environment(
    repo_root: Path,
    base_env: dict[str, str],
    host_system: str | None = None,
) -> tuple[dict[str, str], str, str]:
    validate_environment(base_env)
    env = base_env.copy()
    system = host_system or platform.system()
    home = Path(env.get("HOME", str(Path.home())))

    swift_release = env.get("OPENSWIFTUI_ANDROID_SWIFT_RELEASE", "6.3.2")
    triple = env.get("OPENSWIFTUI_ANDROID_TRIPLE", "aarch64-unknown-linux-android28")

    if system == "Darwin":
        android_home = env.get("ANDROID_HOME") or env.get("ANDROID_SDK_ROOT") or str(home / "Library/Android/sdk")
        if not env.get("DEVELOPER_DIR") and Path("/Applications/Xcode-26.3.0.app").is_dir():
            env["DEVELOPER_DIR"] = "/Applications/Xcode-26.3.0.app/Contents/Developer"
    elif system == "Linux":
        android_home = env.get("ANDROID_HOME") or env.get("ANDROID_SDK_ROOT") or str(home / "Android/Sdk")
    else:
        raise SystemExit(f"Unsupported host OS '{system}' for Android sample builds.")

    java_home = discover_java_home(system, home, env)
    if java_home:
        env["JAVA_HOME"] = java_home

    env["ANDROID_HOME"] = android_home
    swift_sdk_path = discover_swift_android_sdk_path(system, home, env, swift_release)
    env["SWIFT_ANDROID_SDK_PATH"] = swift_sdk_path

    ndk_home = env.get("ANDROID_NDK_HOME") or env.get("ANDROID_NDK_ROOT") or ""
    if not ndk_home:
        for candidate_ndk in (
            Path(android_home) / f"ndk/{REQUIRED_NDK_REVISION}",
            home / "android-ndk/android-ndk-r27d",
        ):
            if candidate_ndk.is_dir():
                ndk_home = str(candidate_ndk)
                break
        else:
            ndk_home = str(Path(android_home) / f"ndk/{REQUIRED_NDK_REVISION}")
    env["ANDROID_NDK_HOME"] = ndk_home

    path_parts = []
    if env.get("JAVA_HOME"):
        path_parts.append(str(Path(env["JAVA_HOME"]) / "bin"))
    path_parts.extend([
        str(Path(android_home) / "platform-tools"),
        str(Path(android_home) / "emulator"),
        str(home / ".swiftly/bin"),
    ])
    if env.get("PATH"):
        path_parts.append(env["PATH"])
    env["PATH"] = ":".join(path_parts)

    use_local = env.get("OPENSWIFTUI_USE_LOCAL_DEPS") == "1"
    local_flag = "1" if use_local else "0"
    env["OPENSWIFTUI_USE_LOCAL_DEPS"] = local_flag
    env["OPENATTRIBUTEGRAPH_USE_LOCAL_DEPS"] = local_flag
    env["OPENRENDERBOX_USE_LOCAL_DEPS"] = local_flag

    env["OPENSWIFTUI_BUILD_FOR_DARWIN_PLATFORM"] = "0"
    env["OPENATTRIBUTEGRAPH_BUILD_FOR_DARWIN_PLATFORM"] = "0"
    env["OPENRENDERBOX_BUILD_FOR_DARWIN_PLATFORM"] = "0"
    env["OPENSWIFTUI_LIBRARY_EVOLUTION"] = "0"
    env["OPENATTRIBUTEGRAPH_LIBRARY_EVOLUTION"] = "0"
    env["OPENRENDERBOX_LIBRARY_EVOLUTION"] = "0"
    env["OPENSWIFTUI_OPENATTRIBUTESHIMS_ATTRIBUTEGRAPH"] = "0"
    env["OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE"] = "1"
    env["OPENATTRIBUTEGRAPH_OPENATTRIBUTESHIMS_COMPUTE"] = "1"
    env["OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE_BINARY"] = "0"
    env["OPENATTRIBUTEGRAPH_OPENATTRIBUTESHIMS_COMPUTE_BINARY"] = "0"

    if "OPENSWIFTUI_ANDROID_COMPUTE_SOURCE_VERSION" in env:
        env["OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_VERSION"] = env[
            "OPENSWIFTUI_ANDROID_COMPUTE_SOURCE_VERSION"
        ]
    else:
        env.pop("OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_VERSION", None)
        env.setdefault("OPENATTRIBUTEGRAPH_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_REPO", "OpenSwiftUIProject/Compute")
        env.setdefault("OPENATTRIBUTEGRAPH_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_BRANCH", "android/dev")

    env["OPENSWIFTUI_UIKIT_CROSS_PLATFORM"] = "1"
    env["OPENSWIFTUI_ANDROID_APP"] = "1"
    env["OPENSWIFTUI_RENDER_GTK"] = "0"
    env["OPENSWIFTUI_SWIFT_TOOLCHAIN_SUPPORTED"] = "0"

    static_swift = Path(swift_sdk_path) / "swift-resources/usr/lib/swift_static-aarch64"
    env["OPENRENDERBOX_LIB_SWIFT_PATH"] = str(static_swift)
    env["OPENSWIFTUI_ANDROID_SWIFT_STATIC_LIB_DIR"] = str(static_swift / "android")

    if use_local and not env.get("OPENSWIFTUI_UIKIT_CROSS_PLATFORM_PATH"):
        sibling_uikit = repo_root.parent / "UIKit-cross-platform"
        if sibling_uikit.is_dir():
            env["OPENSWIFTUI_UIKIT_CROSS_PLATFORM_PATH"] = str(sibling_uikit.resolve())

    count = int(env.get("GIT_CONFIG_COUNT", "0"))
    env[f"GIT_CONFIG_KEY_{count}"] = "url.https://github.com/.insteadOf"
    env[f"GIT_CONFIG_VALUE_{count}"] = "git@github.com:"
    env["GIT_CONFIG_COUNT"] = str(count + 1)

    return env, swift_release, triple


def verify_local_sibling_checkouts(repo_root: Path, env: dict[str, str]) -> None:
    if env.get("OPENSWIFTUI_USE_LOCAL_DEPS") != "1":
        return
    local_osui = (repo_root.parent / "OpenSwiftUI").resolve()
    if not local_osui.is_dir():
        raise SystemExit(
            f"OPENSWIFTUI_USE_LOCAL_DEPS=1 (MISE_ENV=local) requires a sibling OpenSwiftUI checkout at {local_osui}.\n"
            f"Omit MISE_ENV=local to build from remote 'android/dev' repositories automatically, or clone\n"
            f"OpenSwiftUI alongside OpenSwiftUI-Samples and run '../OpenSwiftUI/Scripts/android_setup.sh'."
        )
    uikit_override = env.get("OPENSWIFTUI_UIKIT_CROSS_PLATFORM_PATH")
    if not uikit_override or not Path(uikit_override).is_dir():
        sibling_uikit = (repo_root.parent / "UIKit-cross-platform").resolve()
        raise SystemExit(
            f"OPENSWIFTUI_USE_LOCAL_DEPS=1 (MISE_ENV=local) requires UIKit-cross-platform at {sibling_uikit}.\n"
            f"Run '../OpenSwiftUI/Scripts/android_setup.sh' to populate sibling checkouts, or omit MISE_ENV=local."
        )


def resolve_swift_command(
    env: dict[str, str],
    swift_release: str,
    args: list[str],
    system_toolchain_roots: tuple[Path, ...] | None = None,
) -> list[str]:
    if env.get("SWIFT_EXEC"):
        return [env["SWIFT_EXEC"], *args]

    home = Path(env.get("HOME", str(Path.home())))
    toolchain_name = f"swift-{swift_release}-RELEASE.xctoolchain"
    roots = system_toolchain_roots or (
        home / "Library/Developer/Toolchains",
        Path("/Library/Developer/Toolchains"),
    )
    for root in roots:
        mac_toolchain = root / toolchain_name / "usr/bin/swift"
        if mac_toolchain.is_file() and os.access(mac_toolchain, os.X_OK):
            return [str(mac_toolchain), *args]

    linux_swiftly = Path(env.get("SWIFTLY_HOME_DIR", str(home / ".local/share/swiftly")))
    linux_toolchain = linux_swiftly / f"toolchains/{swift_release}/usr/bin/swift"
    if linux_toolchain.is_file() and os.access(linux_toolchain, os.X_OK):
        return [str(linux_toolchain), *args]

    swiftly = shutil.which("swiftly", path=env.get("PATH"))
    if swiftly is None:
        candidate = home / ".swiftly/bin/swiftly"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            swiftly = str(candidate)
    if swiftly:
        return [swiftly, "run", "swift", *args, f"+{swift_release}"]

    fallback_swift = shutil.which("swift", path=env.get("PATH"))
    if fallback_swift:
        return [fallback_swift, *args]

    raise SystemExit(
        f"Swift {swift_release} toolchain not found.\n"
        f"Install swiftly (https://www.swift.org/install/) and run:\n"
        f"  swiftly install {swift_release}"
    )


def configure_swift_android_sdk_ndk(swift_sdk_path: Path, ndk_home: Path) -> None:
    prebuilts = [p for p in (ndk_home / "toolchains/llvm/prebuilt").glob("*") if p.is_dir()]
    if len(prebuilts) != 1:
        raise SystemExit(f"Expected one host LLVM prebuilt directory under {ndk_home}/toolchains/llvm/prebuilt.")
    prebuilt = prebuilts[0]

    ndk_sysroot = swift_sdk_path / "ndk-sysroot"
    if ndk_sysroot.is_symlink():
        ndk_sysroot.unlink()
    elif ndk_sysroot.exists():
        shutil.rmtree(ndk_sysroot)

    (ndk_sysroot / "usr/lib").mkdir(parents=True, exist_ok=True)
    (ndk_sysroot / "usr/include").symlink_to(prebuilt / "sysroot/usr/include")
    for triple_dir in sorted((prebuilt / "sysroot/usr/lib").iterdir()):
        (ndk_sysroot / "usr/lib" / triple_dir.name).symlink_to(triple_dir)

    clang_dirs = [p for p in (prebuilt / "lib/clang").glob("*") if p.is_dir()]
    if len(clang_dirs) != 1:
        raise SystemExit(f"Expected one clang resource directory under {prebuilt}/lib/clang.")
    swift_clang_link = swift_sdk_path / "swift-resources/usr/lib/swift/clang"
    swift_clang_link.parent.mkdir(parents=True, exist_ok=True)
    if swift_clang_link.is_symlink() or swift_clang_link.exists():
        swift_clang_link.unlink()
    swift_clang_link.symlink_to(clang_dirs[0])

    swift_resources = swift_sdk_path / "swift-resources"
    for folder in ("swift", "swift_static"):
        for swiftrt in sorted((swift_resources / "usr/lib").glob(f"{folder}-*/android/*/swiftrt.o")):
            arch = swiftrt.parent.name
            dest_dir = ndk_sysroot / "usr/lib" / folder / "android" / arch
            dest_dir.mkdir(parents=True, exist_ok=True)
            rel_source = os.path.relpath(swiftrt, dest_dir)
            (dest_dir / "swiftrt.o").symlink_to(rel_source)


def verify_ndk(ndk_home: Path) -> Path:
    props = ndk_home / "source.properties"
    if not props.is_file() or f"Pkg.Revision = {REQUIRED_NDK_REVISION}" not in props.read_text(encoding="utf-8"):
        raise SystemExit(
            f"Android NDK r27d ({REQUIRED_NDK_REVISION}) not found at {ndk_home}.\n"
            f"Install it with Android SDK Manager (or set ANDROID_NDK_HOME):\n"
            f'  sdkmanager "ndk;{REQUIRED_NDK_REVISION}" "platforms;android-35" "platform-tools" "emulator"'
        )

    candidates = [
        Path(p)
        for p in glob.glob(
            str(ndk_home / "toolchains/llvm/prebuilt/*/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so")
        )
        if Path(p).is_file()
    ]
    if len(candidates) != 1:
        raise SystemExit(f"Cannot locate unique NDK arm64 libc++_shared.so under {ndk_home}.")
    return candidates[0]


def verify_native_toolchain(
    env: dict[str, str],
    android_build_dir: Path,
    swift_release: str,
    install_sdk: bool = False,
    auto_configure_ndk: bool = False,
) -> tuple[Path, Path]:
    version_cmd = resolve_swift_command(env, swift_release, ["--version"])
    version_out = subprocess.check_output(version_cmd, env=env, text=True)
    if sys.platform == "darwin" and "swiftlang-" in version_out:
        raise SystemExit(
            f"Resolved Xcode's bundled Apple Swift toolchain instead of swift.org Swift {swift_release}:\n"
            f"  {version_out.strip()}\n"
            f"Android cross-compilation requires the official swift.org Swift {swift_release} toolchain:\n"
            f"  swiftly install {swift_release}"
        )
    if f"Swift version {swift_release} (" not in version_out:
        raise SystemExit(
            f"Expected swift.org Swift {swift_release}; got: {version_out.strip()}\n"
            f"Install Swift {swift_release} (for example: swiftly install {swift_release}) or set SWIFT_EXEC."
        )

    ndk_home = Path(env["ANDROID_NDK_HOME"])
    libcxx_shared = verify_ndk(ndk_home)

    expected_bundle = f"swift-{swift_release}-RELEASE_android.artifactbundle"
    swift_sdk_path = Path(env["SWIFT_ANDROID_SDK_PATH"])
    if not (swift_sdk_path / "swift-sdk.json").is_file():
        sdk_url = env.get("OPENSWIFTUI_ANDROID_SWIFT_SDK_URL") or default_android_sdk_url(swift_release)
        if install_sdk:
            print(f"Installing Swift Android SDK ({swift_release}) from {sdk_url} ...")
            install_cmd = resolve_swift_command(env, swift_release, ["sdk", "install", sdk_url])
            subprocess.run(install_cmd, env=env, check=True)
            system = platform.system()
            home = Path(env.get("HOME", str(Path.home())))
            refreshed = discover_swift_android_sdk_path(system, home, {}, swift_release)
            env["SWIFT_ANDROID_SDK_PATH"] = refreshed
            swift_sdk_path = Path(refreshed)
            static_swift = swift_sdk_path / "swift-resources/usr/lib/swift_static-aarch64"
            env["OPENRENDERBOX_LIB_SWIFT_PATH"] = str(static_swift)
            env["OPENSWIFTUI_ANDROID_SWIFT_STATIC_LIB_DIR"] = str(static_swift / "android")
        if not (swift_sdk_path / "swift-sdk.json").is_file():
            install_hint = " ".join(resolve_swift_command(env, swift_release, ["sdk", "install", sdk_url]))
            raise SystemExit(
                f"Missing matching Swift Android SDK: {swift_sdk_path}\n"
                f"Install and configure it automatically with:\n"
                f"  make android_setup ANDROID_INSTALL_SDK=1\n"
                f"or manually with:\n"
                f"  {install_hint}"
            )

    if swift_sdk_path.parent.name != expected_bundle:
        raise SystemExit(f"SWIFT_ANDROID_SDK_PATH must point inside {expected_bundle}.")

    if not (swift_sdk_path / "ndk-sysroot/usr/include").is_dir():
        if install_sdk or auto_configure_ndk:
            print(f"Configuring Swift Android SDK sysroot against NDK at {ndk_home} ...")
            configure_swift_android_sdk_ndk(swift_sdk_path, ndk_home)
        else:
            raise SystemExit(
                f"Swift Android SDK sysroot is not linked to Android NDK yet ({swift_sdk_path / 'ndk-sysroot'}).\n"
                f"Run 'make android_setup' (or '{swift_sdk_path}/scripts/setup-android-sdk.sh') first."
            )

    sdk_store = android_build_dir / "sdk-store" / swift_release
    sdk_store.mkdir(parents=True, exist_ok=True)
    bundle_link = sdk_store / expected_bundle
    if bundle_link.is_symlink() or bundle_link.exists():
        bundle_link.unlink()
    bundle_link.symlink_to(swift_sdk_path.parent)

    return sdk_store, libcxx_shared


def verify_java_runtime(env: dict[str, str]) -> None:
    java = shutil.which("java", path=env.get("PATH"))
    if java is None:
        raise SystemExit("Install JDK 17+ or Android Studio, or set JAVA_HOME.")
    res = subprocess.run([java, "-version"], env=env, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise SystemExit(
            "No working JDK 17+ runtime found (`java -version` failed).\n"
            "Install JDK 17+ or Android Studio, or set JAVA_HOME."
        )


def stage_jni_libs(
    swift_sdk_path: Path,
    libcxx_shared: Path,
    built_product_so: Path,
    jni_root: Path,
) -> None:
    arm64_dir = jni_root / "arm64-v8a"
    if arm64_dir.exists():
        shutil.rmtree(arm64_dir)
    arm64_dir.mkdir(parents=True, exist_ok=True)

    runtime_dir = swift_sdk_path / "swift-resources/usr/lib/swift-aarch64/android"
    for so_file in sorted(runtime_dir.glob("*.so")):
        shutil.copy2(so_file, arm64_dir / so_file.name)
    shutil.copy2(libcxx_shared, arm64_dir / libcxx_shared.name)
    shutil.copy2(built_product_so, arm64_dir / built_product_so.name)


def build_android_sample(
    repo_root: Path,
    sample: str,
    configuration: str,
    output_dir: Path,
    prepare_only: bool = False,
    install_sdk: bool = False,
) -> Path:
    android_dir = repo_root / "Android"
    samples = ensure_sample_symlinks(repo_root, android_dir)
    if not prepare_only and sample not in samples:
        available = ", ".join(samples)
        raise SystemExit(f"Unknown SAMPLE '{sample}'. Select from: {available}.")

    config_lower = configuration.lower()
    if config_lower not in {"debug", "release"}:
        raise SystemExit(f"Unsupported CONFIGURATION '{configuration}'. Use Debug or Release.")

    env, swift_release, triple = prepare_build_environment(repo_root, os.environ)
    verify_local_sibling_checkouts(repo_root, env)
    android_build_dir = repo_root / ".build" / "android-samples"
    swift_scratch = android_build_dir / "swift"
    cache_dir = android_build_dir / "cache"

    sdk_store, libcxx_shared = verify_native_toolchain(
        env,
        android_build_dir,
        swift_release,
        install_sdk=install_sdk,
        auto_configure_ndk=prepare_only,
    )
    sdk_args = ["--swift-sdks-path", str(sdk_store), "--swift-sdk", triple, "--triple", triple]

    resolve_cmd = resolve_swift_command(
        env,
        swift_release,
        [
            "package",
            "--package-path",
            str(android_dir),
            "--scratch-path",
            str(swift_scratch),
            "--cache-path",
            str(cache_dir),
            *sdk_args,
            "resolve",
        ],
    )
    subprocess.run(resolve_cmd, cwd=repo_root, env=env, check=True)

    if prepare_only:
        print(f"Dependencies ready. Android Studio project: {android_dir}")
        return android_dir

    android_jar = Path(env["ANDROID_HOME"]) / "platforms/android-35/android.jar"
    if not android_jar.is_file():
        raise SystemExit(
            f"Android SDK Platform 35 not found at {android_jar}.\n"
            f'Install it with Android SDK Manager (or set ANDROID_HOME): sdkmanager "platforms;android-35"'
        )
    verify_java_runtime(env)

    product = f"{sample}Android"
    build_cmd = resolve_swift_command(
        env,
        swift_release,
        [
            "build",
            "--package-path",
            str(android_dir),
            "--scratch-path",
            str(swift_scratch),
            "--cache-path",
            str(cache_dir),
            *sdk_args,
            "-c",
            config_lower,
            "--static-swift-stdlib",
            "--product",
            product,
        ],
    )
    subprocess.run(build_cmd, cwd=repo_root, env=env, check=True)

    built_so = swift_scratch / triple / config_lower / f"lib{product}.so"
    if not built_so.is_file():
        raise SystemExit(f"Expected native library not found: {built_so}")

    jni_root = android_build_dir / "jniLibs" / sample / config_lower
    stage_jni_libs(Path(env["SWIFT_ANDROID_SDK_PATH"]), libcxx_shared, built_so, jni_root)

    gradle_task = f":app:assemble{'Debug' if config_lower == 'debug' else 'Release'}"
    display_name = DISPLAY_NAMES.get(sample, sample)
    gradle_cmd = [
        "bash",
        str(android_dir / "gradlew"),
        "-p",
        str(android_dir),
        "--no-daemon",
        f"-Psample={sample}",
        f"-PdisplayName={display_name}",
        f"-PswiftJniLibsDir={jni_root}",
        gradle_task,
    ]
    subprocess.run(gradle_cmd, cwd=repo_root, env=env, check=True)

    gradle_apk = (
        android_dir
        / "app"
        / "build"
        / "outputs"
        / "apk"
        / config_lower
        / f"app-arm64-v8a-{config_lower}.apk"
    )
    if not gradle_apk.is_file():
        raise SystemExit(f"Built APK not found at {gradle_apk}")

    output_dir.mkdir(parents=True, exist_ok=True)
    dest_apk = output_dir / f"{sample}-{config_lower}-arm64-v8a.apk"
    shutil.copy2(gradle_apk, dest_apk)
    print(f"APK: {dest_apk}")
    return dest_apk


def select_or_start_device(env: dict[str, str], android_build_dir: Path, avd: str, serial: str) -> str:
    if avd and serial:
        raise SystemExit("Choose either --avd or --serial/ANDROID_SERIAL.")
    adb = shutil.which("adb", path=env.get("PATH"))
    if adb is None:
        raise SystemExit("Install Android SDK platform-tools, or set ANDROID_HOME.")

    def running_emulators() -> list[str]:
        out = subprocess.check_output([adb, "devices"], env=env, text=True)
        return [
            line.split()[0]
            for line in out.splitlines()
            if line.startswith("emulator-") and line.split()[-1] == "device"
        ]

    def find_avd_serial(target_avd: str) -> str:
        for candidate in running_emulators():
            res = subprocess.run(
                [adb, "-s", candidate, "emu", "avd", "name"],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                first = res.stdout.replace("\r", "").splitlines()
                if first and first[0].strip() == target_avd:
                    return candidate
        return ""

    if avd:
        emulator = shutil.which("emulator", path=env.get("PATH"))
        if emulator is None:
            raise SystemExit("Install Android SDK emulator.")
        avds = subprocess.check_output([emulator, "-list-avds"], env=env, text=True).splitlines()
        if avd not in [a.strip() for a in avds]:
            raise SystemExit(f"Unknown AVD: {avd}")
        found = find_avd_serial(avd)
        if not found:
            android_build_dir.mkdir(parents=True, exist_ok=True)
            log_path = android_build_dir / "emulator.log"
            with log_path.open("w", encoding="utf-8") as log_file:
                proc = subprocess.Popen(
                    [emulator, "-avd", avd, "-no-snapshot-save"],
                    env=env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                )
            deadline = time.monotonic() + 180
            while not found:
                if proc.poll() is not None:
                    raise SystemExit(f"Emulator exited early. See {log_path}")
                if time.monotonic() >= deadline:
                    raise SystemExit(f"Timed out starting {avd}. See {log_path}")
                time.sleep(2)
                found = find_avd_serial(avd)
        serial = found
    elif not serial:
        out = subprocess.check_output([adb, "devices"], env=env, text=True)
        devices = [
            line.split()[0]
            for line in out.splitlines()[1:]
            if len(line.split()) >= 2 and line.split()[1] == "device"
        ]
        if len(devices) != 1:
            raise SystemExit("Connect one arm64 device, or pass --serial SERIAL / --avd NAME.")
        serial = devices[0]

    deadline = time.monotonic() + 180
    while True:
        res = subprocess.run(
            [adb, "-s", serial, "shell", "getprop", "sys.boot_completed"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.stdout.strip() == "1":
            break
        if time.monotonic() >= deadline:
            raise SystemExit(f"Timed out waiting for {serial} to finish booting.")
        time.sleep(2)

    abi = subprocess.check_output(
        [adb, "-s", serial, "shell", "getprop", "ro.product.cpu.abilist"],
        env=env,
        text=True,
    ).strip()
    if "arm64-v8a" not in abi.split(","):
        raise SystemExit(f"This APK requires arm64-v8a; {serial} supports {abi}.")
    sdk_str = subprocess.check_output(
        [adb, "-s", serial, "shell", "getprop", "ro.build.version.sdk"],
        env=env,
        text=True,
    ).strip()
    if not sdk_str.isdigit() or int(sdk_str) < 28:
        raise SystemExit(f"This APK requires API 28+; got {sdk_str}.")

    return serial


def launch_android_sample(
    repo_root: Path,
    sample: str,
    apk_path: Path,
    avd: str,
    serial: str,
    print_tree: bool,
) -> None:
    if not apk_path.is_file():
        raise SystemExit(f"APK not found: {apk_path}")
    env, _, _ = prepare_build_environment(repo_root, os.environ)
    android_build_dir = repo_root / ".build" / "android-samples"
    resolved_serial = select_or_start_device(env, android_build_dir, avd, serial)
    adb = shutil.which("adb", path=env.get("PATH"))
    assert adb is not None

    app_id = f"org.openswiftui.samples.{sample.lower()}"
    activity = f"{app_id}/org.openswiftui.samples.MainActivity"
    subprocess.run([adb, "-s", resolved_serial, "install", "-r", str(apk_path)], env=env, check=True)
    subprocess.run(
        [
            adb,
            "-s",
            resolved_serial,
            "shell",
            "am",
            "start",
            "-S",
            "-W",
            "-n",
            activity,
            "--ez",
            "printTree",
            "true" if print_tree else "false",
        ],
        env=env,
        check=True,
    )
    time.sleep(2)
    pid_check = subprocess.run(
        [adb, "-s", resolved_serial, "shell", "pidof", app_id],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if pid_check.returncode != 0 or not pid_check.stdout.strip():
        raise SystemExit(f"App exited; inspect: adb -s {resolved_serial} logcat -d -b crash")
    print(f"Running {app_id} on {resolved_serial}.")


def main() -> int:
    args = parse_args()
    if args.no_build and (args.prepare or not args.run):
        raise SystemExit("--no-build requires --run and cannot be combined with --prepare.")

    repo_root = Path(__file__).resolve().parent.parent
    config_lower = args.configuration.lower()
    output_dir = (
        Path(args.output).resolve()
        if args.output
        else (repo_root / "Android" / "dist" / args.sample).resolve()
    )

    if args.prepare:
        build_android_sample(
            repo_root=repo_root,
            sample=args.sample,
            configuration=args.configuration,
            output_dir=output_dir,
            prepare_only=True,
            install_sdk=args.install_sdk,
        )
        return 0

    if args.no_build:
        apk_path = output_dir / f"{args.sample}-{config_lower}-arm64-v8a.apk"
    else:
        apk_path = build_android_sample(
            repo_root=repo_root,
            sample=args.sample,
            configuration=args.configuration,
            output_dir=output_dir,
            install_sdk=args.install_sdk,
        )

    if args.run:
        serial = args.serial or os.environ.get("ANDROID_SERIAL", "")
        launch_android_sample(
            repo_root=repo_root,
            sample=args.sample,
            apk_path=apk_path,
            avd=args.avd,
            serial=serial,
            print_tree=args.print_tree,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
