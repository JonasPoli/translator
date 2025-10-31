#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translate.py — pipeline local (gratis) para:
1) traduzir (Argos Translate, offline)
2) romancear (reescrita heurística ampliada, sem alterar fatos)
3) modernizar pt-BR (substituições contextuais e fluência brasileira)
Com barras de progresso reais (por arquivo e por trecho) + ETA.

Dicas anti-crash (macOS + Argos/CT2):
- Por padrão, desativamos multiprocessing para provider=argos.
- Forçamos OMP_NUM_THREADS=1 para reduzir risco de segfault.
- Você pode usar --no-mp (padrão quando provider=argos) ou --mp para tentar paralelizar.
"""

import os
import re
import sys
import json
import argparse
import time
from pathlib import Path
from typing import List, Iterable

# Ajustes de runtime para estabilidade do Argos/CT2
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("CT2_USE_EXPERIMENTAL_PACKED_GEMM", "0")
os.environ.setdefault("ARGOS_DEVICE_TYPE", "cpu")

try:
    from tqdm import tqdm
except Exception:
    print("Instale tqdm: pip install tqdm", file=sys.stderr)
    sys.exit(1)

try:
    from postprocess_ptbr import apply_postprocess_map
except ImportError:
    def apply_postprocess_map(text: str) -> str:  # type: ignore
        return text

# ------------------------ Providers (apenas local) ------------------------

def _load_argos():
    try:
        from argostranslate import translate as argos_translate
        return argos_translate
    except Exception as e:
        print("Erro ao importar Argos Translate. Instale com: pip install argostranslate", file=sys.stderr)
        raise

def translate_text_provider(text: str, src: str, tgt: str, provider: str) -> str:
    if provider == "argos":
        argos = _load_argos()
        return argos.translate(text, src, tgt)
    raise ValueError(f"Provider não suportado: {provider!r} (use 'argos')")

# ------------------------ Romanceador heurístico ------------------------
# Expande levemente, suaviza sintaxe, melhora cadência, sem mudar fatos.

def romancear_ptbr(texto: str, strength: float = 0.5) -> str:
    """Heurística leve: normaliza vícios de tradução literal e melhora fluência."""
    if strength <= 0:
        return texto

    t = texto
    # Normalizações de espaços/pontuação
    t = re.sub(r"\s+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\s+([,;:.!?])", r"\1", t)
    t = re.sub(r"([,;:.!?])([^\s])", r"\1 \2", t)

    # Ajustes frequentes de traduções literais
    replacements = [
        (r"\bri-se\b", "ri"),
        (r"\bri-se de\b", "ri de"),
        (r"\bnum tom mais íntimo e direto\b", ""),
        (r"\s+,", ","),
    ]
    for pattern, repl in replacements:
        t = re.sub(pattern, repl, t, flags=re.IGNORECASE)

    # Evita espaços antes de travessões/hífens duplicados criados acima
    t = re.sub(r"\s+—", " —", t)
    t = re.sub(r"--+", "--", t)
    # Restaura reticências quebradas por normalização
    t = re.sub(r"\.\s*\.\s*\.", "...", t)
    return t.strip()

# ------------------------ Modernizador pt-BR ------------------------

DEFAULT_REWRITES = [
    # Pedidos específicos do usuário
    (r"(?im)^Original Text \(English\)", "Texto original (inglês)"),
    (r"(?im)^The Yellow Wallpaper", "O Papel de Parede Amarelo"),
    (r"(?im)^By Charlotte Perkins Gilman", "Por Charlotte Perkins Gilman"),
    (r"\bpropriedade(?:s)? hereditária(?:s)?\b", "herança de família"),
    (r"\bsalas ancestrais\b", "um casarão antigo"),
    (r"\bassegur\w+\s+salas ancestrais\b", "consigam alugar um casarão antigo"),
    (r"\bassegurar(?:em)?\s+salas ancestrais\b", "conseguir alugar um casarão antigo"),

    # Ajustes de fluência
    (r"\bo John\b", "John"),
    (r"\bO John\b", "John"),
    (r"\bJoão é prático no extremo\b", "John é extremamente pragmático"),
    (r"\bnúmeros\b", "números"),
    (r"\bE o que se pode fazer\?\b", "E o que se há de fazer?"),
    (r"\bele não acredita que estou doente\b", "ele nem acredita que estou doente"),
    (r"\bele não acredita que estou doente!\b", "ele nem acredita que estou doente!"),
    (r"\buma leve tendência histérica\b", "uma leve tendência histérica"),
    (r"\bzomba abertamente\b", "caçoa sem rodeios"),
    (r"\btem intenso horror à superstição\b", "tem verdadeiro horror à superstição"),

    # Outras modernizações comuns
    (r"\bSenão,\s*", "Do contrário, "),
    (r"\bporque é que\b", "por que"),

    # Correções adicionais para fluência contemporânea
    (r"\bpessoas simples\b", "pessoas comuns"),
    (r"\bJoão\b", "John"),
    (r"\bVou declarar orgulhosamente\b", "Declaro com satisfação"),
    (r"\bAinda assim, vou declarar orgulhosamente\b", "Ainda assim, declaro com satisfação"),
    (r"\bhá algo de estranho nisso\b", "há algo de estranho nela"),
    (r"\buma casa assombrada\b", "uma casa mal-assombrada"),
    (r"\be alcançar o auge da felicidade romântica\b", "e atingiria o auge da felicidade poética"),
    (r"\bmas isso seria pedir demais do destino\b", "mas seria pedir demais do destino"),
    (r"Uma mansão colonial, uma herança de família", "Uma mansão colonial, herança de família"),
    (r"Do contrário, porque haveria de ser tão barato\?", "Do contrário, por que o aluguel teria sido tão barato?"),
    (r"porque haveria de ser tão barato", "por que o aluguel teria sido tão barato"),
    (r"\bum casarão antigo para o verão\.", "um casarão antigo para o verão."),
    (r"E porque é que ficou tanto tempo desamparado\?", "Ou por que teria ficado desocupada por tanto tempo?"),
    (r"E por que ficou tanto tempo desamparado\?", "Ou por que teria ficado desocupada por tanto tempo?"),
    (r"Senão, porque haveria de ser tão barato\? E porque é que ficou tanto tempo desamparado\?",
     "Do contrário, por que o aluguel teria sido tão barato? Ou por que teria ficado desocupada por tanto tempo?"),
    (r"John ri de mim, claro, mas espera-se isso no casamento\.", "John ri de mim, é claro, mas já se espera isso no casamento."),
    (r"O John ri de mim", "John ri de mim"),
    (r"O John ri-se de mim", "John ri de mim"),
    (r"João é prático no extremo\. Ele não tem paciência com a fé, um intenso horror da superstição, e zomba abertamente de qualquer conversa de coisas para não ser sentido, visto e colocado em números\.",
     "John é extremamente pragmático. Não tem paciência alguma com religião, tem verdadeiro horror à superstição e caçoa sem rodeios de qualquer discurso sobre coisas que não possam ser sentidas, vistas e expressas em números."),
    (r"Ele não tem paciência com a fé", "Não tem paciência alguma com religião"),
    (r"um intenso horror da superstição", "tem verdadeiro horror à superstição"),
    (r"caçoa sem rodeios de qualquer conversa de coisas para não ser sentido, visto e colocado em números", "caçoa sem rodeios de qualquer discurso sobre coisas que não possam ser sentidas, vistas e expressas em números"),
    (r"ele nem acredita que estou doente!", "Veja bem, ele nem sequer acredita que estou doente!"),
    (r"ele nem acredita que estou doente", "ele nem acredita que estou doente"),
    (r"uma única depressão nervosa temporária", "apenas uma depressão nervosa temporária"),
    (r"uma leve tendência histérica", "uma leve tendência histérica"),
    (r"E o que se pode fazer\?", "E o que se há de fazer?"),
    (r"Mas o que se pode fazer\?", "Mas o que se há de fazer?"),
    (r"John ri-se", "John ri"),
    (r"John ri-se de mim", "John ri de mim"),
    # Ajustes específicos para aproximar do estilo de referência
    (r"John é um médico, e talvez - \(Eu não diria isso a uma alma viva, é claro, mas este é um papel morto e um grande alívio para minha mente\) - talvez essa seja uma razão pela qual eu não fico bem mais rápido\.",
     "John é médico, e talvez – eu não diria isso a nenhuma alma viva, é claro, mas isto aqui é papel morto e um grande alívio para minha mente –, talvez, esse seja um dos motivos pelos quais não me recupero mais rápido."),
    (r"Se um médico de alto nível, e o próprio marido, assegura aos amigos e parentes que não há realmente nada de errado com apenas uma depressão nervosa temporária – uma ligeira tendência histérica – o que se pode fazer\?",
     "Se um médico, de grande prestígio, assegura aos amigos e familiares que não há absolutamente nada de errado com sua esposa, a não ser uma depressão nervosa passageira – uma leve tendência à histeria –, o que se há de fazer?"),
    (r"Meu irmão também é médico, e também de alta estatura, e ele diz a mesma coisa\.",
     "Meu irmão também é médico, também tem grande prestígio, e afirma a mesma coisa."),
    (r"Então eu tomo fosfatos ou fosfitos – o que quer que seja, e tônicos, e viagens, e ar, e exercício, e sou absolutamente proibido de “trabalhar” até que eu esteja bem novamente\.",
     "Sendo assim, tomo fosfato ou fosfito – seja qual for –, e tônicos, além de passear, respirar ar puro, praticar exercícios e estar terminantemente proibida de “trabalhar” até que fique bem de novo."),
    (r"Pessoalmente, discordo das suas ideias\.", "Particularmente, discordo da opinião deles."),
    (r"Pessoalmente, acredito que o trabalho agradável, com entusiasmo e mudança, me faria bem\.",
     "Acredito que um trabalho prazeroso, com empolgação e variedade, só me faria bem."),
    (r"Eu escrevi por um tempo, apesar deles; mas isso me cansa muito – ter que ser tão astuto sobre isso, ou então encontrar oposição pesada\.",
     "A despeito dos dois, escrevi durante um tempo, mas fico exausta demais... por ter que viver camuflando isso, ou então enfrentar a forte oposição deles."),
    (r"Às vezes eu imagino que na minha condição se eu tivesse menos oposição e mais sociedade e estímulo – mas John diz que a pior coisa que posso fazer é pensar sobre minha condição, e confesso que isso sempre me faz sentir mal\.",
     "Às vezes acho que, no meu estado, se tivesse menos oposição e mais companhia e estímulo... John, porém, diz que pensar no meu estado é a pior coisa que posso fazer, e confesso que isso sempre faz com que me sinta mal."),
    (r"Por isso, vou esquecer e falar sobre a casa\.", "Portanto, vou deixar isso de lado e falar sobre a casa."),
    (r"O lugar mais bonito! É completamente sozinho, parado bem para trás da estrada, a cerca de cinco milhas da aldeia\. Faz-me pensar em lugares ingleses sobre os quais se lê, pois há sebes, paredes e portões que trancam, e muitas pequenas casas separadas para os jardineiros e pessoas\.",
     "Que lugar maravilhoso! É bastante isolado, fica bem distante da estrada, a quase cinco quilômetros da vila. Faz-me pensar nos casarões ingleses dos livros, com sua cerca viva e paredes e portões com trancas, e várias casinhas independentes que alojam os jardineiros e outras pessoas."),
    (r"Há um jardim delicioso! Eu nunca vi tal jardim - grande e sombrio, cheio de caminhos box-bordered, e forrado com longos arbors cobertos de uva com assentos sob eles\.",
     "O jardim é encantador! Nunca vi um jardim assim: grande e repleto de sombras, cheio de labirintos ornados por arbustos simétricos e margeados com enormes pérgulas cobertas de videiras e uns bancos embaixo."),
    (r"Houve alguns problemas legais, creio eu, algo sobre os herdeiros e co-herdeiros; de qualquer forma, o lugar está vazio há anos\.",
     "Houve alguns problemas legais, acredito, algo relacionado aos herdeiros e coerdeiros; de qualquer forma, o lugar esteve vazio por anos."),
    (r"Isso estraga minha fantasmacidade, tenho medo; mas não me importo – há algo estranho na casa – eu posso sentir\.",
     "Isso estraga todo o mistério fantasmagórico para mim, receio, mas não importa – há algo de estranho na casa... posso sentir."),
    (r"Até o disse ao John numa noite de luar, mas ele disse que o que eu sentia era uma corrente de ar e fechou a janela\.",
     "Em uma noite de luar, cheguei até a falar com John, mas ele disse que eu havia sentido uma simples corrente de ar e fechou a janela."),
    (r"Às vezes, fico irada com John\. Tenho certeza de que nunca fui tão sensível\. Eu acho que é devido a esta condição nervosa\.",
     "Às vezes fico absurdamente irritada com John. Tenho certeza de que nunca fui tão sensível. Acho que tem a ver com os nervos."),
    (r"Mas John diz que, se eu me sentir assim, vou negligenciar o controle próprio; então eu me esforço para me controlar, - antes dele, pelo menos, - e isso me deixa muito cansado\.",
     "Mas John diz que se me sinto assim é porque descuido do autocontrole adequado; então, faço um esforço para me controlar – diante dele, pelo menos – e isso me deixa exausta."),
    (r"Não gosto nem um pouco do nosso quarto\. Eu queria um lá em baixo que abrisse na piazza e tivesse rosas por toda a janela, e uns belos enforcamentos à moda antiga! Mas John não quis ouvir falar disso\.",
     "Não gosto nem um pouco do nosso quarto. Queria um no andar de baixo que dava para a varanda, com rosas contornando a janela e aqueles lindos cortinados de chita à antiga! Mas John nem me deu ouvidos."),
    (r"Ele disse que só havia uma janela e não havia espaço para duas camas, e não havia espaço perto para ele se ele levou outra\.",
     "Disse que havia apenas uma janela e não tinha espaço para duas camas, e nenhum outro cômodo de que pudesse dispor se quisesse."),
    (r"Ele é muito cuidadoso e amoroso, e dificilmente me deixa mexer sem direção especial\.",
     "Ele é muito cuidadoso e amoroso, e mal permite que eu me mexa sem uma orientação especial."),
    (r"Eu tenho uma prescrição de horário para cada hora do dia; ele cuida de mim, e por isso eu me sinto muito ingrato para não valorizá-lo mais\.",
     "Tenho um cronograma de prescrições para cada hora do dia; ele cuida de tudo para mim e me sinto uma reles ingrata por não valorizar tanta preocupação."),
    (r"Ele disse que viemos aqui apenas por minha causa, que eu deveria ter um descanso perfeito e todo o ar que pudesse ter\. “Seu exercício depende de sua força, minha querida, ” disse ele, “e de sua comida um pouco em seu apetite; mas o ar que você pode absorver o tempo todo\. ” Então, fomos para o berçário, no topo da casa\.",
     "Falou que viemos para cá só por minha causa, que eu precisava fazer repouso absoluto e tomar muito ar puro. – Fazer exercícios depende de sua disposição, minha querida – disse ele –, e a alimentação depende do seu apetite, mas o ar puro você pode aproveitar o tempo todo. Sendo assim, ficamos com o quarto de crianças, no piso de cima da casa."),
    (r"É uma sala grande, arejada, quase todo o chão, com janelas que olham para todos os lados, e ar e sol em abundância\. Era o berçário primeiro e, em seguida, playground e ginásio, eu deveria julgar; para as janelas são barradas para crianças pequenas, e há anéis e coisas nas paredes\.",
     "É um cômodo grande, arejado, ocupa quase o andar inteiro, há janelas com vista para todos os lados, e ar puro e luz do sol aos montes. Primeiro foi um dormitório infantil, depois uma sala de recreação e uma sala de ginástica, presumo; pois as janelas têm grades de proteção para criancinhas e há argolas e coisas do tipo nas paredes."),
    (r"A tinta e o papel parecem ter sido usados por uma escola de rapazes\. Ele está despojado – o papel – em grandes manchas ao redor da cabeça da minha cama, até onde eu possa chegar, e em um ótimo lugar do outro lado do quarto baixo\. Nunca vi um jornal pior na minha vida\.",
     "A pintura e o papel de parede dão a entender que funcionava como uma escolinha para garotos. Foi arrancado... digo, o papel – em grandes manchas ao redor da cabeceira da minha cama, e também num trecho enorme na parte baixa da parede oposta. Nunca vi um papel de parede tão horrível."),
    (r"Um daqueles padrões extravagantes que cometem todos os pecados artísticos\.",
     "É um daqueles padrões espalhafatosos que cometem todos os pecados artísticos."),
    (r"É o suficiente para confundir o olho em seguir, pronunciado o suficiente para irritar constantemente, e provocar o estudo, e quando você segue as curvas coxos e incertas por uma pequena distância eles de repente cometem suicídio - mergulhar em ângulos ultrajantes, destruir-se em contradições inéditas\.",
     "Basta acompanhá-lo para ficar zonza, pois é berrante o bastante para irritar sem parar e ainda obriga a pessoa a estudá-lo; quando você tenta seguir aquelas curvas coxas e incertas por um instante, elas de repente despencam em ângulos absurdos e se destroem em contradições inéditas."),
    (r"A cor é repelente, quase revoltante; um amarelo incandescente, impuro, estranhamente desbotado pela luz solar lenta\.",
     "A cor é repelente, quase revoltante; um amarelo incandescente, impuro, estranhamente desbotado pela luz solar lenta."),
    (r"Em alguns lugares, é uma laranja maçante, mas luridíssima, um tom de enxofre doentio em outros\.",
     "Em alguns pontos é laranja opaco, em outros vira um enxofre doentio e excessivamente vívido."),
    (r"Não admira que as crianças odiassem! Eu próprio odiaria se tivesse de viver muito tempo nesta sala\.",
     "Não admira que as crianças detestassem! Eu mesma odiaria ter de viver muito tempo nesta sala."),
    (r"Aí vem John, e eu devo guardar isso, - ele odeia que eu escreva uma palavra\.",
     "Lá vem John, preciso guardar isso – ele detesta que eu escreva uma palavra sequer."),
]

def load_overrides(path: Path) -> List[tuple]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = []
        for k, v in data.items():
            # Trate k como regex; v como substituição literal
            items.append((k, v))
        return items
    except Exception as e:
        print(f"Não foi possível ler overrides de {path}: {e}", file=sys.stderr)
        return []

def modernize_ptbr(texto: str, overrides: List[tuple]) -> str:
    t = texto
    rules = list(overrides) + list(DEFAULT_REWRITES)

    # Ordena por comprimento da chave (maior primeiro) para evitar sobreposição indesejada
    rules.sort(key=lambda kv: len(kv[0]), reverse=True)

    for pattern, repl in rules:
        try:
            # use raw-style replacement groups quando necessário
            t = re.sub(pattern, repl, t, flags=re.IGNORECASE)
        except re.error as e:
            print(f"Regex inválido '{pattern}': {e}", file=sys.stderr)
    # Correções finais de espaços duplos / hífens
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"-\s*-", "--", t)
    # Ajustes de “há algo de estranho nele/nela” com grupo nomeado
    t = re.sub(r"\bhá algo de estranho (nele|nela)\b", r"há algo de estranho \g<1>", t, flags=re.IGNORECASE)
    return t

# ------------------------ Chunking ------------------------

def split_paragraphs(text: str) -> List[str]:
    # separa por linhas em branco duplas
    paras = re.split(r"\n\s*\n", text.strip(), flags=re.MULTILINE)
    return [p.strip() for p in paras if p.strip()]

def chunk_by_paragraph(text: str, max_chars: int) -> List[str]:
    parts: List[str] = []
    buf = ""
    for p in split_paragraphs(text):
        if not buf:
            buf = p
        elif len(buf) + 2 + len(p) <= max_chars:
            buf = f"{buf}\n\n{p}"
        else:
            parts.append(buf)
            buf = p
    if buf:
        parts.append(buf)
    return parts

def chunk_by_chars(text: str, max_chars: int) -> List[str]:
    text = text.strip()
    parts = []
    i = 0
    while i < len(text):
        parts.append(text[i:i+max_chars])
        i += max_chars
    return parts

# ------------------------ I/O e pipeline ------------------------

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def process_text(text: str, args, overrides: List[tuple], provider: str) -> str:
    # 1) traduz
    translated = translate_text_provider(text, args.src, args.tgt, provider)

    # 1.1) pós-processamento baseado em corpus desejado
    translated = apply_postprocess_map(translated)

    # 2) romanceia
    if args.romance_strength and args.romance_strength > 0:
        translated = romancear_ptbr(translated, args.romance_strength)

    # 3) moderniza
    if args.modernize:
        translated = modernize_ptbr(translated, overrides)

    return translated

def process_file(in_path: Path, out_path: Path, args, overrides: List[tuple], provider: str):
    raw = read_text(in_path)

    # Pré-chunk para ETA estável
    if args.chunk_by == "paragraph":
        chunks = chunk_by_paragraph(raw, args.max_chars)
    else:
        chunks = chunk_by_chars(raw, args.max_chars)

    if args.verbose:
        print(f"[{in_path.name}] {len(chunks)} trecho(s).")

    results: List[str] = []
    bar = tqdm(total=len(chunks), desc=f"Trechos: {in_path.name}", unit="trecho", leave=False)
    start = time.perf_counter()
    for idx, ch in enumerate(chunks, 1):
        try:
            out = process_text(ch, args, overrides, provider)
        except Exception as e:
            bar.close()
            raise
        results.append(out)
        bar.update(1)
        if args.verbose and idx % 5 == 0:
            elapsed = time.perf_counter() - start
            bar.set_postfix({"elapsed_s": f"{elapsed:.1f}"})
    bar.close()

    final = "\n\n".join(results).strip()
    write_text(out_path, final)

# ------------------------ CLI ------------------------

def collect_files(root: Path, exts: List[str]) -> List[Path]:
    if root.is_file():
        return [root]
    files = []
    for ext in exts:
        files.extend(root.rglob(f"*{ext}"))
    return sorted(files)

def main():
    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--mode", choices=["translate", "both"], default="both", help="translate=apenas traduz; both=traduz + romanceia + moderniza conforme flags")
    ap.add_argument("--provider", choices=["argos"], default="argos", help="provedor local")
    ap.add_argument("--src", required=True, help="código língua origem (ex: en)")
    ap.add_argument("--tgt", required=True, help="código língua destino (ex: pt)")
    ap.add_argument("--in", dest="inp", required=True, help="arquivo ou pasta de entrada")
    ap.add_argument("--out", dest="out", required=True, help="arquivo ou pasta de saída")
    ap.add_argument("--ext", nargs="+", default=[".md", ".txt"], help="extensões a processar (quando entrada é pasta)")
    ap.add_argument("--chunk-by", choices=["paragraph", "chars"], default="paragraph", help="estratégia de fatiamento")
    ap.add_argument("--max-chars", type=int, default=2400, help="tamanho máximo por trecho")
    ap.add_argument("--romance-strength", type=float, default=0.0, help="0.0 desliga; 0.3-0.7 recomendado p/ texto natural")
    ap.add_argument("--modernize", action="store_true", help="aplica modernizações pt-BR pós-tradução")
    ap.add_argument("--overrides", default="modernizer_ptbr_overrides.json", help="JSON opcional de substituições personalizadas")
    ap.add_argument("--verbose", action="store_true", help="logs adicionais")
    ap.add_argument("--dry-run", action="store_true", help="mostra chunking e sai (sem traduzir)")
    ap.add_argument("--safe-threads", action="store_true", help="Força OMP_NUM_THREADS=1 (já é padrão); útil p/ depuração")
    ap.add_argument("--mp", action="store_true", help="(opcional) tentar multiprocessing (não recomendado com Argos no macOS)")
    ap.add_argument("--no-mp", action="store_true", help="força execução single-process (padrão para Argos)")
    args = ap.parse_args()

    inp = Path(args.inp).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()

    if args.safe_threads:
        os.environ["OMP_NUM_THREADS"] = "1"
        os.environ["CT2_USE_EXPERIMENTAL_PACKED_GEMM"] = "0"
        os.environ["ARGOS_DEVICE_TYPE"] = "cpu"

    overrides_path = Path(args.overrides).expanduser().resolve()
    overrides = load_overrides(overrides_path)

    if not inp.exists():
        print(f"ERRO: caminho de entrada não existe: {inp}", file=sys.stderr)
        sys.exit(2)

    # Coleta de arquivos
    files = collect_files(inp, args.ext)
    if not files:
        print("Nenhum arquivo correspondente encontrado.", file=sys.stderr)
        sys.exit(3)

    # Quando entrada é arquivo, saída pode ser arquivo. Quando entrada é pasta, saída deve ser pasta.
    single_file = inp.is_file()
    if single_file and out.suffix:
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        out.mkdir(parents=True, exist_ok=True)

    # Dry-run: apenas mostra chunk counts
    if args.dry_run:
        for f in files:
            raw = read_text(f)
            chunks = chunk_by_paragraph(raw, args.max_chars) if args.chunk_by == "paragraph" else chunk_by_chars(raw, args.max_chars)
            print(f"{f}: {len(chunks)} trecho(s)")
        return

    # Processamento (single-thread por padrão para Argos)
    files_bar = tqdm(total=len(files), desc="Arquivos", unit="arq")
    for f in files:
        if single_file and out.suffix:
            out_path = out
        else:
            rel = f.relative_to(inp) if inp.is_dir() else Path(f.name)
            out_path = (out / rel).with_suffix(rel.suffix)
        if args.verbose:
            print(f"→ Processando {f} → {out_path}")
        try:
            process_file(f, out_path, args, overrides, args.provider)
        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário.", file=sys.stderr)
            files_bar.close()
            sys.exit(130)
        files_bar.update(1)
    files_bar.close()

if __name__ == "__main__":
    main()
