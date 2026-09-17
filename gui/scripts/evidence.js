import {loadPreferences} from './preferences.js';

export function renderEvidence(payload){
  const sources=document.querySelector('#evidence-sources');
  const existingSources=payload.append?[...sources.querySelectorAll('li')].map(item=>item.textContent).filter(text=>text!=='No attributable source accepted.'):[];
  if(sources){
    sources.replaceChildren();
    const allSources=[...new Set([...existingSources,...(payload.sources||[])])];
    for(const source of allSources){
      const item=document.createElement('li');
      item.textContent=source||'Unspecified source';
      sources.append(item);
    }
    if(!sources.children.length){
      const item=document.createElement('li');
      item.textContent='No attributable source accepted.';
      sources.append(item);
    }

    const badge=document.querySelector('#evidence-count-badge');
    if(badge){
      const validCount=allSources.filter(s=>s&&s!=='No attributable source accepted.').length;
      badge.textContent=String(validCount);
      badge.classList.toggle('has-evidence',validCount>0);

      const prefs=loadPreferences();
      if(prefs.autoOpenEvidence&&validCount>0){
        workspace?.classList.add('show-evidence');
        toggleBtn?.setAttribute('aria-expanded','true');
      }
    }
  }

  const unknowns=document.querySelector('#evidence-unknowns');
  if(unknowns){
    const existingUnknowns=payload.append?[...unknowns.querySelectorAll('li')].map(item=>item.textContent).filter(text=>text!=='No unresolved evidence gaps reported.'):[];
    unknowns.replaceChildren();
    for(const unknown of [...new Set([...existingUnknowns,...(payload.unknowns||[])])]){
      const item=document.createElement('li');
      item.textContent=unknown;
      unknowns.append(item);
    }
    if(!unknowns.children.length){
      const item=document.createElement('li');
      item.textContent='No unresolved evidence gaps reported.';
      unknowns.append(item);
    }
  }
}

document.addEventListener('evidence-accepted',event=>renderEvidence(event.detail));
document.addEventListener('live-evidence',event=>renderEvidence(event.detail));

const toggleBtn=document.querySelector('#toggle-evidence');
const closeBtn=document.querySelector('#close-evidence');
const workspace=document.querySelector('.workspace');
const inspectorBackdrop=document.querySelector('#inspector-backdrop');

toggleBtn?.addEventListener('click',()=>{
  const isShown=workspace?.classList.toggle('show-evidence');
  toggleBtn.setAttribute('aria-expanded',String(Boolean(isShown)));
});

closeBtn?.addEventListener('click',()=>{
  workspace?.classList.remove('show-evidence');
  toggleBtn?.setAttribute('aria-expanded','false');
});

inspectorBackdrop?.addEventListener('click',()=>{
  workspace?.classList.remove('show-evidence');
  toggleBtn?.setAttribute('aria-expanded','false');
});

// Inspector Tab Switching Controller
const inspectorTabs=document.querySelectorAll('.inspector-tab-btn');
const inspectorPanels=document.querySelectorAll('.inspector-tab-panel');

inspectorTabs.forEach(tab=>{
  tab.addEventListener('click',()=>{
    const targetId=tab.dataset.target;
    inspectorTabs.forEach(t=>{
      t.classList.toggle('active',t===tab);
      t.setAttribute('aria-selected',String(t===tab));
    });
    inspectorPanels.forEach(p=>{
      const isMatch=p.id===targetId;
      p.classList.toggle('active',isMatch);
      p.hidden=!isMatch;
    });
  });
});

// Mobile Sidebar Drawer Controller
const sidebarToggleBtn=document.querySelector('#sidebar-toggle-btn');
const sidebarBackdrop=document.querySelector('#sidebar-backdrop');
const threadsPanel=document.querySelector('.threads-panel');

sidebarToggleBtn?.addEventListener('click',()=>{
  const isOpen=threadsPanel?.classList.toggle('open');
  sidebarToggleBtn.setAttribute('aria-expanded',String(Boolean(isOpen)));
});

sidebarBackdrop?.addEventListener('click',()=>{
  threadsPanel?.classList.remove('open');
  sidebarToggleBtn?.setAttribute('aria-expanded','false');
});
