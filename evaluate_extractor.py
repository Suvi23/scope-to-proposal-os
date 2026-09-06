import json
from pathlib import Path

import openpyxl

from src.extractor import extract_requirements


# ============================================================
# CONFIG
# ============================================================

DATASET_PATH = Path(
    r"D:\scope-to-proposal-os\evaluation_dataset.xlsx"
)

OUTPUT_PATH = Path(
    r"D:\scope-to-proposal-os\extractor_evaluation_results.json"
)


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize(text):
    if text is None:
        return ""

    return (
        str(text)
        .strip()
        .lower()
        .replace(".", "")
        .replace(",", "")
        .replace(";", "")
    )


def words(text):
    return set(
        normalize(text)
        .replace("/", " ")
        .replace("-", " ")
        .split()
    )


# ============================================================
# SEMANTIC MATCHING
# ============================================================

def similarity(expected, actual):
    """
    Lightweight transparent keyword-overlap score.
    """

    expected_words = words(expected)
    actual_words = words(actual)

    if not expected_words:
        return 1.0

    if not actual_words:
        return 0.0

    overlap = expected_words & actual_words

    return len(overlap) / len(expected_words)


def list_score(expected_items, actual_items):
    """
    Calculates how well expected items are captured.
    """

    if not expected_items:
        return 1.0

    if not actual_items:
        return 0.0

    scores = []

    for expected in expected_items:

        best = 0.0

        for actual in actual_items:

            score = similarity(
                expected,
                actual
            )

            best = max(best, score)

        scores.append(best)

    return sum(scores) / len(scores)


# ============================================================
# LOAD DATASET
# ============================================================

def load_cases():

    if not DATASET_PATH.exists():

        raise FileNotFoundError(
            f"""
Dataset not found:

{DATASET_PATH}

Please make sure the uploaded Excel file exists.
"""
        )

    workbook = openpyxl.load_workbook(
        DATASET_PATH,
        data_only=True
    )

    sheet = workbook["12 Synthetic Cases"]

    headers = [
        cell.value
        for cell in sheet[1]
    ]

    cases = []

    for row in sheet.iter_rows(
        min_row=2,
        values_only=True
    ):

        record = dict(
            zip(headers, row)
        )

        cases.append(record)

    return cases


# ============================================================
# SPLIT GROUND TRUTH
# ============================================================

def split_items(value):

    if not value:
        return []

    return [
        item.strip()
        for item in str(value).split(";")
        if item.strip()
    ]


# ============================================================
# EVALUATE ONE CASE
# ============================================================

def evaluate_case(case):

    case_id = case["Case ID"]

    client_input = case["Raw client input"]

    print()
    print("=" * 70)
    print(f"CASE {case_id}")
    print("=" * 70)

    print(
        "\nClient request:"
    )

    print(client_input)

    # --------------------------------------------------------
    # Run extractor
    # --------------------------------------------------------

    try:

        result = extract_requirements(
            client_input
        )

        actual = result.model_dump()

    except Exception as error:

        print(
            f"\n❌ EXTRACTION FAILED"
        )

        print(error)

        return {
            "case_id": case_id,
            "status": "FAILED",
            "error": str(error)
        }

    # --------------------------------------------------------
    # Ground truth
    # --------------------------------------------------------

    expected_requirements = split_items(
        case["Expected requirements"]
    )

    expected_clear = split_items(
        case["Clear items"]
    )

    expected_ambiguities = split_items(
        case["Ambiguities"]
    )

    expected_risks = str(
        case["Risks_or_conflicts"] or ""
    )

    # --------------------------------------------------------
    # Actual output
    # --------------------------------------------------------

    actual_requirements = [
        item["requirement"]
        for item in actual["requirements"]
    ]

    actual_missing = actual[
        "missing_information"
    ]

    actual_constraints = actual[
        "constraints"
    ]

    actual_integrations = actual[
        "integrations"
    ]

    actual_channels = actual[
        "channels"
    ]

    # ========================================================
    # REQUIREMENT SCORE
    # ========================================================

    requirement_score = list_score(
        expected_requirements,
        actual_requirements
    )

    # ========================================================
    # AMBIGUITY SCORE
    # ========================================================

    ambiguity_score = list_score(
        expected_ambiguities,
        actual_missing
    )

    # ========================================================
    # GROUNDING CHECK
    # ========================================================

    input_lower = client_input.lower()

    known_integrations = [
        "crm",
        "shopify",
        "shiprocket",
        "calendly",
        "google calendar",
        "google sheets",
        "quickbooks",
        "pos",
        "hospital system"
    ]

    known_channels = [
        "whatsapp",
        "instagram",
        "website",
        "email",
        "phone",
        "sms"
    ]

    expected_integrations = [
        item
        for item in known_integrations
        if item in input_lower
    ]

    expected_channels = [
        item
        for item in known_channels
        if item in input_lower
    ]

    integration_score = list_score(
        expected_integrations,
        actual_integrations
    )

    channel_score = list_score(
        expected_channels,
        actual_channels
    )

    # ========================================================
    # CONSTRAINT SCORE
    # ========================================================

    constraint_indicators = [
        "must",
        "never",
        "within",
        "required",
        "mandatory",
        "non-negotiable",
        "24/7",
        "100%",
        "zero"
    ]

    explicit_constraint_language = [
        word
        for word in constraint_indicators
        if word in input_lower
    ]

    if not explicit_constraint_language:

        constraint_score = 1.0

    elif actual_constraints:

        constraint_score = 1.0

    else:

        constraint_score = 0.0

    # ========================================================
    # ASSUMPTION SAFETY
    # ========================================================

    if actual["assumptions"]:

        assumption_score = 0.0

    else:

        assumption_score = 1.0

    # ========================================================
    # TIMELINE
    # ========================================================

    timeline_expected = any(
        phrase in input_lower
        for phrase in [
            "today",
            "tomorrow",
            "this week",
            "next week",
            "3 days",
            "one week",
            "2 weeks",
            "two weeks",
            "month",
            "months"
        ]
    )

    if timeline_expected:

        timeline_score = (
            1.0
            if actual["timeline"]
            else 0.0
        )

    else:

        timeline_score = 1.0

    # ========================================================
    # OVERALL
    # ========================================================

    overall_score = (
        requirement_score * 0.35
        + ambiguity_score * 0.20
        + integration_score * 0.10
        + channel_score * 0.05
        + constraint_score * 0.15
        + assumption_score * 0.10
        + timeline_score * 0.05
    )

    # ========================================================
    # DISPLAY
    # ========================================================

    print()
    print("SCORES")
    print("-" * 40)

    print(
        f"Requirements:       {requirement_score:.1%}"
    )

    print(
        f"Ambiguity:           {ambiguity_score:.1%}"
    )

    print(
        f"Integrations:        {integration_score:.1%}"
    )

    print(
        f"Channels:            {channel_score:.1%}"
    )

    print(
        f"Constraints:         {constraint_score:.1%}"
    )

    print(
        f"Assumption Safety:   {assumption_score:.1%}"
    )

    print(
        f"Timeline:            {timeline_score:.1%}"
    )

    print(
        f"\nOVERALL:             {overall_score:.1%}"
    )

    # ========================================================
    # PRINT IMPORTANT OUTPUT
    # ========================================================

    print()
    print("EXTRACTED REQUIREMENTS:")

    for requirement in actual_requirements:

        print(
            f"  • {requirement}"
        )

    print()
    print("CONSTRAINTS:")

    for constraint in actual_constraints:

        print(
            f"  • {constraint}"
        )

    print()
    print("MISSING INFORMATION:")

    for item in actual_missing:

        print(
            f"  • {item}"
        )

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "case_id": case_id,
        "status": "PASSED",

        "scores": {
            "requirements": requirement_score,
            "ambiguity": ambiguity_score,
            "integrations": integration_score,
            "channels": channel_score,
            "constraints": constraint_score,
            "assumption_safety": assumption_score,
            "timeline": timeline_score,
            "overall": overall_score
        },

        "actual_output": actual,

        "ground_truth": {
            "expected_requirements":
                expected_requirements,

            "clear_items":
                expected_clear,

            "ambiguities":
                expected_ambiguities,

            "risks_or_conflicts":
                expected_risks
        }
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("SCOPE-TO-PROPOSAL AI OS")
    print("EXTRACTOR EVALUATION")
    print("=" * 70)

    # --------------------------------------------------------
    # Load cases
    # --------------------------------------------------------

    cases = load_cases()

    print()
    print(
        f"Loaded {len(cases)} synthetic cases."
    )

    results = []

    # --------------------------------------------------------
    # Evaluate all cases
    # --------------------------------------------------------

    for case in cases:

        result = evaluate_case(
            case
        )

        results.append(
            result
        )

    # --------------------------------------------------------
    # Successful cases
    # --------------------------------------------------------

    successful = [
        result
        for result in results
        if result["status"] == "PASSED"
    ]

    # --------------------------------------------------------
    # Aggregate scores
    # --------------------------------------------------------

    dimensions = [
        "requirements",
        "ambiguity",
        "integrations",
        "channels",
        "constraints",
        "assumption_safety",
        "timeline",
        "overall"
    ]

    averages = {}

    for dimension in dimensions:

        if not successful:

            averages[dimension] = 0.0

        else:

            averages[dimension] = (
                sum(
                    result["scores"][dimension]
                    for result in successful
                )
                / len(successful)
            )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()
    print()
    print("=" * 70)
    print("FINAL EVALUATION")
    print("=" * 70)

    print(
        f"\nCases evaluated:     {len(results)}"
    )

    print(
        f"Successful cases:    {len(successful)}"
    )

    print()

    for dimension, score in averages.items():

        label = (
            dimension
            .replace("_", " ")
            .title()
        )

        print(
            f"{label:25s} {score:.1%}"
        )

    # ========================================================
    # CASE BREAKDOWN
    # ========================================================

    print()
    print("=" * 70)
    print("CASE SCORES")
    print("=" * 70)

    for result in successful:

        print(
            f"{result['case_id']:6s}"
            f" {result['scores']['overall']:.1%}"
        )

    # ========================================================
    # WEAK CASES
    # ========================================================

    print()
    print("=" * 70)
    print("CASES NEEDING REVIEW")
    print("=" * 70)

    weak_cases = [
        result
        for result in successful
        if result["scores"]["overall"] < 0.80
    ]

    if not weak_cases:

        print(
            "\n🎉 No case scored below 80%."
        )

    else:

        for result in weak_cases:

            print(
                f"\n⚠️ {result['case_id']}: "
                f"{result['scores']['overall']:.1%}"
            )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    evaluation = {
        "dataset": str(
            DATASET_PATH
        ),

        "cases_evaluated":
            len(results),

        "successful_cases":
            len(successful),

        "averages":
            averages,

        "results":
            results
    }

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            evaluation,
            file,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 70)

    print(
        "Detailed results saved to:"
    )

    print(
        OUTPUT_PATH
    )

    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()