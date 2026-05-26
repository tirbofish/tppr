import argparse
import json

import tppr_paper_utils

parser = argparse.ArgumentParser(
    description="Converts a past paper into a format that can be accepted by 'Thribhus Past Paper Repository'"
)
parser.add_argument("input", help="Path to the input paper file")
parser.add_argument("output", help="Path to the output paper file")
parser.add_help = True


def main():
    args = parser.parse_args()

    with open(args.input, "rb") as file:
        with tppr_paper_utils.PaperExtractor(file) as extract:
            output = extract.extract()
            with open(args.output, "w") as out:
                out.write(json.dumps(output, indent=2))
                print("Successfully converted paper")


if __name__ == "__main__":
    main()
