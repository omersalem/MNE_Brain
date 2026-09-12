import {getJSON} from './api.js';

// Presentation-only visibility for the server's authorization boundary.
// Ordinary redacted context and exact read-only checks are automatic for the
// authenticated owner. Writes show their risk preview and use one Accept/Deny action.
getJSON('/api/v2/settings').then(settings=>{
  document.documentElement.dataset.redactedContextAuthorization=
    settings.auto_authorize_redacted_conversation?'automatic':'explicit';
  const liveStatus=document.querySelector('#live-status');
  if(liveStatus)liveStatus.title='Exact registered P7 reads run automatically under the authenticated owner session. Writes never inherit this authorization.';
}).catch(()=>{});
