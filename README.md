# translate.py (local + grátis)

Pipeline **100% local** para traduzir (Argos Translate), romancear (heurística) e modernizar pt‑BR, com **barras de progresso reais** (por arquivo e por trecho) e **ETA** estável.

## Instalação rápida

```bash
python3 -m venv env_tradutor
source env_tradutor/bin/activate

pip install --upgrade "pip<25"
pip install "numpy>=1.26,<2" "ctranslate2<5" argostranslate tqdm pandas requests
# (opcional) stanza e spacy se você já usa em outros projetos
```

Instale o par de idiomas no Argos:
```python
python - <<'PY'
import argostranslate.package as pkg
pkg.update_package_index()
p = [p for p in pkg.get_available_packages() if p.from_code=="en" and p.to_code=="pt"][0]
pkg.install_from_path(p.download())
print("OK en→pt instalado")
PY
```

## Uso

```bash
python translate.py --mode both --provider argos \
  --src en --tgt pt \
  --in ./originais --out ./final \
  --ext .md .txt \
  --chunk-by paragraph --max-chars 3000 \
  --romance-strength 0.6 \
  --modernize \
  --verbose
```

- `--mode translate` executa somente a tradução.
- `--mode both` traduz → romanceia (leve) → moderniza (lexical/fluência).
- `--modernize` ativa modernizações pt‑BR (ex.: **propriedade hereditária → herança de família**, etc.).
- `--romance-strength` controla quão “fluida” fica a prosa **sem criar fatos** (0.3–0.7 recomendado).
- `--chunk-by paragraph` pré‑fatia por parágrafos (ETA estável).

### Dicas anti‑segfault (macOS + Argos/CT2)
- O script já define `OMP_NUM_THREADS=1`, `ARGOS_DEVICE_TYPE=cpu` e desativa multiprocessing por padrão.
- Evite `--mp` no macOS com Argos. Se quiser tentar paralelismo, use `--mp` por sua conta e risco.
- Se ainda assim travar, rode com `--safe-threads` (reforça env) e/ou reduza `--max-chars` (ex. 1800).

### Personalizando modernizações
Crie um `modernizer_ptbr_overrides.json` ao lado do script, por exemplo:
```json
{
  "\\bpropriedade(?:s)? hereditária(?:s)?\\b": "herança de família",
  "\\bassegurar(?:em)?\\s+salas ancestrais\\b": "conseguir alugar um casarão antigo"
}
```

## Saídas
- Mantém a estrutura de pastas de entrada.
- Barras de progresso:
  - **Arquivos** (lista total)
  - **Trechos** por arquivo (count conhecido para ETA honesto)

## Limites / Filosofia
- Romanceador é **heurístico** (sem IA remota). Ele alisa cadência e acrescenta pequenas reformulações sem inventar fatos.
- Modernizador aplica substituições pt‑BR naturais pós-tradução (com dicionário e regex).

## Reescrever (`reescrever.py`)

Reescreve arquivos Markdown romanceando/modernizando prosa já traduzida. Possui três modos de operação:

### 1. Heurístico local (padrão)
- Não depende de modelos externos;
- Reescreve de forma limitada (agora sem frases metalinguísticas);
- Uso direto:
  ```bash
  python3 reescrever.py --in Reescrever/original.md --out Reescrever/gerado.md
  ```

### 2. GPT4All (modelo `.gguf`)
- Instale a biblioteca no Python correto:
  ```bash
  python3 -m pip install gpt4all
  ```
- Baixe um modelo (ex.: `models/mistral-7b-instruct-v0.2.Q4_K_M.gguf`).
- Execute:
  ```bash
  python3 reescrever.py --in Reescrever/original.md --out Reescrever/gerado.md --llm-model models/mistral-7b-instruct-v0.2.Q4_K_M.gguf
  ```
- Se o LLM inventar fatos, o script volta automaticamente ao modo heurístico.

### 3. OpenAI (online opcional)
- Copie `openai_config.json.example` para `openai_config.json` e informe `api_key` (e `base_url`, se necessário).
- Instale `openai` no Python em uso:
  ```bash
  python3 -m pip install openai
  ```
- Rode com:
  ```bash
  python3 reescrever.py --in Reescrever/original.md --out Reescrever/gerado.md \
    --use-openai --openai-config openai_config.json --openai-model gpt-4o-mini
  ```
- Prompt embutido exige expansão sensorial da prosa e explica termos incomuns dentro do próprio texto (sem notas de rodapé), mantendo fatos intactos.

### Termos raros
- Explicações vêm de `rare_terms_default.json` (base) + `rare_terms.json` (personalizável).
- Elabore sua lista em `rare_terms.json` antes de rodar o script. Qualquer termo presente ali será convertido em “termo (explicação)” dentro da narrativa.

O script indica no stderr a rota utilizada:
- `[OpenAI] Reescrevendo seção via OpenAI (modo online).`
- `[GPT4All] Reescrevendo seção via modelo local.`
- Sem mensagem adicional = heurístico.

Caso nenhuma camada funcione, o texto final virá do modo heurístico.
