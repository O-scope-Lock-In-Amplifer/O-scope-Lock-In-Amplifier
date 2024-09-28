"""Main command-line entry point."""

from o_scope_lock_in_amplifier import ds1054z


def main() -> None:
    """Execute the package's main functionality."""
    print(ds1054z.DS1054z())


# Main command-line entry point.
if __name__ == "__main__":
    main()
