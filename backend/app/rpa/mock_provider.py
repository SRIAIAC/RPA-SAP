"""MockRPAProvider: returns a structured trace entry for every simulated
action instead of driving a real UI. Deterministic (fixed per-action
latency estimates, no randomness) so demo runs are reproducible. Every
returned dict has the same shape: {action, system/target, status, detail,
simulated_latency_ms} so callers can render a uniform "RPA action log"
regardless of which method was invoked.
"""

from typing import Any, Optional

from app.rpa.base import RPAProvider

# Rough, fixed per-action-type latency estimates (ms) for the trace display —
# not actually slept, since real work already happens via SAP/AI calls.
_LATENCY_MS = {
    "login": 420,
    "navigate": 180,
    "fill_form": 650,
    "extract_data": 300,
    "execute_transaction": 900,
    "interact_portal": 500,
    "send_email": 220,
}


class MockRPAProvider(RPAProvider):
    def login(self, system: str, username: str) -> dict[str, Any]:
        return {
            "action": "login",
            "system": system,
            "status": "success",
            "detail": f"Logged into {system} as {username}",
            "simulated_latency_ms": _LATENCY_MS["login"],
        }

    def navigate(self, system: str, target: str) -> dict[str, Any]:
        return {
            "action": "navigate",
            "system": system,
            "status": "success",
            "detail": f"Navigated to {target} in {system}",
            "simulated_latency_ms": _LATENCY_MS["navigate"],
        }

    def fill_form(self, system: str, form: str, fields: dict[str, Any]) -> dict[str, Any]:
        return {
            "action": "fill_form",
            "system": system,
            "status": "success",
            "detail": f"Filled form '{form}' with {len(fields)} field(s): {', '.join(fields.keys())}",
            "simulated_latency_ms": _LATENCY_MS["fill_form"],
        }

    def extract_data(self, system: str, target: str) -> dict[str, Any]:
        return {
            "action": "extract_data",
            "system": system,
            "status": "success",
            "detail": f"Extracted data from {target} in {system}",
            "simulated_latency_ms": _LATENCY_MS["extract_data"],
        }

    def execute_transaction(self, system: str, transaction: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "action": "execute_transaction",
            "system": system,
            "status": "success",
            "detail": f"Executed transaction '{transaction}' in {system} with {len(payload)} field(s)",
            "simulated_latency_ms": _LATENCY_MS["execute_transaction"],
        }

    def interact_portal(self, portal: str, action: str, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return {
            "action": "interact_portal",
            "system": portal,
            "status": "success",
            "detail": f"Performed '{action}' on {portal}" + (f" with payload {payload}" if payload else ""),
            "simulated_latency_ms": _LATENCY_MS["interact_portal"],
        }

    def send_email(self, to: str, subject: str, body: str) -> dict[str, Any]:
        return {
            "action": "send_email",
            "system": "Email",
            "status": "success",
            "detail": f"Sent email to {to}: '{subject}'",
            "simulated_latency_ms": _LATENCY_MS["send_email"],
        }
