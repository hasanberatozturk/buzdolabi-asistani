"""Frontend'in saf JS yardımcılarını (public/js/scale.js) Node'un yerleşik test koşucusuyla çalıştırır."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "app" / "schemas.py"
SCALE_JS = ROOT / "public" / "js" / "scale.js"

node = shutil.which("node")


@pytest.mark.skipif(node is None, reason="Node.js kurulu değil")
def test_scale_js_unit_tests_pass():
    result = subprocess.run(
        [node, "--test", "tests/js/scale.test.mjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_max_servings_matches_server_limit():
    # Arayüz ile sunucu aynı üst sınırı kullanmalı; yoksa form kabul etmediği bir değeri sunabilir.
    js_max = int(re.search(r"MAX_SERVINGS = (\d+)", SCALE_JS.read_text(encoding="utf-8")).group(1))
    server_max = int(re.search(r"servings: int \| None = Field\([^)]*le=(\d+)", SCHEMAS.read_text(encoding="utf-8")).group(1))
    assert js_max == server_max
