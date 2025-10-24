# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Korean online bookstore web scraper that collects book cover images and metadata from major Korean bookstores (Kyobo, Yes24, Aladin). Uses Selenium for browser automation and supports multiple output formats for different sales platforms.

## Development Commands

### Environment Setup
```bash
# Install dependencies with uv
uv sync

# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix
```

### Running the Scraper
```bash
# Main execution
python main.py

# Required setup files:
# - login.yaml: Contains bookstore login credentials (id, pw)
# - isbn.txt: ISBN numbers to scrape, one per line
```

### Building Executable
```bash
# Build with PyInstaller (spec files available)
pyinstaller main.spec
```

## Architecture

### Factory Pattern Implementation
The core architecture uses a **Factory Pattern** for bookstore-specific scrapers:

```
BookScraperFactory
├── create_kyobo() → BookScraperKyobo
├── create_yes24() → BookScraperYes24
└── create_aladin() → BookScraperAladin
```

Each scraper inherits from `BookScraperBase` (Abstract Base Class) and implements site-specific HTML parsing logic.

### Data Flow
1. **book_manager** (main.py) - Orchestrates the entire scraping process
   - Loads login credentials from `login.yaml`
   - Reads ISBNs from `isbn.txt`
   - Creates authenticated Selenium driver via `chrome_controler.get_driver()`
   - For each ISBN, creates appropriate scraper via `BookScraperFactory`

2. **BookScraperFactory** (book_scraper.py) - Creates site-specific scrapers
   - Routes to correct implementation based on `site` parameter
   - Currently supports: "Kyobo", "Yes24", "Aladin"

3. **BookScraper[Site]** classes - Handle scraping for specific bookstores
   - Parse HTML using BeautifulSoup
   - Extract book metadata (title, author, price, etc.)
   - Download and process cover images
   - Save images with platform-specific formatting

4. **Image Processing Pipeline**
   - Downloads original cover image
   - Applies transformations based on platform:
     - **상세** (detailed): Resize to 860px width
     - **y1000**: Resize to 900px height, add border, center on 1000x1000 white background
     - **쿠팡**: Resize to 810px height, add border, paste Coupang icon, center on 1000x1000
     - **네이버**: Resize to 810px height, add border, paste Naver icon, center on 1000x1000

### Key Design Decisions

**Site-Specific URL Patterns:**
- Kyobo: Direct product URL with ISBN barcode
- Yes24: Search-then-navigate (search page → extract item link → product page)
- Aladin: Similar search-then-navigate pattern

**Authentication Strategy:**
- `chrome_controler.get_driver()` handles site-specific login flows
- Each site has different CSS selectors for login form elements
- Driver is created once and reused across all ISBN lookups

**Web Scraping Approach:**
- Primary: Selenium WebDriver (required for JavaScript-rendered content and login)
- Fallback: BeautifulSoup with urllib (defined but not actively used)
- Pages are parsed after Selenium loads them to ensure dynamic content is available

### Data Models

**BookInfo** (book_info.py): Dataclass holding book metadata
- Fields: isbn, title, category, description, author, publisher, price_ori, price_rel, published_date, page, book_size

**Enums** (book_info_save.py):
- `Site`: Kyobo, Yes24, Aladin
- `Mode`: y1000, coopang, naver, normal

## File Organization

### Core Files
- **main.py**: Entry point with `book_manager` class
- **book_scraper.py**: Factory and scraper implementations
- **chrome_controler.py**: Selenium WebDriver initialization with login
- **book_info.py**: BookInfo dataclass
- **book_info_save.py**: Excel export functionality (not currently used in main flow)

### Configuration
- **login.yaml**: Bookstore credentials (gitignored)
- **isbn.txt**: Target ISBN list
- **pyproject.toml**: UV project configuration

### Resources
- **resource/**: Platform-specific overlay icons (쿠팡_아이콘.png, 네이버_아이콘.png)
- **img/**: Output directory for scraped images (auto-created)

## Important Notes

### Current Site Selection
The `main.py` currently defaults to **Yes24** (line 67), but the factory supports all three sites. Modify the site parameter when creating `book_manager` to switch bookstores.

### Image Processing Dependencies
- Platform-specific icons must exist in `resource/` directory
- PIL/Pillow used for all image transformations
- LANCZOS resampling for high-quality resizing

### SSL Context
Uses `ssl._create_unverified_context()` globally for urllib operations to handle certificate verification issues with Korean bookstore sites.

### Extension Points
To add a new bookstore:
1. Create `BookScraper[NewSite]` class inheriting from `BookScraperBase`
2. Implement all abstract methods with site-specific selectors
3. Add factory method to `BookScraperFactory`
4. Add login flow to `chrome_controler.get_driver()`
5. Add `Site` enum value in `book_info_save.py`
