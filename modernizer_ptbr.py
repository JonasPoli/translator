# -*- coding: utf-8 -*-
"""
modernizer_ptbr.py — utilidades para modernização e ajustes de fluência pt-BR.
(Usado indiretamente por translate.py)
"""
import re

def apply_default_rules(text: str) -> str:
    # Esta função é mantida por compatibilidade—regras principais agora estão em translate.py
    t = text
    t = re.sub(r"\bpropriedade(?:s)? hereditária(?:s)?\b", "herança de família", t, flags=re.IGNORECASE)
    t = re.sub(r"\bSenão,\b", "Do contrário,", t, flags=re.IGNORECASE)
    t = re.sub(r"\bporque é que\b", "por que", t, flags=re.IGNORECASE)
    t = re.sub(r"\bhá algo de estranho (nele|nela)\b", r"há algo de estranho \g<1>", t, flags=re.IGNORECASE)
    return t
