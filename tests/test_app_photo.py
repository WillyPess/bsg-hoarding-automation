"""Demo PR B (PLAN-app.md, Demo scope): upload the marked-up photo of a new job, minimal.

The marked-up photo only, JPG or PNG, turned upright by its EXIF tag, replaceable, and stored the way package_gen
expects it: <P>_hoarding_markup.jpg in the job folder. Run stays disabled until there is one ("Upload the marked-up
photo to run"), so the demo never shows a run that fails for a missing photo. Examples stay read-only."""
import io, json, re, sqlite3
from contextlib import closing

import pytest
from PIL import Image

import app_helpers as H
from app import engine, photos, storage
import test_app_runs as R


@pytest.fixture
def app_s(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "run_job", R.fake_engine())
    return H.make_app(tmp_path / "data")


@pytest.fixture
def gus(app_s):
    return H.logged_in(app_s[0], "gus")


@pytest.fixture
def bikini(app_s):
    storage.create_job(app_s[1], R.job("Bikini"), storage.user_id(app_s[1], "gus"))
    return app_s[1]


def image_bytes(fmt="JPEG", size=(40, 20), mode="RGB", color=(200, 30, 60), orientation=None):
    im = Image.new(mode, size, color)
    buf = io.BytesIO()
    kw = {}
    if orientation:
        exif = Image.Exif(); exif[0x0112] = orientation
        kw["exif"] = exif
    im.save(buf, fmt, **kw)
    return buf.getvalue()


def upload(client, folder, data, name="photo.jpg", ctype="image/jpeg"):
    page = client.get(f"/jobs/{folder}")
    m = re.search(r'<form method="post" action="(/jobs/[^"]+/photo)" enctype="multipart/form-data">(.*?)</form>', page.text, re.S)
    assert m, "no photo upload form on the job page"
    return client.post(m.group(1), data={"csrf_token": H.csrf_from(m.group(2))}, files={"photo": (name, data, ctype)},
                       follow_redirects=False)


def stored(s, folder="Bikini"):
    return s.data_dir / "jobs" / folder / f"{folder}_hoarding_markup.jpg"


def audit(s, action):
    with closing(sqlite3.connect(s.data_dir / "bsg.sqlite")) as c:
        return c.execute("SELECT u.name, a.detail FROM audit a LEFT JOIN users u ON u.id = a.user_id WHERE a.action = ? ORDER BY a.id",
                         (action,)).fetchall()


# --- the Run button waits for the photo -------------------------------------------------------------------------------

def test_run_is_disabled_until_the_photo_is_there(bikini, gus):
    html = gus.get("/jobs/Bikini").text
    assert "Upload the marked-up photo to run" in html
    assert re.search(r'<button type="submit" disabled[^>]*>Generate PDFs</button>', html)


def test_run_without_the_photo_is_refused_on_the_server_too(bikini, gus):
    html = gus.get("/jobs/Bikini").text
    r = gus.post("/jobs/Bikini/run", data={"csrf_token": H.csrf_from(html)}, follow_redirects=False)
    assert r.status_code == 409 and "Upload the marked-up photo to run" in r.text
    assert not list((bikini.data_dir / "jobs" / "Bikini" / "runs").glob("0*"))     # no run folder: no failed run to show


def test_upload_then_run(bikini, gus):
    r = upload(gus, "Bikini", image_bytes())
    assert r.status_code == 303 and r.headers["location"] == "/jobs/Bikini"
    html = gus.get("/jobs/Bikini").text
    assert "Upload the marked-up photo to run" not in html
    assert re.search(r'<button type="submit">Generate PDFs</button>', html)
    run = R.press_run(gus, "/jobs/Bikini")
    page = R.finished(gus, run.headers["location"])
    assert 'data-status="done"' in page.text
    copy = bikini.data_dir / "jobs" / "Bikini" / "runs" / "0001" / "Bikini_hoarding_markup.jpg"
    assert copy.read_bytes() == stored(bikini).read_bytes()                     # the run has its own copy of the photo


# --- what is stored ---------------------------------------------------------------------------------------------------

def test_jpg_is_stored_as_package_gen_expects(bikini, gus):
    upload(gus, "Bikini", image_bytes())
    with Image.open(stored(bikini)) as im:
        assert (im.format, im.mode, im.size) == ("JPEG", "RGB", (40, 20))


def test_png_is_stored_as_a_jpg(bikini, gus):
    r = upload(gus, "Bikini", image_bytes("PNG", mode="RGBA", color=(0, 0, 0, 0)), "markup.png", "image/png")
    assert r.status_code == 303
    with Image.open(stored(bikini)) as im:
        assert (im.format, im.mode) == ("JPEG", "RGB")
        assert im.getpixel((5, 5))[0] > 240                                      # transparent becomes white, not black
    assert not list((bikini.data_dir / "jobs" / "Bikini").glob("*.png"))


@pytest.mark.parametrize("orientation, size", [(1, (40, 20)), (3, (40, 20)), (6, (20, 40)), (8, (20, 40))])
def test_exif_rotation_is_applied(bikini, gus, orientation, size):
    upload(gus, "Bikini", image_bytes(orientation=orientation))
    with Image.open(stored(bikini)) as im:
        assert im.size == size
        assert im.getexif().get(0x0112) in (None, 1)                             # upright now: no rotation left to apply


def test_replace(bikini, gus):
    upload(gus, "Bikini", image_bytes(color=(200, 30, 60)))
    first = stored(bikini).read_bytes()
    r = upload(gus, "Bikini", image_bytes(color=(30, 60, 200)))
    assert r.status_code == 303 and stored(bikini).read_bytes() != first
    rows = audit(bikini, "photo.uploaded")
    assert [json.loads(d)["replaced"] for _, d in rows] == [False, True]
    assert {who for who, _ in rows} == {"gus"}


def test_the_job_page_shows_the_photo(bikini, gus):
    upload(gus, "Bikini", image_bytes())
    html = gus.get("/jobs/Bikini").text
    assert '<img class="photo" src="/jobs/Bikini/photo' in html
    r = gus.get("/jobs/Bikini/photo")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg" and r.content == stored(bikini).read_bytes()


def test_no_photo_yet(bikini, gus):
    assert gus.get("/jobs/Bikini/photo").status_code == 404


# --- refused ----------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("data, name, words", [
    (b"not an image at all", "photo.jpg", "JPG or PNG"),          # the name says .jpg, the content doesn't
    (None, "photo.gif", "JPG or PNG"),                             # a real image, but GIF
    (b"", "photo.jpg", "empty"),
])
def test_refused_files_change_nothing(bikini, gus, data, name, words):
    if data is None:
        data = image_bytes("GIF", mode="P")
    r = upload(gus, "Bikini", data, name)
    assert r.status_code == 422 and words in r.text
    assert not stored(bikini).exists() and not audit(bikini, "photo.uploaded")


def test_a_refused_file_keeps_the_previous_photo(bikini, gus):
    upload(gus, "Bikini", image_bytes())
    before = stored(bikini).read_bytes()
    assert upload(gus, "Bikini", b"junk").status_code == 422
    assert stored(bikini).read_bytes() == before


def test_too_big(bikini, gus, monkeypatch):
    monkeypatch.setattr(photos, "MAX_BYTES", 1000)
    r = upload(gus, "Bikini", image_bytes(size=(400, 400)) + b"\0" * 2000)
    assert r.status_code == 413 and "too big" in r.text.lower()
    assert not stored(bikini).exists()


def test_no_file_chosen(bikini, gus):
    page = gus.get("/jobs/Bikini")
    r = gus.post("/jobs/Bikini/photo", data={"csrf_token": H.csrf_from(page.text)}, follow_redirects=False)
    assert r.status_code == 422 and "Choose" in r.text


# --- Examples stay read-only ------------------------------------------------------------------------------------------

def test_examples_have_no_photo_upload(gus):
    html = gus.get("/examples/Bikini").text
    assert 'enctype="multipart/form-data"' not in html
    assert "Upload the marked-up photo" not in html                              # their photo is there: Run works
    assert re.search(r'<button type="submit">Generate PDFs</button>', html)
    for path in ("/examples/Bikini/photo", "/jobs/example-Bikini/photo"):
        r = gus.post(path, data={}, files={"photo": ("p.jpg", image_bytes(), "image/jpeg")})
        assert r.status_code in (403, 404, 405), path


def test_hoarding_is_never_written(gus):
    from pathlib import Path
    before = (Path(H.ROOT) / "hoarding" / "Bikini" / "Bikini_hoarding_markup.jpg").read_bytes()
    gus.post("/examples/Bikini/photo", data={}, files={"photo": ("p.jpg", image_bytes(), "image/jpeg")})
    assert (Path(H.ROOT) / "hoarding" / "Bikini" / "Bikini_hoarding_markup.jpg").read_bytes() == before
