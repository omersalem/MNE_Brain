import {appState,emit,setStatus} from './api.js';

let stream;

export function startTurnStream(turn){
  if(stream)stream.close();
  appState().activeTurn=turn;document.querySelector('#cancel-turn').disabled=false;
  stream=new EventSource(`/api/v2/turns/${encodeURIComponent(turn.turn_id)}/events`);
  const eventTypes=['turn.started','investigation.planned','agent.progress','agent.plan','answer.delta','answer.final','evidence.accepted','tool.proposed','tool.approval_required','tool.started','tool.completed','command.started','command.output','command.completed','file.change','file.diff','turn.completed','turn.cancelled','turn.failed'];
  for(const type of eventTypes){
    stream.addEventListener(type,event=>{
      const envelope=JSON.parse(event.data);emit('stream-event',{envelope});
      if(type==='answer.delta')emit('answer-delta',{text:envelope.redacted_payload.text||''});
      if(type==='answer.final')emit('answer-final',{text:envelope.redacted_payload.text||''});
      if(type==='agent.progress')emit('agent-progress',envelope.redacted_payload);
      if(type==='agent.plan')emit('agent-plan',envelope.redacted_payload);
      if(type==='evidence.accepted')emit('evidence-accepted',envelope.redacted_payload);
      if(type==='investigation.planned'){
        const count=Number(envelope.redacted_payload.candidate_count||0);
        setStatus(`Deep live plan · ${count} governed check${count===1?'':'s'}`);
        emit('investigation-planned',envelope.redacted_payload);
      }
      if(type.startsWith('tool.'))emit('tool-event',{envelope});
      if(type.startsWith('command.')||type.startsWith('file.'))emit('tool-event',{envelope});
      if(['turn.completed','turn.cancelled','turn.failed'].includes(type)){
        setStatus(type==='turn.failed'?(envelope.redacted_payload.message||'Request failed'):type.replace('turn.','').toUpperCase());
        document.querySelector('#cancel-turn').disabled=true;appState().activeTurn=null;stream.close();stream=null;
      }
    });
  }
  stream.onopen=()=>setStatus('Streaming');
  stream.onerror=()=>{if(appState().activeTurn)setStatus(navigator.onLine?'Stream reconnecting…':'Offline · waiting to reconnect');};
}
