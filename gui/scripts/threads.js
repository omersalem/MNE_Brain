import {appState,emit,getJSON,mutateJSON,setStatus} from './api.js';
import {startTurnStream} from './streaming.js';

const list=document.querySelector('#thread-list');
const search=document.querySelector('#thread-search');

function renderThreads(){
  list.replaceChildren();
  for(const thread of appState().threads){
    const item=document.createElement('li');
    const button=document.createElement('button');
    button.type='button';
    button.textContent=thread.title;
    button.dataset.threadId=thread.thread_id;
    button.setAttribute('aria-current',String(appState().currentThread?.thread_id===thread.thread_id));
    button.addEventListener('click',()=>selectThread(thread.thread_id));
    item.append(button); list.append(item);
  }
}

export async function loadThreads(query=''){
  const payload=await getJSON('/api/v2/threads'+(query?`?search=${encodeURIComponent(query)}`:''));
  appState().threads=payload.threads;
  renderThreads();
  return payload.threads;
}

export async function selectThread(threadId){
  const thread=await getJSON(`/api/v2/threads/${encodeURIComponent(threadId)}`);
  appState().currentThread=thread;
  document.querySelector('#conversation-title').textContent=thread.title;
  document.querySelector('#provider-select').value=thread.engine_id;
  document.querySelector('#model-select').value=thread.model_id;
  document.querySelector('#permission-mode').value=thread.permission_mode;
  renderThreads(); emit('thread-selected',{thread});
  const active=[...(thread.turns||[])].reverse().find(turn=>['QUEUED','RUNNING'].includes(turn.status));
  if(active)startTurnStream(active);
}

async function newThread(){
  const title=`Conversation ${appState().threads.length+1}`;
  const engine=document.querySelector('#provider-select').value||'codex';
  const model=document.querySelector('#model-select').value||undefined;
  const thread=await mutateJSON('/api/v2/threads',{title,engine_id:engine,model_id:model,permission_mode:'OWNER_DIRECT'});
  await loadThreads(); await selectThread(thread.thread_id);
}

async function newThreadForEngine(engine,model,prompt){
  const selected=appState().engines.find(item=>item.engine_id===engine);
  const thread=await mutateJSON('/api/v2/threads',{title:`Conversation ${appState().threads.length+1}`,engine_id:engine,model_id:model||selected?.default_model,permission_mode:'OWNER_DIRECT'});
  await loadThreads();await selectThread(thread.thread_id);if(prompt)document.dispatchEvent(new CustomEvent('retry-prompt',{detail:{content:prompt}}));
}

document.querySelector('#new-thread').addEventListener('click',()=>newThread().catch(error=>setStatus(error.message)));
document.addEventListener('new-thread-engine',event=>newThreadForEngine(event.detail.engine_id,event.detail.model_id,event.detail.prompt).catch(error=>setStatus(error.message)));
search.addEventListener('input',()=>loadThreads(search.value).catch(error=>setStatus(error.message)));
document.querySelector('#export-thread').addEventListener('click',async()=>{
  const thread=appState().currentThread;if(!thread)return;
  try{
    const payload=await getJSON(`/api/v2/threads/${encodeURIComponent(thread.thread_id)}/export`);
    const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));
    const anchor=document.createElement('a');anchor.href=url;anchor.download=`mne-brain-${thread.thread_id}.json`;anchor.click();URL.revokeObjectURL(url);setStatus('Conversation exported');
  }catch(error){setStatus(error.message);}
});
const importFile=document.querySelector('#import-thread-file');
document.querySelector('#import-thread').addEventListener('click',()=>importFile.click());
importFile.addEventListener('change',async()=>{
  const file=importFile.files?.[0];if(!file)return;
  try{
    if(file.size>2000000)throw new Error('Import exceeds the 2 MB safety limit');
    const conversation=JSON.parse(await file.text());
    const thread=await mutateJSON('/api/v2/threads/import',{conversation});await loadThreads();await selectThread(thread.thread_id);setStatus('Conversation imported');
  }catch(error){setStatus(error.message);}finally{importFile.value='';}
});

loadThreads().then(async threads=>{
  if(threads.length) await selectThread(threads[0].thread_id); else await newThread();
}).catch(error=>setStatus(error.message));
