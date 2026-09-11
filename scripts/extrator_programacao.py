#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import tempfile
import urllib.request

URL = "https://mercadolivreexperience.mercadolivre.com.br/mlxp.json"
OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "programacao.json"
)

DIAS = {
    "24/SET": "2026-09-24",
    "25/SET": "2026-09-25",
}


def baixar_json():
    req = urllib.request.Request(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://mercadolivreexperience.mercadolivre.com.br/",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalizar_evento(evento, data):
    hora = evento.get("hora", "")
    titulo = evento.get("titulo", "")
    palco = evento.get("palco", "")

    # Mantém o formato que o frontend do projeto espera:
    # um ARRAY de talks, com hora_inicio/data/etc.
    return {
        "id": evento.get("id", ""),
        "data": data,
        "hora_inicio": hora,
        "hora_fim": evento.get("hora_fim", ""),
        "horario_original": evento.get("horario_original", hora),
        "palco": palco,
        "titulo": titulo,
        "descricao": evento.get("descricao", evento.get("bio_palestra", "")),
        "empresa": evento.get("empresa", ""),
        "palestrantes": evento.get("palestrantes", []),
        "tema": evento.get("tema", ""),
        "tags": evento.get("tags", []),
        "imagem": evento.get("imagem", ""),
    }


def validar(origem):
    if not isinstance(origem, dict):
        raise ValueError("O mlxp.json não retornou um objeto JSON.")

    talks = []

    for chave, data in DIAS.items():
        if chave not in origem:
            raise ValueError("Dia ausente no JSON oficial: " + chave)

        if not isinstance(origem[chave], list) or not origem[chave]:
            raise ValueError("Nenhuma sessão encontrada para " + chave)

        for i, evento in enumerate(origem[chave]):
            if not isinstance(evento, dict):
                raise ValueError("Sessão inválida em %s, índice %d." % (chave, i))

            hora = evento.get("hora")
            titulo = evento.get("titulo")
            palco = evento.get("palco")

            if not isinstance(hora, str) or not hora.strip():
                raise ValueError("Sessão sem hora em %s, índice %d." % (chave, i))
            if not isinstance(titulo, str) or not titulo.strip():
                raise ValueError("Sessão sem título em %s, índice %d." % (chave, i))
            if not isinstance(palco, str) or not palco.strip():
                raise ValueError("Sessão sem palco em %s, índice %d." % (chave, i))

            talks.append(normalizar_evento(evento, data))

    if not talks:
        raise ValueError("Nenhuma palestra encontrada.")

    # Ordenação simples por data + hora, sem converter para Date.
    talks.sort(key=lambda x: (x["data"], x["hora_inicio"]))

    return talks


def salvar_atomico(data):
    pasta = os.path.dirname(OUTPUT)
    if not os.path.isdir(pasta):
        os.makedirs(pasta)

    fd, temporario = tempfile.mkstemp(
        prefix="programacao_",
        suffix=".json",
        dir=pasta
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

        os.replace(temporario, OUTPUT)

    except Exception:
        try:
            os.unlink(temporario)
        except OSError:
            pass
        raise


def main():
    print("Baixando programação oficial:")
    print(URL)

    origem = baixar_json()
    talks = validar(origem)
    salvar_atomico(talks)

    qtd24 = len([x for x in talks if x["data"] == "2026-09-24"])
    qtd25 = len([x for x in talks if x["data"] == "2026-09-25"])

    print("Programação atualizada com sucesso.")
    print("24/09:", qtd24, "eventos")
    print("25/09:", qtd25, "eventos")
    print("Total:", len(talks))
    print("Arquivo:", OUTPUT)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERRO:", str(e))
        sys.exit(1)
