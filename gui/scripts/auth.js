import {ensureSession,loginOwner,logoutOwner} from './api.js';

const gate=document.querySelector('#login-gate');
const form=document.querySelector('#owner-login-form');
const status=document.querySelector('#login-status');
const username=document.querySelector('#owner-username');
const password=document.querySelector('#owner-password');

function showGate(detail={}){
  gate.hidden=false;document.body.dataset.authenticated='false';
  const configured=detail.owner_credentials_configured??detail.configured;
  status.textContent=configured===false?'Owner login is not configured. Run: python scripts/configure_owner_login.py':(detail.logged_out?'Signed out safely.':'Sign in with the local owner account.');
  setTimeout(()=>username.focus(),0);
}
function hideGate(){gate.hidden=true;document.body.dataset.authenticated='true';password.value='';status.textContent='';}

document.addEventListener('owner-auth-required',event=>showGate(event.detail));
document.addEventListener('owner-authenticated',hideGate);
form.addEventListener('submit',async event=>{
  event.preventDefault();const submit=form.querySelector('button[type="submit"]');submit.disabled=true;status.textContent='Signing in…';
  try{await loginOwner(username.value.trim(),password.value);hideGate();}catch(error){status.textContent=error.message;password.select();}finally{submit.disabled=false;}
});
document.querySelector('#logout-button').addEventListener('click',async()=>{try{await logoutOwner();}catch(error){showGate({configured:true});status.textContent=error.message;}});
ensureSession().catch(error=>showGate({configured:true,error:error.message}));
