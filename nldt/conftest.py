"""Makes the nldt suite runnable from any working directory.

`python -m pytest nldt/tests` from the repo root failed with
``ModuleNotFoundError: No module named 'services'`` because the test imports
resolve against nldt/ itself; running from inside nldt/ worked. This conftest
is an ancestor of every collected test file, so pytest loads it for both
invocation styles.
"""

import sys
from pathlib import Path

_NLDT_ROOT = Path(__file__).resolve().parent
if str(_NLDT_ROOT) not in sys.path:
    sys.path.insert(0, str(_NLDT_ROOT))
