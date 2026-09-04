import {appState,mutateJSON,setStatus} from './api.js';
import {startTurnStream} from './streaming.js';

const form=document.querySelector('#composer');
const input=document.querySelector('#composer-input');
const messages=document.querySelector('#message-stream');
let assistantNode;
let progressNode;
const turnPrompts=new Map();

function renderInlineMarkdown(parent,text){
  const pattern=/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let lastIndex=0;let match;
  while((match=pattern.exec(text))!==null){
    if(match.index>lastIndex)parent.append(document.createTextNode(text.slice(lastIndex,match.index)));
    const token=match[0];
    if(token.startsWith('`')&&token.endsWith('`')){
      const code=document.createElement('code');code.className='inline-code';code.textContent=token.slice(1,-1);parent.append(code);
    }else if(token.startsWith('**')&&token.endsWith('**')){
      const strong=document.createElement('strong');strong.className='chat-bold';renderInlineMarkdown(strong,token.slice(2,-2));parent.append(strong);
    }else if(token.startsWith('*')&&token.endsWith('*')){
      const em=document.createElement('em');em.textContent=token.slice(1,-1);parent.append(em);
    }
    lastIndex=match.index+token.length;
  }
  if(lastIndex<text.length)parent.append(document.createTextNode(text.slice(lastIndex)));
}

function formatMarkdownInto(container,text){
  container.replaceChildren();if(!text)return;
  const lines=text.split(/\r?\n/);
  let inCodeBlock=false;let codeBuffer=[];let codeLang='';let currentList=null;let listType=null;
  function flushList(){if(currentList){container.append(currentList);currentList=null;listType=null;}}
  for(let i=0;i<lines.length;i++){
    const line=lines[i];
    if(line.trim().startsWith('```')){
      if(inCodeBlock){
        flushList();
        const pre=document.createElement('pre');pre.className='chat-code-block';
        const header=document.createElement('div');header.className='chat-code-header';
        const langSpan=document.createElement('span');langSpan.textContent=codeLang||'code';
        const copyBtn=document.createElement('button');copyBtn.type='button';copyBtn.className='chat-code-copy';copyBtn.textContent='Copy';
        const fullCode=codeBuffer.join('\n');
        copyBtn.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(fullCode);copyBtn.textContent='Copied!';setTimeout(()=>{copyBtn.textContent='Copy';},2000);}catch(_){copyBtn.textContent='Failed';}});
        header.append(langSpan,copyBtn);const codeElem=document.createElement('code');codeElem.textContent=fullCode;pre.append(header,codeElem);container.append(pre);
        codeBuffer=[];inCodeBlock=false;codeLang='';
      }else{
        flushList();inCodeBlock=true;codeLang=line.trim().slice(3).trim();codeBuffer=[];
      }
      continue;
    }
    if(inCodeBlock){codeBuffer.push(line);continue;}
    if(!line.trim()){flushList();continue;}
    const headingMatch=line.match(/^(#{1,4})\s+(.+)$/);
    if(headingMatch){
      flushList();const level=headingMatch[1].length;const h=document.createElement(level<=2?'h3':'h4');h.className='chat-heading';renderInlineMarkdown(h,headingMatch[2]);container.append(h);continue;
    }
    const numMatch=line.match(/^(\d+)\.\s+(.+)$/);
    if(numMatch){
      if(listType!=='ol'){flushList();currentList=document.createElement('ol');currentList.className='chat-list chat-ol';listType='ol';}
      const li=document.createElement('li');renderInlineMarkdown(li,numMatch[2]);currentList.append(li);continue;
    }
    const bulletMatch=line.match(/^[-*•]\s+(.+)$/);
    if(bulletMatch){
      if(listType!=='ul'){flushList();currentList=document.createElement('ul');currentList.className='chat-list chat-ul';listType='ul';}
      const li=document.createElement('li');renderInlineMarkdown(li,bulletMatch[1]);currentList.append(li);continue;
    }
    flushList();const p=document.createElement('p');p.className='chat-paragraph';renderInlineMarkdown(p,line);container.append(p);
  }
  flushList();
  if(inCodeBlock&&codeBuffer.length){
    const pre=document.createElement('pre');pre.className='chat-code-block';const codeElem=document.createElement('code');codeElem.textContent=codeBuffer.join('\n');pre.append(codeElem);container.append(pre);
  }
}

function addMessage(role,text){
  document.querySelector('#empty-state')?.setAttribute('hidden','');
  const item=document.createElement('article');item.className=`message ${role}`;
  if(role==='assistant'&&text)formatMarkdownInto(item,text);else item.textContent=text;
  messages.append(item);messages.scrollTop=messages.scrollHeight;return item;
}

function addFailure(payload,turnId){
  const item=addMessage('error','');
  const title=document.createElement('strong');title.textContent=payload.message||'The response could not be completed.';
  const code=document.createElement('span');code.textContent=`${payload.code||'PROVIDER_UNAVAILABLE'} · Diagnostic ${payload.diagnostic_id||'not available'}`;
  const actions=document.createElement('div');actions.className='message-actions';
  if(payload.retryable!==false&&turnPrompts.has(turnId)){
    const retry=document.createElement('button');retry.type='button';retry.textContent='Retry';
    retry.addEventListener('click',()=>retryTurn(turnId));actions.append(retry);
  }
  if(appState().currentThread?.engine_id==='codex'||appState().currentThread?.engine_id==='opencode'){
    const current=appState().currentThread.engine_id;
    const other=current==='codex'?'opencode':'codex';
    const switchEngine=document.createElement('button');switchEngine.type='button';switchEngine.textContent=other==='opencode'?'Retry with OpenCode':'Retry with Codex';
    switchEngine.addEventListener('click',()=>document.dispatchEvent(new CustomEvent('new-thread-engine',{detail:{engine_id:other,prompt:turnPrompts.get(turnId)}})));actions.append(switchEngine);
    if(current==='opencode'){
      const models=(appState().engines.find(engine=>engine.engine_id==='opencode')?.models||[]).filter(model=>model.id!==appState().currentThread.model_id);
      if(models.length){const another=document.createElement('button');another.type='button';another.textContent='Retry with another OpenCode model';another.addEventListener('click',()=>document.dispatchEvent(new CustomEvent('new-thread-engine',{detail:{engine_id:'opencode',model_id:models[0].id,prompt:turnPrompts.get(turnId)}})));actions.append(another);}
    }
  }
  const copy=document.createElement('button');copy.type='button';copy.textContent='Copy diagnostic details';
  copy.addEventListener('click',async()=>{
    const safe={code:payload.code,message:payload.message,diagnostic_id:payload.diagnostic_id,timestamp:payload.timestamp,phase:payload.phase,retryable:payload.retryable};
    try{await navigator.clipboard.writeText(JSON.stringify(safe,null,2));copy.textContent='Copied';}catch{copy.textContent='Copy unavailable';}
  });
  actions.append(copy);item.append(title,code,actions);
}

function renderThread(thread){
  messages.replaceChildren();assistantNode=null;progressNode=null;
  if(!(thread.messages||[]).length){
    const empty=document.createElement('section');empty.id='empty-state';empty.className='empty-state';
    const heading=document.createElement('h2');heading.textContent='Start a governed infrastructure conversation';
    const detail=document.createElement('p');detail.textContent='Ask naturally. Safe reads run automatically; every write waits for your exact approval.';
    empty.append(heading,detail);messages.append(empty);return;
  }
  for(const message of thread.messages)addMessage(message.role==='user'?'user':message.role==='assistant'?'assistant':'status',message.content);
}

async function send(content,externalAuthorizationId=null){
  const thread=appState().currentThread;if(!thread)throw new Error('No active thread');
  addMessage('user',content);assistantNode=null;setStatus('Queued');
  const turn=await mutateJSON(`/api/v2/threads/${thread.thread_id}/turns`,{content,external_authorization_id:externalAuthorizationId,evidence:[]});
  turnPrompts.set(turn.turn_id,content);startTurnStream(turn);
}

function requestSend(content){
  return send(content);
}

function retryTurn(turnId){
  const content=turnPrompts.get(turnId);if(!content)return;
  requestSend(content).catch(error=>addFailure({code:error.payload?.code,message:error.message,retryable:true},turnId));
}

form.addEventListener('submit',async event=>{
  event.preventDefault();const content=input.value.trim();if(!content)return;input.value='';
  try{await requestSend(content);}catch(error){addFailure({code:error.payload?.code,message:error.message,retryable:true},'');setStatus('Request failed');}
});
input.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();form.requestSubmit();}});
document.addEventListener('answer-delta',event=>{if(!assistantNode)assistantNode=addMessage('assistant','');assistantNode.textContent+=event.detail.text;messages.scrollTop=messages.scrollHeight;});
document.addEventListener('answer-final',event=>{
  const text=String(event.detail.text||'').trim();if(!text)return;
  if(!assistantNode)assistantNode=addMessage('assistant','');
  formatMarkdownInto(assistantNode,text);
  requestAnimationFrame(()=>{messages.scrollTop=messages.scrollHeight;});
});
document.addEventListener('agent-progress',event=>{if(!progressNode)progressNode=addMessage('status','Investigating…');const text=String(event.detail.text||'').trim();if(text)progressNode.textContent=`Investigating · ${text.slice(-1200)}`;setStatus(`${appState().currentThread?.engine_id==='opencode'?'OpenCode':'Codex'} is investigating`);});
document.addEventListener('retry-prompt',event=>{const content=String(event.detail.content||'').trim();if(content)requestSend(content).catch(error=>addFailure({code:error.payload?.code,message:error.message,retryable:true},''));});
document.addEventListener('agent-plan',event=>{const steps=event.detail.plan?.steps||event.detail.steps||[];if(Array.isArray(steps)&&steps.length)addMessage('status',`Plan · ${steps.map(step=>step.step||step.description||String(step)).join(' → ')}`);});
document.addEventListener('thread-selected',event=>renderThread(event.detail.thread));
document.addEventListener('stream-event',event=>{
  const envelope=event.detail.envelope;
  if(envelope.event_type==='turn.failed')addFailure(envelope.redacted_payload,envelope.turn_id);
  if(envelope.event_type==='turn.cancelled')addMessage('status','Response cancelled.');
  if(['turn.completed','turn.cancelled','turn.failed'].includes(envelope.event_type)){assistantNode=null;progressNode=null;}
});
document.querySelector('#cancel-turn').addEventListener('click',async()=>{const turn=appState().activeTurn;if(!turn)return;try{await mutateJSON(`/api/v2/turns/${turn.turn_id}/cancel`,{});setStatus('Cancelling');}catch(error){setStatus(error.message);}});
for(const button of document.querySelectorAll('[data-prompt]'))button.addEventListener('click',()=>{input.value=button.dataset.prompt||'';input.focus();});
