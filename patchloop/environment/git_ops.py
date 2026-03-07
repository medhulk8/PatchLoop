from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _apply_unified_diff(diff: str, workdir: Path) -> list[str]:
    """
    Apply a unified diff to files in workdir using pure Python.

    Parses the diff format and applies each hunk using fuzzy context matching
    (searches for the context block anywhere in the file, not just at the
    stated line number). This makes it robust to LLM-generated patches with
    slightly wrong line numbers.

    Returns a list of filenames that were modified.
    Raises ValueError on unrecoverable errors (file not found, hunk not found).
    """
    lines = diff.splitlines()
    target_file: str | None = None
    changed_files: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # --- a/path or +++ b/path: identify the file being patched
        if line.startswith("+++ "):
            raw = line[4:].strip()
            # Strip b/ prefix (git diff format)
            target_file = re.sub(r"^[ab]/", "", raw)
            i += 1
            continue

        if line.startswith("--- ") or line.startswith("diff "):
            i += 1
            continue

        # @@ -old_start,old_count +new_start,new_count @@
        if line.startswith("@@"):
            if target_file is None:
                raise ValueError(f"Hunk found before file header at line {i}")

            filepath = (workdir / target_file).resolve()
            if not filepath.is_relative_to(workdir.resolve()):
                raise ValueError(f"Patch path escapes workspace: {target_file}")
            if not filepath.exists():
                raise ValueError(f"File not found: {target_file}")

            # Collect hunk lines
            i += 1
            hunk_lines: list[str] = []
            while i < len(lines) and not lines[i].startswith("@@") and not lines[i].startswith("--- ") and not lines[i].startswith("diff "):
                hunk_lines.append(lines[i])
                i += 1

            # Parse hunk into (kind, content) tuples
            # kind: ' '=context, '-'=remove, '+'=add
            ops: list[tuple[str, str]] = []
            for hl in hunk_lines:
                if hl.startswith(" ") or hl == "":
                    ops.append((" ", hl[1:] if hl else ""))
                elif hl.startswith("-"):
                    ops.append(("-", hl[1:]))
                elif hl.startswith("+"):
                    ops.append(("+", hl[1:]))
                elif hl.startswith("\\"):
                    pass  # "\ No newline at end of file" — skip
                # Ignore other lines inside hunk

            # Build the "before" block (context + removed lines)
            before_lines = [content for kind, content in ops if kind in (" ", "-")]
            after_lines = [content for kind, content in ops if kind in (" ", "+")]

            if not before_lines:
                continue  # empty hunk, skip

            # Find the before block in the file using exact string search
            file_lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
            before_text = "\n".join(before_lines)
            file_text = "\n".join(file_lines)

            idx = file_text.find(before_text)
            if idx == -1:
                # Fallback: match only the removed lines (ignore hallucinated context).
                # This handles LLM-generated patches where context lines are wrong
                # but the actual changed lines are correct.
                removed_lines = [c for k, c in ops if k == "-"]
                if removed_lines:
                    removed_text = "\n".join(removed_lines)
                    idx = file_text.find(removed_text)
                    if idx != -1:
                        prefix = file_text[:idx]
                        start_line = prefix.count("\n")
                        # Reconstruct: keep context from file, only replace removed lines
                        new_file_lines = (
                            file_lines[:start_line]
                            + [c for k, c in ops if k == "+"]
                            + file_lines[start_line + len(removed_lines):]
                        )
                        new_content = "\n".join(new_file_lines)
                        if file_text.endswith("\n") or file_text == "":
                            new_content += "\n"
                        filepath.write_text(new_content, encoding="utf-8")
                        if target_file not in changed_files:
                            changed_files.append(target_file)
                        continue

                raise ValueError(
                    f"Could not find hunk context in {target_file}.\n"
                    f"Looking for:\n{before_text[:200]}"
                )

            # Count how many lines precede the match
            prefix = file_text[:idx]
            start_line = prefix.count("\n")

            # Replace before_lines with after_lines
            new_file_lines = (
                file_lines[:start_line]
                + after_lines
                + file_lines[start_line + len(before_lines):]
            )

            # Write back
            new_content = "\n".join(new_file_lines)
            # Preserve trailing newline if original had one
            if file_text.endswith("\n") or file_text == "":
                new_content += "\n"
            filepath.write_text(new_content, encoding="utf-8")

            if target_file not in changed_files:
                changed_files.append(target_file)
            continue

        i += 1

    return changed_files


class GitOps:
    """
    Thin subprocess wrapper around git commands for a specific directory.

    We use raw subprocess (not GitPython) because:
    - `git apply` flag control is cleaner via CLI
    - Diff format is exactly what we need without translation
    - Fewer abstraction layers = easier debugging
    """

    def __init__(self, workdir: Path) -> None:
        self.workdir = workdir

    def _run(self, *args: str, timeout: int = 30) -> tuple[int, str, str]:
        result = subprocess.run(
            ["git", *args],
            cwd=self.workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        self._run("init")
        # Set a local identity so commits don't fail in CI or fresh environments
        self._run("config", "user.name", "patchloop-agent")
        self._run("config", "user.email", "agent@patchloop.local")

    def add_all(self) -> None:
        self._run("add", "-A")

    # ------------------------------------------------------------------ #
    # Committing
    # ------------------------------------------------------------------ #

    def commit(self, message: str) -> str:
        """Stage all changes, commit, return the short SHA."""
        self.add_all()
        rc, stdout, stderr = self._run("commit", "-m", message, "--allow-empty")
        if rc != 0:
            raise RuntimeError(f"git commit failed: {stderr.strip()}")
        # stdout looks like: "[main abc1234] message"
        for line in stdout.splitlines():
            if line.startswith("["):
                return line.split()[1].rstrip("]")
        return "unknown"

    # ------------------------------------------------------------------ #
    # Diff / status
    # ------------------------------------------------------------------ #

    def diff(self, ref: str = "HEAD") -> str:
        """Unified diff of working tree vs ref (default: HEAD).

        Using git diff HEAD shows all uncommitted changes (staged + unstaged)
        in a single pass, avoiding the 'staged or unstaged' drop problem.
        Pass a specific SHA to compare committed changes against a snapshot.
        """
        _, stdout, _ = self._run("diff", ref)
        return stdout

    def diff_stat(self) -> str:
        _, stdout, _ = self._run("diff", "HEAD", "--stat")
        return stdout

    # ------------------------------------------------------------------ #
    # Patching
    # ------------------------------------------------------------------ #

    def apply_patch(self, diff: str) -> tuple[bool, str]:
        """
        Apply a unified diff string using a pure Python parser.

        This handles LLM-generated patches that have slightly wrong line
        numbers by searching for context lines directly in the file.
        More robust than `git apply` for this use case.
        Returns (success, message).
        """
        try:
            changed = _apply_unified_diff(diff, self.workdir)
            if not changed:
                return False, "No hunks applied (diff produced no changes)"
            return True, f"Applied to: {', '.join(changed)}"
        except Exception as e:
            return False, str(e)

    # ------------------------------------------------------------------ #
    # Reset
    # ------------------------------------------------------------------ #

    def reset_hard(self, ref: str = "HEAD") -> None:
        """Hard reset to ref, discarding all local changes and untracked files."""
        self._run("reset", "--hard", ref)
        self._run("clean", "-fd")

    def initial_sha(self) -> str:
        """Return the SHA of the very first commit (our clean snapshot)."""
        _, stdout, _ = self._run("rev-list", "--max-parents=0", "HEAD")
        return stdout.strip()

    def current_sha(self) -> str:
        _, stdout, _ = self._run("rev-parse", "HEAD")
        return stdout.strip()

    def log_oneline(self, n: int = 10) -> str:
        _, stdout, _ = self._run("log", f"-{n}", "--oneline")
        return stdout
