#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import subprocess
import sys


def run(*command):
    subprocess.run(command, check=True)


def output(*command):
    return subprocess.check_output(command, text=True)


def simulator(platform, device_id=""):
    runtimes = {
        "iOS": (".iOS-",),
        "visionOS": (".xrOS-", ".visionOS-"),
    }
    devices = json.loads(output("xcrun", "simctl", "list", "devices", "available", "--json"))
    candidates = [
        device
        for runtime, entries in devices["devices"].items()
        if any(name in runtime for name in runtimes[platform])
        for device in entries
        if device.get("isAvailable", False)
        and (not device_id or device["udid"] == device_id)
    ]
    if not candidates:
        raise ValueError(f"No available {platform} simulator matches id={device_id or '<auto>'}.")
    return next((device for device in candidates if device["state"] == "Booted"), candidates[0])


def main():
    samples = sorted(
        project.parent.name
        for project in (Path(__file__).resolve().parent.parent / "Samples").glob("*/Project.swift")
        if project.is_file()
    )
    parser = argparse.ArgumentParser(description="Build and run an OpenSwiftUI sample on an Apple platform.")
    parser.add_argument("platform", choices=["iOS", "macOS", "visionOS"])
    parser.add_argument("--sample", choices=samples, default="HelloWorld")
    parser.add_argument("--configuration", default="Debug")
    parser.add_argument("--destination", default="", help="Xcode destination; defaults to this Mac or an available simulator.")
    parser.add_argument("--development-team", default="", help="Team ID for automatic code signing.")
    args = parser.parse_args()
    destination = args.destination.strip()
    if destination.startswith("generic/"):
        raise ValueError("Run targets require a specific device, not a generic destination.")
    if not destination:
        if args.platform == "macOS":
            destination = "platform=macOS"
        else:
            device = simulator(args.platform)
            destination = f"platform={args.platform} Simulator,id={device['udid']}"

    scheme = f"{args.sample}App"
    build = [
        "xcodebuild", "-workspace", "App/OpenSwiftUISamples.xcworkspace",
        "-scheme", scheme, "-configuration", args.configuration,
        "-destination", destination,
    ]
    if args.development_team:
        build += [f"DEVELOPMENT_TEAM={args.development_team}", "CODE_SIGN_STYLE=Automatic"]
    targets = json.loads(output(*build, "-showBuildSettings", "-json", "-quiet"))
    settings = next(target["buildSettings"] for target in targets if target["target"] == scheme)
    platforms = {
        "macOS": ("macosx",),
        "iOS": ("iphoneos", "iphonesimulator"),
        "visionOS": ("xros", "xrsimulator"),
    }
    platform = settings["PLATFORM_NAME"]
    if platform not in platforms[args.platform]:
        raise ValueError(f"DESTINATION must select a {args.platform} device; Xcode selected {platform}.")
    device_id = settings.get("TARGET_DEVICE_IDENTIFIER", "")
    if args.platform != "macOS" and (not device_id or "placeholder" in device_id):
        raise ValueError("DESTINATION must select a specific device by id or name.")
    device = simulator(args.platform, device_id) if platform.endswith("simulator") else None
    if args.platform != "macOS" and device is None:
        build.append("-allowProvisioningUpdates")
    run(*build, "build")
    app = Path(settings["TARGET_BUILD_DIR"]) / settings["FULL_PRODUCT_NAME"]

    if args.platform == "macOS":
        run("open", "-n", str(app))
        return

    if device is None:
        run("xcrun", "devicectl", "device", "install", "app", "--device", device_id, str(app))
        run("xcrun", "devicectl", "device", "process", "launch", "--device", device_id,
            "--terminate-existing", settings["PRODUCT_BUNDLE_IDENTIFIER"])
        return

    if device["state"] != "Booted":
        run("xcrun", "simctl", "boot", device_id)
    run("xcrun", "simctl", "bootstatus", device_id, "-b")
    developer = Path(output("xcode-select", "-p").strip())
    run("open", "-a", str(developer / "Applications/Simulator.app"), "--args", "-CurrentDeviceUDID", device_id)
    run("xcrun", "simctl", "install", device_id, str(app))
    run("xcrun", "simctl", "launch", "--terminate-running-process", device_id, settings["PRODUCT_BUNDLE_IDENTIFIER"])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
    except ValueError as error:
        sys.exit(str(error))
