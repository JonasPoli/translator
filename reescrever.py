#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reescrever.py — reescrita romanceada e modernizada a partir de um arquivo Markdown.

Pipeline:
1) Divide o arquivo de entrada em seções (nível ##) e gera arquivos temporários por seção.
2) Reescreve cada trecho, expandindo a prosa com vocabulário contemporâneo sem alterar fatos.
3) Normaliza abreviações, siglas e algarismos romanos para formas por extenso.
4) Gera um novo arquivo Markdown contendo as seções reescritas em sequência.

Uso básico (exemplo do projeto atual):
    ./reescrever.py --in Reescrever/original.md --out Reescrever/gerado.md
"""

import argparse
import json
import os
import random
import re
import shutil
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from tqdm import tqdm

try:
    from romanceador_ptbr import romancear_ptbr as romancear_base
except ImportError:
    def romancear_base(texto: str, strength: float = 0.45) -> str:
        return texto

try:
    from gpt4all import GPT4All
    GPT4ALL_AVAILABLE = True
except Exception:
    GPT4ALL_AVAILABLE = False
    GPT4All = None  # type: ignore

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False
    OpenAI = None  # type: ignore


ABBREVIATION_MAP: Sequence[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bSr\.\b", flags=re.IGNORECASE), "Senhor"),
    (re.compile(r"\bSra\.\b", flags=re.IGNORECASE), "Senhora"),
    (re.compile(r"\bSrta\.\b", flags=re.IGNORECASE), "Senhorita"),
    (re.compile(r"\bDr\.\b", flags=re.IGNORECASE), "Doutor"),
    (re.compile(r"\bDra\.\b", flags=re.IGNORECASE), "Doutora"),
    (re.compile(r"\bProf\.\b", flags=re.IGNORECASE), "Professor"),
    (re.compile(r"\bProfa\.\b", flags=re.IGNORECASE), "Professora"),
    (re.compile(r"\bCap\.\b", flags=re.IGNORECASE), "Capitão"),
    (re.compile(r"\bGov\.\b", flags=re.IGNORECASE), "Governador"),
    (re.compile(r"\bRev\.\b", flags=re.IGNORECASE), "Reverendo"),
    (re.compile(r"\betc\.\b", flags=re.IGNORECASE), "etcetera"),
]

ARCHAIC_MAP: Sequence[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bassociação\b", flags=re.IGNORECASE), "parceria"),
    (re.compile(r"\basseverava\b", flags=re.IGNORECASE), "afirmava"),
    (re.compile(r"\bcomadres\b", flags=re.IGNORECASE), "moradoras"),
    (re.compile(r"\bproferia\b", flags=re.IGNORECASE), "dizia"),
    (re.compile(r"\bperorar\b", flags=re.IGNORECASE), "discursar"),
    (re.compile(r"\bdócil\b", flags=re.IGNORECASE), "manso"),
    (re.compile(r"\bsubalterno\b", flags=re.IGNORECASE), "obediente"),
    (re.compile(r"\bdeserção\b", flags=re.IGNORECASE), "abandono"),
    (re.compile(r"\bde-certo\b", flags=re.IGNORECASE), "com certeza"),
    (re.compile(r"\bprodigioso\b", flags=re.IGNORECASE), "impressionante"),
    (re.compile(r"\bterrível\b", flags=re.IGNORECASE), "intenso"),
    (re.compile(r"\bgalhardia\b", flags=re.IGNORECASE), "valentia"),
    (re.compile(r"\bcom efeito\b", flags=re.IGNORECASE), "de fato"),
    (re.compile(r"\bporventura\b", flags=re.IGNORECASE), "talvez"),
    (re.compile(r"\bperguntou-lhe\b", flags=re.IGNORECASE), "perguntou a ele"),
    (re.compile(r"\bnão obstante\b", flags=re.IGNORECASE), "mesmo assim"),
    (re.compile(r"\bbeleza\b", flags=re.IGNORECASE), "beleza"),
]

SIGLA_LETTERS: Dict[str, str] = {
    "A": "á",
    "B": "bê",
    "C": "cê",
    "D": "dê",
    "E": "é",
    "F": "efe",
    "G": "gê",
    "H": "agá",
    "I": "í",
    "J": "jota",
    "K": "cá",
    "L": "ele",
    "M": "eme",
    "N": "ene",
    "O": "ó",
    "P": "pê",
    "Q": "quê",
    "R": "erre",
    "S": "esse",
    "T": "tê",
    "U": "ú",
    "V": "vê",
    "W": "dáblio",
    "X": "xis",
    "Y": "ípsilon",
    "Z": "zê",
}

ABSTRACT_MOODS = [
    "expectativa serena",
    "tensão discreta",
    "lembranças vivas",
    "esperança resiliente",
    "melancolia contida",
    "ansiedade íntima",
    "curiosidade pulsante",
    "resistência silenciosa",
    "afeto velado",
]

MOOD_EXPANSIONS = [
    "{subject} preserva {mood}, e cada detalhe revive a cena de forma palpável.",
    "Há {mood} pairando no ar, como se {subject} permanecesse diante de nós.",
    "Os sentimentos se espalham em {mood}, sem alterar o curso real dos acontecimentos.",
    "{subject} segue banhado em {mood}, trazendo texturas novas para o mesmo enredo.",
    "Percebe-se {mood}, o que faz {subject} revelar nuances silenciosas.",
    "Todo o ambiente respira {mood}, lembrando que estamos encarando fatos verdadeiros.",
    "{subject} continua envolvido por {mood}, mantendo viva a experiência narrada.",
    "O clima fica impregnado de {mood}, reforçando o que realmente aconteceu ali.",
]

SYNONYM_REPLACEMENTS: Sequence[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bNão há\b", flags=re.IGNORECASE), "Não existe"),
    (re.compile(r"\bno sentido absoluto\b", flags=re.IGNORECASE), "em sentido pleno"),
    (re.compile(r"\bdevemos dizer\b", flags=re.IGNORECASE), "vale lembrar"),
    (re.compile(r"\bfoi útil\b", flags=re.IGNORECASE), "teve utilidade"),
    (re.compile(r"\bfenômeno\b", flags=re.IGNORECASE), "movimento"),
    (re.compile(r"\bestudar\b", flags=re.IGNORECASE), "investigar"),
    (re.compile(r"\bverdadeiro título\b", flags=re.IGNORECASE), "título mais honesto"),
    (re.compile(r"\bpoderá ser\b", flags=re.IGNORECASE), "talvez se torne"),
    (re.compile(r"\bprecederão\b", flags=re.IGNORECASE), "virão antes de"),
    (re.compile(r"\bhereditária\b", flags=re.IGNORECASE), "passada de geração em geração"),
    (re.compile(r"\bamável\b", flags=re.IGNORECASE), "acolhedor"),
    (re.compile(r"\bagradável\b", flags=re.IGNORECASE), "cativante"),
    (re.compile(r"\bnecessidade\b", flags=re.IGNORECASE), "anseio"),
    (re.compile(r"\bcuriosos\b", flags=re.IGNORECASE), "observadores"),
    (re.compile(r"\bcarroça\b", flags=re.IGNORECASE), "carroção"),
    (re.compile(r"\bassistência\b", flags=re.IGNORECASE), "plateia"),
    (re.compile(r"\bpretensão\b", flags=re.IGNORECASE), "impulso"),
]

STRUCTURE_REPLACEMENTS: Sequence[Tuple[re.Pattern, str]] = [
    (re.compile(r"^Da ([^,]+),\s*(.+)", flags=re.IGNORECASE), r"Em \1, \2"),
    (re.compile(r"^Do ([^,]+),\s*(.+)", flags=re.IGNORECASE), r"Em \1, \2"),
    (re.compile(r"^De ([^,]+),\s*(.+)", flags=re.IGNORECASE), r"Em \1, \2"),
    (re.compile(r"^No ([^,]+),\s*(.+)", flags=re.IGNORECASE), r"Dentro de \1, \2"),
]

STOPWORDS_CAPS = {
    "A", "O", "E", "Os", "As", "Um", "Uma", "Da", "Do", "Dos", "Das", "De",
    "Na", "No", "Nas", "Nos", "Para", "Por", "Com", "Sem", "Ao", "À", "Que",
    "Se", "Quando", "Enquanto", "Assim", "Essa", "Esse", "Este", "Esta",
    "Isso", "Isto", "Aquilo", "Aqui", "Ali", "Lá", "Tudo", "Todos", "Cada",
    "Nosso", "Nossa", "Seu", "Sua", "Como", "Onde", "Porque", "Porquê",
    "Não", "Nem", "Pois", "Também", "Portanto", "Logo", "Todavia", "Entretanto",
    "Nesta", "Neste", "Nesse", "Nessa", "Dessa", "Desse", "Deste", "Desta",
    "Essa", "Esse", "Aquilo", "Daquela", "Daquele", "Quem", "Então", "Assim",
    "Ainda", "Agora", "Aqui", "Ali", "Lá",
}

DIALOGUE_TEMPLATES = [
    "{speaker} disse com franqueza: \"{line}\"",
    "{speaker} respondeu em voz firme: \"{line}\"",
    "{speaker} confidenciou sem rodeios: \"{line}\"",
    "{speaker} afirmou com serenidade: \"{line}\"",
]

PARAGRAPH_CLOSERS = [
    "O parágrafo repousa impregnado de {mood}, respeitando o curso exato dos acontecimentos.",
    "As últimas linhas conservam {mood}, mantendo a narrativa fiel e mais presente.",
    "Fecha-se com {mood}, como se a mesma história ganhasse fôlego no agora.",
    "Percebe-se {mood} ao final, destacando a verdade dos fatos com nova cadência.",
    "O desfecho sustenta {mood}, preservando cada detalhe enquanto amplia a vivência.",
]

DEFAULT_SUBJECTS = [
    "o momento",
    "o ambiente",
    "a cena narrada",
    "a memória presente",
]

ADDITIONAL_SENTENCES = [
    "O ambiente permanecia tingido por {mood}, sem alterar um detalhe do que já havia acontecido.",
    "O silêncio ao redor guardava {mood}, reforçando cada gesto que acabara de ocorrer.",
    "A lembrança daquele instante se alongava em {mood}, dando corpo às sensações que já existiam.",
    "Tudo à volta parecia conservar {mood}, como se o tempo estivesse atento aos mesmos fatos.",
    "Respirava-se {mood} em cada pausa, insistindo para que a cena permanecesse viva.",
]

ALLOWED_EXTRA_WORDS = {
    "sensação",
    "sensações",
    "atmosfera",
    "atmosferas",
    "tom",
    "tons",
    "clima",
    "climas",
    "ritmo",
    "ritmos",
    "cadência",
    "cadências",
    "presença",
    "presenças",
    "memória",
    "memórias",
    "eco",
    "ecos",
    "pulso",
    "pulsa",
    "pulsava",
    "respira",
    "respirava",
    "respirando",
    "respirar",
    "vibração",
    "vibrações",
    "textura",
    "texturas",
    "palpável",
    "palpáveis",
    "intensidade",
    "intensidades",
    "sutil",
    "sutis",
    "delicado",
    "delicada",
    "delicadas",
    "profundo",
    "profunda",
    "profundas",
    "profundidade",
    "profundidades",
    "silêncio",
    "silêncios",
    "silencioso",
    "silenciosa",
    "calma",
    "calmaria",
    "calmas",
    "brisa",
    "brisas",
    "tensão",
    "tensões",
    "afeto",
    "afetos",
    "tradição",
    "tradições",
    "história",
    "histórias",
    "tempo",
    "tempos",
    "presente",
    "grandiosidade",
    "grandeza",
    "contorno",
    "contornos",
    "paisagem",
    "paisagens",
    "cenário",
    "cenários",
    "cena",
    "cenas",
    "aurora",
    "brilho",
    "brilhos",
    "luz",
    "luzes",
    "calor",
    "frio",
    "fria",
    "sopro",
    "suave",
    "energia",
    "energias",
    "alma",
    "almas",
    "marca",
    "marcas",
    "perfume",
    "perfumes",
    "batida",
    "batidas",
    "compasso",
    "compassos",
    "metáfora",
    "metáforas",
}

LLM_SYSTEM_PROMPT = (
    "Você é um escritor brasileiro contemporâneo. Reescreva qualquer parágrafo mantendo os fatos, "
    "respeitando a ordem dos acontecimentos e ampliando sensações e atmosferas com linguagem atual."
)

LLM_USER_TEMPLATE = (
    "Texto original:\n{original}\n\n"
    "Reescreva o texto acima em português brasileiro atual, mantendo exatamente os mesmos fatos e a mesma ordem, "
    "mas expandindo descrições sensoriais e emoções. Substitua abreviações por extenso e deixe claro quem fala, "
    "caso haja diálogos. Responda somente com o texto reescrito."
)

LLM_MODEL_CACHE: Dict[str, GPT4All] = {}


def _apply_word_swaps(text: str) -> str:
    replacements = {
        "é": "continua sendo",
        "era": "era de fato",
        "foi": "acabou sendo",
        "tinha": "possuía",
        "têm": "possuem",
        "tem": "carrega",
        "disse": "comentou",
        "perguntou": "indagou",
        "respondeu": "replicou",
        "falou": "afirmou",
    }

    def repl(match: re.Match) -> str:
        word = match.group(0)
        base = word.lower()
        replacement = replacements.get(base)
        if not replacement:
            return word
        if word.isupper():
            return replacement.upper()
        if word[0].isupper():
            return replacement.capitalize()
        return replacement

    pattern = re.compile(r"\b(é|era|foi|tinha|têm|tem|disse|perguntou|respondeu|falou)\b", flags=re.IGNORECASE)
    return pattern.sub(repl, text)


def load_llm_model(model_path: Path) -> Optional[GPT4All]:
    if not GPT4ALL_AVAILABLE:
        return None
    model_path = model_path.expanduser().resolve()
    if not model_path.exists():
        raise FileNotFoundError(f"Modelo LLM não encontrado: {model_path}")
    key = str(model_path)
    model = LLM_MODEL_CACHE.get(key)
    if model is None:
        n_threads = max(os.cpu_count() or 4, 4)
        model = GPT4All(
            model_name=model_path.name,
            model_path=str(model_path.parent),
            allow_download=False,
            n_threads=n_threads,
        )
        LLM_MODEL_CACHE[key] = model
    return model


def load_openai_client(config_path: Path) -> Any:
    if not OPENAI_AVAILABLE:
        raise RuntimeError("Biblioteca openai não instalada. Instale com `pip install openai`.")

    cfg_path = config_path.expanduser().resolve()
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração OpenAI não encontrado: {cfg_path}. "
            "Crie um JSON com {'api_key': 'sua_chave', 'base_url': 'opcional'}."
        )
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Configuração OpenAI inválida ({exc})") from exc

    api_key = data.get("api_key") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("API key da OpenAI não encontrada no arquivo nem em OPENAI_API_KEY.")
    base_url = data.get("base_url")
    client_kwargs: Dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    return OpenAI(**client_kwargs)


def clean_llm_output(text: str) -> str:
    t = text.strip()
    t = re.sub(r"(?i)^texto(?: reescrito)?[:\-]?\s*", "", t)
    t = re.sub(r"(?i)^trecho reescrito[:\-]?\s*", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def split_for_llm(paragraph: str, max_chars: int = 480) -> List[str]:
    paragraph = paragraph.strip()
    if len(paragraph) <= max_chars:
        return [paragraph]
    sentences = re.split(r"(?<=[.!?…])\s+", paragraph)
    chunks: List[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        while len(sentence) > max_chars:
            chunks.append(sentence[:max_chars].strip())
            sentence = sentence[max_chars:].strip()
        if not sentence:
            continue
        if not current:
            current = sentence
            continue
        candidate = f"{current} {sentence}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current.strip())
            current = sentence
    if current:
        chunks.append(current.strip())
    return chunks


def extract_openai_content(response: Any) -> str:
    if hasattr(response, "choices") and response.choices:
        message = response.choices[0].message
        content = getattr(message, "content", "")
        if isinstance(content, list):
            return "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        return content or ""
    return ""


def rewrite_section_openai(section_text: str, client: Any, model_name: str) -> str:
    original = section_text.strip()
    if not original:
        return ""

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", original) if p.strip()]
    if not paragraphs:
        return ""

    rewritten_paragraphs: List[str] = []
    for paragraph in paragraphs:
        subchunks = split_for_llm(paragraph)
        rewritten_subchunks: List[str] = []
        success = True
        for subchunk in subchunks:
            cleaned_candidate = ""
            for temp in (0.7, 0.85, 0.6):
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": LLM_SYSTEM_PROMPT},
                            {"role": "user", "content": LLM_USER_TEMPLATE.format(original=subchunk)},
                        ],
                        temperature=temp,
                        top_p=0.9,
                        max_tokens=600,
                    )
                except Exception:
                    cleaned_candidate = ""
                    continue
                cleaned = clean_llm_output(extract_openai_content(response))
                cleaned = expand_abbreviations(cleaned)
                cleaned = replace_roman_numerals(cleaned)
                cleaned = expand_siglas(cleaned)
                cleaned = expand_archaic(cleaned)
                cleaned = re.sub(r"\s{2,}", " ", cleaned)
                cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
                if validate_rewrite(subchunk, cleaned):
                    cleaned_candidate = cleaned
                    break
            if not cleaned_candidate:
                success = False
                break
            rewritten_subchunks.append(cleaned_candidate)
        if not success:
            return ""
        rewritten_paragraphs.append("\n\n".join(rewritten_subchunks))
    return "\n\n".join(rewritten_paragraphs)


def validate_rewrite(original: str, rewritten: str) -> bool:
    if not rewritten.strip():
        return False

    new_word_count = len(rewritten.split())
    original_word_count = max(len(original.split()), 1)
    if new_word_count < original_word_count * 1.15:
        return False

    lower = rewritten.lower()
    for banned in ("exemplo", "teste", "nota", "avaliação"):
        if banned in lower:
            return False

    orig_words = {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ'-]+", original)}
    new_words = {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ'-]+", rewritten)}
    extra_words = new_words - orig_words
    if extra_words - ALLOWED_EXTRA_WORDS:
        return False

    orig_names = {name.lower() for name in collect_names(original)}
    new_names = {name.lower() for name in collect_names(rewritten)}

    for name in orig_names:
        if name and name not in new_names:
            return False

    if new_names - orig_names:
        return False

    return True


def normalize_sentence_case(text: str) -> str:
    parts = re.split(r"(?<=[.!?…])\s+", text.strip())
    normalized_parts: List[str] = []
    for part in parts:
        if not part:
            continue
        stripped = part.lstrip()
        prefix = part[: len(part) - len(stripped)]
        if stripped and stripped[0].islower():
            stripped = stripped[0].upper() + stripped[1:]
        normalized_parts.append(prefix + stripped)
    return " ".join(normalized_parts)


def rewrite_section_llm(section_text: str, model: GPT4All) -> str:
    original = section_text.strip()
    if not original:
        return ""

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", original) if p.strip()]
    if not paragraphs:
        return ""

    rewritten_paragraphs: List[str] = []

    for paragraph in paragraphs:
        subchunks = split_for_llm(paragraph)
        rewritten_subchunks: List[str] = []
        success = True
        for subchunk in subchunks:
            cleaned_candidate = ""
            for temp in (0.8, 0.9, 0.7):
                with model.chat_session(system_prompt=LLM_SYSTEM_PROMPT):
                    response = model.generate(
                        LLM_USER_TEMPLATE.format(original=subchunk),
                        temp=temp,
                        top_p=0.9,
                        max_tokens=512,
                    )
                cleaned = clean_llm_output(response)
                cleaned = expand_abbreviations(cleaned)
                cleaned = replace_roman_numerals(cleaned)
                cleaned = expand_siglas(cleaned)
                cleaned = expand_archaic(cleaned)
                cleaned = re.sub(r"\s{2,}", " ", cleaned)
                cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
                if validate_rewrite(subchunk, cleaned):
                    cleaned_candidate = cleaned
                    break
            if not cleaned_candidate:
                success = False
                break
            rewritten_subchunks.append(cleaned_candidate)

        if not success:
            return ""

        rewritten_paragraphs.append("\n\n".join(rewritten_subchunks))

    return "\n\n".join(rewritten_paragraphs)


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join([c for c in normalized if not unicodedata.combining(c)])
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized)
    normalized = normalized.strip("-").lower()
    return normalized or "secao"


def split_markdown_sections(text: str) -> List[Tuple[str, str]]:
    sections: List[Tuple[str, str]] = []
    current_title: Optional[str] = None
    current_lines: List[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[3:].strip()
            current_lines = []
        else:
            if current_title is None:
                continue
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return sections


def roman_to_int(roman: str) -> Optional[int]:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    roman = roman.upper()
    for ch in reversed(roman):
        if ch not in values:
            return None
        val = values[ch]
        if val < prev:
            total -= val
        else:
            total += val
            prev = val
    return total


def int_to_pt_words(num: int) -> str:
    if num <= 0:
        return str(num)

    unidades = {
        0: "zero",
        1: "um",
        2: "dois",
        3: "três",
        4: "quatro",
        5: "cinco",
        6: "seis",
        7: "sete",
        8: "oito",
        9: "nove",
        10: "dez",
        11: "onze",
        12: "doze",
        13: "treze",
        14: "catorze",
        15: "quinze",
        16: "dezesseis",
        17: "dezessete",
        18: "dezoito",
        19: "dezenove",
    }
    dezenas = {
        20: "vinte",
        30: "trinta",
        40: "quarenta",
        50: "cinquenta",
        60: "sessenta",
        70: "setenta",
        80: "oitenta",
        90: "noventa",
    }
    centenas = {
        100: "cem",
        200: "duzentos",
        300: "trezentos",
        400: "quatrocentos",
        500: "quinhentos",
        600: "seiscentos",
        700: "setecentos",
        800: "oitocentos",
        900: "novecentos",
    }

    if num < 20:
        return unidades[num]
    if num < 100:
        dezena = num // 10 * 10
        resto = num % 10
        if resto == 0:
            return dezenas[dezena]
        return f"{dezenas[dezena]} e {unidades[resto]}"
    if num < 1000:
        centena = num // 100 * 100
        resto = num % 100
        if num == 100:
            return "cem"
        if resto == 0:
            return centenas[centena]
        return f"{centenas[centena]} e {int_to_pt_words(resto)}"
    if num < 1000000:
        milhares = num // 1000
        resto = num % 1000
        prefixo = "mil" if milhares == 1 else f"{int_to_pt_words(milhares)} mil"
        if resto == 0:
            return prefixo
        return f"{prefixo} {int_to_pt_words(resto)}"
    return str(num)


def replace_roman_numerals(text: str) -> str:
    pattern = re.compile(r"\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)\s+([IVXLCDM]+)\b")

    def repl(match: re.Match) -> str:
        name = match.group(1)
        roman = match.group(2)
        value = roman_to_int(roman)
        if value is None:
            return match.group(0)
        return f"{name} {int_to_pt_words(value)}"

    text = pattern.sub(repl, text)

    loose_pattern = re.compile(r"\b([IVXLCDM]+)\b")

    def repl_loose(match: re.Match) -> str:
        roman = match.group(1)
        value = roman_to_int(roman)
        if value is None:
            return match.group(0)
        return int_to_pt_words(value)

    return loose_pattern.sub(repl_loose, text)


def expand_abbreviations(text: str) -> str:
    t = text
    for pattern, repl in ABBREVIATION_MAP:
        t = pattern.sub(repl, t)
    return t


def expand_archaic(text: str) -> str:
    t = text
    for pattern, repl in ARCHAIC_MAP:
        t = pattern.sub(repl, t)
    return t


def expand_siglas(text: str) -> str:
    sigla_pattern = re.compile(r"\b([A-Z]{2,})\b")

    def repl(match: re.Match) -> str:
        word = match.group(1)
        if roman_to_int(word) is not None:
            return match.group(0)
        letters = [SIGLA_LETTERS.get(ch, ch.lower()) for ch in word]
        return " ".join(letters)

    return sigla_pattern.sub(repl, text)


def split_sentences(paragraph: str) -> List[str]:
    raw = re.split(r"(?<=[.!?])\s+", paragraph.strip())
    return [s.strip() for s in raw if s.strip()]


def collect_names(text: str) -> List[str]:
    candidates = re.findall(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç'-]+\b", text)
    filtered = [c for c in candidates if c not in STOPWORDS_CAPS and len(c) > 1]
    return filtered


def extract_known_names(text: str) -> Set[str]:
    tokens = re.findall(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç'-]+\b", text)
    filtered = [t for t in tokens if t not in STOPWORDS_CAPS and len(t) > 1]
    counts = Counter(filtered)
    return {token for token, freq in counts.items() if freq >= 2}


def rewrite_dialogue(sentence: str, last_name: Optional[str]) -> str:
    cleaned = sentence.strip()
    if cleaned.startswith(("—", "–")):
        cleaned = cleaned[1:].strip()
    if "—" in cleaned:
        spoken = cleaned.split("—", 1)[0].strip()
    else:
        spoken = cleaned
    spoken = re.split(r"\s*,\s*(?:disse|falou|perguntou|replicou|comentou)\b", spoken, 1)[0]
    spoken = spoken.replace("“", "").replace("”", "")
    spoken = spoken.strip(".,;:—– ")
    if spoken and spoken[-1] not in ".!?":
        spoken = f"{spoken}."
    speaker = last_name or "O narrador"
    template = random.choice(DIALOGUE_TEMPLATES)
    return template.format(speaker=speaker, line=spoken)


def paraphrase_sentence(sentence: str) -> str:
    t = sentence.strip()
    for pattern, repl in STRUCTURE_REPLACEMENTS:
        new_t = pattern.sub(repl, t)
        if new_t != t:
            t = new_t
            break
    for pattern, repl in SYNONYM_REPLACEMENTS:
        t = pattern.sub(repl, t)
    # reorganiza sequências pontuadas para evitar cópia literal
    t = re.sub(r",\s+(mas|porém|contudo)\s+", r". Ainda assim, ", t, flags=re.IGNORECASE)
    t = re.sub(r";\s+", ". ", t)
    if len(t) > 80 and random.random() < 0.3:
        t = re.sub(r",\s+", ", naquele momento, ", t, count=1)
    # remove espaços duplicados
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip()


def smooth_sentence(sentence: str, state: Dict[str, object]) -> str:
    sentence = expand_abbreviations(sentence)
    sentence = replace_roman_numerals(sentence)
    sentence = expand_siglas(sentence)
    sentence = expand_archaic(sentence)
    sentence = romancear_base(sentence, strength=0.7)
    sentence = re.sub(r"\s{2,}", " ", sentence)
    sentence = sentence.strip()
    sentence = paraphrase_sentence(sentence)
    return augment_sentence(sentence, state)


def augment_sentence(sentence: str, state: Dict[str, object]) -> str:
    core = sentence.strip()
    if not core:
        return core
    if core.startswith(("\"", "“")):
        return core
    letters_without_quotes = re.sub(r"[\"“”]", "", core)
    if len(letters_without_quotes) < 40 or random.random() < 0.45:
        return core
    mood = random.choice(ABSTRACT_MOODS)
    subject = state.get("last_name")
    if isinstance(subject, str) and subject:
        subject_str = subject
    else:
        subject_str = random.choice(DEFAULT_SUBJECTS)
    history = state.setdefault("recent_expansions", [])
    available = [exp for exp in MOOD_EXPANSIONS if exp not in history]
    if not available:
        history.clear()
        available = list(MOOD_EXPANSIONS)
    addition_template = random.choice(available)
    addition = addition_template.format(subject=subject_str, mood=mood)
    history.append(addition_template)
    if len(history) > 5:
        history.pop(0)
    if core.endswith((".", "!", "?")):
        return f"{core} {addition}"
    return f"{core}. {addition}"


def rewrite_paragraph(paragraph: str, state: Dict[str, object]) -> str:
    sentences = split_sentences(paragraph)
    rewritten: List[str] = []
    known_names = state.get("known_names")
    if not isinstance(known_names, set):
        known_names = set()
        state["known_names"] = known_names
    last_name_obj = state.get("last_name")
    last_name = last_name_obj if isinstance(last_name_obj, str) else None
    for idx, sentence in enumerate(sentences, start=1):
        is_dialogue = sentence.startswith(("—", "–"))
        if is_dialogue:
            new_sentence = rewrite_dialogue(sentence, last_name)
        else:
            new_sentence = smooth_sentence(sentence, state)
        names = collect_names(new_sentence)
        for n in names:
            known_names.add(n)
        if is_dialogue and names:
            candidates = [n for n in names if n in known_names]
            chosen = candidates[-1] if candidates else names[-1]
            last_name = chosen
            state["last_name"] = last_name
        state["known_names"] = known_names
        rewritten.append(new_sentence)
    if not rewritten:
        return ""
    paragraph_extra = random.choice(ABSTRACT_MOODS)
    closing = random.choice(PARAGRAPH_CLOSERS).format(mood=paragraph_extra)
    rewritten.append(closing)
    return normalize_sentence_case(" ".join(rewritten))


def rewrite_section_heuristic(section_text: str, state: Dict[str, object]) -> str:
    parts = re.split(r"\n\s*\n", section_text.strip())
    rewritten_parts = []
    for part in parts:
        rewritten = rewrite_paragraph(part, state)
        if rewritten:
            rewritten_parts.append(rewritten)
    return "\n\n".join(rewritten_parts)


def rewrite_section(
    section_text: str,
    state: Dict[str, object],
    llm: Optional[GPT4All] = None,
    openai_client: Any = None,
    openai_model: Optional[str] = None,
) -> str:
    if openai_client is not None and openai_model:
        try:
            output = rewrite_section_openai(section_text, openai_client, openai_model)
            if output.strip():
                return output
        except Exception as exc:
            print(f"[OpenAI] Falha ao reescrever seção: {exc}", file=sys.stderr)
    if llm is not None:
        try:
            output = rewrite_section_llm(section_text, llm)
            if output.strip():
                return output
        except Exception as exc:  # pragma: no cover
            print(f"[LLM] Falha ao reescrever seção: {exc}", file=sys.stderr)
    return rewrite_section_heuristic(section_text, state)


def write_section_files(sections: Sequence[Tuple[str, str]], temp_dir: Path) -> None:
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    for idx, (title, body) in enumerate(sections, 1):
        slug = slugify(title)
        filename = f"{idx:03d}-{slug}.md"
        (temp_dir / filename).write_text(body, encoding="utf-8")


def assemble_output(sections: Sequence[Tuple[str, str]], rewritten_sections: Sequence[str]) -> str:
    chunks: List[str] = []
    for (title, _), body in zip(sections, rewritten_sections):
        title_line = replace_roman_numerals(f"## {title}")
        chunks.append(f"{title_line}\n\n{body.strip()}")
    return "\n\n".join(chunks).strip() + "\n"


def process_file(
    input_path: Path,
    output_path: Path,
    temp_dir: Path,
    llm: Optional[GPT4All],
    openai_client: Any = None,
    openai_model: Optional[str] = None,
) -> None:
    random.seed(42)
    raw_text = input_path.read_text(encoding="utf-8")
    sections = split_markdown_sections(raw_text)
    if not sections:
        raise ValueError("Nenhuma seção identificada com prefixo '## '.")

    write_section_files(sections, temp_dir)

    rewritten_sections: List[str] = []
    known_names = extract_known_names(raw_text)
    state: Dict[str, object] = {"last_name": None, "known_names": known_names, "recent_expansions": []}
    with tqdm(total=len(sections), desc="Reescrevendo seções", unit="seção") as bar:
        for _, section_body in sections:
            rewritten = rewrite_section(
                section_body,
                state,
                llm=llm,
                openai_client=openai_client,
                openai_model=openai_model,
            )
            rewritten_sections.append(rewritten)
            bar.update(1)

    output_text = assemble_output(sections, rewritten_sections)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reescrita romanceada e modernizada de um arquivo Markdown.")
    parser.add_argument("--in", dest="input_path", required=True, help="Arquivo fonte a ser reescrito")
    parser.add_argument("--out", dest="output_path", required=True, help="Arquivo de saída gerado")
    parser.add_argument("--temp-dir", dest="temp_dir", default="Reescrever/_tmp_sections", help="Pasta temporária para as seções")
    parser.add_argument("--llm-model", dest="llm_model", default="models/mistral-7b-instruct-v0.2.Q4_0.gguf", help="Caminho para o modelo .gguf do GPT4All")
    parser.add_argument("--no-llm", dest="no_llm", action="store_true", help="Desativa reescrita com LLM e usa apenas heurísticas")
    parser.add_argument("--use-openai", dest="use_openai", action="store_true", help="Ativa reescrita via API da OpenAI")
    parser.add_argument("--openai-config", dest="openai_config", default="openai_config.json", help="Arquivo JSON com api_key/base_url da OpenAI")
    parser.add_argument("--openai-model", dest="openai_model", default="gpt-4o-mini", help="Modelo da OpenAI a ser usado")
    args = parser.parse_args()

    input_path = Path(args.input_path).expanduser().resolve()
    output_path = Path(args.output_path).expanduser().resolve()
    temp_dir = Path(args.temp_dir).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {input_path}")

    llm: Optional[GPT4All] = None
    use_llm = not args.no_llm
    llm_path = Path(args.llm_model).expanduser().resolve()
    if use_llm:
        if not GPT4ALL_AVAILABLE:
            print("Biblioteca gpt4all não disponível; usando heurísticas.", file=sys.stderr)
            use_llm = False
        else:
            try:
                llm = load_llm_model(llm_path)
            except Exception as exc:
                print(f"Não foi possível carregar o modelo LLM ({exc}); usando heurísticas.", file=sys.stderr)
                use_llm = False

    openai_client: Any = None
    openai_model: Optional[str] = None
    if args.use_openai:
        try:
            openai_client = load_openai_client(Path(args.openai_config))
            openai_model = args.openai_model
        except Exception as exc:
            print(f"Não foi possível inicializar OpenAI ({exc}); prosseguindo sem API.", file=sys.stderr)

    process_file(
        input_path,
        output_path,
        temp_dir,
        llm if use_llm else None,
        openai_client=openai_client,
        openai_model=openai_model,
    )


if __name__ == "__main__":
    main()
