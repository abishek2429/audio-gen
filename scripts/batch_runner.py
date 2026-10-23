#!/usr/bin/env python3
"""Batch Runner for IncuBrix AI Background Music Engine.

Submits test inputs to the live API, polls to completion, downloads all generated
audio and metadata assets, runs independent DSP/audio validations, and generates
a consolidated test report.
"""
import argparse
import glob
import io
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional, Tuple

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.audio.validator import validate_audio_pack

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("batch_runner")


def http_post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, Any]]:
    """Submit HTTP POST request with JSON payload."""
    data = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return e.code, parsed


def http_get_json(url: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, Any]]:
    """Submit HTTP GET request."""
    req_headers = {}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return e.code, parsed


def download_file(url: str, dest_path: str, api_base: str):
    """Download a file from an absolute or relative URL."""
    if not url.startswith("http://") and not url.startswith("https://"):
        full_url = urllib.parse.urljoin(api_base, url)
    else:
        full_url = url

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    urllib.request.urlretrieve(full_url, dest_path)


class BatchRunner:
    """Orchestrates batch execution of test cases against the IncuBrix API."""

    def __init__(self, api_base: str, output_dir: str, timeout: int = 120, poll_interval: float = 1.0):
        self.api_base = api_base.rstrip("/")
        self.output_dir = os.path.abspath(output_dir)
        self.timeout = timeout
        self.poll_interval = poll_interval
        os.makedirs(self.output_dir, exist_ok=True)

    def check_health(self) -> bool:
        """Verify API liveness."""
        try:
            status, data = http_get_json(f"{self.api_base}/health")
            return status == 200 and data.get("status") == "ok"
        except Exception as e:
            logger.error("Health check failed on %s: %s", self.api_base, e)
            return False

    def run_case(self, case_name: str, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test case from input payload."""
        case_dir = os.path.join(self.output_dir, case_name)
        os.makedirs(case_dir, exist_ok=True)

        # Save input request
        input_file = os.path.join(case_dir, "input_request.json")
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(input_payload, f, indent=2)

        idempotency_key = f"batch-{case_name}-{int(time.time())}"
        headers = {
            "Idempotency-Key": idempotency_key,
            "X-Correlation-Id": f"corr-{case_name}",
        }

        t0 = time.time()
        logger.info("Executing [%s] -> POST %s/api/v1/music/jobs", case_name, self.api_base)
        status_code, post_resp = http_post_json(
            f"{self.api_base}/api/v1/music/jobs",
            input_payload,
            headers=headers,
        )
        post_elapsed = time.time() - t0

        # Save initial response
        with open(os.path.join(case_dir, "initial_response.json"), "w", encoding="utf-8") as f:
            json.dump({"status_code": status_code, "body": post_resp, "elapsed_s": post_elapsed}, f, indent=2)

        # Expected rejection cases (HTTP 400 or 409)
        expected_rejections = ["sections_too_close", "section_after_end", "unsupported_fields"]
        is_expected_rejection = any(sub in case_name for sub in expected_rejections)

        if is_expected_rejection:
            if status_code == 400:
                logger.info("Case [%s] correctly rejected invalid request with HTTP 400 (%s)", case_name, post_resp.get("error", {}).get("code"))
                return {
                    "case_name": case_name,
                    "status": "PASSED",
                    "http_status": 400,
                    "expected_rejection": True,
                    "error_code": post_resp.get("error", {}).get("code"),
                    "error_message": post_resp.get("error", {}).get("message"),
                    "details": post_resp.get("error", {}).get("details"),
                    "elapsed_s": round(post_elapsed, 3),
                    "summary": "Correctly rejected invalid input at request boundary.",
                }
            else:
                logger.error("Case [%s] was expected to fail with HTTP 400, but got %d", case_name, status_code)
                return {
                    "case_name": case_name,
                    "status": "FAILED",
                    "http_status": status_code,
                    "expected_rejection": True,
                    "reason": f"Expected HTTP 400 validation error, got {status_code}",
                    "elapsed_s": round(post_elapsed, 3),
                }

        # Otherwise, expect HTTP 202
        if status_code != 202:
            logger.error("Case [%s] submission failed: HTTP %d: %s", case_name, status_code, post_resp)
            return {
                "case_name": case_name,
                "status": "FAILED",
                "http_status": status_code,
                "reason": f"Submission rejected: {post_resp}",
                "elapsed_s": round(post_elapsed, 3),
            }

        job_id = post_resp.get("job_id")
        logger.info("Case [%s] accepted with job_id: %s. Polling...", case_name, job_id)

        # Poll status
        poll_start = time.time()
        final_job: Dict[str, Any] = {}
        while time.time() - poll_start < self.timeout:
            time.sleep(self.poll_interval)
            c, get_resp = http_get_json(f"{self.api_base}/api/v1/jobs/{job_id}")
            if c != 200:
                logger.warning("Polling error HTTP %d: %s", c, get_resp)
                continue

            job_status = get_resp.get("status")
            progress = get_resp.get("progress", 0)
            logger.info("  [%s] Status: %s (Progress: %d%%)", case_name, job_status, progress)

            if job_status in ("succeeded", "failed"):
                final_job = get_resp
                break

        if not final_job:
            return {
                "case_name": case_name,
                "job_id": job_id,
                "status": "FAILED",
                "reason": f"Job timed out after {self.timeout}s without terminal status",
                "elapsed_s": round(time.time() - t0, 3),
            }

        # Save final job state
        with open(os.path.join(case_dir, "final_job_status.json"), "w", encoding="utf-8") as f:
            json.dump(final_job, f, indent=2)

        if final_job.get("status") == "failed":
            err = final_job.get("error", {})
            return {
                "case_name": case_name,
                "job_id": job_id,
                "status": "FAILED",
                "reason": f"Job failed in worker: [{err.get('code')}] {err.get('message')}",
                "error": err,
                "elapsed_s": round(time.time() - t0, 3),
            }

        # Download Assets
        result_urls = final_job.get("result", {})
        mix_wav_url = result_urls.get("mix_wav")
        manifest_url = result_urls.get("manifest")
        stems_urls = result_urls.get("stems", {})
        ducked_url = result_urls.get("mix_ducked_wav")

        if mix_wav_url:
            download_file(mix_wav_url, os.path.join(case_dir, "mix.wav"), self.api_base)
        if manifest_url:
            download_file(manifest_url, os.path.join(case_dir, "music_manifest.json"), self.api_base)
        if ducked_url:
            download_file(ducked_url, os.path.join(case_dir, "mix_ducked.wav"), self.api_base)

        stems_dir = os.path.join(case_dir, "stems")
        for stem_name, s_url in stems_urls.items():
            download_file(s_url, os.path.join(stems_dir, f"{stem_name}.wav"), self.api_base)

        # Independent Audio Pack Validation
        requested_dur = float(input_payload.get("duration_s", 30.0))
        target_lufs = float(input_payload.get("output", {}).get("target_lufs", -16.0))
        val_report = validate_audio_pack(case_dir, requested_duration_s=requested_dur, target_lufs=target_lufs)

        # Save independent validation report
        with open(os.path.join(case_dir, "independent_validation_report.json"), "w", encoding="utf-8") as f:
            json.dump(val_report.model_dump(), f, indent=2)

        # Inspect Manifest
        manifest_data = final_job.get("manifest") or {}
        manifest_warnings = manifest_data.get("warnings", [])

        # Hard-case specific validation rules
        case_passed = val_report.overall_passed
        special_notes = []

        if "contradictory" in case_name:
            has_contra_warn = any("contradictory" in w.lower() for w in manifest_warnings)
            if not has_contra_warn:
                case_passed = False
                special_notes.append("Expected contradiction warning in manifest, but none was found.")
            else:
                special_notes.append("Confirmed contradictory warning emitted.")

        if "artist" in case_name:
            has_artist_warn = any("artist" in w.lower() or "copyright" in w.lower() for w in manifest_warnings)
            if not has_artist_warn:
                case_passed = False
                special_notes.append("Expected artist copyright protection warning in manifest, but none was found.")
            else:
                special_notes.append("Confirmed artist protection warning emitted.")

        if "vocal" in case_name:
            has_vocal_warn = any("vocal" in w.lower() or "instrumental" in w.lower() for w in manifest_warnings)
            if not has_vocal_warn:
                case_passed = False
                special_notes.append("Expected vocal suppression warning in manifest, but none was found.")
            else:
                special_notes.append("Confirmed vocal suppression warning emitted; output strictly instrumental.")

        if "non_english" in case_name:
            has_lang_warn = any("non-english" in w.lower() for w in manifest_warnings)
            if not has_lang_warn:
                case_passed = False
                special_notes.append("Expected non-English prompt handling warning in manifest, but none was found.")
            else:
                special_notes.append("Confirmed non-English prompt normalized without error.")

        elapsed_total = round(time.time() - t0, 3)
        cost_usd = manifest_data.get("cost_usd", 0.0)

        gates_summary = {k: v.passed for k, v in val_report.gates.items()}
        logger.info("Case [%s] finished with overall_passed=%s in %.2fs", case_name, case_passed, elapsed_total)

        return {
            "case_name": case_name,
            "job_id": job_id,
            "status": "PASSED" if case_passed else "FAILED",
            "overall_passed": case_passed,
            "elapsed_s": elapsed_total,
            "cost_usd": cost_usd,
            "gates": gates_summary,
            "audio_metrics": manifest_data.get("audio_metrics", {}),
            "warnings": manifest_warnings,
            "notes": " ".join(special_notes) if special_notes else "All Must-Have gates verified.",
        }

    def run_all(self, test_files: List[str]) -> Dict[str, Any]:
        """Run all specified test case JSON files."""
        results = []
        for file_path in test_files:
            case_name = os.path.splitext(os.path.basename(file_path))[0]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                res = self.run_case(case_name, payload)
                results.append(res)
            except Exception as e:
                logger.exception("Failed to execute case file %s: %s", file_path, e)
                results.append({
                    "case_name": case_name,
                    "status": "FAILED",
                    "reason": f"Execution error: {e}",
                })

        passed_count = sum(1 for r in results if r.get("status") == "PASSED")
        failed_count = sum(1 for r in results if r.get("status") == "FAILED")

        summary = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_cases": len(results),
            "passed": passed_count,
            "failed": failed_count,
            "results": results,
        }

        # Save consolidated JSON report
        report_json = os.path.join(self.output_dir, "consolidated_report.json")
        with open(report_json, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Generate Markdown Summary
        self.generate_markdown_summary(summary)

        return summary

    def generate_markdown_summary(self, summary: Dict[str, Any]):
        """Generate human-readable test summary markdown."""
        md_file = os.path.join(self.output_dir, "test_summary.md")
        lines = [
            "# IncuBrix AI Background Music Engine — Automated Test Summary",
            "",
            f"**Execution Timestamp:** {summary['timestamp']}  ",
            f"**Total Cases:** {summary['total_cases']} | **Passed:** {summary['passed']} | **Failed:** {summary['failed']}  ",
            "",
            "## Results Table",
            "",
            "| Case Name | Status | Elapsed | Cost | LUFS | True Peak | Gates | Warnings & Notes |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
        ]

        for r in summary["results"]:
            case = r.get("case_name", "unknown")
            status = r.get("status", "UNKNOWN")
            status_badge = "✅ PASS" if status == "PASSED" else "❌ FAIL"
            elapsed = f"{r.get('elapsed_s', 0):.2f}s"
            cost = f"${r.get('cost_usd', 0):.4f}" if "cost_usd" in r else "--"
            metrics = r.get("audio_metrics", {})
            lufs = f"{metrics.get('integrated_lufs', '--')} LUFS" if metrics else "--"
            tp = f"{metrics.get('true_peak_dbtp', '--')} dBTP" if metrics else "--"

            gates = r.get("gates", {})
            passed_gates = f"{sum(1 for v in gates.values() if v)}/{len(gates)}" if gates else "--"
            notes = r.get("notes") or r.get("reason") or r.get("summary") or "--"
            if r.get("warnings"):
                notes += " (Warnings: " + "; ".join(r["warnings"]) + ")"

            lines.append(f"| `{case}` | {status_badge} | {elapsed} | {cost} | {lufs} | {tp} | {passed_gates} | {notes} |")

        lines.append("")
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("Saved Markdown summary to %s", md_file)


def main():
    parser = argparse.ArgumentParser(description="IncuBrix Batch Test Runner")
    parser.add_argument("--inputs-dir", default="test_inputs", help="Directory containing test JSON files")
    parser.add_argument("--input-file", default=None, help="Specific test JSON file to run")
    parser.add_argument("--api-url", default="http://localhost:8000", help="IncuBrix API base URL")
    parser.add_argument("--output-dir", default="artifacts/test_results", help="Directory to save test outputs")
    parser.add_argument("--timeout", type=int, default=120, help="Per-job polling timeout in seconds")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds")

    args = parser.parse_args()

    runner = BatchRunner(
        api_base=args.api_url,
        output_dir=args.output_dir,
        timeout=args.timeout,
        poll_interval=args.poll_interval,
    )

    if not runner.check_health():
        logger.error("API at %s is not healthy or reachable. Make sure the server is running.", args.api_url)
        sys.exit(1)

    if args.input_file:
        files = [args.input_file]
    else:
        files = sorted(glob.glob(os.path.join(args.inputs_dir, "*.json")))

    if not files:
        logger.error("No test input JSON files found in %s", args.inputs_dir)
        sys.exit(1)

    logger.info("Running batch runner on %d test case(s)...", len(files))
    summary = runner.run_all(files)
    logger.info("Batch run complete! Passed: %d / %d", summary["passed"], summary["total_cases"])
    if summary["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
