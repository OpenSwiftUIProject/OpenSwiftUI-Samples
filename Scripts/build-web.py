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
        description="Build and optionally serve an OpenSwiftUI sample for Web deployment."
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


def build_web_sample(
    repo_root: Path,
    sample: str,
    configuration: str,
    output_dir: Path,
) -> None:
    web_dir = repo_root / "Web"
    samples = ensure_sample_symlinks(repo_root, web_dir)
    if sample not in samples:
        available = ", ".join(samples)
        raise SystemExit(f"Unknown SAMPLE '{sample}'. Select from: {available}.")

    config_lower = configuration.lower()
    if config_lower not in {"debug", "release"}:
        raise SystemExit(f"Unsupported CONFIGURATION '{configuration}'. Use Debug or Release.")

    env = os.environ.copy()
    validate_environment(env)

    env["OPENSWIFTUI_WASI"] = "1"
    env["OPENSWIFTUI_BUILD_FOR_DARWIN_PLATFORM"] = "0"
    env["OPENSWIFTUI_RENDER_GTK"] = "0"
    env["OPENSWIFTUI_OPENATTRIBUTESHIMS_ATTRIBUTEGRAPH"] = "0"
    env["OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE"] = "1"
    env["OPENSWIFTUI_SWIFT_TOOLCHAIN_SUPPORTED"] = "0"
    if "OPENSWIFTUI_WEB_COMPUTE_SOURCE_VERSION" in env:
        env["OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_VERSION"] = env[
            "OPENSWIFTUI_WEB_COMPUTE_SOURCE_VERSION"
        ]
    else:
        env.pop("OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_VERSION", None)

    swift_release = env.get("OPENSWIFTUI_WEB_SWIFT_RELEASE", "6.3.2")
    swift_sdk_id = env.get("OPENSWIFTUI_WEB_SWIFT_SDK_ID", f"swift-{swift_release}-RELEASE_wasm")
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

    swiftly = shutil.which("swiftly", path=env.get("PATH"))
    if swiftly is None:
        candidate = Path.home() / ".swiftly" / "bin" / "swiftly"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            swiftly = str(candidate)

    if swiftly:
        cmd = [swiftly, "run", "swift", *package_args, f"+{swift_release}"]
    else:
        cmd = ["swift", *package_args]

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
    )
    if args.serve:
        serve_directory(output_dir, args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
