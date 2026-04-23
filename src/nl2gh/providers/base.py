from abc import ABC, abstractmethod
from ..schemas import GitHubSearchArgs


class BaseProvider(ABC):
    @abstractmethod
    def query(self, nl_text: str) -> GitHubSearchArgs:
        """Convert a natural language string to structured GitHub search args."""
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        ...
