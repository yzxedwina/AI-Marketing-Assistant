#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.ai_contracts import build_opportunity_evidence, structured_output_format

parser = argparse.ArgumentParser(description="构建 AI 请求预览，不调用模型")
parser.add_argument("--candidate-id", default="MKT-003")
parser.add_argument("--scoring-file", type=Path, default=ROOT / "mock_data" / "scoring_usr001.json")
parser.add_argument("--output", type=Path)
args = parser.parse_args()
scoring = json.loads(args.scoring_file.read_text(encoding="utf-8"))
request = {"instructions_file":"config/prompts/opportunity_explanation_system.md",
           "input":build_opportunity_evidence(scoring, args.candidate_id),
           "text":{"format":structured_output_format("opportunity_explanation")}, "store":False}
rendered = json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
args.output.write_text(rendered, encoding="utf-8") if args.output else print(rendered, end="")
