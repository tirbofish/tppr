#!/usr/bin/env python3
# Generate a markdown security summary from Bandit JSON and CodeQL SARIF files.
import json
import glob
import os
import re
from datetime import datetime, timezone
from pathlib import Path

REPORT = Path("security_report.md")
BANDIT_JSON = "bandit-report.json"
CODEQL_GLOB = "codeql-*.sarif"


def repo_root_name():
    return os.path.basename(os.getcwd())


def normalize_uri(uri):
    # CodeQL local SARIF sometimes prefixes the artifact URI with the database
    # source archive path (e.g. codeql-db-python/src/D_/REPO/...).  Strip it.
    root = repo_root_name()
    marker = root + "/"
    idx = uri.find(marker)
    if idx != -1:
        return uri[idx + len(marker):]
    marker = root + "\\"
    idx = uri.find(marker)
    if idx != -1:
        return uri[idx + len(marker):]
    return uri


def bandit_findings():
    if not os.path.exists(BANDIT_JSON):
        return []
    with open(BANDIT_JSON, encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for r in data.get("results", []):
        out.append({
            "tool": "Bandit",
            "severity": (r.get("issue_severity") or "UNKNOWN").capitalize(),
            "file": r.get("filename", ""),
            "line": r.get("line_number", 0),
            "rule": r.get("test_id", ""),
            "desc": r.get("issue_text", ""),
        })
    return out


def codeql_findings():
    findings = []
    for path in sorted(glob.glob(CODEQL_GLOB)):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for run in data.get("runs", []):
            rules = {r["id"]: r for r in run.get("tool", {}).get("driver", {}).get("rules", [])}
            seen = set()
            for res in run.get("results", []):
                rule = rules.get(res.get("ruleId", ""), {})
                props = rule.get("properties", {})
                sev_score = props.get("security-severity", 0)
                try:
                    sev_score = float(sev_score)
                except Exception:
                    sev_score = 0.0
                if sev_score >= 7.0:
                    severity = "High"
                elif sev_score >= 4.0:
                    severity = "Medium"
                else:
                    severity = "Low"
                locs = res.get("locations", [])
                if not locs:
                    continue
                phy = locs[0].get("physicalLocation", {})
                uri = phy.get("artifactLocation", {}).get("uri", "")
                region = phy.get("region", {})
                line = region.get("startLine", 0)
                norm = normalize_uri(uri)
                key = (res.get("ruleId"), norm, line)
                if key in seen:
                    continue
                seen.add(key)
                findings.append({
                    "tool": "CodeQL",
                    "severity": severity,
                    "file": norm,
                    "line": line,
                    "rule": res.get("ruleId", ""),
                    "desc": re.sub(r"\s+", " ", res.get("message", {}).get("text", "")).strip(),
                    "score": sev_score,
                })
    return findings


def severity_rank(s):
    return {"High": 0, "Medium": 1, "Low": 2, "Unknown": 3}.get(s, 4)


def main():
    bandit = bandit_findings()
    codeql = codeql_findings()
    all_findings = sorted(
        bandit + codeql,
        key=lambda x: (severity_rank(x["severity"]), x["file"], x["line"])
    )

    counts = {"High": 0, "Medium": 0, "Low": 0}
    for f in all_findings:
        counts[f.get("severity", "Unknown")] = counts.get(f.get("severity", "Unknown"), 0) + 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Security Scan Summary\n",
        f"Generated: {now}  ",
        f"Repository: `{os.path.basename(os.getcwd())}`\n",
        "## Summary\n",
        "| Tool | Scope | Issues | High | Medium | Low |",
        "|------|-------|--------|------|--------|-----|",
        f"| Bandit | Python backend | {len(bandit)} | {sum(1 for x in bandit if x['severity']=='High')} | {sum(1 for x in bandit if x['severity']=='Medium')} | {sum(1 for x in bandit if x['severity']=='Low')} |",
        f"| CodeQL | Python + JavaScript/TypeScript | {len(codeql)} | {sum(1 for x in codeql if x['severity']=='High')} | {sum(1 for x in codeql if x['severity']=='Medium')} | {sum(1 for x in codeql if x['severity']=='Low')} |",
        f"| **Total** | | **{len(all_findings)}** | **{counts.get('High',0)}** | **{counts.get('Medium',0)}** | **{counts.get('Low',0)}** |\n",
    ]

    def section(title, items):
        if not items:
            return [f"## {title}\n", "No findings.\n"]
        sec = [f"## {title}\n", f"{len(items)} issue(s) found.\n", "| Severity | File | Line | Rule | Description |", "|----------|------|------|------|-------------|"]
        for x in items:
            file_cell = f"`{x['file']}`" if x['file'] else "-"
            desc = x['desc'].replace("|", r"\|")
            sec.append(f"| {x['severity']} | {file_cell} | {x['line'] or '-'} | `{x['rule']}` | {desc} |")
        sec.append("")
        return sec

    lines += section("Bandit Findings", bandit)
    lines += section("CodeQL Findings", codeql)

    lines += ["## Recommendations\n"]
    if not all_findings:
        lines.append("No security findings to address.\n")
    else:
        recs = []
        for x in all_findings:
            if x["rule"] in ("B107", "B106"):
                recs.append("Avoid default empty password strings in user creation flows (`auth/db.py`).")
            elif x["rule"] == "B104":
                recs.append("Bind the backend to a specific interface in production instead of `0.0.0.0` (`settings.py`).")
            elif "path-injection" in x["rule"]:
                recs.append("Sanitize or restrict user-provided file paths before using them in filesystem operations (`main.py`).")
            elif "bad-tag-filter" in x["rule"]:
                recs.append("Use a robust HTML sanitizer instead of a fragile regex for tag filtering (`main.py`).")
            elif "clear-text-logging-sensitive-data" in x["rule"]:
                recs.append("Never log passwords or other sensitive credentials (`admin.py`).")
        seen = set()
        for r in recs:
            if r not in seen:
                seen.add(r)
                lines.append(f"- {r}")
        lines.append("")

    lines += [
        "## Raw Artifacts\n",
        f"- `{BANDIT_JSON}` - full Bandit JSON output.",
        f"- `{CODEQL_GLOB}` - CodeQL SARIF output per language.",
        "\n_Report produced by Bandit + CodeQL._\n",
    ]

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT} ({len(all_findings)} findings)")


if __name__ == "__main__":
    main()
