#!/usr/bin/env python3
"""
Usage examples:
  # Generate queries from inputs.json and append new ones to queries.csv
  python query_manager.py gen-queries --inputs inputs.json --queries queries.csv

  # Add a painpoint discovered by an agent
  python query_manager.py add-painpoint --queries queries.csv --painpoints painpoints.csv \
      --query-id 12 --url "https://reddit.com/..." --quote "No encuentro repuestos..."

  # Mark a query as searched and set counts
  python query_manager.py mark-searched --queries queries.csv --query-id 12 \
      --date-searched 2025-08-09 --num-results 25 --num-painpoints 3

  # List pending queries
  python query_manager.py list-queries --queries queries.csv --status pending
"""

import argparse
import csv
import json
import os
import sys
import tempfile
import time
from datetime import datetime
from itertools import product

LOCK_TRIES = 10
LOCK_WAIT = 0.2  # seconds
DATE_FMT = "%Y-%m-%d"

QUERIES_FIELDS = [
    "query_id", "product_niche", "site", "query", "date_created",
    "date_searched", "num_results_searched", "num_painpoints_found", "status"
]

PAINPOINTS_FIELDS = [
    "painpoint_id", "query_id", "url", "quote", "author", "date_found"
]


def acquire_lock(lock_path):
    tries = 0
    while True:
        try:
            # Atomic create
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            tries += 1
            if tries >= LOCK_TRIES:
                return False
            time.sleep(LOCK_WAIT)


def release_lock(lock_path):
    try:
        os.remove(lock_path)
    except FileNotFoundError:
        pass


def atomic_write_csv(path, rows, fieldnames):
    """Atomically write the entire CSV file (used when updating small metadata fields)."""
    dirn = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix="tmp_", dir=dirn, text=True)
    os.close(fd)
    try:
        with open(tmp_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def ensure_csv_exists(path, fieldnames):
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def read_csv_as_dicts(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def next_int_id(rows, id_field):
    max_id = 0
    for r in rows:
        try:
            v = int(r.get(id_field, 0) or 0)
            if v > max_id:
                max_id = v
        except Exception:
            continue
    return max_id + 1


def normalize_site_for_niche(site):
    """Normalize site string (strip site: prefix) for default niche name fallback."""
    s = site
    if s.startswith("site:"):
        s = s.split("site:", 1)[1]
    s = s.strip().rstrip("/")
    return s


def gen_queries(inputs_path, queries_path, lock=True):
    with open(inputs_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sites = data.get("SITES", [])
    key_phrases = data.get("KEY_PHRASES", [])
    site_map = data.get("SITE_MAP", {})

    ensure_csv_exists(queries_path, QUERIES_FIELDS)
    lockfile = queries_path + ".lock"

    if lock and not acquire_lock(lockfile):
        print("Could not acquire lock for queries file. Try again later.", file=sys.stderr)
        sys.exit(1)

    try:
        rows = read_csv_as_dicts(queries_path)
        existing_queries = set(r["query"] for r in rows)

        next_id = next_int_id(rows, "query_id")

        added = 0
        now = datetime.utcnow().strftime(DATE_FMT)
        for site, phrase in product(sites, key_phrases):
            # ensure we create a site token usable in queries
            site_token = site.strip()
            # standard query
            query_text = f'site:{site_token} "{phrase}"'
            if query_text in existing_queries:
                continue
            product_niche = site_map.get(site_token) or normalize_site_for_niche(site_token)
            new_row = {
                "query_id": str(next_id),
                "product_niche": product_niche,
                "site": site_token,
                "query": query_text,
                "date_created": now,
                "date_searched": "",
                "num_results_searched": "0",
                "num_painpoints_found": "0",
                "status": "pending"
            }
            rows.append(new_row)
            existing_queries.add(query_text)
            next_id += 1
            added += 1

        if added:
            atomic_write_csv(queries_path, rows, QUERIES_FIELDS)
        print(f"Generated {added} new queries (file: {queries_path}).")
    finally:
        if lock:
            release_lock(lockfile)


def list_queries(queries_path, status=None, limit=None):
    rows = read_csv_as_dicts(queries_path)
    results = []
    for r in rows:
        if status and r.get("status") != status:
            continue
        results.append(r)
        if limit and len(results) >= limit:
            break
    # print as CSV to stdout
    writer = csv.DictWriter(sys.stdout, fieldnames=QUERIES_FIELDS)
    writer.writeheader()
    for r in results:
        writer.writerow(r)


def add_painpoint(queries_path, painpoints_path, query_id, url, quote, author=None, lock=True):
    ensure_csv_exists(painpoints_path, PAINPOINTS_FIELDS)
    lockfile = painpoints_path + ".lock"
    if lock and not acquire_lock(lockfile):
        print("Could not acquire lock for painpoints file. Try again later.", file=sys.stderr)
        sys.exit(1)
    try:
        pain_rows = read_csv_as_dicts(painpoints_path)
        next_id = next_int_id(pain_rows, "painpoint_id")
        now = datetime.utcnow().strftime(DATE_FMT)
        new_pp = {
            "painpoint_id": str(next_id),
            "query_id": str(query_id),
            "url": url,
            "quote": quote,
            "author": author or "",
            "date_found": now
        }
        # append safely
        with open(painpoints_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=PAINPOINTS_FIELDS)
            if os.path.getsize(painpoints_path) == 0:
                writer.writeheader()
            writer.writerow(new_pp)
        print(f"Appended painpoint id={next_id} to {painpoints_path}")
    finally:
        if lock:
            release_lock(lockfile)


def mark_searched(queries_path, query_id, date_searched=None, num_results=None, num_painpoints=None, status=None, lock=True):
    ensure_csv_exists(queries_path, QUERIES_FIELDS)
    lockfile = queries_path + ".lock"
    if lock and not acquire_lock(lockfile):
        print("Could not acquire lock for queries file. Try again later.", file=sys.stderr)
        sys.exit(1)
    try:
        rows = read_csv_as_dicts(queries_path)
        changed = False
        for r in rows:
            if str(r.get("query_id")) == str(query_id):
                if date_searched:
                    r["date_searched"] = date_searched
                if num_results is not None:
                    r["num_results_searched"] = str(num_results)
                if num_painpoints is not None:
                    r["num_painpoints_found"] = str(num_painpoints)
                if status:
                    r["status"] = status
                changed = True
                break
        if not changed:
            print(f"No query with id {query_id} found in {queries_path}", file=sys.stderr)
            return
        atomic_write_csv(queries_path, rows, QUERIES_FIELDS)
        print(f"Updated query {query_id}")
    finally:
        if lock:
            release_lock(lockfile)


def summary(queries_path, painpoints_path):
    qrows = read_csv_as_dicts(queries_path)
    prows = read_csv_as_dicts(painpoints_path)
    total_q = len(qrows)
    pending = sum(1 for r in qrows if r.get("status") == "pending")
    searched = total_q - pending
    total_pp = len(prows)
    print(f"Queries: total={total_q}, pending={pending}, searched={searched}")
    print(f"Painpoints logged: {total_pp}")
    # top queries by painpoints_found
    by_pp = sorted(qrows, key=lambda r: int(r.get("num_painpoints_found", 0) or 0), reverse=True)
    print("\nTop queries by recorded painpoints:")
    for r in by_pp[:10]:
        print(f"  id={r['query_id']} pp={r.get('num_painpoints_found')} status={r.get('status')} {r.get('query')}")


def parse_args():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)

    g = sp.add_parser("gen-queries")
    g.add_argument("--inputs", required=True)
    g.add_argument("--queries", required=True)

    l = sp.add_parser("list-queries")
    l.add_argument("--queries", required=True)
    l.add_argument("--status", required=False)
    l.add_argument("--limit", type=int, required=False)

    ap = sp.add_parser("add-painpoint")
    ap.add_argument("--queries", required=True)
    ap.add_argument("--painpoints", required=True)
    ap.add_argument("--query-id", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--quote", required=True)
    ap.add_argument("--author", required=False)

    ms = sp.add_parser("mark-searched")
    ms.add_argument("--queries", required=True)
    ms.add_argument("--query-id", required=True)
    ms.add_argument("--date-searched", required=False)
    ms.add_argument("--num-results", type=int, required=False)
    ms.add_argument("--num-painpoints", type=int, required=False)
    ms.add_argument("--status", required=False)

    s = sp.add_parser("summary")
    s.add_argument("--queries", required=True)
    s.add_argument("--painpoints", required=True)

    return p.parse_args()


def main():
    args = parse_args()
    if args.cmd == "gen-queries":
        gen_queries(args.inputs, args.queries)
    elif args.cmd == "list-queries":
        list_queries(args.queries, status=args.status, limit=args.limit)
    elif args.cmd == "add-painpoint":
        add_painpoint(args.queries, args.painpoints, args.query_id, args.url, args.quote, author=args.author)
    elif args.cmd == "mark-searched":
        ds = args.date_searched or datetime.utcnow().strftime(DATE_FMT)
        mark_searched(args.queries, args.query_id, date_searched=ds,
                      num_results=args.num_results, num_painpoints=args.num_painpoints, status=args.status)
    elif args.cmd == "summary":
        summary(args.queries, args.painpoints)
    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
