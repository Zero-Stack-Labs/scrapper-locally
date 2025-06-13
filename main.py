"""Main script to run the locally scraper."""

import argparse
import sys
from pathlib import Path

from scrapers.locally_scraper import LocallyScraper

# Configuration list for different stores/locations to scrape
STORE_CONFIGURATIONS = [
    {"zipcode": "98125", "lat": 47.72, "lng": -122.30, 'store_id': '85940', 'store_name': "DICK'S Sporting Goods"},
]


def main():
    """Main function to run the scraper with command line arguments."""

    parser = argparse.ArgumentParser(
        description="Scrape products from locally.com with advanced features"
    )

    # Basic options
    parser.add_argument(
        "--start-page",
        type=int,
        default=0,
        help="Starting page number (default: 0)"
    )

    parser.add_argument(
        "--pages",
        nargs="+",
        type=int,
        help="Specific pages to scrape (e.g., --pages 1 2 3)"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Output directory for files (default: current directory)"
    )

    # Rate limiting options
    parser.add_argument(
        "--page-delay",
        type=float,
        default=5.0,
        help="Delay in seconds between pages (default: 5.0)"
    )

    parser.add_argument(
        "--max-product-workers",
        type=int,
        default=10,
        help="Maximum workers for product detail scraping (default: 10)"
    )

    parser.add_argument(
        "--max-stock-workers",
        type=int,
        default=3,
        help="Deprecated: Stock info is now extracted directly from product pages"
    )

    parser.add_argument(
        "--stock-rate-limit",
        type=float,
        default=2.0,
        help="Deprecated: No longer needed since stock is extracted from product pages"
    )

    # Feature options
    parser.add_argument(
        "--no-stock",
        action="store_true",
        help="Deprecated: Stock information is always extracted from product pages"
    )

    parser.add_argument(
        "--save-every",
        type=int,
        default=5,
        help="Save progress every N pages (default: 5)"
    )

    parser.add_argument(
        "--store-id",
        type=str,
        default="85940",
        help="Store ID to scrape (default: 85940)"
    )

    # Parse arguments
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize scraper
    print("=" * 60)
    print("LOCALLY.COM SCRAPER - MULTI-LOCATION VERSION")
    print("=" * 60)

    # Show deprecation warnings if needed
    if args.no_stock:
        print("⚠️  WARNING: --no-stock is deprecated. Stock info is always extracted from product pages.")
    if args.stock_rate_limit != 2.0:
        print("⚠️  WARNING: --stock-rate-limit is deprecated. No separate stock API calls are made.")
    if args.max_stock_workers != 3:
        print("⚠️  WARNING: --max-stock-workers is deprecated. Stock info comes from product pages.")
    if hasattr(args, 'store_id') and args.store_id != "85940":
        print("⚠️  INFO: --store-id is now configured in STORE_CONFIGURATIONS. Command line argument will be ignored.")
    print()

    # Process each store configuration
    all_location_products = []  # Store products from all locations for stock analysis

    for config in STORE_CONFIGURATIONS:
        try:
            print(f"\n{'=' * 80}")
            print(f"PROCESSING STORE: {config['store_id']} (Zipcode: {config['zipcode']})")
            print(f"Location: LAT {config['lat']}, LNG {config['lng']}")
            print(f"{'=' * 80}")

            # Create filename suffix for this store
            filename_suffix = f"{config['store_id']}_{config['zipcode']}"

            # Note: enable_stock_scraping is always True now since we extract from product pages
            scraper = LocallyScraper(
                enable_stock_scraping=True,  # Always True now
                output_dir=args.output_dir,
                store_config=config,
                filename_suffix=filename_suffix
            )

            # Print configuration
            status = scraper.get_status()
            print(f"Configuration:")
            print(f"  - Store ID: {status['store_id']}")
            print(f"  - Zipcode: {config['zipcode']}")
            print(f"  - Coordinates: ({config['lat']}, {config['lng']})")
            print(f"  - Stock scraping: Always enabled (extracted from product pages)")
            print(f"  - Output directory: {status['output_directory']}")
            print(f"  - Output files: products_{filename_suffix}.csv/json")
            print(f"  - Page delay: {args.page_delay} seconds")
            print(f"  - Product workers: {args.max_product_workers}")
            print()

            # Choose scraping method
            if args.pages:
                print(f"Scraping specific pages: {args.pages}")
                products = scraper.scrape_specific_pages(
                    pages=args.pages,
                    max_product_workers=args.max_product_workers
                )
            else:
                print(f"Scraping all pages starting from page {args.start_page}")
                products = scraper.scrape_all_products_with_delays(
                    start_page=args.start_page,
                    page_delay=args.page_delay,
                    max_product_workers=args.max_product_workers,
                    save_progress_every=args.save_every
                )

            # Save final results for this location
            scraper.save_results(products)

            # Add products to global collection for stock analysis
            for product in products:
                product['location_zipcode'] = config['zipcode']  # Tag with location
            all_location_products.extend(products)

            print(f"\n✅ Completed scraping for store {config['store_id']} (zipcode: {config['zipcode']})")

        except KeyboardInterrupt:
            print(f"\n\nScraping interrupted by user for store {config['store_id']}. Saving current progress...")
            # Try to save whatever we have collected so far
            try:
                scraper.save_results(products)
            except NameError:
                print("No data to save.")
            return 1

        except Exception as e:
            print(f"\nError during scraping for store {config['store_id']}: {e}")
            import traceback
            traceback.print_exc()
            # Continue with next store instead of stopping completely
            continue

    print(f"\n{'=' * 80}")
    print("ALL STORES COMPLETED - GENERATING STOCK ANALYSIS")
    print(f"{'=' * 80}")

    # Generate stock analysis files
    if all_location_products:
        from utils.stock_analyzer import StockAnalyzer
        analyzer = StockAnalyzer(args.output_dir)
        analyzer.generate_stock_analysis_files(all_location_products, STORE_CONFIGURATIONS)

    print(f"\n{'=' * 80}")
    print("ALL PROCESSING COMPLETED")
    print(f"{'=' * 80}")
    return 0


def run_simple_scrape():
    """Simple function to run scraper with default settings."""
    scraper = LocallyScraper(enable_stock_scraping=True)

    products = scraper.scrape_all_products_with_delays(
        start_page=0,
        page_delay=5.0,
        max_product_workers=10,
        save_progress_every=5
    )

    scraper.save_results(products)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
