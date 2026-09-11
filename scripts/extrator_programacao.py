#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib, json, re, urllib.request
from pathlib import Path

SOURCE_URL="https://mercadolivreexperience.mercadolivre.com.br/mlxp.json"
OUTPUT=Path(__file__).resolve().parents[1]/"data"/"programacao.json"
DATES={"24/SET":"2026-09-24","25/SET":"2026-09-25"}

def s(v): return v if isinstance(v,str) else ""
def arr(v): return v if isinstance(v,list) else []
def make_id(x):
    raw="|".join(s(x.get(k)) for k in ("data","hora_inicio","palco","titulo"))
    return "talk-"+hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"Mozilla/5.0 (MELIXP26 updater)"})
with urllib.request.urlopen(req,timeout=30) as r:
    src=json.loads(r.read().decode("utf-8"))

if not isinstance(src,dict):
    raise RuntimeError("A fonte oficial não retornou o formato esperado.")

out=[]
for day,events in src.items():
    date=DATES.get(day)
    if not date:
        m=re.match(r"^(\d{2})/SET$",str(day).upper())
        if m: date="2026-09-"+m.group(1)
    if not date or not isinstance(events,list): continue
    for e in events:
        if not isinstance(e,dict): continue
        x={
            "id":"",
            "data":date,
            "hora_inicio":s(e.get("hora_inicio") or e.get("horaInicio") or e.get("hora")),
            "hora_fim":s(e.get("hora_fim") or e.get("horaFim") or e.get("fim")),
            "horario_original":s(e.get("horario_original") or e.get("hora")),
            "palco":s(e.get("palco")),
            "titulo":s(e.get("titulo")),
            "descricao":s(e.get("descricao") or e.get("descricao_palestra") or e.get("bio_palestra")),
            "empresa":s(e.get("empresa")),
            "palestrantes":arr(e.get("palestrantes")),
            "tema":s(e.get("tema")),
            "tags":arr(e.get("tags")),
            "imagem":s(e.get("imagem"))
        }
        x["id"]=make_id(x)
        out.append(x)

out.sort(key=lambda x:(x["data"],x["hora_inicio"] or "99:99",x["palco"],x["titulo"]))
if not out or len({x["id"] for x in out})!=len(out):
    raise RuntimeError("Programação vazia ou IDs duplicados.")

OUTPUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("OK:",len(out),"palestras")
