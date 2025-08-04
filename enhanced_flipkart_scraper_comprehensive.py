
"""
Enhanced Comprehensive Flipkart Scraper for comprehensive_amazon_offers.json
- Traverses ALL nested locations (variants, all_matching_products, unmapped)
- Uses correct input file (comprehensive_amazon_offers.json)
- Skips URLs with existing offers to preserve data
- Completely isolates Amazon and Croma offers from any changes
- Focuses ONLY on Flipkart links
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
import shutil

# Setup logging
logging.basicConfig(
    filename='enhanced_flipkart_scraper.log',
    filemode='a',
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO
)

class ComprehensiveFlipkartExtractor:
    """Extract ALL Flipkart store links from comprehensive JSON structure"""
    
    def __init__(self, input_file: str, flipkart_urls_file: str = None):
        self.input_file = input_file
        self.flipkart_urls_file = flipkart_urls_file or "flipkart_urls_with_offers_20250801_132347.txt"
        self.visited_flipkart_urls = set()
        self.load_visited_urls()
    
    def load_visited_urls(self):
        """Load list of Flipkart URLs that already have offers"""
        try:
            if os.path.exists(self.flipkart_urls_file):
                with open(self.flipkart_urls_file, 'r', encoding='utf-8') as f:
                    self.visited_flipkart_urls = set(line.strip() for line in f if line.strip() and not line.startswith('#'))
                print(f"📋 Loaded {len(self.visited_flipkart_urls)} Flipkart URLs with existing offers")
            else:
                print(f"⚠️  No existing Flipkart URLs file found at {self.flipkart_urls_file}")
        except Exception as e:
            print(f"❌ Error loading visited URLs: {e}")
    
    def find_all_flipkart_store_links(self, data: Any, path: str = "") -> List[Dict]:
        """
        COMPREHENSIVE search for ALL Flipkart store links in ALL nested locations
        - scraped_data.variants
        - scraped_data.all_matching_products  
        - scraped_data.unmapped
        """
        flipkart_links = []
        
        def extract_flipkart_from_store_links(store_links, parent_path, parent_data):
            """Extract Flipkart links from store_links array"""
            if not isinstance(store_links, list):
                return
            
            for store_idx, store_link in enumerate(store_links):
                if isinstance(store_link, dict):
                    name = store_link.get('name', '').lower()
                    if 'flipkart' in name:
                        url = store_link.get('url', '')
                        
                        # CRITICAL: Skip if URL already has offers (preserve existing data)
                        if url in self.visited_flipkart_urls:
                            print(f"   ⏭️  Flipkart URL already has offers, skipping: {url}")
                            continue
                        
                        flipkart_links.append({
                            'path': f"{parent_path}.store_links[{store_idx}]",
                            'url': url,
                            'name': store_link.get('name', ''),
                            'price': store_link.get('price', ''),
                            'store_link_ref': store_link,  # Direct reference for updating
                            'parent_data': parent_data,
                            'store_idx': store_idx
                        })
        
        def search_recursive(obj: Any, current_path: str = ""):
            if isinstance(obj, dict):
                # CRITICAL: Only process entries that are NOT Amazon or Croma
                if 'scraped_data' in obj:
                    scraped_data = obj['scraped_data']
                    if isinstance(scraped_data, dict):
                        
                        # 1. Search in variants (original location)
                        if 'variants' in scraped_data and isinstance(scraped_data['variants'], list):
                            for variant_idx, variant in enumerate(scraped_data['variants']):
                                if isinstance(variant, dict) and 'store_links' in variant:
                                    variant_path = f"{current_path}.scraped_data.variants[{variant_idx}]"
                                    extract_flipkart_from_store_links(
                                        variant['store_links'], 
                                        variant_path, 
                                        variant
                                    )
                        
                        # 2. Search in all_matching_products (MISSING in original script)
                        if 'all_matching_products' in scraped_data and isinstance(scraped_data['all_matching_products'], list):
                            for amp_idx, amp_item in enumerate(scraped_data['all_matching_products']):
                                if isinstance(amp_item, dict) and 'store_links' in amp_item:
                                    amp_path = f"{current_path}.scraped_data.all_matching_products[{amp_idx}]"
                                    extract_flipkart_from_store_links(
                                        amp_item['store_links'], 
                                        amp_path, 
                                        amp_item
                                    )
                        
                        # 3. Search in unmapped (MISSING in original script)
                        if 'unmapped' in scraped_data and isinstance(scraped_data['unmapped'], list):
                            for unmapped_idx, unmapped_item in enumerate(scraped_data['unmapped']):
                                if isinstance(unmapped_item, dict) and 'store_links' in unmapped_item:
                                    unmapped_path = f"{current_path}.scraped_data.unmapped[{unmapped_idx}]"
                                    extract_flipkart_from_store_links(
                                        unmapped_item['store_links'], 
                                        unmapped_path, 
                                        unmapped_item
                                    )
                
                # Continue recursive search
                for key, value in obj.items():
                    new_path = f"{current_path}.{key}" if current_path else key
                    search_recursive(value, new_path)
                    
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{current_path}[{i}]" if current_path else f"[{i}]"
                    search_recursive(item, new_path)
        
        search_recursive(data, path)
        return flipkart_links

@dataclass
class Offer:
    title: str
    description: str
    amount: float
    type: str
    bank: Optional[str] = None
    validity: Optional[str] = None
    min_spend: Optional[float] = None
    is_instant: bool = True
    card_type: Optional[str] = None
    card_provider: Optional[str] = None

class FlipkartOfferAnalyzer:
    def __init__(self):
        # Same comprehensive bank scores as original script
        self.bank_scores = {
            # Public Sector Banks (PSBs)
            "SBI": 75, "State Bank of India": 75, "PNB": 72, "Punjab National Bank": 72,
            "BoB": 70, "Bank of Baroda": 70, "Canara Bank": 68, "Union Bank of India": 65,
            "Indian Bank": 65, "Bank of India": 65, "UCO Bank": 62, "Indian Overseas Bank": 62,
            "IOB": 62, "Central Bank of India": 62, "Bank of Maharashtra": 60, "Punjab & Sind Bank": 60,
            
            # Private Sector Banks
            "HDFC": 85, "HDFC Bank": 85, "ICICI": 90, "ICICI Bank": 90, "Axis": 80, "Axis Bank": 80,
            "Kotak": 70, "Kotak Mahindra Bank": 70, "IndusInd Bank": 68, "Yes Bank": 60,
            "IDFC FIRST Bank": 65, "IDFC": 65, "Federal Bank": 63, "South Indian Bank": 60,
            "RBL Bank": 62, "DCB Bank": 60, "Tamilnad Mercantile Bank": 58, "TMB": 58,
            "Karur Vysya Bank": 58, "CSB Bank": 58, "City Union Bank": 58, "Bandhan Bank": 60,
            "Jammu & Kashmir Bank": 58,
            
            # Small Finance Banks
            "AU Small Finance Bank": 65, "AU Bank": 65, "Equitas Small Finance Bank": 62,
            "Equitas": 62, "Ujjivan Small Finance Bank": 60, "Ujjivan": 60,
            
            # Foreign Banks
            "Citi": 80, "Citibank": 80, "HSBC": 78, "Standard Chartered": 75, "Deutsche Bank": 75,
            "Barclays Bank": 75, "DBS Bank": 72, "JP Morgan Chase Bank": 75, "Bank of America": 75,
            
            # Credit Card Companies
            "Amex": 85, "American Express": 85
        }
        
        self.bank_name_patterns = {
            "SBI": ["SBI", "State Bank", "State Bank of India"],
            "HDFC": ["HDFC", "HDFC Bank"], "ICICI": ["ICICI", "ICICI Bank"],
            "Axis": ["Axis", "Axis Bank"], "Kotak": ["Kotak", "Kotak Mahindra"],
            "Yes Bank": ["Yes Bank", "YES Bank"], "IDFC": ["IDFC", "IDFC FIRST", "IDFC Bank"],
            "IndusInd": ["IndusInd", "IndusInd Bank"], "Federal": ["Federal", "Federal Bank"],
            "RBL": ["RBL", "RBL Bank"], "Citi": ["Citi", "Citibank", "CitiBank"],
            "HSBC": ["HSBC"], "Standard Chartered": ["Standard Chartered", "StanChart", "SC Bank"],
            "AU Bank": ["AU Bank", "AU Small Finance", "AU"], "Equitas": ["Equitas", "Equitas Bank"],
        }
        
        self.card_providers = [
            "Visa", "Mastercard", "RuPay", "American Express", "Amex", 
            "Diners Club", "Discover", "UnionPay", "JCB", "Maestro"
        ]
        
        self.default_bank_score = 70

    def extract_amount(self, description: str) -> float:
        """Extract numerical amount from offer description"""
        try:
            # Enhanced flat discount patterns
            flat_patterns = [
                r'(?:Additional\s+)?[Ff]lat\s+(?:INR\s+|₹\s*)([\d,]+\.?\d*)',
                r'(?:Additional\s+)?(?:INR\s+|₹\s*)([\d,]+\.?\d*)\s+(?:Instant\s+)?Discount',
                r'(?:Get\s+)?(?:INR\s+|₹\s*)([\d,]+\.?\d*)\s+(?:off|discount)',
                r'(?:Save\s+)?(?:INR\s+|₹\s*)([\d,]+\.?\d*)',
                r'₹\s*([\d,]+\.?\d*)', r'Rs\.?\s*([\d,]+\.?\d*)', r'INR\s*([\d,]+\.?\d*)'
            ]
            
            for pattern in flat_patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match:
                    return float(match.group(1).replace(',', ''))
            
            # Handle percentage discounts with caps
            percent_patterns = [
                r'([\d.]+)%\s+(?:Instant\s+)?Discount\s+up\s+to\s+(?:INR\s+|₹\s*)([\d,]+\.?\d*)',
                r'Up\s+to\s+([\d.]+)%\s+(?:off|discount).*?(?:max|maximum|up\s+to)\s+(?:INR\s+|₹\s*)([\d,]+\.?\d*)'
            ]
            
            for pattern in percent_patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match:
                    return float(match.group(2).replace(',', ''))
            
            return 0.0
        except (ValueError, AttributeError):
            return 0.0

    def extract_bank(self, description: str) -> Optional[str]:
        """Extract bank name from offer description"""
        if not description:
            return None
        
        description_lower = description.lower()
        
        # Try pattern matching first
        for bank_key, patterns in self.bank_name_patterns.items():
            for pattern in patterns:
                if pattern.lower() in description_lower:
                    return bank_key
        
        # Direct bank scores dictionary
        sorted_banks = sorted(self.bank_scores.keys(), key=len, reverse=True)
        for bank in sorted_banks:
            if bank.lower() in description_lower:
                return bank
        
        return None

    def extract_min_spend(self, description: str) -> Optional[float]:
        """Extract minimum spend requirement"""
        patterns = [
            r'(?:Mini|Minimum)\s+purchase\s+value\s+(?:of\s+)?(?:INR\s+|₹\s*|Rs\.?\s*)([\d,]+\.?\d*)',
            r'(?:Mini|Minimum)\s+(?:purchase|spend|transaction)\s+(?:of\s+|value\s+)?(?:INR\s+|₹\s*|Rs\.?\s*)([\d,]+\.?\d*)',
            r'valid\s+on\s+(?:orders?|purchases?)\s+(?:of\s+|above\s+|worth\s+)(?:INR\s+|₹\s*|Rs\.?\s*)([\d,]+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except ValueError:
                    continue
        return None

    def parse_offer(self, offer: Dict[str, str]) -> Offer:
        """Parse offer details from raw offer data"""
        description = offer.get('offer_description', '').strip()
        title = offer.get('card_type', 'Flipkart Offer').strip()
        
        amount = self.extract_amount(description)
        bank = self.extract_bank(description)
        min_spend = self.extract_min_spend(description)
        
        # Determine offer type
        if 'bank' in description.lower() or 'card' in description.lower():
            offer_type = "Bank Offer"
        elif 'emi' in description.lower():
            offer_type = "No Cost EMI"
        elif 'cashback' in description.lower():
            offer_type = "Cashback"
        elif 'exchange' in description.lower():
            offer_type = "Exchange Offer"
        else:
            offer_type = "Flipkart Offer"
        
        return Offer(
            title=title,
            description=description,
            amount=amount,
            type=offer_type,
            bank=bank,
            min_spend=min_spend,
            is_instant='instant' in description.lower()
        )

    def calculate_offer_score(self, offer: Offer, product_price: float) -> float:
        """Calculate offer score focusing on Bank Offers"""
        if offer.type != "Bank Offer":
            return 0
        
        base_score = 80
        
        # Discount amount bonus
        if product_price > 0 and offer.amount > 0:
            discount_percentage = (offer.amount / product_price) * 100
            discount_points = min(discount_percentage * 2, 50)
            base_score += discount_points
        
        # Minimum spend penalty/bonus
        if offer.min_spend and offer.min_spend > product_price:
            penalty_percentage = ((offer.min_spend - product_price) / product_price) * 100
            if penalty_percentage > 50:
                base_score = 15
            else:
                penalty = penalty_percentage * 0.5
                base_score -= penalty
                base_score = max(base_score, 20)
        elif offer.min_spend is None or offer.min_spend <= product_price:
            if offer.min_spend is None:
                base_score += 20
            else:
                spend_ratio = offer.min_spend / product_price if product_price > 0 else 0
                if spend_ratio <= 0.9:
                    bonus = (1 - spend_ratio) * 10
                    base_score += bonus
        
        # Bank reputation bonus
        if offer.bank:
            bank_bonus = (self.bank_scores.get(offer.bank, self.default_bank_score) - 70) / 2
            base_score += bank_bonus
        else:
            base_score -= 5
        
        return max(0, min(100, base_score))

    def rank_offers(self, offers_data: List[Dict], product_price: float) -> List[Dict[str, Any]]:
        """Rank offers focusing on Bank Offers"""
        parsed_offers = [self.parse_offer(offer) for offer in offers_data if isinstance(offer, dict)]
        bank_offers = [offer for offer in parsed_offers if offer.type == "Bank Offer"]
        other_offers = [offer for offer in parsed_offers if offer.type != "Bank Offer"]
        
        all_ranked_offers = []
        
        # Process Bank Offers with ranking
        if bank_offers:
            scored_bank_offers = []
            for offer in bank_offers:
                score = self.calculate_offer_score(offer, product_price)
                
                if offer.min_spend and product_price < offer.min_spend:
                    net_effective_price = product_price
                    is_applicable = False
                else:
                    net_effective_price = max(product_price - offer.amount, 0)
                    is_applicable = True
                
                scored_bank_offers.append({
                    'title': offer.title,
                    'description': offer.description,
                    'amount': offer.amount,
                    'bank': offer.bank,
                    'validity': None,
                    'min_spend': offer.min_spend,
                    'score': score,
                    'is_instant': offer.is_instant,
                    'net_effective_price': net_effective_price,
                    'is_applicable': is_applicable,
                    'note': f"Flipkart bank offer: ₹{offer.amount} discount" + (f" (Min spend: ₹{offer.min_spend})" if offer.min_spend else ""),
                    'offer_type': 'Bank Offer',
                    'card_type': None,
                    'card_provider': None
                })
            
            scored_bank_offers.sort(key=lambda x: x['score'], reverse=True)
            for idx, offer in enumerate(scored_bank_offers):
                offer['rank'] = idx + 1
            all_ranked_offers.extend(scored_bank_offers)
        
        # Process other offers without ranking
        for offer in other_offers:
            if offer.min_spend and product_price < offer.min_spend:
                net_effective_price = product_price
                is_applicable = False
            else:
                net_effective_price = max(product_price - offer.amount, 0)
                is_applicable = True
            
            all_ranked_offers.append({
                'title': offer.title,
                'description': offer.description,
                'amount': offer.amount,
                'bank': offer.bank,
                'validity': None,
                'min_spend': offer.min_spend,
                'score': None,
                'is_instant': offer.is_instant,
                'net_effective_price': net_effective_price,
                'is_applicable': is_applicable,
                'note': f"Flipkart {offer.type.lower()}: ₹{offer.amount} value" if offer.amount > 0 else f"Flipkart {offer.type.lower()}",
                'offer_type': offer.type,
                'rank': None,
                'card_type': None,
                'card_provider': None
            })
        
        return all_ranked_offers

def extract_price_amount(price_str):
    """Extract numeric amount from price string"""
    if not price_str:
        return 0.0
    numbers = re.findall(r'[\d,]+\.?\d*', price_str)
    if numbers:
        return float(numbers[0].replace(',', ''))
    return 0.0

def get_flipkart_offers(driver, url, max_retries=2):
    """Enhanced Flipkart offers scraping"""
    for attempt in range(max_retries):
        try:
            logging.info(f"Visiting Flipkart URL (attempt {attempt + 1}/{max_retries}): {url}")
            driver.get(url)
            time.sleep(3)

            # Close login popup if it appears
            try:
                close_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'✕')]"))
                )
                close_btn.click()
                time.sleep(1)
            except TimeoutException:
                pass

            # Scroll to trigger offers
            driver.execute_script("window.scrollBy(0, 1200);")
            time.sleep(2)

            # Wait for offers section
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'Available offers')]"))
                )
            except TimeoutException:
                if attempt < max_retries - 1:
                    continue
                return []

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            offers = []
            
            # Find offers using multiple patterns
            offer_header = soup.find("div", string=lambda text: text and "Available offers" in text)
            if offer_header:
                parent = offer_header.find_parent("div")
                if parent:
                    offer_items = parent.find_all("li")
                    for item in offer_items:
                        text = item.get_text(" ", strip=True)
                        if text and len(text) > 10:
                            offers.append({
                                "card_type": "Flipkart Offer",
                                "offer_title": "Available Offer",
                                "offer_description": text
                            })

            # Remove duplicates
            unique_offers = []
            seen_descriptions = set()
            for offer in offers:
                desc = offer['offer_description']
                if desc not in seen_descriptions and len(desc) > 15:
                    seen_descriptions.add(desc)
                    unique_offers.append(offer)

            logging.info(f"Extracted {len(unique_offers)} unique offers from {url}")
            return unique_offers

        except Exception as e:
            logging.error(f"Exception in get_flipkart_offers (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
                continue
            else:
                return []
    
    return []

def process_comprehensive_flipkart_links(input_file="comprehensive_amazon_offers.json", 
                                       output_file="comprehensive_amazon_offers.json",
                                       flipkart_urls_file="flipkart_urls_with_offers_20250801_132347.txt",
                                       start_idx=0, max_entries=None):
    """
    Process ALL Flipkart store links in the comprehensive JSON file
    - Completely isolates Amazon and Croma offers (no changes)
    - Only processes Flipkart links that don't have existing offers
    - Traverses ALL nested locations comprehensively
    """
    
    # Create backup before processing
    backup_file = f"{input_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(input_file, backup_file)
    print(f"💾 Created backup: {backup_file}")
    
    # Load the JSON data
    print(f"📖 Loading data from {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✅ Loaded {len(data)} entries")
    
    # Initialize comprehensive extractor
    extractor = ComprehensiveFlipkartExtractor(input_file, flipkart_urls_file)
    
    # Find ALL Flipkart store links using comprehensive traversal
    print(f"🔍 Searching for Flipkart links in ALL nested locations...")
    flipkart_links = extractor.find_all_flipkart_store_links(data)
    
    print(f"📊 Found {len(flipkart_links)} Flipkart store links (excluding those with existing offers)")
    
    # Apply start index and max entries limit
    if start_idx > 0:
        flipkart_links = flipkart_links[start_idx:]
        print(f"▶️  Starting from index {start_idx}, processing {len(flipkart_links)} links")
    
    if max_entries:
        flipkart_links = flipkart_links[:max_entries]
        print(f"🔢 Limited to processing {len(flipkart_links)} links")
    
    if not flipkart_links:
        print("✅ No new Flipkart links to process (all existing links already have offers)")
        return
    
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
    
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = uc.Chrome(options=options)
    analyzer = FlipkartOfferAnalyzer()
    
    processed_count = 0
    new_offers_count = 0
    
    try:
        for idx, link_data in enumerate(flipkart_links):
            print(f"\n🔍 Processing {idx + 1}/{len(flipkart_links)}")
            print(f"   Path: {link_data['path']}")
            print(f"   URL: {link_data['url']}")
            
            # CRITICAL: Verify this is indeed a Flipkart link and doesn't have offers
            store_link_ref = link_data['store_link_ref']
            if 'ranked_offers' in store_link_ref and store_link_ref['ranked_offers']:
                print(f"   ⏭️  Link already has offers, skipping to preserve existing data")
                continue
            
            # Get Flipkart offers
            offers = get_flipkart_offers(driver, link_data['url'])
            
            if offers:
                # Get product price for ranking
                price_str = store_link_ref.get('price', '₹0')
                product_price = extract_price_amount(price_str)
                
                # Rank the offers
                ranked_offers = analyzer.rank_offers(offers, product_price)
                
                # CRITICAL: Update ONLY the Flipkart store link (no other changes)
                store_link_ref['ranked_offers'] = ranked_offers
                
                processed_count += 1
                new_offers_count += len(ranked_offers)
                
                print(f"   ✅ Added {len(ranked_offers)} ranked offers")
                
                # Log top offers
                for i, offer in enumerate(ranked_offers[:2], 1):
                    score_display = offer['score'] if offer['score'] is not None else 'N/A'
                    print(f"      Rank {i}: {offer['title']} (Score: {score_display}, Amount: ₹{offer['amount']})")
            else:
                print(f"   ❌ No offers found")
                store_link_ref['ranked_offers'] = []
                processed_count += 1
            
            # Save progress every 10 entries
            if (idx + 1) % 10 == 0:
                temp_backup = f"{output_file}.progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(temp_backup, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"   💾 Progress saved to {temp_backup}")
            
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
        
        # Summary
        print(f"\n📊 COMPREHENSIVE FLIPKART PROCESSING SUMMARY:")
        print(f"   Flipkart links processed: {processed_count}")
        print(f"   New offers added: {new_offers_count}")
        print(f"   🔒 Amazon offers: COMPLETELY ISOLATED (no changes)")
        print(f"   🔒 Croma offers: COMPLETELY ISOLATED (no changes)")
        print(f"   ✅ Backup created: {backup_file}")

if __name__ == "__main__":
    import sys
    
    print("🚀 Enhanced Comprehensive Flipkart Scraper")
    print("📍 Target: comprehensive_amazon_offers.json")
    print("🔒 Amazon & Croma offers: COMPLETELY ISOLATED")
    print("🎯 Focus: ONLY Flipkart links without existing offers")
    print("🔍 Traversal: ALL nested locations (variants, all_matching_products, unmapped)")
    print("-" * 80)
    
    # Check for command line arguments
    if len(sys.argv) > 1 and '--headless' in sys.argv:
        os.environ['HEADLESS'] = 'true'
        print("🤖 Headless mode enabled via command line")
    elif len(sys.argv) > 1 and '--gui' in sys.argv:
        os.environ['HEADLESS'] = 'false'
        print("🖥️  GUI mode enabled via command line")
    
    # Ask user for browser mode if not specified
    if 'HEADLESS' not in os.environ:
        while True:
            browser_mode = input("Run in headless mode? (y/n) [y for servers]: ").lower().strip()
            if browser_mode in ['y', 'yes', '']:
                os.environ['HEADLESS'] = 'true'
                break
            elif browser_mode in ['n', 'no']:
                os.environ['HEADLESS'] = 'false'
                break
            else:
                print("Please enter 'y' for yes or 'n' for no")
    
    # Ask user for parameters
    while True:
        try:
            start_idx = input("Enter start index (or 0 for beginning): ")
            start_idx = int(start_idx) if start_idx else 0
            break
        except ValueError:
            print("Please enter a valid number")
    
    while True:
        try:
            max_entries = input("Enter max entries to process (or 'all' for all): ")
            if max_entries.lower() == 'all':
                max_entries = None
                break
            else:
                max_entries = int(max_entries)
                if max_entries > 0:
                    break
                else:
                    print("Please enter a positive number")
        except ValueError:
            print("Please enter a valid number or 'all'")
    
    process_comprehensive_flipkart_links(
        input_file="comprehensive_amazon_offers.json",
        output_file="comprehensive_amazon_offers.json",
        start_idx=start_idx,
        max_entries=max_entries
    ) 