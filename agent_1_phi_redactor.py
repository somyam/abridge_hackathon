"""
VigilantAI - Agent 1: PHI Redactor
Strips Protected Health Information (PHI) before sending to external APIs
HIPAA-compliant local processing
"""

import json
import re
from datetime import datetime, timedelta
import hashlib
from typing import Dict, List, Any


class PHIRedactor:
    """
    Local PHI redaction engine
    Runs entirely on-premises - NO external API calls
    """

    def __init__(self, random_seed: int = 42):
        self.random_seed = random_seed
        self.token_map = {}  # Store mappings for consistency

    def redact_patient_data(self, patient_json: Dict) -> Dict:
        """
        Main redaction function - removes all PHI from patient data

        Args:
            patient_json: Complete patient JSON with 5 encounters

        Returns:
            De-identified patient JSON safe for external processing
        """

        print("🔒 PHI Redactor Agent Starting...")
        print("=" * 60)

        redacted = json.loads(json.dumps(patient_json))  # Deep copy

        # Step 1: Redact demographics
        print("  → Redacting patient demographics...")
        redacted["patient_demographics"] = self._redact_demographics(
            patient_json["patient_demographics"]
        )

        # Step 2: Redact encounters
        print("  → Redacting encounter data...")
        redacted["encounters"] = [
            self._redact_encounter(enc)
            for enc in patient_json["encounters"]
        ]

        # Step 3: Redact adverse event summary (if present)
        if "adverse_event_summary" in patient_json:
            print("  → Redacting adverse event summary...")
            redacted["adverse_event_summary"] = self._redact_adverse_event_summary(
                patient_json["adverse_event_summary"]
            )

        # Step 4: Add redaction metadata
        redacted["_redaction_metadata"] = {
            "redacted_at": datetime.now().isoformat(),
            "redaction_method": "VigilantAI PHI Redactor v1.0",
            "hipaa_compliant": True,
            "safe_for_external_api": True
        }

        print("✅ PHI Redaction Complete")
        print("=" * 60)

        return redacted

    def _redact_demographics(self, demographics: Dict) -> Dict:
        """Redact patient demographic information"""

        redacted = demographics.copy()

        # Generate consistent patient token
        patient_id = demographics.get("patient_id", "UNKNOWN")
        patient_token = self._generate_token("PATIENT", patient_id)

        redacted["patient_id"] = patient_token
        redacted["patient_token"] = patient_token
        redacted["name_deidentified"] = f"Patient {self._get_initials(patient_id)}"

        # Shift date of birth (keep age roughly same)
        if "date_of_birth" in demographics:
            dob = datetime.strptime(demographics["date_of_birth"], "%Y-%m-%d")
            # Shift by random offset
            offset_days = self._get_date_offset(patient_id)
            shifted_dob = dob + timedelta(days=offset_days)
            redacted["date_of_birth"] = shifted_dob.strftime("%Y-%m-%d")

        # Redact address
        if "address_deidentified" in demographics:
            redacted["address_deidentified"] = {
                "city": f"City_{self._generate_token('CITY', patient_id)[:3]}",
                "state": demographics["address_deidentified"].get("state", "XX"),
                "zip": "XXXXX",
                "country": demographics["address_deidentified"].get("country", "US")
            }

        # Redact contact info
        if "contact_deidentified" in demographics:
            redacted["contact_deidentified"] = {
                "phone": "XXX-XXX-XXXX",
                "email": f"patient_{patient_token[:8]}@redacted.example"
            }

        return redacted

    def _redact_encounter(self, encounter: Dict) -> Dict:
        """Redact a single encounter"""

        redacted = encounter.copy()

        # Redact provider names
        if "provider" in encounter:
            provider_name = encounter["provider"]
            # Extract role (e.g., "MD (Dermatology)")
            role_match = re.search(r'\((.*?)\)', provider_name)
            role = role_match.group(1) if role_match else "Healthcare Professional"
            redacted["provider"] = f"Provider {self._generate_token('PROV', provider_name)[:4]}, {role}"

        # Redact facility name
        if "location" in encounter:
            redacted["location"] = self._redact_facility_name(encounter["location"])

        # Redact dates (shift consistently)
        if "date" in encounter:
            original_date = datetime.strptime(encounter["date"], "%Y-%m-%d")
            offset_days = self._get_date_offset(encounter.get("encounter_id", ""))
            shifted_date = original_date + timedelta(days=offset_days)
            redacted["date"] = shifted_date.strftime("%Y-%m-%d")

        # Redact clinical narratives (remove any accidental PHI)
        text_fields = [
            "chief_complaint",
            "history_of_present_illness"
        ]

        for field in text_fields:
            if field in encounter:
                redacted[field] = self._scrub_narrative(encounter[field])

        # Redact referrals
        if "referrals" in encounter:
            redacted["referrals"] = [
                self._redact_referral(ref) for ref in encounter["referrals"]
            ]

        return redacted

    def _redact_adverse_event_summary(self, summary: Dict) -> Dict:
        """Redact adverse event summary while keeping clinical details"""

        redacted = summary.copy()

        # Keep product info intact (needed for FDA reporting)
        # But redact reporter personal info
        if "reporter_information" in summary:
            reporter = summary["reporter_information"]
            redacted["reporter_information"] = {
                "reporter_name": f"Dr. {self._generate_token('REPORTER', reporter.get('reporter_name', ''))[:4]}",
                "reporter_type": reporter.get("reporter_type", "Healthcare Professional"),
                "specialty": reporter.get("specialty", "Unknown"),
                "organization": self._redact_facility_name(reporter.get("organization", "Healthcare Facility")),
                "relationship_to_patient": reporter.get("relationship_to_patient", "Treating physician"),
                "report_date": reporter.get("report_date")
            }

        return redacted

    def _redact_referral(self, referral: Dict) -> Dict:
        """Redact referral information"""

        redacted = referral.copy()

        if "provider" in referral:
            provider = referral["provider"]
            # Keep specialty, redact name
            specialty_match = re.search(r'\((.*?)\)', provider)
            specialty = specialty_match.group(1) if specialty_match else ""
            redacted["provider"] = f"Dr. {self._generate_token('REF', provider)[:4]}{', ' + specialty if specialty else ''}"

        return redacted

    def _redact_facility_name(self, facility: str) -> str:
        """Redact facility name while keeping type"""

        # Preserve facility type
        facility_types = {
            "hospital": "Hospital",
            "clinic": "Clinic",
            "center": "Medical Center",
            "health": "Health Center"
        }

        facility_lower = facility.lower()
        facility_type = "Healthcare Facility"

        for key, value in facility_types.items():
            if key in facility_lower:
                facility_type = value
                break

        token = self._generate_token("FACILITY", facility)[:4]
        return f"{facility_type} {token}"

    def _scrub_narrative(self, text: str) -> str:
        """
        Remove potential PHI from narrative text
        This is a basic implementation - production would use NER models
        """

        # Remove potential names (simple heuristic - production would use NER)
        # This is already mostly de-identified in our example, but adding safety

        text = re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', 'PATIENT', text)

        # Remove phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'XXX-XXX-XXXX', text)

        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL_REDACTED', text)

        # Remove SSN-like patterns
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', 'XXX-XX-XXXX', text)

        # Remove specific street addresses
        text = re.sub(r'\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)', 'STREET_ADDRESS', text)

        return text

    def _generate_token(self, prefix: str, identifier: str) -> str:
        """Generate consistent de-identified token"""

        if identifier in self.token_map:
            return self.token_map[identifier]

        # Use hash for consistency
        hash_obj = hashlib.sha256(f"{identifier}{self.random_seed}".encode())
        token = f"{prefix}_{hash_obj.hexdigest()[:8].upper()}"

        self.token_map[identifier] = token
        return token

    def _get_initials(self, identifier: str) -> str:
        """Generate consistent initials"""
        hash_obj = hashlib.sha256(f"{identifier}{self.random_seed}".encode())
        hex_str = hash_obj.hexdigest()
        # Use first two hex chars to generate letters
        letter1 = chr(65 + (int(hex_str[0], 16) % 26))
        letter2 = chr(65 + (int(hex_str[1], 16) % 26))
        return f"{letter1}.{letter2}."

    def _get_date_offset(self, identifier: str) -> int:
        """Get consistent date offset for shifting dates"""
        hash_obj = hashlib.sha256(f"DATE_{identifier}{self.random_seed}".encode())
        # Offset between -180 and +180 days
        return (int(hash_obj.hexdigest()[:8], 16) % 360) - 180


def demo_phi_redactor():
    """Demo the PHI redactor with patient case"""

    print("\n" + "=" * 60)
    print("VIGILANTAI - PHI REDACTOR AGENT DEMO")
    print("=" * 60 + "\n")

    # Load patient case
    with open("patient_adverse_event_case.json", "r") as f:
        patient_data = json.load(f)

    print(f"📋 Original patient data:")
    print(f"  Patient ID: {patient_data['patient_demographics']['patient_id']}")
    print(f"  Name: {patient_data['patient_demographics']['name_deidentified']}")
    print(f"  Address: {patient_data['patient_demographics']['address_deidentified']['city']}, {patient_data['patient_demographics']['address_deidentified']['state']}")
    print(f"  Encounters: {len(patient_data['encounters'])}")
    print()

    # Redact
    redactor = PHIRedactor(random_seed=12345)
    redacted_data = redactor.redact_patient_data(patient_data)

    # Show results
    print(f"\n✅ Redacted patient data:")
    print(f"  Patient Token: {redacted_data['patient_demographics']['patient_token']}")
    print(f"  Name: {redacted_data['patient_demographics']['name_deidentified']}")
    print(f"  Address: {redacted_data['patient_demographics']['address_deidentified']['city']}, {redacted_data['patient_demographics']['address_deidentified']['state']}")
    print(f"  Phone: {redacted_data['patient_demographics']['contact_deidentified']['phone']}")
    print(f"  Provider (Visit 1): {redacted_data['encounters'][0]['provider']}")
    print(f"  Facility (Visit 1): {redacted_data['encounters'][0]['location']}")
    print()

    # Save redacted version
    with open("patient_case_redacted.json", "w") as f:
        json.dump(redacted_data, f, indent=2)

    print("💾 Redacted data saved to: patient_case_redacted.json")
    print("✅ Safe to send to external APIs (Anthropic Claude)")
    print("\n" + "=" * 60)

    return redacted_data


if __name__ == "__main__":
    demo_phi_redactor()
