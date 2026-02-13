from pathlib import Path
import shutil

# Get the repository root directory
REPOSITORY_DIR = Path.cwd()
print(f"Repository root directory: {REPOSITORY_DIR}")
SKILL_DIR = Path(__file__).parent.parent
print(f"Skill directory: {SKILL_DIR}")
ASSETS_DIR = Path(__file__).parent
print(f"Assets directory: {ASSETS_DIR}")

# Step 1: identify AGENTS.md files in the repository
agents_files = list(REPOSITORY_DIR.glob("**/AGENTS.md"))
print(f"Found {len(agents_files)} AGENTS.md files:")
for agents_file in agents_files:
    print(f" - {agents_file}")
# If there are no AGENTS.md files, create them
if len(agents_files) == 0:
    # Create AGENTS.md files in the repository based on the template
    agents_template_file = ASSETS_DIR / "AGENTS_TEMPLATE.md"

    # Create the AGENTS.md file for the root directory
    shutil.copy2(agents_template_file, REPOSITORY_DIR / "AGENTS.md")
    print(f"Created AGENTS.md file in {REPOSITORY_DIR / 'AGENTS.md'}")

    # List the directories in the repository
    subdirectories = list(REPOSITORY_DIR.glob("**/"))
    print(f"Found {len(subdirectories)} subdirectories:")
    for subdirectory in subdirectories:
        print(f" - {subdirectory}")

# Step 2: identify SKILL.md files in the repository
skills_files = list(REPOSITORY_DIR.glob("**/SKILL.md"))
print(f"Found {len(skills_files)} SKILL.md files:")
for skills_file in skills_files:
    print(f" - {skills_file}")
