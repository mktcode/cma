from __future__ import annotations

from dataclasses import replace
import re
from typing import Protocol

import pymysql
from pymysql.cursors import DictCursor

from .config import DatabaseConfig
from .models import WebsiteMapping

IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")


class MappingRepository(Protocol):
    def ensure_ready(self) -> None: ...
    def add_mapping(self, sender_email: str, website_domain: str) -> WebsiteMapping: ...
    def get_mappings(self, sender_email: str) -> list[WebsiteMapping]: ...
    def list_mappings(self) -> list[WebsiteMapping]: ...
    def delete_mapping(self, sender_email: str, website_domain: str | None = None) -> bool: ...


class MySQLMappingRepository:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._ready = False

    def ensure_ready(self) -> None:
        if self._ready:
            return

        database_name = self._validated_database_name()
        admin_config = replace(self.config, database=None)
        with self._connect(admin_config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            conn.commit()

        with self._connect(self.config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS websites (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        domain VARCHAR(253) NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uniq_websites_domain (domain)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                self._ensure_column(cur, "websites", "created_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
                self._ensure_column(
                    cur,
                    "websites",
                    "updated_at",
                    "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS senders (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        sender_email VARCHAR(320) NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uniq_senders_email (sender_email)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sender_website_links (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        sender_id BIGINT UNSIGNED NOT NULL,
                        website_id BIGINT UNSIGNED NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uniq_sender_website (sender_id, website_id),
                        KEY idx_sender_website_links_sender_id (sender_id),
                        KEY idx_sender_website_links_website_id (website_id),
                        CONSTRAINT fk_sender_website_links_sender
                            FOREIGN KEY (sender_id) REFERENCES senders(id)
                            ON DELETE CASCADE,
                        CONSTRAINT fk_sender_website_links_website
                            FOREIGN KEY (website_id) REFERENCES websites(id)
                            ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
                if self._table_exists(cur, "sender_mappings"):
                    cur.execute(
                        """
                        INSERT INTO senders (sender_email)
                        SELECT DISTINCT sender_email
                        FROM sender_mappings
                        ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
                        """
                    )
                    cur.execute(
                        """
                        INSERT INTO sender_website_links (sender_id, website_id)
                        SELECT s.id, sm.website_id
                        FROM sender_mappings sm
                        INNER JOIN senders s ON s.sender_email = sm.sender_email
                        ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
                        """
                    )
                    cur.execute("DROP TABLE sender_mappings")
            conn.commit()

        self._ready = True

    def add_mapping(self, sender_email: str, website_domain: str) -> WebsiteMapping:
        self.ensure_ready()
        with self._connect(self.config) as conn:
            with conn.cursor() as cur:
                website_id = self._ensure_website(cur, website_domain)
                sender_id = self._ensure_sender(cur, sender_email)
                cur.execute(
                    """
                    INSERT INTO sender_website_links (sender_id, website_id)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
                    """,
                    (sender_id, website_id),
                )
            conn.commit()
        return WebsiteMapping(sender_email=sender_email, website_domain=website_domain)

    def get_mappings(self, sender_email: str) -> list[WebsiteMapping]:
        self.ensure_ready()
        with self._connect(self.config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.sender_email, w.domain AS website_domain
                    FROM sender_website_links swl
                    INNER JOIN senders s ON s.id = swl.sender_id
                    INNER JOIN websites w ON w.id = swl.website_id
                    WHERE s.sender_email = %s
                    ORDER BY w.domain ASC
                    """,
                    (sender_email,),
                )
                rows = cur.fetchall()
        return [WebsiteMapping(sender_email=row["sender_email"], website_domain=row["website_domain"]) for row in rows]

    def list_mappings(self) -> list[WebsiteMapping]:
        self.ensure_ready()
        with self._connect(self.config) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.sender_email, w.domain AS website_domain
                    FROM sender_website_links swl
                    INNER JOIN senders s ON s.id = swl.sender_id
                    INNER JOIN websites w ON w.id = swl.website_id
                    ORDER BY s.sender_email ASC, w.domain ASC
                    """
                )
                rows = cur.fetchall()
        return [WebsiteMapping(sender_email=row["sender_email"], website_domain=row["website_domain"]) for row in rows]

    def delete_mapping(self, sender_email: str, website_domain: str | None = None) -> bool:
        self.ensure_ready()
        with self._connect(self.config) as conn:
            with conn.cursor() as cur:
                if website_domain is None:
                    cur.execute(
                        """
                        DELETE swl
                        FROM sender_website_links swl
                        INNER JOIN senders s ON s.id = swl.sender_id
                        WHERE s.sender_email = %s
                        """,
                        (sender_email,),
                    )
                else:
                    cur.execute(
                        """
                        DELETE swl
                        FROM sender_website_links swl
                        INNER JOIN senders s ON s.id = swl.sender_id
                        INNER JOIN websites w ON w.id = swl.website_id
                        WHERE s.sender_email = %s AND w.domain = %s
                        """,
                        (sender_email, website_domain),
                    )
                deleted = cur.rowcount > 0
                if deleted:
                    self._cleanup_orphans(cur)
            conn.commit()
        return deleted

    def _ensure_website(self, cur, website_domain: str) -> int:
        cur.execute(
            """
            INSERT INTO websites (domain)
            VALUES (%s)
            ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id), updated_at = CURRENT_TIMESTAMP
            """,
            (website_domain,),
        )
        return cur.lastrowid

    def _ensure_sender(self, cur, sender_email: str) -> int:
        cur.execute(
            """
            INSERT INTO senders (sender_email)
            VALUES (%s)
            ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id), updated_at = CURRENT_TIMESTAMP
            """,
            (sender_email,),
        )
        return cur.lastrowid

    def _cleanup_orphans(self, cur) -> None:
        cur.execute(
            """
            DELETE s
            FROM senders s
            LEFT JOIN sender_website_links swl ON swl.sender_id = s.id
            WHERE swl.id IS NULL
            """
        )
        cur.execute(
            """
            DELETE w
            FROM websites w
            LEFT JOIN sender_website_links swl ON swl.website_id = w.id
            WHERE swl.id IS NULL
            """
        )

    def _table_exists(self, cur, table_name: str) -> bool:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = %s
            LIMIT 1
            """,
            (table_name,),
        )
        return cur.fetchone() is not None

    def _column_exists(self, cur, table_name: str, column_name: str) -> bool:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s
            LIMIT 1
            """,
            (table_name, column_name),
        )
        return cur.fetchone() is not None

    def _ensure_column(self, cur, table_name: str, column_name: str, column_definition: str) -> None:
        if self._column_exists(cur, table_name, column_name):
            return
        cur.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {column_definition}")

    def _connect(self, config: DatabaseConfig):
        params = {
            "user": config.user,
            "charset": "utf8mb4",
            "autocommit": False,
            "cursorclass": DictCursor,
        }
        if config.password:
            params["password"] = config.password
        if config.database:
            params["database"] = config.database
        if config.unix_socket:
            params["unix_socket"] = config.unix_socket
        else:
            params["host"] = config.host
            params["port"] = config.port
        return pymysql.connect(**params)

    def _validated_database_name(self) -> str:
        database_name = self.config.database or ""
        if not IDENTIFIER_RE.match(database_name):
            raise ValueError(f"unsafe database name: {database_name}")
        return database_name
