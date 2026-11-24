#!/usr/bin/env python3

from __future__ import annotations

import argparse
import functools
import http.server
import os
from pathlib import Path
import shutil
import subprocess
import sys


DISPLAY_NAMES = {
    "HelloWorld": "Hello World",
    "Game2048": "2048",
}

BACKGROUNDS = {
    "HelloWorld": "#ffffff",
    "Game2048": "#f5f0e6",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare, build, and optionally serve an OpenSwiftUI sample for Web deployment."
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
        help="Output directory for the deployable static site (default: Web/dist/<Sample>).",
    )
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Verify the Swift WASM toolchain/SDK and resolve Web SwiftPM dependencies.",
    )
    parser.add_argument(
        "--install-sdk",
        action="store_true",
        help="Automatically install the matching swift.org WASM Swift SDK if missing.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Serve the built static site over local HTTP after building.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP bind host when --serve is set (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP port when --serve is set (default: 8000).",
    )
    return parser.parse_args()


def validate_environment(env: dict[str, str]) -> None:
    if env.get("OPENSWIFTUI") == "0":
        raise SystemExit("Web builds require OpenSwiftUI source (osui-source), not sui.")
    if env.get("OPENSWIFTUI_BINARY") == "1":
        raise SystemExit("Web builds require OpenSwiftUI source (osui-source), not osui-binary.")


def ensure_sample_symlinks(repo_root: Path, web_dir: Path) -> list[str]:
    samples_dir = repo_root / "Samples"
    web_sources_dir = web_dir / "Sources"
    web_sources_dir.mkdir(parents=True, exist_ok=True)

    discovered: list[str] = []
    for project_file in sorted(samples_dir.glob("*/Project.swift")):
        sample_name = project_file.parent.name
        discovered.append(sample_name)
        link_path = web_sources_dir / sample_name
        relative_target = Path("../../Samples") / sample_name / "Sources"
        if link_path.is_symlink():
            if Path(os.readlink(link_path)) == relative_target:
                continue
            link_path.unlink()
        elif link_path.exists():
            continue
        link_path.symlink_to(relative_target)
    return discovered


def prepare_web_environment(base_env: dict[str, str]) -> dict[str, str]:
    validate_environment(base_env)
    env = base_env.copy()

    use_local = env.get("OPENSWIFTUI_USE_LOCAL_DEPS") == "1"
    local_flag = "1" if use_local else "0"
    env["OPENSWIFTUI_USE_LOCAL_DEPS"] = local_flag
    env["OPENATTRIBUTEGRAPH_USE_LOCAL_DEPS"] = local_flag
    env["OPENRENDERBOX_USE_LOCAL_DEPS"] = local_flag

    env["OPENSWIFTUI_WASI"] = "1"
    env["OPENSWIFTUI_BUILD_FOR_DARWIN_PLATFORM"] = "0"
    env["OPENATTRIBUTEGRAPH_BUILD_FOR_DARWIN_PLATFORM"] = "0"
    env["OPENRENDERBOX_BUILD_FOR_DARWIN_PLATFORM"] = "0"
    env["OPENCOREGRAPHICS_BUILD_FOR_DARWIN_PLATFORM"] = "0"
    env["OPENSWIFTUI_LIBRARY_EVOLUTION"] = "0"
    env["OPENATTRIBUTEGRAPH_LIBRARY_EVOLUTION"] = "0"
    env["OPENRENDERBOX_LIBRARY_EVOLUTION"] = "0"
    env["OPENCOREGRAPHICS_LIBRARY_EVOLUTION"] = "0"
    env["OPENSWIFTUI_RENDER_GTK"] = "0"
    env["OPENSWIFTUI_OPENATTRIBUTESHIMS_ATTRIBUTEGRAPH"] = "0"
    env["OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE"] = "1"
    env["OPENATTRIBUTEGRAPH_OPENATTRIBUTESHIMS_COMPUTE"] = "1"
    env["OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE_BINARY"] = "0"
    env["OPENATTRIBUTEGRAPH_OPENATTRIBUTESHIMS_COMPUTE_BINARY"] = "0"
    env["OPENSWIFTUI_SWIFT_TOOLCHAIN_SUPPORTED"] = "0"

    if "OPENSWIFTUI_WEB_COMPUTE_SOURCE_VERSION" in env:
        env["OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_VERSION"] = env[
            "OPENSWIFTUI_WEB_COMPUTE_SOURCE_VERSION"
        ]
    else:
        env.pop("OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_VERSION", None)
        env.pop("OPENATTRIBUTEGRAPH_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_VERSION", None)

    return env


def default_wasm_sdk_url(swift_release: str, swift_sdk_id: str) -> str:
    return (
        f"https://download.swift.org/swift-{swift_release}-release/wasm-sdk/"
        f"swift-{swift_release}-RELEASE/{swift_sdk_id}.artifactbundle.tar.gz"
    )


def build_swift_command(
    env: dict[str, str],
    swift_release: str,
    swift_args: list[str],
    home_dir: Path | None = None,
) -> list[str]:
    explicit_swift = env.get("OPENSWIFTUI_WEB_SWIFT_BIN")
    if explicit_swift:
        return [explicit_swift, *swift_args]

    home = home_dir or Path(env.get("HOME", str(Path.home())))
    swiftly = shutil.which("swiftly", path=env.get("PATH"))
    if swiftly is None:
        candidate = home / ".swiftly" / "bin" / "swiftly"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            swiftly = str(candidate)

    if swiftly:
        return [swiftly, "run", "swift", *swift_args, f"+{swift_release}"]

    toolchain_name = f"swift-{swift_release}-RELEASE.xctoolchain"
    for toolchain_root in (
        home / "Library" / "Developer" / "Toolchains",
        Path("/Library/Developer/Toolchains"),
    ):
        toolchain_swift = toolchain_root / toolchain_name / "usr" / "bin" / "swift"
        if toolchain_swift.is_file() and os.access(toolchain_swift, os.X_OK):
            return [str(toolchain_swift), *swift_args]

    return ["swift", *swift_args]


def verify_web_toolchain_and_sdk(
    env: dict[str, str],
    swift_release: str,
    swift_sdk_id: str,
    install_sdk: bool = False,
) -> None:
    version_cmd = build_swift_command(env, swift_release, ["--version"])
    try:
        version_proc = subprocess.run(
            version_cmd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            f"Swift {swift_release} toolchain not found ({exc}).\n"
            f"Install swiftly (https://www.swift.org/install/) and run:\n"
            f"  swiftly install {swift_release}"
        ) from exc

    combined_version = f"{version_proc.stdout}\n{version_proc.stderr}".strip()
    if version_proc.returncode != 0:
        raise SystemExit(
            f"Unable to run Swift {swift_release} toolchain:\n{combined_version}\n\n"
            f"Install Swift {swift_release} first, for example:\n"
            f"  swiftly install {swift_release}"
        )

    if sys.platform == "darwin" and "swiftlang-" in combined_version:
        raise SystemExit(
            f"Resolved Xcode's bundled Apple Swift toolchain instead of swift.org Swift {swift_release}.\n"
            f"WASI Swift SDK builds require an open-source swift.org toolchain.\n"
            f"Install Swift {swift_release} via swiftly or swift.org:\n"
            f"  swiftly install {swift_release}"
        )

    sdk_list_cmd = build_swift_command(env, swift_release, ["sdk", "list"])
    sdk_proc = subprocess.run(
        sdk_list_cmd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    installed_sdks = {line.strip() for line in sdk_proc.stdout.splitlines() if line.strip()}
    if swift_sdk_id in installed_sdks:
        return

    sdk_url = env.get("OPENSWIFTUI_WEB_SWIFT_SDK_URL") or default_wasm_sdk_url(
        swift_release, swift_sdk_id
    )
    if install_sdk:
        print(f"Installing Swift WASM SDK '{swift_sdk_id}' from {sdk_url} ...")
        install_cmd = build_swift_command(env, swift_release, ["sdk", "install", sdk_url])
        subprocess.run(install_cmd, env=env, check=True)
        return

    install_hint = " ".join(build_swift_command(env, swift_release, ["sdk", "install", sdk_url]))
    raise SystemExit(
        f"Swift WASM SDK '{swift_sdk_id}' is not installed.\n"
        f"Install it automatically with:\n"
        f"  make web_setup WEB_INSTALL_SDK=1\n"
        f"or manually with:\n"
        f"  {install_hint}"
    )


def prepare_web_workspace(
    repo_root: Path,
    install_sdk: bool = False,
) -> None:
    web_dir = repo_root / "Web"
    ensure_sample_symlinks(repo_root, web_dir)
    env = prepare_web_environment(os.environ)

    if env.get("OPENSWIFTUI_USE_LOCAL_DEPS") == "1":
        local_osui = (repo_root.parent / "OpenSwiftUI").resolve()
        if not local_osui.is_dir():
            raise SystemExit(
                f"OPENSWIFTUI_USE_LOCAL_DEPS=1 requires a sibling OpenSwiftUI checkout at {local_osui}."
            )

    swift_release = env.get("OPENSWIFTUI_WEB_SWIFT_RELEASE", "6.3.2")
    swift_sdk_id = env.get("OPENSWIFTUI_WEB_SWIFT_SDK_ID", f"swift-{swift_release}-RELEASE_wasm")
    verify_web_toolchain_and_sdk(
        env=env,
        swift_release=swift_release,
        swift_sdk_id=swift_sdk_id,
        install_sdk=install_sdk,
    )

    resolve_cmd = build_swift_command(
        env,
        swift_release,
        [
            "package",
            "--build-system",
            "native",
            "--swift-sdk",
            swift_sdk_id,
            "resolve",
        ],
    )
    subprocess.run(resolve_cmd, cwd=web_dir, env=env, check=True)
    print(f"Web workspace ready (Swift {swift_release}, SDK {swift_sdk_id}).")


def build_web_sample(
    repo_root: Path,
    sample: str,
    configuration: str,
    output_dir: Path,
    check_toolchain: bool = False,
    install_sdk: bool = False,
) -> None:
    web_dir = repo_root / "Web"
    samples = ensure_sample_symlinks(repo_root, web_dir)
    if sample not in samples:
        available = ", ".join(samples)
        raise SystemExit(f"Unknown SAMPLE '{sample}'. Select from: {available}.")

    config_lower = configuration.lower()
    if config_lower not in {"debug", "release"}:
        raise SystemExit(f"Unsupported CONFIGURATION '{configuration}'. Use Debug or Release.")

    env = prepare_web_environment(os.environ)
    swift_release = env.get("OPENSWIFTUI_WEB_SWIFT_RELEASE", "6.3.2")
    swift_sdk_id = env.get("OPENSWIFTUI_WEB_SWIFT_SDK_ID", f"swift-{swift_release}-RELEASE_wasm")

    if check_toolchain:
        verify_web_toolchain_and_sdk(
            env=env,
            swift_release=swift_release,
            swift_sdk_id=swift_sdk_id,
            install_sdk=install_sdk,
        )

    product = f"{sample}Web"
    title = f"{DISPLAY_NAMES.get(sample, sample)} — OpenSwiftUI Web"
    background = BACKGROUNDS.get(sample, "#111216")
    output_dir.mkdir(parents=True, exist_ok=True)

    package_args = [
        "package",
        "--build-system",
        "native",
        "--swift-sdk",
        swift_sdk_id,
        "plugin",
        "--allow-writing-to-package-directory",
        "web-deploy",
        "--product",
        product,
        "--configuration",
        config_lower,
        "--title",
        title,
        "--background",
        background,
        "--output",
        str(output_dir),
    ]

    cmd = build_swift_command(env, swift_release, package_args)
    subprocess.run(cmd, cwd=web_dir, env=env, check=True)


def serve_directory(directory: Path, host: str, port: int) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    with http.server.ThreadingHTTPServer((host, port), handler) as server:
        print(f"Serving {directory} at http://{host}:{port}/ (Ctrl+C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped server.")


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    if args.prepare:
        prepare_web_workspace(repo_root=repo_root, install_sdk=args.install_sdk)
        return 0

    output_dir = (
        Path(args.output).resolve()
        if args.output
        else (repo_root / "Web" / "dist" / args.sample).resolve()
    )
    build_web_sample(
        repo_root=repo_root,
        sample=args.sample,
        configuration=args.configuration,
        output_dir=output_dir,
        check_toolchain=True,
        install_sdk=args.install_sdk,
    )
    if args.serve:
        serve_directory(output_dir, args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
