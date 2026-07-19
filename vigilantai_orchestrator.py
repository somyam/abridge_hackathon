"""
VigilantAI - Multi-Agent Orchestrator
Coordinates the complete pipeline: PHI Redaction → Extraction → Computer Use
"""

import json
import os
import sys
from datetime import datetime

from agent_1_phi_redactor import PHIRedactor
from agent_2_adverse_event_extractor import AdverseEventExtractor
from agent_3_computer_use_filler import ComputerUseFormFiller


class VigilantAIOrchestrator:
    """
    Orchestrates the complete VigilantAI pipeline
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        # Initialize agents
        self.phi_redactor = PHIRedactor(random_seed=12345)
        self.adverse_event_extractor = AdverseEventExtractor(api_key=self.api_key)
        self.computer_use_filler = ComputerUseFormFiller(api_key=self.api_key)

        self.execution_log = []

    def run_pipeline(
        self,
        patient_data_file: str,
        portal_url: str = "https://vaers.hhs.gov/esub/EsubController",
        portal_name: str = "VAERS"
    ) -> dict:
        """
        Run the complete VigilantAI pipeline

        Args:
            patient_data_file: Path to patient JSON file
            portal_url: URL of the FDA form to fill
            portal_name: Name of the portal

        Returns:
            Dict with complete pipeline results
        """

        print("\n" + "=" * 80)
        print("🚨 VIGILANTAI - AUTONOMOUS ADVERSE EVENT REPORTING SYSTEM")
        print("=" * 80)
        print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Input: {patient_data_file}")
        print(f"Target: {portal_name} ({portal_url})")
        print("\n" + "=" * 80)

        # Load patient data
        print("\n📂 Loading patient data...")
        try:
            with open(patient_data_file, "r") as f:
                patient_data = json.load(f)
            print(f"  ✅ Loaded patient data")
            print(f"     Patient ID: {patient_data['patient_demographics']['patient_id']}")
            print(f"     Encounters: {len(patient_data['encounters'])}")
        except FileNotFoundError:
            print(f"  ❌ File not found: {patient_data_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"  ❌ Invalid JSON: {e}")
            sys.exit(1)

        # AGENT 1: PHI Redaction
        print("\n" + "─" * 80)
        print("AGENT 1: PHI REDACTOR")
        print("─" * 80)

        redacted_data = self.phi_redactor.redact_patient_data(patient_data)

        self.execution_log.append({
            "agent": "PHI_Redactor",
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "output_file": "patient_case_redacted.json"
        })

        # Save redacted data
        with open("patient_case_redacted.json", "w") as f:
            json.dump(redacted_data, f, indent=2)

        print(f"\n✅ Agent 1 Complete")
        print(f"   Output: patient_case_redacted.json")

        # AGENT 2: Adverse Event Extraction
        print("\n" + "─" * 80)
        print("AGENT 2: ADVERSE EVENT EXTRACTOR")
        print("─" * 80)

        fda_data = self.adverse_event_extractor.extract_adverse_event(redacted_data)

        self.execution_log.append({
            "agent": "Adverse_Event_Extractor",
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "has_reportable_event": fda_data.get("has_reportable_event", False),
            "output_file": "fda_extracted_data.json"
        })

        # Save FDA data
        with open("fda_extracted_data.json", "w") as f:
            json.dump(fda_data, f, indent=2)

        print(f"\n✅ Agent 2 Complete")
        print(f"   Output: fda_extracted_data.json")
        print(f"   Reportable Event: {fda_data.get('has_reportable_event')}")

        # Check if reportable
        if not fda_data.get("has_reportable_event"):
            print("\n" + "=" * 80)
            print("ℹ️  NO REPORTABLE ADVERSE EVENT IDENTIFIED")
            print("=" * 80)
            print("Pipeline stopped - no FDA reporting required.")
            return {
                "success": True,
                "reportable": False,
                "message": "No adverse event requiring FDA reporting identified",
                "execution_log": self.execution_log
            }

        # AGENT 3: Computer Use Form Filler
        print("\n" + "─" * 80)
        print("AGENT 3: COMPUTER USE FORM FILLER")
        print("─" * 80)

        computer_use_result = self.computer_use_filler.fill_fda_form(
            fda_data=fda_data,
            portal_url=portal_url,
            portal_name=portal_name
        )

        self.execution_log.append({
            "agent": "Computer_Use_Form_Filler",
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "prompt_file": computer_use_result.get("prompt_file"),
            "portal_url": portal_url
        })

        print(f"\n✅ Agent 3 Complete")
        print(f"   Output: {computer_use_result.get('prompt_file')}")

        # Final summary
        print("\n" + "=" * 80)
        print("✅ VIGILANTAI PIPELINE COMPLETE")
        print("=" * 80)

        print("\n📊 PIPELINE SUMMARY:")
        print("─" * 80)
        print(f"✓ Agent 1: PHI Redaction → patient_case_redacted.json")
        print(f"✓ Agent 2: Adverse Event Extraction → fda_extracted_data.json")
        print(f"✓ Agent 3: Computer Use Prompt → computer_use_prompt.txt")
        print("─" * 80)

        print("\n🎯 NEXT STEPS - COMPUTER USE EXECUTION:")
        print("=" * 80)
        for i, instruction in enumerate(computer_use_result.get("instructions", []), 1):
            print(f"{i}. {instruction}")
        print("=" * 80)

        print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Save execution log
        log_data = {
            "pipeline_run": datetime.now().isoformat(),
            "input_file": patient_data_file,
            "target_portal": portal_name,
            "reportable_event": True,
            "execution_log": self.execution_log,
            "outputs": {
                "redacted_data": "patient_case_redacted.json",
                "fda_data": "fda_extracted_data.json",
                "computer_use_prompt": computer_use_result.get("prompt_file")
            }
        }

        with open("vigilantai_execution_log.json", "w") as f:
            json.dump(log_data, f, indent=2)

        print(f"\n📋 Execution log saved to: vigilantai_execution_log.json")

        return {
            "success": True,
            "reportable": True,
            "execution_log": self.execution_log,
            "computer_use_result": computer_use_result,
            "outputs": log_data["outputs"]
        }


def main():
    """Main entry point"""

    print("\n" + "=" * 80)
    print("VIGILANTAI - Multi-Agent Adverse Event Reporting System")
    print("=" * 80)
    print("\nArchitecture:")
    print("  Agent 1: PHI Redactor (Local - HIPAA compliant)")
    print("  Agent 2: Adverse Event Extractor (Claude-powered)")
    print("  Agent 3: Computer Use Form Filler (Autonomous browser automation)")
    print("=" * 80)

    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n❌ ANTHROPIC_API_KEY not set!")
        print("\nSet it with:")
        print('  export ANTHROPIC_API_KEY="sk-ant-your-key-here"')
        sys.exit(1)

    # Check input file
    input_file = "patient_adverse_event_case.json"
    if not os.path.exists(input_file):
        print(f"\n❌ Input file not found: {input_file}")
        sys.exit(1)

    # Confirm execution
    print(f"\n📋 Input file: {input_file}")
    print(f"🎯 Target: VAERS (https://vaers.hhs.gov/esub/EsubController)")

    proceed = input("\nRun VigilantAI pipeline? (yes/no): ").strip().lower()
    if proceed not in ['yes', 'y']:
        print("❌ Cancelled by user")
        sys.exit(0)

    # Initialize orchestrator
    orchestrator = VigilantAIOrchestrator()

    # Run pipeline
    try:
        result = orchestrator.run_pipeline(
            patient_data_file=input_file,
            portal_url="https://vaers.hhs.gov/esub/EsubController",
            portal_name="VAERS"
        )

        if result["success"] and result["reportable"]:
            print("\n" + "=" * 80)
            print("🎉 SUCCESS - READY FOR COMPUTER USE EXECUTION")
            print("=" * 80)
            print("\nThe pipeline has prepared everything for autonomous form filling.")
            print("Follow the instructions above to complete the Computer Use step.")

    except Exception as e:
        print(f"\n❌ Pipeline error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
