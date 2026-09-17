import {ensureSession,loginOwner,logoutOwner} from './api.js';

const gate=document.querySelector('#login-gate');
const form=document.querySelector('#owner-login-form');
const status=document.querySelector('#login-status');
const username=document.querySelector('#owner-username');
const password=document.querySelector('#owner-password');

let preservedDraft='';

export function getPreservedDraft(){
  return preservedDraft;
}

let wasSessionExpired=false;

function showGate(detail={}){
  // Close any open <dialog> elements in browser top-layer to prevent modal obscuration
  document.querySelectorAll('dialog[open]').forEach(d => {
    try { d.close(); } catch (_) { d.removeAttribute('open'); }
  });
  // Close open action menus and dropdowns
  document.querySelectorAll('.thread-menu-dropdown').forEach(el => el.setAttribute('hidden', ''));
  document.querySelectorAll('.thread-menu-trigger').forEach(el => el.setAttribute('aria-expanded', 'false'));
  const modelPicker = document.querySelector('#model-picker-dropdown');
  if (modelPicker) modelPicker.setAttribute('hidden', '');
  document.querySelector('#model-picker-btn')?.setAttribute('aria-expanded', 'false');
  document.querySelector('#model-picker-button')?.setAttribute('aria-expanded', 'false');

  if(detail.session_expired) wasSessionExpired = true;

  // Preserve unsent composer draft
  const composerInput = document.querySelector('#composer-input');
  if(composerInput && composerInput.value && composerInput.value.trim()){
    preservedDraft = composerInput.value;
  }

  if(gate) gate.hidden=false;
  if(document.body) document.body.dataset.authenticated='false';
  const configured=detail.owner_credentials_configured??detail.configured;
  if(status) status.textContent=configured===false?'Owner login is not configured. Run: python scripts/configure_owner_login.py':(detail.logged_out?'Signed out safely.':(detail.session_expired?'Your owner session expired due to inactivity. Please sign in to resume.':'Sign in with the local owner account.'));
  if(username) setTimeout(()=>username.focus(),0);
}

function hideGate(){
  if(gate) gate.hidden=true;
  if(document.body) document.body.dataset.authenticated='true';
  if(password) password.value='';
  if(status) status.textContent='';
}

let isRehydrating=false;

export async function rehydrateSession(){
  if(isRehydrating) return;
  isRehydrating=true;
  try {
    hideGate();

    const { loadProviders } = await import('./providers.js');
    const { loadThreads, selectThread, newThread } = await import('./threads.js');
    const { appState } = await import('./api.js');

    try {
      await loadProviders();
    } catch (_) {}

    let threads = [];
    try {
      threads = await loadThreads();
    } catch (_) {}

    const hash = typeof window !== 'undefined' ? (window.location.hash || '') : '';
    const hashMatch = hash.match(/#thread=([^&]+)/);
    const hashThreadId = hashMatch ? decodeURIComponent(hashMatch[1]) : null;

    const currentId = hashThreadId || appState().currentThread?.thread_id;
    if (currentId && (threads || []).some(t => t.thread_id === currentId)) {
      try {
        await selectThread(currentId);
      } catch (_) {}
    } else {
      const firstActive = (threads || []).find(t => t.status !== 'ARCHIVED');
      if (firstActive) {
        try {
          await selectThread(firstActive.thread_id);
        } catch (_) {}
      } else if (!threads || threads.length === 0) {
        try {
          await newThread();
        } catch (_) {}
      }
    }

    if (preservedDraft) {
      const composerInput = document.querySelector('#composer-input');
      if (composerInput && !composerInput.value) {
        composerInput.value = preservedDraft;
      }
    }
  } finally {
    isRehydrating = false;
  }
}

document.addEventListener('owner-auth-required',event=>showGate(event.detail));
document.addEventListener('owner-authenticated',()=>{
  hideGate();
  if(wasSessionExpired){
    wasSessionExpired=false;
    rehydrateSession().catch(err=>{if(status)status.textContent=err.message;});
  }
});

if(form){
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    const submit=form.querySelector('button[type="submit"]');
    if(submit) submit.disabled=true;
    if(status) status.textContent='Signing in…';
    try{
      await loginOwner(username.value.trim(),password.value);
      hideGate();
    }catch(error){
      if(status) status.textContent=error.message;
      if(password) password.select();
    }finally{
      if(submit) submit.disabled=false;
    }
  });
}

document.querySelector('#logout-button')?.addEventListener('click',async()=>{
  try{
    await logoutOwner();
  }catch(error){
    showGate({configured:true});
    if(status) status.textContent=error.message;
  }
});

ensureSession().catch(error=>showGate({configured:true,error:error.message}));
