import {appState,getJSON,mutateJSON,setStatus} from './api.js';
import {loadPreferences,savePreferences,applyPreferences} from './preferences.js';

const engineSelect=document.querySelector('#provider-select');
const modelSelect=document.querySelector('#model-select');
const status=document.querySelector('#provider-status');
const settings=document.querySelector('#settings-panel');
const modelPickerBtn=document.querySelector('#model-picker-btn');
const modelPickerLabel=document.querySelector('#model-picker-label');
const modelPickerDropdown=document.querySelector('#model-picker-dropdown');
const modelSearchInput=document.querySelector('#model-search-input');
const modelSearchClear=document.querySelector('#model-search-clear');
const modelSearchCount=document.querySelector('#model-search-count');
const modelPickerList=document.querySelector('#model-picker-list');
let openCodeCatalog={providers:[],models:[]};
let lastServerSettings=null;

function formatLimit(num){
  if(num==null||num==='unknown'||isNaN(Number(num)))return num||'unknown';
  const n=Number(num);
  if(n>=1000000)return (n/1000000).toFixed(n%1000000===0?0:1)+'M';
  if(n>=1000)return Math.round(n/1000)+'k';
  return String(n);
}

function updateModelPickerLabel(){
  if(!modelPickerLabel)return;
  const engine=activeEngine();
  const model=(engine?.models||[]).find(item=>item.id===modelSelect.value);
  if(!model||modelSelect.value==='select-model'){
    modelPickerLabel.textContent=engine?.engine_id==='opencode'?'Choose an OpenCode model…':'Select model…';
    return;
  }
  if(engine?.engine_id==='opencode'){
    modelPickerLabel.textContent=`${model.display_name||model.model_id||model.id} · ${model.provider_id}`;
  }else{
    modelPickerLabel.textContent=model.label||model.display_name||model.id;
  }
}

function renderModelPickerOptions(query=''){
  if(!modelPickerList)return;
  modelPickerList.replaceChildren();
  const engine=activeEngine();
  const allModels=engine?.models||[];
  const q=query.trim().toLowerCase();
  const filtered=allModels.filter(m=>{
    if(!q)return true;
    const name=(m.display_name||m.label||'').toLowerCase();
    const id=(m.id||'').toLowerCase();
    const modelId=(m.model_id||'').toLowerCase();
    const provider=(m.provider_id||'').toLowerCase();
    const cost=(m.cost_classification||'').toLowerCase();
    return name.includes(q)||id.includes(q)||modelId.includes(q)||provider.includes(q)||cost.includes(q);
  });

  if(modelSearchCount){
    modelSearchCount.textContent=`${filtered.length} of ${allModels.length} models`;
  }

  if(!filtered.length){
    const empty=document.createElement('div');
    empty.className='model-picker-empty';
    empty.textContent=q?`No models matching "${query}"`:'No models available for this engine';
    modelPickerList.append(empty);
    return;
  }

  for(const model of filtered){
    const opt=document.createElement('button');
    opt.type='button';
    opt.className='model-picker-option';
    opt.dataset.modelId=model.id;
    opt.setAttribute('role','option');
    const isSelected=modelSelect.value===model.id;
    opt.setAttribute('aria-selected',String(isSelected));
    if(isSelected)opt.classList.add('selected');

    const header=document.createElement('div');
    header.className='model-opt-header';
    const name=document.createElement('span');
    name.className='model-opt-name';
    name.textContent=model.display_name||model.label||model.id;
    header.append(name);

    const tags=document.createElement('div');
    tags.className='model-opt-tags';
    if(model.provider_id){
      const pTag=document.createElement('span');
      pTag.className='model-badge model-badge-provider';
      pTag.textContent=model.provider_id;
      tags.append(pTag);
    }
    if(model.cost_classification==='FREE'){
      const fTag=document.createElement('span');
      fTag.className='model-badge model-badge-free';
      fTag.textContent='FREE';
      tags.append(fTag);
    }
    header.append(tags);
    opt.append(header);

    const sub=document.createElement('div');
    sub.className='model-opt-sub';
    if(model.description){
      const description=document.createElement('span');
      description.textContent=model.description;
      sub.append(description);
    }
    if(model.context_limit){
      const ctxSpan=document.createElement('span');
      ctxSpan.textContent=`ctx ${formatLimit(model.context_limit)}`;
      sub.append(ctxSpan);
    }
    if(model.output_limit){
      const outSpan=document.createElement('span');
      outSpan.textContent=`out ${formatLimit(model.output_limit)}`;
      sub.append(outSpan);
    }
    if(model.tool_support){
      const tSpan=document.createElement('span');
      tSpan.textContent='tools ✓';
      sub.append(tSpan);
    }
    if(model.reasoning){
      const rSpan=document.createElement('span');
      rSpan.textContent='reasoning ✓';
      sub.append(rSpan);
    }
    if(sub.hasChildNodes()){
      opt.append(sub);
    }

    opt.addEventListener('click',()=>{
      selectModel(model.id);
    });

    modelPickerList.append(opt);
  }
}

function selectModel(modelId){
  modelSelect.value=modelId;
  updateModelPickerLabel();
  closeModelPicker();
  modelSelect.dispatchEvent(new Event('change'));
}

function openModelPicker(){
  if(!modelPickerDropdown)return;
  modelPickerDropdown.removeAttribute('hidden');
  modelPickerBtn?.setAttribute('aria-expanded','true');
  if(modelSearchInput){
    modelSearchInput.value='';
    if(modelSearchClear)modelSearchClear.hidden=true;
  }
  renderModelPickerOptions('');
  const rect=modelPickerDropdown.getBoundingClientRect();
  if(rect.right > window.innerWidth - 16){
    const overflow=rect.right - (window.innerWidth - 16);
    modelPickerDropdown.style.left=`-${overflow}px`;
  }else{
    modelPickerDropdown.style.left='0';
  }
  if(modelSearchInput)modelSearchInput.focus();
  const selectedNode=modelPickerList?.querySelector('.model-picker-option.selected');
  if(selectedNode){
    selectedNode.scrollIntoView({block:'nearest'});
  }
}

function closeModelPicker(){
  if(!modelPickerDropdown)return;
  modelPickerDropdown.setAttribute('hidden','');
  modelPickerBtn?.setAttribute('aria-expanded','false');
}

function readinessCard(id,title,health,detail){
  const root=document.querySelector(id);
  if(!root)return;
  root.replaceChildren();
  const badge=document.createElement('span');
  const statusClass=health.status==='READY'?'configured':health.status==='AUTHENTICATION_REQUIRED'?'warning':'missing';
  badge.className=`provider-health ${statusClass}`;
  badge.textContent=health.status;
  const heading=document.createElement('h3');
  heading.textContent=title;
  const text=document.createElement('p');
  text.textContent=detail;
  root.append(badge,heading,text);
  if((health.missing_prerequisites||[]).length){
    const list=document.createElement('ul');
    for(const value of health.missing_prerequisites){
      const item=document.createElement('li');
      item.textContent=value;
      list.append(item);
    }
    root.append(list);
  }
}

function activeEngine(){
  return appState().engines.find(item=>item.engine_id===engineSelect.value)||appState().engines[0];
}

function renderModels(selected){
  const engine=activeEngine();
  modelSelect.replaceChildren();
  if(engine?.engine_id==='opencode'){
    const placeholder=document.createElement('option');
    placeholder.value='select-model';
    placeholder.textContent='Choose an OpenCode provider model';
    placeholder.disabled=true;
    modelSelect.append(placeholder);
  }
  for(const model of engine?.models||[]){
    const option=document.createElement('option');
    option.value=model.id;
    if(engine?.engine_id==='opencode'){
      option.textContent=`${model.display_name} · ${model.provider_id} · ${model.cost_classification} · ctx ${model.context_limit||'unknown'} · out ${model.output_limit||'unknown'} · tools ${model.tool_support?'yes':'no'} · reasoning ${model.reasoning?'yes':'no'} · ${model.availability} · ${model.connection_status}`;
    }else{
      option.textContent=model.label;
    }
    modelSelect.append(option);
  }
  modelSelect.value=selected||engine?.default_model||'select-model';
  updateModelPickerLabel();
  if(modelPickerDropdown&&!modelPickerDropdown.hasAttribute('hidden')){
    renderModelPickerOptions(modelSearchInput?.value||'');
  }
  renderModelDetails();
}

function renderModelDetails(){
  const engine=activeEngine();
  const model=(engine?.models||[]).find(item=>item.id===modelSelect.value);
  const root=document.querySelector('#model-details');
  if(!root)return;
  if(!model){
    root.textContent=engine?.engine_id==='opencode'?'Select an exact connected OpenCode model; no automatic fallback will occur.':'';
    return;
  }
  if(engine?.engine_id==='opencode'){
    root.textContent=`${model.provider_id}/${model.model_id} · ${model.cost_classification} · context ${model.context_limit||'unknown'} · output ${model.output_limit||'unknown'} · tools ${model.tool_support?'supported':'not reported'} · reasoning ${model.reasoning?'reported':'not reported'} · ${model.availability} · ${model.connection_status}${model.warnings?.length?' · '+model.warnings.join(' · '):''}`;
  }else if(engine?.engine_id==='antigravity'){
    root.textContent=`${engine.label} · ${model.label}${model.effort?' · effort: '+model.effort:''} · Unrestricted Read & Governed Write Review`;
  }else if(engine?.engine_id==='codex'){
    root.textContent=`${engine.label} · ${model.description||model.label}${model.default_reasoning_effort?' · default reasoning: '+model.default_reasoning_effort:''}${model.supported_reasoning_efforts?.length?' · available reasoning: '+model.supported_reasoning_efforts.join(', '):''}`;
  }else{
    root.textContent=`${engine.label} · ${model.label}`;
  }
}

function renderEngines(){
  const es = engineSelect || document.querySelector('#provider-select');
  if(!es) return;
  es.replaceChildren();
  const engines = appState().engines || [];
  const readyEngine = engines.find(item => item.status === 'READY');
  const threadEngineId = appState().currentThread?.engine_id;
  const threadHasTurns = Boolean((appState().currentThread?.turn_ids || []).length || (appState().currentThread?.turns || []).length);

  for(const engine of engines){
    const option=document.createElement('option');
    option.value=engine.engine_id;
    option.textContent=`${engine.label} · ${engine.authentication} · ${engine.status}`;
    if(engine.status !== 'READY' && !(threadHasTurns && threadEngineId === engine.engine_id)){
      option.disabled = true;
    }
    es.append(option);
  }

  if(!threadHasTurns){
    const preferredEngine = engines.find(item => item.engine_id === threadEngineId && item.status === 'READY')
      || readyEngine
      || engines[0];
    es.value = preferredEngine ? preferredEngine.engine_id : 'antigravity';
  }else{
    es.value = threadEngineId || readyEngine?.engine_id || 'antigravity';
  }

  renderModels(appState().currentThread?.model_id);
}

function addText(parent,tag,text,className=''){
  const node=document.createElement(tag);
  node.textContent=text;
  if(className)node.className=className;
  parent.append(node);
  return node;
}

function renderOAuthMethods(){
  const providerSelect=document.querySelector('#opencode-oauth-provider');
  const select=document.querySelector('#opencode-oauth-method');
  if(!providerSelect||!select)return;
  const providerId=providerSelect.value;
  select.replaceChildren();
  const provider=openCodeCatalog.providers.find(item=>item.provider_id===providerId);
  for(const method of provider?.authentication_methods.filter(item=>item.type==='oauth')||[]){
    const option=document.createElement('option');
    option.value=String(method.index);
    option.textContent=method.label;
    select.append(option);
  }
  renderOAuthInputs();
}

function selectedOAuthMethod(){
  const providerSelect=document.querySelector('#opencode-oauth-provider');
  const methodSelect=document.querySelector('#opencode-oauth-method');
  if(!providerSelect||!methodSelect)return null;
  const provider=openCodeCatalog.providers.find(item=>item.provider_id===providerSelect.value);
  return provider?.authentication_methods.find(item=>item.type==='oauth'&&item.index===Number(methodSelect.value));
}

function renderOAuthInputs(){
  const root=document.querySelector('#opencode-oauth-inputs');
  if(!root)return;
  root.replaceChildren();
  for(const prompt of selectedOAuthMethod()?.prompts||[]){
    const label=document.createElement('label');
    label.textContent=prompt.message||prompt.label||prompt.key;
    let input;
    if(Array.isArray(prompt.options)&&prompt.options.length){
      input=document.createElement('select');
      for(const value of prompt.options){
        const option=document.createElement('option');
        option.value=typeof value==='string'?value:(value.value??value.label);
        option.textContent=typeof value==='string'?value:(value.label??value.value);
        input.append(option);
      }
    }else{
      input=document.createElement('input');
      input.type=prompt.type==='password'?'password':'text';
      input.autocomplete='off';
    }
    input.dataset.oauthKey=prompt.key;
    input.required=prompt.required!==false;
    label.append(input);
    root.append(label);
  }
}

function oauthInputs(){
  const result={};
  for(const input of document.querySelectorAll('#opencode-oauth-inputs [data-oauth-key]')){
    result[input.dataset.oauthKey]=input.value;
  }
  return result;
}

function refreshAuthSelects(){
  const api=document.querySelector('#opencode-api-provider');
  const oauth=document.querySelector('#opencode-oauth-provider');
  if(api)api.replaceChildren();
  if(oauth)oauth.replaceChildren();
  for(const provider of openCodeCatalog.providers){
    if(provider.authentication_methods.some(method=>method.type==='api')&&api){
      const option=document.createElement('option');
      option.value=provider.provider_id;
      option.textContent=provider.display_name;
      api.append(option);
    }
    if(provider.authentication_methods.some(method=>method.type==='oauth')&&oauth){
      const option=document.createElement('option');
      option.value=provider.provider_id;
      option.textContent=provider.display_name;
      oauth.append(option);
    }
  }
  renderOAuthMethods();
}

function renderOpenCodeProviders(unavailableMessage=''){
  const root=document.querySelector('#provider-settings-list');
  if(!root)return;
  root.replaceChildren();
  if(unavailableMessage){
    addText(root,'p',unavailableMessage,'tool-error');
  }
  if(!openCodeCatalog.providers.length&&!unavailableMessage){
    addText(root,'p','No OpenCode providers are available from the local runtime.','tool-error');
  }
  for(const provider of openCodeCatalog.providers){
    const card=document.createElement('section');
    card.className='provider-card';
    addText(card,'span',provider.connection_status,`provider-health ${provider.connected?'configured':'missing'}`);
    addText(card,'h3',provider.display_name);
    const free=openCodeCatalog.models.filter(model=>model.provider_id===provider.provider_id&&model.cost_classification==='FREE').length;
    addText(card,'p',`${provider.provider_id} · ${provider.model_count} models · ${free} free · source ${provider.source||'unknown'}`);
    if(provider.environment_refs.length){
      addText(card,'p',`Environment credentials supported: ${provider.environment_refs.join(', ')}`);
    }
    for(const warning of provider.warnings){
      addText(card,'p',warning,'tool-error');
    }
    if(provider.authentication_methods.some(item=>item.type==='api')){
      const connect=document.createElement('button');
      connect.type='button';
      connect.textContent=provider.connected?'Reconnect API key':'Connect API key';
      connect.addEventListener('click',()=>{
        const select=document.querySelector('#opencode-api-provider');
        if(select)select.value=provider.provider_id;
        document.querySelector('#opencode-api-key')?.focus();
      });
      card.append(connect);
    }
    for(const method of provider.authentication_methods.filter(item=>item.type==='oauth')){
      const start=document.createElement('button');
      start.type='button';
      start.textContent=`Start ${method.label}`;
      start.addEventListener('click',()=>{
        const select=document.querySelector('#opencode-oauth-provider');
        if(select)select.value=provider.provider_id;
        renderOAuthMethods();
        const mSelect=document.querySelector('#opencode-oauth-method');
        if(mSelect)mSelect.value=String(method.index);
        renderOAuthInputs();
        const panel=document.querySelector('#opencode-oauth-panel');
        if(panel)panel.open=true;
        panel?.scrollIntoView({behavior:'smooth',block:'nearest'});
        const statusEl=document.querySelector('#settings-status');
        if(statusEl)statusEl.textContent='Review any provider-specific prompts, then start through OpenCode.';
      });
      card.append(start);
    }
    const test=document.createElement('button');
    test.type='button';
    test.textContent='Test configuration';
    test.addEventListener('click',()=>providerAction('test',provider.provider_id));
    card.append(test);
    if(provider.connected){
      const disconnect=document.createElement('button');
      disconnect.type='button';
      disconnect.textContent='Disconnect';
      disconnect.addEventListener('click',()=>providerAction('disconnect',provider.provider_id));
      card.append(disconnect);
    }
    if(provider.custom){
      const remove=document.createElement('button');
      remove.type='button';
      remove.textContent='Remove custom provider';
      remove.addEventListener('click',async()=>{
        try{
          const result=await mutateJSON('/api/v2/opencode/custom-providers/remove',{provider_id:provider.provider_id});
          const statusEl=document.querySelector('#settings-status');
          if(statusEl)statusEl.textContent=result.status;
          await loadProviders();
        }catch(error){
          const statusEl=document.querySelector('#settings-status');
          if(statusEl)statusEl.textContent=error.message;
        }
      });
      card.append(remove);
    }
    root.append(card);
  }
  refreshAuthSelects();
}

function renderOperationsAndSafety(server){
  const p7Reads=document.querySelector('#safety-p7-reads');
  const p10Writes=document.querySelector('#safety-p10-writes');
  const ownerMode=document.querySelector('#safety-owner-mode');
  const loopback=document.querySelector('#safety-loopback');
  const storage=document.querySelector('#safety-storage');
  const externalAuth=document.querySelector('#safety-external-auth');
  const retentionStatus=document.querySelector('#conv-retention-status');

  if(p7Reads)p7Reads.textContent=server.p7_live_reads_enabled?'Globally Active':(server.p7_owner_scoped_live_reads_available?'Available (Requires Separate Activation)':'Disabled at Rest');
  if(p10Writes)p10Writes.textContent=server.p10_writes_enabled?'Enabled by Exception':'Disabled by Default · Requires Exact Single-Use Phrase';
  if(ownerMode)ownerMode.textContent=server.permission_mode?`${server.permission_mode} · Governed Policy`:'Not reported by server';
  if(loopback)loopback.textContent=server.bind_host?`Bound to loopback (${server.bind_host}) · Isolated from WAN`:'Bind host not reported by server';
  if(storage)storage.textContent=server.credential_storage?`Credential Store: ${server.credential_storage}`:'Credential store not reported by server';
  if(externalAuth)externalAuth.textContent=server.auto_authorize_redacted_conversation!==undefined?(server.auto_authorize_redacted_conversation?'Automatic Short-Lived Digest (<5 min)':'Manual Authorization Only'):'Not reported by server';
  if(retentionStatus)retentionStatus.textContent=server.conversation_retention?(server.conversation_retention==='LOCAL_STORAGE'?'Local Disk Retention (Repository Storage)':'In-Memory Only'):'Not reported by server';
}

function renderDiagnostics(server){
  const srvUrl=document.querySelector('#diag-server-url');
  const srvVer=document.querySelector('#diag-server-version');
  const codexVer=document.querySelector('#diag-codex-version');
  const opencodeVer=document.querySelector('#diag-opencode-version');
  const antigravityVer=document.querySelector('#diag-antigravity-version');
  const lastRefresh=document.querySelector('#diag-last-refresh');

  if(srvUrl)srvUrl.textContent=window.location.origin;
  if(srvVer)srvVer.textContent=server?.server_version||'Release 2 (P11)';
  if(codexVer)codexVer.textContent=server?.codex?.status||'Unknown';
  if(opencodeVer)opencodeVer.textContent=server?.opencode?(server.opencode.version?`OpenCode ${server.opencode.version} · ${server.opencode.status||'Unknown'}`:`OpenCode · ${server.opencode.status||'Unknown'}`):'Unknown';
  if(antigravityVer)antigravityVer.textContent=server?.antigravity?(server.antigravity.version?`Antigravity CLI ${server.antigravity.version} · ${server.antigravity.status||'Unknown'}`:`Antigravity CLI · ${server.antigravity.status||'Unknown'}`):'Unknown';
  if(lastRefresh)lastRefresh.textContent=new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'});
}

let providersCatalogPromise = null;

export function getProvidersCatalogPromise(){
  return providersCatalogPromise;
}

export async function loadProviders(){
  providersCatalogPromise = (async () => {
    const server=await getJSON('/api/v2/settings');
    lastServerSettings=server;

    readinessCard('#codex-readiness','Codex App Server readiness',server.codex,`ChatGPT session · ${server.codex?.sandbox||'restricted'} · ${server.codex?.approval_policy||'strict'} approvals · network ${server.codex?.network_access?'enabled':'off'}`);
    readinessCard('#opencode-readiness','OpenCode readiness',server.opencode,`Version ${server.opencode?.version||'unknown'} · turn timeout ${Math.round((server.opencode?.turn_timeout_seconds||0)/60)} min · Basic Auth ${server.opencode?.basic_auth||'disabled'} · native shell ${server.opencode?.native_shell||'disabled'} · native edits ${server.opencode?.native_edits||'disabled'}`);
    if(server.antigravity)readinessCard('#antigravity-readiness','Antigravity CLI readiness',server.antigravity,`Version ${server.antigravity?.version||'unknown'} · Unrestricted read & governed write review · Google AI session`);

    const [providersResult,enginesResult,catalogResult]=await Promise.allSettled([
      getJSON('/api/v2/providers'),
      getJSON('/api/v2/engines'),
      getJSON('/api/v2/opencode/providers')
    ]);

    const failures=[];
    if(providersResult.status==='fulfilled')appState().providers=providersResult.value.profiles||[];
    else failures.push(`Provider profiles: ${providersResult.reason.message}`);
    if(enginesResult.status==='fulfilled')appState().engines=enginesResult.value.engines||[];
    else failures.push(`Engine catalog: ${enginesResult.reason.message}`);
    if(catalogResult.status==='fulfilled')openCodeCatalog=catalogResult.value;
    else{openCodeCatalog={providers:[],models:[]};failures.push(`OpenCode catalog: ${catalogResult.reason.message}`);}

    renderEngines();
    renderOpenCodeProviders(catalogResult.status==='rejected'?failures.at(-1):'');
    renderOperationsAndSafety(server);
    renderDiagnostics(server);
    refreshDefaultEngineControls();

    const codexStatus=document.querySelector('#codex-status');
    if(codexStatus)codexStatus.textContent=`Codex ${server.codex?.status||'UNKNOWN'} · OpenCode ${server.opencode?.status||'UNKNOWN'}${server.antigravity?' · Antigravity '+server.antigravity.status:''}`;
    const liveStatus=document.querySelector('#live-status');
    if(liveStatus)liveStatus.textContent=server.p7_live_reads_enabled?'Globally active':(server.p7_owner_scoped_live_reads_available?'Available (Activation Required)':'Disabled at rest');
    const current=activeEngine();
    if(status)status.textContent=current?`${current.label} · ${modelSelect.value} · ${current.status}`:'No AI engine';
    const settingsStatus=document.querySelector('#settings-status');
    if(settingsStatus)settingsStatus.textContent=failures.length?failures.join(' · '):'All provider diagnostics loaded.';
  })();
  return providersCatalogPromise;
}

async function pinSelection(){
  const thread=appState().currentThread;
  if(!thread)return;
  if(engineSelect.value==='opencode'&&(!modelSelect.value||modelSelect.value==='select-model')){
    setStatus('Choose an available OpenCode model.');
    return;
  }
  if(thread.engine_id===engineSelect.value&&thread.model_id===modelSelect.value)return;
  if(thread.turn_ids?.length||thread.turns?.length){
    document.dispatchEvent(new CustomEvent('new-thread-engine',{detail:{engine_id:engineSelect.value,model_id:modelSelect.value}}));
    return;
  }
  try{
    const updated=await mutateJSON(`/api/v2/threads/${thread.thread_id}/engine`,{engine_id:engineSelect.value,model_id:modelSelect.value});
    appState().currentThread={...thread,...updated};
    if(status)status.textContent=`${activeEngine()?.label} · ${updated.model_id} · pinned to this conversation`;
    renderEngines();
  }catch(error){
    setStatus(error.message);
    engineSelect.value=thread.engine_id;
    renderModels(thread.model_id);
  }
}

engineSelect?.addEventListener('change',()=>{renderModels();pinSelection();});
modelSelect?.addEventListener('change',()=>{renderModelDetails();pinSelection();});

if(modelPickerBtn){
  modelPickerBtn.addEventListener('click',e=>{
    e.stopPropagation();
    if(!modelPickerDropdown||modelPickerDropdown.hasAttribute('hidden'))openModelPicker();
    else closeModelPicker();
  });
}

if(modelSearchInput){
  modelSearchInput.addEventListener('input',()=>{
    if(modelSearchClear)modelSearchClear.hidden=!modelSearchInput.value;
    renderModelPickerOptions(modelSearchInput.value);
  });
  modelSearchInput.addEventListener('keydown',e=>{
    if(e.key==='Escape'){
      e.stopPropagation();
      closeModelPicker();
      modelPickerBtn?.focus();
    }else if(e.key==='Enter'){
      e.preventDefault();
      const firstOpt=modelPickerList?.querySelector('.model-picker-option');
      if(firstOpt&&firstOpt.dataset.modelId){
        selectModel(firstOpt.dataset.modelId);
      }
    }else if(e.key==='ArrowDown'){
      e.preventDefault();
      const firstOpt=modelPickerList?.querySelector('.model-picker-option');
      if(firstOpt)firstOpt.focus();
    }
  });
}

if(modelSearchClear){
  modelSearchClear.addEventListener('click',()=>{
    modelSearchInput.value='';
    modelSearchClear.hidden=true;
    renderModelPickerOptions('');
    modelSearchInput.focus();
  });
}

if(modelPickerList){
  modelPickerList.addEventListener('keydown',e=>{
    const current=document.activeElement;
    if(!current||!current.classList.contains('model-picker-option'))return;
    if(e.key==='ArrowDown'){
      e.preventDefault();
      const next=current.nextElementSibling;
      if(next&&next.classList.contains('model-picker-option'))next.focus();
    }else if(e.key==='ArrowUp'){
      e.preventDefault();
      const prev=current.previousElementSibling;
      if(prev&&prev.classList.contains('model-picker-option'))prev.focus();
      else modelSearchInput?.focus();
    }else if(e.key==='Escape'){
      closeModelPicker();
      modelPickerBtn?.focus();
    }
  });
}

document.addEventListener('click',e=>{
  if(modelPickerDropdown&&!modelPickerDropdown.hasAttribute('hidden')){
    if(!e.target.closest('.model-picker-wrapper')){
      closeModelPicker();
    }
  }
});

window.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&modelPickerDropdown&&!modelPickerDropdown.hasAttribute('hidden')){
    closeModelPicker();
    modelPickerBtn?.focus();
  }
});

async function providerAction(action,providerId){
  const output=document.querySelector('#settings-status');
  try{
    if(output)output.textContent=`${action} in progress…`;
    const result=await mutateJSON(`/api/v2/opencode/providers/${action}`,{provider_id:providerId});
    if(output)output.textContent=`${result.status} · no credential material returned`;
    await loadProviders();
  }catch(error){
    if(output)output.textContent=error.message;
  }
}

document.querySelector('#settings-button')?.addEventListener('click',()=>{
  if(settings)settings.showModal();
  const output=document.querySelector('#settings-status');
  if(output)output.textContent='Refreshing provider diagnostics…';
  loadProviders().catch(error=>{if(output)output.textContent=error.message;});
  initSettingsFormControls();
});

document.querySelector('#refresh-opencode')?.addEventListener('click',async()=>{
  try{
    const output=document.querySelector('#settings-status');
    if(output)output.textContent='Refreshing OpenCode providers and models…';
    await mutateJSON('/api/v2/opencode/providers/refresh',{});
    await loadProviders();
    if(output)output.textContent='OpenCode catalog refreshed.';
  }catch(error){
    const output=document.querySelector('#settings-status');
    if(output)output.textContent=error.message;
  }
});

document.querySelector('#opencode-oauth-provider')?.addEventListener('change',renderOAuthMethods);
document.querySelector('#opencode-oauth-method')?.addEventListener('change',renderOAuthInputs);

document.querySelector('#opencode-api-key-form')?.addEventListener('submit',async event=>{
  event.preventDefault();
  const input=document.querySelector('#opencode-api-key');
  const apiKey=input.value;
  input.value='';
  try{
    const result=await mutateJSON('/api/v2/opencode/providers/connect-api',{provider_id:document.querySelector('#opencode-api-provider').value,api_key:apiKey});
    const output=document.querySelector('#settings-status');
    if(output)output.textContent=`${result.status} · credential sent directly to OpenCode and not returned`;
    await loadProviders();
  }catch(error){
    const output=document.querySelector('#settings-status');
    if(output)output.textContent=error.message;
  }
});

document.querySelector('#opencode-oauth-start')?.addEventListener('click',async()=>{
  const inputs=oauthInputs();
  for(const input of document.querySelectorAll('#opencode-oauth-inputs [data-oauth-key]'))input.value='';
  try{
    const result=await mutateJSON('/api/v2/opencode/providers/oauth/start',{provider_id:document.querySelector('#opencode-oauth-provider').value,method:Number(document.querySelector('#opencode-oauth-method').value),inputs});
    const output=document.querySelector('#settings-status');
    if(output)output.textContent=`${result.status} · ${result.instructions}`;
    const opened=window.open(result.authorization_url,'_blank','noopener,noreferrer');
    if(!opened&&output)output.textContent+=' · Browser popup was blocked.';
  }catch(error){
    const output=document.querySelector('#settings-status');
    if(output)output.textContent=error.message;
  }
});

document.querySelector('#opencode-oauth-complete-form')?.addEventListener('submit',async event=>{
  event.preventDefault();
  const codeInput=document.querySelector('#opencode-oauth-code');
  const code=codeInput.value;
  codeInput.value='';
  try{
    const result=await mutateJSON('/api/v2/opencode/providers/oauth/callback',{provider_id:document.querySelector('#opencode-oauth-provider').value,method:Number(document.querySelector('#opencode-oauth-method').value),code:code||undefined});
    const output=document.querySelector('#settings-status');
    if(output)output.textContent=result.status;
    await loadProviders();
  }catch(error){
    const output=document.querySelector('#settings-status');
    if(output)output.textContent=error.message;
  }
});

document.querySelector('#opencode-custom-provider-form')?.addEventListener('submit',async event=>{
  event.preventDefault();
  const keyInput=document.querySelector('#custom-provider-key');
  let apiKey=keyInput.value;
  keyInput.value='';
  try{
    const models=document.querySelector('#custom-provider-models').value.split(/\r?\n/).filter(Boolean).map(line=>{
      const [model_id,display_name,context,output]=line.split('|').map(value=>value.trim());
      const item={model_id,display_name};
      if(context)item.context_limit=Number(context);
      if(output)item.output_limit=Number(output);
      return item;
    });
    const headers=JSON.parse(document.querySelector('#custom-provider-headers').value||'{}');
    const environmentRef=document.querySelector('#custom-provider-env').value.trim();
    if(apiKey&&environmentRef)throw new Error('Choose either a one-time API key or an environment reference, not both.');
    const provider={
      provider_id:document.querySelector('#custom-provider-id').value.trim(),
      display_name:document.querySelector('#custom-provider-name').value.trim(),
      base_url:document.querySelector('#custom-provider-url').value.trim(),
      protocol:document.querySelector('#custom-provider-protocol').value,
      environment_ref:environmentRef||null,
      models,
      headers,
      allow_loopback:document.querySelector('#custom-provider-loopback').checked
    };
    const result=await mutateJSON('/api/v2/opencode/custom-providers/save',{provider});
    if(apiKey)await mutateJSON('/api/v2/opencode/providers/connect-api',{provider_id:provider.provider_id,api_key:apiKey});
    apiKey='';
    const output=document.querySelector('#settings-status');
    if(output)output.textContent=`${result.status} · non-secret metadata saved; OpenCode restarted safely`;
    event.target.reset();
    document.querySelector('#custom-provider-headers').value='{}';
    await loadProviders();
  }catch(error){
    apiKey='';
    const output=document.querySelector('#settings-status');
    if(output)output.textContent=error.message;
  }
});

// Settings Navigation Tabs Controller
function setupSettingsNavigation(){
  const navTabs=document.querySelectorAll('.settings-nav-tab');
  const panels=document.querySelectorAll('.settings-tab-panel');

  navTabs.forEach(tab=>{
    tab.addEventListener('click',()=>{
      const targetId=tab.dataset.target;
      navTabs.forEach(t=>{
        t.classList.toggle('active',t===tab);
        t.setAttribute('aria-selected',String(t===tab));
      });
      panels.forEach(p=>{
        const isMatch=p.id===targetId;
        p.classList.toggle('active',isMatch);
        p.hidden=!isMatch;
      });
    });
  });
}

// Presentation Preferences Form Controls
function initSettingsFormControls(){
  const prefs=loadPreferences();

  // General Controls
  const restoreCheck=document.querySelector('#pref-restore-conversation');
  if(restoreCheck){
    restoreCheck.checked=prefs.restoreLastConversation;
    restoreCheck.onchange=()=>savePreferences({restoreLastConversation:restoreCheck.checked});
  }

  const enterCheck=document.querySelector('#pref-enter-send');
  if(enterCheck){
    enterCheck.checked=prefs.enterToSend;
    enterCheck.onchange=()=>savePreferences({enterToSend:enterCheck.checked});
  }

  const timestampsCheck=document.querySelector('#pref-show-timestamps');
  if(timestampsCheck){
    timestampsCheck.checked=prefs.showTimestamps;
    timestampsCheck.onchange=()=>savePreferences({showTimestamps:timestampsCheck.checked});
  }

  const autoEvidenceCheck=document.querySelector('#pref-auto-open-evidence');
  if(autoEvidenceCheck){
    autoEvidenceCheck.checked=prefs.autoOpenEvidence;
    autoEvidenceCheck.onchange=()=>savePreferences({autoOpenEvidence:autoEvidenceCheck.checked});
  }

  // Appearance Controls
  const themeSelect=document.querySelector('#pref-theme-select');
  if(themeSelect){
    themeSelect.value=prefs.theme;
    themeSelect.onchange=()=>savePreferences({theme:themeSelect.value});
  }

  const accentSelect=document.querySelector('#pref-accent-select');
  if(accentSelect){
    accentSelect.value=prefs.accent;
    accentSelect.onchange=()=>savePreferences({accent:accentSelect.value});
  }

  const densitySelect=document.querySelector('#pref-density-select');
  if(densitySelect){
    densitySelect.value=prefs.density;
    densitySelect.onchange=()=>savePreferences({density:densitySelect.value});
  }

  const fontSelect=document.querySelector('#pref-font-select');
  if(fontSelect){
    fontSelect.value=prefs.fontSize;
    fontSelect.onchange=()=>savePreferences({fontSize:fontSelect.value});
  }

  const motionSelect=document.querySelector('#pref-motion-select');
  if(motionSelect){
    motionSelect.value=prefs.reducedMotion;
    motionSelect.onchange=()=>savePreferences({reducedMotion:motionSelect.value});
  }

  const codeWrapCheck=document.querySelector('#pref-code-wrap');
  if(codeWrapCheck){
    codeWrapCheck.checked=prefs.codeWrap;
    codeWrapCheck.onchange=()=>savePreferences({codeWrap:codeWrapCheck.checked});
  }

  // Conversations Controls
  const convSortSelect=document.querySelector('#pref-conv-sort');
  if(convSortSelect){
    convSortSelect.value=prefs.conversationsSort;
    convSortSelect.onchange=()=>{
      savePreferences({conversationsSort:convSortSelect.value});
      document.dispatchEvent(new CustomEvent('render-threads-request'));
    };
  }

  const showArchivedCheck=document.querySelector('#pref-show-archived');
  if(showArchivedCheck){
    showArchivedCheck.checked=prefs.showArchived;
    showArchivedCheck.onchange=()=>{
      savePreferences({showArchived:showArchivedCheck.checked});
      document.dispatchEvent(new CustomEvent('render-threads-request'));
    };
  }

  // AI Engines Preferences Controls
  const defaultEngineSelect=document.querySelector('#pref-default-engine-select');
  const defaultModelSelect=document.querySelector('#pref-default-model-select');
  const defaultModelWarning=document.querySelector('#pref-default-model-warning');

  if(defaultEngineSelect){
    defaultEngineSelect.onchange=()=>{
      const newEngine=defaultEngineSelect.value;
      savePreferences({defaultEngine:newEngine,defaultModel:''});
      refreshDefaultEngineControls();
    };
  }

  if(defaultModelSelect){
    defaultModelSelect.onchange=()=>{
      const newModel=defaultModelSelect.value;
      savePreferences({defaultModel:newModel});
      if(defaultModelWarning)defaultModelWarning.hidden=true;
    };
  }

  refreshDefaultEngineControls();

  // Sidebar Width Control in Settings
  const sidebarWidthSelect=document.querySelector('#pref-sidebar-width');
  if(sidebarWidthSelect){
    syncSidebarWidthSelect(sidebarWidthSelect, prefs.sidebarWidth || 280);
    sidebarWidthSelect.onchange=()=>{
      const chosen=Number(sidebarWidthSelect.value)||280;
      savePreferences({sidebarWidth:chosen});
    };
  }
}

export function syncSidebarWidthSelect(sw, width){
  if(!sw)return;
  const strVal=String(width);
  const presetValues=['280','360','440','520'];
  let customOpt=sw.querySelector('option[data-custom="true"]');
  if(!presetValues.includes(strVal)){
    if(!customOpt){
      customOpt=document.createElement('option');
      customOpt.dataset.custom='true';
      sw.append(customOpt);
    }
    customOpt.value=strVal;
    customOpt.textContent=`Custom (${strVal}px)`;
  }else if(customOpt){
    customOpt.remove();
  }
  sw.value=strVal;
}

export function getServerDefaultEngine(engines = appState().engines || []){
  if(!engines || !engines.length) return null;
  const explicitlyDefault = engines.find(e => e.default || e.is_default);
  if(explicitlyDefault) return explicitlyDefault;
  const readyEngine = engines.find(e => e.status === 'READY');
  if(readyEngine) return readyEngine;
  return engines[0];
}

export function resolveTargetEngineAndModel(prefs = loadPreferences(), engines = appState().engines || []){
  const preferredEngineId = prefs.defaultEngine || '';
  if(preferredEngineId){
    const engineObj = engines.find(e => e.engine_id === preferredEngineId);
    if(engineObj && engineObj.status === 'READY'){
      let targetModel = '';
      if(prefs.defaultModel && (engineObj.models || []).some(m => m.id === prefs.defaultModel)){
        targetModel = prefs.defaultModel;
      } else {
        targetModel = engineObj.default_model || engineObj.models?.[0]?.id || '';
      }
      return { engine_id: engineObj.engine_id, model_id: targetModel };
    }
  }

  const serverDefault = getServerDefaultEngine(engines);
  if(serverDefault){
    let targetModel = serverDefault.default_model || serverDefault.models?.[0]?.id || '';
    return { engine_id: serverDefault.engine_id, model_id: targetModel };
  }

  return { engine_id: '', model_id: '' };
}

export function refreshDefaultEngineControls(){
  const prefs=loadPreferences();
  const defaultEngineSelect=document.querySelector('#pref-default-engine-select');
  const defaultModelSelect=document.querySelector('#pref-default-model-select');
  const defaultEngineWarning=document.querySelector('#pref-default-engine-warning');
  const defaultModelWarning=document.querySelector('#pref-default-model-warning');

  const engines = appState().engines || [];
  const selectedEngineId = prefs.defaultEngine || '';

  if(defaultEngineSelect){
    if(selectedEngineId){
      let exists = false;
      const opts = defaultEngineSelect.options || defaultEngineSelect.children || [];
      for(let i=0; i < opts.length; i++){
        if(opts[i].value === selectedEngineId){
          exists = true;
          break;
        }
      }
      if(!exists){
        const opt = document.createElement('option');
        opt.value = selectedEngineId;
        opt.textContent = `${selectedEngineId} (not in catalog)`;
        defaultEngineSelect.append(opt);
      }
    }
    defaultEngineSelect.value=selectedEngineId;
  }

  if(defaultEngineWarning){
    const enginePill = defaultEngineWarning.querySelector('.warning-pill');
    if(!selectedEngineId){
      defaultEngineWarning.hidden = true;
      if(enginePill) enginePill.textContent = '';
    } else {
      const foundEngine = engines.find(e => e.engine_id === selectedEngineId);
      if(!foundEngine){
        defaultEngineWarning.hidden = false;
        if(enginePill){
          const serverDef = getServerDefaultEngine(engines);
          const fallbackLabel = serverDef ? (serverDef.label || serverDef.engine_id) : 'Server default unavailable';
          enginePill.textContent = `Preferred engine "${selectedEngineId}" is not available in catalog. Falling back to: ${fallbackLabel}.`;
        }
      } else if(foundEngine.status !== 'READY'){
        defaultEngineWarning.hidden = false;
        if(enginePill){
          const serverDef = getServerDefaultEngine(engines);
          const fallbackLabel = serverDef ? (serverDef.label || serverDef.engine_id) : 'Server default unavailable';
          enginePill.textContent = `Preferred engine "${foundEngine.label || selectedEngineId}" is not ready (${foundEngine.status}). Falling back to: ${fallbackLabel}.`;
        }
      } else {
        defaultEngineWarning.hidden = true;
        if(enginePill) enginePill.textContent = '';
      }
    }
  }

  if(defaultModelSelect){
    defaultModelSelect.replaceChildren();
    const defOpt=document.createElement('option');
    defOpt.value='';
    defOpt.textContent='Engine Default';
    defaultModelSelect.append(defOpt);

    if(!selectedEngineId){
      defaultModelSelect.disabled=true;
      if(defaultModelWarning)defaultModelWarning.hidden=true;
      return;
    }

    const engine=engines.find(e=>e.engine_id===selectedEngineId);
    if(!engine || engine.status !== 'READY'){
      defaultModelSelect.disabled=true;
      if(defaultModelWarning)defaultModelWarning.hidden=true;
      return;
    }

    defaultModelSelect.disabled=false;
    const models=engine.models||[];
    let found=false;

    for(const m of models){
      const opt=document.createElement('option');
      opt.value=m.id;
      opt.textContent=m.label||m.display_name||m.id;
      defaultModelSelect.append(opt);
      if(m.id===prefs.defaultModel)found=true;
    }

    if(prefs.defaultModel){
      if(found){
        defaultModelSelect.value=prefs.defaultModel;
        if(defaultModelWarning)defaultModelWarning.hidden=true;
      }else{
        defaultModelSelect.value='';
        if(defaultModelWarning){
          defaultModelWarning.hidden=false;
          const pill=defaultModelWarning.querySelector('.warning-pill');
          if(pill)pill.textContent=`Saved preferred model "${prefs.defaultModel}" is not in active catalog; falling back to Engine Default.`;
        }
      }
    }else{
      defaultModelSelect.value='';
      if(defaultModelWarning)defaultModelWarning.hidden=true;
    }
  }
}

document.addEventListener('preferences-changed',e=>{
  const p=e.detail;
  if(!p)return;
  const sw=document.querySelector('#pref-sidebar-width');
  if(sw){
    syncSidebarWidthSelect(sw, p.sidebarWidth || 280);
  }
});

// Copy Sanitized Diagnostics Action
document.querySelector('#btn-copy-diagnostics')?.addEventListener('click',async()=>{
  const btn=document.querySelector('#btn-copy-diagnostics');
  if(!btn)return;
  const sanitized={
    timestamp:new Date().toISOString(),
    url:window.location.origin,
    engines:(appState().engines||[]).map(e=>({id:e.engine_id,label:e.label,status:e.status,auth:e.authentication})),
    providers:(appState().providers||[]).map(p=>({id:p.provider_id,label:p.label,enabled:p.enabled,credential_status:p.credential_status})),
    server_policy:lastServerSettings?{
      permission_mode:lastServerSettings.permission_mode,
      bind_host:lastServerSettings.bind_host,
      retention:lastServerSettings.conversation_retention,
      p7_reads:lastServerSettings.p7_live_reads_enabled,
      p10_writes:lastServerSettings.p10_writes_enabled,
      secrets_returned:false
    }:null
  };
  try{
    await navigator.clipboard.writeText(JSON.stringify(sanitized,null,2));
    btn.textContent='Diagnostics Copied!';
    setTimeout(()=>{btn.textContent='Copy Sanitized Diagnostics';},2500);
  }catch(_){
    btn.textContent='Copy Unavailable';
  }
});

// Legacy theme toggle compatibility button
const themeButton=document.querySelector('#theme-toggle');
if(themeButton){
  function applyTheme(theme){
    savePreferences({theme});
    themeButton.setAttribute('aria-pressed',String(theme==='light'));
    themeButton.textContent=theme==='light'?'Use dark theme':'Use light theme';
  }
  themeButton.addEventListener('click',()=>{
    const currentTheme=loadPreferences().theme;
    applyTheme(currentTheme==='light'?'dark':'light');
  });
}

setupSettingsNavigation();
initSettingsFormControls();

document.addEventListener('thread-selected',()=>renderEngines());
document.addEventListener('owner-authenticated',()=>loadProviders().catch(error=>{if(status)status.textContent=error.message;}));
loadProviders().catch(error=>{if(status)status.textContent=error.message;});
