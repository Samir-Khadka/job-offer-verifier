"""Red-flag rule engine for job offers (v0.1).

Each rule returns Flag objects: which check fired, a severity, and a
plain-language message saying WHY — never a "safe"/"verified" verdict.
A clean result means "no red flags found in what we could check", and the
disclaimer says so every time. See README "Honest limits".

Rules needing external data (agency registry, wage tables) are NOT guessed:
they fire an explicit "could not check — verify manually" info flag instead.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .schema import Offer

DISCLAIMER = (
    "This tool flags patterns commonly seen in recruitment scams. "
    "A clean result is NOT a guarantee — registries go stale and scammers "
    "adapt. Always verify the agency licence and employer independently "
    "before paying anything or signing."
)

# Nepal's DoFE publishes the licensed-agency list; v1 does not query it.
DOFE_LICENSE_URL = "https://dofe.gov.np"

UPFRONT_PAT = re.compile(
    r"(pay|payment|deposit|fee).{0,40}(before|advance|upfront|prior to)|"
    r"(advance|upfront|pre[-\s]?departure).{0,30}(pay|payment|fee|deposit)|"
    r"processing fee|visa fee|security deposit|job (confirmation|guarantee) fee",
    re.IGNORECASE)

PRESSURE_PAT = re.compile(
    r"pay today|act now|last chance|limited (slots|seats|vacanc\w+)|"
    r"(lose|miss).{0,20}(spot|chance|opportunity)|"
    r"offer (expires|valid).{0,20}today|immediate(ly)? (pay|deposit)|"
    r"only \d+ (slots|seats|positions?) (left|remain)",
    re.IGNORECASE)

SUBSTITUTION_PAT = re.compile(
    r"(sign|final).{0,30}contract.{0,30}(on )?arrival|"
    r"terms (may|will|can) change|second contract|"
    r"(new|another) contract (after|on|upon) arrival|"
    r"salary (will be|may be) (re)?negotiat",
    re.IGNORECASE)

VAGUE_TITLES = {"worker", "staff", "helper", "labour", "labor", "employee",
                "general worker", "company worker", "foreign worker",
                "assistant", "operator"}

INFORMAL_CHANNELS = {"whatsapp", "viber", "imo", "facebook", "messenger",
                     "tiktok", "telegram"}

# NPR 10,000: the cap Nepal sets on what workers pay for the seven
# free-visa / free-ticket destination countries (Qatar, Saudi Arabia, UAE,
# Kuwait, Bahrain, Oman, Malaysia). Other corridors differ — hence warning,
# not verdict, and only when the currency is NPR.
NEPAL_FEE_CAP_NPR = 10_000


@dataclass
class Flag:
    rule: str
    severity: str  # info | warning | high
    message: str
    details: dict


def _has(pat: re.Pattern, text: str) -> bool:
    return bool(pat.search(text or ""))


def check_upfront_fee(offer: Offer) -> list[Flag]:
    text = offer.full_text()
    fee_words = [f for f in offer.fees
                 if _has(UPFRONT_PAT, f.description + " " + f.when)]
    if _has(UPFRONT_PAT, text) or fee_words:
        return [Flag(
            "upfront_fee", "high",
            "This offer demands money from you before the job starts "
            "(fees, deposits or 'processing' charges). Legitimate foreign "
            "employment rarely requires upfront payment from the worker — "
            "do not pay anything until the agency licence and employer are "
            "independently verified.",
            {"matched_fees": [f.description for f in fee_words]})]
    return []


def check_fee_above_cap(offer: Offer) -> list[Flag]:
    over = [f for f in offer.fees
            if f.currency.upper() == "NPR" and f.amount > NEPAL_FEE_CAP_NPR]
    if not over:
        return []
    total = sum(f.amount for f in over)
    return [Flag(
        "fee_above_cap", "warning",
        f"You are asked to pay NPR {total:,.0f}, above the NPR 10,000 cap "
        "Nepal sets on worker-paid costs for its seven free-visa/free-ticket "
        "destinations. Caps differ by corridor — check the current rule for "
        "yours with the Department of Foreign Employment before paying.",
        {"total_npr": total, "cap_npr": NEPAL_FEE_CAP_NPR})]


def check_pressure(offer: Offer) -> list[Flag]:
    if _has(PRESSURE_PAT, offer.full_text()):
        return [Flag(
            "pressure_language", "high",
            "The offer uses pressure tactics ('pay today', 'last chance', "
            "'limited slots'). Scammers manufacture urgency so you don't "
            "verify. A real employer will still be there tomorrow — use the "
            "time to check the agency licence.",
            {})]
    return []


def check_vague_job(offer: Offer) -> list[Flag]:
    title = offer.job_title.casefold().strip()
    if title in VAGUE_TITLES and len(offer.job_description.strip()) < 20:
        return [Flag(
            "vague_job", "warning",
            f"The job is described only as '{offer.job_title}' with no duties, "
            "worksite, or working hours. Vague postings are a classic cover "
            "for contract substitution — ask for the exact role, duties and "
            "worksite in writing before going further.",
            {})]
    return []


def check_employer_details(offer: Offer) -> list[Flag]:
    if offer.employer_name and not offer.employer_address \
            and not offer.employer_registration_no:
        return [Flag(
            "missing_employer_details", "warning",
            f"'{offer.employer_name}' is named but with no address or "
            "registration number. A real employer's details can be checked "
            "against the destination country's business registry — without "
            "them, you cannot verify who you'd work for.",
            {})]
    return []


def check_contract_substitution(offer: Offer) -> list[Flag]:
    if _has(SUBSTITUTION_PAT, offer.full_text()):
        return [Flag(
            "contract_substitution", "high",
            "The wording suggests you'll sign the 'final' contract after "
            "arrival, or that terms may change. Contract substitution — a "
            "worse contract on arrival — is one of the most common abuses in "
            "labour migration. Insist on the full contract, in a language you "
            "understand, before departure.",
            {})]
    return []


def check_salary_context(offer: Offer) -> list[Flag]:
    if offer.salary_amount is None:
        return []
    if not offer.salary_period or not offer.salary_currency:
        return [Flag(
            "salary_no_context", "info",
            "A salary figure is given with no pay period or currency, so it "
            "can't be evaluated. Ask: monthly or annual? Which currency? "
            "Overtime and deductions included?",
            {})]
    return [Flag(
        "salary_no_data", "info",
        f"We hold no verified wage data for {offer.job_title or 'this role'} "
        f"in {offer.destination_country or 'the destination country'}, so the "
        f"stated {offer.salary_currency} {offer.salary_amount:,.0f} "
        f"{offer.salary_period} could not be checked for plausibility. "
        "Compare it against the destination's labour-ministry or ILO "
        "published ranges yourself.",
        {})]


def check_agency(offer: Offer) -> list[Flag]:
    if not offer.agency_name:
        return [Flag(
            "no_agency_named", "warning",
            "No recruiting agency is named. Know exactly who is recruiting "
            "you — unnamed intermediaries are unaccountable if things go wrong.",
            {})]
    return [Flag(
        "agency_unverified", "info",
        f"We could not verify '{offer.agency_name}' against any licensed-agency "
        f"registry in this check. For Nepal, look the agency up yourself on "
        f"the Department of Foreign Employment list ({DOFE_LICENSE_URL}) "
        "before paying or signing anything.",
        {"dofe_url": DOFE_LICENSE_URL})]


def check_channel(offer: Offer) -> list[Flag]:
    ch = offer.contact_channel
    if ch in INFORMAL_CHANNELS and not offer.employer_address:
        return [Flag(
            "informal_channel", "info",
            f"This offer reached you only via {offer.contact_channel}, with no "
            "office address. Scam recruiters operate almost entirely on chat "
            "apps. Visit the agency's physical office and confirm the address "
            "matches their licence.",
            {})]
    return []


RULES = [check_upfront_fee, check_fee_above_cap, check_pressure,
         check_vague_job, check_employer_details, check_contract_substitution,
         check_salary_context, check_agency, check_channel]


def analyze(data: dict) -> dict:
    """Run every rule. Returns flags + summary + disclaimer.

    The summary is deliberately never "safe" or "verified". A clean result
    reads: "No red flags found in what we could check."
    """
    offer = Offer.from_dict(data)
    flags: list[Flag] = []
    for rule in RULES:
        flags.extend(rule(offer))
    order = {"info": 0, "warning": 1, "high": 2}
    severities = [f.severity for f in flags]
    serious = [f for f in flags if f.severity in ("warning", "high")]
    n = len(serious)
    summary = (f"{n} red flag(s) found — review each one before paying "
               f"anything or signing." if n
               else "No red flags found in what we could check. "
                    "This is not a guarantee — verify independently.")
    return {
        "agency": offer.agency_name,
        "employer": offer.employer_name,
        "job_title": offer.job_title,
        "destination": offer.destination_country,
        "flags": [asdict(f) for f in flags],
        "flag_count": n,
        "highest_severity": max(severities, key=lambda s: order[s])
        if severities else None,
        "summary": summary,
        "disclaimer": DISCLAIMER,
    }
