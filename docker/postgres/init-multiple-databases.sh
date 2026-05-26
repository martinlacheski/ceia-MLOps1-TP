#!/usr/bin/env bash
set -euo pipefail

function create_database() {
  local database=$1
  echo "Creating database '${database}'"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE ${database}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${database}')\gexec
    GRANT ALL PRIVILEGES ON DATABASE ${database} TO ${POSTGRES_USER};
EOSQL
}

if [[ -n "${POSTGRES_MULTIPLE_DATABASES:-}" ]]; then
  IFS=',' read -ra databases <<< "$POSTGRES_MULTIPLE_DATABASES"
  for database in "${databases[@]}"; do
    create_database "$database"
  done
fi
