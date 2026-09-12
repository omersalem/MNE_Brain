import { appState, getJSON, mutateJSON } from './api.js';

// --- Element References ---
const secDialog = document.querySelector('#security-agent-dialog');
const secOpenBtn = document.querySelector('#security-agent-button');
const secHeaderStatusPill = document.querySelector('#sec-header-status-pill');

// Overview Action Buttons
const secBtnRun = document.querySelector('#sec-btn-run');
const secBtnViewHtml = document.querySelector('#sec-btn-view-html');
const secBtnDownloadPdf = document.querySelector('#sec-btn-download-pdf');
const secBtnTestEmail = document.querySelector('#sec-btn-test-email');

// Overview Metric Strip
const secStatCritical = document.querySelector('#sec-stat-critical');
const secStatHigh = document.querySelector('#sec-stat-high');
const secStatMedium = document.querySelector('#sec-stat-medium');
const secStatTotal = document.querySelector('#sec-stat-total');
const secStatDevices = document.querySelector('#sec-stat-devices');

// Schedule Controls
const secScheduleForm = document.querySelector('#sec-schedule-form');
const secScheduleEnabledInput = document.querySelector('#sec-schedule-enabled');
const secScheduleTimeInput = document.querySelector('#sec-schedule-time');
const secSchedulerBadge = document.querySelector('#sec-scheduler-badge');
const secTaskStateEl = document.querySelector('#sec-task-state');
const secTaskNextEl = document.querySelector('#sec-task-next');
const secScheduleStatusEl = document.querySelector('#sec-schedule-status');

// Recipients Controls
const secRecipientsListEl = document.querySelector('#sec-recipients-list');
const secRecipientsCountEl = document.querySelector('#sec-recipients-count');
const secNewEmailInput = document.querySelector('#sec-new-email');
const secBtnAddEmail = document.querySelector('#sec-btn-add-email');
const secBtnSaveRecipients = document.querySelector('#sec-btn-save-recipients');
const secRecipientsStatusEl = document.querySelector('#sec-recipients-status');

// Devices Grid
const secDevicesGridEl = document.querySelector('#sec-devices-grid');

// Run Configuration Controls
const secProfileSelect = document.querySelector('#sec-profile-select');
const secRunModeSelect = document.querySelector('#sec-run-mode');
const secTimePresetSelect = document.querySelector('#sec-time-preset');
const secCustomTimeGroup = document.querySelector('#sec-custom-time-group');
const secStartTimeInput = document.querySelector('#sec-start-time');
const secEndTimeInput = document.querySelector('#sec-end-time');
const secBtnSelectAllCollectors = document.querySelector('#sec-btn-select-all-collectors');
const secBtnDeselectAllCollectors = document.querySelector('#sec-btn-deselect-all-collectors');
const secAnalysisEngineSelect = document.querySelector('#sec-analysis-engine');
const secAnalysisModelInput = document.querySelector('#sec-analysis-model');
const secSendEmailCheck = document.querySelector('#sec-send-email-check');
const secBtnStartReview = document.querySelector('#sec-btn-start-review');

// Progress Console Elements
const secConsoleSection = document.querySelector('#sec-console-section');
const secRunStageEl = document.querySelector('#sec-run-stage');
const secCurrentCollectorEl = document.querySelector('#sec-current-collector');
const secElapsedTimeEl = document.querySelector('#sec-elapsed-time');
const secRunStatusIndicator = document.querySelector('#sec-run-status-indicator');
const secCountFetchedEl = document.querySelector('#sec-count-fetched');
const secCountParsedEl = document.querySelector('#sec-count-parsed');
const secCollectorDurationEl = document.querySelector('#sec-collector-duration');
const secRunConsoleEl = document.querySelector('#sec-run-console');

// Run Action Controls
const secBtnCancelRun = document.querySelector('#sec-btn-cancel-run');
const secBtnRetryFailed = document.querySelector('#sec-btn-retry-failed');
const secBtnRunAgain = document.querySelector('#sec-btn-run-again');
const secBtnOpenResults = document.querySelector('#sec-btn-open-results');

// History Table
const secHistoryTable = document.querySelector('#sec-history-table');
const secHistoryTbody = document.querySelector('#sec-history-tbody');
const secHistoryRefreshBtn = document.querySelector('#sec-history-refresh-btn');
const secTrendsContainer = document.querySelector('#sec-trends-container');

// Incidents Table
const secIncidentsTable = document.querySelector('#sec-incidents-table');
const secIncidentsTbody = document.querySelector('#sec-incidents-tbody');
const secIncidentsSearch = document.querySelector('#sec-incidents-search');
const secIncidentsFilterSev = document.querySelector('#sec-incidents-filter-sev');
const secIncidentsFilterStatus = document.querySelector('#sec-incidents-filter-status');

// Incident Drill-Down Modal Elements
const secIncidentDetailDialog = document.querySelector('#sec-incident-detail-dialog');
const secDetailTitle = document.querySelector('#sec-detail-title');
const secDetailSubtitle = document.querySelector('#sec-detail-subtitle');
const secDetailSeverityPill = document.querySelector('#sec-detail-severity-pill');
const secDetailLifecyclePill = document.querySelector('#sec-detail-lifecycle-pill');
const secDetailCloseBtn = document.querySelector('#sec-detail-close-btn');
const secDetailFingerprint = document.querySelector('#sec-detail-fingerprint');
const secDetailDisplayId = document.querySelector('#sec-detail-display-id');
const secDetailFirstSeen = document.querySelector('#sec-detail-first-seen');
const secDetailLastSeen = document.querySelector('#sec-detail-last-seen');
const secDetailOccurrences = document.querySelector('#sec-detail-occurrences');
const secDetailEvents = document.querySelector('#sec-detail-events');
const secDetailRationale = document.querySelector('#sec-detail-rationale');
const secDetailAttacker = document.querySelector('#sec-detail-attacker');
const secDetailTargets = document.querySelector('#sec-detail-targets');
const secDetailDevices = document.querySelector('#sec-detail-devices');
const secDetailBranches = document.querySelector('#sec-detail-branches');
const secDetailAction = document.querySelector('#sec-detail-action');
const secDetailBlocked = document.querySelector('#sec-detail-blocked');
const secDetailAllowed = document.querySelector('#sec-detail-allowed');
const secDetailStatusSelect = document.querySelector('#sec-detail-status-select');
const secDetailStatusNote = document.querySelector('#sec-detail-status-note');
const secDetailUpdateStatusBtn = document.querySelector('#sec-detail-update-status-btn');
const secDetailStatusMsg = document.querySelector('#sec-detail-status-msg');
const secDetailNotesList = document.querySelector('#sec-detail-notes-list');
const secDetailNewNoteInput = document.querySelector('#sec-detail-new-note-input');
const secDetailAddNoteBtn = document.querySelector('#sec-detail-add-note-btn');
const secDetailTimelineList = document.querySelector('#sec-detail-timeline-list');
const secDetailPlaybookCli = document.querySelector('#sec-detail-playbook-cli');
const secDetailPlaybookGui = document.querySelector('#sec-detail-playbook-gui');
const secDetailBtnAnalyzeCodex = document.querySelector('#sec-detail-btn-analyze-codex');
const secDetailBtnAnalyzeAntigravity = document.querySelector('#sec-detail-btn-analyze-antigravity');
const secDetailBtnAnalyzeBoth = document.querySelector('#sec-detail-btn-analyze-both');
const secDetailBtnOpenChat = document.querySelector('#sec-detail-btn-open-chat');
const secDetailBtnTroubleshoot = document.querySelector('#sec-detail-btn-troubleshoot');
const secIncidentTroubleshootContainer = document.querySelector('#sec-incident-troubleshoot-container');
const secDetailPcName = document.querySelector('#sec-detail-pc-name');
const secDetailUsername = document.querySelector('#sec-detail-username');
const secDetailDeviceOwner = document.querySelector('#sec-detail-device-owner');
const secDetailMac = document.querySelector('#sec-detail-mac');
const secDetailScope = document.querySelector('#sec-detail-scope');
const secDetailIdStatus = document.querySelector('#sec-detail-id-status');
const secDetailConfidence = document.querySelector('#sec-detail-confidence');
const secDetailIdSources = document.querySelector('#sec-detail-id-sources');
const secDetailIdObserved = document.querySelector('#sec-detail-id-observed');
const secDetailIdDiagnostics = document.querySelector('#sec-detail-id-diagnostics');
const secDetailIdDiagnosticsContainer = document.querySelector('#sec-detail-id-diagnostics-container');
const secDetailBtnResolveIdentity = document.querySelector('#sec-detail-btn-resolve-identity');

// AI Analysis Panel Elements
const secAnalysisTargetType = document.querySelector('#sec-analysis-target-type');
const secAnalysisEngineSelectPanel = document.querySelector('#sec-analysis-engine-select');
const secRunAnalysisBtn = document.querySelector('#sec-run-analysis-btn');
const secAnalysisProgress = document.querySelector('#sec-analysis-progress');
const secAnalysisContainer = document.querySelector('#sec-analysis-container');

// State Variables
let secLocalRecipients = [];
let activeRunId = sessionStorage.getItem('mne_sec_active_run_id') || null;
let activeEventSource = null;
let runStartTime = null;
let runTimerInterval = null;
let lastEventSeq = 0;
let cachedIncidents = [];
let cachedProfiles = [];
let activeIncidentFingerprint = null;

// --- Helper Utilities ---

function escapeSecHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function setSecNotice(element, text, isError = false) {
  if (!element) return;
  element.textContent = text;
  element.className = 'sec-status-msg ' + (isError ? 'error' : 'success');
  setTimeout(() => {
    if (element.textContent === text) {
      element.textContent = '';
      element.className = 'sec-status-msg';
    }
  }, 5000);
}

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function startElapsedTimer(startTimeMs) {
  stopElapsedTimer();
  runStartTime = startTimeMs || Date.now();
  runTimerInterval = setInterval(() => {
    if (secElapsedTimeEl) {
      const elapsedSec = (Date.now() - runStartTime) / 1000;
      secElapsedTimeEl.textContent = formatDuration(elapsedSec);
    }
  }, 1000);
}

function stopElapsedTimer() {
  if (runTimerInterval) {
    clearInterval(runTimerInterval);
    runTimerInterval = null;
  }
}

function appendConsoleLog(line) {
  if (!secRunConsoleEl) return;
  const timeStr = new Date().toLocaleTimeString();
  secRunConsoleEl.textContent += `[${timeStr}] ${line}\n`;
  secRunConsoleEl.scrollTop = secRunConsoleEl.scrollHeight;
}

// --- Tab Navigation ---

const tabButtons = document.querySelectorAll('.sec-tab-btn');
const tabPanels = document.querySelectorAll('.sec-tab-panel');

function switchTab(targetId) {
  tabButtons.forEach(btn => {
    const isTarget = btn.dataset.target === targetId;
    btn.classList.toggle('active', isTarget);
    btn.setAttribute('aria-selected', String(isTarget));
  });

  tabPanels.forEach(panel => {
    const isTarget = panel.id === targetId;
    panel.classList.toggle('active', isTarget);
    panel.hidden = !isTarget;
  });

  if (targetId === 'sec-panel-history') {
    fetchHistory();
  }
  if (targetId === 'sec-panel-incidents') {
    fetchIncidents();
  }
}

tabButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    if (btn.dataset.target) switchTab(btn.dataset.target);
  });
});

// --- Recipients Presentation ---

function renderSecRecipients() {
  if (!secRecipientsListEl) return;
  secRecipientsListEl.replaceChildren();
  if (secRecipientsCountEl) {
    secRecipientsCountEl.textContent = `${secLocalRecipients.length} Recipient${secLocalRecipients.length === 1 ? '' : 's'}`;
  }

  if (secLocalRecipients.length === 0) {
    const hint = document.createElement('span');
    hint.className = 'sec-empty-hint';
    hint.textContent = 'No recipient emails configured yet. Add one below.';
    secRecipientsListEl.appendChild(hint);
    return;
  }

  secLocalRecipients.forEach((email, index) => {
    const chip = document.createElement('span');
    chip.className = 'sec-email-chip';

    const emailSpan = document.createElement('span');
    emailSpan.className = 'chip-email';
    emailSpan.textContent = email;
    chip.appendChild(emailSpan);

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'chip-remove-btn';
    removeBtn.title = `Remove ${email}`;
    removeBtn.dataset.index = String(index);
    removeBtn.textContent = '✕';
    chip.appendChild(removeBtn);

    secRecipientsListEl.appendChild(chip);
  });
}

// --- Devices Presentation ---

function renderSecDevices(devices = []) {
  if (!secDevicesGridEl) return;
  secDevicesGridEl.replaceChildren();
  if (!devices || devices.length === 0) {
    const hint = document.createElement('p');
    hint.className = 'sec-empty-hint';
    hint.textContent = 'No appliance catalog found.';
    secDevicesGridEl.appendChild(hint);
    return;
  }

  devices.forEach(dev => {
    const row = document.createElement('div');
    row.className = 'sec-device-row';

    const mainDiv = document.createElement('div');
    mainDiv.className = 'sec-device-main';

    const titleRow = document.createElement('div');
    titleRow.className = 'sec-device-title-row';

    const strongName = document.createElement('strong');
    strongName.textContent = dev.name || 'Appliance';
    titleRow.appendChild(strongName);

    const ipSpan = document.createElement('span');
    ipSpan.className = 'sec-device-ip';
    ipSpan.textContent = dev.ip || '';
    titleRow.appendChild(ipSpan);

    mainDiv.appendChild(titleRow);

    const subDiv = document.createElement('div');
    subDiv.className = 'sec-device-sub';

    const roleSpan = document.createElement('span');
    roleSpan.className = 'sec-device-role';
    roleSpan.textContent = dev.role || '';
    subDiv.appendChild(roleSpan);

    const sepSpan = document.createElement('span');
    sepSpan.className = 'sec-device-sep';
    sepSpan.textContent = ' · ';
    subDiv.appendChild(sepSpan);

    const protoSpan = document.createElement('span');
    protoSpan.className = 'sec-device-proto';
    protoSpan.textContent = dev.protocol || '';
    subDiv.appendChild(protoSpan);

    mainDiv.appendChild(subDiv);
    row.appendChild(mainDiv);

    const metaDiv = document.createElement('div');
    metaDiv.className = 'sec-device-meta';

    if (dev.last_events_count) {
      const eventsBadge = document.createElement('span');
      eventsBadge.className = 'badge-code';
      eventsBadge.textContent = `${dev.last_events_count} events`;
      metaDiv.appendChild(eventsBadge);
    }

    const status = dev.last_collection_status || 'CONFIGURED';
    const isSuccess = status === 'SUCCESS' || status === 'READY' || status === 'CONFIGURED';
    const statusClass = isSuccess ? 'safe' : (status === 'PARTIAL' ? 'warning' : 'danger');

    const statusPill = document.createElement('span');
    statusPill.className = `status-pill ${statusClass}`;
    statusPill.textContent = status;
    metaDiv.appendChild(statusPill);

    row.appendChild(metaDiv);
    secDevicesGridEl.appendChild(row);
  });
}

// --- Status Refresh ---

export async function refreshSecurityStatus() {
  try {
    const data = await getJSON('/api/v2/security-agent/status');
    const cfg = data.config || {};
    const sched = data.scheduler || {};
    const last = data.last_status || {};
    const reports = data.reports || {};

    if (secScheduleTimeInput) secScheduleTimeInput.value = cfg.schedule_time || '07:00';
    if (secScheduleEnabledInput) secScheduleEnabledInput.checked = Boolean(cfg.schedule_enabled);

    if (secTaskStateEl) {
      secTaskStateEl.textContent = sched.state || (sched.registered ? 'Registered' : 'Not Registered');
    }
    if (secTaskNextEl) {
      if (sched.NextRunTime) {
        try {
          const d = new Date(sched.NextRunTime);
          secTaskNextEl.textContent = d.toLocaleString();
        } catch {
          secTaskNextEl.textContent = sched.NextRunTime;
        }
      } else {
        secTaskNextEl.textContent = cfg.schedule_enabled ? `Daily at ${cfg.schedule_time}` : 'Automation Paused';
      }
    }

    if (secSchedulerBadge) {
      const isSchedOk = sched.state === 'Ready' || sched.state === 'Queued' || sched.state === 'Running';
      secSchedulerBadge.className = 'status-pill ' + (cfg.schedule_enabled ? (isSchedOk ? 'safe' : 'warning') : 'muted');
      secSchedulerBadge.textContent = cfg.schedule_enabled ? (sched.state || 'Active') : 'Disabled';
    }

    if (secHeaderStatusPill) {
      secHeaderStatusPill.className = 'status-pill ' + (cfg.schedule_enabled ? 'safe' : 'warning');
      secHeaderStatusPill.textContent = cfg.schedule_enabled ? `Daily @ ${cfg.schedule_time}` : 'Schedule Paused';
    }

    secLocalRecipients = [...(cfg.recipients || [])];
    renderSecRecipients();

    if (secStatCritical) secStatCritical.textContent = last.critical_count ?? 0;
    if (secStatHigh) secStatHigh.textContent = last.high_count ?? 0;
    if (secStatMedium) secStatMedium.textContent = last.medium_count ?? 0;
    if (secStatTotal) secStatTotal.textContent = last.total_incidents ?? 0;
    if (secStatDevices) {
      const onlineCount = (last.collectors || []).filter(c => c.status === 'SUCCESS').length;
      secStatDevices.textContent = (last.collectors && last.collectors.length) ? `${onlineCount} / ${last.collectors.length}` : '7 / 7';
    }

    if (secBtnViewHtml) {
      secBtnViewHtml.disabled = !reports.html?.available;
      secBtnViewHtml.title = reports.html?.available ? `Open ${reports.html.filename}` : 'No HTML report generated yet';
    }
    if (secBtnDownloadPdf) {
      secBtnDownloadPdf.disabled = !reports.pdf?.available;
      secBtnDownloadPdf.title = reports.pdf?.available ? `Download ${reports.pdf.filename}` : 'No PDF report generated yet';
    }

    renderSecDevices(data.devices || []);
    fetchProfiles();
  } catch (err) {
    console.error('Failed refreshing security status:', err);
    if (secHeaderStatusPill) {
      secHeaderStatusPill.className = 'status-pill danger';
      secHeaderStatusPill.textContent = 'Offline / Error';
    }
  }
}

// --- Profiles Management ---

const COLLECTOR_SHORT_MAP = {
  all: ['fortigate_core', 'fortianalyzer', 'f5_bigip', 'cisco_fmc', 'sophos_email', 'active_directory', 'exchange_2019'],
  fortigate: ['fortigate_core'],
  fortianalyzer: ['fortianalyzer'],
  f5: ['f5_bigip'],
  f5_bigip: ['f5_bigip'],
  cisco: ['cisco_fmc'],
  cisco_fmc: ['cisco_fmc'],
  fmc: ['cisco_fmc'],
  sophos: ['sophos_email'],
  sophos_email: ['sophos_email'],
  ad: ['active_directory'],
  active_directory: ['active_directory'],
  exchange: ['exchange_2019'],
  exchange_2019: ['exchange_2019'],
};

const ENGINE_MODEL_OPTIONS = {
  CODEX: ['chatgpt', 'gpt-4o', 'o3-mini', 'gpt-4.5-preview'],
  ANTIGRAVITY: ['inherit', 'pro', 'flash', 'flash_lite', 'gemini-2.5-pro', 'gemini-2.5-flash'],
  BOTH: ['Default (Provider native default per engine)'],
};

function updateAnalysisModelChoices() {
  const engine = secAnalysisEngineSelect ? secAnalysisEngineSelect.value : 'NONE';
  const datalist = document.querySelector('#sec-analysis-model-list');
  if (!datalist) return;
  datalist.replaceChildren();
  const models = ENGINE_MODEL_OPTIONS[engine] || [];
  models.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m;
    datalist.appendChild(opt);
  });
}

function applyProfileToForm(profile) {
  if (!profile) return;
  const opts = profile.options || {};
  const mode = profile.mode || opts.mode;
  if (secRunModeSelect && mode) {
    secRunModeSelect.value = mode;
  }
  const hours = profile.hours_back || opts.time_window?.hours;
  if (secTimePresetSelect && hours) {
    secTimePresetSelect.value = String(hours);
    if (secCustomTimeGroup) secCustomTimeGroup.hidden = true;
  }
  const rawCollectors = profile.collector_ids || opts.selected_collectors;
  if (Array.isArray(rawCollectors)) {
    const targetSet = new Set();
    rawCollectors.forEach(col => {
      const mapped = COLLECTOR_SHORT_MAP[String(col).toLowerCase()];
      if (mapped) {
        mapped.forEach(m => targetSet.add(m));
      } else {
        targetSet.add(col);
      }
    });
    const checkboxes = document.querySelectorAll('input[name="sec-collector"]');
    checkboxes.forEach(cb => {
      cb.checked = targetSet.has(cb.value);
    });
  }
  const engine = profile.analysis_engine || opts.ai_engine;
  if (secAnalysisEngineSelect && engine) {
    secAnalysisEngineSelect.value = engine;
    updateAnalysisModelChoices();
  }
  const model = profile.analysis_model || opts.ai_model;
  if (secAnalysisModelInput && model) {
    secAnalysisModelInput.value = model;
  }
  const sendEmail = profile.send_email ?? opts.send_email;
  if (secSendEmailCheck && sendEmail !== undefined) {
    secSendEmailCheck.checked = Boolean(sendEmail);
  }
}

async function fetchProfiles() {
  if (!secProfileSelect) return;
  try {
    const data = await getJSON('/api/v2/security-agent/profiles');
    cachedProfiles = data.profiles || [];
    const activeId = data.active_profile_id || data.active_profile || (cachedProfiles[0] && (cachedProfiles[0].id || cachedProfiles[0].profile_id)) || '';

    secProfileSelect.replaceChildren();
    cachedProfiles.forEach(p => {
      const pid = p.id || p.profile_id;
      const opt = document.createElement('option');
      opt.value = pid;
      opt.textContent = p.name;
      if (pid === activeId || p.name === activeId) opt.selected = true;
      secProfileSelect.appendChild(opt);
    });

    const current = cachedProfiles.find(p => (p.id || p.profile_id) === activeId || p.name === activeId);
    if (current) {
      applyProfileToForm(current);
    }
  } catch (err) {
    console.warn('Could not load security review profiles:', err);
  }
}

if (secProfileSelect) {
  secProfileSelect.addEventListener('change', () => {
    const selectedId = secProfileSelect.value;
    const profile = cachedProfiles.find(p => (p.id || p.profile_id) === selectedId || p.name === selectedId);
    if (profile) {
      applyProfileToForm(profile);
    }
  });
}

if (secAnalysisEngineSelect) {
  secAnalysisEngineSelect.addEventListener('change', updateAnalysisModelChoices);
}

// --- SSE Real-Time Event Streaming ---

function connectEventStream(runId) {
  if (activeEventSource) {
    activeEventSource.close();
    activeEventSource = null;
  }

  activeRunId = runId;
  sessionStorage.setItem('mne_sec_active_run_id', runId);

  if (secConsoleSection) secConsoleSection.hidden = false;
  if (secBtnCancelRun) secBtnCancelRun.disabled = false;
  if (secBtnRetryFailed) secBtnRetryFailed.hidden = true;
  if (secBtnRunAgain) secBtnRunAgain.hidden = true;
  if (secBtnOpenResults) secBtnOpenResults.hidden = true;

  startElapsedTimer();

  const url = `/api/v2/security-agent/runs/${encodeURIComponent(runId)}/events`;
  activeEventSource = new EventSource(url);

  const handleEvent = (event) => {
    try {
      const evId = parseInt(event.lastEventId || event.id, 10);
      if (!isNaN(evId)) lastEventSeq = evId;

      const data = JSON.parse(event.data || '{}');
      const type = event.type;

      if (type === 'run.queued') {
        if (secRunStatusIndicator) {
          secRunStatusIndicator.textContent = 'QUEUED';
          secRunStatusIndicator.className = 'activity-state muted';
        }
        if (secRunStageEl) secRunStageEl.textContent = 'QUEUED';
        appendConsoleLog(`Run queued (ID: ${runId})`);
      } else if (type === 'run.started') {
        if (secRunStatusIndicator) {
          secRunStatusIndicator.textContent = 'RUNNING';
          secRunStatusIndicator.className = 'activity-state';
        }
        if (secRunStageEl) secRunStageEl.textContent = 'STARTING';
        appendConsoleLog(`Review execution started`);
      } else if (type === 'stage.started') {
        const stage = data.stage || 'STAGE';
        if (secRunStageEl) secRunStageEl.textContent = stage;
        appendConsoleLog(`Entering stage: ${stage}`);
      } else if (type === 'collector.started') {
        const devName = data.device_name || data.collector_id || 'Collector';
        if (secCurrentCollectorEl) secCurrentCollectorEl.textContent = devName;
        appendConsoleLog(`Collecting from ${devName}…`);
      } else if (type === 'collector.completed') {
        const devName = data.device_name || data.collector_id || 'Collector';
        const st = data.status || 'DONE';
        const fetched = data.records_fetched ?? 0;
        const dur = data.duration_seconds ?? 0;
        if (secCountFetchedEl) secCountFetchedEl.textContent = String(fetched);
        if (secCountParsedEl) secCountParsedEl.textContent = String(data.records_parsed ?? fetched);
        if (secCollectorDurationEl) secCollectorDurationEl.textContent = `${dur}s`;
        appendConsoleLog(`  • ${devName}: ${st} (${fetched} events in ${dur}s)`);
      } else if (type === 'run.cancelling') {
        if (secRunStatusIndicator) {
          secRunStatusIndicator.textContent = 'CANCELLING';
          secRunStatusIndicator.className = 'activity-state warning';
        }
        appendConsoleLog(`Cancellation requested by operator…`);
      } else if (type === 'run.cancelled') {
        if (secRunStatusIndicator) {
          secRunStatusIndicator.textContent = 'CANCELLED';
          secRunStatusIndicator.className = 'activity-state warning';
        }
        if (secRunStageEl) secRunStageEl.textContent = 'CANCELLED';
        appendConsoleLog(`Run cancelled.`);
        finishRun(false);
      } else if (type === 'run.completed') {
        const finalState = data.state || 'COMPLETED';
        if (secRunStatusIndicator) {
          secRunStatusIndicator.textContent = finalState;
          secRunStatusIndicator.className = 'activity-state ' + (finalState === 'COMPLETED' ? 'success' : 'warning');
        }
        if (secRunStageEl) secRunStageEl.textContent = finalState;
        const counts = data.incident_counts || {};
        appendConsoleLog(`Review complete! Identified ${counts.total ?? 0} incidents (Critical: ${counts.critical ?? 0}, High: ${counts.high ?? 0}, Medium: ${counts.medium ?? 0}).`);
        finishRun(true, finalState);
      } else if (type === 'run.failed') {
        if (secRunStatusIndicator) {
          secRunStatusIndicator.textContent = 'FAILED';
          secRunStatusIndicator.className = 'activity-state danger';
        }
        if (secRunStageEl) secRunStageEl.textContent = 'FAILED';
        appendConsoleLog(`Run failed: ${data.error || 'Execution encountered an error'}`);
        finishRun(false, 'FAILED');
      }
    } catch (e) {
      console.error('Error handling SSE event:', e);
    }
  };

  const eventTypes = [
    'run.queued',
    'run.started',
    'stage.started',
    'collector.started',
    'collector.completed',
    'run.cancelling',
    'run.cancelled',
    'run.completed',
    'run.failed',
  ];

  eventTypes.forEach(t => activeEventSource.addEventListener(t, handleEvent));

  activeEventSource.onerror = () => {
    // Check if run already finished on server
    checkRunTerminalStatus(runId);
  };
}

async function checkRunTerminalStatus(runId) {
  try {
    const run = await getJSON(`/api/v2/security-agent/runs/${encodeURIComponent(runId)}`);
    if (run && ['COMPLETED', 'PARTIAL', 'FAILED', 'CANCELLED'].includes(run.state)) {
      if (secRunStatusIndicator) {
        secRunStatusIndicator.textContent = run.state;
        secRunStatusIndicator.className = 'activity-state ' + (run.state === 'COMPLETED' ? 'success' : (run.state === 'FAILED' ? 'danger' : 'warning'));
      }
      if (secRunStageEl) secRunStageEl.textContent = run.stage || run.state;
      finishRun(run.state === 'COMPLETED' || run.state === 'PARTIAL', run.state);
    }
  } catch (e) {
    console.debug('Polling check for terminal state error:', e);
  }
}

function finishRun(success, state = 'COMPLETED') {
  stopElapsedTimer();
  if (activeEventSource) {
    activeEventSource.close();
    activeEventSource = null;
  }
  if (secBtnCancelRun) secBtnCancelRun.disabled = true;
  if (secBtnRunAgain) secBtnRunAgain.hidden = false;
  if (state === 'PARTIAL' || state === 'FAILED') {
    if (secBtnRetryFailed) secBtnRetryFailed.hidden = false;
  }
  if (secBtnOpenResults && (state === 'COMPLETED' || state === 'PARTIAL')) {
    secBtnOpenResults.hidden = false;
  }
  refreshSecurityStatus();
}

// --- Run Review Submission ---

async function submitSecurityReview() {
  const mode = secRunModeSelect ? secRunModeSelect.value : 'FULL';

  // Collectors
  const collectorCheckboxes = document.querySelectorAll('input[name="sec-collector"]:checked');
  const collector_ids = Array.from(collectorCheckboxes).map(cb => cb.value);
  if (collector_ids.length === 0) {
    alert('Please select at least one collector appliance to review.');
    return;
  }

  // Time Window
  const timePreset = secTimePresetSelect ? secTimePresetSelect.value : '24';
  let hours_back = 24.0;
  let start_time = null;
  let end_time = null;

  if (timePreset === 'custom') {
    start_time = secStartTimeInput?.value ? new Date(secStartTimeInput.value).toISOString() : null;
    end_time = secEndTimeInput?.value ? new Date(secEndTimeInput.value).toISOString() : null;
    if (!start_time || !end_time) {
      alert('Please specify both Start Time and End Time for custom time window.');
      return;
    }
  } else {
    hours_back = parseFloat(timePreset) || 24.0;
  }

  // Categories
  const categoryCheckboxes = document.querySelectorAll('input[name="sec-category"]:checked');
  const categories = Array.from(categoryCheckboxes).map(cb => cb.value);

  // Analysis Engine
  const analysis_engine = secAnalysisEngineSelect ? secAnalysisEngineSelect.value : 'NONE';
  const analysis_model = secAnalysisModelInput?.value.trim() || null;

  // Formats & Email
  const formatCheckboxes = document.querySelectorAll('input[name="sec-report-format"]:checked');
  const report_formats = Array.from(formatCheckboxes).map(cb => cb.value);
  const send_email = secSendEmailCheck ? secSendEmailCheck.checked : true;

  const payload = {
    mode,
    collector_ids,
    analysis_engine,
    send_email,
    report_formats: report_formats.length ? report_formats : ['HTML', 'PDF'],
    categories: categories.length ? categories : undefined,
  };

  if (timePreset === 'custom') {
    payload.start_time = start_time;
    payload.end_time = end_time;
  } else {
    payload.hours_back = hours_back;
  }

  if (analysis_model) {
    payload.analysis_model = analysis_model;
  }

  if (secRunConsoleEl) {
    secRunConsoleEl.textContent = '';
  }

  try {
    if (secBtnStartReview) secBtnStartReview.disabled = true;
    const res = await mutateJSON('/api/v2/security-agent/runs', payload);
    const runId = res.run_id;
    connectEventStream(runId);
  } catch (err) {
    alert(`Failed to start security review: ${err.message}`);
  } finally {
    if (secBtnStartReview) secBtnStartReview.disabled = false;
  }
}

// --- History Presentation ---

async function fetchHistory() {
  if (!secHistoryTbody) return;
  secHistoryTbody.replaceChildren();
  const loadingRow = document.createElement('tr');
  const loadingTd = document.createElement('td');
  loadingTd.colSpan = 7;
  loadingTd.className = 'sec-empty-cell';
  loadingTd.textContent = 'Loading historical runs…';
  loadingRow.appendChild(loadingTd);
  secHistoryTbody.appendChild(loadingRow);

  try {
    const data = await getJSON('/api/v2/security-agent/runs');
    const runs = data.runs || [];
    secHistoryTbody.replaceChildren();

    if (runs.length === 0) {
      const emptyRow = document.createElement('tr');
      const emptyTd = document.createElement('td');
      emptyTd.colSpan = 7;
      emptyTd.className = 'sec-empty-cell';
      emptyTd.textContent = 'No prior review runs found.';
      emptyRow.appendChild(emptyTd);
      secHistoryTbody.appendChild(emptyRow);
      fetchTrends();
      return;
    }

    runs.forEach(run => {
      const tr = document.createElement('tr');

      const stClass = run.state === 'COMPLETED' ? 'safe' : (run.state === 'FAILED' ? 'danger' : 'warning');
      const incCount = (run.incident_counts && run.incident_counts.total) ?? 0;
      const createdStr = run.created_at ? new Date(run.created_at).toLocaleString() : '—';
      const encodedId = encodeURIComponent(run.run_id);

      const td1 = document.createElement('td');
      const strongId = document.createElement('strong');
      strongId.className = 'badge-code';
      strongId.textContent = run.run_id || '';
      td1.appendChild(strongId);

      const td2 = document.createElement('td');
      td2.textContent = createdStr;

      const td3 = document.createElement('td');
      const spanPill = document.createElement('span');
      spanPill.className = `status-pill ${stClass}`;
      spanPill.textContent = run.state || 'UNKNOWN';
      td3.appendChild(spanPill);

      const td4 = document.createElement('td');
      const strongInc = document.createElement('strong');
      strongInc.textContent = String(incCount);
      td4.append(strongInc, ' incidents');

      const td5 = document.createElement('td');
      td5.textContent = `${run.collector_count ?? 7} collectors`;

      const td6 = document.createElement('td');
      td6.textContent = run.email_sent ? 'Sent' : 'Skipped';

      const td7 = document.createElement('td');
      td7.className = 'sec-download-cell';
      td7.style.whiteSpace = 'nowrap';

      const btnInspect = document.createElement('button');
      btnInspect.className = 'compact link-btn sec-btn-view-run';
      btnInspect.dataset.runId = run.run_id || '';
      btnInspect.title = 'Inspect Live Run';
      btnInspect.textContent = 'Inspect';

      const linkExec = document.createElement('a');
      linkExec.href = `/api/v2/security-agent/runs/${encodedId}/report?format=executive`;
      linkExec.target = '_blank';
      linkExec.className = 'compact link-btn';
      linkExec.title = 'Executive HTML Report';
      linkExec.textContent = 'Exec';

      const linkTech = document.createElement('a');
      linkTech.href = `/api/v2/security-agent/runs/${encodedId}/report?format=technical`;
      linkTech.target = '_blank';
      linkTech.className = 'compact link-btn';
      linkTech.title = 'Technical HTML Report';
      linkTech.textContent = 'Tech';

      const linkPdf = document.createElement('a');
      linkPdf.href = `/api/v2/security-agent/runs/${encodedId}/report?format=pdf`;
      linkPdf.target = '_blank';
      linkPdf.className = 'compact link-btn';
      linkPdf.title = 'Download PDF Report';
      linkPdf.textContent = 'PDF';

      const linkJson = document.createElement('a');
      linkJson.href = `/api/v2/security-agent/runs/${encodedId}/report?format=json`;
      linkJson.target = '_blank';
      linkJson.className = 'compact link-btn';
      linkJson.title = 'Download JSON Run Pack';
      linkJson.textContent = 'JSON';

      const linkCsv = document.createElement('a');
      linkCsv.href = `/api/v2/security-agent/runs/${encodedId}/report?format=csv`;
      linkCsv.target = '_blank';
      linkCsv.className = 'compact link-btn';
      linkCsv.title = 'Download CSV Incidents';
      linkCsv.textContent = 'CSV';

      td7.append(btnInspect, ' ', linkExec, ' ', linkTech, ' ', linkPdf, ' ', linkJson, ' ', linkCsv);
      tr.append(td1, td2, td3, td4, td5, td6, td7);

      secHistoryTbody.appendChild(tr);
    });

    fetchTrends();
  } catch (err) {
    secHistoryTbody.replaceChildren();
    const errRow = document.createElement('tr');
    const errTd = document.createElement('td');
    errTd.colSpan = 7;
    errTd.className = 'sec-empty-cell error';
    errTd.textContent = `Failed loading history: ${err.message}`;
    errRow.appendChild(errTd);
    secHistoryTbody.appendChild(errRow);
    fetchTrends();
  }
}

// --- Trends & Fleet Analytics Presentation ---

async function fetchTrends() {
  if (!secTrendsContainer) return;
  try {
    const data = await getJSON('/api/v2/security-agent/trends?days=7');
    const analytics = data.analytics || {};
    const daily = analytics.daily_breakdown || [];
    const devices = analytics.devices || {};
    const totalIncidents = analytics.total_incidents_in_window ?? 0;
    const runsAnalyzed = analytics.runs_analyzed ?? 0;

    const fragment = document.createDocumentFragment();

    const statsGrid = document.createElement('div');
    statsGrid.style.display = 'grid';
    statsGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(180px, 1fr))';
    statsGrid.style.gap = '10px';
    statsGrid.style.marginBottom = '12px';

    const p1 = document.createElement('div');
    p1.className = 'stat-pill';
    p1.style.padding = '8px';
    const strongWin = document.createElement('strong');
    strongWin.textContent = '7 Days';
    p1.append('Window: ', strongWin);

    const p2 = document.createElement('div');
    p2.className = 'stat-pill';
    p2.style.padding = '8px';
    const strongRuns = document.createElement('strong');
    strongRuns.textContent = String(runsAnalyzed);
    p2.append('Runs Analyzed: ', strongRuns);

    const p3 = document.createElement('div');
    p3.className = 'stat-pill';
    p3.style.padding = '8px';
    const strongIncs = document.createElement('strong');
    strongIncs.textContent = String(totalIncidents);
    p3.append('Total Incidents: ', strongIncs);

    const p4 = document.createElement('div');
    p4.className = 'stat-pill';
    p4.style.padding = '8px';
    const strongClean = document.createElement('strong');
    strongClean.textContent = String(analytics.clean_runs ?? 0);
    p4.append('Clean Runs: ', strongClean);

    statsGrid.append(p1, p2, p3, p4);
    fragment.appendChild(statsGrid);

    if (daily.length > 0) {
      const h5 = document.createElement('h5');
      h5.style.margin = '8px 0 4px 0';
      h5.style.fontSize = '0.85rem';
      h5.style.color = '#94a3b8';
      h5.textContent = 'Daily Threat Volume';
      fragment.appendChild(h5);

      const table = document.createElement('table');
      table.className = 'sec-data-table compact';
      table.style.marginBottom = '12px';
      table.style.fontSize = '0.8rem';

      const thead = document.createElement('thead');
      const headRow = document.createElement('tr');
      ['Date', 'Runs', 'Total Incidents', 'Critical', 'High', 'Medium', 'Low'].forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        headRow.appendChild(th);
      });
      thead.appendChild(headRow);
      table.appendChild(thead);

      const tbody = document.createElement('tbody');
      for (const d of daily) {
        const row = document.createElement('tr');

        const tdDate = document.createElement('td');
        const strongDate = document.createElement('strong');
        strongDate.textContent = d.date || '';
        tdDate.appendChild(strongDate);

        const tdRuns = document.createElement('td');
        tdRuns.textContent = String(d.runs_count ?? 0);

        const tdIncs = document.createElement('td');
        tdIncs.textContent = String(d.incidents_count ?? 0);

        const tdCrit = document.createElement('td');
        const critPill = document.createElement('span');
        critPill.className = `status-pill ${d.critical > 0 ? 'danger' : 'safe'}`;
        critPill.textContent = String(d.critical ?? 0);
        tdCrit.appendChild(critPill);

        const tdHigh = document.createElement('td');
        const highPill = document.createElement('span');
        highPill.className = `status-pill ${d.high > 0 ? 'warning' : 'safe'}`;
        highPill.textContent = String(d.high ?? 0);
        tdHigh.appendChild(highPill);

        const tdMed = document.createElement('td');
        tdMed.textContent = String(d.medium ?? 0);

        const tdLow = document.createElement('td');
        tdLow.textContent = String(d.low ?? 0);

        row.append(tdDate, tdRuns, tdIncs, tdCrit, tdHigh, tdMed, tdLow);
        tbody.appendChild(row);
      }
      table.appendChild(tbody);
      fragment.appendChild(table);
    }

    const deviceKeys = Object.keys(devices);
    if (deviceKeys.length > 0) {
      const h5dev = document.createElement('h5');
      h5dev.style.margin = '8px 0 4px 0';
      h5dev.style.fontSize = '0.85rem';
      h5dev.style.color = '#94a3b8';
      h5dev.textContent = 'Collector Reliability & Health';
      fragment.appendChild(h5dev);

      const devGrid = document.createElement('div');
      devGrid.style.display = 'grid';
      devGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(200px, 1fr))';
      devGrid.style.gap = '8px';

      for (const k of deviceKeys) {
        const dev = devices[k];
        const successRate = dev.success_rate !== undefined ? `${Math.round(dev.success_rate * 100)}%` : '—';
        const stClass = dev.last_status === 'SUCCESS' ? 'safe' : (dev.last_status === 'PARTIAL' ? 'warning' : 'danger');

        const devCard = document.createElement('div');
        devCard.style.background = '#0f172a';
        devCard.style.border = '1px solid #1e293b';
        devCard.style.borderRadius = '6px';
        devCard.style.padding = '8px';
        devCard.style.fontSize = '0.8rem';

        const topRow = document.createElement('div');
        topRow.style.display = 'flex';
        topRow.style.justifyContent = 'space-between';
        topRow.style.marginBottom = '4px';

        const strongDev = document.createElement('strong');
        strongDev.textContent = k;

        const pillDev = document.createElement('span');
        pillDev.className = `status-pill ${stClass}`;
        pillDev.style.fontSize = '0.7rem';
        pillDev.style.padding = '2px 6px';
        pillDev.textContent = dev.last_status || 'UNKNOWN';

        topRow.append(strongDev, pillDev);

        const rateRow = document.createElement('div');
        rateRow.style.color = '#64748b';
        const strongRate = document.createElement('strong');
        strongRate.style.color = '#e2e8f0';
        strongRate.textContent = successRate;
        rateRow.append('Success Rate: ', strongRate, ` (${dev.success_runs ?? 0}/${dev.total_runs ?? 0})`);

        const durRow = document.createElement('div');
        durRow.style.color = '#64748b';
        const strongDur = document.createElement('strong');
        strongDur.style.color = '#e2e8f0';
        strongDur.textContent = `${dev.avg_duration_sec ?? 0}s`;
        durRow.append('Avg Duration: ', strongDur);

        devCard.append(topRow, rateRow, durRow);
        devGrid.appendChild(devCard);
      }
      fragment.appendChild(devGrid);
    }

    secTrendsContainer.replaceChildren(fragment);
  } catch (err) {
    const errP = document.createElement('p');
    errP.className = 'sec-empty-cell error';
    errP.textContent = `Failed loading trends: ${err.message}`;
    secTrendsContainer.replaceChildren(errP);
  }
}

// --- Event Listeners Initialization ---

if (secOpenBtn && secDialog) {
  secOpenBtn.addEventListener('click', () => {
    secDialog.showModal();
    refreshSecurityStatus();

    // Check if there was an active run recorded
    if (activeRunId && !activeEventSource) {
      checkRunTerminalStatus(activeRunId);
    }
  });
}

// Tab: Preset Time Dropdown
if (secTimePresetSelect && secCustomTimeGroup) {
  secTimePresetSelect.addEventListener('change', () => {
    secCustomTimeGroup.hidden = secTimePresetSelect.value !== 'custom';
  });
}

// Tab: Select / Deselect All Collectors
if (secBtnSelectAllCollectors) {
  secBtnSelectAllCollectors.addEventListener('click', () => {
    document.querySelectorAll('input[name="sec-collector"]').forEach(cb => { cb.checked = true; });
  });
}

if (secBtnDeselectAllCollectors) {
  secBtnDeselectAllCollectors.addEventListener('click', () => {
    document.querySelectorAll('input[name="sec-collector"]').forEach(cb => { cb.checked = false; });
  });
}

// Start Review Button
if (secBtnStartReview) {
  secBtnStartReview.addEventListener('click', submitSecurityReview);
}

// Quick Overview Run Button (Switches to Run Review tab & starts)
if (secBtnRun) {
  secBtnRun.addEventListener('click', () => {
    switchTab('sec-panel-run');
    submitSecurityReview();
  });
}

// Cancel Run Button
if (secBtnCancelRun) {
  secBtnCancelRun.addEventListener('click', async () => {
    if (!activeRunId) return;
    secBtnCancelRun.disabled = true;
    try {
      await mutateJSON(`/api/v2/security-agent/runs/${encodeURIComponent(activeRunId)}/cancel`, {});
      appendConsoleLog('Cancel signal dispatched to server.');
    } catch (err) {
      alert(`Cancel request failed: ${err.message}`);
      secBtnCancelRun.disabled = false;
    }
  });
}

// Retry Failed Button
if (secBtnRetryFailed) {
  secBtnRetryFailed.addEventListener('click', async () => {
    if (!activeRunId) return;
    secBtnRetryFailed.disabled = true;
    try {
      const res = await mutateJSON(`/api/v2/security-agent/runs/${encodeURIComponent(activeRunId)}/retry`, {
        only_failed: true,
      });
      appendConsoleLog(`Starting retry run ${res.run_id} (retry of ${activeRunId})…`);
      connectEventStream(res.run_id);
    } catch (err) {
      alert(`Retry request failed: ${err.message}`);
    } finally {
      secBtnRetryFailed.disabled = false;
    }
  });
}

// Run Again Button
if (secBtnRunAgain) {
  secBtnRunAgain.addEventListener('click', submitSecurityReview);
}

// Open Results Button
if (secBtnOpenResults) {
  secBtnOpenResults.addEventListener('click', () => {
    window.open('/api/v2/security-agent/report/html', '_blank');
  });
}

// View HTML Button
if (secBtnViewHtml) {
  secBtnViewHtml.addEventListener('click', () => {
    window.open('/api/v2/security-agent/report/html', '_blank');
  });
}

// Download PDF Button
if (secBtnDownloadPdf) {
  secBtnDownloadPdf.addEventListener('click', () => {
    const link = document.createElement('a');
    link.href = '/api/v2/security-agent/report/pdf';
    link.download = 'MNE_Daily_Security_Report_latest.pdf';
    document.body.appendChild(link);
    link.click();
    link.remove();
  });
}

// Test Email Button
if (secBtnTestEmail) {
  secBtnTestEmail.addEventListener('click', async () => {
    secBtnTestEmail.disabled = true;
    const originalText = secBtnTestEmail.textContent;
    secBtnTestEmail.textContent = 'Sending…';
    try {
      const res = await mutateJSON('/api/v2/security-agent/test-email', {});
      alert(res.message || 'Test email dispatched successfully! Please check your inbox.');
    } catch (err) {
      alert(`Test email failed: ${err.message}`);
    } finally {
      secBtnTestEmail.disabled = false;
      secBtnTestEmail.textContent = originalText;
    }
  });
}

// Email Distribution Management
if (secBtnAddEmail && secNewEmailInput) {
  const addAction = () => {
    const email = (secNewEmailInput.value || '').trim().toLowerCase();
    if (!email) return;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setSecNotice(secRecipientsStatusEl, 'Please enter a valid email address.', true);
      return;
    }
    if (secLocalRecipients.includes(email)) {
      setSecNotice(secRecipientsStatusEl, 'Email is already in the list.', true);
      return;
    }
    secLocalRecipients.push(email);
    secNewEmailInput.value = '';
    renderSecRecipients();
    setSecNotice(secRecipientsStatusEl, 'Recipient added. Click "Save Distribution List" to commit.');
  };

  secBtnAddEmail.addEventListener('click', addAction);
  secNewEmailInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addAction();
    }
  });
}

if (secRecipientsListEl) {
  secRecipientsListEl.addEventListener('click', (e) => {
    const btn = e.target.closest('.chip-remove-btn');
    if (!btn) return;
    const index = parseInt(btn.dataset.index, 10);
    if (!isNaN(index) && index >= 0 && index < secLocalRecipients.length) {
      secLocalRecipients.splice(index, 1);
      renderSecRecipients();
      setSecNotice(secRecipientsStatusEl, 'Recipient removed. Click "Save Distribution List" to commit.');
    }
  });
}

if (secBtnSaveRecipients) {
  secBtnSaveRecipients.addEventListener('click', async () => {
    if (secLocalRecipients.length === 0) {
      setSecNotice(secRecipientsStatusEl, 'At least one recipient email is required.', true);
      return;
    }
    secBtnSaveRecipients.disabled = true;
    setSecNotice(secRecipientsStatusEl, 'Saving recipients…');
    try {
      await mutateJSON('/api/v2/security-agent/config', { recipients: secLocalRecipients });
      setSecNotice(secRecipientsStatusEl, 'Distribution list saved successfully!');
      refreshSecurityStatus();
    } catch (err) {
      setSecNotice(secRecipientsStatusEl, `Save failed: ${err.message}`, true);
    } finally {
      secBtnSaveRecipients.disabled = false;
    }
  });
}

// Schedule Automation Form
if (secScheduleForm) {
  secScheduleForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const schedule_time = secScheduleTimeInput ? secScheduleTimeInput.value : '07:00';
    const schedule_enabled = secScheduleEnabledInput ? secScheduleEnabledInput.checked : true;
    const saveBtn = document.querySelector('#sec-btn-save-schedule');

    if (saveBtn) saveBtn.disabled = true;
    setSecNotice(secScheduleStatusEl, 'Syncing schedule with Task Scheduler…');
    try {
      await mutateJSON('/api/v2/security-agent/config', {
        schedule_time,
        schedule_enabled,
      });
      setSecNotice(secScheduleStatusEl, 'Schedule & Windows Task synchronized successfully!');
      refreshSecurityStatus();
    } catch (err) {
      setSecNotice(secScheduleStatusEl, `Sync failed: ${err.message}`, true);
    } finally {
      if (saveBtn) saveBtn.disabled = false;
    }
  });
}

// History Refresh
if (secHistoryRefreshBtn) {
  secHistoryRefreshBtn.addEventListener('click', fetchHistory);
}

// History row action
if (secHistoryTbody) {
  secHistoryTbody.addEventListener('click', (e) => {
    const btn = e.target.closest('.sec-btn-view-run');
    if (!btn) return;
    const runId = btn.dataset.runId;
    if (runId) {
      switchTab('sec-panel-run');
      connectEventStream(runId);
    }
  });
}

// --- Incidents Presentation & Drill-Down ---

async function fetchIncidents() {
  if (!secIncidentsTbody) return;
  secIncidentsTbody.replaceChildren();
  const loadingRow = document.createElement('tr');
  const loadingTd = document.createElement('td');
  loadingTd.colSpan = 7;
  loadingTd.className = 'sec-empty-cell';
  loadingTd.textContent = 'Loading detected incidents…';
  loadingRow.appendChild(loadingTd);
  secIncidentsTbody.appendChild(loadingRow);

  const search = secIncidentsSearch ? secIncidentsSearch.value.trim() : '';
  const severity = secIncidentsFilterSev ? secIncidentsFilterSev.value : 'ALL';
  const status = secIncidentsFilterStatus ? secIncidentsFilterStatus.value : 'ALL';

  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (severity && severity !== 'ALL') params.set('severity', severity);
  if (status && status !== 'ALL') params.set('status', status);

  try {
    const url = `/api/v2/security-agent/incidents?${params.toString()}`;
    const data = await getJSON(url);
    const incidents = data.incidents || [];
    secIncidentsTbody.replaceChildren();

    if (incidents.length === 0) {
      const emptyRow = document.createElement('tr');
      const emptyTd = document.createElement('td');
      emptyTd.colSpan = 7;
      emptyTd.className = 'sec-empty-cell';
      emptyTd.textContent = 'No incidents match the active filters.';
      emptyRow.appendChild(emptyTd);
      secIncidentsTbody.appendChild(emptyRow);
      return;
    }

    incidents.forEach(inc => {
      const tr = document.createElement('tr');

      const sev = inc.current_severity || 'MEDIUM';
      const sevClass = sev === 'CRITICAL' ? 'danger' : (sev === 'HIGH' ? 'warning' : (sev === 'MEDIUM' ? 'safe' : 'subtle'));
      const st = inc.lifecycle_state || 'NEW';
      const stClass = st === 'RESOLVED' ? 'safe' : (st === 'REOPENED' ? 'danger' : (st === 'RECURRING' ? 'warning' : 'info'));

      const dispId = inc.display_id || inc.incident_id || '—';
      const fp = inc.fingerprint || '';
      const attacker = inc.attacker_identity || inc.attacker_ip || 'Internal';
      const target = inc.target_identity || inc.target || 'Perimeter';
      const sourceDev = inc.source_device || 'Perimeter';
      const evCount = inc.event_count || 1;
      const occCount = inc.occurrence_count || 1;

      const tdSev = document.createElement('td');
      const sevSpan = document.createElement('span');
      sevSpan.className = `status-pill ${sevClass}`;
      sevSpan.textContent = sev;
      tdSev.appendChild(sevSpan);

      const tdId = document.createElement('td');
      const strongDisp = document.createElement('strong');
      strongDisp.textContent = dispId;
      const fpSpan = document.createElement('span');
      fpSpan.className = 'badge-code';
      fpSpan.textContent = fp;
      tdId.append(strongDisp, document.createElement('br'), fpSpan);

      const tdTitle = document.createElement('td');
      const strongTitle = document.createElement('strong');
      strongTitle.textContent = inc.title || 'Security Incident';
      const catSpan = document.createElement('span');
      catSpan.className = 'badge-subtle';
      catSpan.textContent = `${inc.category || 'THREAT'} · ${inc.signature_family || 'generic'}`;
      tdTitle.append(strongTitle, document.createElement('br'), catSpan);

      const tdSrc = document.createElement('td');
      tdSrc.textContent = sourceDev;

      const tdFlow = document.createElement('td');
      const atkSpan = document.createElement('span');
      atkSpan.className = 'badge-code';
      atkSpan.textContent = attacker;
      const tgtSpan = document.createElement('span');
      tgtSpan.textContent = target;
      tdFlow.append(atkSpan, ' ➔ ', tgtSpan);

      const pc = inc.attacker_pc_name;
      const user = inc.attacker_username;
      const hasPc = pc && pc !== 'Unknown' && pc !== 'Not applicable';
      const hasUser = user && user !== 'Unknown' && user !== 'Not applicable';
      if (hasPc || hasUser) {
        const idSpan = document.createElement('span');
        idSpan.className = 'badge-subtle';
        idSpan.style.display = 'block';
        idSpan.style.fontSize = '11px';
        idSpan.style.color = '#38bdf8';
        const parts = [];
        if (hasPc) parts.push(`💻 ${pc}`);
        if (hasUser) parts.push(`👤 ${user}`);
        idSpan.textContent = parts.join(' · ');
        tdFlow.appendChild(idSpan);
      }

      const tdStatus = document.createElement('td');
      const strongEv = document.createElement('strong');
      strongEv.textContent = String(evCount);
      const stSpan = document.createElement('span');
      stSpan.className = `status-pill ${stClass}`;
      stSpan.textContent = `${st} (${occCount}x)`;
      tdStatus.append(strongEv, ' events', document.createElement('br'), stSpan);

      const tdAct = document.createElement('td');
      tdAct.className = 'sec-download-cell';
      const inspectBtn = document.createElement('button');
      inspectBtn.className = 'compact link-btn sec-btn-inspect-incident';
      inspectBtn.dataset.fingerprint = fp;
      inspectBtn.textContent = 'Inspect';
      tdAct.appendChild(inspectBtn);

      tr.append(tdSev, tdId, tdTitle, tdSrc, tdFlow, tdStatus, tdAct);

      secIncidentsTbody.appendChild(tr);
    });
  } catch (err) {
    secIncidentsTbody.replaceChildren();
    const errRow = document.createElement('tr');
    const errTd = document.createElement('td');
    errTd.colSpan = 7;
    errTd.className = 'sec-empty-cell error';
    errTd.textContent = `Failed loading incidents: ${err.message}`;
    errRow.appendChild(errTd);
    secIncidentsTbody.appendChild(errRow);
  }
}

async function openIncidentDetail(fingerprint) {
  if (!secIncidentDetailDialog || !fingerprint) return;
  activeIncidentFingerprint = fingerprint;

  if (secDetailTitle) secDetailTitle.textContent = 'Loading Incident…';
  if (secDetailFingerprint) secDetailFingerprint.textContent = fingerprint;
  if (secDetailStatusMsg) secDetailStatusMsg.textContent = '';
  if (secDetailNotesList) secDetailNotesList.replaceChildren();
  if (secDetailTimelineList) secDetailTimelineList.replaceChildren();
  if (secIncidentTroubleshootContainer) {
    secIncidentTroubleshootContainer.style.display = 'none';
    secIncidentTroubleshootContainer.replaceChildren();
  }

  secIncidentDetailDialog.showModal();

  try {
    const inc = await getJSON(`/api/v2/security-agent/incidents/${encodeURIComponent(fingerprint)}`);

    if (secDetailTitle) secDetailTitle.textContent = inc.title || 'Security Incident';
    if (secDetailSubtitle) secDetailSubtitle.textContent = `${inc.category || 'THREAT'} · ${inc.signature_family || 'generic'}`;

    const sev = inc.current_severity || 'MEDIUM';
    if (secDetailSeverityPill) {
      secDetailSeverityPill.textContent = sev;
      secDetailSeverityPill.className = 'status-pill ' + (sev === 'CRITICAL' ? 'danger' : (sev === 'HIGH' ? 'warning' : 'safe'));
    }

    const st = inc.lifecycle_state || 'NEW';
    if (secDetailLifecyclePill) {
      secDetailLifecyclePill.textContent = st;
      secDetailLifecyclePill.className = 'status-pill ' + (st === 'RESOLVED' ? 'safe' : (st === 'REOPENED' ? 'danger' : (st === 'RECURRING' ? 'warning' : 'info')));
    }

    if (secDetailFingerprint) secDetailFingerprint.textContent = inc.fingerprint || '—';
    if (secDetailDisplayId) secDetailDisplayId.textContent = inc.display_id || inc.incident_id || '—';
    if (secDetailFirstSeen) secDetailFirstSeen.textContent = inc.first_seen ? new Date(inc.first_seen).toLocaleString() : '—';
    if (secDetailLastSeen) secDetailLastSeen.textContent = inc.last_seen ? new Date(inc.last_seen).toLocaleString() : '—';
    if (secDetailOccurrences) secDetailOccurrences.textContent = inc.occurrence_count || 1;
    if (secDetailEvents) secDetailEvents.textContent = inc.event_count || 1;

    if (secDetailRationale) secDetailRationale.textContent = inc.severity_rationale || 'Determined by standard SOC rules.';
    if (secDetailAttacker) secDetailAttacker.textContent = inc.attacker_identity || inc.attacker_ip || 'None / Internal';
    if (secDetailTargets) secDetailTargets.textContent = inc.target_identity || inc.target || 'Perimeter';
    if (secDetailDevices) secDetailDevices.textContent = inc.source_device || '—';
    if (secDetailBranches) secDetailBranches.textContent = inc.branch || 'Core Perimeter';

    if (secDetailPcName) {
      secDetailPcName.textContent = inc.attacker_pc_name || '—';
      if (inc.attacker_fqdn && inc.attacker_fqdn !== inc.attacker_pc_name) {
        secDetailPcName.textContent += ` (${inc.attacker_fqdn})`;
      }
    }
    if (secDetailUsername) secDetailUsername.textContent = inc.attacker_username || '—';
    if (secDetailDeviceOwner) secDetailDeviceOwner.textContent = inc.attacker_device_owner || '—';
    if (secDetailMac) secDetailMac.textContent = inc.attacker_mac_address || '—';
    if (secDetailScope) {
      const scope = inc.attacker_network_scope || 'UNKNOWN';
      secDetailScope.textContent = scope;
      secDetailScope.className = 'badge-subtle ' + (scope === 'LOCAL' ? 'safe' : (scope === 'EXTERNAL' ? 'info' : 'muted'));
    }
    if (secDetailIdStatus) {
      const idSt = inc.attacker_identity_status || 'UNKNOWN';
      secDetailIdStatus.textContent = idSt;
      secDetailIdStatus.className = 'status-pill ' + (idSt === 'RESOLVED' ? 'safe' : (idSt === 'PARTIAL' ? 'warning' : (idSt === 'AMBIGUOUS' ? 'danger' : 'subtle')));
    }
    if (secDetailConfidence) {
      const conf = inc.attacker_identity_confidence || '';
      const score = inc.attacker_identity_confidence_score;
      secDetailConfidence.textContent = conf && conf !== 'UNKNOWN' ? `(${conf}${score ? ` · ${score}%` : ''})` : '';
    }
    if (secDetailIdSources) {
      const srcs = inc.attacker_identity_sources || [];
      secDetailIdSources.textContent = srcs.length ? srcs.join(', ') : 'None';
    }
    if (secDetailIdObserved) {
      secDetailIdObserved.textContent = inc.attacker_identity_observed_at ? new Date(inc.attacker_identity_observed_at).toLocaleString() : '—';
    }
    if (secDetailIdDiagnosticsContainer && secDetailIdDiagnostics) {
      const diags = inc.attacker_identity_diagnostics || [];
      if (diags.length > 0) {
        secDetailIdDiagnostics.textContent = diags.join('; ');
        secDetailIdDiagnosticsContainer.style.display = 'block';
      } else {
        secDetailIdDiagnosticsContainer.style.display = 'none';
      }
    }

    if (secDetailAction) secDetailAction.textContent = inc.action_taken || 'UNKNOWN';
    if (secDetailBlocked) secDetailBlocked.textContent = inc.blocked_count ?? '—';
    if (secDetailAllowed) secDetailAllowed.textContent = inc.allowed_count ?? '—';

    if (secDetailStatusSelect) secDetailStatusSelect.value = inc.lifecycle_state || 'NEW';
    if (secDetailStatusNote) secDetailStatusNote.value = '';

    // Render Analyst Notes
    if (secDetailNotesList) {
      secDetailNotesList.replaceChildren();
      const notes = inc.analyst_notes || [];
      if (notes.length === 0) {
        const emptyNote = document.createElement('span');
        emptyNote.className = 'sec-empty-hint';
        emptyNote.textContent = 'No analyst notes recorded yet.';
        secDetailNotesList.appendChild(emptyNote);
      } else {
        notes.forEach(n => {
          const noteDiv = document.createElement('div');
          noteDiv.className = 'sec-note-item';
          const timeStr = n.timestamp ? new Date(n.timestamp).toLocaleString() : '';

          const metaDiv = document.createElement('div');
          metaDiv.className = 'sec-note-meta';
          const authStrong = document.createElement('strong');
          authStrong.textContent = n.author || 'analyst';
          const timeSpan = document.createElement('span');
          timeSpan.textContent = timeStr;
          metaDiv.append(authStrong, timeSpan);

          const bodyDiv = document.createElement('div');
          bodyDiv.className = 'sec-note-body';
          bodyDiv.textContent = n.note || '';

          noteDiv.append(metaDiv, bodyDiv);
          secDetailNotesList.appendChild(noteDiv);
        });
      }
    }

    // Render Playbook
    if (secDetailPlaybookCli) {
      const cliCmds = inc.remediation_cli || [];
      secDetailPlaybookCli.textContent = cliCmds.length ? cliCmds.join('\n') : 'No automated CLI commands available.';
    }
    if (secDetailPlaybookGui) {
      const guiSteps = inc.remediation_gui || [];
      secDetailPlaybookGui.textContent = guiSteps.length ? guiSteps.join('\n') : 'No manual GUI procedure documented.';
    }

    // Fetch Timeline
    fetchIncidentTimeline(fingerprint);

  } catch (err) {
    if (secDetailTitle) secDetailTitle.textContent = 'Error Loading Incident';
    setSecNotice(secDetailStatusMsg, `Failed loading incident details: ${err.message}`, true);
  }
}

async function fetchIncidentTimeline(fingerprint) {
  if (!secDetailTimelineList) return;
  secDetailTimelineList.replaceChildren();
  const loading = document.createElement('span');
  loading.className = 'sec-empty-hint';
  loading.textContent = 'Loading timeline…';
  secDetailTimelineList.appendChild(loading);

  try {
    const data = await getJSON(`/api/v2/security-agent/incidents/${encodeURIComponent(fingerprint)}/timeline`);
    const timeline = data.timeline || [];
    secDetailTimelineList.replaceChildren();

    if (timeline.length === 0) {
      const empty = document.createElement('span');
      empty.className = 'sec-empty-hint';
      empty.textContent = 'No timeline events recorded.';
      secDetailTimelineList.appendChild(empty);
      return;
    }

    timeline.forEach(item => {
      const itemDiv = document.createElement('div');
      itemDiv.className = 'sec-timeline-item';
      const timeStr = item.timestamp ? new Date(item.timestamp).toLocaleString() : '';
      const badgeClass = item.type === 'STATUS_CHANGE' ? 'status-pill warning' : (item.type === 'FIRST_SEEN' ? 'status-pill safe' : 'status-pill info');

      const badgeSpan = document.createElement('span');
      badgeSpan.className = `${badgeClass} sec-timeline-badge`;
      badgeSpan.textContent = item.type || 'EVENT';

      const contentDiv = document.createElement('div');
      contentDiv.className = 'sec-timeline-content';

      const headerDiv = document.createElement('div');
      headerDiv.className = 'sec-timeline-header';
      const strongTitle = document.createElement('strong');
      strongTitle.textContent = item.title || 'Event';
      const spanTime = document.createElement('span');
      spanTime.textContent = timeStr;
      headerDiv.append(strongTitle, spanTime);

      const descDiv = document.createElement('div');
      descDiv.className = 'sec-timeline-desc';
      descDiv.textContent = item.description || '';

      contentDiv.append(headerDiv, descDiv);
      itemDiv.append(badgeSpan, contentDiv);
      secDetailTimelineList.appendChild(itemDiv);
    });
  } catch (err) {
    secDetailTimelineList.replaceChildren();
    const errSpan = document.createElement('span');
    errSpan.className = 'sec-empty-hint error';
    errSpan.textContent = `Timeline unavailable: ${err.message}`;
    secDetailTimelineList.appendChild(errSpan);
  }
}

async function handleUpdateIncidentStatus() {
  if (!activeIncidentFingerprint || !secDetailStatusSelect) return;
  const newStatus = secDetailStatusSelect.value;
  const note = secDetailStatusNote ? secDetailStatusNote.value.trim() : '';

  if (secDetailUpdateStatusBtn) secDetailUpdateStatusBtn.disabled = true;
  try {
    await mutateJSON(`/api/v2/security-agent/incidents/${encodeURIComponent(activeIncidentFingerprint)}/status`, {
      status: newStatus,
      note,
      author: 'operator',
    });
    setSecNotice(secDetailStatusMsg, 'Status updated successfully!');
    if (secDetailStatusNote) secDetailStatusNote.value = '';
    openIncidentDetail(activeIncidentFingerprint);
    fetchIncidents();
  } catch (err) {
    setSecNotice(secDetailStatusMsg, `Update failed: ${err.message}`, true);
  } finally {
    if (secDetailUpdateStatusBtn) secDetailUpdateStatusBtn.disabled = false;
  }
}

async function handleAddIncidentNote() {
  if (!activeIncidentFingerprint || !secDetailNewNoteInput) return;
  const note = secDetailNewNoteInput.value.trim();
  if (!note) return;

  if (secDetailAddNoteBtn) secDetailAddNoteBtn.disabled = true;
  try {
    await mutateJSON(`/api/v2/security-agent/incidents/${encodeURIComponent(activeIncidentFingerprint)}/notes`, {
      note,
      author: 'operator',
    });
    secDetailNewNoteInput.value = '';
    openIncidentDetail(activeIncidentFingerprint);
  } catch (err) {
    alert(`Failed adding note: ${err.message}`);
  } finally {
    if (secDetailAddNoteBtn) secDetailAddNoteBtn.disabled = false;
  }
}

async function handleResolveIncidentIdentity() {
  if (!activeIncidentFingerprint) return;
  if (secDetailBtnResolveIdentity) {
    secDetailBtnResolveIdentity.disabled = true;
    secDetailBtnResolveIdentity.textContent = 'Resolving…';
  }
  try {
    await mutateJSON(`/api/v2/security-agent/incidents/${encodeURIComponent(activeIncidentFingerprint)}/resolve-identity`, {});
    await openIncidentDetail(activeIncidentFingerprint);
    fetchIncidents();
  } catch (err) {
    alert(`Failed resolving identity: ${err.message}`);
  } finally {
    if (secDetailBtnResolveIdentity) {
      secDetailBtnResolveIdentity.disabled = false;
      secDetailBtnResolveIdentity.textContent = '🔍 Resolve Identity';
    }
  }
}

if (secDetailBtnResolveIdentity) {
  secDetailBtnResolveIdentity.addEventListener('click', handleResolveIncidentIdentity);
}

// Incidents Tab Filter Listeners
if (secIncidentsSearch) {
  let searchTimer = null;
  secIncidentsSearch.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(fetchIncidents, 300);
  });
}

if (secIncidentsFilterSev) {
  secIncidentsFilterSev.addEventListener('change', fetchIncidents);
}

if (secIncidentsFilterStatus) {
  secIncidentsFilterStatus.addEventListener('change', fetchIncidents);
}

// Incidents Table Action Listeners
if (secIncidentsTbody) {
  secIncidentsTbody.addEventListener('click', (e) => {
    const btn = e.target.closest('.sec-btn-inspect-incident');
    if (!btn) return;
    const fp = btn.dataset.fingerprint;
    if (fp) openIncidentDetail(fp);
  });
}

// Detail Modal Actions
if (secDetailCloseBtn && secIncidentDetailDialog) {
  secDetailCloseBtn.addEventListener('click', () => {
    secIncidentDetailDialog.close();
  });
}

if (secDetailUpdateStatusBtn) {
  secDetailUpdateStatusBtn.addEventListener('click', handleUpdateIncidentStatus);
}

if (secDetailAddNoteBtn) {
  secDetailAddNoteBtn.addEventListener('click', handleAddIncidentNote);
}

if (secDetailNewNoteInput) {
  secDetailNewNoteInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddIncidentNote();
    }
  });
}

// --- AI Analysis Investigation Handlers ---

function renderSingleAnalysisCard(res, titleLabel = '') {
  if (!res) {
    const empty = document.createElement('div');
    empty.className = 'sec-empty-hint';
    empty.textContent = 'No analysis result available.';
    return empty;
  }

  const engine = (res.engine || titleLabel || 'AI Engine').toUpperCase();
  const provider = res.provider || 'AI Provider';
  const model = res.model || 'default';
  const status = res.status || 'COMPLETED';
  const confidence = typeof res.confidence === 'number' ? Math.round(res.confidence * 100) : 75;

  const card = document.createElement('div');
  card.className = 'sec-analysis-card';

  // Header
  const header = document.createElement('div');
  header.className = 'sec-analysis-card-header';

  const titleDiv = document.createElement('div');
  const h4 = document.createElement('h4');
  h4.textContent = `🤖 ${engine} Assessment`;
  const sub = document.createElement('span');
  sub.className = 'sec-card-subtitle';
  sub.textContent = `${provider} • ${model}`;
  titleDiv.append(h4, sub);

  const badgesDiv = document.createElement('div');
  badgesDiv.className = 'sec-analysis-badges';
  const stBadge = document.createElement('span');
  stBadge.className = `badge-code status-${status.toLowerCase()}`;
  stBadge.textContent = status;
  const confBadge = document.createElement('span');
  confBadge.className = 'badge-code';
  confBadge.textContent = `Confidence: ${confidence}%`;
  badgesDiv.append(stBadge, confBadge);

  if (res.analysis_id) {
    const encId = encodeURIComponent(res.analysis_id);
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'sec-analysis-actions';

    const htmlBtn = document.createElement('a');
    htmlBtn.className = 'sec-export-btn';
    htmlBtn.href = `/api/v2/security-agent/analyses/${encId}/report?format=html`;
    htmlBtn.target = '_blank';
    htmlBtn.rel = 'noopener noreferrer';
    htmlBtn.title = 'View publication-grade HTML report';
    htmlBtn.textContent = '📄 Export HTML';

    const pdfBtn = document.createElement('a');
    pdfBtn.className = 'sec-export-btn';
    pdfBtn.href = `/api/v2/security-agent/analyses/${encId}/report?format=pdf`;
    pdfBtn.target = '_blank';
    pdfBtn.rel = 'noopener noreferrer';
    pdfBtn.title = 'Download forensic PDF report';
    pdfBtn.textContent = '📥 Export PDF';

    actionsDiv.append(htmlBtn, pdfBtn);
    badgesDiv.appendChild(actionsDiv);
  }

  header.append(titleDiv, badgesDiv);
  card.appendChild(header);

  // Summary box
  const summaryBox = document.createElement('div');
  summaryBox.className = 'sec-analysis-summary-box';
  const pSummary = document.createElement('p');
  pSummary.textContent = res.plain_summary || 'No summary provided.';
  summaryBox.appendChild(pSummary);
  card.appendChild(summaryBox);

  // Ranked Hypotheses
  if (Array.isArray(res.ranked_hypotheses) && res.ranked_hypotheses.length > 0) {
    const sec = document.createElement('div');
    sec.className = 'sec-analysis-section';
    const h5 = document.createElement('h5');
    h5.textContent = 'Ranked Root-Cause Hypotheses';
    sec.appendChild(h5);

    const ul = document.createElement('ul');
    ul.className = 'sec-hypo-list';
    for (const h of res.ranked_hypotheses) {
      const li = document.createElement('li');
      li.className = 'sec-hypo-item';

      const like = h.likelihood || 'UNKNOWN';
      const pill = document.createElement('span');
      pill.className = `sec-pill sec-pill-${like.toLowerCase()}`;
      pill.textContent = like;

      const content = document.createElement('div');
      content.className = 'sec-hypo-content';
      const strong = document.createElement('strong');
      strong.textContent = h.hypothesis || '';
      content.appendChild(strong);

      if (h.explanation) {
        const exp = document.createElement('p');
        exp.className = 'sec-hypo-exp';
        exp.textContent = h.explanation;
        content.appendChild(exp);
      }

      li.append(pill, content);
      ul.appendChild(li);
    }
    sec.appendChild(ul);
    card.appendChild(sec);
  }

  // Evidence Corroboration
  const obs = res.observations || {};
  const supporting = Array.isArray(obs.supporting) ? obs.supporting : [];
  const contradicting = Array.isArray(obs.contradicting) ? obs.contradicting : [];
  if (supporting.length > 0 || contradicting.length > 0) {
    const sec = document.createElement('div');
    sec.className = 'sec-analysis-section';
    const h5 = document.createElement('h5');
    h5.textContent = 'Evidence Corroboration';
    sec.appendChild(h5);

    if (supporting.length > 0) {
      const subhead = document.createElement('p');
      subhead.className = 'sec-subhead';
      subhead.textContent = '✅ Supporting Facts:';
      sec.appendChild(subhead);

      const ul = document.createElement('ul');
      ul.className = 'sec-bullet-list';
      for (const s of supporting) {
        const li = document.createElement('li');
        li.textContent = s;
        ul.appendChild(li);
      }
      sec.appendChild(ul);
    }

    if (contradicting.length > 0) {
      const subhead = document.createElement('p');
      subhead.className = 'sec-subhead';
      subhead.textContent = '❌ Contradicting / Excluded Factors:';
      sec.appendChild(subhead);

      const ul = document.createElement('ul');
      ul.className = 'sec-bullet-list';
      for (const c of contradicting) {
        const li = document.createElement('li');
        li.textContent = c;
        ul.appendChild(li);
      }
      sec.appendChild(ul);
    }

    card.appendChild(sec);
  }

  // Recommended Next Verification Checks
  if (Array.isArray(res.recommended_diagnostics) && res.recommended_diagnostics.length > 0) {
    const sec = document.createElement('div');
    sec.className = 'sec-analysis-section';
    const h5 = document.createElement('h5');
    h5.textContent = 'Recommended Next Verification Checks';
    sec.appendChild(h5);

    const ul = document.createElement('ul');
    ul.className = 'sec-code-list';
    for (const d of res.recommended_diagnostics) {
      const li = document.createElement('li');
      const code = document.createElement('code');
      code.textContent = d;
      li.appendChild(code);
      ul.appendChild(li);
    }
    sec.appendChild(ul);
    card.appendChild(sec);
  }

  // Recommended Remediation Actions
  const imm = Array.isArray(res.immediate_actions) ? res.immediate_actions : [];
  const lt = Array.isArray(res.long_term_actions) ? res.long_term_actions : [];
  if (imm.length > 0 || lt.length > 0) {
    const sec = document.createElement('div');
    sec.className = 'sec-analysis-section';
    const h5 = document.createElement('h5');
    h5.textContent = 'Recommended Remediation Actions';
    sec.appendChild(h5);

    if (imm.length > 0) {
      const subhead = document.createElement('p');
      subhead.className = 'sec-subhead';
      subhead.textContent = '⚡ Immediate Containment:';
      sec.appendChild(subhead);

      const ul = document.createElement('ul');
      ul.className = 'sec-bullet-list';
      for (const a of imm) {
        const li = document.createElement('li');
        li.textContent = a;
        ul.appendChild(li);
      }
      sec.appendChild(ul);
    }

    if (lt.length > 0) {
      const subhead = document.createElement('p');
      subhead.className = 'sec-subhead';
      subhead.textContent = '🛡️ Long-Term Hardening:';
      sec.appendChild(subhead);

      const ul = document.createElement('ul');
      ul.className = 'sec-bullet-list';
      for (const l of lt) {
        const li = document.createElement('li');
        li.textContent = l;
        ul.appendChild(li);
      }
      sec.appendChild(ul);
    }

    card.appendChild(sec);
  }

  // Ground-Truth Sources Cited
  if (Array.isArray(res.source_references) && res.source_references.length > 0) {
    const sec = document.createElement('div');
    sec.className = 'sec-analysis-section';
    const h5 = document.createElement('h5');
    h5.textContent = 'Ground-Truth Sources Cited';
    sec.appendChild(h5);

    const ul = document.createElement('ul');
    ul.className = 'sec-sources-list';
    for (const s of res.source_references) {
      const li = document.createElement('li');
      const badge = document.createElement('span');
      badge.className = 'badge-code';
      badge.textContent = s;
      li.appendChild(badge);
      ul.appendChild(li);
    }
    sec.appendChild(ul);
    card.appendChild(sec);
  }

  return card;
}

function renderComparisonCard(cmp) {
  if (!cmp) {
    return document.createDocumentFragment();
  }

  const card = document.createElement('div');
  card.className = 'sec-analysis-card sec-comparison-card';

  const header = document.createElement('div');
  header.className = 'sec-analysis-card-header';
  const titleDiv = document.createElement('div');
  const h4 = document.createElement('h4');
  h4.textContent = '🔬 Multi-Engine Comparison (Codex vs Antigravity)';
  const sub = document.createElement('span');
  sub.className = 'sec-card-subtitle';
  sub.textContent = `Comparison ID: ${cmp.comparison_id || ''}`;
  titleDiv.append(h4, sub);
  header.appendChild(titleDiv);
  card.appendChild(header);

  // Common Conclusions
  if (Array.isArray(cmp.common_conclusions) && cmp.common_conclusions.length > 0) {
    const sec = document.createElement('div');
    sec.className = 'sec-analysis-section';
    const h5 = document.createElement('h5');
    h5.textContent = '🤝 Common Conclusions (Consensus)';
    sec.appendChild(h5);

    const ul = document.createElement('ul');
    ul.className = 'sec-bullet-list';
    for (const c of cmp.common_conclusions) {
      const li = document.createElement('li');
      const strong = document.createElement('strong');
      strong.textContent = c;
      li.appendChild(strong);
      ul.appendChild(li);
    }
    sec.appendChild(ul);
    card.appendChild(sec);
  }

  // Conflicting Conclusions
  if (Array.isArray(cmp.conflicting_conclusions) && cmp.conflicting_conclusions.length > 0) {
    const sec = document.createElement('div');
    sec.className = 'sec-analysis-section sec-conflict-section';
    const h5 = document.createElement('h5');
    h5.textContent = '⚠️ Conflicting Assessments (Divergence)';
    sec.appendChild(h5);

    for (const cf of cmp.conflicting_conclusions) {
      const box = document.createElement('div');
      box.className = 'sec-conflict-box';

      const pTopic = document.createElement('p');
      pTopic.className = 'sec-conflict-topic';
      const strongTopic = document.createElement('strong');
      strongTopic.textContent = 'Topic: ';
      pTopic.append(strongTopic, cf.topic || '');

      const pCodex = document.createElement('p');
      const strongCodex = document.createElement('strong');
      strongCodex.textContent = 'Codex: ';
      pCodex.append(strongCodex, cf.codex_assessment || '');

      const pAgy = document.createElement('p');
      const strongAgy = document.createElement('strong');
      strongAgy.textContent = 'Antigravity: ';
      pAgy.append(strongAgy, cf.antigravity_assessment || '');

      const pReason = document.createElement('p');
      pReason.className = 'sec-conflict-reason';
      const em = document.createElement('em');
      em.textContent = cf.conflict_reason || '';
      pReason.appendChild(em);

      box.append(pTopic, pCodex, pAgy, pReason);
      sec.appendChild(box);
    }
    card.appendChild(sec);
  }

  // Engine-Specific Observations
  const codexOnly = Array.isArray(cmp.codex_only_conclusions) ? cmp.codex_only_conclusions : [];
  const agyOnly = Array.isArray(cmp.antigravity_only_conclusions) ? cmp.antigravity_only_conclusions : [];
  if (codexOnly.length > 0 || agyOnly.length > 0) {
    const sec = document.createElement('div');
    sec.className = 'sec-analysis-section';
    const h5 = document.createElement('h5');
    h5.textContent = 'Engine-Specific Observations';
    sec.appendChild(h5);

    if (codexOnly.length > 0) {
      const p = document.createElement('p');
      p.className = 'sec-subhead';
      p.textContent = 'Codex-Only Points:';
      sec.appendChild(p);

      const ul = document.createElement('ul');
      ul.className = 'sec-bullet-list';
      for (const co of codexOnly) {
        const li = document.createElement('li');
        li.textContent = co;
        ul.appendChild(li);
      }
      sec.appendChild(ul);
    }

    if (agyOnly.length > 0) {
      const p = document.createElement('p');
      p.className = 'sec-subhead';
      p.textContent = 'Antigravity-Only Points:';
      sec.appendChild(p);

      const ul = document.createElement('ul');
      ul.className = 'sec-bullet-list';
      for (const ao of agyOnly) {
        const li = document.createElement('li');
        li.textContent = ao;
        ul.appendChild(li);
      }
      sec.appendChild(ul);
    }

    card.appendChild(sec);
  }

  // Jointly Recommended Diagnostics
  if (Array.isArray(cmp.shared_diagnostics) && cmp.shared_diagnostics.length > 0) {
    const sec = document.createElement('div');
    sec.className = 'sec-analysis-section';
    const h5 = document.createElement('h5');
    h5.textContent = '🔬 Jointly Recommended Diagnostics';
    sec.appendChild(h5);

    const ul = document.createElement('ul');
    ul.className = 'sec-code-list';
    for (const sd of cmp.shared_diagnostics) {
      const li = document.createElement('li');
      const code = document.createElement('code');
      code.textContent = sd;
      li.appendChild(code);
      ul.appendChild(li);
    }
    sec.appendChild(ul);
    card.appendChild(sec);
  }

  // Unresolved Questions
  if (Array.isArray(cmp.unresolved_questions) && cmp.unresolved_questions.length > 0) {
    const sec = document.createElement('div');
    sec.className = 'sec-analysis-section';
    const h5 = document.createElement('h5');
    h5.textContent = '❓ Unresolved Questions & Missing Evidence';
    sec.appendChild(h5);

    const ul = document.createElement('ul');
    ul.className = 'sec-bullet-list';
    for (const uq of cmp.unresolved_questions) {
      const li = document.createElement('li');
      li.textContent = uq;
      ul.appendChild(li);
    }
    sec.appendChild(ul);
    card.appendChild(sec);
  }

  return card;
}

function renderAnalysisResponse(data) {
  if (!secAnalysisContainer) return;
  if (secAnalysisProgress) secAnalysisProgress.style.display = 'none';

  if (data.engine === 'BOTH') {
    const dualView = document.createElement('div');
    dualView.className = 'sec-analysis-dual-view';
    if (data.comparison) {
      dualView.appendChild(renderComparisonCard(data.comparison));
    }
    const sideBySide = document.createElement('div');
    sideBySide.className = 'sec-analysis-side-by-side';
    sideBySide.style.display = 'grid';
    sideBySide.style.gridTemplateColumns = '1fr 1fr';
    sideBySide.style.gap = '1rem';
    sideBySide.style.marginTop = '1rem';
    sideBySide.appendChild(renderSingleAnalysisCard(data.codex, 'Codex App Server'));
    sideBySide.appendChild(renderSingleAnalysisCard(data.antigravity, 'Antigravity CLI'));
    dualView.appendChild(sideBySide);
    secAnalysisContainer.replaceChildren(dualView);
  } else if (data.result) {
    secAnalysisContainer.replaceChildren(renderSingleAnalysisCard(data.result, data.engine));
  } else {
    secAnalysisContainer.replaceChildren(renderSingleAnalysisCard(data, data.engine || 'AI Engine'));
  }
}

function subscribeAnalysisEvents(analysisId, engine) {
  if (secAnalysisProgress) {
    secAnalysisProgress.style.display = 'block';
    secAnalysisProgress.textContent = `🚀 Dispatched ${engine} analysis (${analysisId})...\n`;
  }
  const es = new EventSource(`/api/v2/security-agent/analyses/${encodeURIComponent(analysisId)}/events`);

  const appendProgress = (msg) => {
    if (secAnalysisProgress) {
      secAnalysisProgress.textContent += msg + '\n';
    }
  };

  const handleFinish = async (success, errorMsg) => {
    try {
      es.close();
    } catch (e) {}
    if (success) {
      try {
        const full = await getJSON(`/api/v2/security-agent/analyses/${encodeURIComponent(analysisId)}`);
        if (full) {
          renderAnalysisResponse(full);
          return;
        }
      } catch (e) {
        appendProgress(`Failed to load analysis result: ${e.message || e}`);
      }
    }
    if (secAnalysisContainer) {
      const errDiv = document.createElement('div');
      errDiv.className = 'sec-empty-hint error';
      errDiv.textContent = `❌ AI Analysis failed: ${errorMsg || 'Analysis unsuccessful'}`;
      secAnalysisContainer.replaceChildren(errDiv);
    }
  };

  es.addEventListener('analysis.started', (e) => {
    try {
      const d = JSON.parse(e.data || '{}');
      appendProgress(`Analysis started with engine: ${d.engine || engine}`);
    } catch (err) {}
  });

  es.addEventListener('analysis.completed', (e) => {
    try {
      const d = JSON.parse(e.data || '{}');
      appendProgress(`Analysis completed (confidence: ${d.confidence ?? 'N/A'})`);
    } catch (err) {}
    handleFinish(true);
  });

  es.addEventListener('analysis.failed', (e) => {
    let msg = 'Analysis failed';
    try {
      const d = JSON.parse(e.data || '{}');
      msg = d.error || d.summary || msg;
    } catch (err) {}
    appendProgress(`Analysis failed: ${msg}`);
    handleFinish(false, msg);
  });

  es.onerror = () => {
    setTimeout(async () => {
      try {
        const check = await getJSON(`/api/v2/security-agent/analyses/${encodeURIComponent(analysisId)}`);
        if (check && (check.status === 'COMPLETED' || check.codex || check.result)) {
          es.close();
          renderAnalysisResponse(check);
        }
      } catch (e) {}
    }, 1000);
  };
}

async function runIncidentAnalysis(fingerprint, engine = 'BOTH') {
  if (!fingerprint) return;
  if (secIncidentDetailDialog) secIncidentDetailDialog.close();
  switchTab('sec-panel-analysis');

  if (secAnalysisProgress) {
    secAnalysisProgress.style.display = 'block';
    secAnalysisProgress.textContent = `🚀 Launching ${engine} analysis for incident ${fingerprint}...\n`;
  }
  if (secAnalysisContainer) {
    const hint = document.createElement('div');
    hint.className = 'sec-empty-hint';
    hint.textContent = `⏳ AI Analysis in progress (${engine})...`;
    secAnalysisContainer.replaceChildren(hint);
  }

  try {
    const res = await mutateJSON(`/api/v2/security-agent/incidents/${encodeURIComponent(fingerprint)}/analyses`, {
      engine: engine,
    });
    if (res && res.status === 'ACCEPTED' && res.analysis_id) {
      subscribeAnalysisEvents(res.analysis_id, res.engine || engine);
    } else if (res) {
      renderAnalysisResponse(res);
    }
  } catch (err) {
    if (secAnalysisContainer) {
      const errDiv = document.createElement('div');
      errDiv.className = 'sec-empty-hint error';
      errDiv.textContent = `❌ AI Analysis failed: ${err.message || err}`;
      secAnalysisContainer.replaceChildren(errDiv);
    }
  }
}

async function runRunAnalysis(runId, engine = 'BOTH') {
  const actualRunId = runId || activeRunId;
  if (!actualRunId || actualRunId === 'latest') {
    try {
      const runsData = await getJSON('/api/v2/security-agent/runs?limit=1');
      if (runsData && runsData.runs && runsData.runs.length > 0) {
        return runRunAnalysis(runsData.runs[0].run_id, engine);
      }
    } catch (e) {}
    if (secAnalysisContainer) {
      const hint = document.createElement('div');
      hint.className = 'sec-empty-hint';
      hint.textContent = 'No completed review runs found to analyze. Please execute a review run first.';
      secAnalysisContainer.replaceChildren(hint);
    }
    return;
  }

  switchTab('sec-panel-analysis');
  if (secAnalysisProgress) {
    secAnalysisProgress.style.display = 'block';
    secAnalysisProgress.textContent = `🚀 Launching ${engine} analysis for run ${actualRunId}...\n`;
  }
  if (secAnalysisContainer) {
    const hint = document.createElement('div');
    hint.className = 'sec-empty-hint';
    hint.textContent = `⏳ AI Analysis in progress (${engine})...`;
    secAnalysisContainer.replaceChildren(hint);
  }

  try {
    const res = await mutateJSON(`/api/v2/security-agent/runs/${encodeURIComponent(actualRunId)}/analyses`, {
      engine: engine,
    });
    if (res && res.status === 'ACCEPTED' && res.analysis_id) {
      subscribeAnalysisEvents(res.analysis_id, res.engine || engine);
    } else if (res) {
      renderAnalysisResponse(res);
    }
  } catch (err) {
    if (secAnalysisContainer) {
      const errDiv = document.createElement('div');
      errDiv.className = 'sec-empty-hint error';
      errDiv.textContent = `❌ AI Analysis failed: ${err.message || err}`;
      secAnalysisContainer.replaceChildren(errDiv);
    }
  }
}

async function handleOpenIncidentChat(fingerprint, engine = 'codex') {
  if (!fingerprint) return;
  try {
    const res = await mutateJSON(`/api/v2/security-agent/incidents/${encodeURIComponent(fingerprint)}/open-chat`, {
      engine: engine,
    });
    if (res && res.thread_id) {
      if (secIncidentDetailDialog) secIncidentDetailDialog.close();
      if (secDialog) secDialog.close();
      window.location.hash = `#thread=${res.thread_id}`;
      const composer = document.querySelector('#composer-input');
      if (composer) {
        composer.value = `Investigate incident ${res.fingerprint}`;
        composer.focus();
      }
    }
  } catch (err) {
    console.error('Failed opening incident chat:', err);
  }
}

// Button wiring
if (secDetailBtnAnalyzeCodex) {
  secDetailBtnAnalyzeCodex.addEventListener('click', () => {
    runIncidentAnalysis(activeIncidentFingerprint, 'CODEX');
  });
}

if (secDetailBtnAnalyzeAntigravity) {
  secDetailBtnAnalyzeAntigravity.addEventListener('click', () => {
    runIncidentAnalysis(activeIncidentFingerprint, 'ANTIGRAVITY');
  });
}

if (secDetailBtnAnalyzeBoth) {
  secDetailBtnAnalyzeBoth.addEventListener('click', () => {
    runIncidentAnalysis(activeIncidentFingerprint, 'BOTH');
  });
}

if (secDetailBtnOpenChat) {
  secDetailBtnOpenChat.addEventListener('click', () => {
    handleOpenIncidentChat(activeIncidentFingerprint, 'codex');
  });
}

if (secRunAnalysisBtn) {
  secRunAnalysisBtn.addEventListener('click', () => {
    const targetType = secAnalysisTargetType ? secAnalysisTargetType.value : 'LATEST_RUN';
    const engine = secAnalysisEngineSelectPanel ? secAnalysisEngineSelectPanel.value : 'BOTH';
    if (targetType === 'ACTIVE_INCIDENT' && activeIncidentFingerprint) {
      runIncidentAnalysis(activeIncidentFingerprint, engine);
    } else {
      runRunAnalysis(activeRunId, engine);
    }
  });
}

// --- Diagnostic Troubleshooting Handlers ---

async function handleStartTroubleshooting(fingerprint) {
  if (!fingerprint) return;
  if (!secIncidentTroubleshootContainer) return;

  secIncidentTroubleshootContainer.style.display = 'block';
  const loadingDiv = document.createElement('div');
  loadingDiv.style.color = '#38bdf8';
  loadingDiv.style.display = 'flex';
  loadingDiv.style.alignItems = 'center';
  loadingDiv.style.gap = '8px';

  const spinSpan = document.createElement('span');
  spinSpan.className = 'sec-spinner';
  spinSpan.setAttribute('aria-hidden', 'true');
  spinSpan.textContent = '⏳';

  const spinText = document.createElement('span');
  spinText.textContent = 'Generating P8 diagnostic troubleshooting plan…';

  loadingDiv.append(spinSpan, spinText);
  secIncidentTroubleshootContainer.replaceChildren(loadingDiv);

  if (secDetailBtnTroubleshoot) secDetailBtnTroubleshoot.disabled = true;

  try {
    const res = await mutateJSON(`/api/v2/security-agent/incidents/${encodeURIComponent(fingerprint)}/troubleshoot`, {
      execute_p9: false,
    });

    const target = res.target_canonical || 'Unknown Target';
    const scenario = res.scenario || 'Unknown Scenario';
    const binding = res.binding || 'None';
    const plan = res.p8_plan || {};
    const checks = plan.planned_checks || [];
    const handoff = res.ai_handoff || {};

    const fragment = document.createDocumentFragment();

    const topHeaderDiv = document.createElement('div');
    topHeaderDiv.style.marginBottom = '8px';

    const h4 = document.createElement('h4');
    h4.style.margin = '0 0 4px 0';
    h4.style.color = '#38bdf8';
    h4.style.display = 'flex';
    h4.style.justifyContent = 'space-between';
    h4.style.alignItems = 'center';

    const titleSpan = document.createElement('span');
    titleSpan.textContent = '🛠️ P8 Troubleshooting Plan Prepared';

    const pillSpan = document.createElement('span');
    pillSpan.className = 'status-pill safe';
    pillSpan.style.fontSize = '0.75rem';
    pillSpan.textContent = 'PLAN_READY';

    h4.append(titleSpan, pillSpan);

    const descP = document.createElement('p');
    descP.style.margin = '0';
    descP.style.fontSize = '0.85rem';
    descP.style.color = '#94a3b8';

    const strongTgt = document.createElement('strong');
    strongTgt.textContent = target;
    const codeScen = document.createElement('code');
    codeScen.textContent = scenario;
    const codeBind = document.createElement('code');
    codeBind.textContent = binding;

    descP.append('Target: ', strongTgt, ' · Scenario: ', codeScen, ' · Binding: ', codeBind);
    topHeaderDiv.append(h4, descP);
    fragment.appendChild(topHeaderDiv);

    const checksDiv = document.createElement('div');
    checksDiv.style.margin = '8px 0';
    const strongChecks = document.createElement('strong');
    strongChecks.style.fontSize = '0.85rem';
    strongChecks.style.color = '#f1f5f9';
    strongChecks.textContent = `Planned Read-Only Checks (${checks.length}):`;
    checksDiv.appendChild(strongChecks);

    if (checks.length > 0) {
      const ul = document.createElement('ul');
      ul.style.margin = '6px 0';
      ul.style.paddingLeft = '18px';
      ul.style.fontSize = '0.85rem';
      ul.style.color = '#cbd5e1';
      for (const chk of checks) {
        const li = document.createElement('li');
        const code = document.createElement('code');
        code.textContent = chk.check_id || chk;
        li.append(code, ` — ${chk.description || ''}`);
        ul.appendChild(li);
      }
      checksDiv.appendChild(ul);
    } else {
      const noChecks = document.createElement('div');
      noChecks.style.color = '#64748b';
      noChecks.style.fontSize = '0.85rem';
      noChecks.textContent = 'No read-only checks planned.';
      checksDiv.appendChild(noChecks);
    }
    fragment.appendChild(checksDiv);

    if (handoff.suggested_ai_prompt) {
      const promptBox = document.createElement('div');
      promptBox.style.marginTop = '8px';
      promptBox.style.padding = '8px';
      promptBox.style.background = '#071220';
      promptBox.style.borderRadius = '4px';
      promptBox.style.border = '1px solid #1e293b';

      const promptLabel = document.createElement('div');
      promptLabel.style.fontSize = '0.75rem';
      promptLabel.style.color = '#64748b';
      promptLabel.style.marginBottom = '4px';
      promptLabel.textContent = 'Prepared AI Troubleshooting Prompt:';

      const promptPre = document.createElement('pre');
      promptPre.style.margin = '0';
      promptPre.style.fontSize = '0.8rem';
      promptPre.style.color = '#93c5fd';
      promptPre.style.whiteSpace = 'pre-wrap';
      promptPre.style.maxHeight = '120px';
      promptPre.style.overflowY = 'auto';
      promptPre.textContent = handoff.suggested_ai_prompt;

      promptBox.append(promptLabel, promptPre);
      fragment.appendChild(promptBox);
    }

    const actionsDiv = document.createElement('div');
    actionsDiv.style.marginTop = '10px';
    actionsDiv.style.display = 'flex';
    actionsDiv.style.gap = '8px';

    const copyBtn = document.createElement('button');
    copyBtn.id = 'sec-troubleshoot-copy-prompt-btn';
    copyBtn.className = 'compact link-btn';
    copyBtn.type = 'button';
    copyBtn.textContent = '📋 Copy AI Prompt';

    if (handoff.suggested_ai_prompt) {
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(handoff.suggested_ai_prompt);
        copyBtn.textContent = '✅ Copied!';
        setTimeout(() => { copyBtn.textContent = '📋 Copy AI Prompt'; }, 3000);
      });
    }

    actionsDiv.appendChild(copyBtn);
    fragment.appendChild(actionsDiv);

    secIncidentTroubleshootContainer.replaceChildren(fragment);

    fetchIncidentTimeline(fingerprint);
  } catch (err) {
    const errDiv = document.createElement('div');
    errDiv.style.color = '#f87171';
    errDiv.style.fontSize = '0.85rem';
    errDiv.textContent = `❌ Troubleshooting handoff failed: ${err.message}`;
    secIncidentTroubleshootContainer.replaceChildren(errDiv);
  } finally {
    if (secDetailBtnTroubleshoot) secDetailBtnTroubleshoot.disabled = false;
  }
}

if (secDetailBtnTroubleshoot) {
  secDetailBtnTroubleshoot.addEventListener('click', () => {
    handleStartTroubleshooting(activeIncidentFingerprint);
  });
}
