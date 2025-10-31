<!-- Guia para agentes locais executarem a reescrita romanceada -->

# TRADUTOR

Este guia descreve, passo a passo, como repetir o trabalho de recriar um capítulo traduzido e romanceado a partir do original em inglês, mantendo correspondência linha a linha. A ideia é que qualquer nova instância do agente consiga reproduzir o processo em outro arquivo da pasta `originais/`.
Entenda que o arquivo possui uma estrutura MD, ou seja, se a linha começa com  '##' é porque é um subcapítulo e isso deve ser mantido no arquivo traduzido.
Escreva por extenso toda e qualquer abreviação
Os números romanos devem ser traduzidos para arábicos, menos quando for nome de pessoa, como Luiz III que deve ser trocado por Luiz Terceiro.
---

## 1. Objetivo narrativo
- Produzir um texto em **pt-BR contemporâneo**, fluido e romanceado.
- **Não alterar fatos** nem a sequência de acontecimentos do original.
- **Expandir**: a reescrita precisa ser mais longa e detalhada que a linha correspondente no original.
- **Enriquecer descrições** sensoriais, atmosferas, emoções e pensamentos.
- **Clarificar diálogos**: indique sempre quem fala.
- **Evitar arcaísmos**; substitua termos antiquados por equivalentes modernos.
- Manter uma linha no destino para cada linha do arquivo original (mesma contagem).

Relembrando as diretrizes do pipeline (vide `AGENTS.md`):
1. Tradução fiel (Argos, se usar ferramenta automática).
2. Romanceador heurístico (amplia cadência, sem inventar fatos).
3. Modernizador pt-BR (ajustes lexicais).  
No fluxo manual que seguimos neste capítulo, a etapa 1 foi um entendimento humano direto; 2 e 3 foram cumpridas na escrita manual seguindo as orientações.

---

## 2. Preparação do ambiente
1. Trabalhe na raiz do projeto (`/Volumes/.../translate`).
2. Verifique o arquivo de origem, por exemplo:
   ```bash
   nl -ba originais/cap1.md | head
   wc -l originais/cap1.md
   ```
   O `wc -l` é obrigatório para saber o número exato de linhas a replicar.
3. Leia todo o texto para entender narrador, tom e personagens.
4. Anote trechos que exigem atenção (diálogos, imagens recorrentes, termos arcaicos).

---

## 3. Estratégia de reescrita
Siga as diretrizes abaixo para cada linha:

1. **Contextualize antes de reescrever.** Entenda quem fala, a que se refere e qual emoção está presente.
2. **Parafraseie** com linguagem atual e ritmo de romance moderno.
3. **Amplie** cada linha com detalhes coerentes: sensação física, percepção visual, reflexões internas.
4. **Marque diálogos** com falas diretas e identificação do falante (“disse John”, “perguntei”).
5. **Evite repetições mecânicas** do original; exponha as ideias com vocabulário variado.
6. **Proteja o sentido**: nada de fatos novos ou contradições.
7. **Consistência terminológica**: nomes em inglês permanecem (John, Jennie etc.).
8. **Modernize vocabulário** de imediato (troque “senão” por “do contrário”, “assegurar salas ancestrais” por “conseguir alugar um casarão antigo” etc.). Use `postprocess_map.json` como referência de preferências.

> Dica: escreva tudo em um buffer temporário (por exemplo, em um script Python) para garantir que a contagem de linhas bata com a do original antes de salvar.

---

## 4. Produção do arquivo de destino
1. Construa uma única string contendo todas as linhas já romanceadas.
2. Verifique a contagem:
   ```python
   from pathlib import Path
   texto = """linha 1
   linha 2
   ..."""
   assert len(texto.splitlines()) == NUM_LINHAS_ORIGINAL
   Path("final/capX-v2.md").write_text(texto + "\n", encoding="utf-8")
   ```
   Ajuste `NUM_LINHAS_ORIGINAL` e o caminho do arquivo conforme o capítulo.
3. Alternativa: use um editor com contagem explícita de linhas, mas sempre confirme com `wc -l final/capX-v2.md`.

---

## 5. Validação
1. Confirme contagem de linhas:
   ```bash
   wc -l originais/capX.md final/capX-v2.md
   ```
2. Faça inspeção manual com `sed`, `rg` ou `nl` para garantir que:
   - Não há linhas vazias indesejadas.
   - As falas estão atribuídas ao falante correto.
   - Não existem termos arcaicos ou inconsistências de concordância.
3. Revise pontos críticos:
   - Manter menção a “Jane” no final (é parte do original).
   - Evitar erros como “odiaLo” (corrigir para “odia-lo-ia” ou equivalente moderno) e outros resquícios de normalização.
4. Se alterar manualmente trechos após gerar o arquivo, rode novamente as verificações.

---

## 6. Checklist final
- [ ] Texto em pt-BR fluido e coerente.
- [ ] Expansão perceptível em cada linha.
- [ ] Nenhum fato alterado/inventado.
- [ ] Diálogos com indicação de quem fala.
- [ ] Vocabulário moderno (sem arcaísmos).
- [ ] Número de linhas idêntico ao original.
- [ ] Arquivo salvo em `final/` com sufixo `-v2`.
- [ ] Revisão manual dos trechos-chave (principalmente o clímax).

Após concluir, comunique o usuário informando:
1. Caminho do arquivo produzido.
2. Ferramentas/comandos de verificação utilizados.
3. Qualquer limitação ou sugestão de próximos passos (ex.: rodar diffs, modernizar outro capítulo).

Com este procedimento, qualquer instância do agente consegue repetir a produção romanceada line-by-line para outros capítulos, mantendo consistência estilística com `cap1-v2.md`.
