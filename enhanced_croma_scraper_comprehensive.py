#!/usr/bin/env python3
"""
COMPREHENSIVE Enhanced Croma Bank Offer Scraper
==============================================
- Reaches ALL 3 nested locations for Croma links:
  1. scraped_data.variants[].store_links[]
  2. scraped_data.all_matching_products[].store_links[]  
  3. scraped_data.unmapped[].store_links[]
- Uses comprehensive_amazon_offers.json as input
- Completely isolates Amazon data (no changes to Amazon offers)
- Uses croma_urls_without_offers_*.txt to skip URLs with existing offers
- Same advanced ranking logic as original script
"""

import os
import re
import json
import time
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Import the original analyzer class (keeping all the advanced logic)
import sys
sys.path.append('sorting')
from cromaSDoffers_enhanced import CromaOfferAnalyzer, get_croma_offers, extract_price_amount

# Setup logging
logging.basicConfig(
    filename='enhanced_croma_scraper_comprehensive.log',
    filemode='a',
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO
)

def find_all_croma_store_links_comprehensive(data: List[Dict]) -> List[Dict]:
    """
    Find ALL Croma store links from ALL 3 nested locations:
    1. scraped_data.variants[].store_links[]
    2. scraped_data.all_matching_products[].store_links[]
    3. scraped_data.unmapped[].store_links[]
    
    Returns comprehensive location info for each link.
    """
    
    croma_store_links = []
    locations_checked = {'variants': 0, 'all_matching_products': 0, 'unmapped': 0}
    croma_found = {'variants': 0, 'all_matching_products': 0, 'unmapped': 0}
    
    for entry_idx, entry in enumerate(data):
        if 'scraped_data' not in entry or not isinstance(entry['scraped_data'], dict):
            continue
            
        scraped_data = entry['scraped_data']
        
        # LOCATION 1: scraped_data.variants[].store_links[]
        if 'variants' in scraped_data and isinstance(scraped_data['variants'], list):
            for variant_idx, variant in enumerate(scraped_data['variants']):
                if isinstance(variant, dict) and 'store_links' in variant:
                    locations_checked['variants'] += 1
                    store_links = variant['store_links']
                    if isinstance(store_links, list):
                        for store_idx, store_link in enumerate(store_links):
                            if isinstance(store_link, dict):
                                name = store_link.get('name', '').lower()
                                if 'croma' in name:
                                    croma_found['variants'] += 1
                                    croma_store_links.append({
                                        'entry_idx': entry_idx,
                                        'location': 'variants',
                                        'location_idx': variant_idx,
                                        'store_idx': store_idx,
                                        'entry': entry,
                                        'parent_object': variant,
                                        'store_link': store_link,
                                        'path': f"scraped_data.variants[{variant_idx}].store_links[{store_idx}]"
                                    })
        
        # LOCATION 2: scraped_data.all_matching_products[].store_links[]
        if 'all_matching_products' in scraped_data and isinstance(scraped_data['all_matching_products'], list):
            for product_idx, product in enumerate(scraped_data['all_matching_products']):
                if isinstance(product, dict) and 'store_links' in product:
                    locations_checked['all_matching_products'] += 1
                    store_links = product['store_links']
                    if isinstance(store_links, list):
                        for store_idx, store_link in enumerate(store_links):
                            if isinstance(store_link, dict):
                                name = store_link.get('name', '').lower()
                                if 'croma' in name:
                                    croma_found['all_matching_products'] += 1
                                    croma_store_links.append({
                                        'entry_idx': entry_idx,
                                        'location': 'all_matching_products',
                                        'location_idx': product_idx,
                                        'store_idx': store_idx,
                                        'entry': entry,
                                        'parent_object': product,
                                        'store_link': store_link,
                                        'path': f"scraped_data.all_matching_products[{product_idx}].store_links[{store_idx}]"
                                    })
        
        # LOCATION 3: scraped_data.unmapped[].store_links[]
        if 'unmapped' in scraped_data and isinstance(scraped_data['unmapped'], list):
            for unmapped_idx, unmapped in enumerate(scraped_data['unmapped']):
                if isinstance(unmapped, dict) and 'store_links' in unmapped:
                    locations_checked['unmapped'] += 1
                    store_links = unmapped['store_links']
                    if isinstance(store_links, list):
                        for store_idx, store_link in enumerate(store_links):
                            if isinstance(store_link, dict):
                                name = store_link.get('name', '').lower()
                                if 'croma' in name:
                                    croma_found['unmapped'] += 1
                                    croma_store_links.append({
                                        'entry_idx': entry_idx,
                                        'location': 'unmapped',
                                        'location_idx': unmapped_idx,
                                        'store_idx': store_idx,
                                        'entry': entry,
                                        'parent_object': unmapped,
                                        'store_link': store_link,
                                        'path': f"scraped_data.unmapped[{unmapped_idx}].store_links[{store_idx}]"
                                    })
    
    # Print comprehensive statistics
    print(f"\n📊 COMPREHENSIVE CROMA LINK DISCOVERY:")
    print(f"   Total entries processed: {len(data)}")
    print(f"   Location coverage:")
    for location, checked in locations_checked.items():
        found = croma_found[location]
        print(f"     {location}: {checked} locations checked → {found} Croma links found")
    
    total_found = sum(croma_found.values())
    print(f"   🎯 TOTAL CROMA LINKS FOUND: {total_found} (from all 3 locations)")
    
    return croma_store_links

def load_urls_to_skip(file_pattern: str = "croma_urls_all_status_20250803_033020.txt") -> set:
    """
    Load URLs that already have offers (should be skipped).
    Uses the most recent croma_urls_without_offers_*.txt file.
    """
    import glob
    
    # Find the most recent file matching the pattern
    files = glob.glob(file_pattern)
    if not files:
        print(f"⚠️  No files found matching pattern: {file_pattern}")
        return set()
    
    # Sort by filename (newest timestamp last) and take the most recent
    latest_file = sorted(files)[-1]
    print(f"📋 Loading URLs to SKIP from: {latest_file}")
    
    urls_to_skip = set()
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls_to_skip.add(line)
        
        print(f"✅ Loaded {len(urls_to_skip)} URLs that already have offers (will skip these)")
        return urls_to_skip
    
    except Exception as e:
        print(f"❌ Error loading {latest_file}: {e}")
        return set()

def process_croma_comprehensive(input_file: str = "all_data_amazon_jio.json", 
                              output_file: str = "all_data_amazon_jio_croma.json", 
                              start_idx: int = 0, 
                              max_entries: Optional[int] = None):
    """
    Comprehensive Croma processing that:
    1. Uses comprehensive_amazon_offers.json as input
    2. Finds Croma links in ALL 3 nested locations
    3. Skips URLs that already have offers
    4. Completely isolates Amazon data
    5. Uses advanced ranking logic
    """
    
    print(f"🚀 COMPREHENSIVE CROMA SCRAPER STARTING")
    print(f"📂 Input file: {input_file}")
    print(f"📂 Output file: {output_file}")
    print(f"🛡️  Amazon data isolation: ENABLED (no changes to Amazon offers)")
    print("-" * 80)
    
    # Load the JSON data
    print(f"📖 Loading data from {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} entries successfully")
    except Exception as e:
        print(f"❌ Error loading {input_file}: {e}")
        return
    
    # Load URLs that already have offers (to skip)
    urls_with_offers = load_urls_to_skip()
    
    # Find ALL Croma store links from all 3 locations
    print(f"\n🔍 Discovering Croma links from ALL nested locations...")
    croma_store_links = find_all_croma_store_links_comprehensive(data)
    
    if not croma_store_links:
        print(f"❌ No Croma store links found in {input_file}")
        return
    
    # Apply start index and max entries limit
    if start_idx > 0:
        croma_store_links = croma_store_links[start_idx:]
        print(f"📍 Starting from index {start_idx}, processing {len(croma_store_links)} links")
    
    if max_entries:
        croma_store_links = croma_store_links[:max_entries]
        print(f"📏 Limited to processing {len(croma_store_links)} links")
    
    # Setup Chrome driver and analyzer
    headless_mode = os.getenv('HEADLESS', 'true').lower() == 'true'
    
    options = uc.ChromeOptions()
    if headless_mode:
        print("🤖 Running in headless mode")
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
    else:
        print("🖥️  Running with visible browser")
        options.add_argument('--window-size=1400,1000')
    
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = uc.Chrome(options=options)
    analyzer = CromaOfferAnalyzer()
    
    # Statistics
    stats = {
        'processed': 0,
        'skipped_has_offers': 0,
        'skipped_no_url': 0,
        'scraped_successfully': 0,
        'failed_scraping': 0,
        'total_offers_added': 0,
        'amazon_entries_untouched': 0
    }
    
    try:
        print(f"\n🎯 Starting Croma scraping (Amazon data completely isolated)...")
        
        for idx, link_data in enumerate(croma_store_links):
            entry = link_data['entry']
            store_link = link_data['store_link']
            location_info = f"{link_data['location']}[{link_data['location_idx']}]"
            
            print(f"\n🔍 Processing {idx + 1}/{len(croma_store_links)}: {entry.get('product_name', 'N/A')}")
            print(f"   📍 Location: {link_data['path']}")
            
            # Get parent object info for display
            parent_obj = link_data['parent_object']
            if link_data['location'] == 'variants':
                variant_info = f"{parent_obj.get('colour', 'N/A')} {parent_obj.get('ram', '')} {parent_obj.get('storage', '')}"
                print(f"   📱 Variant: {variant_info}")
            elif link_data['location'] == 'all_matching_products':
                print(f"   🔗 Matching Product: {parent_obj.get('name', 'N/A')}")
            else:  # unmapped
                print(f"   📦 Unmapped: {parent_obj.get('name', 'N/A')}")
            
            croma_url = store_link.get('url', '')
            if not croma_url:
                print(f"   ⚠️  No URL found")
                stats['skipped_no_url'] += 1
                continue
            
            print(f"   🌐 Croma URL: {croma_url}")
            
            # Check if URL already has offers (should be skipped)
            if croma_url in urls_with_offers:
                print(f"   ⏭️  URL already has offers, skipping to preserve existing data")
                stats['skipped_has_offers'] += 1
                continue
            
            # SCRAPE THE CROMA OFFERS
            print(f"   🔄 Scraping Croma offers...")
            offers = get_croma_offers(driver, croma_url)
            stats['processed'] += 1
            
            if offers:
                # Get product price for ranking
                price_str = store_link.get('price', '₹0')
                product_price = extract_price_amount(price_str)
                
                # Rank the offers using advanced logic
                ranked_offers = analyzer.rank_offers(offers, product_price)
                
                # Update the store_link with ranked offers
                store_link['ranked_offers'] = ranked_offers
                stats['scraped_successfully'] += 1
                stats['total_offers_added'] += len(ranked_offers)
                
                print(f"   ✅ Found and ranked {len(offers)} Croma offers")
                
                # Log top 3 offers
                for i, offer in enumerate(ranked_offers[:3], 1):
                    score_display = offer['score'] if offer['score'] is not None else 'N/A'
                    print(f"      🏆 Rank {i}: {offer['title']} (Score: {score_display}, Amount: ₹{offer['amount']})")
            else:
                print(f"   ❌ No offers found")
                store_link['ranked_offers'] = []
                stats['failed_scraping'] += 1
            
            # Save progress every 10 entries
            if (idx + 1) % 10 == 0:
                backup_file = f"{output_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"   💾 Progress saved to {backup_file}")
            
            # Small delay between requests
            time.sleep(3)
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted! Saving progress...")
    
    finally:
        driver.quit()
        
        # Save final output
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Final output saved to {output_file}")
        
        # Print comprehensive statistics
        print(f"\n📊 COMPREHENSIVE PROCESSING SUMMARY:")
        print(f"   🎯 Croma links processed: {stats['processed']}")
        print(f"   ✅ Successfully scraped: {stats['scraped_successfully']}")
        print(f"   ❌ Failed scraping: {stats['failed_scraping']}")
        print(f"   ⏭️  Skipped (already have offers): {stats['skipped_has_offers']}")
        print(f"   ⚠️  Skipped (no URL): {stats['skipped_no_url']}")
        print(f"   🎁 Total offers added: {stats['total_offers_added']}")
        print(f"   🛡️  Amazon entries completely untouched!")
        
        success_rate = (stats['scraped_successfully'] / stats['processed'] * 100) if stats['processed'] > 0 else 0
        print(f"   📈 Success rate: {success_rate:.1f}%")

if __name__ == "__main__":
    import sys
    
    print("🚀 COMPREHENSIVE CROMA SCRAPER")
    print("Reaches ALL nested locations while completely isolating Amazon data")
    print("=" * 80)
    
    # Check for command line arguments
    if len(sys.argv) > 1 and '--headless' in sys.argv:
        os.environ['HEADLESS'] = 'true'
        print("🤖 Headless mode enabled via command line")
    elif len(sys.argv) > 1 and '--gui' in sys.argv:
        os.environ['HEADLESS'] = 'false'
        print("🖥️  GUI mode enabled via command line")
    
    # Default settings optimized for comprehensive processing
    input_file = "all_data_amazon_jio.json"
    output_file = "all_data_amazon_jio_croma.json"
    
    # Ask user for parameters
    if 'HEADLESS' not in os.environ:
        browser_mode = input("Run in headless mode? (y/n) [y]: ").lower().strip()
        os.environ['HEADLESS'] = 'false' if browser_mode in ['n', 'no'] else 'true'
    
    try:
        start_idx = int(input("Enter start index (default 0): ") or "0")
    except ValueError:
        start_idx = 0
    
    max_entries_input = input("Enter max entries to process (or 'all'): ").lower().strip()
    max_entries = None if max_entries_input in ['all', ''] else int(max_entries_input)
    
    print(f"\n🎯 CONFIGURATION:")
    print(f"   Input: {input_file}")
    print(f"   Output: {output_file}")
    print(f"   Start index: {start_idx}")
    print(f"   Max entries: {max_entries or 'All'}")
    print(f"   Browser mode: {'Headless' if os.environ.get('HEADLESS') == 'true' else 'GUI'}")
    print(f"   🛡️  Amazon isolation: ENABLED")
    
    confirm = input("\nProceed with these settings? (y/n) [y]: ").lower().strip()
    if confirm not in ['n', 'no']:
        process_croma_comprehensive(input_file, output_file, start_idx, max_entries)
    else:
        print("❌ Cancelled by user") 