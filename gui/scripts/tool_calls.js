import {mutateJSON,setStatus} from './api.js';

const proposals=document.querySelector('#tool-proposals');
function addText(parent,tag,text,className=''){const node=document.createElement(tag);node.textContent=text;if(className)node.className=className;parent.append(node);return node;}
function appendCard(card){
  if(proposals.classList.contains('empty-tools')){proposals.replaceChildren();proposals.classList.remove('empty-tools');}
  proposals.append(card);
  const content=document.querySelector('#tool-content');
  if(content&&content.hidden){
    content.hidden=false;
    document.querySelector('#tool-drawer')?.classList.remove('collapsed');
    const toggle=document.querySelector('#toggle-tools');
    if(toggle){toggle.setAttribute('aria-expanded','true');toggle.textContent='Collapse';}
  }
}
function renderWorkspacePlan(card,plan){
  const rollback=Boolean(plan.rollback_id);addText(card,'h3',rollback?'Exact proposed reverse diff':'Exact proposed diff');const diff=addText(card,'pre',plan.unified_diff);diff.className='workspace-diff';addText(card,'p',`Direction ${plan.apply_direction||'FORWARD'} - expires ${plan.expires_at} - ${plan.paths.length} path(s)`);
  addText(card,'p','Review the displayed risk and exact diff. Accept sends the server-bound approval and applies this one plan; Deny leaves it unapplied.');
  const accept=document.createElement('button');accept.type='button';accept.textContent=rollback?'Accept and apply rollback once':'Accept and apply change once';
  const deny=document.createElement('button');deny.type='button';deny.textContent='Deny - leave unchanged';
  accept.addEventListener('click',async()=>{accept.disabled=true;deny.disabled=true;try{const approvalPath=rollback?`/api/v2/workspace/rollbacks/${plan.rollback_id}/approve`:`/api/v2/workspace/plans/${plan.plan_id}/approve`;const approval=await mutateJSON(approvalPath,{approval_phrase:plan.approval_phrase});const id=rollback?plan.rollback_id:plan.plan_id;const executePath=rollback?`/api/v2/workspace/rollbacks/${id}/execute`:`/api/v2/workspace/plans/${id}/execute`;const result=await mutateJSON(executePath,{approval_id:approval.approval_id});addText(card,'pre',JSON.stringify(result,null,2));setStatus(result.status);if(!rollback&&result.rollback_available){const prepare=document.createElement('button');prepare.type='button';prepare.textContent='Prepare rollback';prepare.addEventListener('click',async()=>{prepare.disabled=true;try{const reverse=await mutateJSON(`/api/v2/workspace/plans/${plan.plan_id}/rollback/prepare`,{});renderWorkspacePlan(card,reverse);}catch(error){setStatus(error.message);prepare.disabled=false;}});card.append(prepare);}}catch(error){addText(card,'p',error.message,'tool-error');setStatus(error.message);}});
  deny.addEventListener('click',()=>{accept.disabled=true;deny.disabled=true;addText(card,'p','Denied. No workspace change was sent.');setStatus('Workspace change denied.');});
  card.append(accept,deny);
}
function renderAgentApproval(payload,providerId){
  if(providerId!=='prv_codex_app_server')return;
  const card=document.createElement('article');card.className='provider-card tool-card';
  addText(card,'span','Codex App Server approval','provider-health missing');
  addText(card,'h3',payload.kind==='FILE_CHANGE'?'Repository write batch preview':'Untrusted command preview');
  if(payload.kind==='FILE_CHANGE')addText(card,'p',`One approval covers all ${Array.isArray(payload.exact_target)?payload.exact_target.length:1} path(s) in this displayed diff. It does not approve any later change.`);
  if(payload.risk_level)addText(card,'p',`Risk ${payload.risk_level}/4 · ${payload.risk_explanation}`);
  if(payload.risks)addText(card,'p',`Risks: ${payload.risks.join(' · ')}`);
  addText(card,'p',`Exact target: ${Array.isArray(payload.exact_target)?payload.exact_target.join(', '):payload.exact_target}`);
  addText(card,'h3',payload.kind==='FILE_CHANGE'?'Exact diff':'Exact command');
  addText(card,'pre',payload.unified_diff||payload.command||'No action supplied.','workspace-diff');
  addText(card,'p',`Expected impact: ${payload.expected_impact||payload.expected_effect||'Only the displayed exact action.'}`);
  addText(card,'p',`Prechecks: ${(payload.prechecks||[]).join(' · ')}`);
  addText(card,'p',`Post-change validation: ${(payload.post_change_validation||[]).join(' · ')}`);
  addText(card,'p',`Rollback: ${payload.rollback_procedure||payload.rollback}`);
  addText(card,'pre',payload.approval_phrase,'workspace-diff');
  addText(card,'p','Accept submits the displayed server-bound approval once. Deny keeps the exact action unapplied.');
  const approve=document.createElement('button');approve.type='button';approve.textContent=payload.kind==='FILE_CHANGE'?'Approve and apply once':'Approve command once';
  const deny=document.createElement('button');deny.type='button';deny.textContent='Deny';
  const approvalBase='/api/v2/codex/approvals';
  deny.addEventListener('click',async()=>{approve.disabled=true;deny.disabled=true;try{const result=await mutateJSON(`${approvalBase}/${payload.approval_id}/deny`,{});addText(card,'p',result.status);setStatus('Codex action denied.');}catch(error){approve.disabled=false;deny.disabled=false;setStatus(error.message);}});
  approve.addEventListener('click',async()=>{approve.disabled=true;deny.disabled=true;try{const result=await mutateJSON(`${approvalBase}/${payload.approval_id}/approve`,{approval_phrase:payload.approval_phrase});addText(card,'pre',JSON.stringify(result,null,2));setStatus(result.status);if(result.workspace_plan_id&&result.rollback_available){const rollback=document.createElement('button');rollback.type='button';rollback.textContent='Prepare governed rollback';rollback.addEventListener('click',async()=>{rollback.disabled=true;try{renderWorkspacePlan(card,await mutateJSON(`/api/v2/workspace/plans/${result.workspace_plan_id}/rollback/prepare`,{}));}catch(error){rollback.disabled=false;setStatus(error.message);}});card.append(rollback);}}catch(error){approve.disabled=false;deny.disabled=false;addText(card,'p',error.message,'tool-error');setStatus(error.message);}});
  card.append(approve,deny);appendCard(card);
}
const operationCards=new Map();
function renderAgentOperation(envelope){
  const payload=envelope.redacted_payload||{};const key=payload.item_id||payload.id||`${envelope.turn_id}:${envelope.event_type.startsWith('file.')?'files':'activity'}`;
  let state=operationCards.get(key);
  if(!state){const card=document.createElement('article');card.className='provider-card tool-card';addText(card,'span','Codex activity','provider-health configured');addText(card,'h3',envelope.event_type.startsWith('file.')?'Workspace changes':'Local command');const output=addText(card,'pre','','workspace-diff');state={card,output};operationCards.set(key,state);appendCard(card);}
  if(envelope.event_type==='command.output')state.output.textContent+=payload.delta||'';
  else if(envelope.event_type==='file.diff')state.output.textContent=payload.diff||'';
  else if(envelope.event_type==='command.started')state.output.textContent=payload.command||JSON.stringify(payload,null,2);
  else if(envelope.event_type==='command.completed')addText(state.card,'p',`Completed · exit ${payload.exitCode??'unknown'}`);
  else if(envelope.event_type==='file.change')state.output.textContent=JSON.stringify(payload.changes||payload,null,2);
}

function renderP10Plan(card,plan){
  addText(card,'h3',`Infrastructure change preview - risk ${plan.risk_level}/4`);
  addText(card,'p','One approval covers the displayed prechecks, exact change, postchecks, and the displayed rollback only when a declared failure condition occurs. Any changed scope requires a new plan.');
  addText(card,'p',`${plan.title} - exact target ${plan.target} - platform ${plan.platform}`);
  addText(card,'p',plan.risk_preview||plan.expected_impact||'Risk preview supplied by the server.');
  addText(card,'h3','Scope and dependencies');
  addText(card,'pre',JSON.stringify({operation_id:plan.operation_id,operation_type:plan.operation_type,protocol:plan.protocol,binding_id:plan.binding_id,intended_changes:plan.intended_changes,parameters:plan.parameters,affected_systems:plan.affected_systems,maximum_targets:plan.maximum_targets,transaction_mode:plan.transaction_mode,expected_impact:plan.expected_impact,blast_radius:plan.blast_radius,possible_downtime:plan.possible_downtime,worst_reasonable_failure:plan.worst_reasonable_failure,dependencies:plan.dependencies},null,2));
  addText(card,'h3','Current-state evidence and prechecks');
  addText(card,'pre',JSON.stringify({evidence_id:plan.evidence_id,state_digest:plan.state_digest,target_identity_hash:plan.target_identity_hash,owner_session_binding:plan.owner_session_binding,plan_digest:plan.plan_digest,checks:plan.pre_check_results},null,2));
  addText(card,'h3','Exact action');addText(card,'pre',(plan.command_bundle?.display_commands||[]).join('\n'),'workspace-diff');
  addText(card,'h3','Verification after change');addText(card,'pre',(plan.post_checks||[]).join('\n')||'No post-checks declared.');
  addText(card,'h3','Rollback');addText(card,'pre',(plan.rollback_bundle?.display_commands||['NO SAFE ROLLBACK']).join('\n'),'workspace-diff');
  addText(card,'p',`Backup or snapshot: ${plan.backup_snapshot}`);
  addText(card,'pre',JSON.stringify({success_conditions:plan.success_conditions,failure_conditions:plan.failure_conditions,rollback_strategy:plan.rollback_strategy,rollback_conditions:plan.rollback_conditions,non_rollbackable_operations:plan.non_rollbackable_operations},null,2));
  addText(card,'p',`Prepared ${plan.created_at}; expires ${plan.expires_at}; timeout ${plan.timeout_seconds}s; dry run ${plan.supports_dry_run?'supported':'not supported'}. No live connection or persistence occurred during this preview.`);
  if(plan.critical_warning)addText(card,'pre',JSON.stringify(plan.critical_warning,null,2),'tool-error');
  addText(card,'pre',plan.approval_phrase,'workspace-diff');
  addText(card,'p','Review the risk preview, exact action, prechecks, postchecks, and rollback. Accept sends the server-bound approval and executes this one plan; Deny cancels it before mutation.');
  const accept=document.createElement('button');accept.type='button';accept.textContent='Accept and execute once';
  const cancel=document.createElement('button');cancel.type='button';cancel.textContent='Deny - cancel before mutation';
  accept.addEventListener('click',async()=>{accept.disabled=true;cancel.disabled=true;try{await mutateJSON(`/api/v2/p10/plans/${plan.plan_id}/approve`,{approval_phrase:plan.approval_phrase});const result=await mutateJSON(`/api/v2/p10/plans/${plan.plan_id}/execute`,{});addText(card,'pre',JSON.stringify(result,null,2));setStatus(result.status);}catch(error){addText(card,'p',error.message,'tool-error');setStatus(error.message);}});
  cancel.addEventListener('click',async()=>{cancel.disabled=true;accept.disabled=true;try{const result=await mutateJSON(`/api/v2/p10/plans/${plan.plan_id}/cancel`,{});addText(card,'p',result.status);setStatus(result.status);}catch(error){cancel.disabled=false;accept.disabled=false;setStatus(error.message);}});
  card.append(accept,cancel);
}
function renderOwnerDirect(card,payload){
  if(payload.status==='AWAITING_FINAL_CONFIRMATION'){
    const warning=payload.warning||{};
    const canRollback=warning.can_rollback??(warning.rollback_status==='DECLARED');
    const riskLevel=warning.risk_level||payload.risk_level||'HIGH';
    addText(card,'h3','⚠️ Administrator Risk & Rollback Review — Owner Direct Write');
    const riskBadge=document.createElement('div');
    riskBadge.className='provider-health configured';
    riskBadge.style.display='inline-block';
    riskBadge.style.fontWeight='bold';
    riskBadge.style.marginBottom='8px';
    riskBadge.textContent=`RISK LEVEL: ${riskLevel}`;
    card.append(riskBadge);
    const rollbackBanner=document.createElement('div');
    rollbackBanner.style.padding='8px 12px';
    rollbackBanner.style.borderRadius='4px';
    rollbackBanner.style.marginBottom='12px';
    rollbackBanner.style.fontWeight='bold';
    if(canRollback){
      rollbackBanner.style.background='#1b4332';
      rollbackBanner.style.color='#d8f3dc';
      rollbackBanner.textContent='🔄 ROLLBACK FEASIBLE: YES — Automated rollback steps are available.';
    }else{
      rollbackBanner.style.background='#5c1d1d';
      rollbackBanner.style.color='#ffcdd2';
      rollbackBanner.textContent='⛔ ROLLBACK FEASIBLE: NO — IRREVERSIBLE CHANGE / NO AUTOMATED ROLLBACK.';
    }
    card.append(rollbackBanner);
    addText(card,'p',`Target: ${warning.target_device_system||payload.target} · Identity: ${warning.identity_status||payload.identity_status}`);
    addText(card,'p',warning.identity_warning||'Review the identity status before confirming.','tool-error');
    addText(card,'h3','Exact intended change');addText(card,'p',warning.exact_intended_change||'Not supplied.');
    addText(card,'h3','Commands or API operations to apply');addText(card,'pre',(warning.commands_or_api_operations||payload.operations||[]).join('\n'),'workspace-diff');
    addText(card,'p',`Impact and downtime: ${warning.expected_impact_and_downtime_risk||'Not supplied.'}`);
    addText(card,'p',`Blast radius: ${warning.blast_radius||'Not supplied.'}`);
    addText(card,'p',`Prechecks: ${(warning.prechecks||[]).join(' · ')}`);
    addText(card,'p',`Postchecks: ${(warning.postchecks||[]).join(' · ')}`);
    addText(card,'h3','Rollback details');
    addText(card,'p',warning.rollback_summary||(canRollback?'Rollback steps declared below:':'No safe automated rollback is available for this change.'));
    addText(card,'pre',(warning.rollback_steps||[]).join('\n'),'workspace-diff');
    const confirm=document.createElement('button');confirm.type='button';confirm.textContent='Accept & Apply Once';
    const deny=document.createElement('button');deny.type='button';deny.textContent='Deny - leave unchanged';
    confirm.addEventListener('click',async()=>{confirm.disabled=true;deny.disabled=true;setStatus('Sending the exact Owner Direct operation once…');try{const result=await mutateJSON(`/api/v2/owner-direct/writes/${payload.plan_id}/confirm`,{});addText(card,'pre',JSON.stringify(result,null,2));setStatus(`${result.status} · postcheck ${result.postcheck_status||'NOT_RUN'}`);}catch(error){confirm.disabled=false;deny.disabled=false;addText(card,'p',error.message,'tool-error');setStatus(error.message);}});
    deny.addEventListener('click',()=>{confirm.disabled=true;deny.disabled=true;addText(card,'p','Denied. No Owner Direct change was sent.');setStatus('Owner Direct change denied.');});
    card.append(confirm,deny);return;
  }
  addText(card,'h3','Owner Direct discovery result');
  addText(card,'p',`Target ${payload.target||'unknown'} · ${payload.protocol||'unknown'} · ${payload.status||'UNKNOWN'}`);
  addText(card,'p',`Connection: ${payload.reachability?'reachable':'not reachable'} · authentication: ${payload.authentication_result||'UNKNOWN'} · identity: ${payload.identity_result||'UNKNOWN'}`);
  addText(card,'p',`Evidence ID: ${payload.evidence_id||'none'} · attempts: ${payload.attempt_count??0} · no automatic retries.`);
  if(payload.identity_result==='IDENTITY_CONFLICT'||payload.status==='IDENTITY_CONFLICT')addText(card,'p','IDENTITY_CONFLICT: recorded identity was not changed; owner review is required.','tool-error');
  addText(card,'pre',JSON.stringify({serial:payload.serial,model:payload.model,version:payload.version,facts:payload.facts},null,2));
}
function renderLiveReadPlan(card,plan){
  addText(card,'h3','Exact owner-gated P7 live read');
  addText(card,'p',`${plan.entity_id} - target ${plan.target} - check ${plan.check_id} - ${plan.identity_mode}`);
  addText(card,'p','No connection has been made. Approval is short-lived and single-use. P7 remains disabled globally at rest.');
  const phraseText=addText(card,'pre',plan.approval_phrase);phraseText.className='workspace-diff';
  const copy=document.createElement('button');copy.type='button';copy.textContent='Copy exact phrase';copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(plan.approval_phrase);setStatus('Exact live-read phrase copied.');}catch(_error){setStatus('Copy was blocked; select the displayed phrase manually.');}});card.append(copy);
  const label=document.createElement('label');label.textContent='Paste the exact server approval phrase';const phrase=document.createElement('input');phrase.type='text';phrase.autocomplete='off';phrase.spellcheck=false;label.append(phrase);card.append(label);
  const approve=document.createElement('button');approve.type='button';approve.textContent='Approve this exact read';
  const execute=document.createElement('button');execute.type='button';execute.textContent='Run one live read';execute.disabled=true;
  let approvalId='';
  approve.addEventListener('click',async()=>{try{const result=await mutateJSON(`/api/v2/live-reads/${plan.live_read_id}/approve`,{approval_phrase:phrase.value});phrase.value='';approvalId=result.approval_id;approve.disabled=true;execute.disabled=false;addText(card,'p','Approved once. No connection has been made yet.');setStatus('Exact P7 read approved; press Run one live read to connect.');}catch(error){setStatus(error.message);}});
  execute.addEventListener('click',async()=>{execute.disabled=true;setStatus('Running one exact pinned P7 read...');try{const result=await mutateJSON(`/api/v2/live-reads/${plan.live_read_id}/execute`,{approval_id:approvalId});if(result.live_verified&&result.evidence){const evidence=result.evidence;addText(card,'span','LIVE VERIFIED','provider-health configured');addText(card,'p',`Evidence ${evidence.evidence_id} - observed ${evidence.observed_at} - target ${evidence.verification_target} - check ${evidence.verification_check_id}`);document.dispatchEvent(new CustomEvent('live-evidence',{detail:{sources:[`${evidence.source} - ${evidence.evidence_id} - ${evidence.observed_at}`],unknowns:[]}}));setStatus(`LIVE VERIFIED - ${evidence.evidence_id}`);}else{addText(card,'p',`Live read not verified: ${result.status}`,'tool-error');document.dispatchEvent(new CustomEvent('live-evidence',{detail:{sources:[],unknowns:[`Live read was not verified: ${result.status}. No automatic retry was made.`]}}));setStatus(`Live read not verified - ${result.status}`);}}catch(error){addText(card,'p',error.message,'tool-error');document.dispatchEvent(new CustomEvent('live-evidence',{detail:{sources:[],unknowns:[`Live read could not run: ${error.message}`]}}));setStatus(error.message);}});
  card.append(approve,execute);
}
function renderLiveReadResult(card,result){
  const evidence=result.evidence;
  if(result.live_verified&&evidence){
    addText(card,'span','LIVE VERIFIED','provider-health configured');
    addText(card,'p',`Evidence ${evidence.evidence_id} - observed ${evidence.observed_at} - target ${evidence.verification_target} - check ${evidence.verification_check_id}`);
    document.dispatchEvent(new CustomEvent('live-evidence',{detail:{sources:[`${evidence.source} - ${evidence.evidence_id} - ${evidence.observed_at}`],unknowns:[]}}));
    setStatus(`LIVE VERIFIED - ${evidence.evidence_id}`);
    return;
  }
  const status=result.status||'NOT_VERIFIED';
  addText(card,'p',`Live read not verified: ${status}. No automatic retry was made.`,'tool-error');
  document.dispatchEvent(new CustomEvent('live-evidence',{detail:{sources:[],unknowns:[`Live read was not verified: ${status}. No automatic retry was made.`]}}));
  setStatus(`Live read not verified - ${status}`);
}
async function invoke(card,payload,button){
  button.disabled=true;setStatus(`Reviewing ${payload.tool_name}`);
  try{const response=await mutateJSON(`/api/v2/tool-calls/${payload.tool_call_id}/invoke`,{});const result=response.result||{};if(typeof result.live_verified==='boolean')renderLiveReadResult(card,result);else if(result.live_read_id)renderLiveReadPlan(card,result);else if(result.mode==='OWNER_DIRECT'||result.evidence_id)renderOwnerDirect(card,result);else if((result.plan_id||result.rollback_id)&&result.unified_diff)renderWorkspacePlan(card,result);else if(result.plan_id&&result.command_bundle)renderP10Plan(card,result);else addText(card,'pre',JSON.stringify(result,null,2));if(typeof result.live_verified!=='boolean')setStatus(`${payload.tool_name} prepared`);}catch(error){button.disabled=false;addText(card,'p',error.message,'tool-error');setStatus(error.message);}
}
const automaticCards=new Map();
document.addEventListener('tool-event',event=>{
  const envelope=event.detail.envelope;const payload=envelope.redacted_payload;
  if(envelope.event_type==='tool.approval_required'){renderAgentApproval(payload,envelope.provider_id);return;}
  if(envelope.event_type.startsWith('command.')||envelope.event_type.startsWith('file.')){renderAgentOperation(envelope);return;}
  if(envelope.event_type==='tool.completed'&&automaticCards.has(payload.tool_call_id)){const card=automaticCards.get(payload.tool_call_id);const result=payload.result||{};addText(card,'p',`Completed - ${envelope.status}`);if(typeof result.live_verified==='boolean')renderLiveReadResult(card,result);else if(result.live_read_id)renderLiveReadPlan(card,result);else if(result.mode==='OWNER_DIRECT'||result.evidence_id)renderOwnerDirect(card,result);else if((result.plan_id||result.rollback_id)&&result.unified_diff)renderWorkspacePlan(card,result);else if(result.plan_id&&result.command_bundle)renderP10Plan(card,result);return;}
  if(envelope.event_type!=='tool.proposed')return;const card=document.createElement('article');card.className='provider-card tool-card';
  addText(card,'span','Server validated proposal','provider-health configured');addText(card,'h3',payload.tool_name);addText(card,'p',`Proposal ${payload.tool_call_id} - immutable argument digest ${payload.argument_digest}`);
  if(['AUTOMATIC_READ','AUTOMATIC_PREPARATION'].includes(envelope.status)){addText(card,'p',envelope.status==='AUTOMATIC_READ'?'Running automatically under the authenticated owner read policy.':'Building the exact server preview automatically. No write will execute without your approval.');automaticCards.set(payload.tool_call_id,card);if(proposals.classList.contains('empty-tools')){proposals.replaceChildren();proposals.classList.remove('empty-tools');}proposals.append(card);return;}
  const action=document.createElement('button');action.type='button';action.textContent='Review proposal';action.addEventListener('click',()=>invoke(card,payload,action));card.append(action);
  if(proposals.classList.contains('empty-tools')){proposals.replaceChildren();proposals.classList.remove('empty-tools');}proposals.append(card);
});
const toggle=document.querySelector('#toggle-tools');
toggle?.addEventListener('click',()=>{
  const content=document.querySelector('#tool-content');
  const drawer=document.querySelector('#tool-drawer');
  const hidden=!content.hidden;
  content.hidden=hidden;
  drawer?.classList.toggle('collapsed',hidden);
  toggle.setAttribute('aria-expanded',String(!hidden));
  toggle.textContent=hidden?'Expand':'Collapse';
});
