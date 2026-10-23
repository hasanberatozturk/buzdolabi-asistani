"""Frontend'in saf JS yardımcılarını (public/js/*.js) Node'un yerleşik test koşucusuyla çalıştırır
ve arayüzdeki sabitlerin sunucudakilerle aynı olduğunu denetler."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "app" / "schemas.py"
JS = ROOT / "public" / "js"

node = shutil.which("node")


def js_constant(file: str, name: str) -> int:
    return int(re.search(rf"{name} = (\d+)", (JS / file).read_text(encoding="utf-8")).group(1))


def py_constant(name: str) -> int:
    return int(re.search(rf"^{name} = (\d+)", SCHEMAS.read_text(encoding="utf-8"), re.M).group(1))


@pytest.mark.skipif(node is None, reason="Node.js kurulu değil")
def test_js_unit_tests_pass():
    result = subprocess.run(
        [node, "--test", "tests/js/*.test.mjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_max_servings_matches_server_limit():
    # Arayüz ile sunucu aynı üst sınırı kullanmalı; yoksa form kabul etmediği bir değeri sunabilir.
    server_max = int(re.search(r"servings: int \| None = Field\([^)]*le=(\d+)", SCHEMAS.read_text(encoding="utf-8")).group(1))
    assert js_constant("scale.js", "MAX_SERVINGS") == server_max


def test_tag_limits_match_server_limits():
    assert js_constant("tags.js", "MAX_TAGS") == py_constant("MAX_TAGS_PER_RECIPE")
    assert js_constant("tags.js", "MAX_TAG_LENGTH") == py_constant("MAX_TAG_LENGTH")