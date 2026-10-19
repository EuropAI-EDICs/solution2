"""PoC-fundament: het MiniGIM-harnas voor PoC's (agent–fase–tool matrix).

Deel van de LDT-toolbox. Dependency-regel: dit package importeert nooit
deep-agents en nooit een poc-package (spec 2026-10-18, §12).
"""

from .manifest import ManifestError, load_manifest  # noqa: F401
from .registers import TaskRegistry  # noqa: F401
from .executor import BindingExecutor  # noqa: F401
from .ops import DEFAULT_OPS  # noqa: F401
from .models import ModelRegistryError, load_model_registry, model_by_id  # noqa: F401
