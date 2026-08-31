import os
import re
import pytest

PRIMARY_FILE = "/home/hash/Knowledge/05_Logs/Weekly-Monetization-Intelligence-2026-W36.md"
WORKSPACE_FILE = "/home/hash/teamwork_projects/ecosystem_monetization_intelligence/deliverables/Weekly-Monetization-Intelligence-2026-W36.md"

@pytest.fixture(scope="module")
def primary_content():
    assert os.path.exists(PRIMARY_FILE)
    with open(PRIMARY_FILE, "r", encoding="utf-8") as f:
        return f.read()

@pytest.fixture(scope="module")
def workspace_content():
    assert os.path.exists(WORKSPACE_FILE)
    with open(WORKSPACE_FILE, "r", encoding="utf-8") as f:
        return f.read()

def test_file_sizes(primary_content, workspace_content):
    assert len(primary_content) > 90000
    assert len(workspace_content) > 90000

def test_no_placeholders(primary_content):
    forbidden = ["TODO", "TBD", "PLACEHOLDER", "FIXME", "LOREM IPSUM", "YOUR_API_KEY"]
    for token in forbidden:
        assert not re.search(rf"\b{token}\b", primary_content, re.IGNORECASE)

def test_all_four_tracks_count(primary_content):
    t1 = re.findall(r"### Profile 1\.\d+:", primary_content)
    t2 = re.findall(r"### Lead 2\.\d+:", primary_content)
    t3 = re.findall(r"### Scheme 3\.\d+:", primary_content)
    t4 = re.findall(r"### Contest 4\.\d+:", primary_content)
    assert len(t1) == 8
    assert len(t2) == 7
    assert len(t3) == 7
    assert len(t4) == 7

def test_expansion_counts(primary_content):
    sec_4_1 = primary_content[primary_content.find("## 4.1 Top 8 High-Signal Discord Servers"):primary_content.find("## 4.2 Top 8 High-Signal Telegram Groups")]
    sec_4_2 = primary_content[primary_content.find("## 4.2 Top 8 High-Signal Telegram Groups"):primary_content.find("## 4.3 Top 15 High-Impact Twitter / X Accounts")]
    sec_4_3 = primary_content[primary_content.find("## 4.3 Top 15 High-Impact Twitter / X Accounts"):primary_content.find("# 5. R4: Actionable Execution Plan")]
    
    discords = re.findall(r"\|\s*\*\*[1-8]\*\*", sec_4_1)
    telegrams = re.findall(r"\|\s*\*\*[1-8]\*\*", sec_4_2)
    twitters = re.findall(r"\|\s*\*\*(?:[1-9]|1[0-5])\*\*", sec_4_3)
    
    assert len(discords) == 8
    assert len(telegrams) == 8
    assert len(twitters) == 15

def test_roadmap_horizons(primary_content):
    assert "W37" in primary_content
    assert "W38–W39" in primary_content
    assert "W40–W42" in primary_content
