import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch


spec = importlib.util.spec_from_file_location(
    "build_android", Path(__file__).resolve().parents[1] / "build-android.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildAndroidTests(unittest.TestCase):
    def create_fake_workspace(self, root: Path, include_siblings: bool = True) -> Path:
        repo_root = root / "OpenSwiftUI-Samples"
        for sample in ("HelloWorld", "Game2048"):
            sample_dir = repo_root / "Samples" / sample
            (sample_dir / "Sources").mkdir(parents=True)
            (sample_dir / "Project.swift").write_text("// stub\n", encoding="utf-8")
        android_dir = repo_root / "Android"
        android_dir.mkdir(parents=True)
        (android_dir / "gradlew").write_text("#!/bin/sh\n", encoding="utf-8")
        if include_siblings:
            (root / "OpenSwiftUI").mkdir(parents=True)
            (root / "UIKit-cross-platform").mkdir(parents=True)
            (root / "UIKit-cross-platform" / "build.gradle").write_text("// stub\n", encoding="utf-8")
        return repo_root

    def test_validate_environment_rejects_sui_and_binary(self):
        with self.assertRaisesRegex(SystemExit, "not sui"):
            builder.validate_environment({"OPENSWIFTUI": "0"})
        with self.assertRaisesRegex(SystemExit, "not osui-binary"):
            builder.validate_environment({"OPENSWIFTUI_BINARY": "1"})
        builder.validate_environment({"OPENSWIFTUI": "1", "OPENSWIFTUI_BINARY": "0"})

    def test_ensure_sample_symlinks_creates_and_repairs_relative_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = self.create_fake_workspace(Path(tmp))
            android_dir = repo_root / "Android"
            stale_link = android_dir / "Sources" / "HelloWorld"
            stale_link.parent.mkdir(parents=True)
            stale_link.symlink_to(Path("../../Samples/Wrong/Sources"))

            discovered = builder.ensure_sample_symlinks(repo_root, android_dir)
            self.assertEqual(discovered, ["Game2048", "HelloWorld"])
            for sample in discovered:
                link = android_dir / "Sources" / sample
                self.assertTrue(link.is_symlink())
                self.assertEqual(
                    Path(os.readlink(link)),
                    Path("../../Samples") / sample / "Sources",
                )

    def test_prepare_build_environment_propagates_local_and_remote_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = self.create_fake_workspace(Path(tmp))

            local_env, release, triple = builder.prepare_build_environment(
                repo_root,
                {
                    "HOME": tmp,
                    "JAVA_HOME": "/opt/jdk",
                    "OPENSWIFTUI": "1",
                    "OPENSWIFTUI_USE_LOCAL_DEPS": "1",
                    "OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_VERSION": "0.6.0-bugfix.2",
                },
                host_system="Darwin",
            )
            self.assertEqual(release, "6.3.2")
            self.assertEqual(triple, "aarch64-unknown-linux-android28")
            self.assertEqual(local_env["OPENSWIFTUI_USE_LOCAL_DEPS"], "1")
            self.assertEqual(local_env["OPENATTRIBUTEGRAPH_USE_LOCAL_DEPS"], "1")
            self.assertEqual(local_env["OPENRENDERBOX_USE_LOCAL_DEPS"], "1")
            self.assertEqual(local_env["OPENSWIFTUI_UIKIT_CROSS_PLATFORM"], "1")
            self.assertEqual(local_env["OPENSWIFTUI_ANDROID_APP"], "1")
            self.assertEqual(local_env["OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE"], "1")
            self.assertNotIn("OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_VERSION", local_env)
            self.assertEqual(
                Path(local_env["OPENSWIFTUI_UIKIT_CROSS_PLATFORM_PATH"]),
                (repo_root.parent / "UIKit-cross-platform").resolve(),
            )

            remote_env, _, _ = builder.prepare_build_environment(
                repo_root,
                {"HOME": tmp, "JAVA_HOME": "/opt/jdk", "OPENSWIFTUI": "1", "OPENSWIFTUI_USE_LOCAL_DEPS": "0"},
                host_system="Linux",
            )
            self.assertEqual(remote_env["OPENSWIFTUI_USE_LOCAL_DEPS"], "0")
            self.assertEqual(remote_env["OPENATTRIBUTEGRAPH_USE_LOCAL_DEPS"], "0")
            self.assertEqual(
                remote_env["OPENATTRIBUTEGRAPH_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_BRANCH"],
                "android/dev",
            )
            self.assertNotIn("OPENSWIFTUI_UIKIT_CROSS_PLATFORM_PATH", remote_env)

    def test_verify_local_sibling_checkouts_reports_missing_repos(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = self.create_fake_workspace(Path(tmp), include_siblings=False)
            with self.assertRaisesRegex(SystemExit, "android_setup.sh"):
                builder.verify_local_sibling_checkouts(repo_root, {"OPENSWIFTUI_USE_LOCAL_DEPS": "1"})

    def test_resolve_swift_command_checks_system_library_toolchains(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            user_toolchains = tmp_path / "user-toolchains"
            sys_toolchains = tmp_path / "system-toolchains"
            swift_bin = sys_toolchains / "swift-6.3.2-RELEASE.xctoolchain/usr/bin/swift"
            swift_bin.parent.mkdir(parents=True)
            swift_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            swift_bin.chmod(0o755)

            cmd = builder.resolve_swift_command(
                {"HOME": tmp, "PATH": ""},
                "6.3.2",
                ["--version"],
                system_toolchain_roots=(user_toolchains, sys_toolchains),
            )
            self.assertEqual(cmd, [str(swift_bin), "--version"])

    def test_configure_swift_android_sdk_ndk_creates_sysroot_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sdk_root = tmp_path / "swift-6.3.2-RELEASE_android.artifactbundle/swift-android"
            swiftrt = sdk_root / "swift-resources/usr/lib/swift-aarch64/android/aarch64/swiftrt.o"
            swiftrt.parent.mkdir(parents=True)
            swiftrt.write_bytes(b"rt")
            swiftrt_static = sdk_root / "swift-resources/usr/lib/swift_static-aarch64/android/aarch64/swiftrt.o"
            swiftrt_static.parent.mkdir(parents=True)
            swiftrt_static.write_bytes(b"rt_static")

            ndk_root = tmp_path / "ndk"
            prebuilt = ndk_root / "toolchains/llvm/prebuilt/darwin-x86_64"
            (prebuilt / "sysroot/usr/include").mkdir(parents=True)
            (prebuilt / "sysroot/usr/lib/aarch64-linux-android").mkdir(parents=True)
            (prebuilt / "lib/clang/18").mkdir(parents=True)

            builder.configure_swift_android_sdk_ndk(sdk_root, ndk_root)
            self.assertTrue((sdk_root / "ndk-sysroot/usr/include").is_symlink())
            self.assertTrue((sdk_root / "ndk-sysroot/usr/lib/aarch64-linux-android").is_symlink())
            self.assertTrue((sdk_root / "swift-resources/usr/lib/swift/clang").is_symlink())
            self.assertTrue((sdk_root / "ndk-sysroot/usr/lib/swift/android/aarch64/swiftrt.o").is_file())
            self.assertTrue((sdk_root / "ndk-sysroot/usr/lib/swift_static/android/aarch64/swiftrt.o").is_file())

    def test_build_android_sample_rejects_unknown_sample_and_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = self.create_fake_workspace(Path(tmp))
            out_dir = repo_root / "Android" / "dist" / "Unknown"
            with self.assertRaisesRegex(SystemExit, "Unknown SAMPLE"):
                builder.build_android_sample(repo_root, "Unknown", "Debug", out_dir)
            with self.assertRaisesRegex(SystemExit, "Unsupported CONFIGURATION"):
                builder.build_android_sample(repo_root, "HelloWorld", "Profile", out_dir)

    def test_build_android_sample_invokes_swift_and_gradle(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_root = self.create_fake_workspace(tmp_path)
            out_dir = repo_root / "Android" / "dist" / "Game2048"

            sdk_root = tmp_path / "swift-6.3.2-RELEASE_android.artifactbundle" / "swift-android"
            runtime_dir = sdk_root / "swift-resources/usr/lib/swift-aarch64/android"
            runtime_dir.mkdir(parents=True)
            (runtime_dir / "libswiftCore.so").write_bytes(b"core")
            (sdk_root / "ndk-sysroot/usr/include").mkdir(parents=True)
            (sdk_root / "swift-sdk.json").write_text("{}", encoding="utf-8")

            ndk_root = tmp_path / "ndk"
            ndk_root.mkdir()
            (ndk_root / "source.properties").write_text("Pkg.Revision = 27.3.13750724\n", encoding="utf-8")
            libcxx = ndk_root / "toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so"
            libcxx.parent.mkdir(parents=True)
            libcxx.write_bytes(b"cxx")

            android_home = tmp_path / "android-sdk"
            (android_home / "platforms/android-35").mkdir(parents=True)
            (android_home / "platforms/android-35/android.jar").write_bytes(b"jar")

            calls = []

            def fake_run(cmd, cwd=None, env=None, check=False, capture_output=False, text=False):
                if cmd[1:] == ["-version"]:
                    return MagicMock(returncode=0, stdout="", stderr='openjdk version "21.0.2"')
                calls.append(cmd)
                if "build" in cmd and "--product" in cmd:
                    so_out = (
                        repo_root
                        / ".build/android-samples/swift/aarch64-unknown-linux-android28/release/libGame2048Android.so"
                    )
                    so_out.parent.mkdir(parents=True, exist_ok=True)
                    so_out.write_bytes(b"game2048")
                elif cmd[0] == "bash":
                    apk_out = repo_root / "Android/app/build/outputs/apk/release/app-arm64-v8a-release.apk"
                    apk_out.parent.mkdir(parents=True, exist_ok=True)
                    apk_out.write_bytes(b"apk-bytes")
                return MagicMock(returncode=0)

            base_env = {
                "HOME": tmp,
                "PATH": "/usr/bin:/bin",
                "JAVA_HOME": "/opt/jdk",
                "SWIFT_EXEC": "/opt/swift/usr/bin/swift",
                "SWIFT_ANDROID_SDK_PATH": str(sdk_root),
                "ANDROID_NDK_HOME": str(ndk_root),
                "ANDROID_HOME": str(android_home),
                "OPENSWIFTUI": "1",
                "OPENSWIFTUI_USE_LOCAL_DEPS": "1",
            }

            with patch.dict(os.environ, base_env, clear=True), \
                 patch.object(builder.subprocess, "check_output", return_value="Swift version 6.3.2 (swift-6.3.2-RELEASE)\n"), \
                 patch.object(builder.shutil, "which", return_value="/usr/bin/java"), \
                 patch.object(builder.subprocess, "run", side_effect=fake_run):
                apk_path = builder.build_android_sample(repo_root, "Game2048", "Release", out_dir)

            self.assertEqual(len(calls), 3)
            self.assertIn("resolve", calls[0])
            self.assertIn("Game2048Android", calls[1])
            self.assertIn(":app:assembleRelease", calls[2])
            self.assertIn("-Psample=Game2048", calls[2])
            self.assertTrue(apk_path.is_file())
            self.assertEqual(apk_path.name, "Game2048-release-arm64-v8a.apk")


if __name__ == "__main__":
    unittest.main()
