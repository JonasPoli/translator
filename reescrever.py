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
from difflib import SequenceMatcher
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

PORTUGUESE_STOPWORDS = {
    "a", "o", "e", "os", "as", "um", "uma", "uns", "umas", "de", "da", "do",
    "das", "dos", "em", "no", "na", "nos", "nas", "ao", "aos", "à", "às",
    "para", "por", "com", "sem", "que", "como", "onde", "quando", "enquanto",
    "porque", "porquê", "se", "ser", "ter", "foi", "era", "são", "está",
    "estavam", "estava", "há", "houve", "até", "mais", "menos", "também",
    "muito", "tudo", "todos", "todas", "cada", "mesmo", "mesma", "mesmos",
    "mesmas", "todo", "toda", "pois", "então", "ainda", "já", "não", "sim",
    "é", "será", "era", "eram", "lá", "ali", "aqui", "isso", "isto", "aquilo",
    "essa", "esse", "esse", "essas", "esses",
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

FOCUS_PREFIX_STRIP = {"Em", "No", "Na", "Nos", "Nas", "Ao", "Aos", "À", "Pelo", "Pela", "Pelos", "Pelas", "Do", "Da", "Dos", "Das", "O", "A"}

RARE_TERMS: Dict[str, str] = {}

LLM_SYSTEM_PROMPT = (
    "Reescreva o texto a seguir deixando-o mais envolvente, fluido e emocionalmente rico, como se fosse escrito por um autor brasileiro contemporâneo.\n"
    "Mantenha o sentido original, mas melhore o ritmo, a clareza e a beleza da linguagem.\n\n"
    "Aplique todas as instruções abaixo de forma consistente.\n\n"
    " Objetivo\n\n"
    "Aprimorar o texto literário tornando-o:\n\n"
    "mais natural e prazeroso de ler;\n\n"
    "com frases curtas, equilibradas e expressivas;\n\n"
    "com emoção, ritmo e sensorialidade;\n\n"
    "mantendo o mesmo conteúdo e atmosfera do original.\n\n"
    "✍️ Estilo desejado\n\n"
    "Português brasileiro atual, elegante, mas fácil de entender.\n\n"
    "Narrativa fluida e poética, com ritmo de respiração (pausas e variações de intensidade).\n\n"
    "Linguagem emocional, visual e cinematográfica.\n\n"
    "Inspiração em autores brasileiros modernos como Martha Medeiros, Itamar Vieira Junior, Milton Hatoum, Carpinejar, Conceição Evaristo e Clarice Lispector (em tom narrativo).\n\n"
    " Regras de reescrita\n\n"
    "Preserve o conteúdo, o enredo e os sentimentos originais.\n\n"
    "Simplifique frases longas, sem perder o sentido poético.\n\n"
    "Evite termos arcaicos ou formais demais.\n\n"
    "Ex: “ó”, “todavia”, “dilaceramento”, “pleno” → substitua por termos mais naturais.\n\n"
    "Use frases curtas e com ritmo.\n\n"
    "Alterne períodos curtos e médios para dar musicalidade.\n\n"
    "Dê vida às emoções: mostre o que os personagens sentem com gestos, respiração, calor, vertigem, tremor, etc.\n\n"
    "Use imagens sensoriais.\n\n"
    "Substitua abstrações por percepções (som, toque, luz, cor, temperatura).\n\n"
    "Use travessões (—) para falas e expressões diretas, com naturalidade.\n\n"
    "Evite redundâncias e palavras repetidas.\n\n"
    "Crie pausas visuais (linhas em branco entre blocos de emoção ou ação).\n\n"
    "Não altere o tempo, local ou personagens originais.\n\n"
    " Técnicas sugeridas\n\n"
    "Mostrar em vez de contar:\n"
    "“Ela estava nervosa” → “As mãos dela tremiam, e o ar parecia faltar.”\n\n"
    "Ritmo respirado:\n"
    "Intercale ação e sensação:\n"
    "“Ela parou. Olhou. E o mundo pareceu suspenso por um instante.”\n\n"
    "Imagens concretas:\n"
    "“Sentiu a alma leve” → “Sentiu o peito abrir, como se o ar tivesse ficado mais claro.”\n\n"
    "Voz interna sutil:\n"
    "Adicione pensamentos curtos, naturais, que expressem emoção real.\n\n"
    " Formato do resultado\n\n"
    "Texto final limpo, pronto para publicação.\n\n"
    "Mantém os parágrafos separados, com ritmo fluido.\n\n"
    "Se houver diálogos, preserve-os com travessões e pausas realistas.\n\n"
    "Sem comentários, explicações ou listas — apenas o texto reescrito.\n\n"
    " Exemplo de uso\n\n"
    "Prompt:\n"
    "“Reescreva o texto abaixo conforme as instruções.”\n\n"
    "Texto:\n"
    "“A lua subia devagar. O vento passava frio pela janela. Ele pensava nela, e o coração doía.”\n\n"
    "Resultado esperado:\n"
    "“A lua subia lenta, desenhando um rastro de prata na noite.\n"
    "O vento entrava pela janela e roçava o rosto dele, frio e silencioso.\n"
    "Pensou nela — e o peito apertou como se o tempo tivesse parado.”"
)

LLM_USER_TEMPLATE = (
    "Melhore o texto literário a seguir deixando-o mais fluido, natural e emocionante. "
    "Use português brasileiro moderno, frases curtas, ritmo poético e linguagem sensorial. "
    "Preserve o sentido, mas simplifique a estrutura e aprofunde a emoção. "
    "Escreva como um autor brasileiro contemporâneo.\n\n"
    "Trecho original:\n{original}\n\n"
    "Texto reescrito:"
)

LLM_MODEL_CACHE: Dict[str, GPT4All] = {}

VALIDATION_DEBUG = bool(os.getenv("REWRITE_DEBUG"))

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
            forbidden_phrases = extract_forbidden_phrases(subchunk)
            extra_block = ""
            if forbidden_phrases:
                listed = "\n".join(f"- {phrase}" for phrase in forbidden_phrases)
                extra_block = (
                    "\n\nFrases do original que NÃO podem aparecer de forma literal ou com a mesma ordem:\n"
                    f"{listed}"
                )
            base_prompt = LLM_USER_TEMPLATE.format(original=subchunk) + extra_block
            for attempt, temp in enumerate((0.75, 0.9, 0.6)):
                user_prompt = base_prompt
                if attempt > 0:
                    user_prompt += (
                        "\n\nO texto anterior permaneceu próximo do original. Reescreva de novo "
                        "sem repetir nenhuma frase ou expressão inicial. Reformule cada oração com verbos e imagens novas, "
                        "use quebras de linha e dê ritmo respirado."
                    )
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": LLM_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=temp,
                        top_p=0.85,
                        presence_penalty=1.0,
                        frequency_penalty=0.8,
                        max_tokens=800,
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
                else:
                    print("[OpenAI] Saída rejeitada pela validação, tentando novamente.", file=sys.stderr)
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
    growth_ratio = new_word_count / original_word_count
    if growth_ratio < 0.6:
        if VALIDATION_DEBUG:
            preview = rewritten.strip().splitlines()[0] if rewritten.strip() else ""
            print(f"[validate] Rejeitado por crescimento insuficiente ({growth_ratio:.2f}) -> {preview[:120]!r}", file=sys.stderr)
        return False

    lower = rewritten.lower()
    for banned in ("exemplo", "teste", "nota", "avaliação"):
        if banned in lower:
            return False

    similarity = SequenceMatcher(None, original.lower(), rewritten.lower()).ratio()
    if similarity > 0.97:
        if VALIDATION_DEBUG:
            preview = rewritten.strip().splitlines()[0] if rewritten.strip() else ""
            print(f"[validate] Rejeitado por similaridade alta ({similarity:.3f}) -> {preview[:120]!r}", file=sys.stderr)
        return False

    orig_names = {name.lower() for name in extract_known_names(original)}
    new_names = {name.lower() for name in collect_names(rewritten) if name}

    for name in orig_names:
        if name not in new_names:
            if VALIDATION_DEBUG:
                preview = rewritten.strip().splitlines()[0] if rewritten.strip() else ""
                print(f"[validate] Rejeitado por remover nome essencial ({name}) -> {preview[:120]!r}", file=sys.stderr)
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
            forbidden_phrases = extract_forbidden_phrases(subchunk)
            extra_block = ""
            if forbidden_phrases:
                listed = "\n".join(f"- {phrase}" for phrase in forbidden_phrases)
                extra_block = (
                    "\n\nFrases do original que NÃO podem ser repetidas literalmente:\n"
                    f"{listed}"
                )
            base_prompt = LLM_USER_TEMPLATE.format(original=subchunk) + extra_block
            for attempt, temp in enumerate((0.85, 0.95, 0.7)):
                user_prompt = base_prompt
                if attempt > 0:
                    user_prompt += (
                        "\n\nO texto anterior ainda ficou próximo do original. Reescreva novamente "
                        "sem repetir frases, mude completamente a ordem e o vocabulário, use ritmo moderno e imagens sensoriais."
                    )
                with model.chat_session(system_prompt=LLM_SYSTEM_PROMPT):
                    response = model.generate(
                        user_prompt,
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
                else:
                    print("[GPT4All] Saída rejeitada pela validação, tentando novamente.", file=sys.stderr)
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


def extract_forbidden_phrases(text: str, limit: int = 6) -> List[str]:
    phrases: List[str] = []
    for sentence in split_sentences(text):
        cleaned = sentence.strip()
        if len(cleaned) < 5:
            continue
        phrases.append(cleaned)
        if len(phrases) >= limit:
            break
    return phrases


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
    # Preserve the original fala sem criar narrador fictício.
    stripped = sentence.strip()
    if not stripped:
        return sentence
    if stripped.startswith("—"):
        return "— " + stripped[1:].strip()
    if stripped.startswith("–"):
        return "– " + stripped[1:].strip()
    return stripped


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
    # Para reduzir comentários metalinguísticos, não acrescentamos frases extras na heurística.
    return core


def select_focus(sentence: str, state: Dict[str, object]) -> Optional[str]:
    # Procura sequências de palavras iniciadas por maiúsculas (ex.: "Hauteville House").
    capital_sequences = re.findall(r"(?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\w-]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\w-]+)*)", sentence)
    for seq in reversed(capital_sequences):
        words = seq.strip().split()
        while words and words[0] in FOCUS_PREFIX_STRIP:
            words.pop(0)
        if not words:
            continue
        stripped = " ".join(words)
        first_token = words[0]
        if first_token in STOPWORDS_CAPS:
            continue
        return stripped
    names = collect_names(sentence)
    known_names = state.get("known_names")
    if isinstance(known_names, set):
        for candidate in reversed(names):
            if candidate not in STOPWORDS_CAPS and candidate in known_names:
                return candidate
    for candidate in reversed(names):
        if candidate not in STOPWORDS_CAPS:
            return candidate
    tokens = re.findall(r"[A-Za-zÀ-ÿ'-]+", sentence)
    for token in tokens:
        if token and token[0].isupper() and token not in STOPWORDS_CAPS:
            return token
    return None


def explain_rare_terms(sentence: str) -> str:
    def replace(match: re.Match) -> str:
        word = match.group(0)
        key = word.lower()
        explanation = RARE_TERMS.get(key)
        if not explanation:
            return word
        # Evita duplicar explicação se já existir parênteses logo após
        tail = sentence[match.end():match.end()+2]
        if tail.startswith("("):
            return word
        if word[0].isupper():
            explanation_text = explanation[0].upper() + explanation[1:]
        else:
            explanation_text = explanation
        return f"{word} ({explanation_text})"

    pattern = re.compile(r"\b(" + "|".join(map(re.escape, RARE_TERMS.keys())) + r")\b", flags=re.IGNORECASE)
    return pattern.sub(replace, sentence)


def load_rare_terms(default_path: Path, user_path: Path) -> Dict[str, str]:
    combined: Dict[str, str] = {}
    if default_path.exists():
        try:
            combined.update(json.loads(default_path.read_text(encoding="utf-8")))
        except Exception as exc:
            print(f"[RareTerms] Não foi possível ler {default_path}: {exc}", file=sys.stderr)
    if user_path.exists():
        try:
            combined.update(json.loads(user_path.read_text(encoding="utf-8")))
        except Exception as exc:
            print(f"[RareTerms] Não foi possível ler {user_path}: {exc}", file=sys.stderr)
    return {k.lower(): v for k, v in combined.items()}




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
            new_sentence = explain_rare_terms(new_sentence)
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
            print("[OpenAI] Reescrevendo seção via OpenAI (modo online).", file=sys.stderr)
            output = rewrite_section_openai(section_text, openai_client, openai_model)
            if output.strip():
                return output
        except Exception as exc:
            print(f"[OpenAI] Falha ao reescrever seção: {exc}", file=sys.stderr)
    if llm is not None:
        try:
            print("[GPT4All] Reescrevendo seção via modelo local.", file=sys.stderr)
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
    rare_terms_path: Optional[Path] = None,
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
    parser.add_argument("--rare-terms", dest="rare_terms", default="rare_terms.json", help="Arquivo JSON de termos raros e suas explicações")
    args = parser.parse_args()

    input_path = Path(args.input_path).expanduser().resolve()
    output_path = Path(args.output_path).expanduser().resolve()
    temp_dir = Path(args.temp_dir).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {input_path}")

    script_dir = Path(__file__).resolve().parent
    default_rare_terms_path = script_dir / "rare_terms_default.json"
    rare_terms_path = Path(args.rare_terms).expanduser().resolve()

    loaded_rare_terms = load_rare_terms(default_rare_terms_path, rare_terms_path)
    RARE_TERMS.clear()
    RARE_TERMS.update(loaded_rare_terms)

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
        rare_terms_path=rare_terms_path if rare_terms_path else None,
    )


if __name__ == "__main__":
    main()
