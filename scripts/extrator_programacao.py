#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extrator da programação do Mercado Livre Experience.

- Baixa a página principal para descobrir o chunk JS atual.
- Localiza o chunk que contém a programação.
- Extrai 24/SET e 25/SET diretamente do JavaScript.
- Gera data/programacao.json.
- Compatível com GitHub Actions e Python 3.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


SITE_URL = "https://mercadolivreexperience.mercadolivre.com.br/"
KNOWN_JS_URL = (
    "https://mercadolivreexperience.mercadolivre.com.br/"
    "_next/static/chunks/app/page-eba548846f7b2a93.js"
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "data" / "programacao.json"


def http_get(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Referer": SITE_URL,
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    request = Request(url, headers=headers)

    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def discover_js_urls():
    """
    Descobre os scripts referenciados pela página principal.
    O chunk atualmente conhecido é mantido como fallback.
    """
    urls = []

    try:
        html = http_get(SITE_URL)

        patterns = [
            r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']',
            r'["\']([^"\']+/_next/static/[^"\']+\.js)["\']',
        ]

        for pattern in patterns:
            for match in re.findall(pattern, html, flags=re.I):
                full_url = urljoin(SITE_URL, match)
                if full_url not in urls:
                    urls.append(full_url)

    except Exception as exc:
        print("Aviso: não foi possível ler a página principal: %s" % exc)

    # Fallback conhecido e também prioridade para o chunk que já contém a agenda.
    if KNOWN_JS_URL in urls:
        urls.remove(KNOWN_JS_URL)
    urls.insert(0, KNOWN_JS_URL)

    return urls


def extract_js_object(js):
    """
    Encontra o objeto:
        l={"24/SET":[...],"25/SET":[...]}
    sem executar o JavaScript.
    """
    match = re.search(r'\blet\s+n\s*=\s*\["24/SET","25/SET"\]\s*,\s*l\s*=\s*\{', js)

    if not match:
        # Fallback mais permissivo para mudanças pequenas na minificação.
        match = re.search(
            r'\["24/SET","25/SET"\].{0,200}?\bl\s*=\s*\{',
            js
        )

    if not match:
        raise ValueError("Objeto da programação não encontrado no JavaScript.")

    start = js.find("{", match.start())
    if start < 0:
        raise ValueError("Início do objeto da programação não encontrado.")

    level = 0
    in_string = False
    quote = ""
    escaped = False

    for i in range(start, len(js)):
        char = js[i]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                in_string = False
            continue

        if char in ('"', "'"):
            in_string = True
            quote = char
            continue

        if char == "{":
            level += 1
        elif char == "}":
            level -= 1
            if level == 0:
                return js[start:i + 1]

    raise ValueError("Objeto da programação não foi fechado corretamente.")


def js_object_to_python(js_object):
    """
    Converte o subconjunto de JavaScript usado pelo chunk em JSON.
    A agenda usa propriedades simples, strings, arrays e objetos.
    """
    # O JS do chunk usa escapes \xNN em textos acentuados.
    js_object = re.sub(
        r'\\x([0-9a-fA-F]{2})',
        lambda m: chr(int(m.group(1), 16)),
        js_object
    )

    # Converte propriedades sem aspas:
    # {hora:"12:20",titulo:"..."} -> {"hora":"12:20","titulo":"..."}
    js_object = re.sub(
        r'([,{])([A-Za-z_$][A-Za-z0-9_$-]*):',
        r'\1"\2":',
        js_object
    )

    try:
        return json.loads(js_object)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Não foi possível interpretar a estrutura da programação: %s"
            % exc
        )


def convert_date(day):
    dates = {
        "24/SET": "2026-09-24",
        "25/SET": "2026-09-25",
    }
    return dates.get(day, "")


def unique_companies(speakers):
    companies = []

    for speaker in speakers:
        company = speaker.get("empresa", "")
        if company and company not in companies:
            companies.append(company)

    return ", ".join(companies)


def normalize_speaker(speaker):
    return {
        "nome": speaker.get("nome", ""),
        "cargo": speaker.get("cargo", ""),
        "empresa": speaker.get("empresa", ""),
        "imagem": speaker.get("imagem", ""),
    }


def normalize_event(event, day, number):
    speakers = event.get("palestrantes", [])

    if not isinstance(speakers, list):
        speakers = []

    speakers = [normalize_speaker(s) for s in speakers]

    # No JS atual, bio_palestra é a descrição da palestra quando preenchida.
    description = event.get("bio_palestra", "")
    if not description:
        description = event.get("descricao", "")
    if not description:
        description = event.get("bio", "")

    tags = event.get("tags", [])
    if not isinstance(tags, list):
        tags = []

    return {
        "id": "mlxp-2026-%03d" % number,
        "data": convert_date(day),
        "hora_inicio": event.get("hora", ""),
        "hora_fim": "",
        "horario_original": event.get("hora", ""),
        "palco": event.get("palco", ""),
        "titulo": event.get("titulo", ""),
        "descricao": description,
        "empresa": unique_companies(speakers),
        "palestrantes": speakers,
        "tema": event.get("tema", ""),
        "tags": tags,
        "imagem": event.get("imagem", ""),
    }


def main():
    print("=" * 60)
    print("EXTRATOR MERCADO LIVRE EXPERIENCE")
    print("=" * 60)

    js = None
    source_url = None

    for url in discover_js_urls():
        print("Testando:", url)

        try:
            candidate = http_get(url)

            if '"24/SET"' in candidate and '"25/SET"' in candidate:
                js = candidate
                source_url = url
                break

        except Exception as exc:
            print("  Falhou:", exc)

    if js is None:
        print("ERRO: não encontrei um JavaScript contendo os dois dias.")
        sys.exit(1)

    print("Fonte encontrada:", source_url)
    print("Tamanho do JS:", len(js), "bytes")

    obj_text = extract_js_object(js)
    schedule = js_object_to_python(obj_text)

    if "24/SET" not in schedule or "25/SET" not in schedule:
        print("ERRO: o objeto não contém 24/SET e 25/SET.")
        sys.exit(1)

    output = []
    counter = 1

    for day in ("24/SET", "25/SET"):
        events = schedule[day]

        if not isinstance(events, list):
            print("ERRO: %s não é uma lista de eventos." % day)
            sys.exit(1)

        print("%s: %d eventos" % (day, len(events)))

        for event in events:
            output.append(normalize_event(event, day, counter))
            counter += 1

    if not output:
        print("ERRO: nenhum evento encontrado.")
        sys.exit(1)

    # Cria data/ caso ainda não exista.
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Grava primeiro em temporário e depois substitui o JSON.
    temp_file = OUTPUT_FILE.with_suffix(".json.tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )
        file.write("\n")

    temp_file.replace(OUTPUT_FILE)

    print()
    print("Total de eventos:", len(output))
    print("Arquivo atualizado:", OUTPUT_FILE)
    print("Concluído com sucesso.")


if __name__ == "__main__":
    main()
