"""Real-model test. Needs Ollama running with the model pulled.
Run:  python tests/live_check.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import scopeguard as sg

ROOT = os.path.join(os.path.dirname(__file__), "..", "samples")


def run(name):
    text = open(os.path.join(ROOT, name), encoding="utf-8").read()
    res = sg.analyze(text)
    print(f"\n== {name} | model={res['model']} | score={res['score']} ({res['level']}) | "
          f"verified flags={len(res['risk_flags'])} | removed={res['dropped_flags']}")
    for f in res["risk_flags"]:
        print(f"  [{f['severity']}] {f['category']}: \"{f['quote']}\"")
    return res


vague = run("vague_brief.txt")
clear = run("clear_brief.txt")
print("\nCHECK 1 vague brief has >=2 verified flags:", "PASS" if len(vague["risk_flags"]) >= 2 else "FAIL")
print("CHECK 2 vague score > clear score:", "PASS" if vague["score"] > clear["score"] else "FAIL")
