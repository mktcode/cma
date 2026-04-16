CREATE DATABASE cma;

use cma;

CREATE TABLE IF NOT EXISTS websites (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  domain VARCHAR(253) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_websites_domain (domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS senders (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  sender_email VARCHAR(320) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_senders_email (sender_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS mail_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    thread_id VARCHAR(255) NOT NULL,
    security_checks_passed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL,
    completed_at DATETIME NULL,
    replied_at DATETIME NULL,
    reply_content TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
