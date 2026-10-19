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


def simulator(platform, device_id):
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
        raise ValueError(f"No available {platform} simulator matches DEVICE={device_id or '<auto>'}.")
    return next((device for device in candidates if device["state"] == "Booted"), candidates[0])


def main():
    parser = argparse.ArgumentParser(description="Build and run Game2048 on an Apple platform.")
    parser.add_argument("platform", choices=["iOS", "macOS", "visionOS"])
    parser.add_argument("--configuration", default="Debug")
    parser.add_argument("--device", default="", help="Simulator UDID; defaults to a booted or available simulator.")
    args = parser.parse_args()
    if args.platform == "macOS" and args.device:
        raise ValueError("DEVICE applies only to simulator runs.")

    device = None if args.platform == "macOS" else simulator(args.platform, args.device)
    destination = "platform=macOS" if device is None else f"platform={args.platform} Simulator,id={device['udid']}"
    build = [
        "xcodebuild", "-workspace", "App/Game2048App.xcworkspace",
        "-scheme", "Game2048App", "-configuration", args.configuration,
        "-destination", destination,
    ]
    run(*build, "build")
    targets = json.loads(output(*build, "-showBuildSettings", "-json", "-quiet"))
    settings = next(target["buildSettings"] for target in targets if target["target"] == "Game2048App")
    app = Path(settings["TARGET_BUILD_DIR"]) / settings["FULL_PRODUCT_NAME"]

    if device is None:
        run("open", "-n", str(app))
        return

    device_id = device["udid"]
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
