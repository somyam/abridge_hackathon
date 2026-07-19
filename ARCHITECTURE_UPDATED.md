# VigilantAI - Updated Architecture

## **Overview**

VigilantAI is now a **fully autonomous adverse event reporting system** with 3 specialized agents:

1. **Agent 1: Adverse Event Detector** (Claude-powered)
2. **Agent 2: PHI Redactor** (Local processing)
3. **Agent 3: Computer Use Form Filler** (Auto-submit to FDA)

---

## **Complete Pipeline Flow**

```
Raw Patient EHR Data
(encounters, medications, symptoms, labs - NO pre-filled adverse event summary)
         ↓
┌────────────────────────────────────────────────────────────────┐
│  AGENT 1: Adverse Event Detector                               │
│  ─────────────────────────────────────────────────────────     │
│  • Uses Claude Sonnet 4-6 to analyze encounters                │
│  • Identifies temporal relationships (symptoms after drug)     │
│  • Detects drug discontinuations                              │
│  • Recognizes known drug-AE patterns                          │
│  • Outputs structured adverse events with confidence scores   │
│  • Determines FDA reportability                               │
└────────────────────────────────────────────────────────────────┘
         ↓
  adverse_events_detected.json
  {
    "adverse_events_detected": [
      {
        "suspect_drug": {...},
        "adverse_event_description": "...",
        "severity": "Serious",
        "fda_reportable": true,
        "fda_criteria_met": ["hospitalization", "intervention required"],
        "confidence_level": "High"
      }
    ]
  }
         ↓
┌────────────────────────────────────────────────────────────────┐
│  FDA REPORTABILITY CHECK                                       │
│  • Checks if any detected events meet FDA criteria:           │
│    - Patient death                                            │
│    - Life-threatening                                         │
│    - Hospitalization                                          │
│    - Persistent disability                                    │
│    - Congenital anomaly                                       │
│    - Required intervention to prevent impairment              │
│  • If NO reportable events → STOP                            │
│  • If YES reportable events → Continue to Agent 2            │
└────────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────────┐
│  AGENT 2: PHI Redactor                                         │
│  ─────────────────────────────────────────────────────────     │
│  • Runs 100% locally (NO API calls)                           │
│  • Strips all patient identifiable information:               │
│    - Names → "NAME_A1B2C3D4"                                  │
│    - Patient IDs → "PATIENT_D9FD325B"                         │
│    - Dates → Shifted by consistent offset                    │
│    - Locations → "City_XYZ"                                   │
│    - Phone → "XXX-XXX-XXXX"                                   │
│  • Uses deterministic hashing (same patient = same token)    │
│  • HIPAA compliant de-identification                         │
└────────────────────────────────────────────────────────────────┘
         ↓
  patient_case_redacted.json
  (Safe to send to external APIs)
         ↓
┌────────────────────────────────────────────────────────────────┐
│  AGENT 3: Computer Use Form Filler                             │
│  ─────────────────────────────────────────────────────────     │
│  • Generates detailed FDA MedWatch Form 3500 prompt            │
│  • Calls Anthropic Computer Use API:                          │
│    - Model: claude-sonnet-4-6                                 │
│    - Tools: computer_20241022, bash_20241022                  │
│    - Beta: computer-use-2025-01-24                            │
│  • Claude controls virtual browser:                           │
│    1. Opens Firefox                                           │
│    2. Navigates to FDA MedWatch portal                        │
│    3. Takes screenshots to see form                           │
│    4. Analyzes form fields visually                           │
│    5. Fills in patient data, adverse events, drug info        │
│    6. Handles multi-page forms                                │
│    7. STOPS before final "Submit" button                      │
│  • Returns screenshot for human review                        │
└────────────────────────────────────────────────────────────────┘
         ↓
  FDA MedWatch Form 3500 Filled
  (Awaiting human verification & submission)
```

---

## **Key Features**

### **1. Fully Autonomous Adverse Event Detection**

**Input**: Raw patient encounters (no manual adverse event documentation required)

**Agent 1 analyzes**:
- **Temporal relationships**: "Conjunctivitis appeared 2 weeks after starting Dupixent"
- **Drug discontinuations**: "Dupixent stopped at Visit 5 due to severe eye symptoms"
- **Worsening conditions**: "Mild dry eyes at Visit 4 → Severe conjunctivitis at Visit 5"
- **Known adverse event patterns**: "Dupixent is known to cause conjunctivitis in ~10% of patients"
- **Rare/unexpected events**: Can identify novel adverse events not previously documented
  - Example: New symptom appearing after drug initiation with no prior reports
  - Based on temporal correlation, not just known drug-AE databases

**Output**: Structured adverse events with:
- Suspect drug (generic + brand name)
- Event description
- Severity (Mild/Moderate/Serious)
- Causality (Definite/Probable/Possible/Unlikely)
- Timeline (drug start → event onset → drug stop)
- Clinical evidence
- FDA reportability determination
- Confidence level

### **2. HIPAA-Compliant PHI Protection**

**Local Processing**:
- Agent 2 runs entirely on local machine
- NO API calls during de-identification
- No patient data leaves machine in identifiable form

**De-identification Methods**:
- **Hashing**: SHA256 with random seed → consistent tokens
- **Date shifting**: Random offset (-180 to +180 days), consistent per patient
- **Location redaction**: Cities → "City_XYZ", Zip → "XXXXX"
- **Phone/email**: Fully masked

**Result**: Only de-identified data sent to Anthropic Computer Use API

### **3. Intelligent FDA Reportability Assessment**

**Agent 1** determines if event meets FDA MedWatch criteria:

| Criterion | How Detected |
|-----------|--------------|
| Death | Searches for "death", "fatal", "died" in outcome/description |
| Life-threatening | Checks severity, seriousness criteria, event description |
| Hospitalization | Looks for "hospitalized", "hospital admission", "prolongation" |
| Disability | Searches for "disability", "impairment", "permanent damage" |
| Congenital anomaly | Checks for "birth defect", "congenital" |
| Intervention required | Identifies "required intervention to prevent permanent impairment" |

**Pipeline behavior**:
- If **NO reportable events** → Pipeline stops, no FDA report filed
- If **reportable events** → Continues to PHI redaction and form submission

### **4. Autonomous Browser Control (Computer Use)**

**How it works**:

```python
# Agent 3 calls Computer Use API
response = client.messages.create(
    model="claude-sonnet-4-6",
    tools=[
        {"type": "computer_20241022"},  # Browser/desktop control
        {"type": "bash_20241022"},      # Terminal commands
        {"type": "text_editor_20241022"} # File operations
    ],
    betas=["computer-use-2025-01-24"]
)
```

**Tool execution loop**:
1. `bash`: Launch Firefox, navigate to URL
2. `computer screenshot`: Take screenshot of form
3. **Claude analyzes visually**: "I see the patient ID field at coordinates [450, 200]"
4. `computer left_click [450, 200]`: Click the field
5. `computer type "PATIENT_D9FD325B"`: Type the value
6. `computer screenshot`: Verify entry
7. Repeat for all fields across multiple form pages
8. `computer screenshot`: Final review before stopping

**Safety gate**: Claude stops before clicking "Submit" and returns screenshot for human verification

---

## **File Structure**

```
abridge/
├── patient_adverse_event_case.json           # Input: Raw patient data
│
├── agent_1_adverse_event_detector.py         # Agent 1: Autonomous AE detection
├── agent_1_phi_redactor.py                   # Agent 2: Local PHI redaction
├── simple_computer_use_filler.py             # Agent 3: Computer Use form filling
│
├── simple_orchestrator.py                    # Main pipeline coordinator
│
├── adverse_events_detected.json              # Output: Agent 1 results
├── patient_case_redacted.json                # Output: Agent 2 results
│
└── ARCHITECTURE_UPDATED.md                   # This file
```

---

## **Usage**

### **Run the complete pipeline**:

```bash
python simple_orchestrator.py
```

### **Expected Output**:

```
================================================================================
VIGILANTAI - AUTONOMOUS ADVERSE EVENT REPORTING
================================================================================
Agent 1: Adverse Event Detection (Claude-powered)
Agent 2: PHI Redaction (Local)
Agent 3: Computer Use Form Submission (Auto)
================================================================================

📂 Loading patient data: patient_adverse_event_case.json
⚠️  Removing pre-filled adverse_event_summary (testing autonomous detection)

────────────────────────────────────────────────────────────────────────────────
AGENT 1: ADVERSE EVENT DETECTOR
────────────────────────────────────────────────────────────────────────────────

🔍 Analyzing patient encounters for adverse drug events...
================================================================================

📊 Patient Profile:
   Patient ID: PT-2847
   Age: 32
   Sex: Female
   Total Encounters: 5

🤖 Sending to Claude for analysis...
✅ Claude analysis complete - 1 event(s) found

================================================================================
DETECTION RESULTS:
================================================================================

✅ Found 1 adverse event(s)

┌─ Adverse Event #1 ───────────────────────────────────────┐
│
│ 💊 SUSPECT DRUG:
│    Generic: Dupilumab
│    Brand:   Dupixent
│
│ ⚠️  ADVERSE EVENT:
│    Description: Severe bilateral conjunctivitis with mucopurulent discharge
│    Severity:    Serious
│    Outcome:     Recovering
│
│ 📅 TIMELINE:
│    Drug Started:  2023-09-05
│    Event Onset:   2023-12-25
│    Drug Stopped:  2024-01-03
│    Time to Onset: Approximately 3.5 months after initiation
│
│ 🎯 CONFIDENCE: High
│    FDA Reportable: YES
│
└──────────────────────────────────────────────────────────────┘

✅ Agent 1 Complete
   Output: adverse_events_detected.json
   Adverse Events Found: 1

────────────────────────────────────────────────────────────────────────────────
AGENT 2: PHI REDACTOR
────────────────────────────────────────────────────────────────────────────────

🔒 De-identifying patient data (100% local, no API calls)...

✅ Agent 2 Complete
   Output: patient_case_redacted.json

────────────────────────────────────────────────────────────────────────────────
FDA REPORTING CRITERIA ASSESSMENT:
────────────────────────────────────────────────────────────────────────────────

✅ 1 REPORTABLE EVENT(S) IDENTIFIED

Event #1:
  Drug: Dupilumab (Dupixent)
  Event: Severe bilateral conjunctivitis with mucopurulent discharge
  Severity: Serious
  FDA Criteria Met:
    ✓ Required intervention to prevent permanent impairment (vision)
    ✓ Medically important event

📋 These events meet FDA reporting requirements.
   Proceeding to Agent 3: Computer Use Form Submission

────────────────────────────────────────────────────────────────────────────────
AGENT 3: COMPUTER USE FORM FILLER
────────────────────────────────────────────────────────────────────────────────

🖥️  AUTO-SUBMITTING TO COMPUTER USE API...
================================================================================
✅ Prompt generated (3247 characters)
🎯 Target URL: https://www.accessdata.fda.gov/scripts/medwatch/...
🤖 Model: claude-sonnet-4-6
================================================================================

🚀 Starting Computer Use session...
(Claude will control a virtual browser to fill the FDA MedWatch form)

================================================================================
📬 RESPONSE FROM COMPUTER USE
================================================================================

🔧 Tool used: computer
   Action: screenshot
   📸 Taking screenshot...

💬 Claude says:
I can see the FDA MedWatch Form 3500. I'll begin filling in the patient information
and adverse event details...

🔧 Tool used: computer
   Action: left_click
   👆 Clicking at: [450, 200]

🔧 Tool used: computer
   Action: type
   ⌨️  Typing: PATIENT_D9FD325B

... (continues until form complete)

================================================================================
✅ PIPELINE COMPLETE - COMPUTER USE INITIATED
================================================================================
Generated Files:
  1. adverse_events_detected.json
  2. patient_case_redacted.json

Computer Use Status:
  Response ID: msg_01ABC123...
  Model: claude-sonnet-4-6
  Actions taken: 15
================================================================================
```

---

## **Key Capability: Detecting Rare & Novel Adverse Events**

### **Why This Matters:**

Traditional pharmacovigilance systems rely on:
- **Known adverse event databases** - Only detect what's already documented
- **Rule-based alerts** - Miss unexpected drug-symptom combinations
- **Manual provider reporting** - Depends on provider recognizing the pattern

### **VigilantAI's Approach:**

**Agent 1 uses temporal pattern recognition**, not just known drug-AE databases:

```
Example: Detecting a Rare Event

Patient Timeline:
  Visit 1: Starts new medication "DrugX" for condition A
  Visit 2 (2 weeks later): Reports strange tingling in fingers
  Visit 3 (1 month later): Tingling worsening, now bilateral
  Visit 4 (2 months later): DrugX discontinued, tingling resolves within days

Claude Analysis:
  ✓ Temporal relationship: Symptom started after drug initiation
  ✓ Dose-response: Worsened over time while on drug
  ✓ Dechallenge: Resolved after drug stopped
  ✓ Causality: Probable

  → Reports to FDA even if "DrugX → tingling" is NOT in literature
  → This could be the FIRST report of this adverse event
  → Critical for FDA signal detection
```

### **Detection Algorithm:**

1. **Start with temporal correlation** (not known patterns)
   - Did a NEW symptom appear after drug start?
   - Did an EXISTING symptom worsen after drug start?

2. **Assess strength of evidence**
   - Time to onset (days? weeks? months?)
   - Dechallenge (did it improve when drug stopped?)
   - Re-challenge (did it recur if drug restarted?)
   - Alternative explanations (other drugs, disease progression, comorbidities)

3. **Assign causality**
   - **Definite**: Positive re-challenge
   - **Probable**: Clear temporal relationship + dechallenge + no other explanation
   - **Possible**: Temporal relationship but could be other causes
   - **Unlikely**: Temporal relationship but clearly explained by other factors

4. **Report if medically significant**
   - Serious events (hospitalization, disability, life-threatening) → Always report
   - Moderate events → Report if causality ≥ Possible
   - Mild events → Report if causality ≥ Probable

### **Real-World Impact:**

**FDA relies on initial case reports to detect signals:**
- First few reports of rare AE → Investigation triggered
- Pattern emerges across multiple reports → Safety review
- If confirmed → Drug label update, boxed warning, or market withdrawal

**VigilantAI can detect the "first case" that starts this process**

---

## **Advantages Over Previous Architecture**

| Aspect | Old (3-agent with structured extraction) | New (3-agent with autonomous detection) |
|--------|------------------------------------------|----------------------------------------|
| **Input** | Required pre-filled `adverse_event_summary` | Works with raw encounter data only |
| **Autonomy** | Depended on human documenting AE | Fully autonomous AE detection |
| **Detection** | None (assumed AE already identified) | Claude analyzes temporal patterns |
| **Flexibility** | Only worked with known AE format | Discovers unexpected adverse events |
| **Rare Events** | Could not detect novel AEs | **Can detect first-ever reports of rare AEs** |
| **Use Case** | Automate reporting of known AEs | Discover + report both known AND novel AEs |

---

## **Technical Details**

### **Agent 1: Adverse Event Detector**

**File**: `agent_1_adverse_event_detector.py`

**Model**: `claude-sonnet-4-6`

**Prompt Strategy**:
- Provides complete encounter history
- Asks Claude to identify temporal relationships
- Requires structured JSON output
- Includes FDA reporting criteria in prompt

**Output Format**:
```json
{
  "adverse_events": [
    {
      "suspect_drug": {
        "generic_name": "Dupilumab",
        "brand_name": "Dupixent",
        "dose": "300mg",
        "route": "Subcutaneous"
      },
      "adverse_event_description": "Severe bilateral conjunctivitis...",
      "severity": "Serious",
      "outcome": "Recovering",
      "causality": "Probable",
      "timeline": {
        "drug_start_date": "2023-09-05",
        "event_onset_date": "2023-12-25",
        "drug_stop_date": "2024-01-03",
        "time_to_onset": "3.5 months"
      },
      "clinical_evidence": "Patient had no history of conjunctivitis...",
      "fda_reportable": true,
      "fda_criteria_met": ["intervention required"],
      "confidence_level": "High"
    }
  ]
}
```

### **Agent 2: PHI Redactor**

**File**: `agent_1_phi_redactor.py`

**Processing**: 100% local, no API calls

**Methods**:
- `_generate_token()`: SHA256 hashing with random seed
- `_shift_date()`: Consistent date offset per patient
- `redact_patient_data()`: Main redaction function

### **Agent 3: Computer Use Form Filler**

**File**: `simple_computer_use_filler.py`

**API Configuration**:
- Model: `claude-sonnet-4-6`
- Tools: `computer_20241022`, `bash_20241022`, `text_editor_20241022`
- Beta: `computer-use-2025-01-24`
- Max tokens: 4096

**Prompt includes**:
- De-identified patient demographics
- All detected adverse events with full details
- Encounter summaries
- FDA MedWatch Form 3500 section-by-section instructions

---

## **Safety & Compliance**

✅ **HIPAA Compliant**: All PHI stripped before external API calls

✅ **Human-in-the-Loop**: Computer Use stops before final submission

✅ **Auditable**: All intermediate outputs saved (detected events, redacted data)

✅ **Transparent**: Complete logging of all agent actions

✅ **Reversible**: Human can review and cancel before final submission

---

## **Future Enhancements**

1. **Multi-patient batch processing**: Analyze entire cohorts
2. **Real-time EHR integration**: Connect to live EHR systems
3. **Post-submission tracking**: Monitor FDA case numbers
4. **Feedback loop**: Learn from FDA responses to improve detection
5. **Multi-language support**: International adverse event reporting
