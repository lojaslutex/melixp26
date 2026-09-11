#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Extrator da programação do Mercado Livre Experience 2026.

Fonte oficial utilizada pelo próprio site:
https://mercadolivreexperience.mercadolivre.com.br/mlxp.json

O script:
- baixa o JSON oficial;
- valida a estrutura;
- valida as duas datas do evento;
- normaliza os campos para o formato usado pelo GitHub Pages;
- só grava o arquivo final se a validação for aprovada.

Compatível com Python 3.x.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime

URL_ORIGINAL = "https://mercadolivreexperience.mercadolivre.com.br/mlxp.json"
ARQUIVO_SAIDA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "programacao.json",
)

DATAS = ("24/SET", "25/SET")


def baixar_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; "
                "MLXP26-Programacao/1.0; +https://github.com/lojaslutex/melixp26)"
            ),
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://mercadolivreexperience.mercadolivre.com.br/",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resposta:
        conteudo = resposta.read()

    try:
        texto = conteudo.decode("utf-8")
    except UnicodeDecodeError:
        texto = conteudo.decode("utf-8-sig")

    return json.loads(texto)


def lista_segura(valor):
    if isinstance(valor, list):
        return valor
    return []


def texto(valor, padrao=""):
    if valor is None:
        return padrao
    if isinstance(valor, str):
        return valor.strip()
    return str(valor).strip()


def normalizar_palestrantes(valor):
    resultado = []

    for palestrante in lista_segura(valor):
        if isinstance(palestrante, dict):
            resultado.append({
                "nome": texto(
                    palestrante.get("nome")
                    or palestrante.get("name")
                ),
                "empresa": texto(
                    palestrante.get("empresa")
                    or palestrante.get("company")
                ),
                "cargo": texto(
                    palestrante.get("cargo")
                    or palestrante.get("role")
                    or palestrante.get("job")
                ),
            })
        elif isinstance(palestrante, str):
            resultado.append({
                "nome": palestrante.strip(),
                "empresa": "",
                "cargo": "",
            })

    return resultado


def normalizar_evento(evento, data):
    if not isinstance(evento, dict):
        return None

    hora = texto(
        evento.get("hora")
        or evento.get("horario")
        or evento.get("hora_inicio")
    )

    titulo = texto(
        evento.get("titulo")
        or evento.get("title")
        or evento.get("nome")
    )

    palco = texto(
        evento.get("palco")
        or evento.get("stage")
    )

    if not titulo or not hora:
        return None

    descricao = texto(
        evento.get("descricao")
        or evento.get("bio_palestra")
        or evento.get("description")
    )

    palestrantes = normalizar_palestrantes(
        evento.get("palestrantes")
        or evento.get("speakers")
    )

    tags = []
    for tag in lista_segura(evento.get("tags")):
        if isinstance(tag, dict):
            valor = texto(tag.get("nome") or tag.get("name"))
        else:
            valor = texto(tag)
        if valor:
            tags.append(valor)

    # Mantém a ordem original e elimina duplicidades.
    tags = list(dict.fromkeys(tags))

    hora_inicio = hora
    hora_fim = texto(
        evento.get("hora_fim")
        or evento.get("horario_fim")
    )

    horario_original = texto(
        evento.get("horario_original")
        or evento.get("horario")
        or hora
    )

    imagem = texto(
        evento.get("imagem")
        or evento.get("image")
    )

    tema = texto(
        evento.get("tema")
        or evento.get("theme")
    )

    # O ID original é preservado quando existe.
    evento_id = evento.get("id")
    if evento_id is None or texto(evento_id) == "":
        evento_id = "%s-%s-%s" % (
            data.lower().replace("/", "-"),
            hora.replace(":", ""),
            titulo.lower().replace(" ", "-")[:80],
        )

    return {
        "id": evento_id,
        "data": data,
        "hora_inicio": hora_inicio,
        "hora_fim": hora_fim,
        "horario_original": horario_original,
        "palco": palco,
        "titulo": titulo,
        "descricao": descricao,
        "empresa": texto(evento.get("empresa")),
        "palestrantes": palestrantes,
        "tema": tema,
        "tags": tags,
        "imagem": imagem,
    }


def extrair_eventos(dados):
    if not isinstance(dados, dict):
        raise ValueError("O mlxp.json não retornou um objeto JSON.")

    eventos_por_data = {}

    for data in DATAS:
        valor = dados.get(data)

        if valor is None:
            # Aceita também chaves equivalentes em minúsculas.
            for chave, item in dados.items():
                if texto(chave).upper() == data:
                    valor = item
                    break

        if not isinstance(valor, list):
            raise ValueError(
                "A chave %s não contém uma lista de eventos." % data
            )

        eventos = []
        for evento in valor:
            normalizado = normalizar_evento(evento, data)
            if normalizado:
                eventos.append(normalizado)

        eventos_por_data[data] = eventos

    return eventos_por_data


def validar(eventos_por_data):
    contagens = {
        data: len(eventos_por_data.get(data, []))
        for data in DATAS
    }

    print("Eventos encontrados:")
    for data in DATAS:
        print("  %s: %d" % (data, contagens[data]))

    if any(contagens[data] == 0 for data in DATAS):
        raise ValueError(
            "Validação interrompida: uma das datas não possui eventos."
        )

    total = sum(contagens.values())

    # Proteção contra uma resposta inesperada ou parcial.
    # O site atualmente possui uma programação substancial nos dois dias.
    if total < 10:
        raise ValueError(
            "Validação interrompida: apenas %d eventos encontrados." % total
        )

    return total


def gerar_saida(eventos_por_data):
    # Mantém a estrutura simples: lista única, ordenada por data/hora.
    eventos = []

    for data in DATAS:
        eventos.extend(eventos_por_data[data])

    def chave(evento):
        hora = texto(evento.get("hora_inicio"))
        try:
            hora_ordem = datetime.strptime(hora, "%H:%M")
        except ValueError:
            hora_ordem = datetime.strptime("23:59", "%H:%M")
        return (DATAS.index(evento["data"]), hora_ordem)

    eventos.sort(key=chave)
    return eventos


def salvar_com_seguranca(eventos):
    diretorio = os.path.dirname(ARQUIVO_SAIDA)
    if not os.path.isdir(diretorio):
        os.makedirs(diretorio)

    temporario = ARQUIVO_SAIDA + ".tmp"

    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(
            eventos,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )
        arquivo.write("\n")

    os.replace(temporario, ARQUIVO_SAIDA)


def main():
    print("Baixando programação oficial:")
    print(URL_ORIGINAL)

    try:
        dados = baixar_json(URL_ORIGINAL)
        eventos_por_data = extrair_eventos(dados)
        total = validar(eventos_por_data)
        eventos = gerar_saida(eventos_por_data)

        salvar_com_seguranca(eventos)

        print("Total: %d eventos." % total)
        print("Arquivo atualizado: %s" % ARQUIVO_SAIDA)

    except Exception as erro:
        print("ERRO: %s" % erro, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
