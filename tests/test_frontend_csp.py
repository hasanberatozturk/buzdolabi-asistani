"""vercel.json'daki CSP ile frontend'in uyumunu korur (satır içi betik/stil yok)."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"


class InlineFinder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.problems: list[str] = []
        self._in_script_without_src = False

    def handle_starttag(self, tag, attrs):
        names = {name for name, _ in attrs}
        if tag == "script" and "src" not in names:
            self.problems.append("satır içi <script>")
        if tag == "style":
            self.problems.append("<style> bloğu")
        if "style" in names:
            self.problems.append(f"style özniteliği (<{tag}>)")
        for name in names:
            if name.startswith("on"):
                self.problems.append(f"olay özniteliği {name} (<{tag}>)")
        for name, value in attrs:
            if name in ("href", "src", "action") and (value or "").strip().lower().startswith("javascript:"):
                self.problems.append(f"javascript: adresi (<{tag}>)")


def csp_header() -> dict[str, list[str]]:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    values = [
        header["value"]
        for rule in config["headers"]
        for header in rule["headers"]
        if header["key"] == "Content-Security-Policy"
    ]
    assert len(values) == 1
    return {
        parts[0]: parts[1:]
        for parts in (directive.split() for directive in values[0].split(";") if directive.strip())
    }


def test_html_pages_have_no_inline_script_style_or_event_handlers():
    for page in PUBLIC.glob("*.html"):
        finder = InlineFinder()
        finder.feed(page.read_text(encoding="utf-8"))
        assert finder.problems == [], f"{page.name}: {finder.problems}"


def test_js_does_not_set_inline_styles_via_attributes():
    # CSP style-src 'self' setAttribute("style")/style özniteliğini engeller; CSSOM (el.style.x) serbest.
    for script in (PUBLIC / "js").glob("*.js"):
        source = script.read_text(encoding="utf-8")
        assert not re.search(r"setAttribute\(\s*[\"']style[\"']", source), script.name
        assert not re.search(r"\bstyle\s*:\s*[`\"']", source), script.name
        assert "innerHTML" not in source.replace("(innerHTML yok)", ""), script.name
        assert "eval(" not in source, script.name


def test_csp_forbids_unsafe_inline_and_remote_sources():
    csp = csp_header()

    assert csp["default-src"] == ["'self'"]
    assert csp["script-src"] == ["'self'"]
    assert csp["style-src"] == ["'self'"]
    assert csp["object-src"] == ["'none'"]
    assert csp["frame-ancestors"] == ["'none'"]
    for sources in csp.values():
        assert "'unsafe-inline'" not in sources
        assert "'unsafe-eval'" not in sources
        assert "*" not in sources


def test_security_headers_are_configured_for_every_path():
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    global_rule = next(rule for rule in config["headers"] if rule["source"] == "/(.*)")
    keys = {header["key"] for header in global_rule["headers"]}

    assert {"X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"} <= keys


def test_csp_rule_does_not_apply_to_api_or_docs():
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    csp_rule = next(
        rule
        for rule in config["headers"]
        if any(header["key"] == "Content-Security-Policy" for header in rule["headers"])
    )

    for path in ("/", "/recipe.html", "/js/home.js", "/css/style.css"):
        assert re.fullmatch(csp_rule["source"], path), path
    for path in ("/api/health", "/api/recipes/1", "/docs", "/redoc", "/openapi.json"):
        assert not re.fullmatch(csp_rule["source"], path), path
