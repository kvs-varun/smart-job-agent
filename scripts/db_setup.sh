#!/bin/bash
# Smart Job Agent V2 — Database Setup Script
# Usage: bash scripts/db_setup.sh

set -e

DB_NAME="${POSTGRES_DB:-smartjob_v2}"
DB_USER="${POSTGRES_USER:-smartjob}"
DB_PASS="${POSTGRES_PASSWORD:-smartjob}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

echo ">>> Creating PostgreSQL database and user..."

psql -U postgres -h $DB_HOST -p $DB_PORT <<EOF
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
    CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
  END IF;
END
\$\$;

SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')
\gexec
EOF

echo ">>> Running schema migrations..."
psql -U $DB_USER -d $DB_NAME -h $DB_HOST -p $DB_PORT -f backend_v2/db/schema.sql

echo ">>> Database setup complete."
echo "    DB:   $DB_NAME"
echo "    User: $DB_USER"
echo "    Host: $DB_HOST:$DB_PORT"
