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
