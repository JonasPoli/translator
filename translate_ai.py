#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translate_ai.py — fluxo de tradução com LLM para literatura longa.

Objetivos principais:
1) Preservar todos os fatos narrativos, cronologia e nomes originais.
2) Produzir um texto em português brasileiro contemporâneo, com cadência moderna.
3) Manter a mesma estrutura de parágrafos do original, evitando notas ou explicações externas.

O script usa um LLM (OpenAI ou GPT4All) para gerar a versão final. Opcionalmente,
gera uma tradução literal de apoio via Argos Translate para servir de guarda-corpo
sem nunca ser escrita diretamente.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Mantém ambiente estável para Argos / CT2 quando usado como apoio.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("CT2_USE_EXPERIMENTAL_PACKED_GEMM", "0")
os.environ.setdefault("ARGOS_DEVICE_TYPE", "cpu")

try:
    from tqdm import tqdm
except Exception:
    print("Instale tqdm: pip install tqdm", file=sys.stderr)
    sys.exit(1)

try:
    from argostranslate import translate as argos_translate
    ARGOS_AVAILABLE = True
except Exception:
    argos_translate = None  # type: ignore
    ARGOS_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OpenAI = None  # type: ignore
    OPENAI_AVAILABLE = False

try:
    from gpt4all import GPT4All
    GPT4ALL_AVAILABLE = True
except Exception:
    GPT4All = None  # type: ignore
    GPT4ALL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Utilidades de chunking

def split_paragraphs(text: str) -> List[str]:
    parts = re.split(r"\n\s*\n", text.strip(), flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def chunk_by_paragraph(text: str, max_chars: int) -> List[str]:
    chunks: List[str] = []
    buffer = ""
    for paragraph in split_paragraphs(text):
        if not buffer:
            buffer = paragraph
            continue
        candidate = f"{buffer}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            buffer = candidate
        else:
            chunks.append(buffer)
            buffer = paragraph
    if buffer:
        chunks.append(buffer)
    return chunks


def chunk_by_chars(text: str, max_chars: int) -> List[str]:
    text = text.strip()
    if not text:
        return []
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def count_paragraphs(text: str) -> int:
    return len(split_paragraphs(text)) or 1


# ---------------------------------------------------------------------------
# Tradução literal (opcional) via Argos

def literal_translate(text: str, src: str, tgt: str) -> str:
    if not ARGOS_AVAILABLE:
        raise RuntimeError("Argos Translate não está instalado; instale com `pip install argostranslate`.")
    return argos_translate.translate(text, src, tgt)


# ---------------------------------------------------------------------------
# LLM helpers

SYSTEM_PROMPT_TEMPLATE = (
    "Você é um tradutor literário brasileiro especializado em romances históricos. "
    "Converte textos escritos em {src_lang} para português brasileiro atual com fluidez, ritmo envolvente e vocabulário contemporâneo. "
    "Você mantém fidelidade absoluta aos fatos narrados, à cronologia, aos lugares e aos nomes próprios. "
    "Jamais cria, remove ou altera eventos, e nunca muda a época da história. "
    "Você evita qualquer nota de rodapé, explicação externa ou metacomentário, limitando-se ao texto narrativo. "
    "Quando adequado, usa expressões e gírias brasileiras de hoje, mas sem exageros ou rupturas de tom."
)

USER_PROMPT_TEMPLATE = """Traduza e reescreva o trecho a seguir em português brasileiro contemporâneo,
mantendo o mesmo número de parágrafos do original e preservando integralmente os fatos,
personagens, cronologia e atmosfera da cena. Não adicione comentários, notas ou títulos extras.

<TextoOriginal>
{original}
</TextoOriginal>
{literal_block}

Instruções adicionais:
- Todos os nomes próprios e termos históricos devem aparecer exatamente como no texto original.
- Se houver falas, mantenha quem fala e o conteúdo, apenas modernize a forma de dizer.
- Use pontuação viva, frases com ritmo natural e vocabulário do Brasil de hoje.
- Evite palavras arcaicas e traduções literais engessadas.
- Não explique termos; incorpore significados no fluxo da frase.

Entregue apenas o texto traduzido e parafraseado, sem prefácio ou conclusão.
"""


def build_user_prompt(original: str, literal: Optional[str]) -> str:
    literal_block = ""
    if literal and literal.strip():
        literal_block = (
            "\nTradução literal de apoio (não copie, use apenas como referência de sentido):\n"
            "<TraducaoLiteral>\n"
            f"{literal.strip()}\n"
            "</TraducaoLiteral>\n"
        )
    return USER_PROMPT_TEMPLATE.format(original=original.strip(), literal_block=literal_block)


def extract_content_from_openai(resp: Any) -> str:
    if not resp or not getattr(resp, "choices", None):
        return ""
    message = resp.choices[0].message
    content = getattr(message, "content", "")
    if isinstance(content, list):
        return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return content or ""


def load_openai_client(config_path: Path) -> Any:
    if not OPENAI_AVAILABLE:
        raise RuntimeError("Biblioteca openai não instalada. Instale com `pip install openai`.")

    cfg = config_path.expanduser().resolve()
    if not cfg.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração OpenAI não encontrado: {cfg}. "
            "Use o modelo openai_config.json.example como referência."
        )
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Configuração OpenAI inválida: {exc}") from exc

    api_key = data.get("api_key") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("API key não encontrada nem no JSON nem na variável OPENAI_API_KEY.")
    base_url = data.get("base_url")

    kwargs: Dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


class LLMTranslator:
    def __init__(
        self,
        backend: str,
        src_lang: str,
        tgt_lang: str,
        *,
        openai_client: Any = None,
        openai_model: Optional[str] = None,
        gpt4all_model_path: Optional[Path] = None,
        max_tokens: int = 900,
    ):
        self.backend = backend
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.openai_client = openai_client
        self.openai_model = openai_model
        self.gpt4all_model_path = gpt4all_model_path
        self.max_tokens = max_tokens
        self._gpt4all_model: Optional[GPT4All] = None

        if backend == "openai" and not (openai_client and openai_model):
            raise ValueError("Backend OpenAI requer cliente inicializado e nome do modelo.")
        if backend == "gpt4all" and not gpt4all_model_path:
            raise ValueError("Backend GPT4All requer caminho para o modelo .gguf.")

    def _ensure_gpt4all(self) -> GPT4All:
        if not GPT4ALL_AVAILABLE:
            raise RuntimeError("Biblioteca gpt4all não instalada. Instale com `pip install gpt4all`.")
        if self._gpt4all_model is None:
            model_path = self.gpt4all_model_path
            if model_path is None:
                raise RuntimeError("Caminho do modelo GPT4All não configurado.")
            model_path = model_path.expanduser().resolve()
            if not model_path.exists():
                raise FileNotFoundError(f"Modelo GPT4All não encontrado: {model_path}")
            self._gpt4all_model = GPT4All(
                model_name=model_path.name,
                model_path=str(model_path.parent),
                allow_download=False,
                n_threads=max(os.cpu_count() or 4, 4),
            )
        return self._gpt4all_model

    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        if self.backend == "openai":
            assert self.openai_client is not None
            assert self.openai_model is not None
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                top_p=0.9,
                presence_penalty=0.2,
                frequency_penalty=0.4,
                max_tokens=self.max_tokens,
            )
            return extract_content_from_openai(response)

        if self.backend == "gpt4all":
            model = self._ensure_gpt4all()
            with model.chat_session(system_prompt=system_prompt):
                return model.generate(
                    user_prompt,
                    temp=temperature,
                    top_p=0.92,
                    max_tokens=self.max_tokens,
                )

        raise ValueError(f"Backend desconhecido: {self.backend}")

    def translate_chunk(self, original: str, literal: Optional[str], *, retries: int = 2) -> str:
        if not original.strip():
            return ""

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(src_lang=self.src_lang, tgt_lang=self.tgt_lang)
        attempt = 0
        issues_note = ""
        reference_text = literal or original
        ref_tokens = max(len(reference_text.split()), 1)

        while attempt <= retries:
            user_prompt = build_user_prompt(original, literal)
            if issues_note:
                user_prompt += f"\nObservação: {issues_note}\nReescreva novamente obedecendo rigorosamente a instrução mencionada."
            try:
                candidate = self._call_llm(system_prompt, user_prompt, temperature=0.85 if attempt == 0 else 0.75)
            except Exception as exc:
                if attempt >= retries:
                    raise RuntimeError(f"Falha ao consultar LLM ({self.backend}): {exc}") from exc
                time.sleep(1 + attempt)
                attempt += 1
                issues_note = "houve uma falha técnica; tente outra formulação mantendo todas as instruções"
                continue

            cleaned = clean_output(candidate)
            valid, issues = validate_output(original, cleaned, ref_tokens)
            if valid:
                return cleaned

            if attempt >= retries:
                break

            issues_note = "; ".join(issues)
            attempt += 1

        # Fallback derradeiro: retorna tradução literal se disponível, senão candidato bruto.
        if literal:
            return literal.strip()
        return cleaned if cleaned.strip() else original.strip()


# ---------------------------------------------------------------------------
# Validação e pós-processamento

def clean_output(text: str) -> str:
    t = text.strip()
    t = re.sub(r"(?i)^texto\s*(?:traduzido|reescrito)?[:\-]?\s*", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def validate_output(original: str, candidate: str, reference_tokens: int) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    if not candidate.strip():
        issues.append("texto vazio")
        return False, issues

    original_paragraphs = count_paragraphs(original)
    candidate_paragraphs = count_paragraphs(candidate)
    if original_paragraphs != candidate_paragraphs:
        issues.append("mantenha o mesmo número de parágrafos")

    words = len(candidate.split())
    ratio = words / max(reference_tokens, 1)
    if ratio < 0.55:
        issues.append("texto ficou conciso demais em relação ao original")
    if ratio > 1.75:
        issues.append("texto expandiu demais em relação ao original")

    if issues:
        return False, issues
    return True, issues


# ---------------------------------------------------------------------------
# Arquivos de entrada / saída

def collect_files(path: Path, extensions: Iterable[str]) -> List[Path]:
    if path.is_file():
        return [path]
    files: List[Path] = []
    for ext in extensions:
        files.extend(path.rglob(f"*{ext}"))
    return sorted(files)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def process_file(
    in_path: Path,
    out_path: Path,
    *,
    args: argparse.Namespace,
    translator: LLMTranslator,
) -> None:
    raw = read_text(in_path)
    if args.chunk_by == "paragraph":
        chunks = chunk_by_paragraph(raw, args.max_chars)
    else:
        chunks = chunk_by_chars(raw, args.max_chars)

    literal_chunks: List[Optional[str]] = [None] * len(chunks)
    if args.literal_provider == "argos":
        for idx, chunk in enumerate(chunks):
            try:
                literal_chunks[idx] = literal_translate(chunk, args.src, args.tgt)
            except Exception as exc:
                print(f"[literal] Falhou ao traduzir trecho {idx+1} de {in_path.name}: {exc}", file=sys.stderr)
                literal_chunks[idx] = None

    results: List[str] = []
    bar = tqdm(total=len(chunks), desc=f"Trechos: {in_path.name}", unit="trecho", leave=False)
    for idx, chunk in enumerate(chunks):
        literal = literal_chunks[idx]
        try:
            translated = translator.translate_chunk(chunk, literal, retries=args.max_retries)
        except Exception as exc:
            bar.close()
            raise RuntimeError(f"Falha ao traduzir trecho {idx+1} do arquivo {in_path}: {exc}") from exc
        results.append(translated)
        bar.update(1)
    bar.close()

    final_text = "\n\n".join(results).strip()
    write_text(out_path, final_text)


# ---------------------------------------------------------------------------
# CLI

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Tradutor literário com LLM mantendo fidelidade factual e estilo brasileiro contemporâneo.",
    )
    parser.add_argument("--src", required=True, help="Código da língua de origem (ex.: en).")
    parser.add_argument("--tgt", required=True, help="Código da língua de destino (ex.: pt).")
    parser.add_argument("--input", dest="inp", required=True, help="Arquivo ou pasta de entrada.")
    parser.add_argument("--output", dest="out", required=True, help="Arquivo ou pasta de saída.")
    parser.add_argument("--ext", nargs="+", default=[".md", ".txt"], help="Extensões consideradas ao usar pasta.")
    parser.add_argument("--chunk-by", choices=["paragraph", "chars"], default="paragraph", help="Estratégia de chunking.")
    parser.add_argument("--max-chars", type=int, default=3200, help="Tamanho máximo por chunk quando chunk-by=paragraph.")
    parser.add_argument("--max-retries", type=int, default=3, help="Tentativas por chunk quando validação falhar.")
    parser.add_argument("--backend", choices=["openai", "gpt4all"], required=True, help="LLM utilizado para a reescrita.")
    parser.add_argument("--openai-config", default="openai_config.json", help="Arquivo JSON com api_key/base_url.")
    parser.add_argument("--openai-model", default="gpt-4o-mini", help="Modelo a ser usado com a API da OpenAI.")
    parser.add_argument("--llm-model", default="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf", help="Modelo local GPT4All.")
    parser.add_argument("--literal-provider", choices=["argos", "none"], default="argos", help="Tradução literal de apoio.")
    parser.add_argument("--dry-run", action="store_true", help="Só mostra contagem de chunks e sai.")
    parser.add_argument("--verbose", action="store_true", help="Mensagens adicionais.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    inp = Path(args.inp).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    if not inp.exists():
        print(f"ERRO: caminho de entrada não encontrado: {inp}", file=sys.stderr)
        sys.exit(2)

    files = collect_files(inp, args.ext)
    if not files:
        print("Nenhum arquivo encontrado com as extensões informadas.", file=sys.stderr)
        sys.exit(3)

    if inp.is_file() and out.suffix:
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        out.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        for f in files:
            raw = read_text(f)
            if args.chunk_by == "paragraph":
                chunks = chunk_by_paragraph(raw, args.max_chars)
            else:
                chunks = chunk_by_chars(raw, args.max_chars)
            print(f"{f}: {len(chunks)} trecho(s)")
        return

    openai_client = None
    gpt4all_model_path: Optional[Path] = None

    if args.backend == "openai":
        try:
            openai_client = load_openai_client(Path(args.openai_config))
            if args.verbose:
                print("[OpenAI] cliente inicializado.", file=sys.stderr)
        except Exception as exc:
            print(f"Não foi possível inicializar OpenAI: {exc}", file=sys.stderr)
            sys.exit(4)
    else:
        gpt4all_model_path = Path(args.llm_model)

    if args.literal_provider == "none":
        args.literal_provider = None
    translator = LLMTranslator(
        backend=args.backend,
        src_lang=args.src,
        tgt_lang=args.tgt,
        openai_client=openai_client,
        openai_model=args.openai_model,
        gpt4all_model_path=gpt4all_model_path,
    )

    files_bar = tqdm(total=len(files), desc="Arquivos", unit="arq")
    for file_path in files:
        if inp.is_file() and out.suffix:
            out_path = out
        else:
            rel = file_path.relative_to(inp) if inp.is_dir() else Path(file_path.name)
            out_path = (out / rel).with_suffix(rel.suffix)
            out_path.parent.mkdir(parents=True, exist_ok=True)

        if args.verbose:
            print(f"→ Traduzindo {file_path} para {out_path}", file=sys.stderr)

        process_file(
            file_path,
            out_path,
            args=args,
            translator=translator,
        )
        files_bar.update(1)
    files_bar.close()


if __name__ == "__main__":
    main()
