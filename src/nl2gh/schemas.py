from pydantic import BaseModel, Field
from typing import Optional, Literal


class GitHubSearchArgs(BaseModel):
    search_type: Literal["repositories", "issues", "users", "code"] = Field(
        description="Type of GitHub search to perform"
    )
    keywords: list[str] = Field(default_factory=list, description="Main search keywords")

    # Shared filters
    language: Optional[str] = Field(None, description="Programming language")
    user: Optional[str] = Field(None, description="GitHub username")
    org: Optional[str] = Field(None, description="GitHub organization")
    repo: Optional[str] = Field(None, description="Specific repo 'owner/repo'")

    # Repository filters
    stars: Optional[str] = Field(None, description="Stars filter e.g. '>1000', '100..500'")
    forks: Optional[str] = Field(None, description="Forks filter e.g. '>100'")
    size: Optional[str] = Field(None, description="Repo size in KB")
    topic: Optional[str] = Field(None, description="Repository topic tag")
    license: Optional[str] = Field(None, description="License key e.g. 'mit', 'apache-2.0'")
    fork: Optional[bool] = Field(None, description="true=forks only, false=exclude forks")
    archived: Optional[bool] = Field(None, description="true=archived only, false=exclude archived")

    # Date filters
    created: Optional[str] = Field(None, description="Created date e.g. '>2024-01-01'")
    pushed: Optional[str] = Field(None, description="Last push date filter")
    updated: Optional[str] = Field(None, description="Last update date filter")
    closed: Optional[str] = Field(None, description="Issue close date filter")

    # Issue/PR filters
    state: Optional[Literal["open", "closed"]] = Field(None, description="Issue/PR state")
    label: Optional[str] = Field(None, description="Issue label")
    issue_type: Optional[Literal["issue", "pr"]] = Field(None, description="Issue or PR")
    author: Optional[str] = Field(None, description="Issue/PR author username")
    assignee: Optional[str] = Field(None, description="Assignee username")
    comments: Optional[str] = Field(None, description="Comment count filter")

    # User filters
    account_type: Optional[Literal["user", "org"]] = Field(None, description="Account type")
    location: Optional[str] = Field(None, description="User location")
    followers: Optional[str] = Field(None, description="Follower count filter")
    repos: Optional[str] = Field(None, description="User repo count filter")

    # Sorting
    sort: Optional[str] = Field(None, description="Sort field")
    order: Optional[Literal["asc", "desc"]] = Field("desc", description="Sort order")
    limit: int = Field(10, ge=1, le=30, description="Max results")

    clarification_needed: Optional[str] = Field(
        None, description="Ask user to clarify if query is genuinely ambiguous"
    )


class GitHubSearchResult(BaseModel):
    query_string: str
    search_type: str
    total_count: int
    items: list[dict]


# Shared JSON schema used by all providers for tool/function calling
TOOL_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "search_type": {
            "type": "string",
            "enum": ["repositories", "issues", "users", "code"],
            "description": "Type of GitHub search",
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Main search keywords",
        },
        "language": {"type": "string", "description": "Programming language"},
        "user": {"type": "string", "description": "GitHub username"},
        "org": {"type": "string", "description": "GitHub organization"},
        "repo": {"type": "string", "description": "Specific repo 'owner/repo'"},
        "stars": {"type": "string", "description": "Stars filter e.g. '>1000', '100..500'"},
        "forks": {"type": "string", "description": "Forks filter e.g. '>100'"},
        "size": {"type": "string", "description": "Repo size in KB"},
        "topic": {"type": "string", "description": "Repository topic"},
        "license": {"type": "string", "description": "License key e.g. 'mit'"},
        "fork": {"type": "boolean", "description": "true=forks only, false=exclude forks"},
        "archived": {"type": "boolean", "description": "true=archived, false=exclude archived"},
        "created": {"type": "string", "description": "Created date filter"},
        "pushed": {"type": "string", "description": "Last push date filter"},
        "updated": {"type": "string", "description": "Last update date filter"},
        "closed": {"type": "string", "description": "Issue close date filter"},
        "state": {"type": "string", "enum": ["open", "closed"], "description": "Issue state"},
        "label": {"type": "string", "description": "Issue label"},
        "issue_type": {"type": "string", "enum": ["issue", "pr"], "description": "issue or pr"},
        "author": {"type": "string", "description": "Issue/PR author"},
        "assignee": {"type": "string", "description": "Assignee username"},
        "comments": {"type": "string", "description": "Comment count filter"},
        "account_type": {"type": "string", "enum": ["user", "org"], "description": "Account type"},
        "location": {"type": "string", "description": "User location"},
        "followers": {"type": "string", "description": "Follower count filter"},
        "repos": {"type": "string", "description": "User repo count filter"},
        "sort": {
            "type": "string",
            "description": "Sort by: stars/forks/updated/help-wanted-issues/created/comments/followers/repositories/joined",
        },
        "order": {"type": "string", "enum": ["asc", "desc"], "description": "Sort order"},
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 30,
            "description": "Max results to return",
        },
        "clarification_needed": {
            "type": "string",
            "description": "Set this if query is genuinely ambiguous and cannot be resolved",
        },
    },
    "required": ["search_type"],
}
