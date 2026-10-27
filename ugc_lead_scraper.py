#!/usr/bin/env python3
"""
=============================================================================
           AI UGC DTC Brand Lead Scraper & Qualification Engine
=============================================================================
Target: E-commerce / DTC brands running ads on Meta & TikTok (Shopify stores)
Author: Elite Automation & Web Scraping Engineer
Stack: Python 3.9+, Requests, BeautifulSoup4, Playwright (Headless Browser)
Cost: 100% Free (Zero Paid APIs required)
=============================================================================
"""

import os
import re
import csv
import sys
import time
import json
import random
import argparse
import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple

# Third-party dependencies
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("[!] Missing required libraries. Please run: pip install requests beautifulsoup4 playwright")
    print("[!] For browser rendering, also run: playwright install chromium")
    sys.exit(1)

# Playwright dynamic engine (optional import / graceful fallback)
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# =============================================================================
# 1. ANTI-DETECTION HEADERS & USER-AGENT ROTATION
# =============================================================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
]

def get_random_headers() -> Dict[str, str]:
    """Generates realistic browser headers to bypass naive bot detection."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    }


# =============================================================================
# 2. DOMAIN BLACKLIST & CLEANING RULES
# =============================================================================
# Exclude marketplaces, social networks, developer platforms, and CDNs
EXCLUDED_DOMAINS = {
    "myshopify.com", "shopify.com", "apps.shopify.com", "community.shopify.com",
    "amazon.com", "amazon.co.uk", "ebay.com", "etsy.com", "walmart.com", "target.com",
    "facebook.com", "instagram.com", "tiktok.com", "twitter.com", "x.com", "youtube.com",
    "pinterest.com", "linkedin.com", "reddit.com", "quora.com", "medium.com",
    "wikipedia.org", "google.com", "bing.com", "yahoo.com", "duckduckgo.com",
    "apple.com", "play.google.com", "cloudflare.com", "github.com", "trustpilot.com",
    "aliexpress.com", "alibaba.com", "temu.com", "shein.com"
}

# Regex pattern for cleaning and extracting verified emails
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

# Junk email extensions or false positives to ignore
JUNK_EMAIL_SUBSTRINGS = [
    "sentry", "png", "jpg", "jpeg", "webp", "gif", "svg", "wixpress", "example.com",
    "domain.com", "email.com", "yourname", "test@test", "schema.org", "bootstrap",
    "jquery", "node_modules", "2x.png", "@2x", "w3.org", "noreply", "no-reply"
]


# =============================================================================
# 3. GOOGLE DORK QUERY BUILDER
# =============================================================================
def build_dork_queries(niche: str) -> List[str]:
    """
    Constructs high-converting Google Dorking queries targeting Shopify and DTC brands.
    Uses footprints that e-commerce sites inherently expose.
    """
    cleaned_niche = niche.strip().lower()
    return [
        f'site:myshopify.com "add to cart" "{cleaned_niche}"',
        f'inurl:collections/all "shipping policy" "{cleaned_niche}"',
        f'"powered by shopify" "{cleaned_niche}" "contact us"',
        f'inurl:products "add to cart" "reviews" "{cleaned_niche}" -site:amazon.com -site:ebay.com',
        f'inurl:pages/contact "{cleaned_niche}" "free shipping" -site:shopify.com',
        f'"add to cart" "track your order" "{cleaned_niche}" "tiktok"',
        f'inurl:collections "shop all" "usd" "{cleaned_niche}"'
    ]


# =============================================================================
# 4. FREE SEARCH ENGINE DISCOVERY (DuckDuckGo HTML + Fallbacks)
# =============================================================================
def discover_brand_urls(query: str, max_pages: int = 2) -> Set[str]:
    """
    Discovers target brand domains using free DuckDuckGo HTML queries.
    Does not require any paid Google Custom Search API or proxy credits.
    """
    discovered_urls = set()
    print(f"\n[*] Executing Free Dork: {query}")

    for page in range(max_pages):
        try:
            # DuckDuckGo HTML endpoint is free and rate-friendly
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query, "s": str(page * 30), "dc": str(page * 30)}
            headers = get_random_headers()
            headers["Content-Type"] = "application/x-www-form-urlencoded"

            time.sleep(random.uniform(2.0, 3.5))  # Polite delay
            response = requests.post(url, data=data, headers=headers, timeout=12)

            if response.status_code != 200:
                print(f"    [!] Search query returned status code {response.status_code}. Moving forward.")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            result_links = soup.select(".result__url, .result__snippet, .result__title a")

            found_on_page = 0
            for link in result_links:
                href = link.get("href", "")
                
                # Extract clean target destination if wrapped in DDG redirect
                if "uddg=" in href:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    if "uddg" in parsed:
                        href = parsed["uddg"][0]

                if not href.startswith("http"):
                    # Check text content for raw url
                    text = link.get_text().strip()
                    if text.startswith("http"):
                        href = text
                    elif "." in text and not " " in text:
                        href = f"https://{text}"

                # Parse domain
                parsed_url = urllib.parse.urlparse(href)
                domain = parsed_url.netloc.lower()
                domain = re.sub(r"^www\.", "", domain)

                if not domain or any(blocked in domain for blocked in EXCLUDED_DOMAINS):
                    continue

                # Reconstruct base domain
                clean_url = f"{parsed_url.scheme or 'https'}://{domain}"
                if clean_url not in discovered_urls:
                    discovered_urls.add(clean_url)
                    found_on_page += 1

            print(f"    [+] Page {page + 1}: Found {found_on_page} candidate brand domains.")
            if found_on_page == 0:
                break

        except Exception as e:
            print(f"    [!] Discovery error on page {page + 1}: {e}")
            break

    return discovered_urls


# =============================================================================
# 5. BRAND DEEP SCRAPER & DATA EXTRACTOR
# =============================================================================
class BrandScraper:
    def __init__(self, use_playwright: bool = False):
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE
        self.session = requests.Session()

    def fetch_page_html(self, url: str) -> Optional[str]:
        """Fetches page content using requests with automatic fallback."""
        try:
            headers = get_random_headers()
            response = self.session.get(url, headers=headers, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                return response.text
        except requests.exceptions.RequestException:
            pass
        return None

    def fetch_with_playwright(self, url: str) -> Optional[str]:
        """Renders JavaScript-heavy storefronts with headless Playwright."""
        if not PLAYWRIGHT_AVAILABLE:
            return None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=random.choice(USER_AGENTS))
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=12000)
                # Wait small amount for JS pixels / widgets to mount
                page.wait_for_timeout(1500)
                content = page.content()
                browser.close()
                return content
        except Exception:
            return None

    def extract_brand_name(self, soup: BeautifulSoup, base_url: str) -> str:
        """Extracts the cleanest brand name from title, OpenGraph tags, or domain."""
        # 1. Try og:site_name
        og_name = soup.find("meta", property="og:site_name")
        if og_name and og_name.get("content"):
            return og_name["content"].strip()

        # 2. Try title tag
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            # Split common delimiters: "Glow Skin | Official Store" -> "Glow Skin"
            delimiters = ["|", "–", "-", "—", ":", "•"]
            for d in delimiters:
                if d in title:
                    candidate = title.split(d)[0].strip()
                    if 2 < len(candidate) < 35:
                        return candidate
            if len(title) < 40:
                return title

        # 3. Fallback: derive from domain name (e.g., https://getsolawave.com -> Solawave)
        domain = urllib.parse.urlparse(base_url).netloc
        domain_clean = re.sub(r'^(www\.|get|shop|try|use|the)', '', domain, flags=re.IGNORECASE)
        brand_slug = domain_clean.split('.')[0]
        return brand_slug.capitalize()

    def extract_emails(self, text: str, soup: BeautifulSoup) -> List[str]:
        """Extracts and verifies clean public contact emails."""
        found_emails = set()

        # Check mailto: links
        for a_tag in soup.select('a[href^="mailto:"]'):
            href = a_tag.get("href", "")
            raw_email = href.replace("mailto:", "").split("?")[0].strip()
            if EMAIL_REGEX.match(raw_email):
                found_emails.add(raw_email.lower())

        # Regex scan raw page text
        raw_matches = EMAIL_REGEX.findall(text)
        for email in raw_matches:
            email_lower = email.lower()
            # Clean trailing dot
            if email_lower.endswith("."):
                email_lower = email_lower[:-1]

            # Validate against false-positive keywords
            if not any(junk in email_lower for junk in JUNK_EMAIL_SUBSTRINGS):
                # Ensure plausible domain extension
                if len(email_lower.split(".")[-1]) >= 2:
                    found_emails.add(email_lower)

        # Sort priority emails (support, hello, info, partnerships, founders)
        priority_prefixes = ["hello@", "support@", "info@", "contact@", "collab@", "partnerships@", "press@", "founder@"]
        sorted_emails = sorted(
            list(found_emails),
            key=lambda e: (0 if any(e.startswith(p) for p in priority_prefixes) else 1)
        )
        return sorted_emails

    def extract_socials(self, soup: BeautifulSoup, brand_name: str) -> Dict[str, Optional[str]]:
        """Finds verified social links and constructs Meta Ad Library search URL."""
        socials = {
            "instagram": None,
            "tiktok": None,
            "facebook": None,
            "meta_ad_library": None,
            "youtube": None
        }

        links = soup.find_all("a", href=True)
        for a in links:
            href = a["href"].strip()
            if not href.startswith("http"):
                continue

            href_lower = href.lower()
            if "instagram.com" in href_lower and not socials["instagram"]:
                if not any(x in href_lower for x in ["/p/", "/reel/", "/stories/", "sharer"]):
                    socials["instagram"] = href
            elif "tiktok.com/@" in href_lower and not socials["tiktok"]:
                socials["tiktok"] = href
            elif "facebook.com" in href_lower and not socials["facebook"]:
                if not any(x in href_lower for x in ["sharer", "/share", "dialog", "intent"]):
                    socials["facebook"] = href
            elif ("youtube.com/" in href_lower or "youtu.be/" in href_lower) and not socials["youtube"]:
                socials["youtube"] = href

        # Generate direct Meta Ad Library search link for cold outreach prep
        encoded_brand = urllib.parse.quote_plus(brand_name)
        socials["meta_ad_library"] = (
            f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all"
            f"&country=ALL&q={encoded_brand}&search_type=keyword_unordered"
        )

        return socials

    def qualify_for_ai_ugc(self, html_content: str) -> Tuple[int, str, str, Dict[str, bool]]:
        """
        AI UGC Qualification Engine:
        Evaluates DTC storefront tech stack for paid ad activity and UGC video ad demand.
        Returns (Opportunity Score 0-100, Tier, Pitch Angle, Feature Dict).
        """
        content_lower = html_content.lower()

        # 1. Pixel Detection (indicates paid media spending)
        has_meta_pixel = bool(
            "fbevents.js" in content_lower or
            "fbq('init'" in content_lower or
            "connect.facebook.net" in content_lower
        )
        has_tiktok_pixel = bool(
            "analytics.tiktok.com" in content_lower or
            "ttq.load" in content_lower or
            "tiktok-pixel" in content_lower
        )

        # 2. UGC Review Apps
        review_apps = []
        if "loox" in content_lower: review_apps.append("Loox")
        if "judge.me" in content_lower or "judgeme" in content_lower: review_apps.append("Judge.me")
        if "okendo" in content_lower: review_apps.append("Okendo")
        if "yotpo" in content_lower: review_apps.append("Yotpo")
        if "stamped.io" in content_lower or "stamped" in content_lower: review_apps.append("Stamped")
        if "junip" in content_lower: review_apps.append("Junip")
        has_ugc_reviews = len(review_apps) > 0

        # 3. Native Video Embeds
        has_video_embeds = bool(
            "<video" in content_lower or
            "fast.wistia.net" in content_lower or
            "player.vimeo.com" in content_lower or
            "tiktok.com/embed" in content_lower or
            "videowise" in content_lower or
            "tolstoy" in content_lower
        )

        # 4. UGC & Creator Keywords
        ugc_keywords = [
            "ugc", "creator", "ambassador", "collab", "as seen on tiktok",
            "tiktok made me buy it", "user generated", "send us your video"
        ]
        has_ugc_mentions = any(kw in content_lower for kw in ugc_keywords)

        # 5. Opportunity Score Calculation (0 to 100)
        score = 30  # Baseline for any active DTC store

        if has_meta_pixel:
            score += 25  # Active Meta ad spender!
        if has_tiktok_pixel:
            score += 20  # Active TikTok advertiser!
        if has_ugc_reviews:
            score += 15  # Already values customer proof
        if has_ugc_mentions:
            score += 10  # Actively seeking creators

        # Negative factor: if already saturated with high-end video widgets
        if has_video_embeds:
            # They already use video, but need continuous creative variations
            pitch_angle = "Fatigued creative refresh: Deliver 20+ viral AI UGC hook variations based on their top-selling product."
        elif has_meta_pixel or has_tiktok_pixel:
            score += 10  # Highest leverage: Spending money on ads WITHOUT video UGC on landing page!
            pitch_angle = "High ad spend with static assets: Pitch high-converting AI UGC video ads to lower CAC and boost ROAS on Meta/TikTok."
        elif has_ugc_reviews:
            pitch_angle = "Review-to-Video Transformation: Turn their 5-star customer reviews into realistic AI avatar UGC video ads."
        else:
            pitch_angle = "Organic TikTok Growth & Paid Ad Launcher: Zero-production-cost AI UGC video pipeline for rapid product testing."

        score = min(100, score)

        # Tier assignment
        if score >= 75:
            tier = "HOT (High Ad Spend / Prime UGC Candidate)"
        elif score >= 50:
            tier = "WARM (Active E-comm / Growing Brand)"
        else:
            tier = "STANDARD (DTC Storefront)"

        features = {
            "has_meta_pixel": has_meta_pixel,
            "has_tiktok_pixel": has_tiktok_pixel,
            "has_ugc_reviews": has_ugc_reviews,
            "review_apps": ", ".join(review_apps) if review_apps else "None",
            "has_video_embeds": has_video_embeds,
            "has_ugc_mentions": has_ugc_mentions
        }

        return score, tier, pitch_angle, features

    def scrape_brand(self, base_url: str, category: str) -> Optional[Dict]:
        """Deep scrapes a brand domain, discovering contact pages and extracting all data points."""
        print(f"\n[>] Scraping Brand: {base_url} ...")
        html = self.fetch_page_html(base_url)

        # If requests fails or returns JS-shield and Playwright is enabled, try browser
        if (not html or len(html) < 600) and self.use_playwright:
            print("    [*] Invoking Playwright headless browser for full JS render...")
            html = self.fetch_with_playwright(base_url)

        if not html:
            print("    [!] Could not fetch storefront HTML. Skipping.")
            return None

        soup = BeautifulSoup(html, "html.parser")
        brand_name = self.extract_brand_name(soup, base_url)
        emails = self.extract_emails(html, soup)
        socials = self.extract_socials(soup, brand_name)
        score, tier, pitch, features = self.qualify_for_ai_ugc(html)

        # Deep crawl: if no email found on homepage, check common contact/about subpages
        if not emails:
            candidate_paths = [
                "/pages/contact", "/contact", "/pages/contact-us", "/contact-us",
                "/pages/about", "/about", "/pages/about-us", "/pages/help"
            ]
            for path in candidate_paths:
                sub_url = urllib.parse.urljoin(base_url, path)
                sub_html = self.fetch_page_html(sub_url)
                if sub_html:
                    sub_soup = BeautifulSoup(sub_html, "html.parser")
                    discovered = self.extract_emails(sub_html, sub_soup)
                    if discovered:
                        emails.extend(discovered)
                        print(f"    [+] Discovered email on contact page: {discovered[0]}")
                        break

        primary_email = emails[0] if emails else "Not Found (Check Contact Form)"
        all_emails_str = "; ".join(emails) if emails else ""

        lead_record = {
            "Brand Name": brand_name,
            "Website URL": base_url,
            "Niche / Category": category.title(),
            "Primary Contact Email": primary_email,
            "All Emails Found": all_emails_str,
            "Instagram": socials["instagram"] or "N/A",
            "TikTok": socials["tiktok"] or "N/A",
            "Facebook": socials["facebook"] or "N/A",
            "Meta Ad Library Link": socials["meta_ad_library"],
            "UGC Opportunity Score": score,
            "Lead Qualification Tier": tier,
            "Has Video Embeds": "Yes" if features["has_video_embeds"] else "No",
            "Has TikTok Pixel": "Yes" if features["has_tiktok_pixel"] else "No",
            "Has Meta Pixel": "Yes" if features["has_meta_pixel"] else "No",
            "Review Apps Detected": features["review_apps"],
            "Suggested AI UGC Pitch Angle": pitch,
            "Scraped At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        print(f"    [OK] {brand_name} | Email: {primary_email} | Score: {score}/100 [{tier}]")
        return lead_record


# =============================================================================
# 6. CSV STORAGE & EXPORT
# =============================================================================
def export_leads_to_csv(leads: List[Dict], filename: str = "leads.csv"):
    """Saves leads into an Excel/Google Sheets compatible CSV with complete header schema."""
    if not leads:
        print("[!] No leads to export.")
        return

    fieldnames = list(leads[0].keys())
    file_exists = os.path.exists(filename)

    with open(filename, mode="a" if file_exists else "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(leads)

    print(f"\n[✓] Successfully exported {len(leads)} qualified leads to: {os.path.abspath(filename)}")


# =============================================================================
# 7. CLI RUNNER & DISCOVERY ORCHESTRATOR
# =============================================================================
def run_scraper():
    parser = argparse.ArgumentParser(
        description="Elite Python Lead Scraper & AI UGC Ad Qualification Engine for Shopify/DTC Brands."
    )
    parser.add_argument(
        "--niche", 
        type=str, 
        default="skincare", 
        help="Target niche (e.g. skincare, hair growth, mouth tape, mushroom coffee, greens powder, electrolytes, barefoot shoes, smart rings, minimalist wallet, dog allergy, ceramic cookware, shapewear, waterproof jewelry)"
    )
    parser.add_argument("--pages", type=int, default=2, help="Number of search dork pages to crawl (default: 2)")
    parser.add_argument("--limit", type=int, default=15, help="Maximum number of brands to scrape (default: 15)")
    parser.add_argument("--output", type=str, default="leads.csv", help="Output CSV filename (default: leads.csv)")
    parser.add_argument("--playwright", action="store_true", help="Enable Playwright headless browser for heavy JS sites")

    args = parser.parse_args()

    print("=" * 75)
    print("      AI UGC AD AGENCY — DTC BRAND LEAD SCRAPER ENGINE")
    print("=" * 75)
    print(f"Target Niche      : {args.niche}")
    print(f"Max Lead Limit    : {args.limit}")
    print(f"Output Destination: {args.output}")
    print(f"Playwright Engine : {'Active' if args.playwright and PLAYWRIGHT_AVAILABLE else 'Disabled (Fast HTTP Mode)'}")
    print("=" * 75)

    dorks = build_dork_queries(args.niche)
    all_discovered_urls: Set[str] = set()

    # Step 1: Execute Dork Queries to collect brand URLs
    for dork in dorks[:args.pages]:
        urls = discover_brand_urls(dork, max_pages=1)
        all_discovered_urls.update(urls)
        if len(all_discovered_urls) >= args.limit:
            break

    print(f"\n[*] Total Unique Brand Domains Discovered: {len(all_discovered_urls)}")
    target_urls = list(all_discovered_urls)[:args.limit]

    # Step 2: Scrape and Qualify Brand Leads
    scraper = BrandScraper(use_playwright=args.playwright)
    scraped_leads = []

    for idx, domain_url in enumerate(target_urls, start=1):
        print(f"\n--- [{idx}/{len(target_urls)}] Processing Store ---")
        try:
            lead = scraper.scrape_brand(domain_url, category=args.niche)
            if lead:
                scraped_leads.append(lead)
            
            # Polite delay between store requests
            delay = random.uniform(1.8, 3.2)
            time.sleep(delay)
        except Exception as err:
            print(f"[!] Error processing {domain_url}: {err}")

    # Step 3: Export to structured CSV
    export_leads_to_csv(scraped_leads, filename=args.output)
    print("\n[+] Scraping run complete! Happy client hunting for your AI UGC agency!")


if __name__ == "__main__":
    run_scraper()
