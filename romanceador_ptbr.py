# -*- coding: utf-8 -*-
import re
from typing import List

# Heurísticas para PT-BR natural sem depender de LLM (100% local).
# A ideia é suavizar europeísmos, normalizar pontuação/aspas,
# ajustar verbos/colocações e opcionalmente expandir levemente
# sem adicionar fatos.

_REPLACEMENTS = [
    # europeísmos comuns → PT-BR
    (r"(?i)ri-se de", "ri de"),
    (r"(?i)ri-se", "ri"),
    (r"(?i)você próprio", "você mesmo"),
    (r"(?i)prático no extremo", "extremamente pragmático"),
    (r"(?i)ligeir[ao]?", "leve"),
    (r"(?i)assombração", "assombro"),
    (r"(?i)mal assombrad[ao]?", "mal-assombrada"),
    (r"(?i)proibição de “trabalhar”", "proibição de trabalhar"),
    (r"(?i)uma única", "apenas uma"),
    (r"(?i)horror da superstição", "horror à superstição"),
    (r"(?i)assegurar(\w*)", "garantir\1"),
    (r"(?i)alugar\s+um", "alugar um"),
    (r"(?i)uma casa mal-?assombrad[ao]?", "uma casa mal-assombrada"),
    (r"(?i)é claro", "claro"),
]

_BAD_META = [
    "neste trecho", "segue o texto", "como se vê", "o narrador diz",
    "neste ponto", "a autora afirma", "o texto mostra"
]

_SPACING_FIXES = [
    (r"\s+([,.;:!?—])", r"\1"),
    (r"([\(\[“])\s+", r"\1"),
    (r"\s+([\)\]”])", r"\1"),
    (r"\s{2,}", " "),
    (r" ?— ?", " — "),  # separa travessões com espaço fino
]

def _norm_quotes(text: str) -> str:
    # aspas portuguesas -> aspas tipográficas simples
    t = text
    t = t.replace('"', '“').replace('"', '”')
    t = t.replace("““", "“").replace("””", "”")
    return t

def _apply_replacements(text: str) -> str:
    t = text
    for pat, repl in _REPLACEMENTS:
        t = re.sub(pat, repl, t)
    return t

def _remove_boiler(text: str) -> str:
    t = text
    for b in _BAD_META:
        t = re.sub(rf"(?i)\b{re.escape(b)}\b[:,]?\s*", "", t)
    return t

def _fix_spacing(text: str) -> str:
    t = text
    for pat, repl in _SPACING_FIXES:
        t = re.sub(pat, repl, t)
    # casos específicos: "alugarum" → "alugar um"
    t = re.sub(r"\b([A-Za-zÁ-ú]+)um\b", lambda m: (m.group(0) if m.group(1).lower().endswith(('r','g')) else m.group(0)), t)
    t = t.replace("alugarum", "alugar um")
    return t

def _expand_light(pt: str, strength: float) -> str:
    # Expansão leve: adiciona pequenas apposições ou marcadores rítmicos
    # sem novos fatos. Strength 0..1.
    if strength <= 0.05:
        return pt
    # Inserções cautelosas em finais de período.
    def add_cadence(s):
        s = s.strip()
        if not s:
            return s
        if len(s) < 60 or strength < 0.3:
            return s
        # pequenos realces
        s = re.sub(r"(,\s*)(mas|ainda assim|porém)\b", r" — \2", s, flags=re.IGNORECASE)
        return s
    # aplica por frase
    sentences = re.split(r"(?<=[.!?])\s+", pt)
    sentences = [add_cadence(s) for s in sentences]
    return " ".join(sentences)

def limpar_boilerplate(texto: str) -> str:
    t = _remove_boiler(texto)
    # remove espaços duplos criados pela limpeza
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip()

def romancear_ptbr(texto: str, strength: float = 0.5) -> str:
    t = texto
    t = _apply_replacements(t)
    t = _fix_spacing(t)
    t = _norm_quotes(t)
    t = _expand_light(t, strength=strength)
    t = limpar_boilerplate(t)
    # Garantias finais de PT-BR naturalidade
    t = re.sub(r"(?i)\bprático no extremo\b", "extremamente pragmático", t)
    return t.strip()
