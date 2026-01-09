# 🧩 Schema Generator (Streamlit)

This is a Streamlit-based Schema.org structured data generator that helps you build clean **JSON-LD schema markup** for common website page types including **Homepage, Local Business, Service Pages, Collection/Category Pages, and Product Pages**. It supports optional enhancement blocks (FAQ, Breadcrumbs, Shipping, Return Policy, Ratings, etc.) and outputs schema in **JSON-LD** or **script tag** format.

---

## Features

- Generate Schema.org JSON-LD for multiple page types:
  - **Homepage** (WebSite + Organization / LocalBusiness + SearchAction)
  - **Local Business** (LocalBusiness + business details)
  - **Service Page** (WebPage + Service + optional FAQ + BreadcrumbList)
  - **Collection / Category Page** (CollectionPage + ItemList + optional FAQ + BreadcrumbList)
  - **Product Page** (Product + Offer + optional shipping, return policy, seller, ratings)

- Optional schema blocks via toggles:
  - Aggregate Rating
  - Opening Hours Specification
  - Identifier (kgmid / mapsCid)
  - Founder (Person)
  - sameAs links
  - additionalType (ProductOntology)
  - knowsAbout / about links (Wikipedia/Wikidata)
  - areaServed (postal codes + cities)
  - Offer Catalog (service list)
  - BreadcrumbList
  - FAQPage
  - Product identifiers (GTIN / MPN)
  - Offer enhancements (itemCondition, priceValidUntil, shippingDetails, return policy)

- Built-in guidance for beginners:
  - Shows **Must-have**, **Recommended**, and **Optional** entities per page type.

- Output modes:
  - JSON-LD (raw)
  - Script Tag (`<script type="application/ld+json">...</script>`)

- Export schema output:
  - Download generated schema as `schema.json`

---

## Setup Instructions

1. Clone the repo:

   ```bash
   git clone https://github.com/rajeshtudu/schema-generator.git
   cd schema-generator  