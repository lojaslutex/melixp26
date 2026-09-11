window.App={
  talks:[],

  async load(){const data=await fetch('data/programacao.json?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Não foi possível carregar a programação.');return r.json()});if(!Array.isArray(data))throw Error('A programação carregada não é uma lista de palestras. Verifique data/programacao.json.');this.talks=data;this.talks.sort((a,b)=>`${a.data}|${a.hora_inicio||'99:99'}|${a.palco}`.localeCompare(`${b.data}|${b.hora_inicio||'99:99'}|${b.palco}`,'pt-BR'));return this.talks},

  render(talks,container=document.querySelector('#schedule')){
    if(!container)return;

    container.innerHTML=talks.map(t=>{
      const speakers=Array.isArray(t.palestrantes)?t.palestrantes:[];
      const tags=Array.isArray(t.tags)?t.tags:[];

      return `
        <article class="talk" data-id="${Utils.escape(t.id)}">
          <div class="talk-time">
            <strong>${Utils.escape(t.hora_inicio||t.horario_original||'')}</strong>
            ${t.hora_fim?`<span>${Utils.escape(t.hora_fim)}</span>`:''}
          </div>

          <div class="talk-content">
            <div class="talk-meta">
              <span>${Utils.escape(t.palco||'')}</span>
              ${Utils.duration(t)?`<span>${Utils.escape(Utils.duration(t))}</span>`:''}
            </div>

            <h3>${Utils.escape(t.titulo||'')}</h3>

            ${t.descricao?`<p>${Utils.escape(t.descricao)}</p>`:''}

            ${speakers.length?`
              <div class="speakers">
                ${speakers.map(s=>{
                  if(typeof s==='string') return `<span>${Utils.escape(s)}</span>`;
                  const name=s.nome||s.name||'';
                  const role=s.cargo||s.role||'';
                  return `<span>${Utils.escape(name)}${role?` — ${Utils.escape(role)}`:''}</span>`;
                }).join('')}
              </div>`:''}

            ${tags.length?`
              <div class="tags">
                ${tags.map(tag=>`<span>${Utils.escape(String(tag))}</span>`).join('')}
              </div>`:''}
          </div>
        </article>
      `;
    }).join('');
  }
};