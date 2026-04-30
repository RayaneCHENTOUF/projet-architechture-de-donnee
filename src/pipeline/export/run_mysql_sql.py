#!/usr/bin/env python3
"""Execute SQL files against MySQL.

Usage examples:
python src/pipeline/export/run_mysql_sql.py --all
python src/pipeline/export/run_mysql_sql.py --files sql/kpi_prix_m2_quartier_annuel.sql
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import mysql.connector
from mysql.connector import errorcode


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SQL scripts on MySQL.")
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    parser.add_argument("--database", default=os.getenv("MYSQL_DATABASE", "urban_data"))
    parser.add_argument("--user", default=os.getenv("MYSQL_USER", "root"))
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD", "nawfel"))
    parser.add_argument(
        "--sql-dir",

        default="../../../sql",
        help="Directory where SQL files are located.",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        help="Explicit file list to run (relative or absolute paths).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all kpi_*.sql files from --sql-dir in lexical order.",
    )
    parser.add_argument(
        "--create-db-if-missing",
        action="store_true",
        help="Create the target database if it does not already exist.",
    )
    return parser.parse_args()


def resolve_files(args: argparse.Namespace) -> list[Path]:
    def resolve_input_path(p: str) -> Path:
        candidate = Path(p)
        if candidate.is_absolute():
            return candidate
        if candidate.exists():
            return candidate.resolve()
        return (REPO_ROOT / candidate).resolve()

    if args.files:
        return [resolve_input_path(f) for f in args.files]

    if args.all:
        sql_dir = resolve_input_path(args.sql_dir)
        if not sql_dir.exists():
            raise FileNotFoundError(
                f"SQL directory not found: {sql_dir} (cwd={Path.cwd()})"
            )

        files = sorted(sql_dir.glob("kpi_*.sql"))
        if not files:
            raise FileNotFoundError(f"No kpi_*.sql files found in {sql_dir}")
        return files

    raise ValueError("Use --files or --all")


def connect_mysql(
    host: str,
    port: int,
    user: str,
    password: str,
    database: str | None,
):
    return mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        autocommit=False,
        use_pure=True,
        allow_local_infile=True,
    )


def ensure_database(args: argparse.Namespace) -> None:
    conn = connect_mysql(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=None,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{args.database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()


def run_sql_file(conn, file_path: Path) -> None:
    sql = file_path.read_text(encoding="utf-8")

    def has_executable_sql(statement: str) -> bool:
        in_block_comment = False
        kept_parts: list[str] = []

        for raw_line in statement.splitlines():
            line = raw_line

            if in_block_comment:
                if "*/" in line:
                    line = line.split("*/", 1)[1]
                    in_block_comment = False
                else:
                    continue

            while "/*" in line:
                before, after = line.split("/*", 1)
                if "*/" in after:
                    after = after.split("*/", 1)[1]
                    line = before + " " + after
                else:
                    line = before
                    in_block_comment = True
                    break

            line = line.split("--", 1)[0]
            if line.strip():
                kept_parts.append(line)

        return bool("\n".join(kept_parts).strip())

    # mysql-connector versions may not support cursor.execute(..., multi=True).
    # Split simple migration scripts on ';' while preserving quoted text.
    statements: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    prev = ""

    for ch in sql:
        if ch == "'" and not in_double and prev != "\\":
            in_single = not in_single
        elif ch == '"' and not in_single and prev != "\\":
            in_double = not in_double

        if ch == ";" and not in_single and not in_double:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
        else:
            current.append(ch)
        prev = ch

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)

    with conn.cursor() as cur:
        for stmt in statements:
            if not has_executable_sql(stmt):
                continue
            cur.execute(stmt)
    conn.commit()


def main() -> None:
    args = parse_args()
    files = resolve_files(args)

    if args.create_db_if_missing:
        ensure_database(args)

    try:
        conn = connect_mysql(
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
            database=args.database,
        )
    except mysql.connector.Error as exc:
        if exc.errno == errorcode.ER_BAD_DB_ERROR and args.create_db_if_missing:
            ensure_database(args)
            conn = connect_mysql(
                host=args.host,
                port=args.port,
                user=args.user,
                password=args.password,
                database=args.database,
            )
        else:
            raise

    try:
        for file_path in files:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            print(f"[RUN] {file_path}")
            run_sql_file(conn, file_path)
            print(f"[OK] {file_path}")
    finally:
        conn.close()

    print("Done.")


if __name__ == "__main__":
    main() 
