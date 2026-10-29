CREATE DATABASE IF NOT EXISTS surplusreach CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE surplusreach;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('donor','ngo','volunteer','admin') NOT NULL,
  organization_name VARCHAR(180), phone VARCHAR(32), address VARCHAR(500),
  lat DECIMAL(10,7), lng DECIMAL(10,7), is_verified BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_users_role_verified (role, is_verified)
);

CREATE TABLE IF NOT EXISTS donations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  donor_id INT NOT NULL,
  food_name VARCHAR(180) NOT NULL,
  food_type ENUM('cooked meal','raw produce','bakery','packaged') NOT NULL,
  quantity DECIMAL(10,2) NOT NULL,
  unit VARCHAR(32) NOT NULL,
  dietary_info ENUM('veg','non-veg','vegan') NOT NULL,
  preparation_time DATETIME,
  expiry_time DATETIME NOT NULL,
  pickup_address VARCHAR(500) NOT NULL,
  lat DECIMAL(10,7), lng DECIMAL(10,7),
  storage_notes TEXT,
  status ENUM('available','claimed','in_transit','completed','expired') NOT NULL DEFAULT 'available',
  pickup_code VARCHAR(12),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_donations_donor FOREIGN KEY (donor_id) REFERENCES users(id),
  INDEX ix_donations_feed (status, expiry_time), INDEX ix_donations_location (lat,lng)
);

CREATE TABLE IF NOT EXISTS claims (
  id INT AUTO_INCREMENT PRIMARY KEY,
  donation_id INT NOT NULL,
  ngo_id INT NOT NULL,
  volunteer_id INT,
  status ENUM('claimed','assigned','in_transit','completed','cancelled') NOT NULL DEFAULT 'claimed',
  notes TEXT, claimed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  delivered_at DATETIME,
  CONSTRAINT fk_claims_donation FOREIGN KEY (donation_id) REFERENCES donations(id),
  CONSTRAINT fk_claims_ngo FOREIGN KEY (ngo_id) REFERENCES users(id),
  CONSTRAINT fk_claims_volunteer FOREIGN KEY (volunteer_id) REFERENCES users(id),
  INDEX ix_claims_ngo_status (ngo_id,status), INDEX ix_claims_volunteer_status (volunteer_id,status)
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  role ENUM('user','assistant') NOT NULL,
  content TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_chat_user FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX ix_chat_user_created (user_id,created_at)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  actor_id INT, action VARCHAR(120) NOT NULL, entity_type VARCHAR(80), entity_id INT,
  details JSON, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_actor FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX ix_audit_created (created_at)
);
