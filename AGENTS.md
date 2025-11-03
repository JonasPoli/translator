# AGENTS.md

## Visão geral do pipeline (local, sem chaves/IA remota)

1. **Tradutor (Argos Translate, offline)**  
   - Provedor: `--provider argos` (único suportado no momento).
   - Idiomas definidos por `--src` e `--tgt` (ex.: `en` → `pt`).

2. **Romanceador heurístico (opcional)**  
   - Controlado por `--romance-strength` (0.0 desliga).  
   - Objetivo: dar fluidez moderna, leve aumento descritivo **sem criar fatos**.

3. **Modernizador pt‑BR (opcional)**  
   - Ligado por `--modernize`.  
   - Substituições contextuais para evitar traduções literais engessadas.  
   - Regras internas + `modernizer_ptbr_overrides.json` para preferências do usuário.

## Decisões de design para estabilidade
- **Sem multiprocessing** por padrão quando `provider=argos` (macOS + CT2 podem segfaultar).  
  Ative manualmente com `--mp` se quiser arriscar.
- Env fixado: `OMP_NUM_THREADS=1`, `ARGOS_DEVICE_TYPE=cpu`, `CT2_USE_EXPERIMENTAL_PACKED_GEMM=0`.

## Extensões futuras
- Provedor adicional (por ex. Marian local) mantendo 100% offline.
- Camada de pós‑edição mais rica (regras morfossintáticas via spaCy/Stanza).

## Qualidade de prosa (pt‑BR contemporâneo)
- Preferência por construções naturais no Brasil.
- Ex.: “propriedade hereditária” → “herança de família”;  
  “assegurem salas ancestrais” → “consigam alugar um casarão antigo”;  
  “zomba abertamente” → “caçoa sem rodeios”.

## Reescrever offline ou com LLM
- `reescrever.py` aceita dois modos:
  - **Heurístico/local:** não usa nenhum modelo externo. Funciona sempre, mas gera ampliação limitada.
  - **LLM integrado (GPT4All ou OpenAI):** texto romanceado longo, com explicação inline de termos incomuns.  
    - O prompt embutido exige fidelidade total aos fatos e clarifica palavras pouco comuns dentro da própria frase, evitando notas de rodapé.
    - Se o LLM inventar fatos ou não atenda às regras, o script cai automaticamente de volta para o modo heurístico.
- **OpenAI:**  
  - Criar `openai_config.json` (veja `openai_config.json.example`) com `api_key` e, opcionalmente, `base_url`.  
  - Com a biblioteca `openai` instalada no mesmo Python:  
    ```bash
    python3 reescrever.py --in arquivo.md --out saida.md --use-openai --openai-config openai_config.json --openai-model gpt-4o-mini
    ```  
    - O script escreve no stderr se está usando OpenAI (`[OpenAI]`) ou o modelo local (`[GPT4All]`).
- **GPT4All:**  
  - Configure `--llm-model` com um `.gguf` (ex.: `models/mistral-7b-instruct-v0.2.Q4_K_M.gguf`).  
  - Se `gpt4all` estiver instalado no Python correto, o script tenta o modelo local antes de cair na heurística.
- **Termos raros:**  
  - Explicações são carregadas de `rare_terms_default.json` + `rare_terms.json`.  
  - Cada ocorrência no texto é transformada em “termo (explicação)” sem notas de rodapé.  
  - Popule `rare_terms.json` manualmente com as palavras que quer explicar (o script não cria entradas automaticamente).
