TITLE: Scope-to-Proposal AI OS:
 An AI-powered workflow that converts unstructured client inquiries into validated, QA-checked, client-ready PDF proposals in under 10 minutes.

DEMO VIDEO OF PROJECT: https://youtu.be/aSASjzf-41w

What It Does:


Client Request → Requirements → Risks → Discovery → Scope → Pitch → Proposal → QA → PDF

Paste a messy client inquiry (email, WhatsApp, call notes)
Review AI-extracted requirements and identified risks
Answer one round of discovery questions (or mark as unresolved)
Validate scope — confirmed, modified, rejected, or unresolved
Download a professional PDF proposal with safety boundaries and open items


How to Use the System :

No coding, no complex prompts, no technical skills required.
Follow these 5 simple steps to turn any messy client inquiry into a professional PDF proposal in under 10 minutes.

Step 1: Paste Your Client's Request 

Open the app in your web browser.
Enter your Client Name (e.g., BrightSmile Dental Clinic).
Select where the message came from (Email, WhatsApp, Web Form, or Phone Call).
Copy and paste the client’s raw email, text, or meeting notes into the Client Request box.
Click Analyze Client Request.

Step 2: Review What the AI Found 

Requirements (Stage 02): The AI extracts clear, individual checklist items from the messy client message.
Risk Analysis (Stage 03): The AI automatically flags ambiguities, technical risks, and safety concerns (like medical/legal boundaries).
Click Start Discovery → to move forward.

Step 3: Answer Simple Discovery Questions 
You will see a list of simple, business-focused discovery questions. Each question is tied to a specific risk.
Type the client's answer in plain English into each box (e.g., "We use Google Calendar for bookings and escalation goes to front desk").
If the client hasn't decided on an answer yet, check the box "Mark as unresolved". The system will safely carry it forward as an Open Item without stopping the proposal.
Click Validate Scope & Generate Proposal →.

Step 4: Review Your AI Pitch & Proposal 

Validated Scope (Stage 05): See which features are confirmed, modified, or set aside.
AI Pitch (Stage 06): Read a short, tailored value pitch ready to send in an email or say on a call.
Proposal (Stage 07): Review your complete proposal — Executive Summary, Scope Inclusions, Safety Exclusions, Timeline, and Next Steps.
If you want to change anything, click 🔄 Regenerate Proposal. Otherwise, click Continue to Proposal QA →.

Step 5: Automatic Quality Audit & PDF Download 

Proposal QA (Stage 08): The system automatically audits the proposal against safety, legal, and scope accuracy rules.
If QA Passes ✅: The proposal is certified safe and accurate.
Click Continue to Final Delivery → and hit ⬇️ Download Approved Proposal (PDF).
Your professional, branded PDF proposal is ready to email directly to your client!

 Built-in Safety Guarantee: If the AI accidentally generates an unsafe claim (like promising 100% revenue increases or illegal medical advice), the QA Gate will Lock Final Delivery and show you exactly what needs fixing.


Quick Start:

Prerequisites:

Python 3.10+
A Groq API key (free tier works): console.groq.com


Setup (3 steps)
Bash

# 1. Clone and install
git clone <repository-url>
cd scope-to-proposal-ai-os
pip install -r requirements.txt

# 2. Configure your API key
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 3. Run
streamlit run app.py



.env File sample:


GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=openai/gpt-oss-20b


Example Usage:

Example 1: Dental Clinic 

Input:  "We are a dental clinic and want an AI assistant for our website and WhatsApp. We want to answer patient inquiries 24/7, qualify leads, and book appointments into Google Calendar. We want more bookings, but the AI must not give medical advice."

Output: A 3-page PDF proposal with executive summary, scope inclusions, medical safety exclusions, implementation timeline, and open items.

Example 2: Law Firm

Input:"Automate client intake for our immigration law practice. Screen eligibility and schedule consultations."

Output: A scoped proposal with legal-advice boundaries and human-review checkpoints.

Example 3: HVAC Company

Input:"AI to handle emergency repair calls, schedule technicians, and send follow-up quotes."

Output: A proposal with scheduling scope, pricing boundaries, and integration requirements.



Architecture:


src/
├── schemas.py              # Pydantic data contracts (single source of truth)
├── extractor.py            # Client request → structured requirements
├── analyzer.py             # Requirements → risk analysis
├── discovery.py            # Risks → discovery questions (exactly one round)
├── scope_validator.py      # Discovery answers → validated scope
├── pitch_generator.py      # Validated scope → client pitch
├── proposal_generator.py   # Validated scope → full proposal
├── proposal_qa.py          # Deterministic + AI quality assurance
└── pipeline.py             # Orchestrator
app.py                      # Streamlit UI
ui/styles.py                # Design system



Key Design Decisions:


Decision
Rationale
One discovery round only
SMBs cannot sustain multi-round consulting workflows
Unresolved items → open items
Proposals proceed with transparency rather than blocking
Pydantic strict schemas
Prevents LLM hallucination from corrupting downstream stages
2-tier Groq execution
Bypasses server-side JSON validation failures on free-tier models
Deterministic + AI QA
Catches both structural violations and semantic safety issues




Limitations:

Requires a Groq API key (free tier has rate limits)
Proposal quality depends on the detail of the client's original request
Medical and legal proposals require human review before delivery
Does not generate pricing or contract terms

License:MIT


