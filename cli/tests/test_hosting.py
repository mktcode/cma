from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from website_tool.hosting import HostingPaths, LetsEncryptManager, NginxManager


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command):
        self.commands.append(list(command))


class HostingTests(unittest.TestCase):
    def test_render_config_contains_expected_live_and_staging_blocks(self) -> None:
        manager = NginxManager()
        rendered = manager.render_config("example.com", ["www.example.com"])
        self.assertIn("server_name example.com www.example.com;", rendered)
        self.assertIn("root /var/www/websites/example.com/live;", rendered)
        self.assertIn("server_name staging.example.com;", rendered)
        self.assertIn("root /var/www/websites/example.com/staging;", rendered)
        self.assertIn("X-Robots-Tag \"noindex, nofollow, noarchive\"", rendered)

    def test_install_site_writes_config_enables_it_and_reloads(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            runner = FakeRunner()
            manager = NginxManager(
                paths=HostingPaths(
                    websites_root=base / "websites",
                    nginx_sites_available=base / "sites-available",
                    nginx_sites_enabled=base / "sites-enabled",
                ),
                runner=runner,
            )
            config_path = manager.install_site("example.com", server_names=["www.example.com"])
            self.assertTrue(config_path.exists())
            self.assertTrue((base / "websites" / "example.com" / "live").exists())
            self.assertTrue((base / "websites" / "example.com" / "staging").exists())
            self.assertTrue((base / "sites-enabled" / "example.com.conf").is_symlink())
            self.assertEqual(runner.commands, [["nginx", "-t"], ["systemctl", "reload", "nginx"]])

    def test_disable_site_unlinks_symlink(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            runner = FakeRunner()
            manager = NginxManager(
                paths=HostingPaths(
                    websites_root=base / "websites",
                    nginx_sites_available=base / "sites-available",
                    nginx_sites_enabled=base / "sites-enabled",
                ),
                runner=runner,
            )
            manager.install_site("example.com")
            runner.commands.clear()
            manager.disable_site("example.com")
            self.assertFalse((base / "sites-enabled" / "example.com.conf").exists())
            self.assertEqual(runner.commands, [["nginx", "-t"], ["systemctl", "reload", "nginx"]])

    def test_issue_certificate_builds_certbot_command(self) -> None:
        runner = FakeRunner()
        manager = LetsEncryptManager(runner=runner)
        manager.issue_certificate(
            "example.com",
            "owner@example.com",
            extra_domains=["www.example.com"],
            staging=True,
        )
        self.assertEqual(
            runner.commands,
            [[
                "certbot",
                "--nginx",
                "--non-interactive",
                "--agree-tos",
                "--no-eff-email",
                "-m",
                "owner@example.com",
                "-d",
                "example.com",
                "-d",
                "staging.example.com",
                "-d",
                "www.example.com",
                "--staging",
                "--redirect",
            ]],
        )

    def test_renew_builds_certbot_command(self) -> None:
        runner = FakeRunner()
        manager = LetsEncryptManager(runner=runner)
        manager.renew(dry_run=True)
        self.assertEqual(runner.commands, [["certbot", "renew", "--dry-run"]])
