import {appState,getJSON,mutateJSON,setStatus} from './api.js';

const engineSelect=document.querySelector('#provider-select');
const modelSelect=document.querySelector('#model-select');
const status=document.querySelector('#provider-status');
const settings=document.querySelector('#settings-panel');
let openCodeCatalog={providers:[],models:[]};

function readinessCard(id,title,health,detail){
  const root=document.querySelector(id);root.replaceChildren();
  const badge=document.createElement('span');badge.className=`provider-health ${health.status==='READY'?'configured':'missing'}`;badge.textContent=health.status;
  const heading=document.createElement('h3');heading.textContent=title;
  const text=document.createElement('p');text.textContent=detail;
  root.append(badge,heading,text);
  if((health.missing_prerequisites||[]).length){const list=document.createElement('ul');for(const value of health.missing_prerequisites){const item=document.createElement('li');item.textContent=value;list.append(item);}root.append(list);}
}
function activeEngine(){return appState().engines.find(item=>item.engine_id===engineSelect.value)||appState().engines[0];}
function renderModels(selected){
  const engine=activeEngine();modelSelect.replaceChildren();
  if(engine?.engine_id==='opencode'){const placeholder=document.createElement('option');placeholder.value='select-model';placeholder.textContent='Choose an OpenCode provider model';placeholder.disabled=true;modelSelect.append(placeholder);}
  for(const model of engine?.models||[]){const option=document.createElement('option');option.value=model.id;if(engine?.engine_id==='opencode')option.textContent=`${model.display_name} · ${model.provider_id} · ${model.cost_classification} · ctx ${model.context_limit||'unknown'} · out ${model.output_limit||'unknown'} · tools ${model.tool_support?'yes':'no'} · reasoning ${model.reasoning?'yes':'no'} · ${model.availability} · ${model.connection_status}`;else option.textContent=model.label;modelSelect.append(option);}
  modelSelect.value=selected||engine?.default_model||'select-model';
  const pinned=Boolean(appState().currentThread?.turn_ids?.length);
  const selectedAvailable=[...modelSelect.options].some(option=>option.value===appState().currentThread?.model_id&&!option.disabled);
  modelSelect.disabled=pinned&&!(appState().currentThread?.engine_id==='opencode'&&!selectedAvailable);
  renderModelDetails();
}
function renderModelDetails(){const engine=activeEngine();const model=(engine?.models||[]).find(item=>item.id===modelSelect.value);const root=document.querySelector('#model-details');if(!model){root.textContent=engine?.engine_id==='opencode'?'Select an exact connected OpenCode model; no automatic fallback will occur.':'';return;}if(engine?.engine_id==='opencode')root.textContent=`${model.provider_id}/${model.model_id} · ${model.cost_classification} · context ${model.context_limit||'unknown'} · output ${model.output_limit||'unknown'} · tools ${model.tool_support?'supported':'not reported'} · reasoning ${model.reasoning?'reported':'not reported'} · ${model.availability} · ${model.connection_status}${model.warnings?.length?' · '+model.warnings.join(' · '):''}`;else if(engine?.engine_id==='antigravity')root.textContent=`${engine.label} · ${model.label}${model.effort?' · effort: '+model.effort:''} · Unrestricted Read & Governed Write Review`;else root.textContent=`${engine.label} · ${model.label}`;}
function renderEngines(){
  engineSelect.replaceChildren();
  for(const engine of appState().engines){const option=document.createElement('option');option.value=engine.engine_id;option.textContent=`${engine.label} · ${engine.authentication} · ${engine.status}`;option.disabled=engine.status!=='READY';engineSelect.append(option);}
  engineSelect.value=appState().currentThread?.engine_id||appState().engines.find(item=>item.status==='READY')?.engine_id||'codex';
  engineSelect.disabled=Boolean(appState().currentThread?.turn_ids?.length);renderModels(appState().currentThread?.model_id);
}
function addText(parent,tag,text,className=''){const node=document.createElement(tag);node.textContent=text;if(className)node.className=className;parent.append(node);return node;}
function renderOAuthMethods(){
  const providerId=document.querySelector('#opencode-oauth-provider').value;const select=document.querySelector('#opencode-oauth-method');select.replaceChildren();
  const provider=openCodeCatalog.providers.find(item=>item.provider_id===providerId);
  for(const method of provider?.authentication_methods.filter(item=>item.type==='oauth')||[]){const option=document.createElement('option');option.value=String(method.index);option.textContent=method.label;select.append(option);}
  renderOAuthInputs();
}
function selectedOAuthMethod(){
  const provider=openCodeCatalog.providers.find(item=>item.provider_id===document.querySelector('#opencode-oauth-provider').value);
  return provider?.authentication_methods.find(item=>item.type==='oauth'&&item.index===Number(document.querySelector('#opencode-oauth-method').value));
}
function renderOAuthInputs(){
  const root=document.querySelector('#opencode-oauth-inputs');root.replaceChildren();
  for(const prompt of selectedOAuthMethod()?.prompts||[]){
    const label=document.createElement('label');label.textContent=prompt.message||prompt.label||prompt.key;
    let input;
    if(Array.isArray(prompt.options)&&prompt.options.length){input=document.createElement('select');for(const value of prompt.options){const option=document.createElement('option');option.value=typeof value==='string'?value:(value.value??value.label);option.textContent=typeof value==='string'?value:(value.label??value.value);input.append(option);}}
    else{input=document.createElement('input');input.type=prompt.type==='password'?'password':'text';input.autocomplete='off';}
    input.dataset.oauthKey=prompt.key;input.required=prompt.required!==false;label.append(input);root.append(label);
  }
}
function oauthInputs(){
  const result={};for(const input of document.querySelectorAll('#opencode-oauth-inputs [data-oauth-key]'))result[input.dataset.oauthKey]=input.value;return result;
}
function refreshAuthSelects(){
  const api=document.querySelector('#opencode-api-provider');const oauth=document.querySelector('#opencode-oauth-provider');api.replaceChildren();oauth.replaceChildren();
  for(const provider of openCodeCatalog.providers){
    if(provider.authentication_methods.some(method=>method.type==='api')){const option=document.createElement('option');option.value=provider.provider_id;option.textContent=provider.display_name;api.append(option);}
    if(provider.authentication_methods.some(method=>method.type==='oauth')){const option=document.createElement('option');option.value=provider.provider_id;option.textContent=provider.display_name;oauth.append(option);}
  }
  renderOAuthMethods();
}
function renderOpenCodeProviders(){
  const root=document.querySelector('#provider-settings-list');root.replaceChildren();
  for(const provider of openCodeCatalog.providers){
    const card=document.createElement('section');card.className='provider-card';addText(card,'span',provider.connection_status,`provider-health ${provider.connected?'configured':'missing'}`);addText(card,'h3',provider.display_name);
    const free=openCodeCatalog.models.filter(model=>model.provider_id===provider.provider_id&&model.cost_classification==='FREE').length;
    addText(card,'p',`${provider.provider_id} · ${provider.model_count} models · ${free} free · source ${provider.source||'unknown'}`);
    if(provider.environment_refs.length)addText(card,'p',`Environment credentials supported: ${provider.environment_refs.join(', ')}`);
    for(const warning of provider.warnings)addText(card,'p',warning,'tool-error');
    if(provider.authentication_methods.some(item=>item.type==='api')){const connect=document.createElement('button');connect.type='button';connect.textContent=provider.connected?'Reconnect API key':'Connect API key';connect.addEventListener('click',()=>{document.querySelector('#opencode-api-provider').value=provider.provider_id;document.querySelector('#opencode-api-key').focus();});card.append(connect);}
    for(const method of provider.authentication_methods.filter(item=>item.type==='oauth')){
      const start=document.createElement('button');start.type='button';start.textContent=`Start ${method.label}`;
      start.addEventListener('click',()=>{document.querySelector('#opencode-oauth-provider').value=provider.provider_id;renderOAuthMethods();document.querySelector('#opencode-oauth-method').value=String(method.index);renderOAuthInputs();document.querySelector('#opencode-oauth-panel').open=true;document.querySelector('#opencode-oauth-panel').scrollIntoView({behavior:'smooth',block:'nearest'});document.querySelector('#settings-status').textContent='Review any provider-specific prompts, then start through OpenCode.';});card.append(start);
    }
    const test=document.createElement('button');test.type='button';test.textContent='Test configuration';test.addEventListener('click',()=>providerAction('test',provider.provider_id));card.append(test);
    if(provider.connected){const disconnect=document.createElement('button');disconnect.type='button';disconnect.textContent='Disconnect';disconnect.addEventListener('click',()=>providerAction('disconnect',provider.provider_id));card.append(disconnect);}
    if(provider.custom){const remove=document.createElement('button');remove.type='button';remove.textContent='Remove custom provider';remove.addEventListener('click',async()=>{try{const result=await mutateJSON('/api/v2/opencode/custom-providers/remove',{provider_id:provider.provider_id});document.querySelector('#settings-status').textContent=result.status;await loadProviders();}catch(error){document.querySelector('#settings-status').textContent=error.message;}});card.append(remove);}
    root.append(card);
  }
  refreshAuthSelects();
}
export async function loadProviders(){
  const server=await getJSON('/api/v2/settings');
  const [providers,engines,catalog]=await Promise.all([getJSON('/api/v2/providers'),getJSON('/api/v2/engines'),getJSON('/api/v2/opencode/providers')]);
  appState().providers=providers.profiles;appState().engines=engines.engines;openCodeCatalog=catalog;renderEngines();renderOpenCodeProviders();
  readinessCard('#codex-readiness','Codex App Server readiness',server.codex,`ChatGPT session · ${server.codex.sandbox} · ${server.codex.approval_policy} approvals · network ${server.codex.network_access?'enabled':'off'}`);
  readinessCard('#opencode-readiness','OpenCode readiness',server.opencode,`Version ${server.opencode.version||'unknown'} · Basic Auth ${server.opencode.basic_auth} · native shell ${server.opencode.native_shell} · native edits ${server.opencode.native_edits}`);
  if(server.antigravity)readinessCard('#antigravity-readiness','Antigravity CLI readiness',server.antigravity,`Version ${server.antigravity.version||'1.1.26'} · Unrestricted read & governed write review · Google AI session`);
  document.querySelector('#codex-status').textContent=`Codex ${server.codex.status} · OpenCode ${server.opencode.status}${server.antigravity?' · Antigravity '+server.antigravity.status:''}`;
  document.querySelector('#live-status').textContent=server.p7_live_reads_enabled?'Globally active':(server.p7_owner_scoped_live_reads_available?'Automatic exact reads':'Unavailable');
  const current=activeEngine();status.textContent=current?`${current.label} · ${modelSelect.value} · ${current.status}`:'No AI engine';
}
async function pinSelection(){
  const thread=appState().currentThread;if(!thread)return;
  if(engineSelect.value==='opencode'&&(!modelSelect.value||modelSelect.value==='select-model')){setStatus('Choose an available OpenCode model.');return;}
  try{const updated=await mutateJSON(`/api/v2/threads/${thread.thread_id}/engine`,{engine_id:engineSelect.value,model_id:modelSelect.value});appState().currentThread={...thread,...updated};status.textContent=`${activeEngine()?.label} · ${updated.model_id} · pinned to this conversation`;renderEngines();}
  catch(error){setStatus(error.message);engineSelect.value=thread.engine_id;renderModels(thread.model_id);}
}
engineSelect.addEventListener('change',()=>{renderModels();pinSelection();});modelSelect.addEventListener('change',()=>{renderModelDetails();pinSelection();});

async function providerAction(action,providerId){const output=document.querySelector('#settings-status');try{output.textContent=`${action} in progress…`;const result=await mutateJSON(`/api/v2/opencode/providers/${action}`,{provider_id:providerId});output.textContent=`${result.status} · no credential material returned`;await loadProviders();}catch(error){output.textContent=error.message;}}
document.querySelector('#settings-button').addEventListener('click',()=>settings.showModal());
document.querySelector('#refresh-opencode').addEventListener('click',async()=>{try{document.querySelector('#settings-status').textContent='Refreshing OpenCode providers and models…';await mutateJSON('/api/v2/opencode/providers/refresh',{});await loadProviders();document.querySelector('#settings-status').textContent='OpenCode catalog refreshed.';}catch(error){document.querySelector('#settings-status').textContent=error.message;}});
document.querySelector('#opencode-oauth-provider').addEventListener('change',renderOAuthMethods);document.querySelector('#opencode-oauth-method').addEventListener('change',renderOAuthInputs);
document.querySelector('#opencode-api-key-form').addEventListener('submit',async event=>{event.preventDefault();const input=document.querySelector('#opencode-api-key');const apiKey=input.value;input.value='';try{const result=await mutateJSON('/api/v2/opencode/providers/connect-api',{provider_id:document.querySelector('#opencode-api-provider').value,api_key:apiKey});document.querySelector('#settings-status').textContent=`${result.status} · credential sent directly to OpenCode and not returned`;await loadProviders();}catch(error){document.querySelector('#settings-status').textContent=error.message;}});
document.querySelector('#opencode-oauth-start').addEventListener('click',async()=>{const inputs=oauthInputs();for(const input of document.querySelectorAll('#opencode-oauth-inputs [data-oauth-key]'))input.value='';try{const result=await mutateJSON('/api/v2/opencode/providers/oauth/start',{provider_id:document.querySelector('#opencode-oauth-provider').value,method:Number(document.querySelector('#opencode-oauth-method').value),inputs});document.querySelector('#settings-status').textContent=`${result.status} · ${result.instructions}`;const opened=window.open(result.authorization_url,'_blank','noopener,noreferrer');if(!opened)document.querySelector('#settings-status').textContent+=' · Browser popup was blocked.';}catch(error){document.querySelector('#settings-status').textContent=error.message;}});
document.querySelector('#opencode-oauth-complete-form').addEventListener('submit',async event=>{event.preventDefault();const codeInput=document.querySelector('#opencode-oauth-code');const code=codeInput.value;codeInput.value='';try{const result=await mutateJSON('/api/v2/opencode/providers/oauth/callback',{provider_id:document.querySelector('#opencode-oauth-provider').value,method:Number(document.querySelector('#opencode-oauth-method').value),code:code||undefined});document.querySelector('#settings-status').textContent=result.status;await loadProviders();}catch(error){document.querySelector('#settings-status').textContent=error.message;}});
document.querySelector('#opencode-custom-provider-form').addEventListener('submit',async event=>{event.preventDefault();const keyInput=document.querySelector('#custom-provider-key');let apiKey=keyInput.value;keyInput.value='';try{const models=document.querySelector('#custom-provider-models').value.split(/\r?\n/).filter(Boolean).map(line=>{const [model_id,display_name,context,output]=line.split('|').map(value=>value.trim());const item={model_id,display_name};if(context)item.context_limit=Number(context);if(output)item.output_limit=Number(output);return item;});const headers=JSON.parse(document.querySelector('#custom-provider-headers').value||'{}');const environmentRef=document.querySelector('#custom-provider-env').value.trim();if(apiKey&&environmentRef)throw new Error('Choose either a one-time API key or an environment reference, not both.');const provider={provider_id:document.querySelector('#custom-provider-id').value.trim(),display_name:document.querySelector('#custom-provider-name').value.trim(),base_url:document.querySelector('#custom-provider-url').value.trim(),protocol:document.querySelector('#custom-provider-protocol').value,environment_ref:environmentRef||null,models,headers,allow_loopback:document.querySelector('#custom-provider-loopback').checked};const result=await mutateJSON('/api/v2/opencode/custom-providers/save',{provider});if(apiKey)await mutateJSON('/api/v2/opencode/providers/connect-api',{provider_id:provider.provider_id,api_key:apiKey});apiKey='';document.querySelector('#settings-status').textContent=`${result.status} · non-secret metadata saved; OpenCode restarted safely`;event.target.reset();document.querySelector('#custom-provider-headers').value='{}';await loadProviders();}catch(error){apiKey='';document.querySelector('#settings-status').textContent=error.message;}});

const themeButton=document.querySelector('#theme-toggle');function applyTheme(theme){document.documentElement.dataset.theme=theme;themeButton.setAttribute('aria-pressed',String(theme==='light'));themeButton.textContent=theme==='light'?'Use dark theme':'Use light theme';localStorage.setItem('mne-theme',theme);}themeButton.addEventListener('click',()=>applyTheme(document.documentElement.dataset.theme==='light'?'dark':'light'));applyTheme(localStorage.getItem('mne-theme')||'dark');
document.addEventListener('thread-selected',()=>renderEngines());
loadProviders().catch(error=>{status.textContent=error.message;});
