#!/usr/bin/env python3
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

# Config
README_PATH = Path("README.md")
PKG_PATH = Path("pkgs")
SOURCES_PATH = Path("_sources/generated.nix")
START_MARKER = "<!--table:start-->"
END_MARKER = "<!--table:end-->"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_REPO = "NixOS/nixpkgs"

# Category to emoji mapping (with "unknown" fallback)
category_emojis = {
    "chat": "💬",
    "cloud": "☁️",
    "dev-tools": "🛠️",
    "gaming": "🎮",
    "media": "🎵",
    "network": "🌐",
    "productivity": "📈",
    "utilities": "🧰",
    "security": "🔐",
    "tools": "🛎️",
    "system": "🖥️",
    "backup": "📦",
    "mobile": "📱",
    "office": "📎",
    "other": "📦",
    "misc": "🌀",
    "unknown": "❓",
}


def parse_generated_sources():
    """Parse _sources/generated.nix to extract version info."""
    if not SOURCES_PATH.exists():
        return {}

    try:
        content = SOURCES_PATH.read_text()
        sources = {}

        # Look for package entries like:
        # packagename = {
        #   pname = "packagename";
        #   version = "1.2.3";
        #   ...
        # };

        # Find all package blocks
        package_blocks = re.findall(r"(\w+)\s*=\s*{([^}]*)};", content, re.DOTALL)

        for package_name, block_content in package_blocks:
            # Extract pname and version from the block
            pname_match = re.search(r'pname\s*=\s*"([^"]+)"', block_content)
            version_match = re.search(r'version\s*=\s*"([^"]+)"', block_content)

            if pname_match and version_match:
                sources[package_name] = {
                    "pname": pname_match.group(1),
                    "version": version_match.group(1),
                }

        return sources
    except Exception as e:
        print(f"⚠️  Error parsing generated sources: {e}")
        return {}


def find_pr_number(package_dir):
    for name in ["PR.txt", ".pr"]:
        pr_file = package_dir / name
        if pr_file.exists():
            return pr_file.read_text().strip()
    default_nix = package_dir / "default.nix"
    if default_nix.exists():
        content = default_nix.read_text()
        match = re.search(r"#\s*(?:nixpkgs\s*)?PR[:\s]+(\d+)", content, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def get_pr_status(pr_number):
    if not pr_number:
        return None, False
    try:
        url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/pulls/{pr_number}"
        req = urllib.request.Request(url, headers={"User-Agent": "NixPkgs-PR-Checker"})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            merged = data.get("merged", False)
            state = data.get("state", "unknown")
            if merged:
                return "✅ Merged", True
            elif state == "open":
                return "🔄 Open", False
            elif state == "closed":
                return "❌ Closed", False
            else:
                return "❓ Unknown", False
    except urllib.error.HTTPError as e:
        return {404: "❓ Not Found", 403: "⚠️ API Limited"}.get(e.code, "⚠️ Error"), False
    except Exception:
        return "⚠️ API Error", False


def extract_fields(file_path, generated_sources):
    package_dir = file_path.parent
    package_name = package_dir.name
    content = file_path.read_text()

    def extract(patterns, default="unknown"):
        if not isinstance(patterns, list):
            patterns = [patterns]
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()
        return default

    # Try to get version and pname from generated sources first
    if package_name in generated_sources:
        pname = generated_sources[package_name]["pname"]
        version = generated_sources[package_name]["version"]
        print(f"📦 Using nvfetcher data for {package_name}: v{version}")
    else:
        # Fall back to extracting from default.nix
        pname = extract(r'\bpname\s*=\s*"([^"]+)"')
        version = extract(r'\bversion\s*=\s*"([^"]+)"')
        if version != "unknown":
            print(f"📝 Using default.nix data for {package_name}: v{version}")
        else:
            print(f"⚠️  No version found for {package_name}")

    # Check if package uses generated sources
    uses_generated = "inherit (generated)" in content or "generated." in content

    license_ = extract(
        [
            r"\bmeta\s*=\s*with\s+lib;\s*{[^}]*license\s*=\s*licenses\.([a-zA-Z0-9_]+)",
            r"license\s*=\s*licenses\.([a-zA-Z0-9_]+)",
            r"\bmeta\s*=\s*{[^}]*license\s*=\s*lib\.licenses\.([a-zA-Z0-9_]+)",
        ]
    )
    description = extract(
        [
            r'\bmeta\s*=\s*with\s+lib;\s*{[^}]*description\s*=\s*"([^"]+)"',
            r'description\s*=\s*"([^"]+)"',
        ],
        default="No description available",
    )
    homepage = extract(
        [
            r'\bmeta\s*=\s*with\s+lib;\s*{[^}]*homepage\s*=\s*"([^"]+)"',
            r'homepage\s*=\s*"([^"]+)"',
        ],
        default=None,
    )
    changelog = extract(
        [
            r'\bmeta\s*=\s*with\s+lib;\s*{[^}]*changelog\s*=\s*"([^"]+)"',
            r'changelog\s*=\s*"([^"]+)"',
        ],
        default=None,
    )
    platform_str = extract(
        [
            r"\bmeta\s*=\s*with\s+lib;\s*{[^}]*platforms\s*=\s*platforms\.([a-zA-Z0-9_]+)",
            r'platforms\s*=\s*\[\s*((?:"[^"]+"\s*)+)\]',
            r"\bmeta\s*=\s*{[^}]*platforms\s*=\s*lib\.platforms\.([a-zA-Z0-9_]+)",
        ]
    )
    if '"' in platform_str:
        platforms = ", ".join(re.findall(r'"([^"]+)"', platform_str))
    else:
        platforms = platform_str

    pr_number = find_pr_number(package_dir)
    pr_url = f"https://github.com/NixOS/nixpkgs/pull/{pr_number}" if pr_number else None
    tracker_url = (
        f"https://nixpkgs-tracker.ocfox.me/?pr={pr_number}" if pr_number else None
    )
    status, _ = get_pr_status(pr_number)

    return {
        "category": file_path.parent.parent.name,
        "pname": pname,
        "version": version,
        "description": description,
        "license": license_,
        "platforms": platforms,
        "homepage": homepage,
        "changelog": changelog,
        "pr": pr_url,
        "tracker": tracker_url,
        "status": status,
        "uses_nvfetcher": uses_generated,
    }


def generate_markdown_list_with_toc_defaulted():
    categories = defaultdict(list)

    # Parse generated sources first
    print("🔍 Parsing nvfetcher generated sources...")
    generated_sources = parse_generated_sources()
    if generated_sources:
        print(f"✅ Found {len(generated_sources)} packages in generated sources")
    else:
        print("ℹ️  No generated sources found, using default.nix fallback")

    for default_nix in PKG_PATH.glob("*/*/default.nix"):
        pkg = extract_fields(default_nix, generated_sources)
        category = pkg["category"].lower()
        if category not in category_emojis:
            print(f"⚠️  Unknown category '{category}', defaulting to 'unknown'")
            category = "unknown"
        pkg["category"] = category

        lines = [
            f"### 🧰 {pkg['pname']} `v{pkg['version']}`",
            f"- 💡 **Description:** {pkg['description']}",
            f"- 🛡️ **License:** {pkg['license']}",
            f"- 🖥️ **Platforms:** {pkg['platforms']}",
        ]

        # Add nvfetcher indicator if applicable
        if pkg["uses_nvfetcher"]:
            lines.append("- 🔄 **Auto-updated:** Uses nvfetcher for version management")

        if pkg["homepage"]:
            lines.append(
                f"- 🌐 **Homepage:** [{pkg['pname']} Website]({pkg['homepage']})"
            )
        if pkg["changelog"]:
            lines.append(f"- 📄 **Changelog:** [CHANGELOG]({pkg['changelog']})")
        if pkg["pr"]:
            lines.append(f"- 🔗 **PR:** [#{pkg['pr'].split('/')[-1]}]({pkg['pr']})")
        if pkg["tracker"]:
            lines.append(f"  • [Tracker]({pkg['tracker']})")
        if pkg["status"]:
            lines.append(f"- 📦 **Status:** {pkg['status']}")

        categories[category].append("\n".join(lines))

    markdown = [START_MARKER, "## 📦 Packages by Category", ""]

    markdown.append("### 🗂️ Table of Contents")
    for category in sorted(categories.keys()):
        emoji = category_emojis.get(category, "❓")
        markdown.append(f"- [{emoji} {category.capitalize()}](#{category.lower()})")
    markdown.append("")

    for category in sorted(categories.keys()):
        emoji = category_emojis.get(category, "❓")
        package_count = len(categories[category])

        # Create collapsible section using HTML details/summary
        markdown.append(f'<details id="{category.lower()}">')
        markdown.append(
            f"<summary><h2>{emoji} {category.capitalize()} ({package_count} packages)</h2></summary>"
        )
        markdown.append("")

        # Add all packages in this category
        for package_content in categories[category]:
            markdown.append(package_content)
            markdown.append("")

        markdown.append("</details>")
        markdown.append("")

    markdown.append(END_MARKER)
    return "\n".join(markdown)


def replace_readme_section(new_content):
    if not README_PATH.exists():
        README_PATH.write_text(f"{START_MARKER}\n{END_MARKER}\n")
    content = README_PATH.read_text()
    pattern = re.compile(rf"{START_MARKER}.*?{END_MARKER}", re.DOTALL)
    updated = pattern.sub(new_content, content)
    README_PATH.write_text(updated)


if __name__ == "__main__":
    print("🔧 Generating README section with nvfetcher support...")
    section = generate_markdown_list_with_toc_defaulted()
    replace_readme_section(section)
    print("✅ README updated with nvfetcher version support.")
