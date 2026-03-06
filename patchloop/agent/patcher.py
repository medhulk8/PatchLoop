from __future__ import annotations

from dataclasses import dataclass

from patchloop.environment.base import Environment


@dataclass
class PatchOutcome:
    """Result of attempting to apply a patch."""
    success: bool
    git_sha: str | None
    message: str


def validate_diff(diff: str) -> tuple[bool, str]:
    """
    Basic sanity checks on a unified diff before passing it to git apply.

    Returns (valid, reason). Catches common LLM mistakes early so we get
    a clearer error message than what git apply would produce.
    """
    if not diff or not diff.strip():
        return False, "Empty diff"

    lines = diff.strip().splitlines()

    has_minus_file = any(line.startswith("---") for line in lines)
    has_plus_file = any(line.startswith("+++") for line in lines)
    has_hunk = any(line.startswith("@@") for line in lines)

    if not (has_minus_file and has_plus_file and has_hunk):
        return False, (
            "Diff is missing required headers. "
            "Expected: --- file, +++ file, and at least one @@ hunk."
        )

    return True, "OK"


class Patcher:
    """
    Handles the APPLY_PATCH phase.

    Validates the diff, applies it via the environment, and commits.
    The commit happens regardless of whether tests will pass — we want
    every attempted patch in the git history for replay.
    """

    def apply(
        self,
        diff: str,
        env: Environment,
        run_id: str,
        iteration: int,
    ) -> PatchOutcome:
        """
        Validate, apply, and commit a diff.

        Commit message format: [run_id] iter_N: apply patch
        This format lets us easily grep the git log for a specific run.
        """
        valid, reason = validate_diff(diff)
        if not valid:
            return PatchOutcome(success=False, git_sha=None, message=reason)

        success, message = env.apply_patch(diff)
        if not success:
            return PatchOutcome(success=False, git_sha=None, message=message)

        # Commit immediately — even if tests will fail.
        # Every patch attempt is a git commit so nothing is lost.
        try:
            sha = env.git_commit(f"[{run_id}] iter_{iteration}: apply patch")
        except RuntimeError as e:
            # Commit failed (e.g. nothing changed). Patch was a no-op.
            return PatchOutcome(
                success=False,
                git_sha=None,
                message=f"git commit failed: {e}",
            )

        return PatchOutcome(success=True, git_sha=sha, message="Patch applied")
