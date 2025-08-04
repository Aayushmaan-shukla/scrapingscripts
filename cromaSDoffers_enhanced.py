#!/usr/bin/env python3
"""
Enhanced Croma Bank Offer Scraper with Advanced Ranking Logic
============================================================
- Same advanced logic as Amazon and Flipkart scripts
- Comprehensive bank detection and card type identification
- Intelligent offer ranking and scoring
- Human-like comprehensive notes
- Uses flipkart_ranked_offers_test.json as input
- Only processes Croma store links without affecting others
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

# Setup logging
logging.basicConfig(
    filename='enhanced_croma_scraper.log',
    filemode='a',
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO
)

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
    percentage: Optional[float] = None  # For percentage-based offers like "upto x%"

class CromaOfferAnalyzer:
    def __init__(self):
        # Comprehensive bank reputation scores for Indian banks (same as Amazon/Flipkart scripts)
        self.bank_scores = {
            # Public Sector Banks (PSBs)
            "SBI": 75,
            "State Bank of India": 75,
            "PNB": 72,
            "Punjab National Bank": 72,
            "BoB": 70,
            "Bank of Baroda": 70,
            "Canara Bank": 68,
            "Union Bank of India": 65,
            "Indian Bank": 65,
            "Bank of India": 65,
            "UCO Bank": 62,
            "Indian Overseas Bank": 62,
            "IOB": 62,
            "Central Bank of India": 62,
            "Bank of Maharashtra": 60,
            "Punjab & Sind Bank": 60,
            
            # Private Sector Banks
            "HDFC": 85,
            "HDFC Bank": 85,
            "ICICI": 90,
            "ICICI Bank": 90,
            "Axis": 80,
            "Axis Bank": 80,
            "Kotak": 70,
            "Kotak Mahindra Bank": 70,
            "IndusInd Bank": 68,
            "Yes Bank": 60,
            "IDFC FIRST Bank": 65,
            "IDFC": 65,
            "Federal Bank": 63,
            "South Indian Bank": 60,
            "RBL Bank": 62,
            "DCB Bank": 60,
            "Tamilnad Mercantile Bank": 58,
            "TMB": 58,
            "Karur Vysya Bank": 58,
            "CSB Bank": 58,
            "City Union Bank": 58,
            "Bandhan Bank": 60,
            "Jammu & Kashmir Bank": 58,
            
            # Small Finance Banks
            "AU Small Finance Bank": 65,
            "AU Bank": 65,
            "Equitas Small Finance Bank": 62,
            "Equitas": 62,
            "Ujjivan Small Finance Bank": 60,
            "Ujjivan": 60,
            "Suryoday Small Finance Bank": 58,
            "ESAF Small Finance Bank": 58,
            "Fincare Small Finance Bank": 58,
            "Jana Small Finance Bank": 58,
            "North East Small Finance Bank": 58,
            "Capital Small Finance Bank": 58,
            "Unity Small Finance Bank": 58,
            "Shivalik Small Finance Bank": 58,
            
            # Foreign Banks
            "Citi": 80,
            "Citibank": 80,
            "HSBC": 78,
            "Standard Chartered": 75,
            "Deutsche Bank": 75,
            "Barclays Bank": 75,
            "DBS Bank": 72,
            "JP Morgan Chase Bank": 75,
            "Bank of America": 75,
            
            # Co-operative Banks
            "Saraswat Co-operative Bank": 60,
            "Saraswat Bank": 60,
            "Shamrao Vithal Co-operative Bank": 55,
            "PMC Bank": 50,
            "TJSB Sahakari Bank": 55,
            
            # Credit Card Companies
            "Amex": 85,
            "American Express": 85
        }
        
        # Enhanced bank name patterns for better matching
        self.bank_name_patterns = {
            # Common abbreviations and variations
            "SBI": ["SBI", "State Bank", "State Bank of India"],
            "HDFC": ["HDFC", "HDFC Bank"],
            "ICICI": ["ICICI", "ICICI Bank"],
            "Axis": ["Axis", "Axis Bank"],
            "Kotak": ["Kotak", "Kotak Mahindra"],
            "Yes Bank": ["Yes Bank", "YES Bank"],
            "IDFC": ["IDFC", "IDFC FIRST", "IDFC Bank"],
            "IndusInd": ["IndusInd", "IndusInd Bank"],
            "Federal": ["Federal", "Federal Bank"],
            "RBL": ["RBL", "RBL Bank"],
            "Citi": ["Citi", "Citibank", "CitiBank"],
            "HSBC": ["HSBC"],
            "Standard Chartered": ["Standard Chartered", "StanChart", "SC Bank"],
            "AU Bank": ["AU Bank", "AU Small Finance", "AU"],
            "Equitas": ["Equitas", "Equitas Bank"],
            "Ujjivan": ["Ujjivan", "Ujjivan Bank"],
            "PNB": ["PNB", "Punjab National Bank"],
            "BoB": ["BoB", "Bank of Baroda", "Baroda"],
            "Canara": ["Canara", "Canara Bank"],
            "Union Bank": ["Union Bank", "Union Bank of India"],
            "Indian Bank": ["Indian Bank"],
            "Bank of India": ["Bank of India"],
            "UCO Bank": ["UCO", "UCO Bank"],
            "Indian Overseas Bank": ["IOB", "Indian Overseas"],
            "Central Bank": ["Central Bank", "Central Bank of India"],
            "Bank of Maharashtra": ["Bank of Maharashtra", "Maharashtra Bank"],
            "Amex": ["Amex", "American Express"],
            "DBS": ["DBS", "DBS Bank"]
        }
        
        # Card providers list
        self.card_providers = [
            "Visa", "Mastercard", "RuPay", "American Express", "Amex", 
            "Diners Club", "Discover", "UnionPay", "JCB", "Maestro", 
            "Cirrus", "PLUS"
        ]
        
        # Default bank score if not found in the list
        self.default_bank_score = 70

    def extract_card_type(self, description: str) -> Optional[str]:
        """Extract card type (Credit/Debit) from offer description with enhanced detection."""
        description_lower = description.lower()
        
        # Enhanced patterns for better detection
        credit_patterns = [
            r'\bcredit\s+card\b', r'\bcc\b', r'\bcredit\b.*\bcard\b',
            r'\bmaster\s+card\b', r'\bvisa\s+card\b.*\bcredit\b'
        ]
        
        debit_patterns = [
            r'\bdebit\s+card\b', r'\bdc\b', r'\bdebit\b.*\bcard\b',
            r'\bvisa\s+card\b.*\bdebit\b', r'\bmaster\s+card\b.*\bdebit\b'
        ]
        
        # Check for credit card patterns
        if any(re.search(pattern, description_lower) for pattern in credit_patterns):
            # Check if it's both credit and debit
            if any(re.search(pattern, description_lower) for pattern in debit_patterns):
                return "Credit/Debit"
            return "Credit"
        
        # Check for debit card patterns
        if any(re.search(pattern, description_lower) for pattern in debit_patterns):
            return "Debit"
        
        # Check for general card mentions
        if re.search(r'\bcard\b', description_lower):
            # If card is mentioned but type is unclear, try to infer from context
            if any(word in description_lower for word in ['premium', 'rewards', 'cashback', 'points']):
                return "Credit"  # Premium features usually indicate credit cards
            elif 'atm' in description_lower:
                return "Debit"
        
        return None

    def extract_card_provider(self, description: str) -> Optional[str]:
        """Extract card provider from offer description with enhanced matching."""
        description_lower = description.lower()
        
        # Enhanced provider matching with context
        for provider in self.card_providers:
            # Direct match
            if provider.lower() in description_lower:
                return provider
            
            # Special cases for common variations
            if provider == "Mastercard" and "master" in description_lower:
                return "Mastercard"
            elif provider == "RuPay" and "rupay" in description_lower:
                return "RuPay"
        
        return None

    def extract_amount(self, description: str) -> float:
        """Extract numerical amount from offer description with enhanced patterns."""
        try:
            # Enhanced flat discount patterns
            flat_patterns = [
                r'(?:Additional\s+)?[Ff]lat\s+(?:INR\s+|₹\s*)([\d,]+\.?\d*)',
                r'(?:Additional\s+)?(?:INR\s+|₹\s*)([\d,]+\.?\d*)\s+(?:Instant\s+)?Discount',
                r'(?:Get\s+)?(?:INR\s+|₹\s*)([\d,]+\.?\d*)\s+(?:off|discount)',
                r'(?:Save\s+)?(?:INR\s+|₹\s*)([\d,]+\.?\d*)',
                r'₹\s*([\d,]+\.?\d*)',
                r'Rs\.?\s*([\d,]+\.?\d*)',
                r'INR\s*([\d,]+\.?\d*)'
            ]
            
            for pattern in flat_patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match:
                    amount = float(match.group(1).replace(',', ''))
                    logging.info(f"Extracted amount: ₹{amount} using pattern: {pattern[:30]}...")
                    return amount
            
            # Handle percentage discounts with caps
            percent_patterns = [
                r'([\d.]+)%\s+(?:Instant\s+)?Discount\s+up\s+to\s+(?:INR\s+|₹\s*)([\d,]+\.?\d*)',
                r'Up\s+to\s+([\d.]+)%\s+(?:off|discount).*?(?:max|maximum|up\s+to)\s+(?:INR\s+|₹\s*)([\d,]+\.?\d*)',
                r'([\d.]+)%\s+(?:off|discount).*?(?:capped\s+at|maximum)\s+(?:INR\s+|₹\s*)([\d,]+\.?\d*)'
            ]
            
            for pattern in percent_patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match:
                    cap_amount = float(match.group(2).replace(',', ''))
                    logging.info(f"Extracted capped amount: ₹{cap_amount} from percentage offer")
                    return cap_amount
            
            # Handle cashback patterns
            cashback_patterns = [
                r'(?:Get\s+)?(?:INR\s+|₹\s*)([\d,]+\.?\d*)\s+(?:cashback|cash\s+back)',
                r'(?:Earn\s+)?(?:INR\s+|₹\s*)([\d,]+\.?\d*)\s+(?:cashback|cash\s+back)'
            ]
            
            for pattern in cashback_patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match:
                    amount = float(match.group(1).replace(',', ''))
                    logging.info(f"Extracted cashback amount: ₹{amount}")
                    return amount
            
            return 0.0
        except (ValueError, AttributeError) as e:
            logging.warning(f"Error extracting amount from '{description[:50]}...': {e}")
            return 0.0

    def extract_percentage(self, description: str) -> Optional[float]:
        """Extract percentage value from offer description for percentage-based offers."""
        try:
            # Patterns to extract percentage values without caps (for "upto x%" offers)
            percentage_patterns = [
                r'(?:up\s+to|upto)\s+([\d.]+)%',
                r'([\d.]+)%\s+(?:off|discount)(?!\s+up\s+to)',  # Percentage without "up to" following
                r'get\s+([\d.]+)%\s+(?:off|discount)',
                r'save\s+([\d.]+)%'
            ]
            
            for pattern in percentage_patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match:
                    percentage = float(match.group(1))
                    logging.info(f"Extracted percentage: {percentage}% from description")
                    return percentage
            
            return None
        except (ValueError, AttributeError) as e:
            logging.warning(f"Error extracting percentage from '{description[:50]}...': {e}")
            return None

    def extract_bank(self, description: str) -> Optional[str]:
        """Extract bank names from offer description, supporting multiple banks separated by commas/&."""
        if not description:
            return None
        
        description_lower = description.lower()
        found_banks = set()  # Use set to avoid duplicates
        
        # Enhanced pattern matching for common bank variations
        bank_variations = {
            'hdfc': 'HDFC',
            'icici': 'ICICI', 
            'axis': 'Axis',
            'sbi': 'SBI',
            'kotak': 'Kotak',
            'yes bank': 'Yes Bank',
            'yes': 'Yes Bank',
            'idfc': 'IDFC',
            'indusind': 'IndusInd Bank',
            'federal': 'Federal Bank',
            'rbl': 'RBL Bank',
            'citi': 'Citi',
            'citibank': 'Citi',
            'hsbc': 'HSBC',
            'standard chartered': 'Standard Chartered',
            'au bank': 'AU Bank',
            'au': 'AU Bank',
            'equitas': 'Equitas',
            'ujjivan': 'Ujjivan',
            'pnb': 'PNB',
            'punjab national bank': 'PNB',
            'bob': 'BoB',
            'bank of baroda': 'BoB',
            'baroda': 'BoB',
            'canara': 'Canara Bank',
            'canara bank': 'Canara Bank',
            'union bank': 'Union Bank of India',
            'indian bank': 'Indian Bank',
            'bank of india': 'Bank of India',
            'uco': 'UCO Bank',
            'uco bank': 'UCO Bank',
            'iob': 'Indian Overseas Bank',
            'indian overseas bank': 'Indian Overseas Bank',
            'central bank': 'Central Bank of India',
            'amex': 'Amex',
            'american express': 'American Express'
        }
        
        # First, try exact matches with bank name patterns (longest first to avoid partial matches)
        for bank_key, patterns in self.bank_name_patterns.items():
            for pattern in patterns:
                if pattern.lower() in description_lower:
                    found_banks.add(bank_key)
                    logging.info(f"Found bank '{bank_key}' using pattern '{pattern}' in description")
        
        # If no pattern match, try direct bank scores dictionary
        if not found_banks:
            sorted_banks = sorted(self.bank_scores.keys(), key=len, reverse=True)
            for bank in sorted_banks:
                if bank.lower() in description_lower:
                    found_banks.add(bank)
                    logging.info(f"Found bank '{bank}' through direct matching in description")
        
        # Try bank variations if still no matches
        if not found_banks:
            for variation, standard_name in bank_variations.items():
                if variation in description_lower:
                    found_banks.add(standard_name)
                    logging.info(f"Found bank '{standard_name}' using variation '{variation}' in description")
        
        # Return comma-separated list of banks if multiple found, or single bank
        if found_banks:
            banks_list = sorted(list(found_banks))  # Sort for consistency
            result = ', '.join(banks_list)
            logging.info(f"Final extracted banks: {result}")
            return result
        
        logging.debug(f"No bank found in description: {description[:100]}...")
        return None

    def extract_validity(self, description: str) -> Optional[str]:
        """Extract validity period from offer description with enhanced patterns."""
        validity_patterns = [
            r'valid\s+(?:till|until|up\s+to)\s+([^,\.;]+)',
            r'offer\s+valid\s+(?:till|until|up\s+to)\s+([^,\.;]+)',
            r'expires?\s+(?:on|by)?\s+([^,\.;]+)',
            r'valid\s+(?:from|between).*?(?:to|till|until)\s+([^,\.;]+)',
            r'(?:validity|valid)\s*:\s*([^,\.;]+)'
        ]
        
        for pattern in validity_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                validity = match.group(1).strip()
                logging.info(f"Extracted validity: {validity}")
                return validity
        
        return None

    def extract_min_spend(self, description: str) -> Optional[float]:
        """Extract minimum spend requirement from offer description with enhanced patterns."""
        # Enhanced patterns to catch different formats
        patterns = [
            r'(?:Mini|Minimum)\s+purchase\s+value\s+(?:of\s+)?(?:INR\s+|₹\s*|Rs\.?\s*)([\d,]+\.?\d*)',
            r'(?:Mini|Minimum)\s+(?:purchase|spend|transaction)\s+(?:of\s+|value\s+)?(?:INR\s+|₹\s*|Rs\.?\s*)([\d,]+\.?\d*)',
            r'min(?:imum)?\s+(?:purchase|spend|transaction)\s+(?:of\s+|value\s+)?(?:INR\s+|₹\s*|Rs\.?\s*)([\d,]+\.?\d*)',
            r'valid\s+on\s+(?:orders?|purchases?)\s+(?:of\s+|above\s+|worth\s+)(?:INR\s+|₹\s*|Rs\.?\s*)([\d,]+\.?\d*)',
            r'applicable\s+on\s+(?:purchases?|orders?|transactions?)\s+(?:of\s+|above\s+|worth\s+)(?:INR\s+|₹\s*|Rs\.?\s*)([\d,]+\.?\d*)',
            r'(?:on\s+)?(?:orders?|purchases?|spending)\s+(?:of\s+|above\s+|worth\s+)(?:INR\s+|₹\s*|Rs\.?\s*)([\d,]+\.?\d*)\s+(?:or\s+more|and\s+above)',
            r'(?:minimum|min)\s+(?:spend|purchase|order)\s*:\s*(?:INR\s+|₹\s*|Rs\.?\s*)([\d,]+\.?\d*)',
            r'(?:spend|purchase|order)\s+(?:minimum|min|at\s+least)\s+(?:INR\s+|₹\s*|Rs\.?\s*)([\d,]+\.?\d*)'
        ]
        
        for pattern in patterns:
            min_spend_match = re.search(pattern, description, re.IGNORECASE)
            if min_spend_match:
                try:
                    extracted_value = float(min_spend_match.group(1).replace(',', ''))
                    logging.info(f"Extracted min_spend: ₹{extracted_value} from: {description[:100]}...")
                    return extracted_value
                except ValueError:
                    continue
        
        logging.debug(f"No min_spend found in: {description[:100]}...")
        return None

    def determine_offer_type(self, card_title: str, description: str) -> str:
        """Determine offer type based on card title and description."""
        card_title_lower = card_title.lower() if card_title else ""
        description_lower = description.lower() if description else ""
        
        # Enhanced type detection for Croma
        if any(keyword in card_title_lower for keyword in ['bank offer', 'instant discount', 'card offer']):
            return "Bank Offer"
        elif any(keyword in card_title_lower for keyword in ['no cost emi', 'no-cost emi', 'emi']):
            return "No Cost EMI"
        elif any(keyword in card_title_lower for keyword in ['cashback', 'cash back']):
            return "Cashback"
        elif any(keyword in card_title_lower for keyword in ['exchange offer', 'exchange']):
            return "Exchange Offer"
        elif any(keyword in card_title_lower for keyword in ['partner offer', 'partner']):
            return "Partner Offers"
        elif any(keyword in description_lower for keyword in ['bank', 'credit card', 'debit card']):
            return "Bank Offer"  # Fallback for bank-related offers
        elif any(keyword in description_lower for keyword in ['emi', 'no cost']):
            return "No Cost EMI"
        else:
            return card_title if card_title else "Croma Offer"

    def parse_offer(self, offer: Dict[str, str]) -> Offer:
        """Parse offer details from raw offer data with enhanced processing."""
        card_title = offer.get('card_type', '').strip()
        description = offer.get('offer_description', '').strip()
        
        # Determine offer type
        offer_type = self.determine_offer_type(card_title, description)
        
        # Fix title for bank offers - ensure it's never blank
        if offer_type == "Bank Offer":
            title = "Bank Offer"
        elif not card_title or card_title.lower() in ['summary', '', 'croma offer']:
            # If title is empty or generic, use the offer type
            title = offer_type
        else:
            title = card_title
        
        # Extract offer details
        amount = self.extract_amount(description)
        percentage = self.extract_percentage(description)  # Extract percentage for "upto x%" offers
        bank = self.extract_bank(description)  # This now supports multiple banks
        validity = self.extract_validity(description)
        min_spend = self.extract_min_spend(description)
        card_type = self.extract_card_type(description)
        card_provider = self.extract_card_provider(description)
        
        # Determine if it's an instant discount
        is_instant = 'instant' in description.lower() or 'cashback' not in description.lower()
        
        # Enhanced logging
        logging.info(f"Parsed offer - Original Title: '{card_title}' -> Final Title: '{title}', Type: {offer_type}, Amount: ₹{amount}, Percentage: {percentage}%, Bank: {bank}, Min_spend: ₹{min_spend if min_spend else 'None'}, Card Type: {card_type}, Card Provider: {card_provider}")
        
        return Offer(
            title=title,
            description=description,
            amount=amount,
            type=offer_type,
            bank=bank,
            validity=validity,
            min_spend=min_spend,
            is_instant=is_instant,
            card_type=card_type,
            card_provider=card_provider,
            percentage=percentage
        )

    def generate_comprehensive_note(self, offer: Offer, product_price: float, is_applicable: bool, net_effective_price: float) -> str:
        """Generate comprehensive, human-like notes for offers."""
        if offer.type == "Bank Offer":
            if is_applicable:
                savings_amount = product_price - net_effective_price
                savings_percentage = (savings_amount / product_price) * 100 if product_price > 0 else 0
                
                note_parts = []
                
                # Main benefit description
                if savings_amount > 0:
                    note_parts.append(f"🎉 Fantastic Croma deal! You'll save ₹{savings_amount:,.0f} ({savings_percentage:.1f}%) with this bank offer.")
                else:
                    note_parts.append("💡 Excellent Croma bank offer available for your purchase!")
                
                # Bank and card details
                bank_info = ""
                if offer.bank and offer.card_type:
                    bank_info = f"using your {offer.bank} {offer.card_type.lower()} card"
                elif offer.bank:
                    bank_info = f"using your {offer.bank} card"
                elif offer.card_type:
                    bank_info = f"using your {offer.card_type.lower()} card"
                
                if bank_info:
                    note_parts.append(f"Simply pay {bank_info} to get ₹{offer.amount:,.0f} instant discount at Croma.")
                else:
                    note_parts.append(f"You'll get ₹{offer.amount:,.0f} instant discount on your Croma purchase.")
                
                # Minimum spend information
                if offer.min_spend:
                    note_parts.append(f"✅ This phone (₹{product_price:,.0f}) meets the minimum spend requirement of ₹{offer.min_spend:,.0f}.")
                else:
                    note_parts.append("✅ No minimum purchase requirement - the discount applies immediately!")
                
                # Final price information
                note_parts.append(f"Your final Croma price will be ₹{net_effective_price:,.0f} instead of ₹{product_price:,.0f}.")
                
                # Additional details
                if offer.card_provider:
                    note_parts.append(f"Works with {offer.card_provider} cards.")
                
                if offer.validity:
                    note_parts.append(f"⏰ Offer valid {offer.validity}.")
                
                return " ".join(note_parts)
            
            else:
                # Not applicable - minimum spend not met
                shortfall = offer.min_spend - product_price if offer.min_spend else 0
                
                note_parts = []
                note_parts.append(f"⚠️ This Croma bank offer isn't applicable for this phone's current price.")
                note_parts.append(f"The offer requires a minimum purchase of ₹{offer.min_spend:,.0f}, but this phone costs ₹{product_price:,.0f}.")
                note_parts.append(f"You would need to add ₹{shortfall:,.0f} more to your cart to use this offer.")
                
                if offer.bank and offer.card_type:
                    note_parts.append(f"However, if you reach the minimum spend using your {offer.bank} {offer.card_type.lower()} card, you could save ₹{offer.amount:,.0f}!")
                elif offer.bank:
                    note_parts.append(f"But if you meet the minimum spend with your {offer.bank} card, you could save ₹{offer.amount:,.0f}!")
                else:
                    note_parts.append(f"If you meet the minimum spend, you could save ₹{offer.amount:,.0f}!")
                
                if offer.validity:
                    note_parts.append(f"⏰ Offer valid {offer.validity}.")
                
                return " ".join(note_parts)
        
        elif offer.type == "No Cost EMI":
            note_parts = []
            note_parts.append(f"💳 Convert your Croma purchase into easy EMIs without any additional interest charges!")
            
            if offer.amount > 0:
                note_parts.append(f"You can save up to ₹{offer.amount:,.0f} on interest that you would normally pay.")
            
            if offer.min_spend and not is_applicable:
                note_parts.append(f"⚠️ This EMI option requires a minimum purchase of ₹{offer.min_spend:,.0f}, but this phone costs ₹{product_price:,.0f}.")
            elif offer.min_spend:
                note_parts.append(f"✅ This phone meets the minimum requirement of ₹{offer.min_spend:,.0f} for no-cost EMI.")
            else:
                note_parts.append("✅ Available for this Croma purchase with no minimum spend requirement.")
            
            if offer.bank:
                note_parts.append(f"Available with {offer.bank} cards.")
            
            if offer.validity:
                note_parts.append(f"⏰ Offer valid {offer.validity}.")
            
            return " ".join(note_parts)
        
        elif offer.type == "Exchange Offer":
            note_parts = []
            note_parts.append(f"📱 Great exchange opportunity at Croma!")
            
            if offer.amount > 0:
                note_parts.append(f"You can get up to ₹{offer.amount:,.0f} off by exchanging your old device.")
            else:
                note_parts.append("Trade in your old device to get additional discount on this phone.")
            
            note_parts.append("The final exchange value depends on your device's condition and model.")
            
            if offer.validity:
                note_parts.append(f"⏰ Exchange offer valid {offer.validity}.")
            
            return " ".join(note_parts)
        
        elif offer.type == "Cashback":
            note_parts = []
            
            if is_applicable:
                note_parts.append(f"💰 Earn ₹{offer.amount:,.0f} cashback on your Croma purchase!")
                note_parts.append("The cashback will be credited to your account after the purchase.")
                
                if offer.min_spend:
                    note_parts.append(f"✅ This phone (₹{product_price:,.0f}) meets the minimum spend requirement of ₹{offer.min_spend:,.0f}.")
                else:
                    note_parts.append("✅ No minimum purchase requirement.")
            else:
                note_parts.append(f"⚠️ This Croma cashback offer requires a minimum purchase of ₹{offer.min_spend:,.0f}.")
                note_parts.append(f"This phone costs ₹{product_price:,.0f}, so you'll need to add ₹{offer.min_spend - product_price:,.0f} more to qualify.")
            
            if offer.bank:
                note_parts.append(f"Available with {offer.bank} cards.")
            
            if offer.validity:
                note_parts.append(f"⏰ Offer valid {offer.validity}.")
            
            return " ".join(note_parts)
        
        else:
            # Generic offer type
            note_parts = []
            if offer.amount > 0:
                note_parts.append(f"💫 This Croma {offer.type.lower()} offers ₹{offer.amount:,.0f} value.")
            else:
                note_parts.append(f"💫 Special Croma {offer.type.lower()} available for your purchase.")
            
            if not is_applicable and offer.min_spend:
                note_parts.append(f"⚠️ Requires minimum purchase of ₹{offer.min_spend:,.0f}.")
            elif is_applicable and offer.min_spend:
                note_parts.append(f"✅ This phone meets the minimum requirement of ₹{offer.min_spend:,.0f}.")
            
            if offer.validity:
                note_parts.append(f"⏰ Offer valid {offer.validity}.")
            
            return " ".join(note_parts)

    def calculate_offer_score(self, offer: Offer, product_price: float) -> float:
        """Calculate score specifically for Bank Offers only."""
        
        # Only calculate scores for Bank Offers
        if offer.type != "Bank Offer":
            return 0
        
        base_score = 80  # Base score for Bank Offers
        
        # PRIMARY FACTOR: Discount amount (heavily weighted) - handle both percentage and fixed amount
        if product_price > 0:
            if offer.percentage and offer.percentage > 0:
                # For percentage-based offers, use the percentage directly
                discount_percentage = offer.percentage
                # High weight for discount amount (up to 50 points)
                discount_points = min(discount_percentage * 2, 50)
                actual_discount = (offer.percentage / 100) * product_price
                base_score += discount_points
                logging.info(f"Bank Offer percentage discount bonus: {discount_points:.1f} points for {offer.percentage}% (₹{actual_discount:.2f}) discount")
            elif offer.amount > 0:
                # For fixed amount offers
                discount_percentage = (offer.amount / product_price) * 100
                # High weight for discount amount (up to 50 points)
                discount_points = min(discount_percentage * 2, 50)  
                base_score += discount_points
                logging.info(f"Bank Offer fixed discount bonus: {discount_points:.1f} points for ₹{offer.amount} discount")

        # CRITICAL FACTOR: Minimum spend requirement
        if offer.min_spend and offer.min_spend > product_price:
            # Check if ALL bank offers have min spend > product price
            # For now, apply penalty but keep some score for ranking among non-applicable offers
            penalty_percentage = ((offer.min_spend - product_price) / product_price) * 100
            
            if penalty_percentage > 50:  # Very high min spend
                base_score = 15  # Low but rankable score
                logging.info(f"HIGH MIN SPEND: ₹{offer.min_spend} vs ₹{product_price} - Score set to 15")
            else:
                # Moderate penalty
                penalty = penalty_percentage * 0.5
                base_score -= penalty
                base_score = max(base_score, 20)  # Minimum rankable score
                logging.info(f"MODERATE MIN SPEND PENALTY: -{penalty:.1f} points")
        
        # BONUS: For applicable offers (min spend <= product price)
        elif offer.min_spend is None or offer.min_spend <= product_price:
            # Major bonus for applicable offers
            if offer.min_spend is None:
                base_score += 20  # Big bonus for no restrictions
                logging.info(f"NO MIN SPEND BONUS: +20 points")
            else:
                # Bonus for reasonable minimum spend
                spend_ratio = offer.min_spend / product_price if product_price > 0 else 0
                if spend_ratio <= 0.9:  # Min spend is 90% or less of product price
                    bonus = (1 - spend_ratio) * 10  # Up to 10 points bonus
                    base_score += bonus
                    logging.info(f"REASONABLE MIN SPEND BONUS: +{bonus:.1f} points")

        # INSTANT DISCOUNT BONUS
        if offer.is_instant:
            base_score += 5
            logging.info(f"INSTANT DISCOUNT BONUS: +5 points")

        # Bank reputation bonus - enhanced to handle null banks
        if offer.bank:
            bank_bonus = (self.bank_scores.get(offer.bank, self.default_bank_score) - 70) / 2
            base_score += bank_bonus
            logging.info(f"BANK BONUS: +{bank_bonus:.1f} points for {offer.bank}")
        else:
            # Penalty for unknown bank, but not too harsh
            base_score -= 5
            logging.info(f"UNKNOWN BANK PENALTY: -5 points")

        # Card type bonus
        if offer.card_type:
            if offer.card_type == "Credit":
                base_score += 3  # Credit cards generally have better offers
                logging.info(f"CREDIT CARD BONUS: +3 points")
            elif offer.card_type == "Credit/Debit":
                base_score += 2  # Flexible options get moderate bonus
                logging.info(f"CREDIT/DEBIT CARD BONUS: +2 points")
            elif offer.card_type == "Debit":
                base_score += 1  # Debit cards get small bonus
                logging.info(f"DEBIT CARD BONUS: +1 point")

        # Card provider bonus
        if offer.card_provider:
            provider_bonus = {
                "Visa": 2, "Mastercard": 2, "RuPay": 3,  # RuPay gets extra for being domestic
                "American Express": 4, "Amex": 4,  # Premium cards
                "Diners Club": 3
            }.get(offer.card_provider, 1)  # Default bonus for other providers
            base_score += provider_bonus
            logging.info(f"CARD PROVIDER BONUS: +{provider_bonus} points for {offer.card_provider}")

        final_score = max(0, min(100, base_score))
        
        # Enhanced logging with percentage information
        if offer.percentage and offer.percentage > 0:
            actual_discount = (offer.percentage / 100) * product_price
            logging.info(f"FINAL BANK OFFER SCORE: {final_score:.1f} for {offer.percentage}% discount (₹{actual_discount:.2f}) (Bank: {offer.bank}, Min spend: ₹{offer.min_spend if offer.min_spend else 'None'}, Card: {offer.card_type}, Provider: {offer.card_provider})")
        else:
            logging.info(f"FINAL BANK OFFER SCORE: {final_score:.1f} for ₹{offer.amount} discount (Bank: {offer.bank}, Min spend: ₹{offer.min_spend if offer.min_spend else 'None'}, Card: {offer.card_type}, Provider: {offer.card_provider})")
        
        return final_score

    def rank_offers(self, offers_data: List[Dict], product_price: float) -> List[Dict[str, Any]]:
        """Rank offers based on comprehensive scoring - focusing only on Bank Offers."""
        logging.info(f"Ranking Croma offers for product price: ₹{product_price}")
        
        # Parse all offers
        parsed_offers = [self.parse_offer(offer) for offer in offers_data if isinstance(offer, dict)]
        
        # Separate Bank Offers from other offers
        bank_offers = [offer for offer in parsed_offers if offer.type == "Bank Offer"]
        other_offers = [offer for offer in parsed_offers if offer.type != "Bank Offer"]
        
        logging.info(f"Found {len(bank_offers)} Bank Offers and {len(other_offers)} other offers")
        
        # Process all offers (both bank and others) to create the result list
        all_ranked_offers = []
        
        # Process Bank Offers with ranking
        if bank_offers:
            # Calculate scores for bank offers only
            scored_bank_offers = []
            for offer in bank_offers:
                score = self.calculate_offer_score(offer, product_price)
                
                # Calculate net effective price and applicability
                if offer.min_spend and product_price < offer.min_spend:
                    net_effective_price = product_price  # Offer not applicable - no discount
                    is_applicable = False
                    logging.info(f"Bank Offer NOT applicable - Min spend: ₹{offer.min_spend}, Product price: ₹{product_price}")
                else:
                    # Calculate discount amount based on percentage or fixed amount
                    if offer.percentage and offer.percentage > 0:
                        # For percentage-based offers, calculate discount as percentage of product price
                        discount_amount = (offer.percentage / 100) * product_price
                        net_effective_price = max(product_price - discount_amount, 0)
                        logging.info(f"Bank Offer applicable - {offer.percentage}% discount = ₹{discount_amount:.2f}, Net price: ₹{net_effective_price}")
                    else:
                        # For fixed amount offers
                        net_effective_price = max(product_price - offer.amount, 0)
                        logging.info(f"Bank Offer applicable - Fixed ₹{offer.amount} discount, Net price: ₹{net_effective_price}")
                    is_applicable = True
                
                # Generate comprehensive human-like note
                note = self.generate_comprehensive_note(offer, product_price, is_applicable, net_effective_price)
                
                scored_bank_offers.append({
                    'title': offer.title,
                    'description': offer.description,
                    'amount': offer.amount,
                    'percentage': offer.percentage,  # Include percentage information
                    'bank': offer.bank,
                    'validity': offer.validity,
                    'min_spend': offer.min_spend,
                    'score': score,
                    'is_instant': offer.is_instant,
                    'net_effective_price': net_effective_price,
                    'is_applicable': is_applicable,
                    'note': note,
                    'offer_type': 'Bank Offer',
                    'card_type': offer.card_type,
                    'card_provider': offer.card_provider
                })
            
            # Sort bank offers by score in descending order
            scored_bank_offers.sort(key=lambda x: x['score'], reverse=True)
            
            # Add rank numbers to bank offers only
            for idx, offer in enumerate(scored_bank_offers):
                offer['rank'] = idx + 1
            
            all_ranked_offers.extend(scored_bank_offers)
        
        # Process other offers (No Cost EMI, Cashback, Exchange, etc.) - no ranking
        for offer in other_offers:
            # Calculate basic info but no ranking
            if offer.min_spend and product_price < offer.min_spend:
                net_effective_price = product_price
                is_applicable = False
            else:
                # Calculate discount amount based on percentage or fixed amount
                if offer.percentage and offer.percentage > 0:
                    # For percentage-based offers, calculate discount as percentage of product price
                    discount_amount = (offer.percentage / 100) * product_price
                    net_effective_price = max(product_price - discount_amount, 0)
                else:
                    # For fixed amount offers
                    net_effective_price = max(product_price - offer.amount, 0)
                is_applicable = True
            
            # Generate comprehensive human-like note
            note = self.generate_comprehensive_note(offer, product_price, is_applicable, net_effective_price)
            
            all_ranked_offers.append({
                'title': offer.title,
                'description': offer.description,
                'amount': offer.amount,
                'percentage': offer.percentage,  # Include percentage information
                'bank': offer.bank,
                'validity': offer.validity,
                'min_spend': offer.min_spend,
                'score': None,  # No score for non-bank offers
                'is_instant': offer.is_instant,
                'net_effective_price': net_effective_price,
                'is_applicable': is_applicable,
                'note': note,
                'offer_type': offer.type,
                'rank': None,  # No rank for non-bank offers
                'card_type': offer.card_type,
                'card_provider': offer.card_provider
            })
        
        logging.info(f"Ranked {len(bank_offers)} bank offers, included {len(other_offers)} other offers without ranking")
        return all_ranked_offers

# Helper to extract price amount
def extract_price_amount(price_str):
    """Extract numeric amount from price string like '₹30,999'"""
    if not price_str:
        return 0.0
    
    # Remove currency symbols and extract numbers
    numbers = re.findall(r'[\d,]+\.?\d*', price_str)
    if numbers:
        return float(numbers[0].replace(',', ''))
    return 0.0

# Enhanced Croma offer scraping
def get_croma_offers(driver, url, max_retries=2):
    """Enhanced Croma offers scraping with comprehensive extraction"""
    for attempt in range(max_retries):
        try:
            logging.info(f"Visiting Croma URL (attempt {attempt + 1}/{max_retries}): {url}")
            driver.get(url)
            time.sleep(5)  # Give time to load

            # Try to scroll to offer section
            try:
                offer_section = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "offer-section-pdp"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", offer_section)
                logging.info("Scrolled to offer section")
                time.sleep(3)
            except TimeoutException:
                logging.warning("Could not find offer section")
                if attempt < max_retries - 1:
                    continue

            # Wait for bank offers carousel
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "bank-offers-text-pdp-carousel"))
                )
                logging.info("Bank offers carousel found")
            except TimeoutException:
                logging.warning("Bank offers carousel not found")
                if attempt < max_retries - 1:
                    continue
                return []
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Extract offers from carousel slides
            offers = []
            offer_wrappers = soup.select("div.offer-section-pdp div.swiper-slide")
            
            for wrapper in offer_wrappers:
                desc_tag = wrapper.select_one("span.bank-offers-text-pdp-carousel")
                bank_tag = wrapper.select_one("div.bank-text-name-container span.bank-name-text")

                if desc_tag:
                    description = desc_tag.get_text(strip=True)
                    bank = bank_tag.get_text(strip=True) if bank_tag else None
                    
                    if description and len(description) > 10:  # Filter out empty or too short descriptions
                        offer = {
                            "card_type": f"{bank} Offer" if bank else "Bank Offer",
                            "offer_title": f"{bank} Bank Offer" if bank else "Bank Offer",
                            "offer_description": description
                        }
                        offers.append(offer)

            # Alternative extraction if no offers found
            if not offers:
                # Look for alternative offer patterns
                offer_texts = soup.find_all(text=lambda text: text and any(keyword in text.lower() for keyword in ['bank', 'card', 'discount', 'cashback', 'emi']))
                for text in offer_texts:
                    text = text.strip()
                    if len(text) > 20 and any(keyword in text.lower() for keyword in ['bank', 'card', 'discount']):
                        offers.append({
                            "card_type": "Croma Offer",
                            "offer_title": "Bank Offer",
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
            logging.error(f"Exception in get_croma_offers (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                logging.info(f"Retrying in 3 seconds...")
                time.sleep(3)
                continue
            else:
                return []
    
    return []

def process_croma_store_links(input_file, output_file, start_idx=0, max_entries=None):
    """
    Process Croma store links in the JSON file and add ranked offers
    """
    
    # Load the JSON data
    print(f"Loading data from {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} entries")
    
    # Optional: Verify existing scraped data before processing
    if start_idx > 0:
        existing_offers_count = 0
        for i in range(min(start_idx, len(data))):
            entry = data[i]
            if 'scraped_data' in entry and isinstance(entry['scraped_data'], dict):
                scraped_data = entry['scraped_data']
                if 'variants' in scraped_data and isinstance(scraped_data['variants'], list):
                    for variant in scraped_data['variants']:
                        if isinstance(variant, dict) and 'store_links' in variant:
                            for store_link in variant['store_links']:
                                if isinstance(store_link, dict) and 'croma' in store_link.get('name', '').lower():
                                    if store_link.get('ranked_offers'):
                                        existing_offers_count += len(store_link['ranked_offers'])
        print(f"🔒 Preserving {existing_offers_count} existing Croma offers from entries 0-{start_idx-1}")
    
    # Load visited URLs to avoid re-scraping
    visited_urls_file = "sorting/visited_url_cromastore.txt"
    visited_urls = set()
    
    try:
        with open(visited_urls_file, 'r', encoding='utf-8') as f:
            visited_urls = set(line.strip() for line in f if line.strip())
        print(f"Loaded {len(visited_urls)} visited URLs from {visited_urls_file}")
    except FileNotFoundError:
        print(f"Warning: {visited_urls_file} not found. Will process all URLs.")
        visited_urls = set()
    
    # Find Croma store links
    croma_store_links = []
    for entry_idx, entry in enumerate(data):
        if 'scraped_data' in entry and isinstance(entry['scraped_data'], dict):
            scraped_data = entry['scraped_data']
            
            if 'variants' in scraped_data and isinstance(scraped_data['variants'], list):
                for variant_idx, variant in enumerate(scraped_data['variants']):
                    if isinstance(variant, dict) and 'store_links' in variant:
                        store_links = variant['store_links']
                        if isinstance(store_links, list):
                            for store_idx, store_link in enumerate(store_links):
                                if isinstance(store_link, dict):
                                    name = store_link.get('name', '').lower()
                                    if 'croma' in name:
                                        croma_store_links.append({
                                            'entry_idx': entry_idx,
                                            'variant_idx': variant_idx,
                                            'store_idx': store_idx,
                                            'entry': entry,
                                            'variant': variant,
                                            'store_link': store_link
                                        })
    
    print(f"Found {len(croma_store_links)} Croma store links")
    
    # Apply start index and max entries limit
    if start_idx > 0:
        croma_store_links = croma_store_links[start_idx:]
        print(f"Starting from index {start_idx}, processing {len(croma_store_links)} links")
    
    if max_entries:
        croma_store_links = croma_store_links[:max_entries]
        print(f"Limited to processing {len(croma_store_links)} links")
    
    # Setup Chrome driver and analyzer
    # Configure Chrome options
    import os
    headless_mode = os.getenv('HEADLESS', 'true').lower() == 'true'
    
    options = uc.ChromeOptions()
    if headless_mode:
        print("🤖 Running in headless mode (suitable for servers)")
        options.add_argument('--headless=new')  # Use new headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--window-size=1920,1080')
    else:
        print("🖥️  Running with visible browser")
        options.add_argument('--window-size=1400,1000')
    
    # Additional options for better compatibility  
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = uc.Chrome(options=options)
    analyzer = CromaOfferAnalyzer()
    
    try:
        for idx, link_data in enumerate(croma_store_links):
            entry = link_data['entry']
            store_link = link_data['store_link']
            
            print(f"\n🔍 Processing {idx + 1}/{len(croma_store_links)}: {entry.get('product_name', 'N/A')}")
            print(f"   Variant: {link_data['variant'].get('colour', 'N/A')} {link_data['variant'].get('ram', '')} {link_data['variant'].get('storage', '')}")
            
            croma_url = store_link.get('url', '')
            if not croma_url:
                print(f"   ⚠️  No URL found")
                continue
            
            print(f"   Croma URL: {croma_url}")
            
            # Check if URL has already been visited/scraped
            if croma_url in visited_urls:
                print(f"   ⏭️  URL already scraped, skipping to preserve existing offers")
                continue
            
            # Get Croma offers
            offers = get_croma_offers(driver, croma_url)
            
            if offers:
                # Get product price for ranking
                price_str = store_link.get('price', '₹0')
                product_price = extract_price_amount(price_str)
                
                # Rank the offers
                ranked_offers = analyzer.rank_offers(offers, product_price)
                
                # Update the store_link with ranked offers
                store_link['ranked_offers'] = ranked_offers
                
                print(f"   ✅ Found and ranked {len(offers)} Croma offers")
                
                # Log the ranking summary
                for i, offer in enumerate(ranked_offers[:3], 1):
                    score_display = offer['score'] if offer['score'] is not None else 'N/A'
                    print(f"      Rank {i}: {offer['title']} (Score: {score_display}, Amount: ₹{offer['amount']})")
            else:
                print(f"   ❌ No offers found")
                store_link['ranked_offers'] = []
            
            # Save progress every 10 entries
            if (idx + 1) % 10 == 0:
                backup_file = f"{output_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
        
        # Summary
        total_processed = sum(1 for link_data in croma_store_links 
                            if link_data['store_link'].get('ranked_offers'))
        total_offers = sum(len(link_data['store_link'].get('ranked_offers', [])) 
                         for link_data in croma_store_links)
        
        print(f"📊 Summary:")
        print(f"   Processed Croma links: {total_processed}")
        print(f"   Total ranked offers: {total_offers}")

if __name__ == "__main__":
    import sys
    
    input_file = "flipkartoffers.json"
    output_file = "cromaoffers.json"
    
    print("Croma Bank Offer Scraper & Ranker")
    print("This script processes Croma store links and adds ranked offers with enhanced logic")
    print("-" * 80)
    
    # Check for command line arguments for headless mode
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
    
    process_croma_store_links(input_file, output_file, start_idx, max_entries) 