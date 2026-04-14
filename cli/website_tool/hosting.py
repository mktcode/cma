from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
from typing import Protocol, Sequence

from .validators import normalize_domain, normalize_email


@dataclass(frozen=True)
class HostingPaths:
    websites_root: Path = Path("/var/www/websites")
    nginx_sites_available: Path = Path("/etc/nginx/sites-available")
    nginx_sites_enabled: Path = Path("/etc/nginx/sites-enabled")


class CommandRunner(Protocol):
    def run(self, command: Sequence[str]) -> None: ...


@dataclass
class SubprocessRunner:
    def run(self, command: Sequence[str]) -> None:
        subprocess.run(list(command), check=True)


@dataclass
class NginxManager:
    paths: HostingPaths = field(default_factory=HostingPaths)
    runner: CommandRunner = field(default_factory=SubprocessRunner)

    def install_site(
        self,
        domain: str,
        *,
        server_names: Sequence[str] | None = None,
        force: bool = False,
        reload: bool = True,
    ) -> Path:
        normalized_domain = normalize_domain(domain)
        live_root = self.paths.websites_root / normalized_domain / "live"
        staging_root = self.paths.websites_root / normalized_domain / "staging"
        live_root.mkdir(parents=True, exist_ok=True)
        staging_root.mkdir(parents=True, exist_ok=True)

        config_path = self.available_path(normalized_domain)
        if config_path.exists() and not force:
            raise FileExistsError(f"nginx config already exists: {config_path}")

        self.paths.nginx_sites_available.mkdir(parents=True, exist_ok=True)
        self.paths.nginx_sites_enabled.mkdir(parents=True, exist_ok=True)
        config_path.write_text(self.render_config(normalized_domain, server_names), encoding="utf-8")
        self.enable_site(normalized_domain, reload=reload)
        return config_path

    def render_config(self, domain: str, server_names: Sequence[str] | None = None) -> str:
        normalized_domain = normalize_domain(domain)
        names = self._live_server_names(normalized_domain, server_names)
        staging_name = self.staging_hostname(normalized_domain)
        root = self.paths.websites_root / normalized_domain / "live"
        staging_root = self.paths.websites_root / normalized_domain / "staging"
        return (
            "server {\n"
            "    listen 80;\n"
            "    listen [::]:80;\n"
            f"    server_name {' '.join(names)};\n\n"
            f"    root {root};\n"
            "    index index.html;\n\n"
            f"    access_log /var/log/nginx/{normalized_domain}.access.log;\n"
            f"    error_log /var/log/nginx/{normalized_domain}.error.log;\n\n"
            "    location / {\n"
            "        try_files $uri $uri/ =404;\n"
            "    }\n"
            "}\n\n"
            "server {\n"
            "    listen 80;\n"
            "    listen [::]:80;\n"
            f"    server_name {staging_name};\n\n"
            f"    root {staging_root};\n"
            "    index index.html;\n\n"
            f"    access_log /var/log/nginx/{normalized_domain}.staging.access.log;\n"
            f"    error_log /var/log/nginx/{normalized_domain}.staging.error.log;\n\n"
            "    add_header X-Robots-Tag \"noindex, nofollow, noarchive\" always;\n\n"
            "    location / {\n"
            "        try_files $uri $uri/ =404;\n"
            "    }\n"
            "}\n"
        )

    def enable_site(self, domain: str, *, reload: bool = True) -> None:
        normalized_domain = normalize_domain(domain)
        available = self.available_path(normalized_domain)
        enabled = self.enabled_path(normalized_domain)
        if not available.exists():
            raise FileNotFoundError(f"missing nginx config: {available}")
        if not enabled.exists() and not enabled.is_symlink():
            enabled.symlink_to(available)
        self.test_config()
        if reload:
            self.reload()

    def disable_site(self, domain: str, *, reload: bool = True) -> None:
        normalized_domain = normalize_domain(domain)
        enabled = self.enabled_path(normalized_domain)
        if enabled.exists() or enabled.is_symlink():
            enabled.unlink()
        self.test_config()
        if reload:
            self.reload()

    def show_config(self, domain: str, server_names: Sequence[str] | None = None) -> str:
        return self.render_config(domain, server_names)

    def test_config(self) -> None:
        self.runner.run(["nginx", "-t"])

    def reload(self) -> None:
        self.runner.run(["systemctl", "reload", "nginx"])

    def available_path(self, domain: str) -> Path:
        return self.paths.nginx_sites_available / f"{normalize_domain(domain)}.conf"

    def enabled_path(self, domain: str) -> Path:
        return self.paths.nginx_sites_enabled / f"{normalize_domain(domain)}.conf"

    def _normalized_server_names(self, domain: str, server_names: Sequence[str] | None) -> list[str]:
        names = [domain]
        for name in server_names or []:
            normalized = normalize_domain(name)
            if normalized not in names:
                names.append(normalized)
        return names

    def _live_server_names(self, domain: str, server_names: Sequence[str] | None) -> list[str]:
        staging_name = self.staging_hostname(domain)
        return [name for name in self._normalized_server_names(domain, server_names) if name != staging_name]

    def staging_hostname(self, domain: str) -> str:
        return f"staging.{normalize_domain(domain)}"


@dataclass
class LetsEncryptManager:
    runner: CommandRunner = field(default_factory=SubprocessRunner)

    def issue_certificate(
        self,
        domain: str,
        email: str,
        *,
        extra_domains: Sequence[str] | None = None,
        staging: bool = False,
        redirect: bool = True,
    ) -> None:
        normalized_domain = normalize_domain(domain)
        normalized_email = normalize_email(email)
        domains = [normalized_domain, self.staging_hostname(normalized_domain)]
        for extra in extra_domains or []:
            normalized = normalize_domain(extra)
            if normalized not in domains:
                domains.append(normalized)

        command = [
            "certbot",
            "--nginx",
            "--non-interactive",
            "--agree-tos",
            "--no-eff-email",
            "-m",
            normalized_email,
        ]
        for name in domains:
            command.extend(["-d", name])
        if staging:
            command.append("--staging")
        if redirect:
            command.append("--redirect")
        self.runner.run(command)

    def renew(self, *, dry_run: bool = False) -> None:
        command = ["certbot", "renew"]
        if dry_run:
            command.append("--dry-run")
        self.runner.run(command)

    def staging_hostname(self, domain: str) -> str:
        return f"staging.{normalize_domain(domain)}"
