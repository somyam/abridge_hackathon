"""
VigilantAI - Simplified Computer Use Form Filler
Takes de-identified patient data and sends it directly to Computer Use to fill FDA MedWatch form
"""

import json
import os
from typing import Dict
from anthropic import Anthropic


class SimpleComputerUseFiller:
    """
    Generates Computer Use prompt from de-identified patient data
    No structured extraction - just sends relevant adverse event info directly
    Can either save to file OR automatically submit to Computer Use API
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def generate_prompt(
        self,
        redacted_patient_data: Dict,
        portal_url: str = "https://vaers.hhs.gov/esub/EsubController"
    ) -> str:
        """
        Generate Computer Use prompt directly from patient data

        Args:
            redacted_patient_data: De-identified patient data from Agent 1
            portal_url: URL of the VAERS form

        Returns:
            Prompt string ready to paste into localhost:8080
        """

        # Extract basic info
        demographics = redacted_patient_data.get("patient_demographics", {})
        encounters = redacted_patient_data.get("encounters", [])
        adverse_events = redacted_patient_data.get("adverse_events_detected", [])

        # Build the prompt
        prompt = f"""You are helping fill out FDA MedWatch Form 3500 for VOLUNTARY reporting of adverse events.

FDA FORM 3500 is used for reporting:
- Prescription and OTC medicines
- Biologics (blood components, gene therapies, cell/tissue transplants)
- Medical devices
- Combination products (pre-filled syringes, auto-injectors, inhalers)
- Cosmetics
- Cannabinoid/CBD products

INSTRUCTIONS:
1. Open Firefox and navigate to: {portal_url}
2. Take a screenshot to see the form fields
3. Read each field label carefully and fill in the corresponding information below
4. Handle multi-page forms by clicking "Next" or "Continue" buttons
5. STOP before clicking the final "Submit" button - take a screenshot for human review

PATIENT INFORMATION (DE-IDENTIFIED):
- Patient Identifier: {demographics.get('patient_id', 'UNKNOWN')}
- Age: {demographics.get('age', 'UNKNOWN')} years
- Sex: {demographics.get('sex', 'UNKNOWN')}
- Weight: {demographics.get('weight', 'UNKNOWN')}

ADVERSE EVENT(S) DETECTED:
"""

        # Add detected adverse events
        if adverse_events:
            for idx, ae in enumerate(adverse_events, 1):
                prompt += f"\n--- Adverse Event #{idx} ---\n"
                prompt += f"Suspect Drug: {ae['suspect_drug']['generic_name']} ({ae['suspect_drug']['brand_name']})\n"
                prompt += f"Event Description: {ae['adverse_event_description']}\n"
                prompt += f"Severity: {ae['severity']}\n"
                prompt += f"Outcome: {ae['outcome']}\n"
                prompt += f"Causality: {ae['causality']}\n"
                prompt += f"Timeline:\n"
                prompt += f"  - Drug Started: {ae['timeline']['drug_start_date']}\n"
                prompt += f"  - Event Onset: {ae['timeline']['event_onset_date']}\n"
                prompt += f"  - Drug Stopped: {ae['timeline'].get('drug_stop_date', 'Ongoing')}\n"
                prompt += f"  - Time to Onset: {ae['timeline']['time_to_onset']}\n"
                if ae.get('fda_criteria_met'):
                    prompt += f"FDA Criteria Met: {', '.join(ae['fda_criteria_met'])}\n"
                prompt += f"\nClinical Evidence: {ae['clinical_evidence']}\n"
        else:
            prompt += "\n(No adverse events detected)\n"

        prompt += "\nCLINICAL ENCOUNTERS:\n"

        # Add encounter summaries
        for i, encounter in enumerate(encounters, 1):
            prompt += f"\nVisit {i} - {encounter.get('date', 'Date Unknown')}:\n"
            prompt += f"  Chief Complaint: {encounter.get('chief_complaint', 'N/A')}\n"
            prompt += f"  Assessment: {encounter.get('assessment', 'N/A')}\n"

            if encounter.get('medications'):
                prompt += f"  Medications: {', '.join([m.get('name', 'Unknown') for m in encounter['medications']])}\n"

            if encounter.get('notes'):
                prompt += f"  Notes: {encounter.get('notes', '')}\n"

        prompt += """

FORM FILLING GUIDELINES:
- Use the de-identified patient ID where patient name is requested
- For dates, use the format DD-MMM-YYYY (e.g., 15-JAN-2024)
- Fill in all available information from above
- If a field asks for information not provided above, leave it blank or mark as "Unknown"
- Take screenshots at each page transition
- CRITICAL: Stop before final submission and show screenshot for human review

FDA MEDWATCH FORM 3500 SECTIONS:
SECTION A - PATIENT INFORMATION
- Patient Identifier (use the de-identified ID above)
- Age at time of event
- Sex
- Weight

SECTION B - ADVERSE EVENT OR PRODUCT PROBLEM
- Describe the adverse event or product problem
- Include outcomes (death, hospitalization, disability, etc.)
- Event date

SECTION C - SUSPECT PRODUCT(S)
- Product name (generic and brand)
- Dose, frequency, and route
- Therapy dates (start and stop)
- Diagnosis for use
- Lot number and NDC if available

SECTION D - SUSPECT MEDICAL DEVICE (if applicable)
- Leave blank for drug events

SECTION E - REPORTER INFORMATION
- Use "Automated System" or "Computer Use Demo" for reporter name
- Leave contact information blank or use placeholder

SECTION F - CONCOMITANT MEDICAL PRODUCTS
- List other medications patient was taking

SECTION G - OTHER RELEVANT HISTORY
- Include relevant medical history and lab data

Begin by navigating to the FDA MedWatch portal and taking a screenshot of the initial form.
"""

        return prompt

    def save_prompt_to_file(
        self,
        redacted_patient_data: Dict,
        output_file: str = "computer_use_prompt.txt",
        portal_url: str = "https://vaers.hhs.gov/esub/EsubController"
    ) -> Dict:
        """
        Generate prompt and save to file

        Returns:
            Dict with status and instructions
        """

        print("\n🖥️  Generating Computer Use Prompt...")
        print("=" * 60)

        # Generate prompt
        prompt = self.generate_prompt(redacted_patient_data, portal_url)

        # Save to file
        with open(output_file, "w") as f:
            f.write(prompt)

        print(f"\n✅ Prompt generated and saved to: {output_file}")
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. Open your browser and go to: http://localhost:8080")
        print("2. Open the file: computer_use_prompt.txt")
        print("3. Copy the entire prompt")
        print("4. Paste it into the Computer Use demo interface")
        print("5. Watch as Claude autonomously fills the VAERS form")
        print("6. Review the final screenshot before manual submission")
        print("=" * 60)

        return {
            "success": True,
            "prompt_file": output_file,
            "portal_url": portal_url,
            "prompt_length": len(prompt),
            "next_step": "Paste prompt into http://localhost:8080"
        }

    def auto_submit_to_computer_use(
        self,
        redacted_patient_data: Dict,
        portal_url: str = "https://www.accessdata.fda.gov/scripts/medwatch/index.cfm?action=professional.reporting1"
    ) -> Dict:
        """
        Automatically submit prompt to Computer Use API

        IMPORTANT: This method attempts to call the Computer Use API directly.
        For this to work, you need to either:
        1. Run this script INSIDE the Docker container where the display is available
        2. Or use save_prompt_to_file() and paste into localhost:8501

        The Computer Use tools require access to the X11 display which only exists
        inside the Docker container at localhost:8080/8501.

        Args:
            redacted_patient_data: De-identified patient data from Agent 1
            portal_url: URL of the FDA MedWatch form

        Returns:
            Dict with API response and status
        """

        # First, save the prompt to file as a fallback
        print("\n🖥️  PREPARING COMPUTER USE SUBMISSION...")
        print("=" * 80)

        prompt_result = self.save_prompt_to_file(
            redacted_patient_data=redacted_patient_data,
            portal_url=portal_url
        )

        if not self.client:
            print("\n⚠️  ANTHROPIC_API_KEY not set")
            print("Prompt saved to file. Please use manual submission via localhost:8501")
            return prompt_result

        print("\n🖥️  ATTEMPTING AUTO-SUBMISSION TO COMPUTER USE API...")
        print("=" * 80)

        # Generate the prompt
        prompt = self.generate_prompt(redacted_patient_data, portal_url)

        print(f"✅ Prompt generated ({len(prompt)} characters)")
        print(f"🎯 Target URL: {portal_url}")

        # Use the same model as the Docker Streamlit app
        # This is the model that's confirmed to work with Computer Use
        model_name = "claude-sonnet-4-6"
        print(f"🤖 Model: {model_name}")

        # Check if we're likely inside the Docker container
        in_container = False
        try:
            # Check if DISPLAY is set (should be :1 in container)
            display = os.getenv("DISPLAY")
            if display == ":1":
                in_container = True
                print(f"✅ Detected DISPLAY={display} (likely in Docker container)")
            else:
                print(f"⚠️  DISPLAY={display or 'not set'} (not in Docker container)")
                print("   Computer Use API may fail without access to X11 display")
        except Exception:
            pass

        print("=" * 80)

        # Call Computer Use API
        print("\n🚀 Starting Computer Use session...")
        print("(Claude will control a virtual browser to fill the FDA MedWatch form)\n")

        if not in_container:
            print("⚠️  WARNING: You may not be running inside the Docker container")
            print("   If this fails, try:")
            print("   1. Open http://localhost:8501 in your browser")
            print("   2. Copy the prompt from computer_use_prompt.txt")
            print("   3. Paste it into the Streamlit interface\n")

        try:
            # Use beta.messages for computer use with updated tool types
            # Sonnet 4.6 uses newer tool versions
            response = self.client.beta.messages.create(
                model=model_name,
                max_tokens=4096,
                tools=[
                    {
                        "type": "bash_20250124",
                        "name": "bash"
                    },
                    {
                        "type": "text_editor_20250728",
                        "name": "str_replace_editor"
                    },
                    {
                        "type": "computer_20250124",
                        "name": "computer",
                        "display_width_px": 1024,
                        "display_height_px": 768,
                        "display_number": 1
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                betas=["computer-use-2025-01-24"]
            )

            print("\n" + "=" * 80)
            print("📬 RESPONSE FROM COMPUTER USE")
            print("=" * 80)

            # Parse and display the response
            actions_taken = []
            for block in response.content:
                if block.type == "text":
                    print(f"\n💬 Claude says:\n{block.text}\n")
                elif block.type == "tool_use":
                    action_summary = f"{block.name}"
                    if block.name == "computer":
                        action = block.input.get("action", "unknown")
                        action_summary += f" - {action}"
                        print(f"\n🔧 Tool used: computer")
                        print(f"   Action: {action}")

                        if action == "screenshot":
                            print("   📸 Taking screenshot...")
                        elif action == "mouse_move":
                            print(f"   🖱️  Moving mouse to: {block.input.get('coordinate')}")
                        elif action == "left_click":
                            print(f"   👆 Clicking at: {block.input.get('coordinate')}")
                        elif action == "type":
                            text = block.input.get('text', '')
                            preview = text[:50] + "..." if len(text) > 50 else text
                            print(f"   ⌨️  Typing: {preview}")
                        elif action == "key":
                            print(f"   ⌨️  Pressing key: {block.input.get('text')}")

                    actions_taken.append(action_summary)


            return {
                "success": True,
                "response_id": response.id,
                "model": response.model,
                "stop_reason": response.stop_reason,
                "actions_taken": actions_taken,
                "message": "Computer Use session started successfully"
            }

        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ Error calling Computer Use API: {error_msg}")

            # Check if it's a model not found error
            if "404" in error_msg or "not_found_error" in error_msg:
                print("\n⚠️  MODEL NOT FOUND ERROR")
                print(f"The model '{model_name}' is not available on your API key.")
                print("\nPossible reasons:")
                print("  1. Your API key doesn't have access to Sonnet 4.6")
                print("  2. Your account is on a different tier/region")
                print("  3. Computer Use beta is not enabled for your account")
                print("\n💡 WORKAROUND:")
                print("  Use the Streamlit interface instead:")
                print(f"  1. Open http://localhost:8501")
                print(f"  2. The prompt is already saved in: {prompt_result['prompt_file']}")
                print(f"  3. Copy the prompt and paste it into the interface")
                print(f"  4. The Streamlit app has the Computer Use model configured correctly")

            return {
                "success": False,
                "error": error_msg,
                "fallback_prompt_file": prompt_result.get("prompt_file"),
                "recommendation": "Use Streamlit interface at http://localhost:8501"
            }


if __name__ == "__main__":
    # Test with patient data
    with open("patient_case_redacted.json", "r") as f:
        patient_data = json.load(f)

    filler = SimpleComputerUseFiller()
    result = filler.save_prompt_to_file(patient_data)

    print(f"\n✅ Done! Prompt saved to: {result['prompt_file']}")
