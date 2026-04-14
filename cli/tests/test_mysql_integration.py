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
class MySQLIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database_name = f"website_test_{uuid4().hex[:12]}"
        cls.admin_config = DatabaseConfig(database=None)
        cls.database_config = replace(cls.admin_config, database=cls.database_name)
        repository = MySQLMappingRepository(cls.database_config)
        repository.ensure_ready()
        cls.service = MappingService(repository)

    @classmethod
    def tearDownClass(cls) -> None:
        repository = MySQLMappingRepository(cls.admin_config)
        with repository._connect(cls.admin_config) as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP DATABASE IF EXISTS `{cls.database_name}`")
            conn.commit()

    def test_allow_lookup_list_and_remove(self) -> None:
        self.service.allow("person@example.com", "alpha.example")
        self.service.allow("person@example.com", "beta.example")

        looked_up = self.service.lookup("person@example.com")
        self.assertEqual([mapping.website_domain for mapping in looked_up], ["alpha.example", "beta.example"])

        listed = self.service.list_mappings()
        self.assertEqual(
            [mapping.website_domain for mapping in listed if mapping.sender_email == "person@example.com"],
            ["alpha.example", "beta.example"],
        )

        removed_one = self.service.remove("person@example.com", "alpha.example")
        self.assertTrue(removed_one)
        self.assertEqual([mapping.website_domain for mapping in self.service.lookup("person@example.com")], ["beta.example"])

        removed_rest = self.service.remove("person@example.com")
        self.assertTrue(removed_rest)
        self.assertEqual(self.service.lookup("person@example.com"), [])
