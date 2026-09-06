import pandas as pd


DATASET_PATH = "data/scope_to_proposal_synthetic_evaluation_dataset.xlsx"


def load_dataset():
    excel_file = pd.ExcelFile(DATASET_PATH)

    print("Available sheets:")
    for sheet in excel_file.sheet_names:
        print(f"- {sheet}")

    return excel_file


if __name__ == "__main__":
    load_dataset()