# Guia do Tradutor

Este repositório mantém a tradução romanceada de `cap2.md` em blocos contínuos. Siga estas instruções para retomar o trabalho sem perder o contexto.

## 1. Arquivos Principais

- `cap2.md`: texto-fonte original (inglês).
- `traduzido.md`: versão expandida em português.
- `CONTROLE_TRADUCAO.md`: registro do progresso (linhas cobertas, notas e próximos passos).

## 2. Como Usar o Arquivo de Controle

1. Consulte a tabela em `CONTROLE_TRADUCAO.md` para saber até onde a tradução avançou. Os intervalos de linhas indicam exatamente o que já está completo.
2. Antes de continuar, confirme o próximo intervalo executando, por exemplo, `nl -ba cap2.md | sed -n '108,180p'` (ajuste os números conforme necessário).
3. Após traduzir um novo trecho, adicione uma linha na tabela com:
   - Identificação do trecho (capítulo, parágrafos-chave).
   - Intervalo de linhas em `cap2.md`.
   - Intervalo de linhas correspondente adicionado em `traduzido.md`.
   - Observações relevantes (pendências, decisões de estilo, dúvidas a resolver).
4. Se precisar interromper o trabalho, registre a linha exata do original onde parou na seção “Próximo Passo” ou nas observações.

## 3. Passo a Passo para Traduzir

1. **Selecionar o bloco**: use os cabeçalhos `##` do original como guia. Trabalhe em seções curtas para facilitar revisões.
2. **Manter a estrutura Markdown**: preserve títulos (`##`), listas, citações e itálicos. Ajuste apenas o texto corrido.
3. **Expandir e modernizar**:
   - Reescreva em português contemporâneo, com tom narrativo envolvente.
   - Acrescente descrições sensoriais, emoções e pensamentos, sem alterar eventos ou a ordem dos fatos.
   - Esclareça diálogos indicando quem fala.
4. **Regras específicas**:
   - Escreva abreviações por extenso (ex.: “Sr.” → “Senhor”).
   - Converta números romanos para arábicos, exceto em nomes de pessoas (ex.: “Luiz Terceiro”).
   - Substitua termos arcaicos por equivalentes modernos.
5. **Revisar**:
   - Garanta coerência entre termos originais e tradução (nomes próprios, locais, objetos).
   - Leia em voz alta (ou mentalmente) para checar fluidez.
6. **Registrar o avanço**:
   - Acrescente o texto ao final de `traduzido.md`.
   - Atualize `CONTROLE_TRADUCAO.md`.
   - (Opcional) Anote a contagem de palavras (`wc -w traduzido.md`) para monitorar o crescimento.

## 4. Retomada em Caso de Interrupção

- Caso a sessão seja encerrada ou os créditos acabem, abra `CONTROLE_TRADUCAO.md` na próxima oportunidade e verifique o último item concluído e o “Próximo Passo”.
- Aproveite a nota de linha exata para retomar do ponto correto sem reler todo o texto.
- Se o trabalho foi interrompido no meio de um parágrafo, inclua uma observação no controle indicando a frase final já coberta.

## 5. Dúvidas ou Ajustes

- Se surgir incerteza terminológica, descreva a dúvida em `CONTROLE_TRADUCAO.md` na coluna de observações para resolução futura.
- Prefira manter vocabulário consistente; quando precisar variar, faça anotações rápidas no controle para justificar a escolha.

Seguindo estes passos, qualquer colaborador poderá continuar a tradução de forma coerente e eficiente. Bons trabalhos!***
