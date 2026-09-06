import io
import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

import jinja2
from core.connectors.security.models import (
    CollectorResult,
    Incident,
    SeverityLevel,
)

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
        self.smtp_host = os.getenv("MNE_SMTP_HOST", "172.23.71.36")
        self.smtp_port = int(os.getenv("MNE_SMTP_PORT", "25"))
        self.smtp_user = os.getenv("MNE_SMTP_USER", "")
        self.smtp_password = os.getenv("MNE_SMTP_PASSWORD", "")
        self.smtp_sender = os.getenv("MNE_SMTP_SENDER", "security-alert@mne.gov.ps")
        self.default_recipients = [
            "omersalem@mne.gov.ps",
            "omersalem2008@gmail.com",
        ]

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
            fontSize=13,
            leading=16,
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

        elements = []
        # Header
        elements.append(Paragraph("Ministry of National Economy (MNE)", title_style))
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        elements.append(Paragraph(f"Daily Cyber Threat & Risk Intelligence Briefing | Generated: {today_str}", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=12))

        # Executive Metrics Summary
        if incidents:
            crit_n = sum(1 for i in incidents if i.severity == SeverityLevel.CRITICAL)
            high_n = sum(1 for i in incidents if i.severity == SeverityLevel.HIGH)
            med_n = sum(1 for i in incidents if i.severity == SeverityLevel.MEDIUM)
            summary_data = [
                ["Metric", "Count", "Severity Status"],
                ["Critical Risks", str(crit_n), "IMMEDIATE ATTENTION" if crit_n > 0 else "Clear"],
                ["High Risks", str(high_n), "Action Required" if high_n > 0 else "Clear"],
                ["Medium Risks", str(med_n), "Monitor" if med_n > 0 else "Clear"],
            ]
            summary_table = Table(summary_data, colWidths=[200, 80, 200])
            summary_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            elements.append(Paragraph("Executive Summary & Risk Metrics", h2_style))
            elements.append(summary_table)
            elements.append(Spacer(1, 12))

            elements.append(Paragraph("Detailed Security Incidents & Actionable Remediations", h2_style))
            for inc in incidents:
                inc_title = f"[{inc.severity.value}] {inc.incident_id} — {inc.title}"
                elements.append(Paragraph(f"<b>{inc_title}</b>", styles["Heading3"]))
                details_p = f"Device: {inc.source_device} | Attacker: {inc.attacker_ip or 'N/A'} | Target: {inc.target or 'N/A'} | Attempts: {inc.event_count}"
                elements.append(Paragraph(details_p, styles["Normal"]))
                elements.append(Paragraph(f"Description: {inc.description}", styles["Normal"]))

                if inc.remediation_cli:
                    elements.append(Paragraph("<b>CLI Containment Commands:</b>", styles["Normal"]))
                    cli_text = "<br/>".join(inc.remediation_cli)
                    elements.append(Paragraph(cli_text, code_style))

                if inc.remediation_mode_b_command:
                    elements.append(Paragraph(f"<i>Mode B Remediation Command:</i> {inc.remediation_mode_b_command}", subtitle_style))
                elements.append(Spacer(1, 10))
        else:
            elements.append(Paragraph("Report Summary: All security and identity devices operating normally.", styles["Normal"]))

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
