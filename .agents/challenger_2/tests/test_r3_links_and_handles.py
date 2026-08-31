import re
import pytest
from pathlib import Path

DELIVERABLE_PATH = Path("/home/hash/Knowledge/05_Logs/Weekly-Monetization-Intelligence-2026-W36.md")

def get_markdown_content():
    assert DELIVERABLE_PATH.exists(), f"File {DELIVERABLE_PATH} does not exist"
    return DELIVERABLE_PATH.read_text(encoding="utf-8")

def test_r3_discord_servers():
    """
    Verify Section 4.1 Top 8 High-Signal Discord Servers:
    - Exactly 8 profiled rows in the table
    - Valid discord.gg invite links for each
    - Channels specified
    - Access mechanisms documented
    """
    content = get_markdown_content()
    section_41 = re.search(r"## 4\.1 Top 8 High-Signal Discord Servers(.*?)(?=## 4\.2|\Z)", content, re.DOTALL)
    assert section_41 is not None, "Section 4.1 not found"
    text = section_41.group(1)

    # Match each row: | **<num>** | **<name>** | <access_path> | <channels> | <rationale> |
    rows = re.findall(r"\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|", text)
    assert len(rows) == 8, f"Expected exactly 8 Discord servers in table 4.1, found {len(rows)}"

    for row in rows:
        num, name, access_cell, channels, rationale = row
        assert "discord.gg" in access_cell or "discord.com" in access_cell, f"Invalid Discord link {access_cell} for {name}"
        # Check channel list formatting
        assert "#" in channels, f"Expected channel mentions with # in {channels}"
        # Check rationale length
        assert len(rationale.strip()) > 30, f"Rationale too brief for {name}"

def test_r3_telegram_groups():
    """
    Verify Section 4.2 Top 8 High-Signal Telegram Groups:
    - Exactly 8 profiled rows in the table
    - Valid t.me links or @handles
    - Clear commercial / alpha rationale
    """
    content = get_markdown_content()
    section_42 = re.search(r"## 4\.2 Top 8 High-Signal Telegram Groups(.*?)(?=## 4\.3|\Z)", content, re.DOTALL)
    assert section_42 is not None, "Section 4.2 not found"
    text = section_42.group(1)

    rows = re.findall(r"\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|", text)
    assert len(rows) == 8, f"Expected exactly 8 Telegram groups in table 4.2, found {len(rows)}"

    for row in rows:
        num, name, link_cell, category, rationale = row
        assert "t.me" in link_cell or "@" in link_cell, f"Invalid Telegram link/handle {link_cell} for {name}"
        assert len(category.strip()) > 5
        assert len(rationale.strip()) > 30

def test_r3_twitter_accounts():
    """
    Verify Section 4.3 Top 15 High-Impact Twitter / X Accounts:
    - Exactly 15 profiled rows in the table
    - Valid @handle syntax
    - Verified real personas with relevant credentials
    """
    content = get_markdown_content()
    section_43 = re.search(r"## 4\.3 Top 15 High-Impact Twitter / X Accounts(.*?)(?=# 5\.|\Z)", content, re.DOTALL)
    assert section_43 is not None, "Section 4.3 not found"
    text = section_43.group(1)

    rows = re.findall(r"\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*([^*]+)\*\*(?:<br>([^*|]+))?\s*\|\s*`(@[A-Za-z0-9_]+)`\s*\|\s*([^|]+)\|\s*([^|]+)\|", text)
    assert len(rows) == 15, f"Expected exactly 15 Twitter accounts in table 4.3, found {len(rows)}"

    expected_handles = [
        "@mZargham", "@tarunchitra", "@sreeramkannan", "@hasufl", "@VitalikButerin",
        "@danrobinson", "@akrtws", "@el33th4x0r", "@musalbas", "@rleshner",
        "@StaniKulechov", "@kaiynne", "@owocki", "@allisonlu_", "@0xKofi"
    ]

    extracted_handles = [row[3] for row in rows]
    assert extracted_handles == expected_handles, f"Handle mismatch: {extracted_handles} != {expected_handles}"

def test_no_placeholders_or_todos():
    """
    Forensic check across the deliverable for any placeholder strings, TODOs, or broken markdown.
    """
    content = get_markdown_content()
    forbidden_terms = ["TODO", "TBD", "PLACEHOLDER", "insert link", "example.com", "lorem ipsum", "FIXME"]
    for term in forbidden_terms:
        matches = [m.start() for m in re.finditer(r"\b" + re.escape(term) + r"\b", content, re.IGNORECASE)]
        assert len(matches) == 0, f"Found forbidden placeholder '{term}' at indices {matches}"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
