import pytest
from pathlib import Path

from departments.operations.tools.validators.validate_git_coverage.logic import analyze

AGENT_HEADER = """---
name: {name}
description: test agent
model: sonnet
---

<system_prompt>
<role>Role</role>
<guardrails>
<rule>Traceability: yes</rule>
</guardrails>
"""

AGENT_FOOTER = """
</system_prompt>
"""


def write_agent(
    staff_dir: Path, name: str, workflow: str, subagents_dir: bool = False
) -> Path:
    target_dir = staff_dir / "subagents" if subagents_dir else staff_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    content = (
        AGENT_HEADER.format(name=name)
        + f"<workflow>\n{workflow}\n</workflow>\n"
        + AGENT_FOOTER
    )
    f = target_dir / f"{name}.md"
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def staff_dir(tmp_path):
    d = tmp_path / "departments" / "testdept" / "staff"
    d.mkdir(parents=True)
    return d


def test_clean_pass(staff_dir):
    """Own write is fully covered by git add before the merge step: no findings."""
    workflow = """
  <step id="1">
    <action><call_tool name="git">git checkout -B testdept/orchestrator develop</call_tool></action>
    <write contract="some/contract.yaml">workspace/testdept/strategy/output.yaml</write>
  </step>
  <step id="2">
    <action><call_tool name="git">git add workspace/testdept/strategy/output.yaml && git commit -m "feat: output"</call_tool></action>
    <action><call_tool name="git">git checkout develop && git merge --no-ff testdept/orchestrator -m "merge"</call_tool></action>
  </step>
"""
    write_agent(staff_dir, "orchestrator", workflow)

    result = analyze(staff_dir)
    assert result.findings == [], f"Expected clean pass, got: {result.findings}"


def test_missing_commit(staff_dir):
    """Artifact written but never git-added before the merge step."""
    workflow = """
  <step id="1">
    <action><call_tool name="git">git checkout -B testdept/orchestrator develop</call_tool></action>
    <write contract="some/contract.yaml">workspace/testdept/strategy/output.yaml</write>
  </step>
  <step id="2">
    <action><call_tool name="git">git add workspace/testdept/strategy/other_file.yaml && git commit -m "feat: other"</call_tool></action>
    <action><call_tool name="git">git checkout develop && git merge --no-ff testdept/orchestrator -m "merge"</call_tool></action>
  </step>
"""
    write_agent(staff_dir, "orchestrator", workflow)

    result = analyze(staff_dir)
    categories = [f.category for f in result.findings]
    assert "MISSING_COMMIT" in categories
    missing = next(f for f in result.findings if f.category == "MISSING_COMMIT")
    assert "output.yaml" in missing.message


def test_path_mismatch(staff_dir):
    """git add references a path that was never written / never a tool output — typo detector."""
    workflow = """
  <step id="1">
    <action><call_tool name="git">git checkout -B testdept/orchestrator develop</call_tool></action>
    <write contract="some/contract.yaml">workspace/testdept/strategy/output.yaml</write>
  </step>
  <step id="2">
    <action><call_tool name="git">git add workspace/testdept/strategy/output.yaml workspace/testdept/strategy/outptu_typo.yaml && git commit -m "feat: output"</call_tool></action>
    <action><call_tool name="git">git checkout develop && git merge --no-ff testdept/orchestrator -m "merge"</call_tool></action>
  </step>
"""
    write_agent(staff_dir, "orchestrator", workflow)

    result = analyze(staff_dir)
    categories = [f.category for f in result.findings]
    assert "PATH_MISMATCH" in categories
    mismatch = next(f for f in result.findings if f.category == "PATH_MISMATCH")
    assert "outptu_typo.yaml" in mismatch.message


def test_still_self_commits_but_parallel(staff_dir):
    """A sub-agent self-commits, but the orchestrator invokes it inside a parallel for_each."""
    sub_workflow = """
  <step id="1">
    <write contract="some/contract.yaml">workspace/testdept/domains/{domain}/manifest.yaml</write>
  </step>
  <step id="2">
    <action><call_tool name="git">git add workspace/testdept/domains/{domain}/manifest.yaml && git commit -m "feat: sub"</call_tool></action>
  </step>
"""
    write_agent(staff_dir, "sub-worker", sub_workflow, subagents_dir=True)

    orch_workflow = """
  <step id="1">
    <action><call_tool name="git">git checkout -B testdept/orchestrator develop</call_tool></action>
    <for_each collection="workspace/testdept/domains/*" item="domain" execution="parallel" max_concurrent="3">
      <call_agent name="sub-worker">WORKSPACE_ROOT: {WORKSPACE_ROOT} | COMMAND: Do work</call_agent>
    </for_each>
  </step>
  <step id="2">
    <action><call_tool name="git">git checkout develop && git merge --no-ff testdept/orchestrator -m "merge"</call_tool></action>
  </step>
"""
    write_agent(staff_dir, "orchestrator", orch_workflow)

    result = analyze(staff_dir)
    parallel_findings = [
        f for f in result.findings if f.category == "STILL_SELF_COMMITS_BUT_PARALLEL"
    ]
    assert len(parallel_findings) == 1
    assert parallel_findings[0].file_path.endswith("sub-worker.md")
    assert "orchestrator" in parallel_findings[0].message


def test_destructive_git_op(staff_dir):
    """git add -A, git reset --hard, git clean, and bare `git checkout <path>` are all flagged."""
    workflow = """
  <step id="1">
    <action><call_tool name="git">git checkout -B testdept/orchestrator develop</call_tool></action>
    <write contract="some/contract.yaml">workspace/testdept/strategy/output.yaml</write>
  </step>
  <step id="2">
    <action><call_tool name="git">git add -A && git commit -m "feat: bad"</call_tool></action>
  </step>
  <step id="3">
    <action><call_tool name="git">git reset --hard HEAD</call_tool></action>
  </step>
  <step id="4">
    <action><call_tool name="git">git clean -fd</call_tool></action>
  </step>
  <step id="5">
    <action><call_tool name="git">git checkout workspace/testdept/strategy/output.yaml</call_tool></action>
  </step>
  <step id="6">
    <action><call_tool name="git">git checkout develop && git merge --no-ff testdept/orchestrator -m "merge"</call_tool></action>
  </step>
"""
    write_agent(staff_dir, "orchestrator", workflow)

    result = analyze(staff_dir)
    destructive = [f for f in result.findings if f.category == "DESTRUCTIVE_GIT_OP"]
    # add -A, reset --hard, clean, checkout <path> => at least 4 distinct destructive ops
    expected_destructive_ops_count = 4
    assert len(destructive) >= expected_destructive_ops_count


def test_no_merge_step_skips_missing_commit_and_path_mismatch(staff_dir):
    """A sub-agent (no checkout+merge step of its own) that self-commits legitimately
    should not trigger MISSING_COMMIT/PATH_MISMATCH — those rules only fire on files
    that themselves merge back into a shared branch."""
    workflow = """
  <step id="1">
    <write contract="some/contract.yaml">workspace/testdept/strategy/output.yaml</write>
  </step>
  <step id="2">
    <action><call_tool name="git">git add workspace/testdept/strategy/output.yaml && git commit -m "feat: sub"</call_tool></action>
  </step>
"""
    write_agent(staff_dir, "lone-sub", workflow, subagents_dir=True)

    result = analyze(staff_dir)
    categories = {f.category for f in result.findings}
    assert "MISSING_COMMIT" not in categories
    assert "PATH_MISMATCH" not in categories


def test_batch_cap_exceeded_missing_attr(staff_dir):
    """for_each execution=\"parallel\" without max_concurrent triggers BATCH_CAP_EXCEEDED."""
    workflow = """
  <step id="1">
    <action><call_tool name="git">git checkout -B testdept/orchestrator develop</call_tool></action>
    <for_each collection="workspace/testdept/domains/*" item="domain" execution="parallel">
      <call_agent name="sub-worker">WORKSPACE_ROOT: {WORKSPACE_ROOT} | COMMAND: Do work</call_agent>
    </for_each>
  </step>
  <step id="2">
    <action><call_tool name="git">git checkout develop && git merge --no-ff testdept/orchestrator -m "merge"</call_tool></action>
  </step>
"""
    write_agent(staff_dir, "orchestrator", workflow)

    result = analyze(staff_dir)
    cap_findings = [f for f in result.findings if f.category == "BATCH_CAP_EXCEEDED"]
    assert len(cap_findings) == 1
    assert "max_concurrent" in cap_findings[0].message


def test_batch_cap_valid(staff_dir):
    """for_each execution=\"parallel\" with max_concurrent=\"3\" passes cleanly."""
    workflow = """
  <step id="1">
    <action><call_tool name="git">git checkout -B testdept/orchestrator develop</call_tool></action>
    <for_each collection="workspace/testdept/domains/*" item="domain" execution="parallel" max_concurrent="3">
      <write contract="some/contract.yaml">workspace/testdept/domains/{domain}/output.yaml</write>
    </for_each>
  </step>
  <step id="2">
    <action><call_tool name="git">git add workspace/testdept/domains && git commit -m "feat: outputs"</call_tool></action>
    <action><call_tool name="git">git checkout develop && git merge --no-ff testdept/orchestrator -m "merge"</call_tool></action>
  </step>
"""
    write_agent(staff_dir, "orchestrator", workflow)

    result = analyze(staff_dir)
    cap_findings = [f for f in result.findings if f.category == "BATCH_CAP_EXCEEDED"]
    assert cap_findings == []


def test_batch_cap_exceeded_value_too_high(staff_dir):
    """for_each execution=\"parallel\" with max_concurrent=\"8\" triggers BATCH_CAP_EXCEEDED."""
    workflow = """
  <step id="1">
    <action><call_tool name="git">git checkout -B testdept/orchestrator develop</call_tool></action>
    <for_each collection="workspace/testdept/domains/*" item="domain" execution="parallel" max_concurrent="8">
      <write contract="some/contract.yaml">workspace/testdept/domains/{domain}/output.yaml</write>
    </for_each>
  </step>
  <step id="2">
    <action><call_tool name="git">git add workspace/testdept/domains && git commit -m "feat: outputs"</call_tool></action>
    <action><call_tool name="git">git checkout develop && git merge --no-ff testdept/orchestrator -m "merge"</call_tool></action>
  </step>
"""
    write_agent(staff_dir, "orchestrator", workflow)

    result = analyze(staff_dir)
    cap_findings = [f for f in result.findings if f.category == "BATCH_CAP_EXCEEDED"]
    assert len(cap_findings) == 1
    assert "8" in cap_findings[0].message
    assert "≤ 5" in cap_findings[0].message
