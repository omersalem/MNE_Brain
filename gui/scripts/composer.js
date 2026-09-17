import {appState,mutateJSON,setStatus} from './api.js';
import {startTurnStream} from './streaming.js';
import {loadPreferences} from './preferences.js';

const form=document.querySelector('#composer');
const input=document.querySelector('#composer-input');
const messages=document.querySelector('#message-stream');
const fileInput=document.querySelector('#composer-file-input');
const attachBtn=document.querySelector('#attach-file-btn');
const attachmentsTray=document.querySelector('#composer-attachments');
const lightbox=document.querySelector('#image-lightbox');
const lightboxImg=document.querySelector('#lightbox-img');
const lightboxCaption=document.querySelector('#lightbox-caption');
const closeLightboxBtn=document.querySelector('#close-lightbox');
let assistantNode=null;
let assistantText='';
let renderScheduled=false;
let progressNode=null;
const turnPrompts=new Map();
let pendingAttachments=[];

function makeAlertIcon(type){
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width','14');
  svg.setAttribute('height','14');
  svg.setAttribute('viewBox','0 0 16 16');
  svg.setAttribute('fill','currentColor');
  svg.setAttribute('aria-hidden','true');
  if(type==='TIP'){
    const p=document.createElementNS('http://www.w3.org/2000/svg','path');
    p.setAttribute('d','M8 1.5a4.5 4.5 0 0 0-2.8 8c.6.5 1 1.2 1 2v.5h3.6v-.5c0-.8.4-1.5 1-2a4.5 4.5 0 0 0-2.8-8zM6.5 13.5a1.5 1.5 0 0 0 3 0v-.5h-3v.5z');
    svg.append(p);
  }else if(type==='IMPORTANT'||type==='WARNING'){
    const p=document.createElementNS('http://www.w3.org/2000/svg','path');
    p.setAttribute('d','M7.16 2.48a1 1 0 0 1 1.68 0l6.2 10.74A1 1 0 0 1 14.18 14H1.82a1 1 0 0 1-.86-1.48l6.2-10.74zM8 6v3.5M8 11.5h.01');
    p.setAttribute('stroke','currentColor');
    p.setAttribute('stroke-width','1.2');
    p.setAttribute('stroke-linecap','round');
    svg.append(p);
  }else if(type==='CAUTION'){
    const p=document.createElementNS('http://www.w3.org/2000/svg','path');
    p.setAttribute('d','M5.1 1.5h5.8l4.1 4.1v5.8l-4.1 4.1H5.1L1 11.4V5.6l4.1-4.1zM4.5 8h7');
    p.setAttribute('stroke','currentColor');
    p.setAttribute('stroke-width','1.5');
    p.setAttribute('stroke-linecap','round');
    svg.append(p);
  }else{
    const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('cx','8');
    c.setAttribute('cy','8');
    c.setAttribute('r','7');
    c.setAttribute('fill','none');
    c.setAttribute('stroke','currentColor');
    c.setAttribute('stroke-width','1.5');
    const p=document.createElementNS('http://www.w3.org/2000/svg','path');
    p.setAttribute('d','M8 7v4M8 5h.01');
    p.setAttribute('stroke','currentColor');
    p.setAttribute('stroke-width','1.5');
    p.setAttribute('stroke-linecap','round');
    svg.append(c,p);
  }
  return svg;
}

function openLightbox(src,alt){
  if(!lightbox||!lightboxImg)return;
  lightboxImg.src=src;
  lightboxImg.alt=alt||'';
  if(lightboxCaption)lightboxCaption.textContent=alt||'';
  lightbox.showModal();
}
if(closeLightboxBtn&&lightbox){
  closeLightboxBtn.addEventListener('click',()=>lightbox.close());
  lightbox.addEventListener('click',e=>{if(e.target===lightbox)lightbox.close();});
}

function scheduleAssistantRender(){
  if(renderScheduled)return;
  renderScheduled=true;
  requestAnimationFrame(()=>{
    renderScheduled=false;
    if(assistantNode){
      formatMarkdownInto(assistantNode,assistantText);
      messages.scrollTop=messages.scrollHeight;
    }
  });
}

function renderInlineMarkdown(parent,text){
  if(!text)return;
  const pattern=/(!\[([^\]]*)\]\(([^)]+)\)|\[(📎[^\]]+)\]\(([^)]+)\)|`[^`]+`|\[([^\]]+)\]\(([^)]+)\)|\*\*\*[^*]+\*\*\*|\*\*[^*]+\*\*|\*[^*]+\*|_[^_]+_)/g;
  let lastIndex=0;
  let match;
  while((match=pattern.exec(text))!==null){
    if(match.index>lastIndex){
      parent.append(document.createTextNode(text.slice(lastIndex,match.index)));
    }
    const token=match[0];
    if(token.startsWith('![')&&match[3]){
      const alt=match[2]||'';
      const src=match[3];
      const img=document.createElement('img');
      img.className='chat-attached-image';
      img.src=src;
      img.alt=alt;
      img.loading='lazy';
      img.addEventListener('click',()=>openLightbox(src,alt));
      parent.append(img);
    }else if(token.startsWith('[📎')&&match[5]){
      const label=match[4];
      const href=match[5];
      const a=document.createElement('a');
      a.className='chat-attachment-chip';
      a.href=href;
      a.target='_blank';
      a.rel='noopener noreferrer';
      a.textContent=label;
      parent.append(a);
    }else if(token.startsWith('`')&&token.endsWith('`')){
      const code=document.createElement('code');
      code.className='inline-code';
      code.textContent=token.slice(1,-1);
      parent.append(code);
    }else if(token.startsWith('[')&&match[6]&&match[7]){
      const a=document.createElement('a');
      a.className='chat-link';
      a.href=match[7];
      a.target='_blank';
      a.rel='noopener noreferrer';
      if(match[7].startsWith('file:'))a.classList.add('chat-file-link');
      renderInlineMarkdown(a,match[6]);
      parent.append(a);
    }else if(token.startsWith('***')&&token.endsWith('***')){
      const strong=document.createElement('strong');
      strong.className='chat-bold';
      const em=document.createElement('em');
      renderInlineMarkdown(em,token.slice(3,-3));
      strong.append(em);
      parent.append(strong);
    }else if(token.startsWith('**')&&token.endsWith('**')){
      const strong=document.createElement('strong');
      strong.className='chat-bold';
      renderInlineMarkdown(strong,token.slice(2,-2));
      parent.append(strong);
    }else if((token.startsWith('*')&&token.endsWith('*'))||(token.startsWith('_')&&token.endsWith('_'))){
      const em=document.createElement('em');
      renderInlineMarkdown(em,token.slice(1,-1));
      parent.append(em);
    }
    lastIndex=match.index+token.length;
  }
  if(lastIndex<text.length){
    parent.append(document.createTextNode(text.slice(lastIndex)));
  }
}

function appendCodeBlock(container,lang,codeLines){
  const pre=document.createElement('pre');
  pre.className='chat-code-block';
  const header=document.createElement('div');
  header.className='chat-code-header';
  const langSpan=document.createElement('span');
  const safeLang=(lang||'code').trim().toLowerCase();
  langSpan.className=`chat-code-lang badge-${safeLang}`;
  langSpan.textContent=(lang||'code').trim().toUpperCase();
  const copyBtn=document.createElement('button');
  copyBtn.type='button';
  copyBtn.className='chat-code-copy';
  function setCopyState(copied){
    copyBtn.replaceChildren();
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('width','12');
    svg.setAttribute('height','12');
    svg.setAttribute('viewBox','0 0 16 16');
    svg.setAttribute('fill','currentColor');
    svg.setAttribute('aria-hidden','true');
    const path=document.createElementNS('http://www.w3.org/2000/svg','path');
    if(copied){
      path.setAttribute('d','M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z');
    }else{
      path.setAttribute('d','M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z');
      const path2=document.createElementNS('http://www.w3.org/2000/svg','path');
      path2.setAttribute('d','M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z');
      svg.append(path2);
    }
    svg.prepend(path);
    const label=document.createElement('span');
    label.textContent=copied?'Copied!':'Copy';
    copyBtn.append(svg,label);
  }
  setCopyState(false);
  const fullCode=codeLines.join('\n');
  copyBtn.addEventListener('click',async()=>{
    try{
      await navigator.clipboard.writeText(fullCode);
      setCopyState(true);
      setTimeout(()=>{
        setCopyState(false);
      },2000);
    }catch(_){
      copyBtn.textContent='Failed';
    }
  });
  header.append(langSpan,copyBtn);
  const codeElem=document.createElement('code');
  codeElem.className=`code-lang-${safeLang}`;
  codeElem.textContent=fullCode;
  pre.append(header,codeElem);
  container.append(pre);
}

function formatMarkdownInto(container,text){
  container.replaceChildren();
  if(!text)return;
  const lines=text.split(/\r?\n/);
  let inCodeBlock=false;
  let codeBuffer=[];
  let codeLang='';
  let currentList=null;
  let listType=null;

  function flushList(){
    if(currentList){
      container.append(currentList);
      currentList=null;
      listType=null;
    }
  }

  for(let i=0;i<lines.length;i++){
    const line=lines[i];

    if(line.trim().startsWith('```')){
      if(inCodeBlock){
        flushList();
        appendCodeBlock(container,codeLang,codeBuffer);
        codeBuffer=[];
        inCodeBlock=false;
        codeLang='';
      }else{
        flushList();
        inCodeBlock=true;
        codeLang=line.trim().slice(3).trim();
        codeBuffer=[];
      }
      continue;
    }

    if(inCodeBlock){
      codeBuffer.push(line);
      continue;
    }

    if(/^(?:---+|\*\*\*+|___+)$/.test(line.trim())){
      flushList();
      const hr=document.createElement('hr');
      hr.className='chat-divider';
      container.append(hr);
      continue;
    }

    // Markdown Table Support
    if(line.trim().startsWith('|') && line.trim().endsWith('|') && i + 1 < lines.length && /^\|(?:\s*:?-+:?\s*\|)+$/.test(lines[i + 1].trim())){
      flushList();
      const rawHeader = line.trim();
      const rawAlign = lines[i + 1].trim();
      const headers = rawHeader.slice(1, -1).split('|').map(s => s.trim());
      const alignTokens = rawAlign.slice(1, -1).split('|').map(s => s.trim());
      const alignments = alignTokens.map(tok => {
        if(tok.startsWith(':') && tok.endsWith(':')) return 'center';
        if(tok.endsWith(':')) return 'right';
        if(tok.startsWith(':')) return 'left';
        return 'left';
      });
      i += 2;
      const dataRows = [];
      while(i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')){
        const cells = lines[i].trim().slice(1, -1).split('|').map(s => s.trim());
        dataRows.push(cells);
        i++;
      }
      i--; // adjust loop index

      const tableWrapper = document.createElement('div');
      tableWrapper.className = 'chat-table-wrapper';
      const table = document.createElement('table');
      table.className = 'chat-table';
      const thead = document.createElement('thead');
      const headerTr = document.createElement('tr');
      headers.forEach((hText, idx) => {
        const th = document.createElement('th');
        if(alignments[idx]) th.style.textAlign = alignments[idx];
        renderInlineMarkdown(th, hText);
        headerTr.append(th);
      });
      thead.append(headerTr);
      table.append(thead);

      const tbody = document.createElement('tbody');
      dataRows.forEach(row => {
        const tr = document.createElement('tr');
        headers.forEach((_, idx) => {
          const td = document.createElement('td');
          if(alignments[idx]) td.style.textAlign = alignments[idx];
          renderInlineMarkdown(td, row[idx] || '');
          tr.append(td);
        });
        tbody.append(tr);
      });
      table.append(tbody);
      tableWrapper.append(table);
      container.append(tableWrapper);
      continue;
    }

    if(line.trim().startsWith('>')){
      flushList();
      const quoteLines=[];
      while(i<lines.length&&(lines[i].trim().startsWith('>')||(!lines[i].trim()&&quoteLines.length&&i+1<lines.length&&lines[i+1].trim().startsWith('>')))){
        quoteLines.push(lines[i].replace(/^\s*>\s?/,''));
        i++;
      }
      i--;

      const firstLine=quoteLines[0]?quoteLines[0].trim():'';
      const alertMatch=firstLine.match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]$/i);

      if(alertMatch){
        const alertType=alertMatch[1].toUpperCase();
        const alertDiv=document.createElement('div');
        alertDiv.className=`chat-alert chat-alert-${alertType.toLowerCase()}`;
        const alertHeader=document.createElement('div');
        alertHeader.className='chat-alert-header';
        const iconSpan=document.createElement('span');
        iconSpan.className='chat-alert-icon';
        iconSpan.append(makeAlertIcon(alertType));
        const titleSpan=document.createElement('span');
        titleSpan.className='chat-alert-title';
        titleSpan.textContent=alertType;
        alertHeader.append(iconSpan,titleSpan);

        const alertBody=document.createElement('div');
        alertBody.className='chat-alert-body';
        formatMarkdownInto(alertBody,quoteLines.slice(1).join('\n'));

        alertDiv.append(alertHeader,alertBody);
        container.append(alertDiv);
      }else{
        const bq=document.createElement('blockquote');
        bq.className='chat-blockquote';
        formatMarkdownInto(bq,quoteLines.join('\n'));
        container.append(bq);
      }
      continue;
    }

    if(!line.trim()){
      flushList();
      continue;
    }

    const headingMatch=line.match(/^(#{1,4})\s+(.+)$/);
    if(headingMatch){
      flushList();
      const level=headingMatch[1].length;
      const tag=level===1?'h2':level===2?'h3':level===3?'h4':'h5';
      const h=document.createElement(tag);
      h.className=`chat-heading chat-h${level}`;
      renderInlineMarkdown(h,headingMatch[2]);
      container.append(h);
      continue;
    }

    const subMatch=line.match(/^(\s{2,}|\t+)([-*•]|\d+\.)\s+(.+)$/);
    if(subMatch&&currentList&&currentList.lastElementChild){
      const parentLi=currentList.lastElementChild;
      let subList=parentLi.querySelector(':scope > .chat-sublist');
      if(!subList){
        subList=document.createElement(subMatch[2].endsWith('.')?'ol':'ul');
        subList.className='chat-list chat-sublist';
        parentLi.append(subList);
      }
      const li=document.createElement('li');
      li.className='chat-subitem';
      if(subMatch[2].endsWith('.'))li.value=parseInt(subMatch[2],10);
      renderInlineMarkdown(li,subMatch[3]);
      subList.append(li);
      continue;
    }

    const numMatch=line.match(/^(\d+)\.\s+(.+)$/);
    if(numMatch){
      if(listType!=='ol'){
        flushList();
        currentList=document.createElement('ol');
        currentList.className='chat-list chat-ol';
        listType='ol';
      }
      const li=document.createElement('li');
      li.value=parseInt(numMatch[1],10);
      renderInlineMarkdown(li,numMatch[2]);
      currentList.append(li);
      continue;
    }

    const bulletMatch=line.match(/^[-*•]\s+(.+)$/);
    if(bulletMatch){
      if(listType!=='ul'){
        flushList();
        currentList=document.createElement('ul');
        currentList.className='chat-list chat-ul';
        listType='ul';
      }
      const li=document.createElement('li');
      renderInlineMarkdown(li,bulletMatch[1]);
      currentList.append(li);
      continue;
    }

    flushList();
    const p=document.createElement('p');
    p.className='chat-paragraph';
    renderInlineMarkdown(p,line);
    container.append(p);
  }

  flushList();
  if(inCodeBlock&&codeBuffer.length){
    appendCodeBlock(container,codeLang,codeBuffer);
  }
}

function timeLabel(isoString){
  if(!isoString) return new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
  try {
    const d=new Date(isoString);
    return isNaN(d.getTime())?'':d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
  } catch(_) { return ''; }
}

function addMessage(role,text,timestamp=null){
  document.querySelector('#empty-state')?.setAttribute('hidden','');
  const item=document.createElement('article');
  item.className=`message ${role}`;

  const meta=document.createElement('div');
  meta.className='message-meta';

  const author=document.createElement('span');
  author.className='message-author';
  author.textContent=role==='user'?'Owner':role==='assistant'?'MNE_Brain Assistant':role==='error'?'Turn Diagnostics':'System Event';

  const time=document.createElement('time');
  time.className='message-timestamp';
  time.textContent=timeLabel(timestamp);

  meta.append(author,time);
  item.append(meta);

  const body=document.createElement('div');
  body.className='message-body';
  if((role==='assistant'||role==='user')&&text)formatMarkdownInto(body,text);
  else body.textContent=text;

  item.append(body);
  messages.append(item);
  messages.scrollTop=messages.scrollHeight;
  return body;
}

function addFailure(payload,turnId){
  const body=addMessage('error','');
  const card=document.createElement('div');
  card.className='turn-failure-card';

  const title=document.createElement('strong');
  title.className='turn-failure-title';
  title.textContent=payload.message||'The response could not be completed.';

  const code=document.createElement('div');
  code.className='turn-failure-code';
  code.textContent=`Turn Failure (Historical) · ${payload.code||'PROVIDER_UNAVAILABLE'} · Diagnostic ${payload.diagnostic_id||'not available'}`;

  const notice=document.createElement('p');
  notice.className='turn-failure-notice';
  notice.textContent='The local AI engine and infrastructure console remain active and ready for new requests.';

  const actions=document.createElement('div');
  actions.className='message-actions';

  if(payload.retryable!==false&&turnPrompts.has(turnId)){
    const retry=document.createElement('button');
    retry.type='button';
    retry.className='btn-action';
    retry.textContent='Retry Turn';
    retry.addEventListener('click',()=>retryTurn(turnId));
    actions.append(retry);
  }

  if(appState().currentThread?.engine_id==='codex'||appState().currentThread?.engine_id==='opencode'){
    const current=appState().currentThread.engine_id;
    const other=current==='codex'?'opencode':'codex';
    const switchEngine=document.createElement('button');
    switchEngine.type='button';
    switchEngine.className='btn-action';
    switchEngine.textContent=other==='opencode'?'Retry with OpenCode':'Retry with Codex';
    switchEngine.addEventListener('click',()=>document.dispatchEvent(new CustomEvent('new-thread-engine',{detail:{engine_id:other,prompt:turnPrompts.get(turnId)}})));
    actions.append(switchEngine);

    if(current==='opencode'){
      const models=(appState().engines.find(engine=>engine.engine_id==='opencode')?.models||[]).filter(model=>model.id!==appState().currentThread.model_id);
      if(models.length){
        const another=document.createElement('button');
        another.type='button';
        another.className='btn-action';
        another.textContent='Retry with another OpenCode model';
        another.addEventListener('click',()=>document.dispatchEvent(new CustomEvent('new-thread-engine',{detail:{engine_id:'opencode',model_id:models[0].id,prompt:turnPrompts.get(turnId)}})));
        actions.append(another);
      }
    }
  }

  const copy=document.createElement('button');
  copy.type='button';
  copy.className='btn-action';
  copy.textContent='Copy Diagnostic Details';
  copy.addEventListener('click',async()=>{
    const safe={code:payload.code,message:payload.message,diagnostic_id:payload.diagnostic_id,timestamp:payload.timestamp,phase:payload.phase,retryable:payload.retryable};
    try{
      await navigator.clipboard.writeText(JSON.stringify(safe,null,2));
      copy.textContent='Copied!';
      setTimeout(()=>{copy.textContent='Copy Diagnostic Details';},2000);
    }catch{
      copy.textContent='Copy unavailable';
    }
  });
  actions.append(copy);

  card.append(title,code,notice,actions);
  body.append(card);
}

function renderThread(thread){
  messages.replaceChildren();
  assistantNode=null;
  assistantText='';
  progressNode=null;
  pendingAttachments=[];
  renderAttachmentsTray();

  if(!(thread.messages||[]).length){
    const empty=document.createElement('section');
    empty.id='empty-state';
    empty.className='empty-state';

    const mark=document.createElement('div');
    mark.className='empty-mark';
    mark.setAttribute('aria-hidden','true');
    mark.textContent='M';

    const heading=document.createElement('h2');
    heading.textContent='Start a governed infrastructure conversation';

    const detail=document.createElement('p');
    detail.textContent='Ask naturally. Safe reads run automatically; every write waits for your exact approval.';

    const examples=document.createElement('div');
    examples.className='prompt-examples';
    examples.setAttribute('aria-label','Example prompts');

    const p1=document.createElement('button');
    p1.type='button';
    p1.dataset.prompt='Explain the current Release 2 safety state.';
    p1.textContent='Explain the safety state';
    p1.addEventListener('click',()=>{if(input){input.value=p1.dataset.prompt;input.focus();}});

    const p2=document.createElement('button');
    p2.type='button';
    p2.dataset.prompt='Search the workspace for the P7 activation requirements.';
    p2.textContent='Find P7 requirements';
    p2.addEventListener('click',()=>{if(input){input.value=p2.dataset.prompt;input.focus();}});

    examples.append(p1,p2);
    empty.append(mark,heading,detail,examples);
    messages.append(empty);
    return;
  }

  for(const message of thread.messages){
    addMessage(
      message.role==='user'?'user':message.role==='assistant'?'assistant':'status',
      message.content,
      message.created_at
    );
  }
}

async function send(content,externalAuthorizationId=null){
  let thread=appState().currentThread;
  if(!thread){
    const engine=document.querySelector('#provider-select')?.value||'antigravity';
    const model=document.querySelector('#model-select')?.value;
    const title=content.trim().slice(0,60)||'New conversation';
    thread=await mutateJSON('/api/v2/threads',{title,engine_id:engine,model_id:model,permission_mode:'OWNER_DIRECT'});
    appState().currentThread=thread;
    const titleEl=document.querySelector('#conversation-title');
    if(titleEl)titleEl.textContent=thread.title;
  }
  addMessage('user',content);
  assistantNode=null;
  assistantText='';
  setStatus('Queued');
  const turn=await mutateJSON(`/api/v2/threads/${thread.thread_id}/turns`,{content,external_authorization_id:externalAuthorizationId,evidence:[]});
  if(thread){
    if(!thread.turn_ids)thread.turn_ids=[];
    if(!thread.turn_ids.includes(turn.turn_id))thread.turn_ids.push(turn.turn_id);
    if(!thread.turns)thread.turns=[];
    thread.turns.push(turn);
    if(!thread.messages)thread.messages=[];
    thread.messages.push({role:'user',content});
  }
  turnPrompts.set(turn.turn_id,content);
  startTurnStream(turn);
}

function requestSend(content){
  return send(content);
}

function retryTurn(turnId){
  const content=turnPrompts.get(turnId);
  if(!content)return;
  requestSend(content).catch(error=>addFailure({code:error.payload?.code,message:error.message,retryable:true},turnId));
}

function formatBytes(bytes){
  if(bytes<1024)return bytes+' B';
  if(bytes<1024*1024)return (bytes/1024).toFixed(1)+' KB';
  return (bytes/(1024*1024)).toFixed(1)+' MB';
}

function makeFileIcon(){
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width','14');
  svg.setAttribute('height','14');
  svg.setAttribute('viewBox','0 0 16 16');
  svg.setAttribute('fill','currentColor');
  svg.setAttribute('aria-hidden','true');
  const path=document.createElementNS('http://www.w3.org/2000/svg','path');
  path.setAttribute('d','M4 1.5A1.5 1.5 0 0 0 2.5 3v10A1.5 1.5 0 0 0 4 14.5h8a1.5 1.5 0 0 0 1.5-1.5V6L9 1.5H4zm5 1V5a1 1 0 0 0 1 1h2.5L9 2.5z');
  svg.append(path);
  return svg;
}

function makeCloseIcon(){
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width','10');
  svg.setAttribute('height','10');
  svg.setAttribute('viewBox','0 0 16 16');
  svg.setAttribute('fill','currentColor');
  svg.setAttribute('aria-hidden','true');
  const path=document.createElementNS('http://www.w3.org/2000/svg','path');
  path.setAttribute('d','M2.146 2.854a.5.5 0 1 1 .708-.708L8 7.293l5.146-5.147a.5.5 0 0 1 .708.708L8.707 8l5.147 5.146a.5.5 0 0 1-.708.708L8 8.707l-5.146 5.147a.5.5 0 0 1-.708-.708L7.293 8 2.146 2.854z');
  svg.append(path);
  return svg;
}

function renderAttachmentsTray(){
  if(!attachmentsTray)return;
  attachmentsTray.replaceChildren();
  if(pendingAttachments.length===0){
    attachmentsTray.style.display='none';
    return;
  }
  attachmentsTray.style.display='flex';
  pendingAttachments.forEach((att,index)=>{
    const chip=document.createElement('div');
    chip.className='attachment-preview-chip';
    if(att.isImage&&att.dataUrl){
      const thumb=document.createElement('img');
      thumb.className='attachment-preview-thumb';
      thumb.src=att.dataUrl;
      thumb.alt=att.name;
      chip.append(thumb);
    }else{
      const icon=document.createElement('span');
      icon.className='attachment-preview-icon';
      icon.append(makeFileIcon());
      chip.append(icon);
    }
    const info=document.createElement('div');
    info.className='attachment-preview-info';
    const nameSpan=document.createElement('span');
    nameSpan.className='attachment-preview-name';
    nameSpan.textContent=att.name;
    const sizeSpan=document.createElement('span');
    sizeSpan.className='attachment-preview-size';
    sizeSpan.textContent=formatBytes(att.size);
    info.append(nameSpan,sizeSpan);

    const removeBtn=document.createElement('button');
    removeBtn.type='button';
    removeBtn.className='attachment-remove-btn';
    removeBtn.append(makeCloseIcon());
    removeBtn.title='Remove';
    removeBtn.setAttribute('aria-label','Remove attachment');
    removeBtn.addEventListener('click',()=>{
      pendingAttachments.splice(index,1);
      renderAttachmentsTray();
    });

    chip.append(info,removeBtn);
    attachmentsTray.append(chip);
  });
}

async function addFilesToPending(fileList){
  for(const file of Array.from(fileList)){
    if(file.size>25*1024*1024){
      alert(`File "${file.name}" exceeds the 25 MB limit.`);
      continue;
    }
    const isImage=file.type.startsWith('image/');
    const reader=new FileReader();
    const dataUrl=await new Promise(resolve=>{
      reader.onload=()=>resolve(reader.result);
      reader.readAsDataURL(file);
    });
    const base64Content=String(dataUrl).split(',')[1]||'';
    pendingAttachments.push({
      file,
      name:file.name,
      size:file.size,
      mimeType:file.type||'application/octet-stream',
      isImage,
      dataUrl:isImage?dataUrl:null,
      base64:base64Content
    });
  }
  renderAttachmentsTray();
}

if(attachBtn&&fileInput){
  attachBtn.addEventListener('click',()=>fileInput.click());
}
if(fileInput){
  fileInput.addEventListener('change',async()=>{
    await addFilesToPending(fileInput.files);
    fileInput.value='';
  });
}

form.addEventListener('dragover',e=>{
  e.preventDefault();
  form.classList.add('drag-over');
});
form.addEventListener('dragleave',e=>{
  if(!form.contains(e.relatedTarget))form.classList.remove('drag-over');
});
form.addEventListener('drop',async e=>{
  e.preventDefault();
  form.classList.remove('drag-over');
  if(e.dataTransfer?.files?.length){
    await addFilesToPending(e.dataTransfer.files);
  }
});

input.addEventListener('paste',async e=>{
  const items=e.clipboardData?.items;
  if(!items)return;
  const files=[];
  for(const item of items){
    if(item.kind==='file'){
      const file=item.getAsFile();
      if(file)files.push(file);
    }
  }
  if(files.length){
    await addFilesToPending(files);
  }
});

// Auto-resizing textarea
input.addEventListener('input',()=>{
  input.style.height='auto';
  input.style.height=Math.min(input.scrollHeight,240)+'px';
});

function updateComposerHint(){
  const hint=document.querySelector('#composer-hint');
  if(!hint)return;
  const prefs=loadPreferences();
  hint.textContent=prefs.enterToSend
    ?'Enter to send · Shift+Enter for a new line'
    :'Ctrl+Enter to send · Shift+Enter for a new line';
}
document.addEventListener('preferences-changed',updateComposerHint);
updateComposerHint();

input.addEventListener('keydown',event=>{
  if(event.isComposing)return;
  const prefs=loadPreferences();
  if(prefs.enterToSend){
    if(event.key==='Enter'&&!event.shiftKey){
      event.preventDefault();
      form.requestSubmit();
    }
  }else{
    if(event.key==='Enter'&&(event.ctrlKey||event.metaKey)){
      event.preventDefault();
      form.requestSubmit();
    }
  }
});

form.addEventListener('submit',async event=>{
  event.preventDefault();
  const rawText=input.value.trim();
  if(!rawText&&!pendingAttachments.length)return;
  input.value='';
  input.style.height='auto';

  const attachmentsToUpload=[...pendingAttachments];
  pendingAttachments=[];
  renderAttachmentsTray();

  try{
    let composedContent=rawText;
    if(attachmentsToUpload.length){
      setStatus('Uploading attachments…');
      const uploadedResults=[];
      for(const att of attachmentsToUpload){
        const result=await mutateJSON('/api/v2/uploads',{
          filename:att.name,
          mime_type:att.mimeType,
          base64_data:att.base64
        });
        uploadedResults.push(result);
      }
      setStatus('Attachments uploaded');

      const parts=[];
      if(composedContent)parts.push(composedContent);
      for(const res of uploadedResults){
        if(res.is_image){
          parts.push(`![${res.filename}](${res.url})`);
          parts.push(`[Attached local file: ${res.absolute_path}]`);
        }else{
          parts.push(`[📎 ${res.filename}](${res.url})`);
          parts.push(`[Attached local file: ${res.absolute_path}]`);
          if(res.text_content&&res.text_content.length<=40000){
            const ext=(res.filename.split('.').pop()||'text').toLowerCase();
            parts.push('```'+ext+'\n'+res.text_content+'\n```');
          }
        }
      }
      composedContent=parts.join('\n\n');
    }
    await requestSend(composedContent);
  }catch(error){
    const isAuth=error.status===401||error.status===403||error.message?.toLowerCase().includes('session');
    if(isAuth){
      input.value=rawText;
      pendingAttachments=attachmentsToUpload;
      renderAttachmentsTray();
      setStatus('Session expired — please sign in to continue');
    }else{
      addFailure({code:error.payload?.code,message:error.message,retryable:true},'');
      setStatus('Request failed');
    }
  }
});

document.addEventListener('answer-delta',event=>{
  if(!assistantNode){
    assistantNode=addMessage('assistant','');
    assistantText='';
  }
  assistantText+=event.detail.text||'';
  scheduleAssistantRender();
});

document.addEventListener('answer-final',event=>{
  const text=String(event.detail.text||assistantText||'').trim();
  if(!text)return;
  if(!assistantNode)assistantNode=addMessage('assistant','');
  assistantText=text;
  formatMarkdownInto(assistantNode,text);
  requestAnimationFrame(()=>{messages.scrollTop=messages.scrollHeight;});
});

document.addEventListener('agent-progress',event=>{
  if(!progressNode)progressNode=addMessage('status','Investigating…');
  const text=String(event.detail.text||'').trim();
  if(text)progressNode.textContent=`Investigating · ${text.slice(-1200)}`;
  setStatus(`${appState().currentThread?.engine_id==='opencode'?'OpenCode':'Codex'} is investigating`);
});

document.addEventListener('retry-prompt',event=>{
  const content=String(event.detail.content||'').trim();
  if(content)requestSend(content).catch(error=>addFailure({code:error.payload?.code,message:error.message,retryable:true},''));
});

document.addEventListener('agent-plan',event=>{
  const steps=event.detail.plan?.steps||event.detail.steps||[];
  if(Array.isArray(steps)&&steps.length)addMessage('status',`Plan · ${steps.map(step=>step.step||step.description||String(step)).join(' → ')}`);
});

document.addEventListener('thread-selected',event=>renderThread(event.detail.thread));

document.addEventListener('clear-composer-attachments',()=>{
  pendingAttachments=[];
  renderAttachmentsTray();
});

document.addEventListener('stream-event',event=>{
  const envelope=event.detail.envelope;
  if(envelope.event_type==='turn.failed')addFailure(envelope.redacted_payload,envelope.turn_id);
  if(envelope.event_type==='turn.cancelled')addMessage('status','Response cancelled.');
  if(['turn.completed','turn.cancelled','turn.failed'].includes(envelope.event_type)){
    if(envelope.event_type==='turn.completed'){
      if(assistantNode&&assistantText){
        formatMarkdownInto(assistantNode,assistantText);
      }
      const current=appState().currentThread;
      if(current&&assistantText){
        if(!current.messages)current.messages=[];
        current.messages.push({role:'assistant',content:assistantText});
      }
    }
    assistantNode=null;
    assistantText='';
    progressNode=null;
  }
});

document.querySelector('#cancel-turn')?.addEventListener('click',async()=>{
  const turn=appState().activeTurn;
  if(!turn)return;
  try{
    await mutateJSON(`/api/v2/turns/${turn.turn_id}/cancel`,{});
    setStatus('Cancelling');
  }catch(error){
    setStatus(error.message);
  }
});

for(const button of document.querySelectorAll('[data-prompt]')){
  button.addEventListener('click',()=>{
    if(input){
      input.value=button.dataset.prompt||'';
      input.focus();
    }
  });
}
