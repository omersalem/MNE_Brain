from core.security_review.cli import build_parser, run_security_pipeline

def test_cli_parser_options():
    parser = build_parser()
    args = parser.parse_args(["--run-now"])
    assert args.run_now is True
    assert args.dry_run is False

    args_dry = parser.parse_args(["--dry-run"])
    assert args_dry.dry_run is True

    args_rem = parser.parse_args(["--remediate", "MNE-SEC-20260906-01"])
    assert args_rem.remediate == "MNE-SEC-20260906-01"

def test_run_security_pipeline_dry_run():
    # Dry run should execute without calling SMTP server
    result = run_security_pipeline(dry_run=True, send_email=False)
    assert result is not None
    assert "html_report" in result
    assert "pdf_report" in result
    assert "incidents" in result
    assert "collectors" in result
