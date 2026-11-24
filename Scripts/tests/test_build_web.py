import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "build_web", Path(__file__).resolve().parents[1] / "build-web.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildWebTests(unittest.TestCase):
    def create_fake_repo(self, root: Path) -> Path:
        for sample in ("HelloWorld", "Game2048"):
            sample_dir = root / "Samples" / sample
            (sample_dir / "Sources").mkdir(parents=True)
            (sample_dir / "Project.swift").write_text("// stub\n", encoding="utf-8")
        (root / "Web").mkdir(parents=True)
        return root

    def test_validate_environment_rejects_sui_and_binary(self):
        with self.assertRaisesRegex(SystemExit, "not sui"):
            builder.validate_environment({"OPENSWIFTUI": "0"})
        with self.assertRaisesRegex(SystemExit, "not osui-binary"):
            builder.validate_environment({"OPENSWIFTUI_BINARY": "1"})
        builder.validate_environment({"OPENSWIFTUI": "1", "OPENSWIFTUI_BINARY": "0"})

    def test_ensure_sample_symlinks_creates_and_repairs_relative_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = self.create_fake_repo(Path(tmp))
            web_dir = repo_root / "Web"
            stale_link = web_dir / "Sources" / "HelloWorld"
            stale_link.parent.mkdir(parents=True)
            stale_link.symlink_to(Path("../../Samples/Wrong/Sources"))

            discovered = builder.ensure_sample_symlinks(repo_root, web_dir)
            self.assertEqual(discovered, ["Game2048", "HelloWorld"])
            for sample in discovered:
                link = web_dir / "Sources" / sample
                self.assertTrue(link.is_symlink())
                self.assertEqual(
                    Path(os.readlink(link)),
                    Path("../../Samples") / sample / "Sources",
                )

    def test_build_web_sample_rejects_unknown_sample_and_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = self.create_fake_repo(Path(tmp))
            out_dir = repo_root / "Web" / "dist" / "Unknown"
            with self.assertRaisesRegex(SystemExit, "Unknown SAMPLE"):
                builder.build_web_sample(repo_root, "Unknown", "Debug", out_dir)
            with self.assertRaisesRegex(SystemExit, "Unsupported CONFIGURATION"):
                builder.build_web_sample(repo_root, "HelloWorld", "Profile", out_dir)

    def test_build_web_sample_constructs_plugin_invocation_and_wasi_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = self.create_fake_repo(Path(tmp))
            out_dir = repo_root / "Web" / "dist" / "Game2048"
            recorded = {}

            def fake_run(cmd, cwd, env, check):
                recorded["cmd"] = cmd
                recorded["cwd"] = cwd
                recorded["env"] = env
                recorded["check"] = check

            base_env = {
                "PATH": "/usr/bin:/bin",
                "OPENSWIFTUI": "1",
                "OPENSWIFTUI_USE_LOCAL_DEPS": "1",
                "OPENSWIFTUI_OPENATTRIBUTESHIMS_ATTRIBUTEGRAPH": "1",
                "OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE": "0",
                "OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_VERSION": "0.6.0-bugfix.2",
            }
            with patch.dict(os.environ, base_env, clear=True), \
                 patch.object(builder.shutil, "which", return_value="/opt/bin/swiftly"), \
                 patch.object(builder.subprocess, "run", side_effect=fake_run):
                builder.build_web_sample(repo_root, "Game2048", "Release", out_dir)

            self.assertEqual(recorded["cwd"], repo_root / "Web")
            self.assertTrue(recorded["check"])
            cmd = recorded["cmd"]
            self.assertEqual(cmd[:3], ["/opt/bin/swiftly", "run", "swift"])
            self.assertEqual(cmd[-1], "+6.3.2")
            self.assertIn("--swift-sdk", cmd)
            self.assertEqual(cmd[cmd.index("--swift-sdk") + 1], "swift-6.3.2-RELEASE_wasm")
            self.assertIn("web-deploy", cmd)
            self.assertEqual(cmd[cmd.index("--product") + 1], "Game2048Web")
            self.assertEqual(cmd[cmd.index("--configuration") + 1], "release")
            self.assertEqual(cmd[cmd.index("--output") + 1], str(out_dir))

            env = recorded["env"]
            self.assertEqual(env["OPENSWIFTUI_WASI"], "1")
            self.assertEqual(env["OPENSWIFTUI_BUILD_FOR_DARWIN_PLATFORM"], "0")
            self.assertEqual(env["OPENATTRIBUTEGRAPH_BUILD_FOR_DARWIN_PLATFORM"], "0")
            self.assertEqual(env["OPENRENDERBOX_BUILD_FOR_DARWIN_PLATFORM"], "0")
            self.assertEqual(env["OPENSWIFTUI_LIBRARY_EVOLUTION"], "0")
            self.assertEqual(env["OPENSWIFTUI_RENDER_GTK"], "0")
            self.assertEqual(env["OPENSWIFTUI_OPENATTRIBUTESHIMS_ATTRIBUTEGRAPH"], "0")
            self.assertEqual(env["OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE"], "1")
            self.assertEqual(env["OPENATTRIBUTEGRAPH_OPENATTRIBUTESHIMS_COMPUTE_BINARY"], "0")
            self.assertEqual(env["OPENSWIFTUI_USE_LOCAL_DEPS"], "1")
            self.assertNotIn("OPENSWIFTUI_OPENATTRIBUTESHIMS_COMPUTE_SOURCE_VERSION", env)

    def test_build_swift_command_discovers_macos_xctoolchain_without_swiftly(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            swift_bin = (
                home
                / "Library/Developer/Toolchains/swift-6.3.2-RELEASE.xctoolchain/usr/bin/swift"
            )
            swift_bin.parent.mkdir(parents=True)
            swift_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            swift_bin.chmod(0o755)

            with patch.object(builder.shutil, "which", return_value=None):
                cmd = builder.build_swift_command(
                    {"PATH": "/usr/bin"},
                    "6.3.2",
                    ["sdk", "list"],
                    home_dir=home,
                )
            self.assertEqual(cmd, [str(swift_bin), "sdk", "list"])

    def test_verify_web_toolchain_and_sdk_reports_install_hint_when_sdk_missing(self):
        def fake_run(cmd, **kwargs):
            if "--version" in cmd:
                return unittest.mock.Mock(
                    returncode=0,
                    stdout="Apple Swift version 6.3.2 (swift-6.3.2-RELEASE)\n",
                    stderr="",
                )
            if "sdk" in cmd and "list" in cmd:
                return unittest.mock.Mock(
                    returncode=0,
                    stdout="swift-6.3.2-RELEASE_android\n",
                    stderr="",
                )
            raise AssertionError(f"Unexpected command: {cmd}")

        with patch.object(builder.shutil, "which", return_value="/opt/bin/swiftly"), \
             patch.object(builder.subprocess, "run", side_effect=fake_run):
            with self.assertRaisesRegex(SystemExit, "WEB_INSTALL_SDK=1"):
                builder.verify_web_toolchain_and_sdk(
                    {"PATH": "/opt/bin"},
                    "6.3.2",
                    "swift-6.3.2-RELEASE_wasm",
                    install_sdk=False,
                )


if __name__ == "__main__":
    unittest.main()
