#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extrai a programação oficial do Mercado Livre Experience.

Fonte oficial:
https://mercadolivreexperience.mercadolivre.com.br/mlxp.json

O frontend deste projeto espera uma LISTA (array) de palestras em
data/programacao.json.
"""

import hashlib
import json
import re
import urllib.request
from pathlib import Path

SOURCE_URL = "https://mercadolivreexperience.mercadolivre.com.br/mlxp.json"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "programacao.json"

DATE_MAP = {
    "24/SET": "2026-09-24",
    "25/SET": "2026-09-25",
}


def text(value):
    return value if isinstance(value, str) else ""


def list_value(value):
    return value if isinstance(value, list) else []


def stable_id(item):
    raw = "|".join([
        text(item.get("data")),
        text(item.get("hora_inicio")),
        text(item.get("palco")),
        text(item.get("titulo")),
    ])
    return "talk-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def fetch_source():
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; MELIXP26-Schedule-Updater/1.0)"
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize(source):
    # A fonte oficial é um objeto por data: {"24/SET": [...], "25/SET": [...]}
    if not isinstance(source, dict):
        raise RuntimeError("A fonte oficial não retornou um objeto por data.")

    result = []

    for source_date, events in source.items():
        date = DATE_MAP.get(source_date)
        if not date:
            # Mantém suporte para outras grafias de data sem quebrar o extrator.
            m = re.match(r"^(\d{2})/SET$", str(source_date).upper())
            if m:
                date = "2026-09-" + m.group(1)

        if not date:
            continue

        if not isinstance(events, list):
            continue

        for event in events:
            if not isinstance(event, dict):
                continue

            hora = text(event.get("hora"))
            hora_inicio = text(
                event.get("hora_inicio")
                or event.get("horaInicio")
                or hora
            )
            hora_fim = text(
                event.get("hora_fim")
                or event.get("horaFim")
                or event.get("fim")
                or ""
            )

            item = {
                "id": "",
                "data": date,
                "hora_inicio": hora_inicio,
                "hora_fim": hora_fim,
                "horario_original": hora or hora_inicio,
                "palco": text(event.get("palco")),
                "titulo": text(event.get("titulo")),
                "descricao": text(
                    event.get("descricao")
                    or event.get("descricao_palestra")
                    or event.get("bio_palestra")
                ),
                "empresa": text(event.get("empresa")),
                "palestrantes": list_value(event.get("palestrantes")),
                "tema": text(event.get("tema")),
                "tags": list_value(event.get("tags")),
                "imagem": text(event.get("imagem")),
            }

            item["id"] = stable_id(item)
            result.append(item)

    result.sort(key=lambda item: (
        item["data"],
        item["hora_inicio"] or "99:99",
        item["palco"],
        item["titulo"],
    ))

    if not result:
        raise RuntimeError("Nenhuma palestra foi encontrada na fonte oficial.")

    return result


def validate(items):
    if not isinstance(items, list):
        raise RuntimeError("programacao.json precisa ser um array.")

    ids = set()
    for item in items:
        if not item.get("id"):
            raise RuntimeError("Encontrada palestra sem ID.")
        if item["id"] in ids:
            raise RuntimeError("Encontrado ID duplicado: " + item["id"])
        ids.add(item["id"])

        if not isinstance(item.get("palestrantes"), list):
            raise RuntimeError("palestrantes precisa ser array.")
        if not isinstance(item.get("tags"), list):
            raise RuntimeError("tags precisa ser array.")


def main():
    source = fetch_source()
    items = normalize(source)
    validate(items)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Programação atualizada:", len(items), "palestras")
    print("Arquivo:", OUTPUT)


if __name__ == "__main__":
    main()
