-- =========================================================
-- PARKSPOT DATABASE SCHEMA & SEED DATA
-- MySQL 8.0+
-- Optimized for Performance, Integrity, and Zero Bugs
-- =========================================================

CREATE DATABASE IF NOT EXISTS parkspot;
USE parkspot;

-- Disable foreign key checks during schema creation
SET FOREIGN_KEY_CHECKS = 0;

-- Drop existing tables/views in reverse order if needed (clean reinstall)
DROP VIEW IF EXISTS parking_availability_view;
DROP TABLE IF EXISTS search_logs;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS pricing_rules;
DROP TABLE IF EXISTS occupancy_records;
DROP TABLE IF EXISTS complaints;
DROP TABLE IF EXISTS ratings;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS parking_slots;
DROP TABLE IF EXISTS parking_managers;
DROP TABLE IF EXISTS parking_locations;
DROP TABLE IF EXISTS vehicles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS roles;

SET FOREIGN_KEY_CHECKS = 1;


-- =========================================================
-- 1. ROLES
-- =========================================================
CREATE TABLE roles (
    role_id TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    role_name VARCHAR(30) NOT NULL,

    PRIMARY KEY (role_id),
    UNIQUE KEY uk_roles_name (role_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO roles (role_id, role_name) VALUES
(1, 'USER'),
(2, 'MANAGER'),
(3, 'ADMIN');


-- =========================================================
-- 2. PERMISSIONS
-- =========================================================
CREATE TABLE permissions (
    permission_id TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    permission_name VARCHAR(50) NOT NULL,

    PRIMARY KEY (permission_id),
    UNIQUE KEY uk_permissions_name (permission_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO permissions (permission_id, permission_name) VALUES
(1, 'SEARCH_PARKING'),
(2, 'BOOK_PARKING'),
(3, 'CANCEL_BOOKING'),
(4, 'VIEW_BOOKING_HISTORY'),
(5, 'MANAGE_VEHICLE'),
(6, 'GIVE_RATING'),
(7, 'RAISE_COMPLAINT'),
(8, 'MANAGE_PARKING'),
(9, 'MANAGE_SLOTS'),
(10, 'MANAGE_BOOKINGS'),
(11, 'VIEW_REVENUE'),
(12, 'VIEW_OCCUPANCY'),
(13, 'MANAGE_USERS'),
(14, 'MANAGE_MANAGERS'),
(15, 'MANAGE_COMPLAINTS'),
(16, 'VIEW_REPORTS');


-- =========================================================
-- 3. ROLE PERMISSIONS
-- =========================================================
CREATE TABLE role_permissions (
    role_id TINYINT UNSIGNED NOT NULL,
    permission_id TINYINT UNSIGNED NOT NULL,

    PRIMARY KEY (role_id, permission_id),

    CONSTRAINT fk_role_permissions_role
        FOREIGN KEY (role_id)
        REFERENCES roles(role_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_role_permissions_permission
        FOREIGN KEY (permission_id)
        REFERENCES permissions(permission_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- USER PERMISSIONS
INSERT INTO role_permissions (role_id, permission_id) VALUES
(1,1), (1,2), (1,3), (1,4), (1,5), (1,6), (1,7);

-- MANAGER PERMISSIONS
INSERT INTO role_permissions (role_id, permission_id) VALUES
(2,8), (2,9), (2,10), (2,11), (2,12);

-- ADMIN PERMISSIONS
INSERT INTO role_permissions (role_id, permission_id) VALUES
(3,13), (3,14), (3,15), (3,16);


-- =========================================================
-- 4. USERS
-- =========================================================
-- Optimization: role_id defaults to 1 ('USER') to avoid raw insert errors
CREATE TABLE users (
    user_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    role_id TINYINT UNSIGNED NOT NULL DEFAULT 1,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(15),

    account_status ENUM('ACTIVE', 'INACTIVE', 'BLOCKED') NOT NULL DEFAULT 'ACTIVE',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id),
    UNIQUE KEY uk_users_email (email),
    KEY idx_users_role (role_id),
    KEY idx_users_status (account_status),

    CONSTRAINT fk_users_role
        FOREIGN KEY (role_id)
        REFERENCES roles(role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Default sample users with valid bcrypt password hashes
-- password for diuu@test.com: password123
-- password for manager@parkspot.com: manager123
INSERT INTO users (user_id, role_id, name, email, password_hash, phone, account_status)
VALUES
(1, 1, 'Diuu Test', 'diuu@test.com', '$2b$12$ipbCb8gUa7CBp1Ly8N6UpusgmqA6.LRSJ6pMCySld0tgWoea9Altm', '9999999999', 'ACTIVE'),
(2, 2, 'ParkSpot Manager', 'manager@parkspot.com', '$2b$12$27z/u03wGzFfA01yO9wJaeL6oQWf0dO2w3iN5n6fR3yH8sH.vOaU.', '8888888888', 'ACTIVE');


-- =========================================================
-- 5. VEHICLES
-- =========================================================
CREATE TABLE vehicles (
    vehicle_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    vehicle_number VARCHAR(20) NOT NULL,
    vehicle_type ENUM('CAR', 'BIKE', 'SCOOTER', 'EV', 'OTHER') NOT NULL,
    vehicle_model VARCHAR(100),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (vehicle_id),
    UNIQUE KEY uk_vehicle_number (vehicle_number),
    KEY idx_vehicles_user (user_id),

    CONSTRAINT fk_vehicles_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO vehicles (vehicle_id, user_id, vehicle_number, vehicle_type, vehicle_model)
VALUES
(1, 1, 'MH48AB1234', 'CAR', 'Honda City');


-- =========================================================
-- 6. PARKING LOCATIONS
-- =========================================================
CREATE TABLE parking_locations (
    location_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    location_name VARCHAR(150) NOT NULL,
    address VARCHAR(255) NOT NULL,

    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),

    capacity INT UNSIGNED NOT NULL,
    base_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,

    status ENUM('PENDING', 'ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'PENDING',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (location_id),
    KEY idx_locations_status (status),
    -- Optimization: Fast geo and nearby searches
    KEY idx_locations_active_coords (status, latitude, longitude),

    CONSTRAINT chk_location_capacity CHECK (capacity > 0),
    CONSTRAINT chk_location_price CHECK (base_price >= 0),
    CONSTRAINT chk_location_latitude CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    CONSTRAINT chk_location_longitude CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO parking_locations (location_id, location_name, address, latitude, longitude, capacity, base_price, status)
VALUES
(1, 'VCET Parking', 'Vasai, Maharashtra', 19.3919, 72.8397, 100, 30.00, 'ACTIVE'),
(2, 'Vasai Station Parking', 'Vasai, Maharashtra', 19.3810, 72.8320, 80, 25.00, 'ACTIVE'),
(3, 'City Mall Parking', 'Vasai, Maharashtra', 19.3845, 72.8450, 60, 40.00, 'ACTIVE');


-- =========================================================
-- 7. PARKING MANAGERS
-- =========================================================
CREATE TABLE parking_managers (
    manager_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    location_id BIGINT UNSIGNED NOT NULL,

    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (manager_id),
    UNIQUE KEY uk_manager_user (user_id),
    KEY idx_managers_location (location_id),

    CONSTRAINT fk_managers_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_managers_location
        FOREIGN KEY (location_id)
        REFERENCES parking_locations(location_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO parking_managers (manager_id, user_id, location_id)
VALUES
(1, 2, 1);


-- =========================================================
-- 8. PARKING SLOTS
-- =========================================================
CREATE TABLE parking_slots (
    slot_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    location_id BIGINT UNSIGNED NOT NULL,
    slot_number VARCHAR(20) NOT NULL,

    slot_type ENUM('CAR', 'BIKE', 'EV', 'HANDICAPPED', 'GENERAL') NOT NULL DEFAULT 'GENERAL',
    status ENUM('AVAILABLE', 'OCCUPIED', 'MAINTENANCE', 'RESERVED') NOT NULL DEFAULT 'AVAILABLE',

    PRIMARY KEY (slot_id),
    UNIQUE KEY uk_slot_location_number (location_id, slot_number),
    KEY idx_slots_location_status (location_id, status),
    -- Optimization: Fast filtered queries by location + type + status
    KEY idx_slots_type_status (slot_type, status),
    KEY idx_slots_loc_type_status (location_id, slot_type, status),

    CONSTRAINT fk_slots_location
        FOREIGN KEY (location_id)
        REFERENCES parking_locations(location_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO parking_slots (slot_id, location_id, slot_number, slot_type, status)
VALUES
(1, 1, 'A01', 'CAR', 'AVAILABLE'),
(2, 1, 'A02', 'CAR', 'AVAILABLE'),
(3, 1, 'A03', 'CAR', 'OCCUPIED'),
(4, 1, 'A04', 'CAR', 'AVAILABLE'),
(5, 1, 'A05', 'EV', 'AVAILABLE'),

(6, 2, 'B01', 'CAR', 'AVAILABLE'),
(7, 2, 'B02', 'CAR', 'OCCUPIED'),
(8, 2, 'B03', 'BIKE', 'AVAILABLE'),
(9, 2, 'B04', 'CAR', 'AVAILABLE'),

(10, 3, 'C01', 'CAR', 'AVAILABLE'),
(11, 3, 'C02', 'CAR', 'AVAILABLE'),
(12, 3, 'C03', 'EV', 'AVAILABLE'),
(13, 3, 'C04', 'HANDICAPPED', 'AVAILABLE');


-- =========================================================
-- 9. BOOKINGS
-- =========================================================
CREATE TABLE bookings (
    booking_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    user_id BIGINT UNSIGNED NOT NULL,
    vehicle_id BIGINT UNSIGNED NOT NULL,
    slot_id BIGINT UNSIGNED NOT NULL,

    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,

    booking_status ENUM('PENDING', 'CONFIRMED', 'ACTIVE', 'COMPLETED', 'CANCELLED') NOT NULL DEFAULT 'PENDING',
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (booking_id),
    KEY idx_bookings_user (user_id),
    KEY idx_bookings_slot_time (slot_id, start_time, end_time),
    KEY idx_bookings_status (booking_status),
    -- Optimization: Fast overlap check & validation
    KEY idx_bookings_slot_status_time (slot_id, booking_status, start_time, end_time),

    CONSTRAINT fk_bookings_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_bookings_vehicle
        FOREIGN KEY (vehicle_id)
        REFERENCES vehicles(vehicle_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_bookings_slot
        FOREIGN KEY (slot_id)
        REFERENCES parking_slots(slot_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_booking_time CHECK (end_time > start_time),
    CONSTRAINT chk_booking_amount CHECK (total_amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO bookings (booking_id, user_id, vehicle_id, slot_id, start_time, end_time, booking_status, total_amount)
VALUES
(1, 1, 1, 1, '2026-09-27 19:00:00', '2026-09-27 21:00:00', 'COMPLETED', 60.00);


-- =========================================================
-- 10. PAYMENTS
-- =========================================================
CREATE TABLE payments (
    payment_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    booking_id BIGINT UNSIGNED NOT NULL,

    amount DECIMAL(10,2) NOT NULL,
    payment_method ENUM('UPI', 'CARD', 'NET_BANKING', 'CASH') NOT NULL,
    payment_status ENUM('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED') NOT NULL DEFAULT 'PENDING',

    transaction_reference VARCHAR(100),
    paid_at DATETIME,

    PRIMARY KEY (payment_id),
    UNIQUE KEY uk_payment_booking (booking_id),
    UNIQUE KEY uk_transaction_reference (transaction_reference),
    -- Optimization: Fast revenue and financial summary calculations
    KEY idx_payments_status (payment_status),

    CONSTRAINT fk_payments_booking
        FOREIGN KEY (booking_id)
        REFERENCES bookings(booking_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_payment_amount CHECK (amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO payments (payment_id, booking_id, amount, payment_method, payment_status, transaction_reference, paid_at)
VALUES
(1, 1, 60.00, 'UPI', 'SUCCESS', 'TXN_PARKSPOT_001', '2026-09-27 19:05:00');


-- =========================================================
-- 11. RATINGS
-- =========================================================
CREATE TABLE ratings (
    rating_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    location_id BIGINT UNSIGNED NOT NULL,
    booking_id BIGINT UNSIGNED NOT NULL,

    rating TINYINT UNSIGNED NOT NULL,
    review TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (rating_id),
    UNIQUE KEY uk_rating_booking (booking_id),
    KEY idx_ratings_location (location_id),
    KEY idx_ratings_user (user_id),

    CONSTRAINT fk_ratings_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_ratings_location
        FOREIGN KEY (location_id)
        REFERENCES parking_locations(location_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_ratings_booking
        FOREIGN KEY (booking_id)
        REFERENCES bookings(booking_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_rating_value CHECK (rating BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO ratings (rating_id, user_id, location_id, booking_id, rating, review)
VALUES
(1, 1, 1, 1, 5, 'Clean parking area and easy booking experience.');


-- =========================================================
-- 12. COMPLAINTS
-- =========================================================
CREATE TABLE complaints (
    complaint_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    booking_id BIGINT UNSIGNED,

    subject VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,

    status ENUM('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED') NOT NULL DEFAULT 'OPEN',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,

    PRIMARY KEY (complaint_id),
    KEY idx_complaints_user (user_id),
    KEY idx_complaints_status (status),

    CONSTRAINT fk_complaints_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_complaints_booking
        FOREIGN KEY (booking_id)
        REFERENCES bookings(booking_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =========================================================
-- 13. OCCUPANCY RECORDS
-- =========================================================
CREATE TABLE occupancy_records (
    occupancy_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    location_id BIGINT UNSIGNED NOT NULL,
    recorded_at DATETIME NOT NULL,

    occupied_slots INT UNSIGNED NOT NULL,
    available_slots INT UNSIGNED NOT NULL,
    occupancy_percentage DECIMAL(5,2),

    PRIMARY KEY (occupancy_id),
    KEY idx_occupancy_location_time (location_id, recorded_at),

    CONSTRAINT fk_occupancy_location
        FOREIGN KEY (location_id)
        REFERENCES parking_locations(location_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_occupancy_percentage CHECK (
        occupancy_percentage IS NULL OR occupancy_percentage BETWEEN 0 AND 100
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO occupancy_records (location_id, recorded_at, occupied_slots, available_slots, occupancy_percentage)
VALUES
(1, '2026-09-21 09:00:00', 2, 3, 40.00),
(1, '2026-09-21 13:00:00', 4, 1, 80.00),
(1, '2026-09-21 18:00:00', 5, 0, 100.00),
(1, '2026-09-22 09:00:00', 2, 3, 40.00),
(1, '2026-09-22 13:00:00', 3, 2, 60.00),
(1, '2026-09-22 18:00:00', 5, 0, 100.00),
(1, '2026-09-23 09:00:00', 3, 2, 60.00),
(1, '2026-09-23 13:00:00', 4, 1, 80.00),
(1, '2026-09-23 18:00:00', 4, 1, 80.00),
(1, '2026-09-24 09:00:00', 2, 3, 40.00),
(1, '2026-09-24 13:00:00', 4, 1, 80.00),
(1, '2026-09-24 18:00:00', 5, 0, 100.00),
(1, '2026-09-25 09:00:00', 3, 2, 60.00),
(1, '2026-09-25 13:00:00', 4, 1, 80.00),
(1, '2026-09-25 18:00:00', 5, 0, 100.00);


-- =========================================================
-- 14. PRICING RULES
-- =========================================================
CREATE TABLE pricing_rules (
    pricing_rule_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    location_id BIGINT UNSIGNED NOT NULL,

    day_of_week ENUM('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY') NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,

    price_per_hour DECIMAL(10,2) NOT NULL,

    PRIMARY KEY (pricing_rule_id),
    KEY idx_pricing_location_day (location_id, day_of_week),

    CONSTRAINT fk_pricing_location
        FOREIGN KEY (location_id)
        REFERENCES parking_locations(location_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_pricing_time CHECK (end_time > start_time),
    CONSTRAINT chk_pricing_price CHECK (price_per_hour >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO pricing_rules (location_id, day_of_week, start_time, end_time, price_per_hour)
VALUES
(1, 'MONDAY', '08:00:00', '18:00:00', 35.00),
(1, 'SATURDAY', '10:00:00', '22:00:00', 50.00);


-- =========================================================
-- 15. NOTIFICATIONS
-- =========================================================
CREATE TABLE notifications (
    notification_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,

    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (notification_id),
    KEY idx_notifications_user_read (user_id, is_read),

    CONSTRAINT fk_notifications_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =========================================================
-- 16. AUDIT LOGS
-- =========================================================
CREATE TABLE audit_logs (
    audit_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED,

    action VARCHAR(100) NOT NULL,
    table_name VARCHAR(100),
    record_id BIGINT UNSIGNED,
    ip_address VARCHAR(45),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (audit_id),
    KEY idx_audit_user_time (user_id, created_at),

    CONSTRAINT fk_audit_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =========================================================
-- 17. SEARCH LOGS
-- =========================================================
CREATE TABLE search_logs (
    search_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED,

    ip_address VARCHAR(45),
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    search_radius_km DECIMAL(6,2),

    searched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (search_id),
    KEY idx_search_user (user_id),
    KEY idx_search_coordinates (latitude, longitude),

    CONSTRAINT fk_search_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =========================================================
-- 18. DATABASE VIEWS
-- =========================================================
CREATE OR REPLACE VIEW parking_availability_view AS
SELECT
    pl.location_id,
    pl.location_name,
    pl.address,
    COUNT(ps.slot_id) AS total_slots,
    SUM(CASE WHEN ps.status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_slots,
    SUM(CASE WHEN ps.status = 'OCCUPIED' THEN 1 ELSE 0 END) AS occupied_slots
FROM parking_locations pl
LEFT JOIN parking_slots ps
    ON pl.location_id = ps.location_id
WHERE pl.status = 'ACTIVE'
GROUP BY
    pl.location_id,
    pl.location_name,
    pl.address;


-- =========================================================
-- 19. OPTIMIZED ANALYTICAL & REPORTING QUERIES
-- =========================================================

-- Q1: Total Revenue by Parking Location
SELECT
    pl.location_id,
    pl.location_name,
    COUNT(p.payment_id) AS successful_payments,
    COALESCE(SUM(p.amount), 0.00) AS total_revenue
FROM payments p
JOIN bookings b ON p.booking_id = b.booking_id
JOIN parking_slots ps ON b.slot_id = ps.slot_id
JOIN parking_locations pl ON ps.location_id = pl.location_id
WHERE p.payment_status = 'SUCCESS'
GROUP BY pl.location_id, pl.location_name
ORDER BY total_revenue DESC;

-- Q2: Most-Used Parking Locations (Excluding Cancelled Bookings)
SELECT
    pl.location_id,
    pl.location_name,
    COUNT(b.booking_id) AS total_bookings
FROM bookings b
JOIN parking_slots ps ON b.slot_id = ps.slot_id
JOIN parking_locations pl ON ps.location_id = pl.location_id
WHERE b.booking_status <> 'CANCELLED'
GROUP BY pl.location_id, pl.location_name
ORDER BY total_bookings DESC;

-- Q3: Average Rating by Parking Location
SELECT
    pl.location_id,
    pl.location_name,
    COUNT(r.rating_id) AS total_reviews,
    ROUND(AVG(r.rating), 2) AS average_rating
FROM ratings r
JOIN parking_locations pl ON r.location_id = pl.location_id
GROUP BY pl.location_id, pl.location_name
ORDER BY average_rating DESC;

-- Q4: Detect Active Overlapping Bookings (Excludes Cancelled Bookings)
SELECT
    b1.booking_id AS booking_1,
    b2.booking_id AS booking_2,
    b1.slot_id,
    b1.start_time AS booking_1_start,
    b1.end_time AS booking_1_end,
    b2.start_time AS booking_2_start,
    b2.end_time AS booking_2_end
FROM bookings b1
JOIN bookings b2
    ON b1.slot_id = b2.slot_id
    AND b1.booking_id < b2.booking_id
    AND b1.start_time < b2.end_time
    AND b1.end_time > b2.start_time
WHERE b1.booking_status NOT IN ('CANCELLED')
  AND b2.booking_status NOT IN ('CANCELLED');

-- Q5: Nearby Parking Locations Using Haversine Formula (Clean and optimized)
SELECT
    location_id,
    location_name,
    address,
    latitude,
    longitude,
    ROUND(
        6371 * ACOS(
            LEAST(
                1,
                GREATEST(
                    -1,
                    COS(RADIANS(19.3919))
                    * COS(RADIANS(latitude))
                    * COS(RADIANS(longitude) - RADIANS(72.8397))
                    + SIN(RADIANS(19.3919))
                    * SIN(RADIANS(latitude))
                )
            )
        ),
        2
    ) AS distance_km
FROM parking_locations
WHERE status = 'ACTIVE'
  AND latitude IS NOT NULL
  AND longitude IS NOT NULL
ORDER BY distance_km ASC;

-- Q6: Comprehensive ParkScore Calculation
SELECT
    pl.location_id,
    pl.location_name,
    ROUND(
        (
            (SUM(CASE WHEN ps.status = 'AVAILABLE' THEN 1 ELSE 0 END) / COUNT(ps.slot_id)) * 40
        )
        +
        (
            COALESCE(AVG(r.rating), 0) / 5 * 30
        )
        +
        (
            (1 - (pl.base_price / NULLIF((SELECT MAX(base_price) FROM parking_locations WHERE status = 'ACTIVE'), 0))) * 30
        ),
        2
    ) AS park_score
FROM parking_locations pl
JOIN parking_slots ps ON pl.location_id = ps.location_id
LEFT JOIN ratings r ON pl.location_id = r.location_id
WHERE pl.status = 'ACTIVE'
GROUP BY pl.location_id, pl.location_name, pl.base_price
ORDER BY park_score DESC;
