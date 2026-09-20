DB_MIG_DIR := "db/migrations"
DB_PATH := "data/proceeded/data.db"
DB_PATH_SQLITE :="sqlite3://" + DB_PATH
DB_DUMP_DIR := "dumps"

@dump:
  #! /bin/env bash
  dumpfile="{{DB_DUMP_DIR}}/$(date +%FT%H-%M-%S)_data.sql"
  sqlite3 {{DB_PATH}} ".dump" > "$dumpfile"
  echo "Successfully dumped at $dumpfile"


@connectdb:
  sqlite3 {{DB_PATH}}

# Install migrate CLI tool
@mig-install:
    go install -tags 'sqlite3' github.com/golang-migrate/migrate/v4/cmd/migrate@latest

@mig name:
  migrate create -ext sql -dir {{DB_MIG_DIR}} {{name}}

@mig-up n="":
  just mig-base up {{n}}

alias mig-dn := mig-down
@mig-down n="1":
  just mig-base down {{n}}

@mig-reset:
  just mig-base down -all

@mig-ver:
  just mig-base version

@mig-force version:
  just mig-base force {{version}}

@mig-goto version:
  just mig-base goto {{version}}

[private]
mig-base +args:
  migrate -database {{DB_PATH_SQLITE}} -path {{DB_MIG_DIR}} {{args}}
