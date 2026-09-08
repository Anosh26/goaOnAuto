"""
Declaration Registry and Factory for GoaOnAuto.
Single Responsibility: Discovers and instantiates pluggable declaration modules.
"""
from typing import Type
from .base import BaseDeclaration
from .residence import ResidenceDeclaration
from .obc import ObcDeclaration
from .divergence import DivergenceDeclaration

DECLARATION_REGISTRY: dict[str, Type[BaseDeclaration]] = {
    "residence": ResidenceDeclaration,
    "obc": ObcDeclaration,
    "divergence": DivergenceDeclaration
}

def get_declaration(decl_type: str, target_dir: str) -> BaseDeclaration:
    """Instantiates the requested declaration module by name."""
    cls = DECLARATION_REGISTRY.get(decl_type.lower(), ResidenceDeclaration)
    return cls(target_dir)

def list_declarations() -> list[str]:
    """Returns list of registered declaration identifiers."""
    return list(DECLARATION_REGISTRY.keys())

__all__ = [
    "BaseDeclaration",
    "ResidenceDeclaration",
    "ObcDeclaration",
    "DivergenceDeclaration",
    "DECLARATION_REGISTRY",
    "get_declaration",
    "list_declarations"
]
