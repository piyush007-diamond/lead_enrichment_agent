# Directives Directory

This directory contains **Standard Operating Procedures (SOPs)** written in Markdown.

## Purpose

Directives define:
- **Goals**: What the task should accomplish
- **Inputs**: What data or information is required
- **Tools/Scripts**: Which execution scripts to use
- **Outputs**: What the expected results are
- **Edge Cases**: How to handle exceptions and errors

## Guidelines

1. Write directives as clear, natural language instructions
2. Each directive should focus on a single process or workflow
3. Keep directives updated as you learn from execution
4. Reference execution scripts by their path in `execution/`

## Example Structure

```markdown
# Directive: [Task Name]

## Goal
[What this directive accomplishes]

## Inputs
- [Required input 1]
- [Required input 2]

## Execution Script
`execution/script_name.py`

## Expected Output
[Description of expected output]

## Edge Cases
- [Edge case 1]: [How to handle]
- [Edge case 2]: [How to handle]

## Learnings
- [Any discoveries from previous runs]
```
