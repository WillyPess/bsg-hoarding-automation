"""The marked-up photo of a job (PLAN-app.md, Demo scope, PR B): what is accepted and how it is stored.

Accepted: a JPG or a PNG, recognised by its content (Pillow), not by its name. It is turned upright by its EXIF
orientation tag, flattened onto white when it has transparency, and stored as <P>_hoarding_markup.jpg, the file
package_gen puts on the first page of the package. Uploading again replaces it."""
import io
import warnings

from PIL import Image, ImageOps

MAX_BYTES = 25 * 1024 * 1024    # a phone photo is 2-8 MB
FORMATS = ("JPEG", "PNG")
QUALITY = 92


class PhotoError(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def markup_name(prefix):
    return f"{prefix}_hoarding_markup.jpg"


def prepare(data):
    """The upload as the JPEG to store, plus its (width, height). PhotoError when it can't be used."""
    if not data:
        raise PhotoError("The file is empty. Choose the marked-up photo (JPG or PNG).")
    if len(data) > MAX_BYTES:
        raise PhotoError(f"The file is too big ({len(data) / 1e6:.1f} MB; at most {MAX_BYTES // (1024 * 1024)} MB).", 413)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)   # a huge image is refused, not just warned about
            im = Image.open(io.BytesIO(data))
            fmt = im.format
            if fmt not in FORMATS:
                raise PhotoError(f"This is a {fmt} image: upload the marked-up photo as a JPG or PNG.")
            im.load()
    except PhotoError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise PhotoError("The image is too big (too many pixels).", 413) from None
    except Exception:   # Pillow says "cannot identify image file", or a truncated file: not a usable photo either way
        raise PhotoError("This file isn't a photo: upload the marked-up photo as a JPG or PNG.") from None
    im = ImageOps.exif_transpose(im)          # upright, as the phone showed it
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        flat = Image.new("RGB", im.size, (255, 255, 255))
        flat.paste(im, mask=im.getchannel("A"))
        im = flat
    else:
        im = im.convert("RGB")
    out = io.BytesIO()
    im.save(out, "JPEG", quality=QUALITY)     # no EXIF copied: nothing left to rotate it a second time
    return out.getvalue(), im.size
