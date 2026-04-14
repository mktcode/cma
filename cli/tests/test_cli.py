from __future__ import annotations

import io
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cma_utils.cli import main
from cma_utils.models import WebsiteMapping


class StubService:
    def __init__(self):
        self.calls: list[tuple] = []
        self.lookup_result = [
            WebsiteMapping("owner@example.com", "alpha.example"),
            WebsiteMapping("owner@example.com", "beta.example"),
        ]
        self.list_result = list(self.lookup_result)
        self.remove_result = True
        self.initialized = False

    def initialize(self) -> None:
        self.initialized = True

    def allow(self, sender_email: str, website_domain: str) -> WebsiteMapping:
        self.calls.append(("allow", sender_email, website_domain))
        return WebsiteMapping(sender_email, website_domain)

    def lookup(self, sender_email: str) -> list[WebsiteMapping]:
        self.calls.append(("lookup", sender_email))
        return self.lookup_result

    def list_mappings(self) -> list[WebsiteMapping]:
        self.calls.append(("list",))
        return self.list_result

    def remove(self, sender_email: str, website_domain: str | None = None) -> bool:
        self.calls.append(("remove", sender_email, website_domain))
        return self.remove_result


class StubNginx:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def install_site(self, domain: str, *, server_names, force: bool, reload: bool):
        self.calls.append(("install", domain, tuple(server_names), force, reload))
        return Path(f"/etc/nginx/sites-available/{domain}.conf")

    def show_config(self, domain: str, server_names=None) -> str:
        self.calls.append(("show", domain, tuple(server_names or [])))
        return f"server_name {domain};\n"

    def enable_site(self, domain: str, *, reload: bool) -> None:
        self.calls.append(("enable", domain, reload))

    def disable_site(self, domain: str, *, reload: bool) -> None:
        self.calls.append(("disable", domain, reload))

    def test_config(self) -> None:
        self.calls.append(("test",))

    def reload(self) -> None:
        self.calls.append(("reload",))


class StubCert:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def issue_certificate(self, domain: str, email: str, *, extra_domains, staging: bool, redirect: bool) -> None:
        self.calls.append(("issue", domain, email, tuple(extra_domains), staging, redirect))

    def renew(self, *, dry_run: bool) -> None:
        self.calls.append(("renew", dry_run))


class CliTests(unittest.TestCase):
    def test_allow_command(self) -> None:
        service = StubService()
        stdout = io.StringIO()
        code = main(["allow", "owner@example.com", "example.com"], service_factory=lambda: service, stdout=stdout)
        self.assertEqual(code, 0)
        self.assertIn("allowed owner@example.com -> example.com", stdout.getvalue())
        self.assertEqual(service.calls, [("allow", "owner@example.com", "example.com")])

    def test_lookup_command_found(self) -> None:
        service = StubService()
        stdout = io.StringIO()
        code = main(["lookup", "owner@example.com"], service_factory=lambda: service, stdout=stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue().strip().splitlines(), ["alpha.example", "beta.example"])

    def test_lookup_command_missing(self) -> None:
        service = StubService()
        service.lookup_result = []
        stdout = io.StringIO()
        code = main(["lookup", "owner@example.com"], service_factory=lambda: service, stdout=stdout)
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue().strip(), "no mapping found")

    def test_list_command(self) -> None:
        service = StubService()
        stdout = io.StringIO()
        code = main(["list"], service_factory=lambda: service, stdout=stdout)
        self.assertEqual(code, 0)
        self.assertEqual(
            stdout.getvalue().strip().splitlines(),
            ["owner@example.com\talpha.example", "owner@example.com\tbeta.example"],
        )

    def test_remove_single_mapping_command(self) -> None:
        service = StubService()
        stdout = io.StringIO()
        code = main(["remove", "owner@example.com", "alpha.example"], service_factory=lambda: service, stdout=stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue().strip(), "removed owner@example.com -> alpha.example")

    def test_remove_all_mappings_command(self) -> None:
        service = StubService()
        stdout = io.StringIO()
        code = main(["remove", "owner@example.com"], service_factory=lambda: service, stdout=stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue().strip(), "removed all mappings for owner@example.com")

    def test_init_db_command(self) -> None:
        service = StubService()
        stdout = io.StringIO()
        code = main(["init-db"], service_factory=lambda: service, stdout=stdout)
        self.assertEqual(code, 0)
        self.assertTrue(service.initialized)
        self.assertEqual(stdout.getvalue().strip(), "database ready")

    def test_nginx_install_command(self) -> None:
        nginx = StubNginx()
        stdout = io.StringIO()
        code = main(
            ["nginx", "install", "example.com", "--server-name", "www.example.com", "--force"],
            nginx_factory=lambda: nginx,
            stdout=stdout,
        )
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue().strip(), "installed /etc/nginx/sites-available/example.com.conf")
        self.assertEqual(nginx.calls, [("install", "example.com", ("www.example.com",), True, True)])

    def test_nginx_show_command(self) -> None:
        nginx = StubNginx()
        stdout = io.StringIO()
        code = main(["nginx", "show", "example.com"], nginx_factory=lambda: nginx, stdout=stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "server_name example.com;\n")

    def test_nginx_enable_disable_test_and_reload_commands(self) -> None:
        nginx = StubNginx()
        stdout = io.StringIO()
        self.assertEqual(main(["nginx", "enable", "example.com"], nginx_factory=lambda: nginx, stdout=stdout), 0)
        self.assertEqual(main(["nginx", "disable", "example.com", "--no-reload"], nginx_factory=lambda: nginx, stdout=stdout), 0)
        self.assertEqual(main(["nginx", "test"], nginx_factory=lambda: nginx, stdout=stdout), 0)
        self.assertEqual(main(["nginx", "reload"], nginx_factory=lambda: nginx, stdout=stdout), 0)
        self.assertEqual(
            nginx.calls,
            [("enable", "example.com", True), ("disable", "example.com", False), ("test",), ("reload",)],
        )

    def test_cert_issue_command(self) -> None:
        cert = StubCert()
        stdout = io.StringIO()
        code = main(
            ["cert", "issue", "example.com", "--email", "owner@example.com", "--domain", "www.example.com", "--staging"],
            cert_factory=lambda: cert,
            stdout=stdout,
        )
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue().strip(), "certificate requested for example.com")
        self.assertEqual(
            cert.calls,
            [("issue", "example.com", "owner@example.com", ("www.example.com",), True, True)],
        )

    def test_cert_renew_command(self) -> None:
        cert = StubCert()
        stdout = io.StringIO()
        code = main(["cert", "renew", "--dry-run"], cert_factory=lambda: cert, stdout=stdout)
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue().strip(), "certificate renewal run finished")
        self.assertEqual(cert.calls, [("renew", True)])
