from departments.operations.tools.validators.validate_agent.logic import validate_file


def test_validate_valid_agent(tmp_path):
    agent_content = """---
name: valid-agent
description: does something valid
model: sonnet
temperature: 0.5
max_steps: 10
---

<system_prompt>
<role>Role description</role>
<required_skills>
- departments/discovery/playbooks/skill-test.md
</required_skills>
<mindset>
- Question 1?
</mindset>
<guardrails>
<rule>Traceability: yes</rule>
<rule>Anti-Hallucination: yes</rule>
<rule>No Role Bleed: yes</rule>
<rule>Escalation: yes</rule>
</guardrails>
<output_format>Output format details</output_format>

<workflow>
  <step id="1">
    <description>Read something</description>
    <read>workspace/discovery/meta/bounded_contexts.yaml</read>
    <for_each collection="workspace/discovery/domains/*" item="domain" execution="parallel" max_concurrent="5">
      <read>workspace/discovery/domains/{domain}/dictionary.yaml</read>
    </for_each>
  </step>
</workflow>

<escalation_protocol>
<triggers>- trigger 1</triggers>
<action>Refer to escalation_report_template.md</action>
</escalation_protocol>
</system_prompt>
"""
    f = tmp_path / "valid-agent.md"
    f.write_text(agent_content)

    result = validate_file(f)
    assert result.status == "ok", f"Expected ok but got errors: {result.errors}"


def test_validate_invalid_agent(tmp_path):
    agent_content = """---
name: invalid-agent
# missing description, model, etc.
---
<system_prompt>
<inputs>
  <read>some/file.txt</read>
</inputs>
<workflow>
  <step id="1">
    <read>workspace/discovery/{undeclared}/file.yaml</read>
    <write optional="true">workspace/discovery/errata/{epic}.yaml</write>
    <call_tool name="non_existent_tool">python ...</call_tool>
    <call_tool name="also_missing">do-a-lot --fix --force --verbose --dry-run --output workspace/discovery/strategy/some_very_long_output_path.yaml</call_tool>
  </step>
</workflow>
</system_prompt>
"""
    f = tmp_path / "invalid-agent.md"
    f.write_text(agent_content)

    result = validate_file(f)
    assert result.status == "error"
    error_rules = [e.rule for e in result.errors]

    assert "Frontmatter" in error_rules
    assert "XML Sections" in error_rules
    assert "Workflow Tags" in error_rules  # For write optional missing condition
    assert "Placeholder Binding" in error_rules  # For {undeclared}
    assert "Errata Path" in error_rules  # For {epic} instead of {epic_name}
    assert "Tool Existence" in error_rules  # For non_existent_tool
    assert (
        "Tool Call Complexity" in error_rules
    )  # For the long, flag-heavy call_tool body
