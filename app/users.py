"""Users (PLAN-app.md §3): Gus (estimator) and his boss (manager). In v1 both can do everything; the role is shown
and, from step 3 on, recorded with every action.

    python -m app.users add <name> --role estimator|manager      asks for the password twice
    python -m app.users set-password <name>                      asks for the new password twice
    python -m app.users list
Add --password-stdin to read the password from one line of standard input instead (scripts, tests)."""
import argparse, getpass, re, sys
from dataclasses import dataclass

ROLES = ("estimator", "manager")
NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,31}$")
MIN_PASSWORD = 10


class UserError(ValueError):
    pass


@dataclass(frozen=True)
class User:
    id: int
    name: str
    role: str


def _check_password(password):
    if len(password) < MIN_PASSWORD:
        raise UserError(f"the password must have at least {MIN_PASSWORD} characters")


def add(settings, name, role, password):
    from app import auth, db
    name = (name or "").strip().lower()
    if not NAME.match(name):
        raise UserError(f"the name must be 1-32 letters, digits, '.', '_' or '-' (no spaces), not {name!r}")
    if role not in ROLES:
        raise UserError(f"the role must be {' or '.join(ROLES)}, not {role!r}")
    _check_password(password)
    conn = db.connect(settings)
    try:
        if conn.execute("SELECT 1 FROM users WHERE name = ?", (name,)).fetchone():
            raise UserError(f"a user called {name!r} already exists")
        with conn:
            conn.execute("INSERT INTO users (name, role, password_hash, created_at) VALUES (?, ?, ?, ?)",
                         (name, role, auth.hash_password(password), auth.now()))
    finally:
        conn.close()


def set_password(settings, name, password):
    from app import auth, db
    _check_password(password)
    conn = db.connect(settings)
    try:
        with conn:
            n = conn.execute("UPDATE users SET password_hash = ? WHERE name = ?", (auth.hash_password(password), name.strip().lower())).rowcount
            if n:
                # a new password ends that user's sessions everywhere
                conn.execute("DELETE FROM sessions WHERE user_id = (SELECT id FROM users WHERE name = ?)", (name.strip().lower(),))
        if not n:
            raise UserError(f"there is no user called {name!r}")
    finally:
        conn.close()


def find(conn, name):
    """(User, password_hash) or None."""
    row = conn.execute("SELECT id, name, role, password_hash FROM users WHERE name = ? AND active = 1", ((name or "").strip().lower(),)).fetchone()
    return (User(row["id"], row["name"], row["role"]), row["password_hash"]) if row else None


def all_users(settings):
    from app import db
    conn = db.connect(settings)
    try:
        return [User(r["id"], r["name"], r["role"]) for r in conn.execute("SELECT id, name, role FROM users ORDER BY name")]
    finally:
        conn.close()


def _read_password(from_stdin):
    if from_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    first = getpass.getpass("Password: ")
    if getpass.getpass("Password again: ") != first:
        raise UserError("the two passwords are different")
    return first


def main(argv=None):
    from app import settings as S
    p = argparse.ArgumentParser(prog="python -m app.users", description="Users of the BSG Hoarding app.")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="add a user")
    a.add_argument("name"); a.add_argument("--role", required=True, choices=None); a.add_argument("--password-stdin", action="store_true")
    sp = sub.add_parser("set-password", help="set a new password (ends that user's sessions)")
    sp.add_argument("name"); sp.add_argument("--password-stdin", action="store_true")
    sub.add_parser("list", help="list the users")
    args = p.parse_args(argv)
    try:
        s = S.load()
        if args.cmd == "list":
            for u in all_users(s):
                print(f"{u.name:<20} {u.role}")
        elif args.cmd == "add":
            if args.role not in ROLES:
                raise UserError(f"the role must be {' or '.join(ROLES)}, not {args.role!r}")
            add(s, args.name, args.role, _read_password(args.password_stdin))
            print(f"Added {args.name.lower()} ({args.role}).")
        else:
            set_password(s, args.name, _read_password(args.password_stdin))
            print(f"New password set for {args.name.lower()}; their sessions are ended.")
    except (UserError, S.ConfigError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
