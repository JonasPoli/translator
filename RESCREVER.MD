# Reescrita romanceada local

## Comando
- Executável: `python3 reescrever.py`
- Exemplo utilizado: `python3 reescrever.py --in Reescrever/original.md --out Reescrever/gerado.md`
- Parâmetros adicionais:
  - `--temp-dir`: pasta onde as seções fatiadas (`##` por arquivo) são guardadas. Padrão: `Reescrever/_tmp_sections`.

## O que o comando faz
- Divide o Markdown de origem em arquivos menores, um por subtítulo iniciado por `##`.
- Reescreve cada bloco expandindo a prosa com vocabulário contemporâneo, mantendo os fatos.
- Adota o tom de um “outro tradutor”, reforçando que o texto é uma segunda versão moderna.
- Converte abreviações, siglas e algarismos romanos para formas por extenso.
- Mostra barra de progresso (`tqdm`) acompanhando as seções processadas.
- Recombina o material em `Reescrever/gerado.md`, maior e mais detalhado que o original.

## Pré-requisitos
- Python 3 instalado com as dependências já presentes no projeto (`romanceador_ptbr.py`).
- Ambiente offline (não usa API externa).

## Fluxo recomendado
1. Garantir que `Reescrever/original.md` esteja atualizado.
2. Executar o comando indicado acima.
3. Conferir `Reescrever/_tmp_sections/` se precisar revisar alguma parte isolada.
4. Revisar o resultado final em `Reescrever/gerado.md`.
5. Substituir ou versionar o arquivo gerado conforme necessário.

## Uso com OpenAI (opcional)
1. Criar uma conta em [platform.openai.com](https://platform.openai.com/) e gerar uma **API key**.
2. Instalar a biblioteca oficial: `pip install openai`.
3. Copiar `openai_config.json.example` para `openai_config.json` e preencher `api_key` (opcionalmente `base_url`).
4. Rodar o comando ativando a API:
   ```bash
   python3 reescrever.py --in Reescrever/original.md --out Reescrever/gerado.md --use-openai --openai-model gpt-4o-mini
   ```
   - `--openai-model` permite trocar o modelo (ex.: `gpt-4o`, `gpt-4.1-mini`, etc.).
   - O script chama a API para cada trecho, garantindo fidelidade e prosa natural; se a resposta vier com fatos novos, ele volta automaticamente ao modo heurístico.
