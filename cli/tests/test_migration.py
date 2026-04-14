from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import sys
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cma_utils.config import DatabaseConfig
from cma_utils.repository import MySQLMappingRepository
from cma_utils.service import MappingService


@unittest.skipUnless(os.geteuid() == 0, "MariaDB socket auth test needs root")
@unittest.skipUnless(Path("/run/mysqld/mysqld.sock").exists(), "MariaDB socket unavailable")
class MigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database_name = f"website_legacy_{uuid4().hex[:12]}"
        cls.admin_config = DatabaseConfig(database=None)
        cls.database_config = replace(cls.admin_config, database=cls.database_name)
        bootstrap = MySQLMappingRepository(cls.database_config)
        with bootstrap._connect(cls.admin_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE `{cls.database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            conn.commit()
        with bootstrap._connect(cls.database_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE websites (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        domain VARCHAR(253) NOT NULL,
                        UNIQUE KEY uniq_websites_domain (domain)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE sender_mappings (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        sender_email VARCHAR(320) NOT NULL,
                        website_id BIGINT UNSIGNED NOT NULL,
                        UNIQUE KEY uniq_sender_email (sender_email),
                        KEY idx_sender_mappings_website_id (website_id),
                        CONSTRAINT fk_sender_mappings_website
                            FOREIGN KEY (website_id) REFERENCES websites(id)
                            ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                cur.execute("INSERT INTO websites (domain) VALUES ('legacy.example')")
                cur.execute(
                    "INSERT INTO sender_mappings (sender_email, website_id) VALUES ('legacy@example.com', 1)"
                )
            conn.commit()

    @classmethod
    def tearDownClass(cls) -> None:
        repository = MySQLMappingRepository(cls.admin_config)
        with repository._connect(cls.admin_config) as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP DATABASE IF EXISTS `{cls.database_name}`")
            conn.commit()

    def test_legacy_schema_is_migrated(self) -> None:
        service = MappingService(MySQLMappingRepository(self.database_config))
        self.assertEqual(
            [mapping.website_domain for mapping in service.lookup("legacy@example.com")],
            ["legacy.example"],
        )
        service.allow("legacy@example.com", "second.example")
        self.assertEqual(
            [mapping.website_domain for mapping in service.lookup("legacy@example.com")],
            ["legacy.example", "second.example"],
        )
