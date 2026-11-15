import json
import tempfile
import unittest
from pathlib import Path

from sk_llm_eval import blind_judge


class TestBlindJudge(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ids = ["long_text-001", "long_text-003"]
            for model in ("model-a", "model-b"):
                with open(tmp / f"{model}.jsonl", "w", encoding="utf-8") as f:
                    for i in ids:
                        f.write(json.dumps({"id": i, "answer": f"{model} {i}"}) + "\n")
            run = tmp / "run"
            rc = blind_judge.main(["prepare", str(tmp / "model-a.jsonl"), str(tmp / "model-b.jsonl"),
                                   "--out-dir", str(run), "--seed", "1", "--only", *ids])
            self.assertEqual(rc, 0)

            lines = [json.loads(x) for x in open(run / "judge_in.jsonl", encoding="utf-8")]
            self.assertEqual(len(lines), 4)
            for line in lines:
                self.assertNotIn("model-", line["key"])  # the judge never sees model names
                self.assertTrue(line["rubric"])
            self.assertIn("judge_in.jsonl", (run / "PROMPT.md").read_text(encoding="utf-8"))

            # a fake judge: model-a gets 8 everywhere, model-b gets 3
            key = json.loads((run / "key.json").read_text(encoding="utf-8"))
            with open(run / "judge_out.jsonl", "w", encoding="utf-8") as f:
                for k, model in key.items():
                    f.write(json.dumps({"key": k, "score": 8 if model == "model-a" else 3, "reason": "r"}) + "\n")

            out = tmp / "judge"
            self.assertEqual(blind_judge.main(["merge", str(run), "--results-dir", str(out)]), 0)
            a = [json.loads(x) for x in open(out / "model-a.opus-judge.jsonl", encoding="utf-8")]
            b = [json.loads(x) for x in open(out / "model-b.opus-judge.jsonl", encoding="utf-8")]
            self.assertEqual([r["id"] for r in a], ids)
            self.assertTrue(all(r["score"] == 8 for r in a))
            self.assertTrue(all(r["score"] == 3 for r in b))

            # anchors are compared, not overwritten
            (run / "judge_out.jsonl").write_text(
                "".join(json.dumps({"key": k, "score": 0, "reason": "x"}) + "\n" for k in key), encoding="utf-8")
            blind_judge.main(["merge", str(run), "--results-dir", str(out), "--anchors", "model-a", "model-b"])
            a2 = [json.loads(x) for x in open(out / "model-a.opus-judge.jsonl", encoding="utf-8")]
            self.assertEqual(a, a2)


if __name__ == "__main__":
    unittest.main()
