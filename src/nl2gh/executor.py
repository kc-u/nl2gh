import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .schemas import GitHubSearchArgs, GitHubSearchResult


class GitHubAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"GitHub API {status_code}: {message}")


class GitHubExecutor:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    def build_query_string(self, args: GitHubSearchArgs) -> str:
        parts: list[str] = list(args.keywords)

        scalar_qualifiers = [
            ("language", args.language),
            ("stars", args.stars),
            ("forks", args.forks),
            ("size", args.size),
            ("pushed", args.pushed),
            ("created", args.created),
            ("updated", args.updated),
            ("closed", args.closed),
            ("topic", args.topic),
            ("license", args.license),
            ("user", args.user),
            ("org", args.org),
            ("repo", args.repo),
            ("state", args.state),
            ("label", args.label),
            ("author", args.author),
            ("assignee", args.assignee),
            ("comments", args.comments),
            ("location", args.location),
            ("followers", args.followers),
            ("repos", args.repos),
        ]

        for qualifier, value in scalar_qualifiers:
            if value is not None:
                v = str(value)
                parts.append(f'{qualifier}:"{v}"' if " " in v else f"{qualifier}:{v}")

        if args.fork is not None:
            parts.append(f"fork:{'true' if args.fork else 'false'}")
        if args.archived is not None:
            parts.append(f"archived:{'true' if args.archived else 'false'}")
        if args.issue_type:
            parts.append(f"type:{args.issue_type}")
        if args.account_type:
            parts.append(f"type:{args.account_type}")

        return " ".join(filter(None, parts))

    def validate(self, args: GitHubSearchArgs) -> list[str]:
        """Returns non-fatal warnings for potentially invalid or conflicting qualifiers."""
        warnings: list[str] = []

        if args.fork is True and args.search_type == "repositories":
            warnings.append("fork:true returns only forks — did you mean fork:false to exclude forks?")

        if args.search_type == "code" and args.sort:
            warnings.append("Code search does not support sort; sort will be ignored")

        for field_name, value in [("pushed", args.pushed), ("created", args.created)]:
            if value and not any(c in value for c in [">", "<", ".."]):
                warnings.append(
                    f"{field_name} should use a comparator (>2024-01-01) or range (2024-01-01..2024-12-31)"
                )

        return warnings

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def search(self, args: GitHubSearchArgs) -> GitHubSearchResult:
        endpoint_map = {
            "repositories": "/search/repositories",
            "issues": "/search/issues",
            "users": "/search/users",
            "code": "/search/code",
        }
        q = self.build_query_string(args)
        params: dict = {"q": q, "per_page": args.limit}
        if args.sort:
            params["sort"] = args.sort
        if args.order:
            params["order"] = args.order

        resp = self._client.get(
            f"{self.BASE_URL}{endpoint_map[args.search_type]}", params=params
        )

        if resp.status_code == 403:
            msg = resp.json().get("message", resp.text)
            raise GitHubAPIError(403, msg)
        if resp.status_code == 422:
            msg = resp.json().get("message", resp.text)
            raise GitHubAPIError(422, f"Validation failed — {msg}")

        resp.raise_for_status()
        data = resp.json()

        return GitHubSearchResult(
            query_string=q,
            search_type=args.search_type,
            total_count=data.get("total_count", 0),
            items=data.get("items", []),
        )
