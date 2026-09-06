from src.extractor import extract_requirements
from src.analyzer import analyze_risks


client_request = """
We run a multi-specialty clinic. Patients message us for
doctor availability, fees, symptoms and appointment booking.
We want an AI that answers symptoms, tells patients what
disease they have, recommends medicines, books appointments,
sends reminders and follows up after visits. It should
integrate with our hospital system and support Hindi,
Marathi and English. We want it to replace most front-desk work.
"""


print("=" * 70)
print("REQUIREMENT EXTRACTION")
print("=" * 70)


requirement_map = extract_requirements(
    client_request
)


print(
    requirement_map.model_dump_json(
        indent=2
    )
)


print()
print("=" * 70)
print("RISK ANALYSIS")
print("=" * 70)


risks = analyze_risks(
    requirement_map
)


for risk in risks:

    print()
    print(
        f"[{risk.severity.upper()}] "
        f"{risk.type}"
    )

    print(
        f"Issue: {risk.issue}"
    )

    print(
        f"Evidence: {risk.evidence}"
    )

    print(
        f"Impact: {risk.impact}"
    )

    print(
        f"Confirmation required: "
        f"{risk.needs_confirmation}"
    )