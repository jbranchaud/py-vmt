from sqlite3 import Connection


MIGRATIONS = [
    # v1
    """
    create table tags (
        id integer primary key,
        name text not null unique,
        created_at text not null default (datetime('now')),
        updated_at text not null default (datetime('now'))
    );

    create table projects (
        id integer primary key,
        name text not null unique,
        created_at text not null default (datetime('now')),
        updated_at text not null default (datetime('now'))
    );

    create table sessions (
        id integer primary key,
        active integer not null check (active in (0, 1)),
        project_id integer not null references projects(id) on delete cascade,
        start_time text not null,
        end_time text,
        created_at text not null default (datetime('now')),
        updated_at text not null default (datetime('now'))
    );
    create unique index idx_sessions_single_active
        on sessions(active)
        where active = 1;

    create table session_tags (
        session_id integer not null references sessions(id) on delete cascade,
        tag_id integer not null references tags(id) on delete cascade,
        primary key (session_id, tag_id)
    );
    create index idx_session_tags_tag on session_tags(tag_id);
    """
]


# Using the `user_version` pragma in SQLite, this checks if there are any
# sets of statements in `MIGRATIONS` that have not been run yet. It then
# executes those and updates `user_version`.
def migrate(conn: Connection):
    version = conn.execute("pragma user_version").fetchone()[0]
    for i, statement in enumerate(MIGRATIONS[version:], start=version):
        conn.executescript(statement)
        conn.execute(f"pragma user_version = {i + 1}")
    conn.commit()
