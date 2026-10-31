# Job Offer Verifier

Migrant workers lose life savings to fake overseas job offers: upfront
"processing fees", pressure tactics, vague postings, contract substitution.
This tool reads an offer's details and flags the patterns commonly seen in
recruitment scams — in plain language, naming each flag and why it fired.

## The safety contract (read first)

- **This tool NEVER says an offer is safe, verified, legitimate, or genuine.**
  A clean result reads *"No red flags found in what we could check"* — and
  every result carries that disclaimer. A wrong "looks safe" can cost someone
  their savings; we err toward flagging uncertainty.
- **Checks we cannot perform are reported as unperformed**, not guessed:
  agency-licence lookup and salary plausibility need registry/wage data we
  don't hold yet — v1 tells you exactly that and where to check manually
  (e.g. Nepal's DoFE licensed-agency list).
- **Flags, not verdicts.** A flag means "verify this independently", never
  "this is a scam". This is not legal advice.

## The checks (v0.1 — red-flag rules, no external data needed)

| Rule | Severity | What it says |
|---|---|---|
| `upfront_fee` | high | Money demanded before the job starts |
| `pressure_language` | high | "Pay today", "last chance", "limited slots" |
| `contract_substitution` | high | "Sign the final contract on arrival" |
| `fee_above_cap` | warning | Worker-paid fee above Nepal's NPR 10,000 cap context |
| `vague_job` | warning | Generic title ("helper") with no duties described |
| `missing_employer_details` | warning | Named employer, no address/registration to verify |
| `no_agency_named` | warning | No recruiting agency named at all |
| `salary_no_context` | info | Salary with no period/currency — can't be evaluated |
| `salary_no_data` | info | No verified wage data held for this corridor |
| `agency_unverified` | info | Licence not checked — manual DoFE lookup pointer |
| `informal_channel` | info | Offer only via chat app, no office address |

## Quickstart

```bash
python -m unittest discover -s tests   # 16 tests
python demo.py                          # clean offer vs scam pattern
```

```python
from offercheck.rules import analyze

result = analyze({
    "agency_name": "Himal Overseas Pvt. Ltd.",
    "employer_name": "Gulf Construction LLC",
    "employer_address": "Doha, Qatar",
    "job_title": "Mason",
    "destination_country": "Qatar",
    "offer_text": "Pay NPR 50,000 processing fee before departure!",
    "fees": [{"description": "processing fee", "amount": 50000,
              "currency": "NPR", "when": "before departure"}],
})
for f in result["flags"]:
    print(f["severity"], "-", f["message"])
print(result["summary"])
print(result["disclaimer"])
```

## Roadmap (per the build spec)

- v0.1 — red-flag rule engine ✓ (this: catches a large share of scams, no ML)
- next — agency-licence lookup against the DoFE registry (the hard
  data-engineering piece: scraped/compiled list, starting Nepal → 2–3
  destinations)
- next — salary plausibility from published wage data per corridor
- next — pilot with a migrant-worker support NGO before any public launch
- later — document OCR (same stack as invoice-fraud-checker), WhatsApp/Telegram
  bot interface

## Layout

- `offercheck/schema.py` — offer data model + validation
- `offercheck/rules.py` — the eleven red-flag rules + `analyze()`
- `tests/test_rules.py` — 16 tests, each rule tested alone, plus a
  "never says safe" invariant test
- `demo.py` — clean vs scam-pattern example
