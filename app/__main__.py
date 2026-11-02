"""python -m app            serve the app on http://127.0.0.1:8000 (config.toml in the data folder)
python -m app --check    print the settings and the health checks, then exit (1 if a check fails)"""
import sys

from app import health, settings as S


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    try:
        s = S.load()
    except S.ConfigError as e:
        print(f"Can't start: {e}", file=sys.stderr)
        return 2
    if "--check" in argv:
        cs = health.checks(s)
        print(f"BSG Hoarding app: {s.url}")
        for c in cs:
            print(f"  {'ok  ' if c.ok else 'FAIL'}  {c.name}: {c.detail}")
        return 0 if all(c.ok for c in cs) else 1
    import uvicorn
    from app.main import create_app
    print(f"BSG Hoarding app on {s.url} (data: {s.data_dir})")
    uvicorn.run(create_app(s), host=s.host, port=s.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
