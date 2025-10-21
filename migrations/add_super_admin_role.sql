-- Migration: Add SUPER_ADMIN role to UserRole enum
-- Description: Adds 'super_admin' value to the user_role enum type in PostgreSQL
-- Date: 2025-10-16

-- Add super_admin value to the enum BEFORE admin
-- Note: PostgreSQL ENUM values cannot be removed once added
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'super_admin' BEFORE 'admin';

-- Verify the enum values
-- SELECT unnest(enum_range(NULL::user_role)) AS user_roles;

-- Expected output after migration:
-- super_admin
-- admin
-- lecturer
-- student
