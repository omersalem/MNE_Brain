export function renderEvidence(payload){
  const sources=document.querySelector('#evidence-sources');
  const existingSources=payload.append?[...sources.querySelectorAll('li')].map(item=>item.textContent).filter(text=>text!=='No attributable source accepted.'):[];
  sources.replaceChildren();
  const allSources=[...new Set([...existingSources,...(payload.sources||[])])];
  for(const source of allSources){const item=document.createElement('li');item.textContent=source||'Unspecified source';sources.append(item);}
  if(!sources.children.length){const item=document.createElement('li');item.textContent='No attributable source accepted.';sources.append(item);}
  const unknowns=document.querySelector('#evidence-unknowns');
  const existingUnknowns=payload.append?[...unknowns.querySelectorAll('li')].map(item=>item.textContent).filter(text=>text!=='No unresolved evidence gaps reported.'):[];
  unknowns.replaceChildren();
  for(const unknown of [...new Set([...existingUnknowns,...(payload.unknowns||[])])]){const item=document.createElement('li');item.textContent=unknown;unknowns.append(item);}
  if(!unknowns.children.length){const item=document.createElement('li');item.textContent='No unresolved evidence gaps reported.';unknowns.append(item);}
  const badge=document.querySelector('#evidence-count-badge');
  if(badge){
    const validCount=allSources.filter(s=>s&&s!=='No attributable source accepted.').length;
    badge.textContent=String(validCount);
    badge.classList.toggle('has-evidence',validCount>0);
  }
}
document.addEventListener('evidence-accepted',event=>renderEvidence(event.detail));
document.addEventListener('live-evidence',event=>renderEvidence(event.detail));

const toggleBtn=document.querySelector('#toggle-evidence');
const closeBtn=document.querySelector('#close-evidence');
const workspace=document.querySelector('.workspace');

toggleBtn?.addEventListener('click',()=>{
  const isShown=workspace?.classList.toggle('show-evidence');
  toggleBtn.setAttribute('aria-expanded',String(Boolean(isShown)));
});
closeBtn?.addEventListener('click',()=>{
  workspace?.classList.remove('show-evidence');
  toggleBtn?.setAttribute('aria-expanded','false');
});
