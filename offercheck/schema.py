"""Offer document schema.

Offer details arrive as plain dicts (typed in, pasted, or OCR'd) and are
validated here. Rules only read these objects, so a WhatsApp bot or web
form can be added later without touching detection logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FeeDemand:
    description: str = ""
    amount: float = 0.0
    currency: str = "NPR"
    when: str = ""  # e.g. "before departure", "on arrival"


@dataclass
class Offer:
    # who
    agency_name: str = ""
    agency_license_no: str = ""
    employer_name: str = ""
    employer_address: str = ""
    employer_registration_no: str = ""
    # what / where
    job_title: str = ""
    job_description: str = ""
    destination_country: str = ""
    # pay
    salary_amount: float | None = None
    salary_currency: str = ""
    salary_period: str = ""  # monthly / annual / unspecified
    # money the worker is asked to pay
    fees: list[FeeDemand] = field(default_factory=list)
    # free text: the offer letter / messages, scanned for red-flag language
    offer_text: str = ""
    contact_channel: str = ""  # e.g. "whatsapp", "facebook", "office visit"

    @staticmethod
    def _num(value, field_name: str) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError(f"offer field '{field_name}' must be a number, "
                             f"got {value!r}")

    @classmethod
    def from_dict(cls, d: dict) -> "Offer":
        if not isinstance(d, dict):
            raise ValueError("offer must be a dict")
        fees = []
        for i, f in enumerate(d.get("fees") or []):
            if not isinstance(f, dict):
                raise ValueError(f"fees[{i}] must be a dict")
            fees.append(FeeDemand(
                description=str(f.get("description", "")),
                amount=cls._num(f.get("amount", 0), f"fees[{i}].amount"),
                currency=str(f.get("currency", "NPR") or "NPR"),
                when=str(f.get("when", "")),
            ))
        sal = d.get("salary_amount")
        return cls(
            agency_name=str(d.get("agency_name", "")).strip(),
            agency_license_no=str(d.get("agency_license_no", "")).strip(),
            employer_name=str(d.get("employer_name", "")).strip(),
            employer_address=str(d.get("employer_address", "")).strip(),
            employer_registration_no=str(d.get("employer_registration_no", "")).strip(),
            job_title=str(d.get("job_title", "")).strip(),
            job_description=str(d.get("job_description", "")).strip(),
            destination_country=str(d.get("destination_country", "")).strip(),
            salary_amount=cls._num(sal, "salary_amount") if sal not in (None, "") else None,
            salary_currency=str(d.get("salary_currency", "") or "").strip(),
            salary_period=str(d.get("salary_period", "") or "").strip().casefold(),
            fees=fees,
            offer_text=str(d.get("offer_text", "")),
            contact_channel=str(d.get("contact_channel", "")).strip().casefold(),
        )

    def full_text(self) -> str:
        """Everything scannable in one blob for pattern rules."""
        parts = [self.offer_text, self.job_description,
                 " ".join(f.description + " " + f.when for f in self.fees)]
        return "\n".join(p for p in parts if p)
