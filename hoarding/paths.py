"""Where the engine finds its fonts and LibreOffice, so the same scripts run on Linux and Windows.
Fonts: $BSG_FONT_DIR, then <repo>/fonts/, then the Debian/Ubuntu DejaVu folder (the original sandbox).
LibreOffice: $SOFFICE, then soffice on the PATH, then the default Windows install folders."""
import os, shutil

HOARDING = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HOARDING)
FONT_DIRS = [d for d in (os.environ.get("BSG_FONT_DIR"), os.path.join(ROOT, "fonts"), "/usr/share/fonts/truetype/dejavu") if d]

def font(name):
    """Path of a .ttf from the first font folder that has it (the Linux path if none does, so the error names it)."""
    for d in FONT_DIRS:
        if os.path.exists(os.path.join(d, name)): return os.path.join(d, name)
    return os.path.join(FONT_DIRS[-1], name)

F, FB = font("DejaVuSans.ttf"), font("DejaVuSans-Bold.ttf")

def soffice():
    """LibreOffice binary for xlsx -> pdf."""
    for c in (os.environ.get("SOFFICE"), shutil.which("soffice"),
              r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if c and os.path.exists(c): return c
    return "soffice"
