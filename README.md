# Fórum ECBR 2026

Aplicação PWA em HTML, CSS e JavaScript puro para consultar a programação oficial do Fórum E-Commerce Brasil 2026.

## Executar

Abra esta pasta com um servidor HTTP local e acesse `index.html`. O uso de servidor é necessário para que o navegador carregue o JSON e instale o PWA.

## Atualizar a programação

O arquivo `data/programacao.json` foi extraído do HTML oficial fornecido. Para repetir a extração, execute na raiz do workspace:

`node extractor.js "C:\\Users\\Guilherme\\Downloads\\Programação _ Fórum E-Commerce Brasil 2026.html" "outputs\\forum-ecbr\\data\\programacao.json"`

O extrator não cria conteúdo: campos ausentes na fonte ficam vazios. Ele preserva data, horário, palco, título, descrição, empresas, palestrantes, temas, tags e imagens disponíveis.

## Recursos

- Busca e filtros instantâneos.
- Favoritas, assistidas e notas pessoais no armazenamento local.
- Roteiro de favoritas, alerta de conflito e exportação CSV/ICS.
- Página individual da palestra, contador para a próxima favorita, tema escuro e funcionamento offline após a primeira visita.

## Publicar

Hospede o conteúdo da pasta em qualquer servidor HTTPS estático. Para publicar uma atualização, substitua `data/programacao.json` e incremente a chave `CACHE` em `service-worker.js`.
