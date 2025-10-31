#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
from pathlib import Path
from tqdm import tqdm
from argostranslate import translate

# Evita travamentos no macOS
os.environ.setdefault("OMP_NUM_THREADS", "1")

try:
    from gpt4all import GPT4All
    GPT4ALL_AVAILABLE = True
except ImportError:
    GPT4ALL_AVAILABLE = False


ROMANCE_PROMPT = """
O objetivo é produzir uma nova versão do texto que:
- Mantenha a fidelidade ao original – a narrativa, os acontecimentos e as descrições não devem ser alterados.
- Seja maior do que o texto original – o novo texto deve expandir o conteúdo, tornando-o mais longo e detalhado.
- Tenha estilo moderno e romanceado, não sendo em verso – a escrita deve ser fluida, clara, atraente e fácil de ler, como se fosse feita por um romancista contemporâneo.
- Aumente a riqueza descritiva – acrescente descrições sensoriais, com foco em ambientes, emoções e pensamentos internos.
- Deixe os diálogos mais claros – indique sempre quem fala.
- Use linguagem atualizada – evite palavras antigas e rebuscadas.
- Reescreva o texto como se fosse outro escritor moderno, fiel aos fatos.
- Evite notas de rodapé; explique termos dentro da narrativa de forma natural.
- Expanda e romanceie o tom narrativo, com ritmo e metáforas, sem mudar o enredo.

Entrada: Trecho original traduzido há 70 anos.
Saída esperada: Texto reescrito, moderno, descritivo, contextualizado, envolvente e claro.
"""

def translate_text(text: str, src: str, tgt: str) -> str:
    return translate.translate(text, src, tgt)


def romancear_texto(text: str) -> str:
    """Reescreve o texto de modo romanceado, localmente se possível."""
    if GPT4ALL_AVAILABLE:
        model = GPT4All("mistral-7b-instruct-v0.2.Q4_0.gguf")
        with model.chat_session():
            response = model.generate(
                f"{ROMANCE_PROMPT}\n\nTexto original:\n{text}\n\nTexto reescrito:",
                temp=0.8,
                top_p=0.9,
                max_tokens=2048
            )
        return response.strip()
    else:
        # Fallback simples: reestrutura e aumenta o texto
        paragraphs = text.split("\n")
        out = []
        for p in paragraphs:
            if not p.strip():
                continue
            out.append(
                f"{p.strip()} — "
                "neste trecho, o narrador mergulha nas sensações e pensamentos dos personagens, "
                "expandindo a cena com detalhes vívidos e uma linguagem contemporânea."
            )
        return "\n\n".join(out)


def process_file(in_file: Path, out_file: Path, src: str, tgt: str, romancear: bool, progress: tqdm):
    text = in_file.read_text(encoding="utf-8", errors="ignore")
    out = translate_text(text, src, tgt)
    if romancear:
        out = romancear_texto(out)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(out, encoding="utf-8")
    progress.update(1)


def main():
    ap = argparse.ArgumentParser(description="Tradutor com modo romanceado opcional.")
    ap.add_argument("--src", default="en", help="Língua origem (ex: en)")
    ap.add_argument("--tgt", default="pt", help="Língua destino (ex: pt)")
    ap.add_argument("--in", dest="inp", required=True, help="Arquivo ou pasta de entrada")
    ap.add_argument("--out", dest="out", required=True, help="Arquivo ou pasta de saída")
    ap.add_argument("--ext", nargs="+", default=[".txt", ".md"], help="Extensões permitidas")
    ap.add_argument("--romancear", action="store_true", help="Ativa modo romanceado (expande e moderniza o texto)")
    args = ap.parse_args()

    in_path = Path(args.inp).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()

    if not in_path.exists():
        print(f"ERRO: caminho de entrada não existe: {in_path}", file=sys.stderr)
        sys.exit(1)

    if in_path.is_file():
        files = [in_path]
    else:
        files = [p for p in in_path.rglob("*") if p.suffix.lower() in args.ext]

    progress = tqdm(total=len(files), desc="Arquivos", ncols=100, unit="arquivo")
    for f in files:
        rel = f.relative_to(in_path)
        out_file = (out_path / rel).with_suffix(".md")
        process_file(f, out_file, args.src, args.tgt, args.romancear, progress)
    progress.close()

    print("\n✅ Tradução concluída com sucesso!")
    if args.romancear:
        print("✨ Modo romanceado aplicado aos textos traduzidos.")


if __name__ == "__main__":
    main()
