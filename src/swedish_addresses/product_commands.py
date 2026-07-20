"""Convenience entry points for individual compact postcode products."""

from __future__ import annotations

from .products import main as products_main


def _product_main(product: str) -> None:
    import sys

    original_argv = sys.argv
    try:
        sys.argv = [original_argv[0], "--product", product, *original_argv[1:]]
        products_main()
    finally:
        sys.argv = original_argv


def postcode_post_towns() -> None:
    _product_main("postcode-post-towns")


def postcode_administrative_areas() -> None:
    _product_main("postcode-administrative-areas")


def postcode_parishes() -> None:
    _product_main("postcode-parishes")


def postcode_centroids() -> None:
    _product_main("postcode-centroids")
