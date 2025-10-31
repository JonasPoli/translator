# translate.py (com progresso decente e modo *romance*)

## Instalação rápida
```bash
python -m venv env_tradutor
source env_tradutor/bin/activate
pip install argostranslate tqdm openai
# (Opcional) Instale o pacote en->pt do Argos (pelo seu script anterior)
```

## Uso (tradução Argos)
```bash
./translate.py --mode translate --provider argos --src en --tgt pt   --in ./originais --out ./traduzidos --ext .md .txt --verbose
```

## Uso (somente romance, via OpenAI)
```bash
export OPENAI_API_KEY="SUA_CHAVE"
./translate.py --mode romance --provider openai --openai-model gpt-4o-mini   --in ./traduzidos --out ./romanceados --ext .md --verbose
```

## Uso (traduzir e depois romancear no mesmo passo)
```bash
export OPENAI_API_KEY="SUA_CHAVE"
./translate.py --mode both --provider openai   --src en --tgt pt   --in ./originais --out ./final --ext .md   --chunk-by paragraph --max-chars 3000 --verbose
```

## Barra de progresso e ETA
- Progresso por **arquivo** e por **chunk** com ETA.
- `--verbose` imprime passo-a-passo, tempo por chunk e ETA restante do arquivo.

## Evitar o texto chato "neste trecho..."
O modo *romance* usa um prompt em `prompts/romance_ptbr.txt` que **proíbe** frases metalinguísticas e
um sanitizador final remove qualquer ocorrência residual (como “neste trecho...”).
