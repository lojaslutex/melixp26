# Extrator Mercado Livre Experience

Este projeto atualiza automaticamente `data/programacao.json` a partir da programação publicada no site do Mercado Livre Experience.

## Estrutura

```text
.
├── data/
│   └── programacao.json
├── scripts/
│   └── extrator_programacao.py
└── .github/
    └── workflows/
        └── atualizar-programacao.yml
```

## Execução manual no GitHub

No repositório:

1. Acesse **Actions**.
2. Selecione **Atualizar programação Mercado Livre Experience**.
3. Clique em **Run workflow**.
4. Aguarde o workflow terminar.

O arquivo `data/programacao.json` será atualizado e, se houver mudanças, o GitHub fará um commit automaticamente.

## Execução automática

O workflow também está configurado para rodar diariamente às **07:00 no horário de Brasília** (10:00 UTC).

## Execução local

É necessário Python 3.

```bash
python scripts/extrator_programacao.py
```

O arquivo será salvo em:

```text
data/programacao.json
```

## Observação

O extrator primeiro tenta descobrir os arquivos JavaScript atuais na página principal. O arquivo JS atualmente conhecido também é mantido como fallback:

```text
https://mercadolivreexperience.mercadolivre.com.br/_next/static/chunks/app/page-eba548846f7b2a93.js
```

A programação é extraída diretamente das estruturas `24/SET` e `25/SET` do JavaScript, sem depender do HTML renderizado da página.
