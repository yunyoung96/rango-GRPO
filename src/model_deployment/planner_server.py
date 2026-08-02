#!/usr/bin/env python3
"""Persistent planner 서버 — planner LLM(Qwen-7B 등)을 한 번 로드하고 /plan(HTTP)로 분해 후보 제공.

run_all은 정리별 subprocess라, searcher가 in-process로 planner를 로드하면 정리마다 재로드된다
(7B bf16 ~30-60s × 200정리 = 낭비, 32B면 치명적). 이 서버로 **한 번만 로드해 공유** →
정리 재로드 0 + 여러 워커(w2)가 같은 서버를 써 워커별 중복 로드도 없앤다(baseline과 공정 w2 가능).

사용: CUDA_VISIBLE_DEVICES=1 python3 src/model_deployment/planner_server.py <model> <port> [4bit]
  예: ... planner_server.py Qwen/Qwen2.5-Coder-7B-Instruct 8130
GPU는 CUDA_VISIBLE_DEVICES로 지정(GPU1 전용, GPU0 금지). ★OCaml 무관.
"""
import os
import sys
import json
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402
from model_deployment.planner_client import PlannerClient, PlannerConf  # noqa: E402


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "Qwen/Qwen2.5-Coder-7B-Instruct"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8130
    load_4bit = len(sys.argv) > 3 and sys.argv[3] == "4bit"
    # 학습된 opener: PLANNER_ADAPTER(어댑터 경로) + PLANNER_OPENER=1(학습 프롬프트)
    adapter = os.environ.get("PLANNER_ADAPTER") or None
    opener_mode = os.environ.get("PLANNER_OPENER", "0") == "1"
    select_mode = os.environ.get("PLANNER_SELECT", "0") == "1"
    tac_mode = os.environ.get("PLANNER_TAC", "0") == "1"
    pc = PlannerClient(PlannerConf(model_name=model, load_4bit=load_4bit, device="cuda:0",
                                   init_adapter=adapter, opener_mode=opener_mode,
                                   select_mode=select_mode, tac_mode=tac_mode))
    pc._ensure_loaded()
    lock = threading.Lock()   # GPU generate 직렬화(w2 동시요청 대비)
    print(f"[planner_server] READY model={model} port={port}", flush=True)

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n)) if n else {}
                with lock:
                    plan = pc.plan(body.get("goal", ""), body.get("premises"), body.get("proofs"))
                payload = json.dumps({"plan": plan}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except Exception as e:
                try:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(str(e).encode())
                except Exception:
                    pass

        def do_GET(self):   # health check
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *a):
            pass

    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()


if __name__ == "__main__":
    main()
