"""DSO Presenteren / Ruimtelijke plannen ↔ RegelRecht formalization overlap."""

__all__ = ["compare_instrument"]


def compare_instrument(*args, **kwargs):
    from .compare import compare_instrument as _ci

    return _ci(*args, **kwargs)
