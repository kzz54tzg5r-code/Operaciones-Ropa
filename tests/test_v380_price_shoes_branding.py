"""V395: Price Shoes en acceso, navegación, app instalada y reportes."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_logo_is_present_in_login_sidebar_and_report_header():
    markup = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'src="/static/price_shoes_logo.png?v=395" class="login-logo-v15"' in markup
    assert '<div class="sidebrand"><img src="/static/price_shoes_logo.png?v=395"' in markup
    assert '<div class="or-report-brand" aria-label="Price Shoes"><img src="/static/price_shoes_logo.png?v=395"' in markup
    assert (WEB / "price_shoes_logo.png").is_file()
    assert markup.count('alt="Price Shoes"') >= 3
    assert 'pwa_brand.js?v=395' in markup
    assert 'pwa_brand.css?v=395' in markup


def test_brand_script_does_not_override_with_operaciones_ropa_icon():
    code = (WEB / "pwa_brand.js").read_text(encoding="utf-8")
    assert "const brandLogo = '/static/price_shoes_logo.png?v=395'" in code
    assert "img.getAttribute('src') !== brandLogo" in code
    assert "img.src = brandLogo" in code
    assert 'src="${brandLogo}" alt="Price Shoes"' in code
    assert "app-logo.svg" not in code
    assert "const iconFallback = '/static/app-icon-192.svg?v=395'" in code
    result = subprocess.run(["node", "--check", "--input-type=commonjs"],
                            input=code, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_report_logo_is_visible_even_with_compact_navigation():
    css = (WEB / "pwa_brand.css").read_text(encoding="utf-8")
    assert ".or-report-brand" in css
    assert "background:#fff!important" in css
    assert "object-fit:contain!important" in css
    assert "html body #appView #sidebar .sidebrand img" in css
    assert ".login-logo-v15{display:block!important" in css


def test_pwa_invalidates_old_logo_cache():
    worker = (WEB / "service-worker.js").read_text(encoding="utf-8")
    assert "operaciones-ropa-runtime-safe-update-v395" in worker
    assert "'/static/price_shoes_logo.png?v=395'" in worker


def test_pdf_already_uses_price_shoes_artwork():
    source = (ROOT / "v272_center_pdf_parity_patch.py").read_text(encoding="utf-8")
    assert 'assets" / "price_shoes_logo.png"' in source
    assert 'c.drawImage(ImageReader(str(logo))' in source


def test_pwa_icon_is_real_price_shoes_logo_and_old_caches_are_busted():
    import xml.etree.ElementTree as ET
    for name in ("app-icon-192.svg", "app-icon-512.svg", "app-icon-maskable.svg"):
        data = (WEB / name).read_text(encoding="utf-8")
        assert "data:image/png;base64," in data
        assert 'aria-label="Price Shoes"' in data
        assert "OPERACIONES</text>" not in data
        assert ET.fromstring(data).tag.endswith("svg")
    manifest = (WEB / "manifest.webmanifest").read_text(encoding="utf-8")
    assert "/static/app-icon-192.svg?v=395" in manifest
    assert "/static/app-icon-maskable.svg?v=395" in manifest
    markup = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'href="/static/app-icon-192.svg?v=395"' in markup
    assert "fetchpriority=\"high\"" in markup


def test_stable_login_and_brand_guards_are_present():
    source = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "pwa_brand.css").read_text(encoding="utf-8")
    js = (WEB / "pwa_brand.js").read_text(encoding="utf-8")
    sw = (WEB / "service-worker.js").read_text(encoding="utf-8")
    assert "for(let attempt=0;attempt<3;attempt++)" in source
    assert "Reconectando con el servidor" in source
    assert "width:min(440px,100%)!important" in css
    assert "aspect-ratio:211/121!important" in css
    assert "MutationObserver(mutations" in js
    assert "window.setTimeout(hideSplash, 2200)" in js
    assert "ignoreSearch: !isBrand" in sw
    for filename in ("pwa_brand.js", "service-worker.js"):
        code = (WEB / filename).read_text(encoding="utf-8")
        result = subprocess.run(["node", "--check"], input=code, text=True, capture_output=True)
        assert result.returncode == 0, f"{filename}: {result.stderr}"
