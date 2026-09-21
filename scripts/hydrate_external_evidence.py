#!/usr/bin/env python3
"""Materialize source-ledger evidence from exact public locators.

Third-party files and Git checkouts are ignored research inputs, not Aeye source. Existing
paths are never replaced: a mismatch fails closed and requires manual inspection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "evidence" / "ledger" / "sources.json"
EXTERNAL_ROOT = ROOT / "evidence" / "external"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:([0-9a-f]{64})$")
MAX_FILE_BYTES = 64 * 1024 * 1024
FILE_DOWNLOAD_ATTEMPTS = 3
ALLOWED_FILE_HOSTS = {
    "arxiv.org",
    "eprint.iacr.org",
    "patch-diff.githubusercontent.com",
    "pearlresearch.ai",
    "tee.fail",
    "www.rfc-editor.org",
    "www.usenix.org",
}
FILE_ROOTS = tuple(
    (ROOT / path).resolve()
    for path in ("evidence/papers", "evidence/standards", "evidence/changes")
)


@dataclass(frozen=True, order=True)
class ExternalSpec:
    source_id: str
    path: str
    commit: str
    remote: str

    @property
    def absolute_path(self) -> Path:
        return ROOT / self.path


@dataclass(frozen=True, order=True)
class FileSpec:
    source_id: str
    path: str
    sha256: str
    retrieval_url: str

    @property
    def absolute_path(self) -> Path:
        return ROOT / self.path


def require_file_path(spec: FileSpec) -> None:
    candidate = spec.absolute_path.resolve()
    if not any(candidate.is_relative_to(root) for root in FILE_ROOTS):
        raise ValueError(f"{spec.source_id}: file path escapes retained-evidence roots")


def require_public_https(source_id: str, value: str) -> None:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_FILE_HOSTS
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ValueError(f"{source_id}: retrieval URL is outside the public HTTPS allowlist")


def load_file_specs(ledger_path: Path = LEDGER) -> list[FileSpec]:
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    specs: list[FileSpec] = []
    seen_paths: set[str] = set()
    for entry in ledger.get("entries", []):
        artifact = entry.get("artifact", {})
        if artifact.get("type") != "file":
            continue
        spec = FileSpec(
            source_id=entry["source_id"],
            path=artifact["path"],
            sha256=artifact["sha256"],
            retrieval_url=artifact["retrieval_url"],
        )
        require_file_path(spec)
        if spec.path in seen_paths:
            raise ValueError(f"{spec.source_id}: duplicate file path {spec.path!r}")
        seen_paths.add(spec.path)
        if not DIGEST_RE.fullmatch(spec.sha256):
            raise ValueError(f"{spec.source_id}: malformed SHA-256 digest")
        require_public_https(spec.source_id, spec.retrieval_url)
        specs.append(spec)
    if not specs:
        raise ValueError("source ledger contains no downloadable file evidence")
    return sorted(specs)


def load_specs(ledger_path: Path = LEDGER) -> list[ExternalSpec]:
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    specs: list[ExternalSpec] = []
    seen_paths: set[str] = set()
    for entry in ledger.get("entries", []):
        artifact = entry.get("artifact", {})
        if artifact.get("type") != "git_tree":
            continue
        spec = ExternalSpec(
            source_id=entry["source_id"],
            path=artifact["path"],
            commit=artifact["commit"],
            remote=artifact["remote"],
        )
        candidate = spec.absolute_path.resolve()
        try:
            candidate.relative_to(EXTERNAL_ROOT.resolve())
        except ValueError as exc:
            raise ValueError(f"{spec.source_id}: external path escapes evidence root") from exc
        if spec.path in seen_paths:
            raise ValueError(f"{spec.source_id}: duplicate external path {spec.path!r}")
        seen_paths.add(spec.path)
        if not COMMIT_RE.fullmatch(spec.commit):
            raise ValueError(f"{spec.source_id}: commit must be 40 lowercase hex characters")
        parsed = urlparse(spec.remote)
        if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.username:
            raise ValueError(f"{spec.source_id}: only anonymous HTTPS GitHub remotes are allowed")
        specs.append(spec)
    if not specs:
        raise ValueError("source ledger contains no external Git evidence")
    return sorted(specs)


def git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def run_git(arguments: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        env=git_environment(),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode:
        diagnostic = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {diagnostic}")
    return completed.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def verify_file(spec: FileSpec, path: Path | None = None) -> dict[str, str | int]:
    artifact = path or spec.absolute_path
    if artifact.is_symlink() or not artifact.is_file():
        raise RuntimeError(f"{spec.source_id}: expected a non-symlink file at {artifact}")
    size = artifact.stat().st_size
    if size > MAX_FILE_BYTES:
        raise RuntimeError(f"{spec.source_id}: file exceeds {MAX_FILE_BYTES} bytes")
    observed = sha256_file(artifact)
    if observed != spec.sha256:
        raise RuntimeError(f"{spec.source_id}: digest {observed} does not match {spec.sha256}")
    return {"sha256": observed, "bytes": size}


def hydrate_file(spec: FileSpec) -> str:
    target = spec.absolute_path
    if target.exists() or target.is_symlink():
        verify_file(spec)
        return "verified-existing"

    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.hydrate-", dir=target.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        observed = ""
        for attempt in range(1, FILE_DOWNLOAD_ATTEMPTS + 1):
            request = Request(
                spec.retrieval_url,
                headers={"User-Agent": "Aeye-evidence-hydrator/1.0"},
            )
            digest = hashlib.sha256()
            total = 0
            with urlopen(request, timeout=120) as response, temporary.open("wb") as output:
                final_url = response.geturl()
                require_public_https(spec.source_id, final_url)
                declared = response.headers.get("Content-Length")
                if declared is not None and int(declared) > MAX_FILE_BYTES:
                    raise RuntimeError(
                        f"{spec.source_id}: declared file size exceeds {MAX_FILE_BYTES} bytes"
                    )
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_FILE_BYTES:
                        raise RuntimeError(f"{spec.source_id}: download exceeds size limit")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            observed = f"sha256:{digest.hexdigest()}"
            if observed == spec.sha256:
                break
            if attempt == FILE_DOWNLOAD_ATTEMPTS:
                raise RuntimeError(
                    f"{spec.source_id}: downloaded digest {observed} does not match "
                    f"{spec.sha256} after {FILE_DOWNLOAD_ATTEMPTS} attempts"
                )
        try:
            os.link(temporary, target)
        except FileExistsError as exc:
            raise RuntimeError(
                f"{spec.source_id}: target appeared during hydration; refusing to replace it"
            ) from exc
        temporary.unlink()
        verify_file(spec)
        return "hydrated"
    finally:
        if temporary.exists():
            temporary.unlink()


def verify_checkout(spec: ExternalSpec, path: Path | None = None) -> dict[str, str]:
    checkout = path or spec.absolute_path
    if checkout.is_symlink() or not checkout.is_dir() or not (checkout / ".git").exists():
        raise RuntimeError(f"{spec.source_id}: expected a non-symlink Git checkout at {checkout}")
    observed = {
        "commit": run_git(["rev-parse", "HEAD"], cwd=checkout),
        "remote": run_git(["remote", "get-url", "origin"], cwd=checkout),
        "status": run_git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=checkout),
    }
    if observed["commit"] != spec.commit:
        raise RuntimeError(
            f"{spec.source_id}: HEAD {observed['commit']} does not match {spec.commit}"
        )
    if observed["remote"] != spec.remote:
        raise RuntimeError(
            f"{spec.source_id}: origin {observed['remote']!r} does not match {spec.remote!r}"
        )
    if observed["status"]:
        raise RuntimeError(f"{spec.source_id}: checkout is dirty")
    return observed


def hydrate(spec: ExternalSpec) -> str:
    target = spec.absolute_path
    if target.exists() or target.is_symlink():
        verify_checkout(spec)
        return "verified-existing"

    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{target.name}.hydrate-", dir=target.parent
    ) as temporary:
        checkout = Path(temporary)
        run_git(["-c", "init.templateDir=", "init", "--quiet", str(checkout)])
        run_git(["remote", "add", "origin", spec.remote], cwd=checkout)
        run_git(
            [
                "-c",
                "protocol.file.allow=never",
                "-c",
                "protocol.ext.allow=never",
                "fetch",
                "--no-tags",
                "--depth=1",
                "origin",
                spec.commit,
            ],
            cwd=checkout,
        )
        run_git(["checkout", "--detach", "--quiet", spec.commit], cwd=checkout)
        verify_checkout(spec, checkout)
        os.replace(checkout, target)
    verify_checkout(spec)
    return "hydrated"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify existing checkouts without network access or creation",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    arguments = parser.parse_args()

    outcomes: list[dict[str, str | int]] = []
    try:
        for spec in load_file_specs():
            if arguments.check:
                observed = verify_file(spec)
                status = "verified-existing"
            else:
                status = hydrate_file(spec)
                observed = verify_file(spec)
            outcomes.append({"kind": "file", **asdict(spec), **observed, "status": status})
        for spec in load_specs():
            if arguments.check:
                verify_checkout(spec)
                status = "verified-existing"
            else:
                status = hydrate(spec)
            outcomes.append({"kind": "git_tree", **asdict(spec), "status": status})
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        if arguments.json:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2, sort_keys=True))
        else:
            print(f"Aeye external evidence hydration: FAIL: {exc}")
        return 1

    if arguments.json:
        print(json.dumps({"ok": True, "sources": outcomes}, indent=2, sort_keys=True))
    else:
        hydrated = sum(item["status"] == "hydrated" for item in outcomes)
        files = sum(item["kind"] == "file" for item in outcomes)
        checkouts = sum(item["kind"] == "git_tree" for item in outcomes)
        print(
            "Aeye external evidence hydration: "
            f"PASS ({files} exact file(s), {checkouts} exact checkout(s), "
            f"{hydrated} newly hydrated)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
