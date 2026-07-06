# Standard library imports.
from argparse import ArgumentParser

# Local imports.
from sync.run import run_heather


def main():
    parser = ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-vantage-write", action="store_true")
    parser.add_argument("--enable-ai-comment-digest", action="store_true")
    args = parser.parse_args()

    run_heather(
        dry_run=args.dry_run,
        write_vantage=not args.skip_vantage_write,
        use_ai_comment_digest=args.enable_ai_comment_digest,
    )


if __name__ == "__main__":
    main()
