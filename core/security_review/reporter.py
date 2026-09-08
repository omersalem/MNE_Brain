import io
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Tuple

import jinja2
from core.connectors.security.models import (
    CollectorResult,
    CollectorStatus,
    Incident,
    SeverityLevel,
)
from core.security_review.config import SecurityAgentConfig

logger = logging.getLogger(__name__)


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
        incidents: List[Incident],
        collectors: List[CollectorResult],
    ) -> str:
        """Renders the responsive HTML email template using Jinja2."""
        template = self.jinja_env.get_template("report.html.j2")
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        critical_count = sum(1 for i in incidents if i.severity == SeverityLevel.CRITICAL)
        high_count = sum(1 for i in incidents if i.severity == SeverityLevel.HIGH)
        medium_count = sum(1 for i in incidents if i.severity == SeverityLevel.MEDIUM)

        return template.render(
            generated_at=now_str,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            collectors=collectors,
            incidents=incidents,
        )

    def compile_pdf_report(
        self,
        html_content: str,
        incidents: Optional[List[Incident]] = None,
        collectors: Optional[List[CollectorResult]] = None,
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
        inc_list = incidents or []
        crit_n = sum(1 for i in inc_list if i.severity == SeverityLevel.CRITICAL)
        high_n = sum(1 for i in inc_list if i.severity == SeverityLevel.HIGH)
        med_n = sum(1 for i in inc_list if i.severity == SeverityLevel.MEDIUM)

        col_list = collectors or []
        success_cols = sum(1 for c in col_list if c.status == CollectorStatus.SUCCESS)
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
                status_str = col.status.value
                if col.status != CollectorStatus.SUCCESS:
                    failed_count += 1
                diag = (col.error_message or "Healthy log synchronization")[:45]
                health_rows.append([col.device_name, status_str, str(len(col.events)), f"{col.collection_duration_seconds}s", diag])

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
                inc_title = f"[{inc.severity.value}] {inc.incident_id} — {inc.title}"
                elements.append(Paragraph(f"<b>{inc_title}</b>", styles["Heading3"]))
                details_p = f"Device: <b>{inc.source_device}</b> | Attacker: <b>{inc.attacker_ip or 'N/A'}</b> | Target: <b>{inc.target or 'N/A'}</b> | Attempts: <b>{inc.event_count}</b>"
                elements.append(Paragraph(details_p, styles["Normal"]))
                elements.append(Paragraph(f"Description: {inc.description}", styles["Normal"]))

                if inc.remediation_cli:
                    elements.append(Paragraph("<b>CLI Containment Playbook:</b>", styles["Normal"]))
                    cli_text = "<br/>".join(inc.remediation_cli)
                    elements.append(Paragraph(cli_text, code_style))

                if inc.remediation_mode_b_command:
                    elements.append(Paragraph(f"<i>Mode B Remediation:</i> {inc.remediation_mode_b_command}", subtitle_style))
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
