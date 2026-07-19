"""
VigilantAI - Agent 3: Computer Use Form Filler
Interfaces with Anthropic Computer Use demo to autonomously fill FDA forms
"""

import json
import os
from typing import Dict
from anthropic import Anthropic


class ComputerUseFormFiller:
    """
    Uses Anthropic Computer Use to autonomously fill out FDA MedWatch forms
    Requires: Computer Use demo running at localhost:8080
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def fill_fda_form(
        self,
        fda_data: Dict,
        portal_url: str = "https://vaers.hhs.gov/esub/EsubController",
        portal_name: str = "VAERS"
    ) -> Dict:
        """
        Generate Computer Use prompt to fill FDA form

        Args:
            fda_data: Structured FDA form data from Agent 2
            portal_url: URL of the form to fill
            portal_name: Name of the portal (for prompt clarity)

        Returns:
            Dict with prompt and metadata
        """

        print("\n🖥️  Computer Use Form Filler Agent Starting...")
        print("=" * 60)

        if not fda_data.get("has_reportable_event"):
            print("❌ No reportable event in data")
            return {
                "success": False,
                "message": "No reportable adverse event to submit"
            }

        # Generate the Computer Use prompt
        print(f"  → Generating Computer Use prompt for {portal_name}...")
        computer_use_prompt = self._generate_computer_use_prompt(
            fda_data,
            portal_url,
            portal_name
        )

        # Save prompt to file
        prompt_file = "computer_use_prompt.txt"
        with open(prompt_file, "w") as f:
            f.write(computer_use_prompt)

        print(f"  ✅ Computer Use prompt generated")
        print(f"  💾 Saved to: {prompt_file}")
        print()
        print("=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. Ensure Computer Use demo is running:")
        print("   → Open http://localhost:8080 in your browser")
        print()
        print("2. Copy the prompt from computer_use_prompt.txt")
        print()
        print("3. Paste into the Computer Use interface")
        print()
        print("4. Click 'Run' and watch it fill the form!")
        print()
        print("5. Watch execution in VNC viewer:")
        print("   → http://localhost:6080/vnc.html")
        print("=" * 60)

        return {
            "success": True,
            "prompt_file": prompt_file,
            "prompt": computer_use_prompt,
            "portal_url": portal_url,
            "portal_name": portal_name,
            "instructions": [
                "1. Open http://localhost:8080",
                "2. Copy prompt from computer_use_prompt.txt",
                "3. Paste and click 'Run'",
                "4. Watch in VNC at http://localhost:6080/vnc.html"
            ]
        }

    def _generate_computer_use_prompt(
        self,
        fda_data: Dict,
        portal_url: str,
        portal_name: str
    ) -> str:
        """
        Generate the prompt for Computer Use agent
        """

        form_data = fda_data.get("fda_medwatch_form_data", {})

        # Extract key data points
        patient_info = form_data.get("section_a_patient_information", {})
        adverse_event = form_data.get("section_b_adverse_event", {})
        suspect_product = form_data.get("section_d_suspect_product", {})
        other_info = form_data.get("section_f_other_relevant_history", {})
        reporter_info = form_data.get("section_g_reporter_information", {})

        prompt = f"""Open Firefox and navigate to {portal_url}

This is the {portal_name} adverse event reporting system.

Your task: Autonomously fill out the adverse event report form with the data below.

CRITICAL INSTRUCTIONS:
1. Take a screenshot after the page loads to see the form layout
2. Read field labels carefully to match them with the data
3. Handle multi-page forms by clicking "Next" or "Continue" buttons
4. Fill ALL applicable fields
5. Use DD-MMM-YYYY date format (e.g., 15-JAN-2024)
6. STOP before clicking the final "Submit" button - take a screenshot instead

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION A: PATIENT INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Patient Identifier: {patient_info.get('patient_identifier', 'N/A')}
Age at Time of Event: {patient_info.get('age_at_event', 'N/A')}
Sex: {patient_info.get('sex', 'N/A')}
Weight: {patient_info.get('weight', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION B: ADVERSE EVENT OR PRODUCT PROBLEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Adverse Event or Product Problem:
{json.dumps(adverse_event.get('adverse_event_or_product_problem', []), indent=2)}

Outcomes Attributed to Adverse Event (check all that apply):
{json.dumps(adverse_event.get('outcomes', []), indent=2)}

Date of Event: {adverse_event.get('date_of_event', 'N/A')}
Date of This Report: {adverse_event.get('date_of_this_report', 'N/A')}

Describe Event or Problem (narrative):
{adverse_event.get('describe_event', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION D: SUSPECT PRODUCT(S)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Name, Strength, Manufacturer: {suspect_product.get('name', 'N/A')} {suspect_product.get('strength', '')} - {suspect_product.get('manufacturer', 'N/A')}

Dose or Amount: {suspect_product.get('dose_or_amount', 'N/A')}
Route of Administration: {suspect_product.get('route', 'N/A')}
Frequency: {suspect_product.get('frequency', 'N/A')}

Therapy Dates:
  Start: {suspect_product.get('therapy_dates_start', 'N/A')}
  Stop: {suspect_product.get('therapy_dates_stop', 'N/A')}

Diagnosis/Indication for Use: {suspect_product.get('diagnosis_indication', 'N/A')}

Event Abated After Use Stopped or Dose Reduced: {suspect_product.get('event_abated_after_stopping', 'N/A')}

Lot Number: {suspect_product.get('lot_number', 'N/A')}
Expiration Date: {suspect_product.get('expiration_date', 'N/A')}
NDC Number or Unique ID: {suspect_product.get('ndc_or_unique_id', 'N/A')}

Event Reappeared After Reintroduction: {suspect_product.get('event_reappeared_after_reintroduction', 'N/A')}

Concomitant Medical Products (other medications patient was taking):
"""

        if suspect_product.get('concomitant_medical_products'):
            for i, med in enumerate(suspect_product['concomitant_medical_products'], 1):
                prompt += f"{i}. {med.get('name', 'N/A')} - {med.get('dose_frequency_route', 'N/A')}\n"
        else:
            prompt += "None reported\n"

        prompt += f"""
��━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION F: OTHER RELEVANT HISTORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Medical History: {other_info.get('medical_history', 'N/A')}

Allergies: {other_info.get('allergies', 'N/A')}

Lab Data/Test Results: {other_info.get('lab_data', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION G: REPORTER INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Name: {reporter_info.get('reporter_name', 'N/A')}
Occupation: {reporter_info.get('occupation', 'N/A')}
Health Professional: {reporter_info.get('health_professional', 'N/A')}
Initial Reporter: {reporter_info.get('initial_reporter', 'N/A')}
Date of Report: {reporter_info.get('date_of_report', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXECUTION INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Take initial screenshot to see form structure
2. Find and fill each field by matching labels to the data above
3. Use visual understanding to locate fields (they may have different labels)
4. For date fields, ensure DD-MMM-YYYY format (convert if needed)
5. For checkboxes, check all that apply based on "outcomes" list
6. For narrative fields, paste the full "describe_event" text
7. Navigate through all form pages (click "Next", "Continue", etc.)
8. Take screenshots after completing each page
9. CRITICAL: STOP before clicking "Submit" or "Send Report"
10. Take final screenshot showing completed form ready for human review

BEGIN EXECUTION NOW.
"""

        return prompt


def demo_computer_use_filler():
    """Demo the Computer Use form filler"""

    print("\n" + "=" * 60)
    print("VIGILANTAI - COMPUTER USE FORM FILLER DEMO")
    print("=" * 60 + "\n")

    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set!")
        return

    # Load FDA extracted data (from Agent 2)
    try:
        with open("fda_extracted_data.json", "r") as f:
            fda_data = json.load(f)
    except FileNotFoundError:
        print("❌ fda_extracted_data.json not found!")
        print("Run Agent 2 (Adverse Event Extractor) first:")
        print("  python agent_2_adverse_event_extractor.py")
        return

    print(f"📋 Loaded FDA extracted data")
    print(f"  Has reportable event: {fda_data.get('has_reportable_event')}")
    print()

    # Generate Computer Use prompt
    filler = ComputerUseFormFiller()
    result = filler.fill_fda_form(
        fda_data=fda_data,
        portal_url="https://vaers.hhs.gov/esub/EsubController",
        portal_name="VAERS"
    )

    if result["success"]:
        print("\n📄 PROMPT PREVIEW (first 500 chars):")
        print("=" * 60)
        print(result["prompt"][:500])
        print("... [truncated] ...")
        print("=" * 60)

    return result


if __name__ == "__main__":
    demo_computer_use_filler()
