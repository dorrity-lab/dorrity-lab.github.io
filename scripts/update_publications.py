#!/usr/bin/env python3
"""
ORCID Publication Auto-Pull Script
===================================

This script fetches publications from ORCID and generates HTML blocks
that can be added to the publications.md file.

Usage:
    python scripts/update_publications.py --orcid YOUR-ORCID-ID
    python scripts/update_publications.py --orcid 0000-0001-2345-6789 --output new_papers.html

Requirements:
    pip install requests

Setup:
    1. Get your ORCID ID from https://orcid.org/
    2. Run this script to generate publication HTML
    3. Review the output
    4. Add thumbnails for each paper (scripts will create placeholder paths)
    5. Copy the HTML into docs/publications.md
"""

import argparse
import json
import requests
import sys
from datetime import datetime
from typing import List, Dict, Optional


class ORCIDPublicationFetcher:
    """Fetch publications from ORCID public API."""

    BASE_URL = "https://pub.orcid.org/v3.0"

    def __init__(self, orcid_id: str):
        self.orcid_id = orcid_id
        self.headers = {
            'Accept': 'application/json'
        }

    def fetch_works(self) -> List[Dict]:
        """Fetch all works from ORCID."""
        url = f"{self.BASE_URL}/{self.orcid_id}/works"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            if 'group' not in data:
                print(f"No works found for ORCID {self.orcid_id}")
                return []

            works = []
            for group in data['group']:
                if 'work-summary' in group and len(group['work-summary']) > 0:
                    # Get the first work summary (they're usually duplicates)
                    work_summary = group['work-summary'][0]
                    put_code = work_summary['put-code']

                    # Fetch full details for this work
                    work_detail = self.fetch_work_detail(put_code)
                    if work_detail:
                        works.append(work_detail)

            return works

        except requests.exceptions.RequestException as e:
            print(f"Error fetching works from ORCID: {e}")
            return []

    def fetch_work_detail(self, put_code: str) -> Optional[Dict]:
        """Fetch detailed information for a specific work."""
        url = f"{self.BASE_URL}/{self.orcid_id}/work/{put_code}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None


class PublicationFormatter:
    """Format publication data into HTML for the website."""

    @staticmethod
    def extract_publication_info(work: Dict) -> Dict:
        """Extract relevant information from ORCID work object."""
        info = {
            'title': '',
            'authors': '',
            'journal': '',
            'year': '',
            'doi': '',
            'type': ''
        }

        # Extract title
        if 'title' in work and 'title' in work['title']:
            info['title'] = work['title']['title']['value']

        # Extract year
        if 'publication-date' in work and work['publication-date']:
            pub_date = work['publication-date']
            if 'year' in pub_date and pub_date['year']:
                info['year'] = pub_date['year']['value']

        # Extract type
        if 'type' in work:
            info['type'] = work['type']

        # Extract journal
        if 'journal-title' in work and work['journal-title']:
            info['journal'] = work['journal-title']['value']

        # Extract DOI
        if 'external-ids' in work and 'external-id' in work['external-ids']:
            for ext_id in work['external-ids']['external-id']:
                if ext_id['external-id-type'] == 'doi':
                    info['doi'] = ext_id['external-id-value']
                    break

        return info

    @staticmethod
    def generate_html_block(pub_info: Dict, first_author: str = "author") -> str:
        """Generate HTML block for a publication."""
        year = pub_info['year']

        # Create filename-friendly first author
        author_slug = first_author.lower().replace(' ', '').replace('.', '')
        thumbnail_path = f"assets/images/papers/{year}_{author_slug}_thumbnail.jpg"

        # Build DOI link
        doi_link = f"https://doi.org/{pub_info['doi']}" if pub_info['doi'] else "#"

        # Format journal info
        journal_info = pub_info['journal'] if pub_info['journal'] else "Journal Name"
        if year:
            journal_info += f". {year}"

        html = f'''<div class="paper-card">
  <img src="{thumbnail_path}" alt="{pub_info['title'][:50]}" class="paper-thumbnail">
  <div class="paper-content">
    <h3 class="paper-title">{pub_info['title']}</h3>
    <p class="paper-authors"><!-- ADD AUTHORS HERE - use <strong> for lab members --></p>
    <p class="paper-journal">{journal_info}.</p>
    <div class="paper-links">
      <a href="{doi_link}" class="paper-link">Paper</a>
      <!-- Add more links as needed: Preprint, Code, Data -->
    </div>
  </div>
</div>
'''
        return html

    @staticmethod
    def sort_by_year(publications: List[Dict]) -> List[Dict]:
        """Sort publications by year (newest first)."""
        return sorted(
            publications,
            key=lambda x: int(x.get('year', '0')),
            reverse=True
        )


def main():
    parser = argparse.ArgumentParser(
        description='Fetch publications from ORCID and generate HTML for website'
    )
    parser.add_argument(
        '--orcid',
        required=True,
        help='Your ORCID ID (e.g., 0000-0001-2345-6789)'
    )
    parser.add_argument(
        '--output',
        default='new_publications.html',
        help='Output file for generated HTML (default: new_publications.html)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of publications to fetch'
    )

    args = parser.parse_args()

    print(f"Fetching publications for ORCID: {args.orcid}")
    print("=" * 60)

    # Fetch publications
    fetcher = ORCIDPublicationFetcher(args.orcid)
    works = fetcher.fetch_works()

    if not works:
        print("No publications found.")
        return

    print(f"Found {len(works)} publications")

    # Process and format publications
    formatter = PublicationFormatter()
    publications = []

    for work in works:
        pub_info = formatter.extract_publication_info(work)
        if pub_info['title']:  # Only include if we have a title
            publications.append(pub_info)

    # Sort by year
    publications = formatter.sort_by_year(publications)

    # Limit if requested
    if args.limit:
        publications = publications[:args.limit]

    # Generate HTML
    html_blocks = []
    for pub in publications:
        # Try to extract first author from title for filename
        # (You'll want to review and correct these)
        html = formatter.generate_html_block(pub, first_author="author")
        html_blocks.append(html)

    # Write output
    output_content = f"""<!-- Generated by update_publications.py on {datetime.now().strftime('%Y-%m-%d')} -->
<!-- INSTRUCTIONS:
     1. Review each publication below
     2. Add author lists (use <strong> tags for lab members)
     3. Add thumbnail images to docs/assets/images/papers/
     4. Add additional links (preprints, code, data) as needed
     5. Copy the reviewed HTML into docs/publications.md
-->

<div class="paper-grid">

{''.join(html_blocks)}

</div>
"""

    with open(args.output, 'w') as f:
        f.write(output_content)

    print(f"\nGenerated HTML written to: {args.output}")
    print(f"Processed {len(publications)} publications")
    print("\nNext steps:")
    print("1. Review the generated HTML file")
    print("2. Add author names and bold lab members with <strong> tags")
    print("3. Add thumbnail images to docs/assets/images/papers/")
    print("4. Add links to preprints, code, and data where available")
    print("5. Copy the reviewed blocks into docs/publications.md")
    print("\nThumbnail images needed:")
    for pub in publications:
        year = pub['year']
        print(f"  - docs/assets/images/papers/{year}_author_thumbnail.jpg")


if __name__ == '__main__':
    main()
