"""Package CLI entrypoint and argument parsing."""

import argparse

from .generate_mazes import DEFAULT_DIFFICULTY, DEFAULT_LOCALE, LOCALIZATIONS
from .generate_mazes import MIN_PATH_FACTOR, GenerationOptions, run_generation


def build_parser():
    parser = argparse.ArgumentParser(
        description="Generate a printable A4 black-and-white maze booklet for children."
    )
    parser.add_argument("--output", default="output/mazes.pdf", help="output PDF file")
    parser.add_argument("--pages", type=int, default=20, help="number of mazes")
    parser.add_argument(
        "--difficulty",
        type=float,
        default=DEFAULT_DIFFICULTY,
        help="overall/average difficulty (e.g. 1.0 easy ... 4.0 hard, or more). "
        "Default: %(default)s",
    )
    parser.add_argument("--seed", type=int, default=None,
                        help="fixed seed for a reproducible PDF (default: random)")
    parser.add_argument(
        "--min-path-factor",
        type=float,
        default=MIN_PATH_FACTOR,
        help="minimum solution length as a fraction of n*n cells "
        "(0 < f <= 1; higher = longer forced route, more re-carving). "
        "Default: %(default)s",
    )
    parser.add_argument(
        "--locale",
        default=DEFAULT_LOCALE,
        choices=sorted(LOCALIZATIONS),
        help="text/theme localization language. Default: %(default)s",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        seed, sizes = run_generation(
            GenerationOptions(
                output=args.output,
                pages=args.pages,
                difficulty=args.difficulty,
                seed=args.seed,
                min_path_factor=args.min_path_factor,
                locale=args.locale,
            )
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(
        f"PDF created: {args.output}  ({args.pages} mazes)  "
        f"difficulty={args.difficulty}  seed={seed}  "
        f"min_path_factor={args.min_path_factor}  locale={args.locale}"
    )
    print(f"Grids: first {sizes[0]}x{sizes[0]} -> last {sizes[-1]}x{sizes[-1]}.")
    if args.seed is None:
        print(
            f"Run again for completely different mazes. "
            f"Use --seed {seed} to reproduce this exact PDF."
        )


if __name__ == "__main__":
    main()

