import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "run_apple", Path(__file__).resolve().parents[1] / "run-apple.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunAppleTests(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "PLATFORM_NAME": "iphoneos",
            "TARGET_DEVICE_IDENTIFIER": "phone-id",
            "TARGET_BUILD_DIR": "/tmp/Sample Products",
            "FULL_PRODUCT_NAME": "HelloWorldApp.app",
            "PRODUCT_BUNDLE_IDENTIFIER": "org.example.HelloWorldApp",
        }
        self.devices = {
            "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
                {"udid": "stopped-sim", "state": "Shutdown", "isAvailable": True},
                {"udid": "booted-sim", "state": "Booted", "isAvailable": True},
            ],
            "com.apple.CoreSimulator.SimRuntime.xrOS-26-5": [
                {"udid": "vision-sim", "state": "Shutdown", "isAvailable": True},
            ],
        }
        self.commands = []

    def output(self, *command):
        self.commands.append(command)
        if command[:4] == ("xcrun", "simctl", "list", "devices"):
            return json.dumps({"devices": self.devices})
        if command[0] == "xcodebuild" and "-showBuildSettings" in command:
            return json.dumps([{"target": "HelloWorldApp", "buildSettings": self.settings}])
        if command == ("xcode-select", "-p"):
            return "/Applications/Xcode.app/Contents/Developer\n"
        self.fail(f"Unexpected command: {command}")

    def run_main(self, *arguments, failure=None):
        def run(*command):
            self.commands.append(command)
            if failure and failure(command):
                raise subprocess.CalledProcessError(65, command)

        with patch("sys.argv", ["run-apple.py", *arguments]), \
             patch.object(runner, "output", side_effect=self.output), \
             patch.object(runner, "run", side_effect=run):
            runner.main()

    def builds(self):
        return [command for command in self.commands if command[0] == "xcodebuild" and "build" in command]

    def test_physical_device_build_install_and_launch(self):
        for platform, sdk in (("iOS", "iphoneos"), ("visionOS", "xros")):
            with self.subTest(platform=platform):
                self.commands.clear()
                self.settings["PLATFORM_NAME"] = sdk
                destination = f"platform={platform},id=phone-id"
                self.run_main(platform, "--destination", destination,
                              "--configuration", "Release", "--development-team", "TEAMID")
                build, = self.builds()
                self.assertEqual(build[build.index("-destination") + 1], destination)
                self.assertEqual(build[build.index("-configuration") + 1], "Release")
                self.assertIn("DEVELOPMENT_TEAM=TEAMID", build)
                self.assertIn("CODE_SIGN_STYLE=Automatic", build)
                self.assertIn("-allowProvisioningUpdates", build)
                self.assertIn(("xcrun", "devicectl", "device", "install", "app", "--device",
                               "phone-id", "/tmp/Sample Products/HelloWorldApp.app"), self.commands)
                self.assertIn(("xcrun", "devicectl", "device", "process", "launch", "--device",
                               "phone-id", "--terminate-existing", "org.example.HelloWorldApp"), self.commands)
                self.assertFalse(any(command[:2] == ("xcrun", "simctl") for command in self.commands))

    def test_simulator_name_uses_xcode_resolved_identifier(self):
        self.settings.update(PLATFORM_NAME="iphonesimulator", TARGET_DEVICE_IDENTIFIER="stopped-sim")
        self.run_main("iOS", "--destination", "platform=iOS Simulator,name=My iPhone,OS=26.5")
        self.assertIn(("xcrun", "simctl", "boot", "stopped-sim"), self.commands)
        self.assertIn(("xcrun", "simctl", "install", "stopped-sim",
                       "/tmp/Sample Products/HelloWorldApp.app"), self.commands)
        self.assertIn(("xcrun", "simctl", "launch", "--terminate-running-process", "stopped-sim",
                       "org.example.HelloWorldApp"), self.commands)
        self.assertNotIn("-allowProvisioningUpdates", self.builds()[0])

    def test_default_simulator_prefers_booted_device_on_requested_platform(self):
        for platform, sdk, device_id in (("iOS", "iphonesimulator", "booted-sim"),
                                        ("visionOS", "xrsimulator", "vision-sim")):
            with self.subTest(platform=platform):
                self.commands.clear()
                self.settings.update(PLATFORM_NAME=sdk, TARGET_DEVICE_IDENTIFIER=device_id)
                self.run_main(platform)
                self.assertIn(f"platform={platform} Simulator,id={device_id}", self.builds()[0])
                self.assertFalse(any(command[:2] == ("xcrun", "devicectl") for command in self.commands))
                if platform == "iOS":
                    self.assertNotIn(("xcrun", "simctl", "boot", device_id), self.commands)

    def test_macos_opens_built_app(self):
        self.settings.update(PLATFORM_NAME="macosx")
        self.settings.pop("TARGET_DEVICE_IDENTIFIER")
        self.run_main("macOS")
        self.assertIn("platform=macOS", self.builds()[0])
        self.assertEqual(self.commands[-1], ("open", "-n", "/tmp/Sample Products/HelloWorldApp.app"))
        self.assertFalse(any(command[0] == "xcrun" for command in self.commands))

    def test_generic_destination_rejected_before_build(self):
        with self.assertRaisesRegex(ValueError, "concrete|specific"):
            self.run_main("iOS", "--destination", "generic/platform=iOS")
        self.assertFalse(self.commands)

    def test_wrong_platform_rejected_before_build(self):
        self.settings["PLATFORM_NAME"] = "xros"
        with self.assertRaisesRegex(ValueError, "iOS"):
            self.run_main("iOS", "--destination", "platform=visionOS,id=phone-id")
        self.assertFalse(self.builds())

    def test_missing_device_identifier_rejected_before_build(self):
        self.settings.pop("TARGET_DEVICE_IDENTIFIER")
        with self.assertRaisesRegex(ValueError, "device|identifier"):
            self.run_main("iOS", "--destination", "platform=iOS")
        self.assertFalse(self.builds())

    def test_failed_build_does_not_install_or_launch(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_main("iOS", "--destination", "platform=iOS,id=phone-id",
                          failure=lambda command: command[0] == "xcodebuild")
        self.assertFalse(any(command[:2] == ("xcrun", "devicectl") for command in self.commands))

    def test_failed_install_does_not_launch(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_main("iOS", "--destination", "platform=iOS,id=phone-id",
                          failure=lambda command: "install" in command)
        self.assertFalse(any("launch" in command for command in self.commands))


if __name__ == "__main__":
    unittest.main()
