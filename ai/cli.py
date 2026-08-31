"""Command-line entry point for the MVP baseline."""
import argparse
import json
import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
from ai.pipeline.baseline import BaselineAuditPipeline
from ai.providers.openai_provider import OpenAIResponsesProvider
from ai.schemas.audit_schema import AuditScreen, LLMAuditRequest

def build_parser() -> argparse.ArgumentParser:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="darkaudit")
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="Audit 1 to 5 screenshots")
    audit.add_argument("--image", action="append", required=True, type=Path)
    audit.add_argument("--flow-step", action="append", required=True)
    audit.add_argument("--screen-id", action="append")
    audit.add_argument("--audit-id", default=None)
    audit.add_argument("--model", default=os.getenv("DARKAUDIT_MODEL"))
    return parser

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if len(args.image) != len(args.flow_step): raise SystemExit("--image and --flow-step counts must match")
    if not 1 <= len(args.image) <= 5: raise SystemExit("Provide 1 to 5 images")
    ids = args.screen_id or [f"screen_{index:02d}" for index in range(1, len(args.image) + 1)]
    if len(ids) != len(args.image): raise SystemExit("--screen-id count must match --image count")
    if not args.model: raise SystemExit("Set --model or DARKAUDIT_MODEL")
    request = LLMAuditRequest(args.audit_id or f"audit_{uuid.uuid4().hex[:12]}",
                              tuple(AuditScreen(sid, step, image) for sid, step, image in zip(ids, args.flow_step, args.image)))
    result = BaselineAuditPipeline(OpenAIResponsesProvider(args.model)).analyze(request)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__": raise SystemExit(main())
