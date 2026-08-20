"""RPAProvider: the abstract contract for simulated robotic actions a real
RPA robot (UiPath, etc.) would perform against a UI — login, navigation,
form entry, data extraction, transaction execution, portal interaction,
email sending. Every call returns a structured trace entry rather than
actually driving a browser/desktop, since there is no real UiPath license
in this demo. Workflow recipes use this for steps described as "RPA does
X" in the original 15 workflow definitions (e.g. "Email PO to supplier",
"Notify technician via Teams/Email").

Future real implementation (not built now): UiPathProvider, backed by
settings.uipath_base_url, implementing this same interface against the
UiPath Orchestrator API.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class RPAProvider(ABC):
    @abstractmethod
    def login(self, system: str, username: str) -> dict[str, Any]: ...

    @abstractmethod
    def navigate(self, system: str, target: str) -> dict[str, Any]: ...

    @abstractmethod
    def fill_form(self, system: str, form: str, fields: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def extract_data(self, system: str, target: str) -> dict[str, Any]: ...

    @abstractmethod
    def execute_transaction(self, system: str, transaction: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def interact_portal(self, portal: str, action: str, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]: ...

    @abstractmethod
    def send_email(self, to: str, subject: str, body: str) -> dict[str, Any]: ...
