export function renderEvidence(payload){
  const sources=document.querySelector('#evidence-sources');
  const existingSources=payload.append?[...sources.querySelectorAll('li')].map(item=>item.textContent).filter(text=>text!=='No attributable source accepted.'):[];
  sources.replaceChildren();
  for(const source of [...new Set([...existingSources,...(payload.sources||[])])]){const item=document.createElement('li');item.textContent=source||'Unspecified source';sources.append(item);}
  if(!sources.children.length){const item=document.createElement('li');item.textContent='No attributable source accepted.';sources.append(item);}
  const unknowns=document.querySelector('#evidence-unknowns');
  const existingUnknowns=payload.append?[...unknowns.querySelectorAll('li')].map(item=>item.textContent).filter(text=>text!=='No unresolved evidence gaps reported.'):[];
  unknowns.replaceChildren();
  for(const unknown of [...new Set([...existingUnknowns,...(payload.unknowns||[])])]){const item=document.createElement('li');item.textContent=unknown;unknowns.append(item);}
  if(!unknowns.children.length){const item=document.createElement('li');item.textContent='No unresolved evidence gaps reported.';unknowns.append(item);}
}
document.addEventListener('evidence-accepted',event=>renderEvidence(event.detail));
document.addEventListener('live-evidence',event=>renderEvidence(event.detail));
