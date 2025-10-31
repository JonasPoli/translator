# -*- coding: utf-8 -*-
"""
postprocess_ptbr.py — etapa adicional de pós-processamento para
ajustar traduções Argos ao estilo de PT-BR moderno desejado.

As regras abaixo foram extraídas comparando a saída literal do Argos
com a versão revisada fornecida pelo usuário. Cada entrada é aplicada
depois da tradução crua e antes das demais heurísticas (romanceador
e modernizador). 100% local, sem dependências de rede.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

_DEFAULT_MAP_PATH = Path(__file__).with_name("postprocess_map.json")


def _load_line_map(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        data: Dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    return data


_LINE_MAP = _load_line_map(_DEFAULT_MAP_PATH)


def apply_postprocess_map(text: str) -> str:
    """Aplica substituições aprendidas a partir do corpus de referência."""
    if not _LINE_MAP:
        return text

    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line in _LINE_MAP:
            lines[idx] = _LINE_MAP[line]

    return "\n".join(lines)


__all__ = ["apply_postprocess_map"]
