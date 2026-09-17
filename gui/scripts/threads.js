import {appState,emit,getJSON,mutateJSON,setStatus} from './api.js';
import {startTurnStream} from './streaming.js';
import {loadPreferences,savePreferences} from './preferences.js';
import {resolveTargetEngineAndModel,getProvidersCatalogPromise} from './providers.js';

const list=document.querySelector('#thread-list');
const search=document.querySelector('#thread-search');
const deleteDialog=document.querySelector('#thread-delete-dialog');
const deleteDialogTitle=document.querySelector('#delete-dialog-thread-title');
const deleteDialogWarning=document.querySelector('#delete-dialog-active-turn-warning');
const deleteDialogConfirmBtn=document.querySelector('#delete-dialog-confirm-btn');
const deleteDialogCancelBtn=document.querySelector('#delete-dialog-cancel-btn');

const enlargeBtn=document.querySelector('#sidebar-enlarge-btn');
const sidebarResizer=document.querySelector('#sidebar-resizer');
const selectModeBtn=document.querySelector('#thread-select-mode-btn');
const batchBar=document.querySelector('#thread-batch-bar');
const selectAllBtn=document.querySelector('#thread-select-all-btn');
const selectedCountBadge=document.querySelector('#thread-selected-count');
const batchDeleteBtn=document.querySelector('#thread-batch-delete-btn');
const batchCancelBtn=document.querySelector('#thread-batch-cancel-btn');

const batchDeleteDialog=document.querySelector('#thread-batch-delete-dialog');
const batchDeleteCountLabel=document.querySelector('#batch-delete-count-label');
const batchDeletePreviewList=document.querySelector('#batch-delete-preview-list');
const batchDeleteActiveWarning=document.querySelector('#batch-delete-active-turn-warning');
const batchDeleteActiveMsg=document.querySelector('#batch-delete-active-turn-msg');
const batchDeleteConfirmBtn=document.querySelector('#batch-delete-confirm-btn');
const batchDeleteCancelBtn=document.querySelector('#batch-delete-cancel-btn');

let threadPendingDelete=null;
let activeMenuThreadId=null;
let isSelectMode=false;
const selectedThreadIds=new Set();

// Close any open thread action menu when clicking outside or pressing Escape
document.addEventListener('click',event=>{
  if(!event.target.closest('.thread-menu-wrapper')){
    closeAllThreadMenus();
  }
});

document.addEventListener('keydown',event=>{
  if(event.key==='Escape'){
    closeAllThreadMenus();
  }
});

function closeAllThreadMenus(){
  activeMenuThreadId=null;
  document.querySelectorAll('.thread-menu-dropdown').forEach(el=>el.setAttribute('hidden',''));
  document.querySelectorAll('.thread-menu-trigger').forEach(el=>el.setAttribute('aria-expanded','false'));
}

function makeIcon(type){
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width',type==='dots'?'16':(type==='warn'?'12':'14'));
  svg.setAttribute('height',type==='dots'?'16':(type==='warn'?'12':'14'));
  svg.setAttribute('viewBox','0 0 16 16');
  svg.setAttribute('fill','currentColor');
  svg.setAttribute('aria-hidden','true');
  if(type==='dots'){
    for(const cx of ['3','8','13']){
      const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
      c.setAttribute('cx',cx);
      c.setAttribute('cy','8');
      c.setAttribute('r','1.5');
      svg.append(c);
    }
  }else if(type==='rename'){
    const p=document.createElementNS('http://www.w3.org/2000/svg','path');
    p.setAttribute('d','M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175-.806 2.016 2.016-.806L4.5 11.5h-.5a.5.5 0 0 1-.5-.5v-.5h-.5a.5.5 0 0 1-.5-.5v-.5l-.268-.268z');
    svg.append(p);
  }else if(type==='export'){
    const p1=document.createElementNS('http://www.w3.org/2000/svg','path');
    p1.setAttribute('d','M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z');
    const p2=document.createElementNS('http://www.w3.org/2000/svg','path');
    p2.setAttribute('d','M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z');
    svg.append(p1,p2);
  }else if(type==='delete'){
    const p1=document.createElementNS('http://www.w3.org/2000/svg','path');
    p1.setAttribute('d','M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z');
    const p2=document.createElementNS('http://www.w3.org/2000/svg','path');
    p2.setAttribute('fill-rule','evenodd');
    p2.setAttribute('d','M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z');
    svg.append(p1,p2);
  }else if(type==='archive'){
    const p1=document.createElementNS('http://www.w3.org/2000/svg','path');
    p1.setAttribute('d','M0 2a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1v7.5a2.5 2.5 0 0 1-2.5 2.5h-9A2.5 2.5 0 0 1 1 12.5V5a1 1 0 0 1-1-1zm2 3v7.5A1.5 1.5 0 0 0 3.5 14h9a1.5 1.5 0 0 0 1.5-1.5V5zm13-3H1v2h14zM5 7.5a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5');
    svg.append(p1);
  }else if(type==='unarchive'){
    const p1=document.createElementNS('http://www.w3.org/2000/svg','path');
    p1.setAttribute('d','M12.643 15C13.979 15 15 13.845 15 12.5V5H1v7.5C1 13.845 2.021 15 3.357 15zM5.5 7h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1 0-1M.8 1a.8.8 0 0 0-.8.8V3a.8.8 0 0 0 .8.8h14.4A.8.8 0 0 0 16 3V1.8a.8.8 0 0 0-.8-.8z');
    svg.append(p1);
  }else if(type==='warn'){
    const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('cx','8');
    c.setAttribute('cy','8');
    c.setAttribute('r','7');
    c.setAttribute('fill','none');
    c.setAttribute('stroke','currentColor');
    c.setAttribute('stroke-width','1.5');
    const p=document.createElementNS('http://www.w3.org/2000/svg','path');
    p.setAttribute('d','M4 8h8');
    p.setAttribute('stroke','currentColor');
    p.setAttribute('stroke-width','1.5');
    svg.append(c,p);
  }
  return svg;
}

function makeLabelSpan(text){
  const s=document.createElement('span');
  s.textContent=text;
  return s;
}

export function toggleThreadSelection(threadId){
  if(selectedThreadIds.has(threadId)){
    selectedThreadIds.delete(threadId);
  }else{
    selectedThreadIds.add(threadId);
  }
  updateBatchBarState();
  const item=list.querySelector(`.thread-item[data-thread-id="${threadId}"]`);
  if(item){
    const isSelected=selectedThreadIds.has(threadId);
    item.classList.toggle('is-selected',isSelected);
    const cb=item.querySelector('.thread-select-checkbox');
    if(cb)cb.checked=isSelected;
  }
}

export function updateBatchBarState(){
  const count=selectedThreadIds.size;
  if(selectedCountBadge){
    selectedCountBadge.textContent=`${count} selected`;
  }
  if(batchDeleteBtn){
    batchDeleteBtn.disabled=count===0;
  }
  const total=appState().threads.length;
  const allSelected=total>0&&selectedThreadIds.size>=total;
  if(selectAllBtn){
    selectAllBtn.textContent=allSelected?'Deselect all':'Select all';
  }
}

export function setSelectMode(enabled){
  isSelectMode=enabled;
  const panel=document.querySelector('.threads-panel');
  if(isSelectMode){
    selectModeBtn?.classList.add('active');
    selectModeBtn?.setAttribute('aria-pressed','true');
    batchBar?.removeAttribute('hidden');
    panel?.classList.add('select-mode');
  }else{
    selectModeBtn?.classList.remove('active');
    selectModeBtn?.setAttribute('aria-pressed','false');
    batchBar?.setAttribute('hidden','');
    panel?.classList.remove('select-mode');
    selectedThreadIds.clear();
  }
  updateBatchBarState();
  renderThreads();
}

export function renderThreads(){
  const listEl=list||document.querySelector('#thread-list');
  if(!listEl)return;
  listEl.replaceChildren();
  const prefs=loadPreferences();
  let threads=[...(appState().threads || [])];

  if(!prefs.showArchived){
    threads=threads.filter(t=>t.status!=='ARCHIVED');
  }

  if(prefs.conversationsSort==='alpha'){
    threads.sort((a,b)=>(a.title||'').localeCompare(b.title||''));
  }else if(prefs.conversationsSort==='created_desc'){
    threads.sort((a,b)=>(b.created_at||'').localeCompare(a.created_at||''));
  }else{
    // Default: updated_desc
    threads.sort((a,b)=>(b.updated_at||'').localeCompare(a.updated_at||''));
  }

  for(const thread of threads){
    const item=document.createElement('li');
    item.className='thread-item';
    item.dataset.threadId=thread.thread_id;
    const isArchived=thread.status==='ARCHIVED';
    if(isArchived){
      item.classList.add('is-archived');
    }

    if(isSelectMode){
      if(selectedThreadIds.has(thread.thread_id)){
        item.classList.add('is-selected');
      }

      const checkbox=document.createElement('input');
      checkbox.type='checkbox';
      checkbox.className='thread-select-checkbox';
      checkbox.checked=selectedThreadIds.has(thread.thread_id);
      checkbox.setAttribute('aria-label',`Select ${thread.title}`);
      checkbox.addEventListener('change',event=>{
        event.stopPropagation();
        toggleThreadSelection(thread.thread_id);
      });
      item.append(checkbox);
    }

    // Title button
    const button=document.createElement('button');
    button.type='button';
    button.className='thread-button';
    button.dataset.threadId=thread.thread_id;
    button.setAttribute('aria-current',String(appState().currentThread?.thread_id===thread.thread_id));
    const titleSpan=document.createElement('span');
    titleSpan.className='thread-title-text';
    titleSpan.textContent=thread.title;
    button.append(titleSpan);
    if(isArchived){
      const badge=document.createElement('span');
      badge.className='thread-archived-badge';
      badge.textContent='Archived';
      button.append(badge);
    }
    button.addEventListener('click',()=>{
      if(isSelectMode){
        toggleThreadSelection(thread.thread_id);
      }else{
        selectThread(thread.thread_id);
      }
    });
    item.append(button);

    if(!isSelectMode){
      // Three-dot action menu container
      const menuWrapper=document.createElement('div');
      menuWrapper.className='thread-menu-wrapper';

      const menuTrigger=document.createElement('button');
      menuTrigger.type='button';
      menuTrigger.className='thread-menu-trigger';
      menuTrigger.setAttribute('aria-label',`Actions for ${thread.title}`);
      menuTrigger.setAttribute('aria-haspopup','menu');
      menuTrigger.setAttribute('aria-expanded','false');
      menuTrigger.title='Conversation actions';
      menuTrigger.append(makeIcon('dots'));

      const dropdown=document.createElement('div');
      dropdown.className='thread-menu-dropdown';
      dropdown.setAttribute('role','menu');
      dropdown.setAttribute('hidden','');

      // Menu Item: Rename
      const renameItem=document.createElement('button');
      renameItem.type='button';
      renameItem.className='thread-menu-item';
      renameItem.setAttribute('role','menuitem');
      renameItem.append(makeIcon('rename'),makeLabelSpan('Rename'));
      renameItem.addEventListener('click',event=>{
        event.stopPropagation();
        closeAllThreadMenus();
        startSidebarInlineRename(item,thread,button);
      });

      // Menu Item: Export
      const exportItem=document.createElement('button');
      exportItem.type='button';
      exportItem.className='thread-menu-item';
      exportItem.setAttribute('role','menuitem');
      exportItem.append(makeIcon('export'),makeLabelSpan('Export'));
      exportItem.addEventListener('click',event=>{
        event.stopPropagation();
        closeAllThreadMenus();
        exportThreadById(thread.thread_id);
      });

      // Menu Item: Archive / Unarchive
      const archiveItem=document.createElement('button');
      archiveItem.type='button';
      archiveItem.className='thread-menu-item';
      archiveItem.setAttribute('role','menuitem');
      if(isArchived){
        archiveItem.append(makeIcon('unarchive'),makeLabelSpan('Unarchive'));
        archiveItem.addEventListener('click',async event=>{
          event.stopPropagation();
          closeAllThreadMenus();
          await unarchiveThreadAction(thread);
        });
      }else{
        archiveItem.append(makeIcon('archive'),makeLabelSpan('Archive'));
        archiveItem.addEventListener('click',async event=>{
          event.stopPropagation();
          closeAllThreadMenus();
          await archiveThreadAction(thread);
        });
      }

      // Menu Item: Delete
      const deleteItem=document.createElement('button');
      deleteItem.type='button';
      deleteItem.className='thread-menu-item danger';
      deleteItem.setAttribute('role','menuitem');
      deleteItem.append(makeIcon('delete'),makeLabelSpan('Delete'));
      deleteItem.addEventListener('click',event=>{
        event.stopPropagation();
        closeAllThreadMenus();
        openDeleteConfirmationDialog(thread);
      });

      dropdown.append(renameItem,exportItem,archiveItem,deleteItem);

      menuTrigger.addEventListener('click',event=>{
        event.stopPropagation();
        const isExpanded=dropdown.hasAttribute('hidden');
        closeAllThreadMenus();
        if(isExpanded){
          dropdown.removeAttribute('hidden');
          menuTrigger.setAttribute('aria-expanded','true');
          activeMenuThreadId=thread.thread_id;
        }
      });

      menuWrapper.append(menuTrigger,dropdown);
      item.append(menuWrapper);
    }

    listEl.append(item);
  }
}

function startSidebarInlineRename(itemEl,thread,buttonEl){
  const input=document.createElement('input');
  input.type='text';
  input.className='thread-inline-rename-input';
  input.value=thread.title;
  input.maxLength=160;
  input.setAttribute('aria-label','Rename conversation');

  buttonEl.style.display='none';
  itemEl.prepend(input);
  input.focus();
  input.select();

  let committed=false;

  async function saveRename(){
    if(committed)return;
    const newTitle=input.value.trim();
    if(!newTitle){
      setStatus('Conversation title cannot be blank');
      cancelRename();
      return;
    }
    if(newTitle===thread.title){
      cancelRename();
      return;
    }
    committed=true;
    input.disabled=true;
    input.classList.add('saving');
    setStatus('Renaming conversation…');

    try{
      const updated=await mutateJSON(`/api/v2/threads/${encodeURIComponent(thread.thread_id)}/title`,{title:newTitle});
      thread.title=updated.title;
      const titleSpan=buttonEl.querySelector('.thread-title-text');
      if(titleSpan)titleSpan.textContent=updated.title;
      else buttonEl.textContent=updated.title;
      if(appState().currentThread?.thread_id===thread.thread_id){
        appState().currentThread.title=updated.title;
        const headerTitle=document.querySelector('#conversation-title');
        if(headerTitle)headerTitle.textContent=updated.title;
      }
      setStatus('Conversation renamed');
    }catch(error){
      setStatus(error.message);
    }finally{
      input.remove();
      buttonEl.style.display='';
      buttonEl.focus();
    }
  }

  function cancelRename(){
    if(committed)return;
    committed=true;
    input.remove();
    buttonEl.style.display='';
    buttonEl.focus();
  }

  input.addEventListener('keydown',event=>{
    if(event.key==='Enter'){
      event.preventDefault();
      saveRename();
    }else if(event.key==='Escape'){
      event.preventDefault();
      cancelRename();
    }
  });

  input.addEventListener('blur',()=>{
    if(!committed)cancelRename();
  });
}

function setupHeaderRename(){
  const headerTitle=document.querySelector('#conversation-title');
  const renameBtn=document.querySelector('#rename-conversation-btn');
  if(!headerTitle||!renameBtn)return;

  function triggerHeaderRename(){
    const current=appState().currentThread;
    if(!current)return;

    const input=document.createElement('input');
    input.type='text';
    input.id='header-rename-input';
    input.className='header-rename-input';
    input.value=current.title;
    input.maxLength=160;
    input.setAttribute('aria-label','Conversation title');

    headerTitle.style.display='none';
    renameBtn.style.display='none';
    headerTitle.after(input);
    input.focus();
    input.select();

    let committed=false;

    async function saveHeaderRename(){
      if(committed)return;
      const newTitle=input.value.trim();
      if(!newTitle){
        setStatus('Conversation title cannot be blank');
        cancelHeaderRename();
        return;
      }
      if(newTitle===current.title){
        cancelHeaderRename();
        return;
      }
      committed=true;
      input.disabled=true;
      input.classList.add('saving');
      setStatus('Renaming conversation…');

      try{
        const updated=await mutateJSON(`/api/v2/threads/${encodeURIComponent(current.thread_id)}/title`,{title:newTitle});
        current.title=updated.title;
        current.updated_at=updated.updated_at;
        headerTitle.textContent=updated.title;
        const matching=appState().threads.find(t=>t.thread_id===current.thread_id);
        if(matching)matching.title=updated.title;
        renderThreads();
        setStatus('Conversation renamed');
      }catch(error){
        setStatus(error.message);
      }finally{
        input.remove();
        headerTitle.style.display='';
        renameBtn.style.display='';
        renameBtn.focus();
      }
    }

    function cancelHeaderRename(){
      if(committed)return;
      committed=true;
      input.remove();
      headerTitle.style.display='';
      renameBtn.style.display='';
      renameBtn.focus();
    }

    input.addEventListener('keydown',event=>{
      if(event.key==='Enter'){
        event.preventDefault();
        saveHeaderRename();
      }else if(event.key==='Escape'){
        event.preventDefault();
        cancelHeaderRename();
      }
    });

    input.addEventListener('blur',()=>{
      if(!committed)cancelHeaderRename();
    });
  }

  renameBtn.addEventListener('click',triggerHeaderRename);
  headerTitle.addEventListener('dblclick',triggerHeaderRename);
}

function openDeleteConfirmationDialog(thread){
  if(!deleteDialog)return;
  threadPendingDelete=thread;

  if(deleteDialogTitle){
    deleteDialogTitle.textContent=`"${thread.title}"`;
  }

  // Check if thread has an active turn
  const activeTurn=[...(thread.turns||[])].reverse().find(turn=>['QUEUED','RUNNING'].includes(turn.status));
  const isActiveThreadRunning=(appState().currentThread?.thread_id===thread.thread_id)&&Boolean(activeTurn);

  if(isActiveThreadRunning||activeTurn){
    if(deleteDialogWarning)deleteDialogWarning.hidden=false;
    if(deleteDialogConfirmBtn)deleteDialogConfirmBtn.disabled=true;
  }else{
    if(deleteDialogWarning)deleteDialogWarning.hidden=true;
    if(deleteDialogConfirmBtn)deleteDialogConfirmBtn.disabled=false;
  }

  deleteDialog.showModal();
}

function setupDeleteDialogListeners(){
  if(!deleteDialog)return;

  deleteDialogCancelBtn?.addEventListener('click',()=>{
    deleteDialog.close();
    threadPendingDelete=null;
  });

  deleteDialog.addEventListener('cancel',()=>{
    threadPendingDelete=null;
  });

  deleteDialogConfirmBtn?.addEventListener('click',async()=>{
    if(!threadPendingDelete)return;
    const target=threadPendingDelete;
    deleteDialogConfirmBtn.disabled=true;
    setStatus('Deleting conversation…');

    try{
      await mutateJSON(`/api/v2/threads/${encodeURIComponent(target.thread_id)}/delete`,{});
      deleteDialog.close();
      const threads=await loadThreads();
      if(appState().currentThread?.thread_id===target.thread_id){
        if(threads.length)await selectThread(threads[0].thread_id);
        else await newThread();
      }
      setStatus('Conversation deleted');
    }catch(error){
      setStatus(error.message);
    }finally{
      deleteDialogConfirmBtn.disabled=false;
      threadPendingDelete=null;
    }
  });
}

function openBatchDeleteDialog(){
  if(!batchDeleteDialog||selectedThreadIds.size===0)return;
  const selectedThreads=appState().threads.filter(t=>selectedThreadIds.has(t.thread_id));
  if(selectedThreads.length===0)return;

  if(batchDeleteCountLabel){
    batchDeleteCountLabel.textContent=`${selectedThreads.length} conversation${selectedThreads.length===1?'':'s'}`;
  }

  if(batchDeletePreviewList){
    batchDeletePreviewList.replaceChildren();
    for(const t of selectedThreads){
      const row=document.createElement('div');
      row.className='batch-preview-item';
      const activeTurn=(t.turns||[]).find(turn=>['QUEUED','RUNNING'].includes(turn.status));
      if(activeTurn){
        row.classList.add('blocked');
        const warnIcon=document.createElement('span');
        warnIcon.setAttribute('aria-hidden','true');
        warnIcon.style.display='inline-flex';
        warnIcon.style.verticalAlign='middle';
        warnIcon.style.marginRight='4px';
        warnIcon.append(makeIcon('warn'));
        row.append(warnIcon,`[Running] ${t.title}`);
      }else{
        row.textContent=`• ${t.title}`;
      }
      batchDeletePreviewList.append(row);
    }
  }

  const activeThreads=selectedThreads.filter(t=>(t.turns||[]).some(turn=>['QUEUED','RUNNING'].includes(turn.status)));
  const inactiveThreads=selectedThreads.filter(t=>!(t.turns||[]).some(turn=>['QUEUED','RUNNING'].includes(turn.status)));

  if(activeThreads.length>0){
    if(batchDeleteActiveWarning)batchDeleteActiveWarning.hidden=false;
    if(batchDeleteActiveMsg){
      if(inactiveThreads.length===0){
        batchDeleteActiveMsg.textContent='All selected conversations have active running turns and cannot be deleted. Please stop or wait for them to finish.';
      }else{
        batchDeleteActiveMsg.textContent=`${activeThreads.length} conversation(s) have active turns and will be skipped. Only ${inactiveThreads.length} will be deleted.`;
      }
    }
    if(batchDeleteConfirmBtn){
      batchDeleteConfirmBtn.disabled=inactiveThreads.length===0;
      batchDeleteConfirmBtn.textContent=inactiveThreads.length>0?`Delete ${inactiveThreads.length} Permanently`:'Cannot Delete Active';
    }
  }else{
    if(batchDeleteActiveWarning)batchDeleteActiveWarning.hidden=true;
    if(batchDeleteConfirmBtn){
      batchDeleteConfirmBtn.disabled=false;
      batchDeleteConfirmBtn.textContent=`Delete ${selectedThreads.length} Permanently`;
    }
  }

  batchDeleteDialog.showModal();
}

function setupBatchDeleteListeners(){
  selectModeBtn?.addEventListener('click',()=>{
    setSelectMode(!isSelectMode);
  });

  selectAllBtn?.addEventListener('click',()=>{
    const total=appState().threads.length;
    if(selectedThreadIds.size>=total){
      selectedThreadIds.clear();
    }else{
      for(const t of appState().threads){
        selectedThreadIds.add(t.thread_id);
      }
    }
    updateBatchBarState();
    renderThreads();
  });

  batchCancelBtn?.addEventListener('click',()=>{
    setSelectMode(false);
  });

  batchDeleteBtn?.addEventListener('click',()=>{
    openBatchDeleteDialog();
  });

  batchDeleteCancelBtn?.addEventListener('click',()=>{
    batchDeleteDialog?.close();
  });

  batchDeleteConfirmBtn?.addEventListener('click',async()=>{
    if(!batchDeleteDialog||selectedThreadIds.size===0)return;
    const selectedThreads=appState().threads.filter(t=>selectedThreadIds.has(t.thread_id));
    const idsToDelete=selectedThreads
      .filter(t=>!(t.turns||[]).some(turn=>['QUEUED','RUNNING'].includes(turn.status)))
      .map(t=>t.thread_id);

    if(idsToDelete.length===0){
      setStatus('No deletable conversations selected');
      batchDeleteDialog.close();
      return;
    }

    batchDeleteConfirmBtn.disabled=true;
    setStatus(`Deleting ${idsToDelete.length} conversation(s)…`);

    try{
      const result=await mutateJSON('/api/v2/threads/batch-delete',{thread_ids:idsToDelete});
      batchDeleteDialog.close();
      const currentId=appState().currentThread?.thread_id;
      const threads=await loadThreads();
      if(currentId&&idsToDelete.includes(currentId)){
        if(threads.length)await selectThread(threads[0].thread_id);
        else await newThread();
      }
      setSelectMode(false);
      const count=result?.deleted?.length??idsToDelete.length;
      setStatus(`Successfully deleted ${count} conversation(s)`);
    }catch(error){
      setStatus(error.message);
    }finally{
      batchDeleteConfirmBtn.disabled=false;
    }
  });
}

function setupSidebarResize(){
  const prefs=loadPreferences();
  const updateEnlargeBtnState=(isEnlarged)=>{
    if(!enlargeBtn)return;
    enlargeBtn.setAttribute('aria-pressed',String(isEnlarged));
    enlargeBtn.classList.toggle('active',isEnlarged);
    enlargeBtn.title=isEnlarged
      ?'Restore standard conversations bar (280px)'
      :'Enlarge conversations bar (440px)';
  };

  const prefSidebarWidthSelect=document.querySelector('#pref-sidebar-width');

  const syncSidebarWidthSelector=(width)=>{
    if(!prefSidebarWidthSelect)return;
    const strVal=String(width);
    const presetValues=['280','360','440','520'];
    let customOpt=prefSidebarWidthSelect.querySelector('option[data-custom="true"]');
    if(!presetValues.includes(strVal)){
      if(!customOpt){
        customOpt=document.createElement('option');
        customOpt.dataset.custom='true';
        prefSidebarWidthSelect.append(customOpt);
      }
      customOpt.value=strVal;
      customOpt.textContent=`Custom (${strVal}px)`;
    }else if(customOpt){
      customOpt.remove();
    }
    prefSidebarWidthSelect.value=strVal;
  };

  const initialWidth=prefs.sidebarWidth||280;
  updateEnlargeBtnState(initialWidth >= 440);
  syncSidebarWidthSelector(initialWidth);

  enlargeBtn?.addEventListener('click',()=>{
    const currentPrefs=loadPreferences();
    const currentW=currentPrefs.sidebarWidth||280;
    const targetWidth=currentW>=440?280:440;
    savePreferences({sidebarWidth:targetWidth});
    setStatus(targetWidth>=440?'Conversations bar enlarged (440px)':'Conversations bar restored (280px)');
  });

  document.addEventListener('preferences-changed',e=>{
    const p=e.detail;
    if(!p)return;
    const activeW=p.sidebarWidth||280;
    updateEnlargeBtnState(activeW >= 440);
    syncSidebarWidthSelector(activeW);
    if(sidebarResizer)sidebarResizer.setAttribute('aria-valuenow',String(activeW));
  });

  if(sidebarResizer){
    let isDragging=false;
    const workspace=document.querySelector('.workspace');

    const onMouseDown=(e)=>{
      e.preventDefault();
      isDragging=true;
      workspace?.classList.add('is-resizing');
      sidebarResizer.classList.add('is-dragging');
      document.body.style.cursor='col-resize';
      window.addEventListener('mousemove',onMouseMove);
      window.addEventListener('mouseup',onMouseUp);
    };

    const onMouseMove=(e)=>{
      if(!isDragging)return;
      const newWidth=Math.min(600,Math.max(240,e.clientX));
      document.documentElement.style.setProperty('--sidebar-width',`${newWidth}px`);
      sidebarResizer.setAttribute('aria-valuenow',String(newWidth));
    };

    const onMouseUp=(e)=>{
      if(!isDragging)return;
      isDragging=false;
      workspace?.classList.remove('is-resizing');
      sidebarResizer.classList.remove('is-dragging');
      document.body.style.cursor='';
      window.removeEventListener('mousemove',onMouseMove);
      window.removeEventListener('mouseup',onMouseUp);

      const finalWidth=Math.min(600,Math.max(240,e.clientX));
      savePreferences({sidebarWidth:finalWidth});
    };

    sidebarResizer.addEventListener('mousedown',onMouseDown);

    sidebarResizer.addEventListener('keydown',e=>{
      if(e.key==='ArrowLeft'||e.key==='ArrowRight'){
        e.preventDefault();
        const currentW=parseInt(getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width'))||280;
        const delta=e.key==='ArrowRight'?20:-20;
        const newWidth=Math.min(600,Math.max(240,currentW+delta));
        savePreferences({sidebarWidth:newWidth});
      }
    });
  }
}

export async function exportThreadById(threadId){
  try{
    setStatus('Exporting conversation…');
    const payload=await getJSON(`/api/v2/threads/${encodeURIComponent(threadId)}/export`);
    const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob);
    const anchor=document.createElement('a');
    anchor.href=url;
    anchor.download=`mne-brain-${threadId}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setStatus('Conversation exported');
  }catch(error){
    setStatus(error.message);
  }
}

export async function archiveThreadAction(thread){
  if(!thread) return;
  const targetId = thread.thread_id;
  const activeTurn = (thread.turns || []).find(turn => ['QUEUED', 'RUNNING'].includes(turn.status));
  if (activeTurn) {
    setStatus('Cannot archive conversation with active turns');
    return;
  }
  try {
    setStatus('Archiving conversation…');
    await mutateJSON(`/api/v2/threads/${encodeURIComponent(targetId)}/archive`, {});
    thread.status = 'ARCHIVED';
    await loadThreads();
    setStatus('Conversation archived');

    const prefs = loadPreferences();
    if (appState().currentThread?.thread_id === targetId) {
      if (!prefs.showArchived) {
        const remaining = (appState().threads || []).filter(t => t.status !== 'ARCHIVED');
        if (remaining.length > 0) {
          await selectThread(remaining[0].thread_id);
        } else {
          await newThread();
        }
      } else {
        await selectThread(targetId);
      }
    }
  } catch (err) {
    setStatus(err.message);
  }
}

export async function unarchiveThreadAction(thread){
  if(!thread) return;
  const targetId = thread.thread_id;
  try {
    setStatus('Unarchiving conversation…');
    await mutateJSON(`/api/v2/threads/${encodeURIComponent(targetId)}/unarchive`, {});
    thread.status = 'ACTIVE';
    await loadThreads();
    setStatus('Conversation unarchived');
    if (appState().currentThread?.thread_id === targetId) {
      await selectThread(targetId);
    }
  } catch (err) {
    setStatus(err.message);
  }
}

export async function loadThreads(query=''){
  const payload=await getJSON('/api/v2/threads'+(query?`?search=${encodeURIComponent(query)}`:''));
  appState().threads=payload?.threads||[];
  renderThreads();
  return appState().threads;
}

export async function selectThread(threadId){
  const thread=await getJSON(`/api/v2/threads/${encodeURIComponent(threadId)}`);
  appState().currentThread=thread;
  const titleEl=document.querySelector('#conversation-title');
  if(titleEl)titleEl.textContent=thread.title;
  const provSelect=document.querySelector('#provider-select');
  if(provSelect)provSelect.value=thread.engine_id;
  const modSelect=document.querySelector('#model-select');
  if(modSelect)modSelect.value=thread.model_id;
  const permSelect=document.querySelector('#permission-mode');
  if(permSelect)permSelect.value=thread.permission_mode;

  const isArchived=thread.status==='ARCHIVED';
  const composerInput=document.querySelector('#composer-input');
  const sendBtn=document.querySelector('#send-turn');
  const attachBtn=document.querySelector('#attach-file-btn');
  const modelBtn=document.querySelector('#model-picker-btn');
  const archivedBanner=document.querySelector('#composer-archived-banner');
  const statusEl=document.querySelector('#turn-status');

  if(composerInput){
    composerInput.disabled=isArchived;
    if(isArchived)composerInput.placeholder='This conversation is archived and read-only.';
    else composerInput.placeholder='Ask with an exact target and evidence need…';
  }
  if(sendBtn)sendBtn.disabled=isArchived;
  if(attachBtn)attachBtn.disabled=isArchived;
  if(modelBtn)modelBtn.disabled=isArchived;
  if(archivedBanner)archivedBanner.hidden=!isArchived;
  if(isArchived&&statusEl)statusEl.textContent='Archived · Read only';
  else if(!isArchived&&statusEl&&statusEl.textContent==='Archived · Read only')statusEl.textContent='Ready';

  if(window.location.hash!==`#thread=${thread.thread_id}`){
    window.history.replaceState(null,'',`#thread=${thread.thread_id}`);
  }
  renderThreads();
  emit('thread-selected',{thread});
  const active=[...(thread.turns||[])].reverse().find(turn=>['QUEUED','RUNNING'].includes(turn.status));
  if(active)startTurnStream(active);
}

document.querySelector('#composer-unarchive-btn')?.addEventListener('click',async()=>{
  if(appState().currentThread){
    await unarchiveThreadAction(appState().currentThread);
  }
});

function isThreadEmpty(thread){
  if(!thread || !thread.thread_id)return false;
  if((thread.turn_ids&&thread.turn_ids.length>0)||(thread.turns&&thread.turns.length>0)||(thread.messages&&thread.messages.length>0))return false;
  if(appState().currentThread?.thread_id===thread.thread_id){
    const userMsg=document.querySelector('#message-stream .message.user');
    const asstMsg=document.querySelector('#message-stream .message.assistant');
    if(userMsg||asstMsg)return false;
  }
  return true;
}

function nextConversationTitle(){
  let maxNum=0;
  for(const t of (appState().threads || [])){
    const match=t.title?.match(/^Conversation\s+(\d+)$/i);
    if(match){
      const n=parseInt(match[1],10);
      if(n>maxNum)maxNum=n;
    }
  }
  const thCount = (appState().threads || []).length;
  return `Conversation ${Math.max(maxNum+1, thCount+1)}`;
}

let newThreadInFlight = null;

export async function newThread(){
  if(newThreadInFlight){
    return newThreadInFlight;
  }
  newThreadInFlight = (async ()=>{
    try {
      await _doNewThread();
    } finally {
      newThreadInFlight = null;
    }
  })();
  return newThreadInFlight;
}

async function _doNewThread(){
  const catalogPromise = getProvidersCatalogPromise?.();
  if(catalogPromise){
    try {
      await catalogPromise;
    } catch (_) {}
  }

  const current=appState().currentThread;
  const input=document.querySelector('#composer-input');
  const prefs=loadPreferences();

  const resolved = resolveTargetEngineAndModel(prefs, appState().engines || []);
  let targetEngine = resolved.engine_id || document.querySelector('#provider-select')?.value || 'antigravity';
  let targetModel = resolved.model_id || document.querySelector('#model-select')?.value || undefined;

  if(current && isThreadEmpty(current)){
    if(input){input.value='';input.focus();}
    emit('clear-composer-attachments');
    if(targetEngine && (current.engine_id !== targetEngine || (targetModel && current.model_id !== targetModel))){
      try{
        await mutateJSON(`/api/v2/threads/${encodeURIComponent(current.thread_id)}/engine`,{engine_id:targetEngine,model_id:targetModel});
        current.engine_id=targetEngine;
        current.model_id=targetModel;
        const provSelect=document.querySelector('#provider-select');
        if(provSelect)provSelect.value=targetEngine;
        const modSelect=document.querySelector('#model-select');
        if(modSelect)modSelect.value=targetModel;
      }catch(err){
        setStatus(err.message || 'Failed to update conversation engine');
      }
    }
    setStatus('Ready for new conversation');
    return;
  }

  const emptyExisting=(appState().threads || []).find(t=>isThreadEmpty(t));
  if(emptyExisting&&emptyExisting.thread_id!==current?.thread_id){
    await selectThread(emptyExisting.thread_id);
    if(input){input.value='';input.focus();}
    emit('clear-composer-attachments');
    if(targetEngine && (emptyExisting.engine_id !== targetEngine || (targetModel && emptyExisting.model_id !== targetModel))){
      try{
        await mutateJSON(`/api/v2/threads/${encodeURIComponent(emptyExisting.thread_id)}/engine`,{engine_id:targetEngine,model_id:targetModel});
        emptyExisting.engine_id=targetEngine;
        emptyExisting.model_id=targetModel;
        const provSelect=document.querySelector('#provider-select');
        if(provSelect)provSelect.value=targetEngine;
        const modSelect=document.querySelector('#model-select');
        if(modSelect)modSelect.value=targetModel;
      }catch(err){
        setStatus(err.message || 'Failed to update conversation engine');
      }
    }
    setStatus('Ready for new conversation');
    return;
  }

  if(input)input.value='';
  emit('clear-composer-attachments');
  setStatus('Creating new conversation…');
  const title=nextConversationTitle();
  const thread=await mutateJSON('/api/v2/threads',{title,engine_id:targetEngine,model_id:targetModel,permission_mode:'OWNER_DIRECT'});
  await loadThreads();
  if(thread?.thread_id){
    await selectThread(thread.thread_id);
  }
  if(input)input.focus();
  setStatus('Ready');
}

async function newThreadForEngine(engine,model,prompt){
  const current=appState().currentThread;
  const input=document.querySelector('#composer-input');
  if(isThreadEmpty(current)){
    await mutateJSON(`/api/v2/threads/${encodeURIComponent(current.thread_id)}/engine`,{engine_id:engine,model_id:model});
    current.engine_id=engine;
    current.model_id=model;
    document.querySelector('#provider-select').value=engine;
    document.querySelector('#model-select').value=model;
    renderThreads();
    if(prompt)document.dispatchEvent(new CustomEvent('retry-prompt',{detail:{content:prompt}}));
    if(input)input.focus();
    return;
  }
  const emptyExisting=appState().threads.find(t=>isThreadEmpty(t));
  if(emptyExisting&&emptyExisting.thread_id!==current?.thread_id){
    await selectThread(emptyExisting.thread_id);
    await mutateJSON(`/api/v2/threads/${encodeURIComponent(emptyExisting.thread_id)}/engine`,{engine_id:engine,model_id:model});
    emptyExisting.engine_id=engine;
    emptyExisting.model_id=model;
    document.querySelector('#provider-select').value=engine;
    document.querySelector('#model-select').value=model;
    renderThreads();
    if(prompt)document.dispatchEvent(new CustomEvent('retry-prompt',{detail:{content:prompt}}));
    if(input)input.focus();
    return;
  }
  const selected=appState().engines.find(item=>item.engine_id===engine);
  const thread=await mutateJSON('/api/v2/threads',{title:nextConversationTitle(),engine_id:engine,model_id:model||selected?.default_model,permission_mode:'OWNER_DIRECT'});
  await loadThreads();
  await selectThread(thread.thread_id);
  if(prompt)document.dispatchEvent(new CustomEvent('retry-prompt',{detail:{content:prompt}}));
  if(input)input.focus();
}

document.querySelector('#new-thread')?.addEventListener('click',()=>newThread().catch(error=>setStatus(error.message)));
document.addEventListener('new-thread-engine',event=>newThreadForEngine(event.detail.engine_id,event.detail.model_id,event.detail.prompt).catch(error=>setStatus(error.message)));
search?.addEventListener('input',()=>loadThreads(search.value).catch(error=>setStatus(error.message)));

document.querySelector('#export-thread')?.addEventListener('click',async()=>{
  const thread=appState().currentThread;
  if(!thread)return;
  await exportThreadById(thread.thread_id);
});

const importFile=document.querySelector('#import-thread-file');
document.querySelector('#import-thread')?.addEventListener('click',()=>importFile?.click());
importFile?.addEventListener('change',async()=>{
  const file=importFile.files?.[0];if(!file)return;
  try{
    if(file.size>2000000)throw new Error('Import exceeds the 2 MB safety limit');
    const conversation=JSON.parse(await file.text());
    const thread=await mutateJSON('/api/v2/threads/import',{conversation});
    await loadThreads();
    await selectThread(thread.thread_id);
    setStatus('Conversation imported');
  }catch(error){setStatus(error.message);}finally{importFile.value='';}
});

function getHashThreadId() {
  const match = window.location.hash.match(/#thread=([A-Za-z0-9_-]+)/);
  return match ? match[1] : null;
}

window.addEventListener('hashchange', async () => {
  const tid = getHashThreadId();
  if (tid && appState().currentThread?.thread_id !== tid) {
    try {
      await loadThreads();
      await selectThread(tid);
    } catch (e) {
      console.warn('Could not select thread from hash:', e);
    }
  }
});

setupHeaderRename();
setupDeleteDialogListeners();
setupBatchDeleteListeners();
setupSidebarResize();

const initialThreadId = getHashThreadId();
loadThreads().then(async threads => {
  const prefs=loadPreferences();
  if (initialThreadId && threads.some(t => t.thread_id === initialThreadId)) {
    await selectThread(initialThreadId);
  } else if (prefs.restoreLastConversation && threads.length) {
    await selectThread(threads[0].thread_id);
  } else if (threads.length) {
    await selectThread(threads[0].thread_id);
  } else {
    await newThread();
  }
}).catch(error => setStatus(error.message));

document.addEventListener('owner-authenticated', () => {
  loadThreads().catch(error => setStatus(error.message));
});
