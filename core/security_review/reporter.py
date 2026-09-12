import csv
import html
import io
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

import jinja2
from core.connectors.security.models import (
    CollectorResult,
    CollectorStatus,
    Incident,
    SeverityLevel,
)
from core.security_review.config import SecurityAgentConfig
from core.security_review.trends import categorize_run_incidents_delta, get_trend_analytics

logger = logging.getLogger(__name__)


class SeverityWrapper(str):
    @property
    def value(self) -> str:
        return str(self)


class CategoryWrapper(str):
    @property
    def value(self) -> str:
        return str(self)


class StatusWrapper(str):
    @property
    def value(self) -> str:
        return str(self)


class SecurityReporter:
    """Generates executive HTML email reports, renders attached PDFs, and handles SMTP dispatch."""

    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_dir),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
        )
        self.config_mgr = SecurityAgentConfig()
        self.smtp_host = os.getenv("MNE_SMTP_HOST", "172.23.71.36")
        self.smtp_port = int(os.getenv("MNE_SMTP_PORT", "25"))
        self.smtp_user = os.getenv("MNE_SMTP_USER", "")
        self.smtp_password = os.getenv("MNE_SMTP_PASSWORD", "")
        self.smtp_sender = os.getenv("MNE_SMTP_SENDER", "security-alert@mne.gov.ps")

    @property
    def default_recipients(self) -> List[str]:
        return self.config_mgr.get_recipients()

    def render_html_report(
        self,
        incidents: List[Any],
        collectors: List[Any],
        run_id: Optional[str] = None,
        generated_at: Optional[str] = None,
    ) -> str:
        """Renders the responsive executive HTML report using Jinja2."""
        template = self.jinja_env.get_template("report.html.j2")
        now_str = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        norm_incidents = []
        for inc in (incidents or []):
            if isinstance(inc, dict):
                sev_raw = str(inc.get("current_severity") or inc.get("severity", "MEDIUM")).upper()
                cat_raw = str(inc.get("category", "ANOMALY"))
                dev = str(inc.get("source_device", "Perimeter"))
                i_id = str(inc.get("display_id") or inc.get("incident_id") or inc.get("fingerprint", "INC"))
                title = str(inc.get("title", "Security Threat Incident"))
                desc = str(inc.get("description", ""))
                atk = str(inc.get("attacker_identity") or inc.get("attacker_ip") or "")
                tgt = str(inc.get("target_identity") or inc.get("target") or "")
                ev_cnt = int(inc.get("event_count") or 1)
                action = str(inc.get("action_taken") or "BLOCKED")
                cli = list(inc.get("remediation_cli") or [])
                gui = list(inc.get("remediation_gui") or [])
                mode_b = inc.get("remediation_mode_b_command")
                sig = str(inc.get("signature_family") or title)
                pc_name = inc.get("attacker_pc_name")
                fqdn = inc.get("attacker_fqdn")
                user = inc.get("attacker_username")
                user_display = inc.get("attacker_user_display_name")
                owner = inc.get("attacker_device_owner")
                mac = inc.get("attacker_mac_address")
                scope = inc.get("attacker_network_scope")
                id_status = inc.get("attacker_identity_status")
                id_conf = inc.get("attacker_identity_confidence")
                conf_score = inc.get("attacker_identity_confidence_score")
                id_sources = inc.get("attacker_identity_sources") or []
                observed_at = inc.get("attacker_identity_observed_at")
                id_candidates = inc.get("attacker_identity_candidates") or []
                id_diags = inc.get("attacker_identity_diagnostics") or []
                attr = inc.get("attacker_attribution") or {}
            else:
                sev_raw = inc.severity.value if hasattr(inc.severity, "value") else str(inc.severity).upper()
                cat_raw = inc.category.value if hasattr(inc.category, "value") else str(inc.category)
                dev = str(inc.source_device)
                i_id = str(inc.incident_id)
                title = str(inc.title)
                desc = str(inc.description)
                atk = str(inc.attacker_ip or "")
                tgt = str(inc.target or "")
                ev_cnt = int(inc.event_count or 1)
                action = str(inc.action_taken or "BLOCKED")
                cli = list(inc.remediation_cli or [])
                gui = list(inc.remediation_gui or [])
                mode_b = inc.remediation_mode_b_command
                sig = str(getattr(inc, "signature_family", title) or title)
                pc_name = getattr(inc, "attacker_pc_name", None)
                fqdn = getattr(inc, "attacker_fqdn", None)
                user = getattr(inc, "attacker_username", None)
                user_display = getattr(inc, "attacker_user_display_name", None)
                owner = getattr(inc, "attacker_device_owner", None)
                mac = getattr(inc, "attacker_mac_address", None)
                scope = getattr(inc, "attacker_network_scope", None)
                id_status = getattr(inc, "attacker_identity_status", None)
                id_conf = getattr(inc, "attacker_identity_confidence", None)
                conf_score = getattr(inc, "attacker_identity_confidence_score", None)
                id_sources = getattr(inc, "attacker_identity_sources", None) or []
                observed_at = getattr(inc, "attacker_identity_observed_at", None)
                id_candidates = getattr(inc, "attacker_identity_candidates", None) or []
                id_diags = getattr(inc, "attacker_identity_diagnostics", None) or []
                attr = getattr(inc, "attacker_attribution", None) or {}

            norm_incidents.append({
                "incident_id": i_id,
                "title": title,
                "severity": SeverityWrapper(sev_raw),
                "source_device": dev,
                "category": CategoryWrapper(cat_raw),
                "signature_family": sig,
                "description": desc,
                "action_taken": action,
                "event_count": ev_cnt,
                "attacker_ip": atk,
                "target": tgt,
                "remediation_cli": cli,
                "remediation_gui": gui,
                "remediation_mode_b_command": mode_b,
                "attacker_pc_name": pc_name,
                "attacker_fqdn": fqdn,
                "attacker_username": user,
                "attacker_user_display_name": user_display,
                "attacker_device_owner": owner,
                "attacker_mac_address": mac,
                "attacker_network_scope": scope,
                "attacker_identity_status": id_status,
                "attacker_identity_confidence": id_conf,
                "attacker_identity_confidence_score": conf_score,
                "attacker_identity_sources": id_sources,
                "attacker_identity_observed_at": observed_at,
                "attacker_identity_candidates": id_candidates,
                "attacker_identity_diagnostics": id_diags,
                "attacker_attribution": attr,
                "_raw": inc,
            })

        critical_count = sum(1 for i in norm_incidents if i["severity"] == "CRITICAL")
        high_count = sum(1 for i in norm_incidents if i["severity"] == "HIGH")
        medium_count = sum(1 for i in norm_incidents if i["severity"] == "MEDIUM")
        low_count = sum(1 for i in norm_incidents if i["severity"] in ("LOW", "INFO"))
        total_incidents = len(norm_incidents)

        norm_collectors = []
        total_events_collected = 0
        for col in (collectors or []):
            if isinstance(col, dict):
                dev_name = str(col.get("device_name") or col.get("collector") or col.get("device_id") or "Device")
                st_raw = str(col.get("status", "UNKNOWN")).upper()
                evs = col.get("events") or []
                if isinstance(evs, list) and len(evs) > 0:
                    ev_count = len(evs)
                else:
                    ev_count = int(col.get("records_parsed") or col.get("events_collected") or col.get("records_fetched") or 0)
                dur = float(col.get("collection_duration_seconds") or col.get("duration_seconds") or 0.0)
                err = col.get("error_message") or col.get("diagnostic_code") or ""
            else:
                dev_name = str(col.device_name)
                st_raw = col.status.value if hasattr(col.status, "value") else str(col.status).upper()
                evs = getattr(col, "events", []) or []
                if isinstance(evs, list) and len(evs) > 0:
                    ev_count = len(evs)
                else:
                    ev_count = int(getattr(col, "records_parsed", 0) or getattr(col, "events_collected", 0) or 0)
                dur = float(col.collection_duration_seconds or 0.0)
                err = col.error_message or getattr(col, "diagnostic_code", "") or ""

            total_events_collected += ev_count
            norm_collectors.append({
                "device_name": dev_name,
                "status": StatusWrapper(st_raw),
                "events_count": ev_count,
                "events": list(range(ev_count)),
                "collection_duration_seconds": f"{dur:.2f}",
                "error_message": err or "Healthy read-only log synchronization",
                "_raw": col,
            })

        total_incident_events = sum(i["event_count"] for i in norm_incidents)
        if total_events_collected == 0 and total_incident_events > 0:
            total_events_collected = total_incident_events

        online_collectors_count = sum(1 for c in norm_collectors if c["status"] in ("SUCCESS", "WARNING"))
        total_collectors_count = len(norm_collectors)

        if critical_count > 0:
            threat_posture = "CRITICAL ALERT"
            threat_posture_class = "crit"
            posture_summary = f"{critical_count} critical severity exploit(s) detected requiring immediate containment."
        elif high_count > 0:
            threat_posture = "ELEVATED RISK"
            threat_posture_class = "high"
            posture_summary = f"{high_count} high severity threat(s) actively detected across perimeter and identity infrastructure."
        elif medium_count > 0:
            threat_posture = "MODERATE POSTURE"
            threat_posture_class = "med"
            posture_summary = f"{medium_count} medium severity anomalous event(s) observed under baseline telemetry."
        else:
            threat_posture = "NORMAL / SECURE"
            threat_posture_class = "ok"
            posture_summary = "Zero critical or high severity security anomalies identified during this 24-hour review window."

        # Attacker Aggregation
        attacker_agg: Dict[str, Dict[str, Any]] = {}
        for inc in norm_incidents:
            atk = inc["attacker_ip"].strip()
            if not atk or atk.upper() in ("N/A", "NONE", "", "UNKNOWN"):
                continue
            if atk not in attacker_agg:
                attacker_agg[atk] = {
                    "ip": atk,
                    "count": 0,
                    "targets": set(),
                    "devices": set(),
                    "actions": set(),
                    "threats": set(),
                }
            attacker_agg[atk]["count"] += inc["event_count"]
            if inc["target"]:
                attacker_agg[atk]["targets"].add(inc["target"])
            if inc["source_device"]:
                attacker_agg[atk]["devices"].add(inc["source_device"])
            if inc["action_taken"]:
                attacker_agg[atk]["actions"].add(inc["action_taken"])
            if inc["title"]:
                attacker_agg[atk]["threats"].add(inc["title"])

        top_attackers = []
        for atk, ad in sorted(attacker_agg.items(), key=lambda x: x[1]["count"], reverse=True)[:8]:
            top_attackers.append({
                "ip": atk,
                "count": ad["count"],
                "target": ", ".join(sorted(list(ad["targets"])))[:45] or "Perimeter VIP",
                "device": ", ".join(sorted(list(ad["devices"])))[:35] or "Edge Gateway",
                "threat": next(iter(ad["threats"]), "Anomalous Traffic"),
                "action": next(iter(ad["actions"]), "BLOCKED"),
            })

        # Category Aggregation
        cat_agg: Dict[str, int] = {}
        for inc in norm_incidents:
            c = str(inc["category"])
            cat_agg[c] = cat_agg.get(c, 0) + 1
        category_breakdown = sorted(
            [{"name": k.replace("_", " ").title(), "count": v, "pct": round(v / max(total_incidents, 1) * 100, 1)} for k, v in cat_agg.items()],
            key=lambda x: x["count"],
            reverse=True
        )

        # Threat Clusters (Signature Aggregation)
        cluster_agg: Dict[str, Dict[str, Any]] = {}
        for inc in norm_incidents:
            sig = inc["signature_family"] or inc["title"]
            if sig not in cluster_agg:
                cluster_agg[sig] = {
                    "signature": sig,
                    "title": inc["title"],
                    "severity": inc["severity"],
                    "source_device": inc["source_device"],
                    "category": inc["category"],
                    "incident_count": 0,
                    "total_events": 0,
                    "primary_cli": inc["remediation_cli"][0] if inc["remediation_cli"] else None,
                }
            cluster_agg[sig]["incident_count"] += 1
            cluster_agg[sig]["total_events"] += inc["event_count"]

        threat_clusters = sorted(
            cluster_agg.values(),
            key=lambda x: (
                0 if x["severity"] == "CRITICAL" else (1 if x["severity"] == "HIGH" else 2),
                -x["total_events"]
            )
        )

        return template.render(
            generated_at=now_str,
            run_id=run_id or f"sec-run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            total_incidents=total_incidents,
            total_events=total_events_collected,
            online_collectors_count=online_collectors_count,
            total_collectors_count=total_collectors_count,
            threat_posture=threat_posture,
            threat_posture_class=threat_posture_class,
            posture_summary=posture_summary,
            collectors=norm_collectors,
            incidents=norm_incidents,
            top_attackers=top_attackers,
            category_breakdown=category_breakdown,
            threat_clusters=threat_clusters,
        )

    def compile_pdf_report(
        self,
        html_content: str = "",
        incidents: Optional[List[Any]] = None,
        collectors: Optional[List[Any]] = None,
        run_id: Optional[str] = None,
        run_store: Optional[Any] = None,
    ) -> bytes:
        """Compiles a professional executive PDF report using ReportLab."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=14,
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0284c7"),
            spaceBefore=12,
            spaceAfter=6,
        )
        code_style = ParagraphStyle(
            "CodeBlock",
            parent=styles["Code"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0f172a"),
            backColor=colors.HexColor("#f1f5f9"),
            borderPadding=6,
            spaceBefore=4,
            spaceAfter=6,
        )
        alert_style = ParagraphStyle(
            "AlertBox",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#991b1b"),
            backColor=colors.HexColor("#fee2e2"),
            borderPadding=6,
            spaceBefore=6,
            spaceAfter=8,
        )

        elements = []
        # Header
        elements.append(Paragraph("Ministry of National Economy (MNE)", title_style))
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        elements.append(Paragraph(f"Daily Cyber Threat & Risk Intelligence Briefing | Generated: {today_str} | Window: Past 24h", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=12))

        # Risk Metrics Grid
        inc_list = incidents
        if inc_list is None and run_id and run_store:
            inc_list = run_store.get_incidents(run_id) or []
        inc_list = inc_list or []

        def _get_sev(item):
            if isinstance(item, dict):
                return str(item.get("current_severity") or item.get("severity", "MEDIUM")).upper()
            return item.severity.value if hasattr(item.severity, "value") else str(item.severity).upper()

        crit_n = sum(1 for i in inc_list if _get_sev(i) == "CRITICAL")
        high_n = sum(1 for i in inc_list if _get_sev(i) == "HIGH")
        med_n = sum(1 for i in inc_list if _get_sev(i) == "MEDIUM")

        col_list = collectors
        if isinstance(col_list, dict):
            col_list = list(col_list.values())
        if col_list is None and run_id and run_store:
            diags = run_store.get_collector_diagnostics(run_id) or {}
            col_list = diags if isinstance(diags, list) else list(diags.values()) if isinstance(diags, dict) else []
        col_list = col_list or []

        def _is_col_success(col):
            if isinstance(col, dict):
                return str(col.get("status", "")).upper() == "SUCCESS"
            if hasattr(col, "status"):
                status_val = col.status.value if hasattr(col.status, "value") else str(col.status)
                return str(status_val).upper() == "SUCCESS"
            return False

        success_cols = sum(1 for c in col_list if _is_col_success(c))
        total_cols = len(col_list) if col_list else 6

        summary_data = [
            ["Critical Risks", "High Risks", "Medium Risks", "Devices Online"],
            [str(crit_n), str(high_n), str(med_n), f"{success_cols}/{total_cols}"],
        ]
        summary_table = Table(summary_data, colWidths=[130, 130, 130, 130])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
            ("FONTSIZE", (0, 1), (-1, 1), 14),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 12))

        # Ingestion Health Table
        if col_list:
            elements.append(Paragraph("Perimeter & Identity Log Ingestion Health", h2_style))
            health_rows = [["System", "Status", "Events", "Time", "Diagnostics"]]
            failed_count = 0
            for col in col_list:
                if isinstance(col, dict):
                    status_str = str(col.get("status", "UNKNOWN"))
                    diag = str(col.get("error_message") or col.get("diagnostic_code") or "Healthy log synchronization")[:45]
                    dev_name = str(col.get("collector") or col.get("device_id") or "Device")
                    ev_count = str(col.get("events_collected", 0))
                    dur = f"{col.get('duration_seconds', 0)}s"
                else:
                    status_str = col.status.value
                    diag = (col.error_message or "Healthy log synchronization")[:45]
                    dev_name = col.device_name
                    ev_count = str(len(col.events))
                    dur = f"{col.collection_duration_seconds}s"
                if status_str != "SUCCESS":
                    failed_count += 1
                health_rows.append([dev_name, status_str, ev_count, dur, diag])

            health_table = Table(health_rows, colWidths=[100, 60, 50, 50, 260])
            health_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            elements.append(health_table)
            elements.append(Spacer(1, 10))

            if failed_count > 0:
                elements.append(Paragraph(f"⚠️ <b>OPERATIONAL ALERT:</b> {failed_count} device(s) encountered log collection errors. Review connectivity or credentials.", alert_style))

        # Incidents Section
        elements.append(Paragraph("Identified Security Risks & Threat Incidents", h2_style))
        if inc_list:
            for inc in inc_list:
                if isinstance(inc, dict):
                    sev_val = str(inc.get("current_severity") or inc.get("severity", "MEDIUM")).upper()
                    inc_id = str(inc.get("display_id") or inc.get("incident_id") or inc.get("fingerprint", "INC"))
                    inc_title = f"[{sev_val}] {inc_id} — {inc.get('title', '')}"
                    elements.append(Paragraph(f"<b>{inc_title}</b>", styles["Heading3"]))
                    atk = str(inc.get("attacker_identity") or inc.get("attacker_ip", "N/A"))
                    tgt = str(inc.get("target_identity") or inc.get("target", "N/A"))
                    dev = str(inc.get("source_device", "N/A"))
                    attempts = inc.get("event_count", 1)
                    desc = str(inc.get("description", ""))
                    rem_cli = inc.get("remediation_cli", [])
                    rem_mode_b = inc.get("remediation_mode_b_command")
                    pc_name = inc.get("attacker_pc_name")
                    user = inc.get("attacker_username")
                    owner = inc.get("attacker_device_owner")
                    mac = inc.get("attacker_mac_address")
                    id_status = inc.get("attacker_identity_status")
                    id_conf = inc.get("attacker_identity_confidence")
                else:
                    inc_title = f"[{inc.severity.value}] {inc.incident_id} — {inc.title}"
                    elements.append(Paragraph(f"<b>{inc_title}</b>", styles["Heading3"]))
                    atk = inc.attacker_ip or "N/A"
                    tgt = inc.target or "N/A"
                    dev = inc.source_device
                    attempts = inc.event_count
                    desc = inc.description
                    rem_cli = inc.remediation_cli
                    rem_mode_b = inc.remediation_mode_b_command
                    pc_name = getattr(inc, "attacker_pc_name", None)
                    user = getattr(inc, "attacker_username", None)
                    owner = getattr(inc, "attacker_device_owner", None)
                    mac = getattr(inc, "attacker_mac_address", None)
                    id_status = getattr(inc, "attacker_identity_status", None)
                    id_conf = getattr(inc, "attacker_identity_confidence", None)

                details_p = f"Device: <b>{dev}</b> | Attacker: <b>{atk}</b> | Target: <b>{tgt}</b> | Attempts: <b>{attempts}</b>"
                elements.append(Paragraph(details_p, styles["Normal"]))

                id_parts = []
                if pc_name and pc_name not in ("Unknown", "Not applicable"):
                    id_parts.append(f"PC: <b>{pc_name}</b>")
                if user and user not in ("Unknown", "Not applicable"):
                    id_parts.append(f"User: <b>{user}</b>")
                if owner and owner not in ("Unknown", "Not applicable"):
                    id_parts.append(f"Owner: <b>{owner}</b>")
                if mac and mac not in ("Unknown", "Not applicable"):
                    id_parts.append(f"MAC: <b>{mac}</b>")
                if id_status and id_status not in ("NOT_APPLICABLE", "NOT_CONFIGURED", "NOT_FOUND"):
                    id_parts.append(f"Status: <b>{id_status}</b> ({id_conf or ''})")
                if id_parts:
                    elements.append(Paragraph(f"Attacker Identity: {' | '.join(id_parts)}", styles["Normal"]))

                elements.append(Paragraph(f"Description: {desc}", styles["Normal"]))

                if rem_cli:
                    elements.append(Paragraph("<b>CLI Containment Playbook:</b>", styles["Normal"]))
                    cli_text = "<br/>".join(rem_cli)
                    elements.append(Paragraph(cli_text, code_style))

                if rem_mode_b:
                    elements.append(Paragraph(f"<i>Mode B Remediation:</i> {rem_mode_b}", subtitle_style))
                elements.append(Spacer(1, 8))
        else:
            elements.append(Paragraph("No active security threats meeting Critical, High, or Medium risk thresholds were observed in the collected telemetry.", styles["Normal"]))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def build_email_message(
        self,
        html_content: str,
        pdf_bytes: bytes,
        recipients: Optional[List[str]] = None,
        subject_date_str: Optional[str] = None,
    ) -> MIMEMultipart:
        """Constructs a standard MIME multipart email with HTML body and attached PDF."""
        target_recipients = recipients or self.default_recipients
        date_label = subject_date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"MNE Daily Cyber Threat & Risk Intelligence Briefing - {date_label}"
        msg["From"] = self.smtp_sender
        msg["To"] = ", ".join(target_recipients)

        # HTML Part
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        # PDF Attachment Part
        pdf_filename = f"MNE_Daily_Security_Report_{date_label}.pdf"
        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
        msg.attach(pdf_part)

        return msg

    def send_daily_security_email(
        self,
        html_content: str,
        pdf_bytes: bytes,
        recipients: Optional[List[str]] = None,
    ) -> bool:
        """Sends the compiled report via SMTP."""
        target_recipients = recipients or self.default_recipients
        msg = self.build_email_message(html_content, pdf_bytes, target_recipients)

        try:
            logger.info("Connecting to SMTP server at %s:%s...", self.smtp_host, self.smtp_port)
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            if self.smtp_port == 587:
                server.starttls()
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)

            server.send_message(msg)
            server.quit()
            logger.info("Security report successfully emailed to %s", target_recipients)
            return True
        except Exception as exc:
            logger.error("Failed to send security report email via SMTP: %s", exc, exc_info=True)
            return False

    def send_test_email(self, recipients: Optional[List[str]] = None) -> Tuple[bool, str]:
        """Sends an automated test email to confirm SMTP server reachability and inbox delivery."""
        target_recipients = recipients or self.default_recipients
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"MNE Security Review Agent — SMTP Verification Test ({now_str})"
        msg["From"] = self.smtp_sender
        msg["To"] = ", ".join(target_recipients)

        text_body = (
            f"MNE Cybersecurity Review Agent — SMTP Verification Test\n"
            f"Timestamp: {now_str}\n"
            f"Configured Recipients: {', '.join(target_recipients)}\n"
            f"SMTP Server: {self.smtp_host}:{self.smtp_port}\n\n"
            f"This is an automated test message from MNE_Brain to verify that daily threat briefings "
            f"and executive reports are delivered successfully."
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
body {{ font-family: Segoe UI, sans-serif; background: #071019; color: #e8f0f7; padding: 24px; }}
.card {{ background: #0e1b28; border: 1px solid #21384c; border-radius: 12px; padding: 22px; max-width: 580px; margin: 0 auto; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }}
.badge {{ display: inline-block; background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
h2 {{ margin: 0 0 10px 0; color: #38bdf8; font-size: 18px; }}
p {{ color: #91a4b7; font-size: 13.5px; line-height: 1.5; margin: 0 0 16px 0; }}
table {{ width: 100%; font-size: 13px; color: #cbd5e1; border-top: 1px solid #1c3044; padding-top: 12px; border-collapse: collapse; }}
td {{ padding: 6px 0; }}
.label {{ color: #64748b; width: 130px; font-weight: 600; }}
.footer {{ margin-top: 16px; padding-top: 10px; border-top: 1px solid #1c3044; font-size: 11px; color: #64748b; }}
</style></head>
<body>
  <div class="card">
    <span class="badge">MNE_Brain Security Verification</span>
    <h2>SMTP Connectivity Confirmed</h2>
    <p>This automated test confirms that the MNE Cybersecurity Review & Threat Reporting Agent can reach your email server and successfully deliver daily briefings and executive PDF reports.</p>
    <table>
      <tr><td class="label">Timestamp:</td><td>{now_str}</td></tr>
      <tr><td class="label">SMTP Server:</td><td>{self.smtp_host}:{self.smtp_port}</td></tr>
      <tr><td class="label">Sender:</td><td>{self.smtp_sender}</td></tr>
      <tr><td class="label">Recipients:</td><td>{', '.join(target_recipients)}</td></tr>
    </table>
    <div class="footer">MNE_Brain Release 2 · Confidential Infrastructure Management</div>
  </div>
</body>
</html>"""
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            logger.info("Connecting to SMTP server at %s:%s for test email...", self.smtp_host, self.smtp_port)
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            if self.smtp_port == 587:
                server.starttls()
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            logger.info("Test email successfully sent to %s", target_recipients)
            return True, f"Test email sent successfully to {', '.join(target_recipients)}"
        except Exception as exc:
            logger.error("Failed sending test email: %s", exc, exc_info=True)
            return False, f"SMTP Error: {str(exc)}"

    def generate_json_export(
        self,
        run_id: str,
        run_store: Any,
        incident_store: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Generates a complete JSON-serializable export of a persisted run."""
        run_data = run_store.get_run(run_id) or {}
        incidents = run_store.get_incidents(run_id) or []
        diagnostics = run_store.get_collector_diagnostics(run_id) or {}
        analyses = run_store.list_analyses(run_id=run_id) if hasattr(run_store, "list_analyses") else []
        delta = categorize_run_incidents_delta(run_id, run_store, incident_store)
        inc_store = incident_store or getattr(run_store, "incident_store", None)
        trends = get_trend_analytics(run_store, inc_store, days=30) if inc_store else {}

        return {
            "export_type": "SECURITY_REVIEW_RUN_EXPORT",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "run": run_data,
            "incidents": incidents,
            "collector_diagnostics": diagnostics,
            "cross_run_delta": delta,
            "analyses": analyses,
            "trends": trends,
        }

    def generate_csv_incident_export(
        self,
        run_id: str,
        run_store: Any,
        incident_store: Optional[Any] = None,
    ) -> str:
        """Generates a CSV export of all incidents detected in a persisted run."""
        incidents = run_store.get_incidents(run_id) or []
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow([
            "fingerprint", "display_id", "title", "category", "severity", "lifecycle_state",
            "occurrence_count", "attacker_identity", "target_identity", "source_device",
            "event_count", "blocked_count", "allowed_count", "first_seen", "last_seen",
        ])

        for inc in incidents:
            disp = inc.get("disposition_breakdown") or {}
            writer.writerow([
                inc.get("fingerprint") or inc.get("incident_id", ""),
                inc.get("display_id", ""),
                inc.get("title", ""),
                inc.get("category", ""),
                inc.get("current_severity") or inc.get("severity", "MEDIUM"),
                inc.get("lifecycle_state", "NEW"),
                inc.get("occurrence_count", 1),
                inc.get("attacker_identity") or inc.get("attacker_ip", ""),
                inc.get("target_identity") or inc.get("target", ""),
                inc.get("source_device", ""),
                inc.get("event_count", 1),
                disp.get("BLOCKED", 0),
                disp.get("ALLOWED", 0),
                inc.get("first_seen", ""),
                inc.get("last_seen", ""),
            ])

        return out.getvalue()

    def generate_executive_report(
        self,
        run_id: str,
        run_store: Any,
        incident_store: Optional[Any] = None,
    ) -> str:
        """Renders an executive HTML briefing from persisted run and incident records."""
        run_data = run_store.get_run(run_id) or {}
        incidents = run_store.get_incidents(run_id) or []
        delta = categorize_run_incidents_delta(run_id, run_store, incident_store)
        inc_store = incident_store or getattr(run_store, "incident_store", None)
        trends = get_trend_analytics(run_store, inc_store, days=30) if inc_store else {}
        analyses = run_store.list_analyses(run_id=run_id) if hasattr(run_store, "list_analyses") else []
        diags = run_store.get_collector_diagnostics(run_id) or {}
        diag_list = diags if isinstance(diags, list) else list(diags.values()) if isinstance(diags, dict) else []

        crit_count = sum(1 for i in incidents if str(i.get("current_severity", i.get("severity"))).upper() == "CRITICAL")
        high_count = sum(1 for i in incidents if str(i.get("current_severity", i.get("severity"))).upper() == "HIGH")
        med_count = sum(1 for i in incidents if str(i.get("current_severity", i.get("severity"))).upper() == "MEDIUM")

        healthy_cols = sum(1 for d in diag_list if isinstance(d, dict) and d.get("status") == "SUCCESS")
        total_cols = len(diag_list) if diag_list else 6

        req = run_data.get("request", {})
        win = req.get("time_window", {})
        win_str = f"Last {win.get('hours', 24)} Hours" if win.get("mode") == "HOURS" else "Custom Window"
        gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # HTML generation
        new_incs = delta.get("new_incidents", [])
        rec_incs = delta.get("recurring_incidents", [])
        res_incs = delta.get("no_longer_observed", [])

        # AI analysis highlight
        ai_summary_html = ""
        if analyses:
            latest_a = analyses[-1]
            engine_label = latest_a.get("engine", "AI")
            conc = latest_a.get("common_conclusions") or [h.get("hypothesis") for h in latest_a.get("hypotheses", [])]
            unres = latest_a.get("unresolved_questions", [])
            conc_list = "".join(f"<li>{html.escape(c)}</li>" for c in conc[:3]) or "<li>Investigation active.</li>"
            unres_list = "".join(f"<li>{html.escape(u)}</li>" for u in unres[:2])
            ai_summary_html = f"""
            <div class="card ai-card">
              <div class="card-title">🤖 Strategic AI Intelligence ({html.escape(engine_label)})</div>
              <p><b>Key Hypotheses & Conclusions:</b></p>
              <ul>{conc_list}</ul>
              {f"<p><b>Open Verification Items:</b></p><ul>{unres_list}</ul>" if unres_list else ""}
            </div>
            """

        # Trend table rows
        trend_rows = ""
        daily_trends = trends.get("seven_day_trends", [])
        for d in daily_trends[-7:]:
            trend_rows += f"""
            <tr>
              <td>{html.escape(d.get('date', ''))}</td>
              <td class="num">{d.get('runs', 0)}</td>
              <td class="num crit">{d.get('critical', 0)}</td>
              <td class="num high">{d.get('high', 0)}</td>
              <td class="num med">{d.get('medium', 0)}</td>
              <td class="num bold">{d.get('total', 0)}</td>
            </tr>
            """
        if not trend_rows:
            trend_rows = "<tr><td colspan='6'>No multi-day history recorded yet.</td></tr>"

        # Collector status rows
        diag_rows = ""
        for d in diag_list:
            if not isinstance(d, dict):
                continue
            st = d.get("status", "UNKNOWN")
            st_class = "ok" if st == "SUCCESS" else "err"
            name = d.get("collector") or d.get("device_id") or "Collector"
            ev = d.get("events_collected", 0)
            dur = f"{d.get('duration_seconds', 0)}s"
            msg = (d.get("error_message") or d.get("diagnostic_code") or "Healthy")[:50]
            diag_rows += f"""
            <tr>
              <td><b>{html.escape(name)}</b></td>
              <td><span class="badge {st_class}">{html.escape(st)}</span></td>
              <td class="num">{ev}</td>
              <td class="num">{dur}</td>
              <td>{html.escape(msg)}</td>
            </tr>
            """

        # High priority cards
        high_pri_cards = ""
        pri_incs = [i for i in incidents if str(i.get("current_severity", i.get("severity"))).upper() in ("CRITICAL", "HIGH")][:5]
        for inc in pri_incs:
            sev = str(inc.get("current_severity", inc.get("severity", "HIGH"))).upper()
            sev_class = "crit" if sev == "CRITICAL" else "high"
            title = inc.get("title", "Security Threat")
            dev = inc.get("source_device", "Perimeter")
            atk = inc.get("attacker_identity") or inc.get("attacker_ip", "N/A")
            tgt = inc.get("target_identity") or inc.get("target", "N/A")
            ev = inc.get("event_count", 1)
            high_pri_cards += f"""
            <div class="threat-card">
              <div class="threat-head">
                <span class="badge {sev_class}">{sev}</span>
                <span class="threat-title">{html.escape(title)}</span>
              </div>
              <div class="threat-body">
                <span><b>Device:</b> {html.escape(dev)}</span> ·
                <span><b>Attacker:</b> <code>{html.escape(atk)}</code></span> ·
                <span><b>Target:</b> <code>{html.escape(tgt)}</code></span> ·
                <span><b>Attempts:</b> {ev}</span>
              </div>
            </div>
            """
        if not high_pri_cards:
            high_pri_cards = "<p class='dim'>No Critical or High severity incidents detected in this window.</p>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MNE Security Executive Briefing — {html.escape(run_id)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 24px; line-height: 1.5; }}
  .container {{ max-width: 960px; margin: 0 auto; background: #1e293b; border-radius: 12px; border: 1px solid #334155; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
  .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 32px; border-bottom: 3px solid #0284c7; }}
  .header h1 {{ margin: 0 0 6px 0; font-size: 22px; color: #f8fafc; letter-spacing: -0.5px; }}
  .header .meta {{ font-size: 13px; color: #94a3b8; display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 1px; background: #334155; border-bottom: 1px solid #334155; }}
  .kpi-cell {{ background: #1e293b; padding: 20px 16px; text-align: center; }}
  .kpi-val {{ font-size: 28px; font-weight: 800; line-height: 1; margin-bottom: 4px; }}
  .kpi-lbl {{ font-size: 11px; text-transform: uppercase; font-weight: 600; color: #94a3b8; letter-spacing: 0.5px; }}
  .crit {{ color: #ef4444; }} .high {{ color: #f97316; }} .med {{ color: #eab308; }} .ok {{ color: #22c55e; }} .err {{ color: #ef4444; }}
  .content {{ padding: 32px; }}
  .section-title {{ font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #38bdf8; margin: 28px 0 14px 0; border-left: 3px solid #0284c7; padding-left: 10px; }}
  .card {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 18px; margin-bottom: 16px; }}
  .ai-card {{ border-color: #0284c7; background: #0c1c2e; }}
  .card-title {{ font-weight: 700; color: #38bdf8; margin-bottom: 10px; font-size: 14px; }}
  .threat-card {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px; margin-bottom: 10px; }}
  .threat-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }}
  .threat-title {{ font-weight: 600; font-size: 14px; color: #f8fafc; }}
  .threat-body {{ font-size: 13px; color: #cbd5e1; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; }}
  .badge.crit {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); }}
  .badge.high {{ background: rgba(249, 115, 22, 0.2); color: #f97316; border: 1px solid rgba(249, 115, 22, 0.4); }}
  .badge.med {{ background: rgba(234, 179, 8, 0.2); color: #eab308; border: 1px solid rgba(234, 179, 8, 0.4); }}
  .badge.ok {{ background: rgba(34, 197, 94, 0.2); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.4); }}
  .badge.err {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }}
  th, td {{ padding: 8px 12px; border: 1px solid #334155; text-align: left; }}
  th {{ background: #0f172a; color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 11px; }}
  td.num {{ text-align: right; }}
  .dim {{ color: #64748b; }}
  .footer {{ padding: 20px 32px; background: #0f172a; border-top: 1px solid #334155; font-size: 12px; color: #64748b; text-align: center; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Ministry of National Economy (MNE)</h1>
    <div style="font-size: 16px; font-weight: 600; color: #38bdf8;">Executive Cyber Threat & Risk Briefing</div>
    <div class="meta">
      <span>Run ID: <b>{html.escape(run_id)}</b></span>
      <span>Window: <b>{html.escape(win_str)}</b></span>
      <span>Generated: <b>{html.escape(gen_time)}</b></span>
    </div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-cell"><div class="kpi-val crit">{crit_count}</div><div class="kpi-lbl">Critical Risks</div></div>
    <div class="kpi-cell"><div class="kpi-val high">{high_count}</div><div class="kpi-lbl">High Risks</div></div>
    <div class="kpi-cell"><div class="kpi-val med">{med_count}</div><div class="kpi-lbl">Medium Risks</div></div>
    <div class="kpi-cell"><div class="kpi-val ok">{healthy_cols}/{total_cols}</div><div class="kpi-lbl">Sensors Active</div></div>
    <div class="kpi-cell"><div class="kpi-val">{len(incidents)}</div><div class="kpi-lbl">Total Incidents</div></div>
    <div class="kpi-cell"><div class="kpi-val">{len(new_incs)}</div><div class="kpi-lbl">New Threats</div></div>
  </div>

  <div class="content">
    <div class="section-title">Executive Threat Posture & Delta</div>
    <div class="card">
      <p style="margin-top:0;">
        During this review period (<b>{html.escape(win_str)}</b>), <b>{len(incidents)}</b> active threat incidents were evaluated across perimeter and identity sensors.
        A total of <b>{len(new_incs)}</b> new threats emerged, <b>{len(rec_incs)}</b> persisted from prior cycles, and <b>{len(res_incs)}</b> prior threats were no longer observed.
      </p>
    </div>

    {ai_summary_html}

    <div class="section-title">High-Priority Threat Incidents</div>
    {high_pri_cards}

    <div class="section-title">7-Day Threat History & Fleet Trends</div>
    <table>
      <thead>
        <tr><th>Date</th><th class="num">Runs</th><th class="num">Critical</th><th class="num">High</th><th class="num">Medium</th><th class="num">Total Threats</th></tr>
      </thead>
      <tbody>{trend_rows}</tbody>
    </table>

    <div class="section-title">Sensor Ingestion Health & Coverage</div>
    <table>
      <thead>
        <tr><th>Security Sensor</th><th>Status</th><th class="num">Events</th><th class="num">Duration</th><th>Ingestion Health</th></tr>
      </thead>
      <tbody>{diag_rows}</tbody>
    </table>
  </div>

  <div class="footer">
    MNE_Brain Release 2 · Executive Cyber Risk Intelligence · Confidential Infrastructure Operations
  </div>
</div>
</body>
</html>"""

    def generate_technical_report(
        self,
        run_id: str,
        run_store: Any,
        incident_store: Optional[Any] = None,
    ) -> str:
        """Renders a comprehensive technical HTML report from persisted run and incident records."""
        run_data = run_store.get_run(run_id) or {}
        incidents = run_store.get_incidents(run_id) or []
        delta = categorize_run_incidents_delta(run_id, run_store, incident_store)
        analyses = run_store.list_analyses(run_id=run_id) if hasattr(run_store, "list_analyses") else []
        diags = run_store.get_collector_diagnostics(run_id) or {}
        diag_list = diags if isinstance(diags, list) else list(diags.values()) if isinstance(diags, dict) else []

        req = run_data.get("request", {})
        win = req.get("time_window", {})
        win_str = f"Last {win.get('hours', 24)} Hours" if win.get("mode") == "HOURS" else "Custom Window"
        gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Collector diagnostics rows
        diag_rows = ""
        for d in diag_list:
            if not isinstance(d, dict):
                continue
            st = d.get("status", "UNKNOWN")
            st_badge = f"<span class='badge ok'>{st}</span>" if st == "SUCCESS" else f"<span class='badge err'>{st}</span>"
            name = d.get("collector") or d.get("device_id") or "Collector"
            ev = d.get("events_collected", 0)
            dur = f"{d.get('duration_seconds', 0)}s"
            code = d.get("diagnostic_code") or "OK"
            timings = d.get("timing") or {}
            timing_str = f"Q:{timings.get('query_duration_ms', 0)}ms | P:{timings.get('parse_duration_ms', 0)}ms" if timings else "N/A"
            err = d.get("error_message") or "-"
            diag_rows += f"""
            <tr>
              <td><b>{html.escape(name)}</b></td>
              <td>{st_badge}</td>
              <td class="num">{ev}</td>
              <td class="num">{dur}</td>
              <td><code>{html.escape(code)}</code></td>
              <td><small>{html.escape(timing_str)}</small></td>
              <td><small>{html.escape(err[:60])}</small></td>
            </tr>
            """

        # Detailed Incidents
        incident_blocks = ""
        for inc in incidents:
            sev = str(inc.get("current_severity", inc.get("severity", "MEDIUM"))).upper()
            sev_class = "crit" if sev == "CRITICAL" else "high" if sev == "HIGH" else "med"
            fp = inc.get("fingerprint") or inc.get("incident_id", "")
            disp_id = inc.get("display_id") or fp[:12]
            title = inc.get("title", "")
            cat = inc.get("category", "SECURITY")
            state = inc.get("lifecycle_state", "NEW")
            occs = inc.get("occurrence_count", 1)
            dev = inc.get("source_device", "Perimeter")
            atk = inc.get("attacker_identity") or inc.get("attacker_ip", "N/A")
            tgt = inc.get("target_identity") or inc.get("target", "N/A")
            ev = inc.get("event_count", 1)
            disps = inc.get("disposition_breakdown") or {}
            disp_str = f"Blocked: {disps.get('BLOCKED', 0)} | Allowed: {disps.get('ALLOWED', 0)}"
            sigs = ", ".join(inc.get("signature_ids", [])) or "N/A"
            rules = ", ".join(inc.get("rule_ids", [])) or "N/A"
            desc = inc.get("description", "")
            rem_cli = inc.get("remediation_cli", [])
            cli_block = f"<div class='cli-box'><pre>{html.escape(chr(10).join(rem_cli))}</pre></div>" if rem_cli else ""

            incident_blocks += f"""
            <div class="tech-incident">
              <div class="tech-head">
                <span class="badge {sev_class}">{sev}</span>
                <span class="badge" style="background:#334155;color:#94a3b8;">{html.escape(state)}</span>
                <span class="title">[{html.escape(disp_id)}] {html.escape(title)}</span>
              </div>
              <div class="tech-grid">
                <div><b>Fingerprint:</b> <code>{html.escape(fp[:20])}...</code></div>
                <div><b>Category:</b> {html.escape(cat)}</div>
                <div><b>Device:</b> {html.escape(dev)}</div>
                <div><b>Occurrences:</b> {occs}</div>
                <div><b>Attacker:</b> <code>{html.escape(atk)}</code></div>
                <div><b>Target:</b> <code>{html.escape(tgt)}</code></div>
                <div><b>Events:</b> {ev} ({html.escape(disp_str)})</div>
                <div><b>Signatures:</b> <code>{html.escape(sigs[:30])}</code></div>
              </div>
              <p style="font-size:13px;color:#cbd5e1;margin:8px 0;">{html.escape(desc)}</p>
              {cli_block}
            </div>
            """

        # AI Technical analysis block
        ai_tech_html = ""
        for a in analyses:
            eng = a.get("engine", "AI")
            hyps = a.get("hypotheses", [])
            hyp_rows = "".join(f"<li><b>[{h.get('likelihood', 'UNSPECIFIED')}]</b> {html.escape(h.get('hypothesis', ''))} — <small>{html.escape(h.get('reasoning', ''))}</small></li>" for h in hyps)
            missing = "".join(f"<li>{html.escape(m)}</li>" for m in a.get("missing_information", []))
            conflicts = "".join(f"<li>⚠️ <b>{html.escape(c.get('topic', ''))}:</b> {html.escape(c.get('conflict', ''))}</li>" for c in a.get("conflicting_conclusions", []))
            ai_tech_html += f"""
            <div class="card" style="border-color:#0284c7;margin-bottom:16px;">
              <div class="card-title">🔬 Deep AI Forensic Evaluation ({html.escape(eng)})</div>
              <p><b>Hypotheses & Root Cause Reasoning:</b></p>
              <ul>{hyp_rows or '<li>No hypotheses provided.</li>'}</ul>
              {f"<p><b>Data Gaps & Missing Information:</b></p><ul>{missing}</ul>" if missing else ""}
              {f"<p><b>Multi-Engine Divergence:</b></p><ul>{conflicts}</ul>" if conflicts else ""}
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MNE Technical Security Operations Report — {html.escape(run_id)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; background: #070e17; color: #e2e8f0; margin: 0; padding: 24px; line-height: 1.5; }}
  .container {{ max-width: 1040px; margin: 0 auto; background: #0f172a; border-radius: 12px; border: 1px solid #1e293b; overflow: hidden; }}
  .header {{ background: #09121d; padding: 28px 32px; border-bottom: 2px solid #0284c7; }}
  .header h1 {{ margin: 0 0 4px 0; font-size: 20px; color: #f8fafc; }}
  .meta {{ font-size: 12px; color: #64748b; display: flex; gap: 20px; flex-wrap: wrap; margin-top: 6px; }}
  .content {{ padding: 32px; }}
  .section-title {{ font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: #38bdf8; margin: 28px 0 12px 0; border-left: 3px solid #0284c7; padding-left: 8px; }}
  .badge {{ display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 700; text-transform: uppercase; }}
  .badge.crit {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); }}
  .badge.high {{ background: rgba(249, 115, 22, 0.2); color: #f97316; border: 1px solid rgba(249, 115, 22, 0.4); }}
  .badge.med {{ background: rgba(234, 179, 8, 0.2); color: #eab308; border: 1px solid rgba(234, 179, 8, 0.4); }}
  .badge.ok {{ background: rgba(34, 197, 94, 0.2); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.4); }}
  .badge.err {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }}
  th, td {{ padding: 8px 10px; border: 1px solid #1e293b; text-align: left; }}
  th {{ background: #09121d; color: #64748b; text-transform: uppercase; font-size: 11px; }}
  td.num {{ text-align: right; }}
  .tech-incident {{ background: #09121d; border: 1px solid #1e293b; border-radius: 8px; padding: 14px; margin-bottom: 12px; }}
  .tech-head {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }}
  .tech-head .title {{ font-size: 14px; font-weight: 600; color: #f8fafc; }}
  .tech-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 6px; font-size: 12px; color: #94a3b8; background: #050b12; padding: 10px; border-radius: 6px; }}
  .cli-box {{ background: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 10px; margin-top: 8px; font-family: monospace; font-size: 11px; color: #38bdf8; overflow-x: auto; }}
  pre {{ margin: 0; }}
  .footer {{ padding: 20px 32px; background: #09121d; border-top: 1px solid #1e293b; font-size: 11px; color: #475569; text-align: center; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>Ministry of National Economy — Technical Security Operations Report</h1>
    <div class="meta">
      <span>Run ID: <b>{html.escape(run_id)}</b></span>
      <span>Window: <b>{html.escape(win_str)}</b></span>
      <span>Total Incidents: <b>{len(incidents)}</b></span>
      <span>Generated: <b>{html.escape(gen_time)}</b></span>
    </div>
  </div>

  <div class="content">
    <div class="section-title">Perimeter & Identity Log Diagnostics</div>
    <table>
      <thead>
        <tr><th>Sensor</th><th>Status</th><th class="num">Events</th><th class="num">Duration</th><th>Diagnostic Code</th><th>Stage Timings</th><th>Errors / Warnings</th></tr>
      </thead>
      <tbody>{diag_rows}</tbody>
    </table>

    {ai_tech_html}

    <div class="section-title">Incident Dossiers & Remediation CLI ({len(incidents)})</div>
    {incident_blocks or "<p class='dim'>No security incidents detected.</p>"}
  </div>

  <div class="footer">
    MNE_Brain Release 2 · Confidential Technical Cybersecurity Report · Internal Operations Only
  </div>
</div>
</body>
</html>"""

    def generate_analysis_html_report(self, analysis: Dict[str, Any]) -> str:
        """Renders a self-contained, publication-grade HTML report for a specific AI assessment."""
        aid = str(analysis.get("analysis_id") or "")
        run_id = str(analysis.get("run_id") or "N/A")
        inc_fp = str(analysis.get("incident_fingerprint") or "")
        target = run_id if run_id != "N/A" else (inc_fp or "N/A")
        provider = str(analysis.get("provider") or "AI Provider")
        engine = str(analysis.get("engine") or "AI").upper()
        model = str(analysis.get("model") or "default")
        status = str(analysis.get("status") or "COMPLETED").upper()
        conf_val = analysis.get("confidence")
        conf = int(conf_val * 100) if isinstance(conf_val, (int, float)) else 75
        gen_time = str(analysis.get("completed_at") or analysis.get("created_at") or datetime.now(timezone.utc).isoformat())

        summary = str(analysis.get("plain_summary") or "No summary provided.")
        hyps = analysis.get("ranked_hypotheses") or []
        systems = analysis.get("affected_systems") or []
        users = analysis.get("affected_users") or []
        branches = analysis.get("affected_branches") or []
        services = analysis.get("affected_services") or []
        obs = analysis.get("observations") or {}
        sup = obs.get("supporting") or [] if isinstance(obs, dict) else []
        contra = obs.get("contradicting") or [] if isinstance(obs, dict) else []
        missing = analysis.get("missing_evidence") or []
        diags = analysis.get("recommended_diagnostics") or []
        imm = analysis.get("immediate_actions") or []
        lt = analysis.get("long_term_actions") or []
        sources = analysis.get("source_references") or []

        hyps_html = ""
        for h in hyps:
            if not isinstance(h, dict):
                continue
            like = str(h.get("likelihood") or "UNKNOWN").upper()
            like_class = like.lower()
            title = html.escape(str(h.get("hypothesis") or ""))
            exp = html.escape(str(h.get("explanation") or ""))
            hyps_html += f"""
            <div class="hypo-card">
              <div class="hypo-head">
                <span class="pill pill-{like_class}">{like}</span>
                <span class="hypo-title">{title}</span>
              </div>
              {f'<p class="hypo-exp">{exp}</p>' if exp else ''}
            </div>
            """
        if not hyps_html:
            hyps_html = "<p class='dim'>No root-cause hypotheses evaluated.</p>"

        sup_html = "".join(f"<li>{html.escape(str(s))}</li>" for s in sup) or "<li>None observed</li>"
        contra_html = "".join(f"<li>{html.escape(str(c))}</li>" for c in contra) or "<li>None observed</li>"
        missing_html = "".join(f"<li>{html.escape(str(m))}</li>" for m in missing) or "<li>No critical operational data gaps recorded</li>"
        diags_html = "".join(f"<div class='code-row'><code>{html.escape(str(d))}</code></div>" for d in diags) or "<p class='dim'>No additional verification commands recommended</p>"
        imm_html = "".join(f"<li>{html.escape(str(a))}</li>" for a in imm) or "<li>No immediate containment steps listed</li>"
        lt_html = "".join(f"<li>{html.escape(str(l))}</li>" for l in lt) or "<li>No long-term hardening steps listed</li>"
        sources_html = "".join(f"<span class='source-badge'>{html.escape(str(s))}</span>" for s in sources) or "<span class='dim'>No explicit sources recorded</span>"

        systems_html = ", ".join(f"<code>{html.escape(str(s))}</code>" for s in systems) or "<span class='dim'>None</span>"
        users_html = ", ".join(html.escape(str(u)) for u in users) or "<span class='dim'>None</span>"
        branches_html = ", ".join(html.escape(str(b)) for b in branches) or "<span class='dim'>None</span>"
        services_html = ", ".join(html.escape(str(s)) for s in services) or "<span class='dim'>None</span>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MNE Security Assessment — {html.escape(aid)}</title>
<style>
  :root {{
    --bg: #0b1320;
    --panel: #111d31;
    --panel-2: #16253d;
    --line: #223755;
    --accent: #38bdf8;
    --accent-dark: #0284c7;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    margin: 0;
    padding: 24px;
    line-height: 1.55;
  }}
  .container {{
    max-width: 1040px;
    margin: 0 auto;
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  }}
  .action-bar {{
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 10px;
    padding: 12px 28px;
    background: #080f1a;
    border-bottom: 1px solid var(--line);
  }}
  .btn {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.15s ease;
    border: 1px solid var(--line);
    background: var(--panel-2);
    color: var(--text);
  }}
  .btn:hover {{
    background: #1c3152;
    border-color: var(--accent);
    color: var(--accent);
  }}
  .btn-primary {{
    background: var(--accent-dark);
    border-color: var(--accent);
    color: #fff;
  }}
  .btn-primary:hover {{
    background: #0369a1;
    color: #fff;
  }}
  .header {{
    background: linear-gradient(135deg, #09121f 0%, #111d31 100%);
    padding: 32px 32px 24px 32px;
    border-bottom: 3px solid var(--accent-dark);
  }}
  .header-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 16px;
  }}
  .header h1 {{
    margin: 0 0 6px 0;
    font-size: 22px;
    color: #f8fafc;
    letter-spacing: -0.5px;
  }}
  .subtitle {{
    font-size: 13px;
    color: var(--accent);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .kpi-row {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1px;
    background: var(--line);
    border-bottom: 1px solid var(--line);
  }}
  .kpi-cell {{
    background: var(--panel);
    padding: 16px;
    text-align: center;
  }}
  .kpi-val {{
    font-size: 20px;
    font-weight: 800;
    color: #f8fafc;
    margin-bottom: 4px;
    font-family: var(--mono);
  }}
  .kpi-lbl {{
    font-size: 11px;
    text-transform: uppercase;
    font-weight: 600;
    color: var(--muted);
    letter-spacing: 0.5px;
  }}
  .content {{
    padding: 32px;
  }}
  .section-title {{
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
    margin: 28px 0 12px 0;
    display: flex;
    align-items: center;
    gap: 8px;
    border-left: 3px solid var(--accent-dark);
    padding-left: 10px;
  }}
  .summary-card {{
    background: var(--panel-2);
    border-left: 4px solid var(--accent-dark);
    padding: 18px 20px;
    border-radius: 0 8px 8px 0;
    font-size: 14.5px;
    line-height: 1.6;
  }}
  .impact-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    margin-top: 10px;
  }}
  .impact-card {{
    background: var(--panel-2);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 14px 16px;
  }}
  .impact-head {{
    font-size: 11px;
    text-transform: uppercase;
    font-weight: 700;
    color: var(--muted);
    margin-bottom: 6px;
  }}
  .impact-val {{
    font-size: 13px;
    color: #f8fafc;
    word-break: break-word;
  }}
  .hypo-card {{
    background: var(--panel-2);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
  }}
  .hypo-head {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }}
  .hypo-title {{
    font-weight: 700;
    font-size: 14.5px;
    color: #f8fafc;
  }}
  .hypo-exp {{
    font-size: 13px;
    color: #cbd5e1;
    margin: 0;
    line-height: 1.55;
  }}
  .pill {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .pill-high {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); }}
  .pill-medium {{ background: rgba(249, 115, 22, 0.2); color: #f97316; border: 1px solid rgba(249, 115, 22, 0.4); }}
  .pill-low {{ background: rgba(234, 179, 8, 0.2); color: #eab308; border: 1px solid rgba(234, 179, 8, 0.4); }}
  .pill-unknown {{ background: rgba(148, 163, 184, 0.2); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.4); }}
  .code-row {{
    background: #080f1a;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 8px 12px;
    margin-bottom: 8px;
    font-family: var(--mono);
    font-size: 12px;
    color: var(--accent);
    overflow-x: auto;
  }}
  ul.fact-list {{
    margin: 6px 0;
    padding-left: 20px;
    font-size: 13px;
    color: #cbd5e1;
  }}
  ul.fact-list li {{
    margin-bottom: 6px;
  }}
  .source-badge {{
    display: inline-block;
    background: #080f1a;
    border: 1px solid var(--line);
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-family: var(--mono);
    color: var(--muted);
    margin: 0 6px 6px 0;
  }}
  .dim {{ color: var(--muted); font-style: italic; }}
  .footer {{
    padding: 20px 32px;
    background: #080f1a;
    border-top: 1px solid var(--line);
    font-size: 12px;
    color: var(--muted);
    text-align: center;
  }}
  @media print {{
    body {{ background: #fff !important; color: #0f172a !important; padding: 0 !important; }}
    .container {{ border: none !important; box-shadow: none !important; max-width: 100% !important; }}
    .action-bar {{ display: none !important; }}
    .header {{ background: #fff !important; color: #0f172a !important; border-bottom: 2px solid #0284c7 !important; padding: 16px 0 !important; }}
    .header h1 {{ color: #0f172a !important; }}
    .subtitle {{ color: #0284c7 !important; }}
    .kpi-row {{ background: #cbd5e1 !important; }}
    .kpi-cell {{ background: #f8fafc !important; }}
    .kpi-val {{ color: #0f172a !important; }}
    .summary-card {{ background: #f0f9ff !important; border-left: 4px solid #0284c7 !important; color: #0f172a !important; }}
    .hypo-card, .impact-card {{ background: #fff !important; border: 1px solid #cbd5e1 !important; color: #0f172a !important; page-break-inside: avoid; }}
    .hypo-title {{ color: #0f172a !important; }}
    .hypo-exp {{ color: #334155 !important; }}
    .code-row {{ background: #f1f5f9 !important; border-color: #cbd5e1 !important; color: #0f172a !important; }}
    ul.fact-list {{ color: #334155 !important; }}
    .footer {{ background: #fff !important; border-top: 1px solid #cbd5e1 !important; color: #64748b !important; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="action-bar">
    <button class="btn btn-primary" onclick="window.print()">🖨️ Print / Save as PDF</button>
    <a class="btn" href="?format=pdf" target="_blank">📥 Download PDF</a>
    <a class="btn" href="?format=json" target="_blank">📦 Export JSON</a>
  </div>

  <div class="header">
    <div class="header-top">
      <div>
        <h1>Ministry of National Economy (MNE)</h1>
        <div class="subtitle">Autonomous AI Cybersecurity Assessment & Root-Cause Analysis</div>
      </div>
      <div style="text-align:right;">
        <span class="pill pill-high" style="font-size:12px;padding:4px 10px;">{status}</span>
      </div>
    </div>
  </div>

  <div class="kpi-row">
    <div class="kpi-cell">
      <div class="kpi-val">{engine}</div>
      <div class="kpi-lbl">Investigation Engine</div>
    </div>
    <div class="kpi-cell">
      <div class="kpi-val">{model}</div>
      <div class="kpi-lbl">AI Model</div>
    </div>
    <div class="kpi-cell">
      <div class="kpi-val" style="color:#38bdf8;">{conf}%</div>
      <div class="kpi-lbl">Confidence Score</div>
    </div>
    <div class="kpi-cell">
      <div class="kpi-val" style="font-size:14px;padding-top:4px;">{html.escape(target[:22])}</div>
      <div class="kpi-lbl">Target Reference</div>
    </div>
  </div>

  <div class="content">
    <div class="section-title">Executive Forensic Assessment Summary</div>
    <div class="summary-card">
      {html.escape(summary)}
    </div>

    <div class="section-title">Scope of Impacted Infrastructure</div>
    <div class="impact-grid">
      <div class="impact-card">
        <div class="impact-head">Affected Systems</div>
        <div class="impact-val">{systems_html}</div>
      </div>
      <div class="impact-card">
        <div class="impact-head">Affected Users</div>
        <div class="impact-val">{users_html}</div>
      </div>
      <div class="impact-card">
        <div class="impact-head">Affected Branches / Networks</div>
        <div class="impact-val">{branches_html}</div>
      </div>
      <div class="impact-card">
        <div class="impact-head">Affected Services / Protocols</div>
        <div class="impact-val">{services_html}</div>
      </div>
    </div>

    <div class="section-title">Ranked Root-Cause Hypotheses ({len(hyps)})</div>
    {hyps_html}

    <div class="section-title">Evidence Corroboration</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));gap:16px;">
      <div class="impact-card">
        <div class="impact-head" style="color:#4ade80;">✅ Supporting Facts</div>
        <ul class="fact-list">{sup_html}</ul>
      </div>
      <div class="impact-card">
        <div class="impact-head" style="color:#f87171;">❌ Contradicting / Excluded Factors</div>
        <ul class="fact-list">{contra_html}</ul>
      </div>
    </div>

    <div class="section-title">Data Gaps & Missing Operational Evidence</div>
    <div class="impact-card">
      <ul class="fact-list">{missing_html}</ul>
    </div>

    <div class="section-title">Recommended Next Verification Checks</div>
    {diags_html}

    <div class="section-title">Recommended Remediation & Hardening Actions</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));gap:16px;">
      <div class="impact-card" style="border-left:3px solid #f97316;">
        <div class="impact-head" style="color:#fb923c;">⚡ Immediate Containment</div>
        <ul class="fact-list">{imm_html}</ul>
      </div>
      <div class="impact-card" style="border-left:3px solid #38bdf8;">
        <div class="impact-head" style="color:#38bdf8;">🛡️ Long-Term Hardening</div>
        <ul class="fact-list">{lt_html}</ul>
      </div>
    </div>

    <div class="section-title">Ground-Truth Sources Cited ({len(sources)})</div>
    <div style="margin-top:8px;">
      {sources_html}
    </div>
  </div>

  <div class="footer">
    MNE_Brain Release 2 · Confidential Cybersecurity Intelligence · Analysis ID: {html.escape(aid)} · Generated {html.escape(gen_time)}
  </div>
</div>
</body>
</html>"""

    def compile_analysis_pdf_report(self, analysis: Dict[str, Any]) -> bytes:
        """Compiles a publication-grade executive PDF document for an AI assessment using ReportLab."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=2,
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=8,
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0284c7"),
            spaceBefore=10,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#334155"),
        )
        summary_style = ParagraphStyle(
            "SummaryBox",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#0f172a"),
            backColor=colors.HexColor("#f0f9ff"),
            borderPadding=6,
            spaceBefore=4,
            spaceAfter=6,
        )
        code_style = ParagraphStyle(
            "CodeBlock",
            parent=styles["Code"],
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#0f172a"),
            backColor=colors.HexColor("#f1f5f9"),
            borderPadding=4,
            spaceBefore=2,
            spaceAfter=3,
        )

        elements = []
        elements.append(Paragraph("Ministry of National Economy (MNE)", title_style))
        elements.append(Paragraph("Autonomous Cybersecurity AI Forensic Assessment Report", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=8))

        aid = str(analysis.get("analysis_id") or "")
        engine = str(analysis.get("engine") or "AI").upper()
        model = str(analysis.get("model") or "default")
        status = str(analysis.get("status") or "COMPLETED").upper()
        conf_val = analysis.get("confidence")
        conf = int(conf_val * 100) if isinstance(conf_val, (int, float)) else 75
        target = str(analysis.get("run_id") or analysis.get("incident_fingerprint") or "N/A")

        meta_data = [
            [Paragraph("<b>Engine / Model:</b>", body_style), Paragraph(f"{engine} ({model})", body_style),
             Paragraph("<b>Status / Confidence:</b>", body_style), Paragraph(f"{status} ({conf}%)", body_style)],
            [Paragraph("<b>Analysis ID:</b>", body_style), Paragraph(aid, body_style),
             Paragraph("<b>Target Reference:</b>", body_style), Paragraph(target, body_style)],
        ]
        t = Table(meta_data, colWidths=[100, 170, 110, 160])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 8))

        # Executive Summary
        elements.append(Paragraph("Executive Assessment Summary", h2_style))
        elements.append(Paragraph(html.escape(str(analysis.get("plain_summary") or "No summary provided.")), summary_style))

        # Hypotheses
        hyps = analysis.get("ranked_hypotheses") or []
        if hyps:
            elements.append(Paragraph("Ranked Root-Cause Hypotheses", h2_style))
            for h in hyps:
                if not isinstance(h, dict):
                    continue
                like = str(h.get("likelihood") or "UNKNOWN").upper()
                h_text = html.escape(str(h.get("hypothesis") or ""))
                exp_text = html.escape(str(h.get("explanation") or ""))
                elements.append(Paragraph(f"<b>[{like}]</b> {h_text}", styles["Heading3"]))
                if exp_text:
                    elements.append(Paragraph(exp_text, body_style))
                elements.append(Spacer(1, 3))

        # Impact
        systems = analysis.get("affected_systems") or []
        users = analysis.get("affected_users") or []
        branches = analysis.get("affected_branches") or []
        services = analysis.get("affected_services") or []
        if systems or users or branches or services:
            elements.append(Paragraph("Scope of Impacted Infrastructure", h2_style))
            impact_data = [
                [Paragraph("<b>Affected Systems:</b>", body_style), Paragraph(", ".join(html.escape(str(s)) for s in systems[:6]) or "None", body_style)],
                [Paragraph("<b>Affected Users:</b>", body_style), Paragraph(", ".join(html.escape(str(u)) for u in users[:4]) or "None", body_style)],
                [Paragraph("<b>Affected Branches/Nets:</b>", body_style), Paragraph(", ".join(html.escape(str(b)) for b in branches[:4]) or "None", body_style)],
                [Paragraph("<b>Affected Services:</b>", body_style), Paragraph(", ".join(html.escape(str(s)) for s in services[:4]) or "None", body_style)],
            ]
            it = Table(impact_data, colWidths=[130, 410])
            it.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            elements.append(it)
            elements.append(Spacer(1, 6))

        # Observations
        obs = analysis.get("observations") or {}
        sup = obs.get("supporting") or [] if isinstance(obs, dict) else []
        contra = obs.get("contradicting") or [] if isinstance(obs, dict) else []
        if sup or contra:
            elements.append(Paragraph("Evidence Corroboration", h2_style))
            for s in sup[:5]:
                elements.append(Paragraph(f"• <b>[Supporting]</b> {html.escape(str(s))}", body_style))
            for c in contra[:3]:
                elements.append(Paragraph(f"• <b>[Contradicting]</b> {html.escape(str(c))}", body_style))
            elements.append(Spacer(1, 4))

        # Recommended Diagnostics
        diags = analysis.get("recommended_diagnostics") or []
        if diags:
            elements.append(Paragraph("Recommended Next Verification Checks", h2_style))
            for d in diags[:4]:
                elements.append(Paragraph(html.escape(str(d)), code_style))

        # Remediation
        imm = analysis.get("immediate_actions") or []
        lt = analysis.get("long_term_actions") or []
        if imm or lt:
            elements.append(Paragraph("Recommended Remediation & Hardening", h2_style))
            for a in imm[:4]:
                elements.append(Paragraph(f"⚡ <b>[Immediate Containment]</b> {html.escape(str(a))}", body_style))
            for l in lt[:4]:
                elements.append(Paragraph(f"🛡️ <b>[Long-Term Hardening]</b> {html.escape(str(l))}", body_style))
            elements.append(Spacer(1, 4))

        doc.build(elements)
        return buffer.getvalue()
