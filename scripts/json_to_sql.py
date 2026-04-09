#!/usr/bin/env python3
"""
Convert cocktails_enriched.json to a normalized SQLite database.
"""

import json
import sqlite3
import os

JSON_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'cocktails_enriched.json')
DB_PATH   = os.path.join(os.path.dirname(__file__), '..', 'data', 'cocktails.db')

# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cocktails (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    category     TEXT,
    alcoholic    TEXT,
    glass        TEXT,
    instructions TEXT,
    thumbnail    TEXT,
    strength     TEXT
);

CREATE TABLE IF NOT EXISTS ingredients (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    cocktail_id   TEXT NOT NULL REFERENCES cocktails(id) ON DELETE CASCADE,
    ingredient    TEXT,
    measure       TEXT
);

CREATE TABLE IF NOT EXISTS flavor_profiles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cocktail_id TEXT NOT NULL REFERENCES cocktails(id) ON DELETE CASCADE,
    flavor      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS moods (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cocktail_id TEXT NOT NULL REFERENCES cocktails(id) ON DELETE CASCADE,
    mood        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS taste_tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cocktail_id TEXT NOT NULL REFERENCES cocktails(id) ON DELETE CASCADE,
    tag         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS best_for (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cocktail_id TEXT NOT NULL REFERENCES cocktails(id) ON DELETE CASCADE,
    use_case    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cocktail_id TEXT NOT NULL REFERENCES cocktails(id) ON DELETE CASCADE,
    tag         TEXT NOT NULL
);

-- Indexes for fast FK lookups
CREATE INDEX IF NOT EXISTS idx_ingredients_cocktail    ON ingredients(cocktail_id);
CREATE INDEX IF NOT EXISTS idx_flavor_profiles_cocktail ON flavor_profiles(cocktail_id);
CREATE INDEX IF NOT EXISTS idx_moods_cocktail           ON moods(cocktail_id);
CREATE INDEX IF NOT EXISTS idx_taste_tags_cocktail      ON taste_tags(cocktail_id);
CREATE INDEX IF NOT EXISTS idx_best_for_cocktail        ON best_for(cocktail_id);
CREATE INDEX IF NOT EXISTS idx_tags_cocktail            ON tags(cocktail_id);
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def insert_list(cur, table, cocktail_id, column, items):
    """Insert a list of scalar values into a child table."""
    if not items:
        return 0
    cur.executemany(
        f"INSERT INTO {table} (cocktail_id, {column}) VALUES (?, ?)",
        [(cocktail_id, item) for item in items if item is not None]
    )
    return cur.rowcount

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Remove stale DB so we start clean
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        cocktails = json.load(f)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Apply schema (executes all statements separated by semicolons)
    cur.executescript(SCHEMA)
    con.commit()

    counts = {
        'cocktails':       0,
        'ingredients':     0,
        'flavor_profiles': 0,
        'moods':           0,
        'taste_tags':      0,
        'best_for':        0,
        'tags':            0,
    }

    for c in cocktails:
        cid = str(c['id'])

        # ── cocktails ──────────────────────────────────────────────────────
        cur.execute(
            """INSERT OR REPLACE INTO cocktails
               (id, name, category, alcoholic, glass, instructions, thumbnail, strength)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cid,
                c.get('name'),
                c.get('category'),
                c.get('alcoholic'),
                c.get('glass'),
                c.get('instructions'),
                c.get('thumbnail'),
                c.get('strength'),
            )
        )
        counts['cocktails'] += 1

        # ── ingredients ───────────────────────────────────────────────────
        for ing in c.get('ingredients') or []:
            cur.execute(
                "INSERT INTO ingredients (cocktail_id, ingredient, measure) VALUES (?, ?, ?)",
                (cid, ing.get('ingredient'), ing.get('measure'))
            )
            counts['ingredients'] += 1

        # ── flavor_profiles ───────────────────────────────────────────────
        for flavor in c.get('flavor_profile') or []:
            cur.execute(
                "INSERT INTO flavor_profiles (cocktail_id, flavor) VALUES (?, ?)",
                (cid, flavor)
            )
            counts['flavor_profiles'] += 1

        # ── moods ─────────────────────────────────────────────────────────
        for mood in c.get('mood') or []:
            cur.execute(
                "INSERT INTO moods (cocktail_id, mood) VALUES (?, ?)",
                (cid, mood)
            )
            counts['moods'] += 1

        # ── taste_tags ────────────────────────────────────────────────────
        for tag in c.get('taste_tags') or []:
            cur.execute(
                "INSERT INTO taste_tags (cocktail_id, tag) VALUES (?, ?)",
                (cid, tag)
            )
            counts['taste_tags'] += 1

        # ── best_for ──────────────────────────────────────────────────────
        for use_case in c.get('best_for') or []:
            cur.execute(
                "INSERT INTO best_for (cocktail_id, use_case) VALUES (?, ?)",
                (cid, use_case)
            )
            counts['best_for'] += 1

        # ── tags ──────────────────────────────────────────────────────────
        for tag in c.get('tags') or []:
            cur.execute(
                "INSERT INTO tags (cocktail_id, tag) VALUES (?, ?)",
                (cid, tag)
            )
            counts['tags'] += 1

    con.commit()
    con.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n  SQLite database written to:", os.path.abspath(DB_PATH))
    print("\n  Rows inserted per table:")
    print(f"    {'Table':<20} {'Rows':>6}")
    print(f"    {'-'*20}  {'-'*6}")
    for table, n in counts.items():
        print(f"    {table:<20} {n:>6}")
    print(f"\n    {'TOTAL':<20} {sum(counts.values()):>6}\n")


if __name__ == '__main__':
    main()
