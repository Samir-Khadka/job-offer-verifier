"""Red-flag rule tests — each rule independently testable."""
import unittest

from offercheck.rules import analyze

BASE = {
    "agency_name": "Himal Overseas Pvt. Ltd.",
    "agency_license_no": "1234",
    "employer_name": "Gulf Construction LLC",
    "employer_address": "Doha, Qatar",
    "job_title": "Mason",
    "job_description": "Block laying on residential sites, 8h/day, 6 days/week.",
    "destination_country": "Qatar",
    "salary_amount": 1200,
    "salary_currency": "QAR",
    "salary_period": "monthly",
    "offer_text": "",
    "contact_channel": "office visit",
}


def offer(**kw):
    d = dict(BASE)
    d.update(kw)
    return d


def rules_of(result):
    return [f["rule"] for f in result["flags"]]


class RuleTests(unittest.TestCase):
    def test_clean_offer_only_info_flags(self):
        r = analyze(offer())
        self.assertNotIn("upfront_fee", rules_of(r))
        self.assertNotIn("pressure_language", rules_of(r))
        # agency_unverified + salary_no_data always fire as info in v1
        self.assertEqual(set(rules_of(r)), {"agency_unverified", "salary_no_data"})
        self.assertEqual(r["highest_severity"], "info")
        self.assertIn("not a guarantee", r["summary"])
        self.assertIn("NOT a guarantee", r["disclaimer"])

    def test_upfront_fee_high(self):
        r = analyze(offer(
            offer_text="Pay a processing fee of NPR 50,000 before departure.",
            fees=[{"description": "processing fee", "amount": 50000,
                   "currency": "NPR", "when": "before departure"}]))
        self.assertIn("upfront_fee", rules_of(r))
        f = next(f for f in r["flags"] if f["rule"] == "upfront_fee")
        self.assertEqual(f["severity"], "high")
        self.assertIn("do not pay", f["message"].lower())
        self.assertEqual(r["highest_severity"], "high")

    def test_fee_above_cap_warning(self):
        r = analyze(offer(fees=[{"description": "service charge", "amount": 80000,
                                 "currency": "NPR", "when": "before visa"}]))
        self.assertIn("fee_above_cap", rules_of(r))
        f = next(f for f in r["flags"] if f["rule"] == "fee_above_cap")
        self.assertEqual(f["severity"], "warning")
        self.assertIn("10,000", f["message"])

    def test_pressure_language_high(self):
        r = analyze(offer(offer_text="Only 3 slots left! Pay today or lose "
                                     "this opportunity."))
        self.assertIn("pressure_language", rules_of(r))
        f = next(f for f in r["flags"] if f["rule"] == "pressure_language")
        self.assertEqual(f["severity"], "high")

    def test_vague_job_warning(self):
        r = analyze(offer(job_title="Worker", job_description=""))
        self.assertIn("vague_job", rules_of(r))

    def test_specific_title_no_flag(self):
        r = analyze(offer(job_title="Worker",
                          job_description="Warehouse packing, 8-hour shifts."))
        self.assertNotIn("vague_job", rules_of(r))

    def test_missing_employer_details(self):
        r = analyze(offer(employer_address="", employer_registration_no=""))
        self.assertIn("missing_employer_details", rules_of(r))

    def test_contract_substitution_high(self):
        r = analyze(offer(offer_text="You will sign the final contract on "
                                     "arrival in Doha."))
        self.assertIn("contract_substitution", rules_of(r))
        f = next(f for f in r["flags"]
                 if f["rule"] == "contract_substitution")
        self.assertEqual(f["severity"], "high")

    def test_salary_no_context(self):
        r = analyze(offer(salary_amount=50000, salary_currency="",
                          salary_period=""))
        self.assertIn("salary_no_context", rules_of(r))

    def test_salary_no_data_honest(self):
        r = analyze(offer())
        f = next(f for f in r["flags"] if f["rule"] == "salary_no_data")
        self.assertEqual(f["severity"], "info")
        self.assertIn("no verified wage data", f["message"])

    def test_no_agency_named(self):
        r = analyze(offer(agency_name=""))
        self.assertIn("no_agency_named", rules_of(r))
        self.assertNotIn("agency_unverified", rules_of(r))

    def test_informal_channel(self):
        r = analyze(offer(contact_channel="whatsapp", employer_address=""))
        self.assertIn("informal_channel", rules_of(r))

    def test_office_visit_no_channel_flag(self):
        r = analyze(offer())
        self.assertNotIn("informal_channel", rules_of(r))

    def test_scam_offer_fires_many(self):
        r = analyze(offer(
            agency_name="",
            job_title="helper",
            job_description="",
            employer_address="",
            offer_text=("URGENT: pay today! Processing fee NPR 150,000 before "
                        "departure. Only 2 slots left. Sign final contract on "
                        "arrival."),
            fees=[{"description": "processing fee", "amount": 150000,
                   "currency": "NPR", "when": "before departure"}],
            contact_channel="whatsapp"))
        found = set(rules_of(r))
        for expected in ("upfront_fee", "pressure_language", "vague_job",
                         "contract_substitution", "no_agency_named",
                         "informal_channel", "fee_above_cap"):
            self.assertIn(expected, found)
        self.assertEqual(r["highest_severity"], "high")
        self.assertIn("red flag(s) found", r["summary"])

    def test_never_says_safe(self):
        for kw in ({}, {"offer_text": "normal offer, office visit"}):
            r = analyze(offer(**kw))
            blob = (r["summary"] + r["disclaimer"]).lower()
            self.assertNotIn("safe", blob)
            self.assertNotIn("verified", blob)
            self.assertNotIn("legitimate", blob)
            self.assertNotIn("genuine", blob)

    def test_schema_rejects_bad_fee(self):
        with self.assertRaises(ValueError):
            analyze(offer(fees=[{"description": "x", "amount": "lots"}]))


if __name__ == "__main__":
    unittest.main()
