"""Demo: a clean offer vs. a scam-pattern offer."""
import json

from offercheck.rules import analyze

clean = {
    "agency_name": "Himal Overseas Pvt. Ltd.",
    "employer_name": "Gulf Construction LLC",
    "employer_address": "Doha, Qatar",
    "job_title": "Mason",
    "job_description": "Block laying on residential sites, 8h/day, 6 days/week.",
    "destination_country": "Qatar",
    "salary_amount": 1200, "salary_currency": "QAR", "salary_period": "monthly",
    "contact_channel": "office visit",
}

scam = {
    "agency_name": "",
    "employer_name": "Gulf Jobs",
    "job_title": "helper",
    "job_description": "",
    "destination_country": "Qatar",
    "offer_text": ("URGENT: pay today! Processing fee NPR 150,000 before "
                   "departure. Only 2 slots left, or lose this opportunity. "
                   "Sign the final contract on arrival."),
    "fees": [{"description": "processing fee", "amount": 150000,
              "currency": "NPR", "when": "before departure"}],
    "contact_channel": "whatsapp",
}

for name, data in (("CLEAN", clean), ("SCAM-PATTERN", scam)):
    r = analyze(data)
    print(f"===== {name}: {r['summary']}")
    for f in r["flags"]:
        print(f"  [{f['severity']}] {f['rule']}: {f['message'][:110]}...")
    print(f"  disclaimer: {r['disclaimer'][:80]}...")
    print()
