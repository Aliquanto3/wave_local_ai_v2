"""Write the bundle the recomputation evidence exports, into a directory given.

The bundle is `tests/published_bundle_fixtures.build_bundle`: the committed
quality rows with `thinking_policy` set and each batch's interval block
computed by `score_interval.interval_block`, and one family record of both
local-vs-cloud pairs written by `comparison`. The committed files are read,
never written.

    uv run python <this file> <bundle-dir>
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "tests"))

from published_bundle_fixtures import build_bundle

if __name__ == "__main__":
    paths = build_bundle(Path(sys.argv[1]))
    print(f"--quality-rows {paths.quality_rows.as_posix()}")
    print(f"--runtime-rows {paths.runtime_rows.as_posix()}")
    print(f"--comparisons-dir {paths.comparisons_dir.as_posix()}")
    print(f"--leader-sets-dir {paths.leader_sets_dir.as_posix()}")
