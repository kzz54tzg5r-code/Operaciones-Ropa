"""Evita que la PWA vuelva a sobrescribir el logotipo Price Shoes."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_logo_is_present_in_login_sidebar_and_report_header():
    markup = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'src="/static/price_shoes_logo.png?v=380" class="login-logo-v15"' in markup
    assert '<div class="sidebrand"><img src="/static/price_shoes_logo.png?v=380"' in markup
    assert '<div class="or-report-brand" aria-label="Price Shoes"><img src="/static/price_shoes_logo.png?v=380"' in markup
    assert (WEB / "price_shoes_logo.png").is_file()
    assert markup.count('alt="Price Shoes"') >= 3
    assert 'pwa_brand.js?v=380' in markup
    assert 'pwa_brand.css?v=380' in markup


def test_brand_script_does_not_override_with_operaciones_ropa_icon():
    code = (WEB / "pwa_brand.js").read_text(encoding="utf-8")
    assert "const brandLogo = '/static/price_shoes_logo.png?v=380'" in code
    assert "loginLogo.src = brandLogo" in code
    assert "img.src = brandLogo" in code
    assert 'src="${brandLogo}" alt="Price Shoes"' in code
    assert "app-logo.svg" not in code
    assert "app-icon-192.svg" not in code
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
    assert "operaciones-ropa-runtime-safe-update-v380" in worker
    assert "'/static/price_shoes_logo.png'" in worker


def test_pdf_already_uses_price_shoes_artwork():
    source = (ROOT / "v272_center_pdf_parity_patch.py").read_text(encoding="utf-8")
    assert 'assets" / "price_shoes_logo.png"' in source
    assert 'c.drawImage(ImageReader(str(logo))' in source
