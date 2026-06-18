"""
AutoApply — Base Job Source

Abstract base class for all job discovery sources.
Each source implements discover() to fetch jobs from a specific platform.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import re
from bs4 import BeautifulSoup


def clean_html(html_content: str) -> str:
    """
    Clean HTML content to readable plain text.
    Preserves line breaks for block-level elements and list items,
    collapses multiple horizontal spaces, but maintains paragraph spacing.
    """
    if not html_content:
        return ""
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Strip script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
        
    # Get text with newlines separating HTML elements
    text = soup.get_text(separator="\n")
    
    # Clean up line endings and collapse extra spaces
    cleaned_lines = []
    for line in text.splitlines():
        line_stripped = line.strip()
        if line_stripped:
            # Collapse multiple spaces or tabs into a single space
            line_stripped = re.sub(r'[ \t]+', ' ', line_stripped)
            cleaned_lines.append(line_stripped)
        else:
            # Keep at most one blank line between text blocks
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
                
    # Trim leading/trailing blank lines
    while cleaned_lines and not cleaned_lines[0]:
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()
        
    return "\n".join(cleaned_lines)


@dataclass
class RawJob:
    """Raw job data from a source, before processing."""
    title: str
    company: str
    description: str
    location: str = ""
    remote_allowed: bool = False
    posted_at: str | None = None
    job_type: str = ""
    experience_level: str = ""
    department: str = ""
    source: str = ""
    source_url: str = ""
    apply_url: str = ""
    skills_required: list[str] = field(default_factory=list)
    salary_info: str = ""
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    raw_data: dict = field(default_factory=dict)  # Original API response


class JobSource(ABC):
    """Abstract base class for job discovery sources."""

    name: str = "unknown"
    source_type: str = "unknown"  # greenhouse, lever, rss, career_page

    @abstractmethod
    async def discover(self, config: dict) -> list[RawJob]:
        """
        Discover new jobs from this source.
        
        Args:
            config: Source-specific configuration dict
                    (e.g., board_token for Greenhouse, company for Lever)
        
        Returns:
            List of RawJob objects
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"
