from __future__ import annotations

import argparse
import sys
from typing import Callable, Sequence, TextIO

from .config import load_database_config
from .hosting import LetsEncryptManager, NginxManager
from .repository import MySQLMappingRepository
from .service import MappingService


ServiceFactory = Callable[[], MappingService]
NginxFactory = Callable[[], NginxManager]
CertFactory = Callable[[], LetsEncryptManager]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="website",
        description="Manage website sender mappings and static hosting.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    allow_parser = subparsers.add_parser("allow", help="Add an allowed sender-to-website mapping")
    allow_parser.add_argument("email", help="Sender email address")
    allow_parser.add_argument("website", help="Website domain, for example example.com")

    lookup_parser = subparsers.add_parser("lookup", help="Resolve a sender email to one or more website domains")
    lookup_parser.add_argument("email", help="Sender email address")

    subparsers.add_parser("list", help="List all sender mappings")

    remove_parser = subparsers.add_parser("remove", help="Delete one mapping, or all mappings for an email")
    remove_parser.add_argument("email", help="Sender email address")
    remove_parser.add_argument("website", nargs="?", help="Website domain to remove for that sender")

    subparsers.add_parser("init-db", help="Create the database and tables if they are missing")

    nginx_parser = subparsers.add_parser("nginx", help="Manage nginx static site configs")
    nginx_subparsers = nginx_parser.add_subparsers(dest="nginx_command", required=True)

    nginx_install = nginx_subparsers.add_parser("install", help="Write and enable an nginx site config")
    nginx_install.add_argument("domain", help="Primary website domain")
    nginx_install.add_argument("--server-name", action="append", default=[], dest="server_names", help="Additional server_name entry")
    nginx_install.add_argument("--force", action="store_true", help="Overwrite an existing config file")
    nginx_install.add_argument("--no-reload", action="store_true", help="Skip nginx reload after install")

    nginx_show = nginx_subparsers.add_parser("show", help="Print the nginx config for a domain")
    nginx_show.add_argument("domain", help="Primary website domain")
    nginx_show.add_argument("--server-name", action="append", default=[], dest="server_names", help="Additional server_name entry")

    nginx_enable = nginx_subparsers.add_parser("enable", help="Enable an existing nginx site config")
    nginx_enable.add_argument("domain", help="Primary website domain")
    nginx_enable.add_argument("--no-reload", action="store_true", help="Skip nginx reload after enabling")

    nginx_disable = nginx_subparsers.add_parser("disable", help="Disable an nginx site config")
    nginx_disable.add_argument("domain", help="Primary website domain")
    nginx_disable.add_argument("--no-reload", action="store_true", help="Skip nginx reload after disabling")

    nginx_subparsers.add_parser("test", help="Run nginx -t")
    nginx_subparsers.add_parser("reload", help="Reload nginx")

    cert_parser = subparsers.add_parser("cert", help="Manage Let's Encrypt certificates via certbot")
    cert_subparsers = cert_parser.add_subparsers(dest="cert_command", required=True)

    cert_issue = cert_subparsers.add_parser("issue", help="Request a certificate with certbot --nginx")
    cert_issue.add_argument("domain", help="Primary website domain")
    cert_issue.add_argument("--email", required=True, help="Registration email for Let's Encrypt")
    cert_issue.add_argument("--domain", action="append", default=[], dest="extra_domains", help="Additional -d name")
    cert_issue.add_argument("--staging", action="store_true", help="Use Let's Encrypt staging")
    cert_issue.add_argument("--no-redirect", action="store_true", help="Skip automatic HTTP to HTTPS redirect")

    cert_renew = cert_subparsers.add_parser("renew", help="Run certbot renew")
    cert_renew.add_argument("--dry-run", action="store_true", help="Run certbot renew --dry-run")

    return parser


def create_service() -> MappingService:
    repository = MySQLMappingRepository(load_database_config())
    return MappingService(repository)


def create_nginx_manager() -> NginxManager:
    return NginxManager()


def create_cert_manager() -> LetsEncryptManager:
    return LetsEncryptManager()


def main(
    argv: Sequence[str] | None = None,
    *,
    service_factory: ServiceFactory = create_service,
    nginx_factory: NginxFactory = create_nginx_manager,
    cert_factory: CertFactory = create_cert_manager,
    stdout: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-db":
        service = service_factory()
        service.initialize()
        print("database ready", file=stdout)
        return 0

    if args.command == "allow":
        service = service_factory()
        mapping = service.allow(args.email, args.website)
        print(f"allowed {mapping.sender_email} -> {mapping.website_domain}", file=stdout)
        return 0

    if args.command == "lookup":
        service = service_factory()
        mappings = service.lookup(args.email)
        if not mappings:
            print("no mapping found", file=stdout)
            return 1
        for mapping in mappings:
            print(mapping.website_domain, file=stdout)
        return 0

    if args.command == "list":
        service = service_factory()
        for mapping in service.list_mappings():
            print(f"{mapping.sender_email}\t{mapping.website_domain}", file=stdout)
        return 0

    if args.command == "remove":
        service = service_factory()
        deleted = service.remove(args.email, args.website)
        if deleted:
            if args.website:
                print(f"removed {args.email} -> {args.website}", file=stdout)
            else:
                print(f"removed all mappings for {args.email}", file=stdout)
            return 0
        print("no mapping found", file=stdout)
        return 1

    if args.command == "nginx":
        nginx = nginx_factory()
        if args.nginx_command == "install":
            config_path = nginx.install_site(
                args.domain,
                server_names=args.server_names,
                force=args.force,
                reload=not args.no_reload,
            )
            print(f"installed {config_path}", file=stdout)
            return 0
        if args.nginx_command == "show":
            print(nginx.show_config(args.domain, server_names=args.server_names), end="", file=stdout)
            return 0
        if args.nginx_command == "enable":
            nginx.enable_site(args.domain, reload=not args.no_reload)
            print(f"enabled {args.domain}", file=stdout)
            return 0
        if args.nginx_command == "disable":
            nginx.disable_site(args.domain, reload=not args.no_reload)
            print(f"disabled {args.domain}", file=stdout)
            return 0
        if args.nginx_command == "test":
            nginx.test_config()
            print("nginx config ok", file=stdout)
            return 0
        if args.nginx_command == "reload":
            nginx.reload()
            print("nginx reloaded", file=stdout)
            return 0

    if args.command == "cert":
        cert = cert_factory()
        if args.cert_command == "issue":
            cert.issue_certificate(
                args.domain,
                args.email,
                extra_domains=args.extra_domains,
                staging=args.staging,
                redirect=not args.no_redirect,
            )
            print(f"certificate requested for {args.domain}", file=stdout)
            return 0
        if args.cert_command == "renew":
            cert.renew(dry_run=args.dry_run)
            print("certificate renewal run finished", file=stdout)
            return 0

    parser.error("unsupported command")
    return 2
