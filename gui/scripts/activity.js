const panel=document.querySelector('#activity-panel');
const body=document.querySelector('#activity-body');
const list=document.querySelector('#activity-list');
const badge=document.querySelector('#activity-state');
const toggle=document.querySelector('#toggle-activity');
const states=new Map();
let visibleTurn='';

function clip(value,limit=4000){return String(value??'').replace(/\u0000/g,'').slice(-limit);}
function clean(value,limit=4000){return clip(value,limit).trim();}
function timeLabel(timestamp){
  const date=new Date(timestamp||Date.now());
  return Number.isNaN(date.getTime())?'now':date.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'});
}
function commandText(payload){
  if(payload.command)return clean(payload.command,12000);
  if(Array.isArray(payload.commandActions))return clean(payload.commandActions.map(item=>item?.command||'').filter(Boolean).join('\n'),12000);
  return '';
}
function planText(payload){
  const steps=payload.plan?.steps||payload.steps||[];
  return Array.isArray(steps)?steps.map((step,index)=>`${index+1}. ${step?.step||step?.description||String(step)}`).join('\n'):'';
}
function showTurn(turnId){
  if(visibleTurn===turnId)return;
  visibleTurn=turnId;states.clear();list.replaceChildren();panel.hidden=false;panel.classList.remove('complete','failed');badge.textContent='Running';
}
function collapseActivity(){body.classList.add('activity-body-hidden');toggle.textContent='Show';toggle.setAttribute('aria-expanded','false');}
function rowFor(turnId,key,title,{status='running',detail='',output=''}={}){
  showTurn(turnId);
  const mapKey=`${turnId}:${key}`;
  let state=states.get(mapKey);
  if(!state){
    const item=document.createElement('li');item.className=`activity-entry ${status}`;
    const dot=document.createElement('span');dot.className='activity-dot';dot.setAttribute('aria-hidden','true');
    const when=document.createElement('time');when.className='activity-time';when.textContent=timeLabel();
    const copy=document.createElement('div');copy.className='activity-copy';
    const heading=document.createElement('strong');const description=document.createElement('span');
    copy.append(heading,description);item.append(dot,when,copy);list.append(item);
    state={item,when,heading,description,output:null,outputText:'',receivedOutput:false};states.set(mapKey,state);
  }
  state.item.className=`activity-entry ${status}`;state.heading.textContent=title;state.description.textContent=clean(detail);
  if(output){
    if(!state.output){state.output=document.createElement('pre');state.output.setAttribute('aria-label',`${title} details`);state.description.after(state.output);}
    state.outputText=clean(output,40000);state.output.textContent=state.outputText;
  }
  list.scrollTop=list.scrollHeight;return state;
}
function appendOutput(turnId,key,delta){
  const state=rowFor(turnId,key,'Command output',{detail:'Receiving redacted terminal output…'});
  if(!state.output){state.output=document.createElement('pre');state.output.setAttribute('aria-label','Command output');state.description.after(state.output);}
  if(!state.receivedOutput&&state.outputText){state.outputText=`${state.outputText}\n\nOutput:\n`;}
  state.receivedOutput=true;
  state.outputText=clip(`${state.outputText}${String(delta??'')}`,40000);state.output.textContent=state.outputText;list.scrollTop=list.scrollHeight;
}
function itemKey(payload,prefix){return `${prefix}:${payload.item_id||payload.id||payload.tool_call_id||'current'}`;}
function toolName(payload){return clean(payload.tool_name||payload.tool?.name||payload.name||payload.id||'Governed tool',300);}

document.addEventListener('stream-event',event=>{
  const envelope=event.detail.envelope;const payload=envelope.redacted_payload||{};const turn=envelope.turn_id;const type=envelope.event_type;
  if(type==='turn.started')rowFor(turn,'turn','Turn started',{detail:`${payload.agent_harness==='OPENCODE_HTTP_SSE'?'OpenCode':'Codex App Server'} accepted the request and began investigating.`});
  else if(type==='investigation.planned')rowFor(turn,'investigation','Investigation planned',{detail:`${Number(payload.candidate_count||0)} governed live check candidate(s) identified.`});
  else if(type==='agent.progress'){
    const state=rowFor(turn,'progress','AI engine is investigating',{detail:'Receiving redacted progress updates…'});
    state.outputText=clip(`${state.outputText}${String(payload.text||'')}`,12000);state.description.textContent=state.outputText.trim()||'Investigating the available evidence…';
  }
  else if(type==='agent.plan')rowFor(turn,'plan','Plan updated',{detail:planText(payload)||'The selected engine updated its working plan.'});
  else if(type==='command.started')rowFor(turn,itemKey(payload,'command'),'Running local command',{detail:'A sandboxed command started.',output:commandText(payload)||'Command details were not supplied.'});
  else if(type==='command.output')appendOutput(turn,itemKey(payload,'command'),payload.delta);
  else if(type==='command.completed')rowFor(turn,itemKey(payload,'command'),'Local command completed',{status:Number(payload.exitCode??payload.exit_code??0)===0?'success':'error',detail:`Exit code ${payload.exitCode??payload.exit_code??'unknown'}.`});
  else if(type==='tool.proposed')rowFor(turn,itemKey(payload,'tool'),'Governed tool prepared',{detail:`${toolName(payload)} · ${envelope.status.replaceAll('_',' ').toLowerCase()}`});
  else if(type==='tool.started')rowFor(turn,itemKey(payload,'tool'),'Governed tool running',{detail:toolName(payload)});
  else if(type==='tool.completed'){
    const validation=payload.validation?.summary||payload.validation?.status||payload.result?.status||'';
    rowFor(turn,itemKey(payload,'tool'),'Governed tool completed',{status:envelope.status==='FAILED'?'error':'success',detail:[toolName(payload),clean(validation,500)].filter(Boolean).join(' · ')});
  }
  else if(type==='tool.approval_required')rowFor(turn,itemKey(payload,'approval'),'Waiting for your approval',{status:'waiting',detail:`${payload.kind||'Action'} · risk ${payload.risk_level??'review required'}/4 · target ${Array.isArray(payload.exact_target)?payload.exact_target.join(', '):(payload.exact_target||'shown below')}`});
  else if(type==='file.change')rowFor(turn,itemKey(payload,'file'),'Workspace change detected',{status:'waiting',detail:'The exact redacted change is available in detailed operations.'});
  else if(type==='file.diff')rowFor(turn,itemKey(payload,'file'),'Workspace diff received',{status:'waiting',detail:'Review the exact diff before approving any repository write.',output:payload.diff});
  else if(type==='evidence.accepted')rowFor(turn,itemKey(payload,'evidence'),'Evidence accepted',{status:'success',detail:`${payload.evidence_id||payload.source||'Attributable evidence'}${payload.observed_at?` · ${payload.observed_at}`:''}`});
  else if(type==='answer.delta')rowFor(turn,'answer','Writing the answer',{detail:'Streaming the evidence-based answer into the conversation.'});
  else if(type==='answer.final'){
    rowFor(turn,'answer','Answer ready',{status:'success',detail:'The complete answer is displayed in the conversation above.'});collapseActivity();
  }
  else if(type==='turn.completed'){
    rowFor(turn,'complete','Turn completed',{status:'success',detail:'Investigation and response completed. Select Show to review the background activity.'});panel.classList.add('complete');badge.textContent='Completed';collapseActivity();
  }
  else if(type==='turn.cancelled'){
    rowFor(turn,'complete','Turn cancelled',{status:'waiting',detail:'The owner stopped this response.'});panel.classList.add('failed');badge.textContent='Cancelled';
  }
  else if(type==='turn.failed'){
    rowFor(turn,'complete','Turn failed safely',{status:'error',detail:`${payload.message||'The turn failed.'}${payload.diagnostic_id?` · ${payload.diagnostic_id}`:''}`});panel.classList.add('failed');badge.textContent='Failed';
  }
});

document.addEventListener('thread-selected',()=>{visibleTurn='';states.clear();list.replaceChildren();panel.hidden=true;});
toggle.addEventListener('click',()=>{const hidden=body.classList.toggle('activity-body-hidden');toggle.textContent=hidden?'Show':'Hide';toggle.setAttribute('aria-expanded',String(!hidden));});
document.querySelector('#activity-open-tools').addEventListener('click',()=>document.querySelector('#tool-drawer').scrollIntoView({behavior:'smooth',block:'start'}));
