#!/usr/bin/env python3
import json
import os

# Read the template
template_path = (
    "/home/pablo/.config/opencode/skills/skill-creator/assets/eval_review.html"
)
with open(template_path, "r") as f:
    template = f.read()

# Read eval queries
eval_path = "/home/pablo/.config/opencode/skills/conventional-commits-workspace/description-optimization/trigger_eval_queries.json"
with open(eval_path, "r") as f:
    eval_data = json.load(f)

# Skill info
skill_name = "conventional-commits"
skill_description = """Create and execute git commits following the Conventional Commits specification. Use when the user asks to make a commit, commit changes, or mentions conventional commits, semantic commits, or git commits with structured messages. Always use this skill when the user wants to commit code changes in a git repository - the skill will guide them through creating a proper conventional commit message even if they don't explicitly ask for it."""

# Replace placeholders
template = template.replace("__SKILL_NAME_PLACEHOLDER__", skill_name)
template = template.replace("__SKILL_DESCRIPTION_PLACEHOLDER__", skill_description)
# IMPORTANT: eval data placeholder must be inserted without quotes
template = template.replace("__EVAL_DATA_PLACEHOLDER__", json.dumps(eval_data))

# Write output
output_path = "/tmp/eval_review_conventional-commits.html"
with open(output_path, "w") as f:
    f.write(template)

print(f"Generated review HTML at {output_path}")
print(f"Open with: open {output_path}")
