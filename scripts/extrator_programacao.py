#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

SITE_URL = "https://mercadolivreexperience.mercadolivre.com.br/"
KNOWN_JS_URL = "https://mercadolivreexperience.mercadolivre.com.br/_next/static/chunks/app/page-eba548846f7b2a93.js"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "data" / "programacao.json"


def http_get(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Referer": SITE_URL,
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    with urlopen(Request(url, headers=headers), timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def discover_js_urls():
    urls = []
    html = http_get(SITE_URL)

    # Extrai os scripts atuais do HTML. Isso evita depender do hash antigo do Next.js.
    for match in re.findall(r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']', html, flags=re.I):
        full = urljoin(SITE_URL, match)
        if full not in urls:
            urls.append(full)

    # O chunk conhecido fica como fallback, caso o site mude temporariamente.
    if KNOWN_JS_URL not in urls:
        urls.append(KNOWN_JS_URL)
    return urls


def extract_balanced_object(js, start):
    level = 0
    in_string = False
    quote = ""
    escaped = False
    in_line_comment = False
    in_block_comment = False

    for i in range(start, len(js)):
        c = js[i]
        n = js[i + 1] if i + 1 < len(js) else ""

        if in_line_comment:
            if c == "\n":
                in_line_comment = False
            continue

        if in_block_comment:
            if c == "*" and n == "/":
                in_block_comment = False
            continue

        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == quote:
                in_string = False
            continue

        if c == "/" and n == "/":
            in_line_comment = True
            continue
        if c == "/" and n == "*":
            in_block_comment = True
            continue

        if c in ('"', "'", "`"):
            in_string = True
            quote = c
            continue

        if c == "{":
            level += 1
        elif c == "}":
            level -= 1
            if level == 0:
                return js[start:i + 1]

    return None


def js_object_to_python(text):
    # Escapes hexadecimais usados pela minificação.
    text = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), text)

    # Propriedades sem aspas: {hora:"12:20"} -> {"hora":"12:20"}
    text = re.sub(r'([,{])\s*([A-Za-z_$][A-Za-z0-9_$-]*)\s*:', r'\1"\2":', text)

    # Valores JS simples.
    text = re.sub(r'\bundefined\b', 'null', text)
    text = re.sub(r'\bNaN\b', 'null', text)

    # Vírgulas finais permitidas pelo JavaScript.
    text = re.sub(r',\s*([}\]])', r'\1', text)

    return json.loads(text)


def extract_schedule_object(js):
    """
    Não depende mais de `let n=[...] ,l={...}`.
    Procura qualquer objeto que contenha simultaneamente 24/SET e 25/SET.
    Isso torna o extrator resistente às mudanças de minificação/nome de variável.
    """
    date_patterns = ['"24/SET"', "'24/SET'", '"25/SET"', "'25/SET'"]

    positions = []
    for pattern in date_patterns:
        start = 0
        while True:
            pos = js.find(pattern, start)
            if pos < 0:
                break
            positions.append(pos)
            start = pos + len(pattern)

    positions = sorted(set(positions))
    if not positions:
        raise ValueError("As datas 24/SET e 25/SET não foram encontradas no JavaScript.")

    # Para cada ocorrência, tenta objetos iniciados antes dela.
    for pos in positions:
        cursor = pos
        minimum = max(0, pos - 30000)
        attempts = 0

        while cursor >= minimum and attempts < 1000:
            cursor = js.rfind("{", minimum, cursor + 1)
            if cursor < 0:
                break
            attempts += 1

            obj = extract_balanced_object(js, cursor)
            if not obj:
                continue

            # Evita tentar converter objetos gigantes que claramente não são a agenda.
            if '"24/SET"' not in obj and "'24/SET'" not in obj:
                continue
            if '"25/SET"' not in obj and "'25/SET'" not in obj:
                continue

            try:
                data = js_object_to_python(obj)
            except Exception:
                continue

            if isinstance(data, dict) and isinstance(data.get("24/SET"), list) and isinstance(data.get("25/SET"), list):
                return data

    raise ValueError("Não foi possível interpretar o objeto da programação no JavaScript atual.")


def convert_date(day):
    return {"24/SET": "2026-09-24", "25/SET": "2026-09-25"}.get(day, "")


def normalize_speaker(speaker):
    if not isinstance(speaker, dict):
        return {"nome": "", "cargo": "", "empresa": "", "imagem": ""}
    return {
        "nome": speaker.get("nome", ""),
        "cargo": speaker.get("cargo", ""),
        "empresa": speaker.get("empresa", ""),
        "imagem": speaker.get("imagem", ""),
    }


def normalize_event(event, day, number):
    if not isinstance(event, dict):
        event = {}
    speakers = event.get("palestrantes", [])
    if not isinstance(speakers, list):
        speakers = []
    speakers = [normalize_speaker(s) for s in speakers]

    companies = []
    for speaker in speakers:
        company = speaker.get("empresa", "")
        if company and company not in companies:
            companies.append(company)

    description = event.get("bio_palestra", "") or event.get("descricao", "") or event.get("bio", "")
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
        "empresa": ", ".join(companies),
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
            # O chunk correto deve conter os dois dias.
            if "24/SET" in candidate and "25/SET" in candidate:
                js = candidate
                source_url = url
                break
        except Exception as exc:
            print("  Falhou:", exc)

    if js is None:
        raise RuntimeError("Não encontrei um JavaScript contendo 24/SET e 25/SET.")

    print("Fonte encontrada:", source_url)
    print("Tamanho do JS:", len(js), "bytes")

    schedule = extract_schedule_object(js)

    output = []
    counter = 1
    for day in ("24/SET", "25/SET"):
        events = schedule.get(day, [])
        if not isinstance(events, list):
            raise RuntimeError("A programação de %s não é uma lista." % day)
        print("%s: %d eventos" % (day, len(events)))
        for event in events:
            output.append(normalize_event(event, day, counter))
            counter += 1

    if not output:
        raise RuntimeError("Nenhum evento encontrado.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = OUTPUT_FILE.with_suffix(".json.tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")
    temp_file.replace(OUTPUT_FILE)

    print("Total de eventos:", len(output))
    print("Arquivo atualizado:", OUTPUT_FILE)
    print("Concluído com sucesso.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERRO:", exc)
        sys.exit(1)
