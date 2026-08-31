"""Package smoke tests."""


def test_package_is_importable() -> None:
    """Ensure the generated package is importable."""
    import agentic_lab

    assert agentic_lab.__name__ == "agentic_lab"
