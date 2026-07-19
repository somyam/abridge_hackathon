"""
VigilantAI - Agent 2: Adverse Event Extractor
Uses Claude to analyze de-identified patient data and extract adverse event details
"""

import json
import os
from typing import Dict, List, Any
from anthropic import Anthropic


class AdverseEventExtractor:
    """
    Claude-powered adverse event extraction
    Input: De-identified patient JSON (from Agent 1)
    Output: Structured adverse event data ready for FDA reporting
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-6"

    def extract_adverse_event(self, redacted_patient_data: Dict) -> Dict:
        """
        Main extraction function

        Args:
            redacted_patient_data: De-identified patient JSON from PHI Redactor

        Returns:
            Structured adverse event data formatted for FDA MedWatch
        """

        print("\n🧠 Adverse Event Extractor Agent Starting...")
        print("=" * 60)

        # Step 1: Analyze patient encounters to identify adverse events
        print("  → Analyzing patient encounters with Claude...")
        adverse_events = self._analyze_encounters(redacted_patient_data)

        # Step 2: Extract structured data for FDA reporting
        print("  → Extracting FDA MedWatch fields...")
        fda_structured_data = self._structure_for_fda(
            redacted_patient_data,
            adverse_events
        )

        # Step 3: Add metadata
        fda_structured_data["_extraction_metadata"] = {
            "extracted_by": "VigilantAI Adverse Event Extractor v1.0",
            "model": self.model,
            "patient_token": redacted_patient_data["patient_demographics"]["patient_token"],
            "total_encounters_analyzed": len(redacted_patient_data["encounters"])
        }

        print("✅ Adverse Event Extraction Complete")
        print("=" * 60)

        return fda_structured_data

    def _analyze_encounters(self, patient_data: Dict) -> List[Dict]:
        """
        Use Claude to analyze all encounters and identify adverse events
        """

        # Format encounters for Claude
        encounters_text = self._format_encounters_for_analysis(patient_data)

        analysis_prompt = f"""You are a medical AI analyzing patient encounter data to identify reportable adverse drug events for FDA MedWatch reporting.

PATIENT DATA:
{encounters_text}

TASK:
1. Review all encounters chronologically
2. Identify any adverse drug events (ADEs) or serious adverse events (SAEs)
3. Determine causality (drug-related vs. coincidental)
4. Assess severity and outcomes

REPORTABLE ADVERSE EVENTS include:
- Death
- Life-threatening events
- Hospitalization (initial or prolonged)
- Disability or permanent damage
- Congenital anomaly/birth defect
- Required intervention to prevent permanent impairment
- Other serious important medical events

OUTPUT FORMAT (JSON):
{{
  "adverse_events_identified": [
    {{
      "event_number": 1,
      "event_description": "Brief summary",
      "suspect_product": "Drug/biologic name",
      "event_onset_encounter": "Visit number",
      "severity": "Serious/Non-serious",
      "seriousness_criteria": ["Death", "Life-threatening", etc.],
      "outcome": "Death/Recovered/Recovering/Not recovered/Unknown",
      "causality": "Definite/Probable/Possible/Unlikely/Unrelated",
      "action_taken": "Drug withdrawn/Dose reduced/No change/etc.",
      "clinical_narrative": "Detailed timeline and description"
    }}
  ],
  "total_events_identified": 1,
  "reportable_to_fda": true/false,
  "reporting_recommendation": "Explanation"
}}

Analyze the encounters and output ONLY the JSON."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0,
            messages=[{
                "role": "user",
                "content": analysis_prompt
            }]
        )

        # Parse Claude's response
        content = response.content[0].text.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()

        try:
            adverse_events = json.loads(content)
            print(f"    ✓ Identified {adverse_events.get('total_events_identified', 0)} adverse event(s)")
            return adverse_events
        except json.JSONDecodeError as e:
            print(f"    ✗ Error parsing Claude response: {e}")
            return {
                "adverse_events_identified": [],
                "total_events_identified": 0,
                "reportable_to_fda": False,
                "error": str(e)
            }

    def _structure_for_fda(self, patient_data: Dict, adverse_events: Dict) -> Dict:
        """
        Structure the adverse event data into FDA MedWatch format
        """

        if adverse_events.get("total_events_identified", 0) == 0:
            return {
                "has_reportable_event": False,
                "message": "No reportable adverse events identified"
            }

        # Get the primary adverse event (in this case, there should be one)
        primary_event = adverse_events["adverse_events_identified"][0]

        # Find the relevant encounters
        event_encounter = self._find_encounter_by_visit_number(
            patient_data,
            primary_event.get("event_onset_encounter", 5)
        )

        # Build FDA MedWatch structure using Claude for detailed mapping
        fda_data = self._generate_fda_form_data(
            patient_data,
            primary_event,
            event_encounter
        )

        return fda_data

    def _generate_fda_form_data(
        self,
        patient_data: Dict,
        adverse_event: Dict,
        event_encounter: Dict
    ) -> Dict:
        """
        Use Claude to generate complete FDA MedWatch form data
        """

        print("  → Generating FDA MedWatch form fields...")

        # Prepare comprehensive patient context
        context = {
            "demographics": patient_data["patient_demographics"],
            "medical_history": patient_data["medical_history"],
            "all_encounters": patient_data["encounters"],
            "adverse_event_analysis": adverse_event,
            "event_encounter": event_encounter,
            "adverse_event_summary": patient_data.get("adverse_event_summary", {})
        }

        fda_mapping_prompt = f"""You are filling out an FDA MedWatch Form 3500 for adverse event reporting.

PATIENT CONTEXT:
{json.dumps(context, indent=2)}

TASK:
Generate complete FDA MedWatch form data using the official form structure.

IMPORTANT INSTRUCTIONS:
1. Dates must be in DD-MMM-YYYY format (e.g., 15-JAN-2024)
2. Use the de-identified patient token (not real name)
3. Include ALL relevant clinical details
4. Map data to exact FDA form fields
5. Include product lot numbers, NDC codes if available

OUTPUT FORMAT (JSON) - FDA MedWatch Form 3500 Fields:
{{
  "section_a_patient_information": {{
    "patient_identifier": "De-identified token",
    "age_at_event": "Number + unit (years/months/days)",
    "sex": "Male/Female/Unknown",
    "weight": "Number + unit (lbs or kg)"
  }},

  "section_b_adverse_event": {{
    "adverse_event_or_product_problem": ["Adverse Event"],
    "outcomes": ["Death", "Life-threatening", "Hospitalization", etc.],
    "date_of_event": "DD-MMM-YYYY",
    "date_of_this_report": "DD-MMM-YYYY (use today)",
    "describe_event": "Detailed narrative following FDA guidelines"
  }},

  "section_d_suspect_product": {{
    "name": "Product name",
    "strength": "Strength",
    "manufacturer": "Manufacturer name",
    "dose_or_amount": "Dose",
    "route": "Route of administration",
    "frequency": "Frequency",
    "therapy_dates_start": "DD-MMM-YYYY",
    "therapy_dates_stop": "DD-MMM-YYYY",
    "diagnosis_indication": "Why product was used",
    "event_abated_after_stopping": "Yes/No/Doesn't apply",
    "lot_number": "Lot number if available",
    "expiration_date": "DD-MMM-YYYY",
    "ndc_or_unique_id": "NDC number",
    "event_reappeared_after_reintroduction": "Yes/No/Doesn't apply",
    "concomitant_medical_products": [
      {{
        "name": "Product name",
        "dose_frequency_route": "Details"
      }}
    ]
  }},

  "section_f_other_relevant_history": {{
    "medical_history": "Relevant past medical history",
    "allergies": "Known allergies",
    "lab_data": "Relevant lab results"
  }},

  "section_g_reporter_information": {{
    "reporter_name": "De-identified reporter name",
    "occupation": "Physician/Nurse/Pharmacist/etc.",
    "health_professional": "Yes/No",
    "initial_reporter": "Healthcare professional",
    "date_of_report": "DD-MMM-YYYY"
  }}
}}

Generate the complete FDA form data in JSON format."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            temperature=0,
            messages=[{
                "role": "user",
                "content": fda_mapping_prompt
            }]
        )

        content = response.content[0].text.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()

        try:
            fda_form_data = json.loads(content)
            print(f"    ✓ FDA form data generated")
            return {
                "has_reportable_event": True,
                "fda_medwatch_form_data": fda_form_data,
                "adverse_event_summary": adverse_event
            }
        except json.JSONDecodeError as e:
            print(f"    ✗ Error parsing FDA form data: {e}")
            return {
                "has_reportable_event": True,
                "error": f"Failed to parse FDA form data: {str(e)}",
                "raw_response": content[:500]
            }

    def _format_encounters_for_analysis(self, patient_data: Dict) -> str:
        """Format patient encounters as readable text for Claude"""

        demographics = patient_data["patient_demographics"]
        encounters = patient_data["encounters"]

        formatted = f"""PATIENT DEMOGRAPHICS:
- Patient ID: {demographics['patient_token']}
- Age: {demographics['age']} years
- Sex: {demographics['sex']}
- Weight: {demographics['weight']}

MEDICAL HISTORY:
"""
        if "medical_history" in patient_data:
            history = patient_data["medical_history"]
            formatted += f"- Chronic Conditions: {', '.join(history.get('chronic_conditions', []))}\n"
            formatted += f"- Allergies: {', '.join([a['allergen'] for a in history.get('allergies', [])])}\n"

        formatted += f"\nENCOUNTERS (Total: {len(encounters)}):\n\n"

        for enc in encounters:
            formatted += f"VISIT {enc['visit_number']} - {enc['date']}:\n"
            formatted += f"  Type: {enc['visit_type']}\n"
            formatted += f"  Provider: {enc['provider']}\n"
            formatted += f"  Chief Complaint: {enc['chief_complaint']}\n"
            formatted += f"  HPI: {enc['history_of_present_illness']}\n"

            if "physical_exam" in enc:
                formatted += f"  Vitals: {enc['physical_exam'].get('vitals', {})}\n"

            if "medications_prescribed" in enc:
                formatted += f"  Medications Prescribed:\n"
                for med in enc['medications_prescribed']:
                    formatted += f"    - {med['name']} {med.get('strength', '')} {med.get('dose', '')} {med.get('frequency', '')}\n"

            if "medications_discontinued" in enc:
                formatted += f"  Medications DISCONTINUED:\n"
                for med in enc['medications_discontinued']:
                    formatted += f"    - {med['name']}: {med['reason_for_discontinuation']}\n"

            if "assessment_and_plan" in enc:
                formatted += f"  Assessment: {', '.join(enc['assessment_and_plan'].get('diagnoses', []))}\n"

            if "adverse_event_reporting" in enc:
                formatted += f"  ⚠️ ADVERSE EVENT DOCUMENTED: {enc['adverse_event_reporting']}\n"

            formatted += "\n"

        return formatted

    def _find_encounter_by_visit_number(self, patient_data: Dict, visit_number: int) -> Dict:
        """Find encounter by visit number"""
        for enc in patient_data["encounters"]:
            if enc["visit_number"] == visit_number:
                return enc
        return patient_data["encounters"][-1]  # Default to last encounter


def demo_adverse_event_extractor():
    """Demo the adverse event extractor"""

    print("\n" + "=" * 60)
    print("VIGILANTAI - ADVERSE EVENT EXTRACTOR DEMO")
    print("=" * 60 + "\n")

    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set!")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return

    # Load redacted patient data (from Agent 1)
    try:
        with open("patient_case_redacted.json", "r") as f:
            redacted_data = json.load(f)
    except FileNotFoundError:
        print("❌ patient_case_redacted.json not found!")
        print("Run Agent 1 (PHI Redactor) first: python agent_1_phi_redactor.py")
        return

    print(f"📋 Loaded redacted patient data:")
    print(f"  Patient: {redacted_data['patient_demographics']['patient_token']}")
    print(f"  Encounters: {len(redacted_data['encounters'])}")
    print()

    # Extract adverse events
    extractor = AdverseEventExtractor()
    fda_data = extractor.extract_adverse_event(redacted_data)

    # Display results
    print(f"\n📊 EXTRACTION RESULTS:")
    print("=" * 60)

    if fda_data.get("has_reportable_event"):
        print("✅ Reportable adverse event identified!")
        print()

        if "fda_medwatch_form_data" in fda_data:
            form = fda_data["fda_medwatch_form_data"]

            print("PATIENT INFO:")
            if "section_a_patient_information" in form:
                for key, value in form["section_a_patient_information"].items():
                    print(f"  {key}: {value}")

            print("\nADVERSE EVENT:")
            if "section_b_adverse_event" in form:
                for key, value in form["section_b_adverse_event"].items():
                    if key == "describe_event":
                        print(f"  {key}: {value[:150]}...")
                    else:
                        print(f"  {key}: {value}")

            print("\nSUSPECT PRODUCT:")
            if "section_d_suspect_product" in form:
                for key, value in form["section_d_suspect_product"].items():
                    if key != "concomitant_medical_products":
                        print(f"  {key}: {value}")

    else:
        print("ℹ️ No reportable adverse events identified")

    # Save to file
    with open("fda_extracted_data.json", "w") as f:
        json.dump(fda_data, f, indent=2)

    print(f"\n💾 FDA data saved to: fda_extracted_data.json")
    print("✅ Ready for Agent 3 (Computer Use Form Filler)")
    print("\n" + "=" * 60)

    return fda_data


if __name__ == "__main__":
    demo_adverse_event_extractor()
