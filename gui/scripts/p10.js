import {getJSON} from './api.js';

function element(tag,className,text){
  const node=document.createElement(tag);
  if(className)node.className=className;
  if(text!==undefined)node.textContent=text;
  return node;
}

async function loadP10Status(){
  const target=document.querySelector('#p10-status');
  if(!target)return;
  try{
    const [session,operations,readiness]=await Promise.all([
      getJSON('/api/p10/session'),getJSON('/api/p10/operations'),getJSON('/api/p10/readiness')
    ]);
    const count=Array.isArray(operations)?operations.length:(operations.operations||[]).length;
    target.replaceChildren();
    const coverage=readiness.asset_coverage||{};
    const counts=coverage.coverage_counts||{};
    target.append(
      element('div','p10-summary',`OWNER_FULL_CONTROL · ${coverage.total_entities||0} canonical assets · ${count} reviewed operations · global writes ${session.execution_enabled?'enabled':'disabled'} · one exact approval per immutable batch.`),
      element('div','p10-warning','Safe registered reads are automatic. No real write runs until identity, credentials, current state, risk, validation, rollback, owner session, and the complete plan digest are exact.'),
      element('div','p10-summary',`Coverage: READY ${counts.READY||0} · conflicts ${counts.IDENTITY_CONFLICT||0} · credential blockers ${counts.CREDENTIAL_REFERENCE_MISSING||0} · identity blockers ${counts.IDENTITY_PIN_MISSING||0} · unsupported ${counts.TRANSPORT_UNSUPPORTED||0} · excluded ${counts.OWNER_EXCLUDED||0}.`)
    );
    const wrap=element('div','p10-table-wrap');
    const table=element('table','p10-table');
    const head=document.createElement('thead');const heading=document.createElement('tr');
    ['Platform','Transport','Write creds','Rendered actions','Blocked actions','Live status'].forEach(label=>heading.append(element('th','',label)));
    head.append(heading);table.append(head);
    const body=document.createElement('tbody');
    (readiness.platforms||[]).forEach(platform=>{
      const configured=(platform.bindings||[]).filter(item=>item.write_credentials_configured).length;
      const row=document.createElement('tr');
      [platform.platform,platform.transport,`${configured}/${(platform.bindings||[]).length}`,
        String((platform.renderer_coverage?.forward_supported||[]).length),String((platform.renderer_coverage?.blocked_actions||[]).length)]
        .forEach(value=>row.append(element('td','',value)));
      row.append(element('td','p10-blocked','BLOCKED'));body.append(row);
    });
    table.append(body);wrap.append(table);target.append(wrap);
    const assetWrap=element('div','p10-table-wrap');const assetTable=element('table','p10-table');
    const assetHead=document.createElement('thead');const assetHeading=document.createElement('tr');
    ['Canonical asset','Platform','Management target','Bindings','Coverage','Exact blocker'].forEach(label=>assetHeading.append(element('th','',label)));
    assetHead.append(assetHeading);assetTable.append(assetHead);const assetBody=document.createElement('tbody');
    (coverage.entities||[]).forEach(asset=>{const row=document.createElement('tr');
      [asset.entity_id,asset.platform,asset.documented_management_ip||asset.documented_fqdn,(asset.binding_ids||[]).join(', ')||'none',asset.status,asset.blocker||'none']
        .forEach((value,index)=>row.append(element('td',index===4&&asset.status!=='READY'?'p10-blocked':'',String(value))));assetBody.append(row);});
    assetTable.append(assetBody);assetWrap.append(assetTable);target.append(assetWrap);
  }catch(error){target.textContent=`P10 unavailable: ${error.message}`;}
}
loadP10Status();
