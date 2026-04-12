#!/usr/bin/env bash
# Sync skill metadata to AGENTS.md Auto-invoke sections
# Usage: propagate.sh [--dry-run] [--scope <scope>]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")")"
SKILLS_DIR="$REPO_ROOT/.opencode/skills"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Options
DRY_RUN=false
FILTER_SCOPE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --scope)
            FILTER_SCOPE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--scope <scope>]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would change without modifying files"
            echo "  --scope      Only sync specific scope (root, ui, api, sdk, mcp_server)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Map scope to AGENTS.md path
get_agents_path() {
    local scope="$1"
    case "$scope" in
        root)       echo "$REPO_ROOT/AGENTS.md" ;;
        ui)         echo "$REPO_ROOT/ui/AGENTS.md" ;;
        api)        echo "$REPO_ROOT/api/AGENTS.md" ;;
        db)         echo "$REPO_ROOT/db/AGENTS.md" ;;
        sdk)        echo "$REPO_ROOT/sdk/AGENTS.md" ;;
        mcp_server) echo "$REPO_ROOT/mcp_server/AGENTS.md" ;;
        tests)      echo "$REPO_ROOT/tests/AGENTS.md" ;;
        infra)      echo "$REPO_ROOT/infra/AGENTS.md" ;;
        docs)       echo "$REPO_ROOT/docs/AGENTS.md" ;;
        *)          echo "" ;;
    esac
}

# Extract YAML frontmatter field using awk
extract_field() {
    local file="$1"
    local field="$2"
    awk -v field="$field" '
        /^---$/ { in_frontmatter = !in_frontmatter; next }
        in_frontmatter && $1 == field":" {
            # Handle single line value
            sub(/^[^:]+:[[:space:]]*/, "")
            if ($0 != "" && $0 != ">") {
                gsub(/^["'\'']|["'\'']$/, "")  # Remove quotes
                print
                exit
            }
            # Handle multi-line value
            getline
            while (/^[[:space:]]/ && !/^---$/) {
                sub(/^[[:space:]]+/, "")
                printf "%s ", $0
                if (!getline) break
            }
            print ""
            exit
        }
    ' "$file" | sed 's/[[:space:]]*$//'
}

# Extract short description for Skills table
# Takes the full description, cuts before "Trigger:", and caps at 120 chars
extract_short_description() {
    local file="$1"
    local full_desc
    full_desc=$(extract_field "$file" "description")

    # Remove everything from "Trigger:" onwards
    full_desc=$(echo "$full_desc" | sed 's/Trigger:.*//; s/[[:space:]]*$//')

    # Remove surrounding quotes if present
    full_desc=$(echo "$full_desc" | sed "s/^['\"]//; s/['\"]$//")

    # Collapse multiple spaces
    full_desc=$(echo "$full_desc" | sed 's/  */ /g')

    # Cap at 120 chars
    if [ ${#full_desc} -gt 120 ]; then
        full_desc="${full_desc:0:117}..."
    fi

    echo "$full_desc"
}

# Extract nested metadata field
#
# Supports either:
#   auto_invoke: "Single Action"
# or:
#   auto_invoke:
#     - "Action A"
#     - "Action B"
#
# For list values, this returns a pipe-delimited string: "Action A|Action B"
extract_metadata() {
    local file="$1"
    local field="$2"

    awk -v field="$field" '
        function trim(s) {
            sub(/^[[:space:]]+/, "", s)
            sub(/[[:space:]]+$/, "", s)
            return s
        }

        /^---$/ { in_frontmatter = !in_frontmatter; next }

        in_frontmatter && /^metadata:/ { in_metadata = 1; next }
        in_frontmatter && in_metadata && /^[a-z]/ && !/^[[:space:]]/ { in_metadata = 0 }

        in_frontmatter && in_metadata && $1 == field":" {
            # Remove "field:" prefix
            sub(/^[^:]+:[[:space:]]*/, "")

            # Single-line scalar: auto_invoke: "Action"
            if ($0 != "") {
                v = $0
                gsub(/^["'\'']|["'\'']$/, "", v)
                gsub(/^\[|\]$/, "", v)  # legacy: allow inline [a, b]
                print trim(v)
                exit
            }

            # Multi-line list:
            # auto_invoke:
            #   - "Action A"
            #   - "Action B"
            out = ""
            while (getline) {
                # Stop when leaving metadata block
                if (!in_frontmatter) break
                if (!in_metadata) break
                if ($0 ~ /^[a-z]/ && $0 !~ /^[[:space:]]/) break

                # On multi-line list, only accept "- item" lines. Anything else ends the list.
                line = $0
                if (line ~ /^[[:space:]]*-[[:space:]]*/) {
                    sub(/^[[:space:]]*-[[:space:]]*/, "", line)
                    line = trim(line)
                    gsub(/^["'\'']|["'\'']$/, "", line)
                    if (line != "") {
                        if (out == "") out = line
                        else out = out "|" line
                    }
                } else {
                    break
                }
            }

            if (out != "") print out
            exit
        }
    ' "$file"
}

echo -e "${BLUE}Skill Sync - Updating AGENTS.md sections${NC}"
echo "========================================================"
echo ""

# Collect skills by scope
declare -A SCOPE_SKILLS       # scope -> "skill1:auto1;;auto2|skill2:auto1"
declare -A SCOPE_SKILLS_INFO  # scope -> "name:desc:relpath|name:desc:relpath"

# Deterministic iteration order (stable diffs)
# Note: macOS ships BSD find; avoid GNU-only flags.
while IFS= read -r skill_file; do
    [ -f "$skill_file" ] || continue

    skill_name=$(extract_field "$skill_file" "name")
    scope_raw=$(extract_metadata "$skill_file" "scope")
    skill_desc=$(extract_short_description "$skill_file")

    # Compute relative path from repo root to SKILL.md
    skill_relpath=".opencode/skills/$skill_name/SKILL.md"

    auto_invoke_raw=$(extract_metadata "$skill_file" "auto_invoke")
    # extract_metadata() returns:
    # - single action: "Action"
    # - multiple actions: "Action A|Action B" (pipe-delimited)
    # But SCOPE_SKILLS also uses '|' to separate entries, so we protect it.
    auto_invoke=${auto_invoke_raw//|/;;}

    # For Skills table, only need scope (auto_invoke is optional)
    [ -z "$scope_raw" ] && continue

    # Parse scope (can be comma-separated or space-separated)
    IFS=', ' read -ra scopes <<< "$scope_raw"

    for scope in "${scopes[@]}"; do
        scope=$(echo "$scope" | tr -d '[:space:]')
        [ -z "$scope" ] && continue

        # Filter by scope if specified
        [ -n "$FILTER_SCOPE" ] && [ "$scope" != "$FILTER_SCOPE" ] && continue

        # Skills table: store name, description, relative path
        # Use \x1F (unit separator) as field separator — never appears in text
        US=$'\x1F'
        info_entry="${skill_name}${US}${skill_desc}${US}${skill_relpath}"
        if [ -z "${SCOPE_SKILLS_INFO[$scope]}" ]; then
            SCOPE_SKILLS_INFO[$scope]="$info_entry"
        else
            SCOPE_SKILLS_INFO[$scope]="${SCOPE_SKILLS_INFO[$scope]}|${info_entry}"
        fi

        # Auto-invoke table: only if auto_invoke is defined
        if [ -n "$auto_invoke" ]; then
            if [ -z "${SCOPE_SKILLS[$scope]}" ]; then
                SCOPE_SKILLS[$scope]="$skill_name:$auto_invoke"
            else
                SCOPE_SKILLS[$scope]="${SCOPE_SKILLS[$scope]}|$skill_name:$auto_invoke"
            fi
        fi
    done
done < <(find "$SKILLS_DIR" -mindepth 2 -maxdepth 2 -name SKILL.md -print | sort)

# Generate sections for each scope
# Collect all unique scopes from both maps
declare -A ALL_SCOPES
for s in "${!SCOPE_SKILLS_INFO[@]}"; do ALL_SCOPES[$s]=1; done
for s in "${!SCOPE_SKILLS[@]}"; do ALL_SCOPES[$s]=1; done

# Deterministic scope order (stable diffs)
scopes_sorted=()
while IFS= read -r scope; do
    scopes_sorted+=("$scope")
done < <(printf "%s\n" "${!ALL_SCOPES[@]}" | sort)

for scope in "${scopes_sorted[@]}"; do
    agents_path=$(get_agents_path "$scope")

    if [ -z "$agents_path" ]; then
        echo -e "${YELLOW}Warning: Unknown scope '$scope'${NC}"
        continue
    fi

    # If AGENTS.md doesn't exist, check if the folder exists
    if [ ! -f "$agents_path" ]; then
        agents_dir=$(dirname "$agents_path")
        if [ ! -d "$agents_dir" ]; then
            echo -e "${YELLOW}Warning: Folder '$agents_dir' does not exist — skipping scope '$scope'${NC}"
            continue
        fi
        # Create AGENTS.md with sections directly (no awk needed)
        echo -e "${GREEN}  ✓ Created $agents_path${NC}"
    fi

    echo -e "${BLUE}Processing: $scope -> $(basename "$(dirname "$agents_path")")/AGENTS.md${NC}"

    # ── 1. Build Skills table (name + description + path) ──────────────
    skills_section="### Skills
| Skill | Description | URL |
|-------|-------------|-----|"

    # Expand into sortable rows: "name<TAB>desc<TAB>relpath"
    info_rows=()
    US=$'\x1F'

    if [ -n "${SCOPE_SKILLS_INFO[$scope]}" ]; then
        IFS='|' read -ra info_entries <<< "${SCOPE_SKILLS_INFO[$scope]}"
        for entry in "${info_entries[@]}"; do
            IFS="$US" read -r sname sdesc srelpath <<< "$entry"
            [ -z "$sname" ] && continue
            info_rows+=("$sname	$sdesc	$srelpath")
        done
    fi

    # Deterministic row order by skill name
    while IFS=$'\t' read -r sname sdesc srelpath; do
        [ -z "$sname" ] && continue
        skills_section="$skills_section
| \`$sname\` | $sdesc | [SKILL.md]($srelpath) |"
    done < <(printf "%s\n" "${info_rows[@]}" | LC_ALL=C sort -t $'\t' -k1,1)

    # ── 2. Build Auto-invoke table (actions → skills) ─────────────────
    auto_invoke_section="### Auto-invoke Skills

When performing these actions, ALWAYS invoke the corresponding skill FIRST:

| Action | Skill |
| -------- | ------- |"

    # Expand into sortable rows: "action<TAB>skill"
    rows=()

    if [ -n "${SCOPE_SKILLS[$scope]}" ]; then
        IFS='|' read -ra skill_entries <<< "${SCOPE_SKILLS[$scope]}"
        for entry in "${skill_entries[@]}"; do
            skill_name="${entry%%:*}"
            actions_raw="${entry#*:}"

            actions_raw=${actions_raw//;;/|}
            IFS='|' read -ra actions <<< "$actions_raw"
            for action in "${actions[@]}"; do
                action="$(echo "$action" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
                [ -z "$action" ] && continue
                rows+=("$action	$skill_name")
            done
        done
    fi

    # Deterministic row order: Action then Skill
    while IFS=$'\t' read -r action skill_name; do
        [ -z "$action" ] && continue
        auto_invoke_section="$auto_invoke_section
| $action | \`$skill_name\` |"
    done < <(printf "%s\n" "${rows[@]}" | LC_ALL=C sort -t $'\t' -k1,1 -k2,2)

    # ── 3. Apply changes to AGENTS.md ─────────────────────────────────
    if $DRY_RUN; then
        echo -e "${YELLOW}[DRY RUN] Would update $agents_path with:${NC}"
        echo ""
        echo "$skills_section"
        echo ""
        echo "$auto_invoke_section"
        echo ""
    else
        # Write sections to temp files (avoids awk multi-line string issues on macOS)
        skills_file=$(mktemp)
        auto_invoke_file=$(mktemp)
        echo "$skills_section" > "$skills_file"
        echo "$auto_invoke_section" > "$auto_invoke_file"

        # Check what exists in the file
        has_skills=$(grep -c "### Skills" "$agents_path" || true)
        has_auto_invoke=$(grep -c "### Auto-invoke Skills" "$agents_path" || true)
        file_size=$(wc -c < "$agents_path")

        if [ "$has_skills" -gt 0 ] || [ "$has_auto_invoke" -gt 0 ]; then
            # ── Replace existing sections ──
            awk -v sf="$skills_file" -v af="$auto_invoke_file" '
                BEGIN {
                    while ((getline line < sf) > 0) { skills_buf = skills_buf line "\n" }
                    close(sf)
                    while ((getline line < af) > 0) { auto_buf = auto_buf line "\n" }
                    close(af)
                    skills_buf = skills_buf "\n"
                    auto_buf = auto_buf "\n"
                }
                /^### Skills/ {
                    printf "%s", skills_buf
                    skip = "skills"
                    next
                }
                /^### Auto-invoke Skills/ {
                    printf "%s", auto_buf
                    skip = "auto"
                    next
                }
                skip && /^(---|##)/ {
                    skip = ""
                }
                skip { next }
                { print }
            ' "$agents_path" > "$agents_path.tmp"
            mv "$agents_path.tmp" "$agents_path"
            echo -e "${GREEN}  ✓ Updated Skills and Auto-invoke sections${NC}"
        elif grep -q "^>.*SKILL\.md)" "$agents_path"; then
            # ── Insert after blockquote marker ──
            awk -v sf="$skills_file" -v af="$auto_invoke_file" '
                BEGIN {
                    while ((getline line < sf) > 0) { skills_buf = skills_buf line "\n" }
                    close(sf)
                    while ((getline line < af) > 0) { auto_buf = auto_buf line "\n" }
                    close(af)
                }
                /^>.*SKILL\.md\)$/ && !inserted {
                    print
                    getline
                    if (/^$/) {
                        print ""
                        printf "%s", skills_buf
                        print ""
                        printf "%s", auto_buf
                        inserted = 1
                        next
                    }
                }
                { print }
            ' "$agents_path" > "$agents_path.tmp"
            mv "$agents_path.tmp" "$agents_path"
            echo -e "${GREEN}  ✓ Inserted Skills and Auto-invoke sections${NC}"
        else
            # ── New/empty file: write sections directly ──
            {
                echo "# Skills Reference"
                echo ""
                echo "$skills_section"
                echo ""
                echo "> Ver SKILL.md for details)"
                echo ""
                echo "$auto_invoke_section"
                echo ""
            } > "$agents_path"
            echo -e "${GREEN}  ✓ Generated Skills and Auto-invoke sections${NC}"
        fi

        rm -f "$skills_file" "$auto_invoke_file"
    fi
done

echo ""
echo -e "${GREEN}Done!${NC}"

# Show skills without metadata
echo ""
echo -e "${BLUE}Skills missing propagate metadata:${NC}"
missing=0
while IFS= read -r skill_file; do
    [ -f "$skill_file" ] || continue
    skill_name=$(extract_field "$skill_file" "name")
    scope_raw=$(extract_metadata "$skill_file" "scope")
    auto_invoke_raw=$(extract_metadata "$skill_file" "auto_invoke")
    auto_invoke=${auto_invoke_raw//|/;;}

    if [ -z "$scope_raw" ] || [ -z "$auto_invoke" ]; then
        echo -e "  ${YELLOW}$skill_name${NC} - missing: ${scope_raw:+}${scope_raw:-scope} ${auto_invoke:+}${auto_invoke:-auto_invoke}"
        missing=$((missing + 1))
    fi
done < <(find "$SKILLS_DIR" -mindepth 2 -maxdepth 2 -name SKILL.md -print | sort)

if [ $missing -eq 0 ]; then
    echo -e "  ${GREEN}All skills have sync metadata${NC}"
fi