const state = {
  session: null,
  threads: [],
  currentThread: null,
  providers: [],
  engines: [],
  activeTurn: null,
};

let sessionPromise;
let loginWaiter;
let resolveLogin;

export function appState(){ return state; }

export function emit(name, detail={}){
  document.dispatchEvent(new CustomEvent(name,{detail}));
}

export async function ensureSession(){
  if(!sessionPromise){
    sessionPromise=fetch('/api/v2/session',{credentials:'same-origin',headers:{Accept:'application/json'}})
      .then(async response=>{
        if(response.status===401){
          const payload=await response.json();
          emit('owner-auth-required',payload);
          if(!loginWaiter) loginWaiter=new Promise(resolve=>{resolveLogin=resolve;});
          return loginWaiter;
        }
        if(!response.ok) throw new Error((await response.json()).error||'Owner session failed');
        state.session=await response.json();
        emit('owner-authenticated',{session:state.session});
        return state.session;
      });
  }
  return sessionPromise;
}

export async function loginOwner(username,password){
  const response=await fetch('/api/v2/login',{
    method:'POST',credentials:'same-origin',
    headers:{Accept:'application/json','Content-Type':'application/json'},
    body:JSON.stringify({username,password}),
  });
  const payload=await response.json();
  if(!response.ok) throw Object.assign(new Error(payload.error||'Owner login failed'),{status:response.status,payload});
  state.session=payload;sessionPromise=Promise.resolve(payload);
  if(resolveLogin) resolveLogin(payload);
  loginWaiter=null;resolveLogin=null;
  emit('owner-authenticated',{session:payload});
  return payload;
}

export async function logoutOwner(){
  if(state.session) await mutateJSON('/api/v2/logout',{});
  state.session=null;sessionPromise=null;loginWaiter=null;resolveLogin=null;
  emit('owner-auth-required',{configured:true,logged_out:true});
}

export async function getJSON(path){
  await ensureSession();
  const response=await fetch(path,{credentials:'same-origin',headers:{Accept:'application/json'}});
  const payload=await response.json();
  if(!response.ok) throw Object.assign(new Error(payload.error||`Request failed (${response.status})`),{status:response.status,payload});
  return payload;
}

function mutationNonce(){
  return crypto.randomUUID().replaceAll('-','')+crypto.randomUUID().replaceAll('-','');
}

export async function mutateJSON(path,payload={}){
  const session=await ensureSession();
  const response=await fetch(path,{
    method:'POST',credentials:'same-origin',
    headers:{Accept:'application/json','Content-Type':'application/json','X-CSRF-Token':session.csrf_token},
    body:JSON.stringify({...payload,request_nonce:mutationNonce()}),
  });
  const result=await response.json();
  if(!response.ok) throw Object.assign(new Error(result.error||`Mutation failed (${response.status})`),{status:response.status,payload:result});
  return result;
}

export function setStatus(text){
  const target=document.querySelector('#turn-status');
  if(target) target.textContent=text;
}

function renderConnectivity(){
  const banner=document.querySelector('#offline-banner');
  if(banner) banner.hidden=navigator.onLine;
  document.documentElement.dataset.connection=navigator.onLine?'online':'offline';
}
window.addEventListener('online',()=>{renderConnectivity();setStatus('Reconnected');});
window.addEventListener('offline',()=>{renderConnectivity();setStatus('Offline');});
renderConnectivity();
