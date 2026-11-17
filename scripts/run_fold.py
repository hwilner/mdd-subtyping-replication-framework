#!/usr/bin/env python
"""One-command single-fold LOSO benchmark runner.

Thin wrapper around ``python -m benchmark.run_loso`` with the repository's
``src/`` layout wired in, matching the other scripts in this directory:

    # Single fold on the synthetic demo (no DUA needed):
    python scripts/run_fold.py --data-root data/demo --synthetic --fold site_0

    # All folds on staged real data (post-DUA):
    python scripts/run_fold.py --data-root /path/to/rest-meta-mdd --all
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from benchmark.run_loso import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
