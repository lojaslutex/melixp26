#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import tempfile
import urllib.request

URL = "https://mercadolivreexperience.mercadolivre.com.br/mlxp.json"
OUTPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "programacao.json")

EXPECTED_DAYS = ("24/SET", "25/SET")


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
        raw = response.read()
    return json.loads(raw.decode("utf-8"))


def validar(data):
    if not isinstance(data, dict):
        raise ValueError("O mlxp.json não retornou um objeto JSON.")

    for dia in EXPECTED_DAYS:
        if dia not in data:
            raise ValueError("Dia ausente no JSON oficial: " + dia)
        if not isinstance(data[dia], list):
            raise ValueError("O conteúdo de " + dia + " não é uma lista.")

    total = sum(len(data[dia]) for dia in EXPECTED_DAYS)
    if total == 0:
        raise ValueError("O JSON oficial não possui sessões.")

    for dia in EXPECTED_DAYS:
        if len(data[dia]) == 0:
            raise ValueError("Nenhuma sessão encontrada para " + dia)

        for i, sessao in enumerate(data[dia]):
            if not isinstance(sessao, dict):
                raise ValueError("Sessão inválida em %s, índice %d." % (dia, i))

            # O site oficial usa "hora" diretamente.
            hora = sessao.get("hora")
            titulo = sessao.get("titulo")
            palco = sessao.get("palco")

            if not isinstance(hora, str) or not hora.strip():
                raise ValueError("Sessão sem 'hora' em %s, índice %d." % (dia, i))
            if not isinstance(titulo, str) or not titulo.strip():
                raise ValueError("Sessão sem 'titulo' em %s, índice %d." % (dia, i))
            if not isinstance(palco, str) or not palco.strip():
                raise ValueError("Sessão sem 'palco' em %s, índice %d." % (dia, i))

            # Evita publicar horários em formatos inesperados.
            if len(hora.strip()) != 5 or hora[2] != ":":
                raise ValueError(
                    "Horário fora do formato HH:MM em %s: %r" % (dia, hora)
                )

    return total


def salvar_atomico(data):
    pasta = os.path.dirname(OUTPUT)
    if not os.path.isdir(pasta):
        os.makedirs(pasta)

    fd, temporario = tempfile.mkstemp(prefix="programacao_", suffix=".json",
                                      dir=pasta)
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

    data = baixar_json()
    total = validar(data)

    # IMPORTANTE:
    # Não transforma, achata, renomeia ou converte os campos.
    # O site oficial espera exatamente o objeto com 24/SET e 25/SET.
    salvar_atomico(data)

    print("Programação atualizada com sucesso.")
    print("24/SET: %d eventos" % len(data["24/SET"]))
    print("25/SET: %d eventos" % len(data["25/SET"]))
    print("Total: %d eventos" % total)
    print("Arquivo: %s" % OUTPUT)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERRO:", str(e))
        sys.exit(1)
