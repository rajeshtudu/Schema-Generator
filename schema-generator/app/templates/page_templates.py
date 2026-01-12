from utils.schema_helpers import to_script_tag

import re


def _clean_schema(obj):
    """
    Recursively remove keys with empty values:
    - None
    - ""
    - []
    - {}
    """
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            v_clean = _clean_schema(v)
            if v_clean in (None, "", [], {}):
                continue
            cleaned[k] = v_clean
        return cleaned
    elif isinstance(obj, list):
        cleaned_list = [_clean_schema(v) for v in obj]
        cleaned_list = [v for v in cleaned_list if v not in (None, "", [], {})]
        return cleaned_list
    else:
        return obj


def entity_recommendations(page_type: str):
    recs = {
        "Homepage": {
            "must_have": ["WebSite", "Organization OR LocalBusiness"],
            "recommended": ["SearchAction", "sameAs", "logo"],
            "optional": ["additionalType", "about/knowsAbout", "OfferCatalog"]
        },
        "Local Business": {
            "must_have": ["LocalBusiness (or subtype)", "PostalAddress", "url", "telephone"],
            "recommended": ["geo", "openingHoursSpecification", "hasMap", "sameAs"],
            "optional": ["aggregateRating", "identifier", "founder", "hasOfferCatalog"]
        },
        "Service Page": {
            "must_have": ["WebPage", "Service"],
            "recommended": ["BreadcrumbList", "FAQPage", "provider"],
            "optional": ["areaServed", "offers"]
        },
        "Collection / Category Page": {
            "must_have": ["CollectionPage", "ItemList"],
            "recommended": ["BreadcrumbList", "FAQPage"],
            "optional": ["ProductCollection", "shipping/return references"]
        },
        "Product Page": {
            "must_have": ["Product", "Offer"],
            "recommended": ["BreadcrumbList", "mainEntityOfPage", "seller", "shippingDetails", "returnPolicy"],
            "optional": ["aggregateRating", "gtin/mpn", "priceValidUntil", "itemCondition"]
        }
    }
    return recs.get(page_type, {})


# -------------------------
# Helpers
# -------------------------
def _slugify_type(t: str) -> str:
    """
    "LocalBusiness" -> "localbusiness"
    "FurnitureStore" -> "furniturestore"
    """
    t = (t or "").strip()
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def _build_has_map(has_map_in):
    """
    Accepts:
      - dict: {"@type":"Map","@id":"...","url":"..."}
      - str:  "https://maps.google..."
    Returns:
      - dict or None
    """
    if isinstance(has_map_in, dict):
        return {
            "@type": has_map_in.get("@type") or "Map",
            "@id": has_map_in.get("@id"),
            "url": has_map_in.get("url"),
        }
    if isinstance(has_map_in, str) and has_map_in.strip():
        return {"@type": "Map", "url": has_map_in.strip()}
    return None


def _build_aggregate_rating(rating_in: dict):
    """
    rating_in example:
      {
        "name": "...",
        "rating_value": "4.8",
        "best_rating": "5",
        "review_count": "123",
        "additional_property": [{"name":"...","value":"..."}]
      }
    """
    rating_in = rating_in or {}
    if not rating_in:
        return None

    additional_props = []
    for p in rating_in.get("additional_property", []) or []:
        additional_props.append({
            "@type": "PropertyValue",
            "name": p.get("name"),
            "value": p.get("value"),
        })

    return {
        "@type": "AggregateRating",
        "name": rating_in.get("name"),
        "ratingValue": rating_in.get("rating_value"),
        "bestRating": rating_in.get("best_rating"),
        "reviewCount": rating_in.get("review_count"),
        "additionalProperty": additional_props,
    }


def _build_founders(founders_in, works_for_id: str | None):
    """
    founders_in: list of {name, job_title, same_as}
    """
    founders = []
    for f in (founders_in or []):
        person = {
            "@type": "Person",
            "name": f.get("name"),
            "jobTitle": f.get("job_title"),
            "sameAs": f.get("same_as", []),
        }
        if works_for_id:
            person["worksFor"] = {"@id": works_for_id}
        founders.append(person)
    return founders


# ✅ NEW: build nested about = Thing + sameAs[] + hasPart[]
def _build_about_nested(about_in):
    """
    Accepts:
      about: [
        {
          "name": "Furniture",
          "same_as": ["wiki", "wikidata"],
          "has_part": [
            {"name":"Bed","same_as":["wiki","wikidata"]},
            ...
          ]
        }
      ]

    Returns schema-ready:
      about: [
        {
          "@type":"Thing",
          "name":"Furniture",
          "sameAs":[...],
          "hasPart":[{"@type":"Thing","name":"Bed","sameAs":[...]}]
        }
      ]
    """
    about_in = about_in or []
    about_list = []

    for t in about_in:
        parent = {
            "@type": t.get("@type") or t.get("type") or "Thing",
            "name": t.get("name"),
            "sameAs": t.get("same_as") if t.get("same_as") is not None else t.get("sameAs", []),
        }

        parts = []
        for p in (t.get("has_part") or t.get("hasPart") or []):
            parts.append({
                "@type": p.get("@type") or p.get("type") or "Thing",
                "name": p.get("name"),
                "sameAs": p.get("same_as") if p.get("same_as") is not None else p.get("sameAs", []),
            })

        if parts:
            parent["hasPart"] = parts

        about_list.append(parent)

    return about_list


def _build_main_entity_of_page_webpage(meop_in: dict, fallback_url: str | None):
    """
    Builds a WebPage object for mainEntityOfPage when you pass:
      main_entity_of_page = {name,url,@id,additionalType/about/mentions}

    Supports nested about structure (Thing + sameAs[] + hasPart[]).
    """
    meop_in = meop_in or {}
    if not meop_in:
        return None

    # ✅ UPDATED: use nested about builder
    about_list = _build_about_nested(meop_in.get("about"))

    mentions_list = []
    for m in (meop_in.get("mentions", []) or []):
        mentions_list.append({
            "@type": m.get("type") or m.get("@type") or "Thing",
            "name": m.get("name"),
            "sameAs": m.get("same_as") if m.get("same_as") is not None else m.get("sameAs"),
        })

    return {
        "@type": "WebPage",
        "name": meop_in.get("name"),
        "url": meop_in.get("url") or fallback_url,
        "@id": meop_in.get("@id") or meop_in.get("id") or fallback_url,
        "additionalType": (
            meop_in.get("additional_type")
            if meop_in.get("additional_type") is not None
            else meop_in.get("additionalType", [])
        ),
        "about": about_list,
        "mentions": mentions_list,
    }


def _build_website_schema(website_in: dict, base_url: str | None, fallback_name: str | None, fallback_url: str | None):
    """
    Optional separate WebSite block. Supply data["website_schema"] if you want it.
    Example:
      website_schema={
        "name": "...",
        "url": "https://...",
        "sameAs": [...],
        "potentialAction": {...}   # SearchAction optional
      }
    """
    website_in = website_in or {}
    if not website_in:
        return None

    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": website_in.get("@id") or (f"{base_url}/#website" if base_url else None),
        "name": website_in.get("name") or fallback_name,
        "url": website_in.get("url") or fallback_url,
        "sameAs": website_in.get("sameAs"),
        "potentialAction": website_in.get("potentialAction"),
    }


def _build_identifier(data: dict):
    """
    Supports BOTH styles:
      A) propertyID + single value:
         identifier_property_id, identifier_value
      B) value: list
         identifier_values
    """
    if data.get("identifier_property_id") or data.get("identifier_value"):
        return {
            "@type": "PropertyValue",
            "propertyID": data.get("identifier_property_id"),
            "value": data.get("identifier_value"),
        }

    if data.get("identifier_values"):
        return {
            "@type": "PropertyValue",
            "value": data.get("identifier_values", []),
        }

    return None


def _build_makes_offer(makes_offer_in):
    """
    makes_offer_in: list of {name, description, url}
    """
    makes_offer = []
    for o in (makes_offer_in or []):
        makes_offer.append({
            "@type": "Offer",
            "name": o.get("name"),
            "description": o.get("description"),
            "url": o.get("url"),
        })
    return makes_offer


def _build_has_offer_catalog(data: dict):
    """
    Universal hasOfferCatalog builder.

    Inputs supported:
      - offer_catalog_services: [{name, description, url}, ...]
      - services: same as above (fallback)
      - offer_catalog_mode:
          * "service_list" (default): itemListElement is list of Service (Cloudavize style)
          * "offer_wrapped": itemListElement is Offer->itemOffered->Service (your local_business_schema style)
      - offer_catalog_name / catalog_name: optional
    """
    catalog_services = data.get("offer_catalog_services") or data.get("services") or []
    if not catalog_services:
        return None

    catalog_mode = (data.get("offer_catalog_mode") or "service_list").strip().lower()
    catalog_name = data.get("offer_catalog_name") or data.get("catalog_name")

    if catalog_mode == "offer_wrapped":
        item_list = [
            {
                "@type": "Offer",
                "itemOffered": {
                    "@type": "Service",
                    "name": s.get("name"),
                    "description": s.get("description"),
                    "url": s.get("url"),
                }
            }
            for s in catalog_services
        ]
    else:
        item_list = [
            {
                "@type": "Service",
                "name": s.get("name"),
                "description": s.get("description"),
                "url": s.get("url"),
            }
            for s in catalog_services
        ]

    return {
        "@type": "OfferCatalog",
        "name": catalog_name,
        "itemListElement": item_list
    }


def _build_faq_schema(faqs):
    """
    faqs: list of {question, answer}
    Returns FAQPage dict or None
    """
    faqs = faqs or []
    if not faqs:
        return None

    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f.get("question"),
                "acceptedAnswer": {"@type": "Answer", "text": f.get("answer")},
            }
            for f in faqs
        ],
    }


# -------------------------
# UNIVERSAL HOMEPAGE SCHEMA
# -------------------------
def homepage_schema(data):
    """
    Universal Homepage schema generator.
    Uses business_type as the single source of truth.
    """

    business_type = data.get("business_type", "Organization")

    LOCAL_BUSINESS_TYPES = {
        "LocalBusiness",
        "ProfessionalService",
        "Store",
        "BeautySalon",
        "HairSalon",
        "NailSalon",
        "DaySpa",
        "HealthAndBeautyBusiness",
        "Dentist",
        "MedicalBusiness",
        "Restaurant",
        "Hotel",
        "RealEstateAgent",
        "HVACBusiness",
        "Plumber",
        "Physiotherapy",
    }

    homepage_entity_type = (
        "LocalBusiness"
        if business_type in LOCAL_BUSINESS_TYPES
        else "Organization"
    )

    site_url = data.get("site_url")
    name = data.get("name")

    if not site_url or not name:
        raise ValueError("homepage_schema: site_url and name are required.")

    entity = {
        "@context": "https://schema.org",
        "@type": business_type,
        "@id": site_url.rstrip("/") + "#entity",
        "url": site_url,
        "name": name,
    }

    # Basic optional properties
    org_name = data.get("org_name")
    if org_name:
        entity["legalName"] = org_name

    for field, key in [
        ("description", "description"),
        ("logo", "logo"),
        ("image", "image"),
        ("telephone", "telephone"),
        ("email", "email"),
        ("price_range", "priceRange"),
    ]:
        value = data.get(field)
        if value:
            entity[key] = value

    # sameAs / alternateName / language
    if data.get("same_as"):
        entity["sameAs"] = data["same_as"]

    if data.get("alternate_names"):
        entity["alternateName"] = data["alternate_names"]

    if data.get("knows_language"):
        entity["knowsLanguage"] = data["knows_language"]

    if data.get("additional_types"):
        entity["additionalType"] = data["additional_types"]

    if data.get("knows_about"):
        entity["knowsAbout"] = data["knows_about"]

    # Address + Geo (for LocalBusiness)
    if homepage_entity_type == "LocalBusiness" and data.get("street"):
        address = {
            "@type": "PostalAddress",
            "streetAddress": data.get("street"),
            "addressLocality": data.get("city"),
            "addressRegion": data.get("state"),
            "postalCode": data.get("zip"),
            "addressCountry": data.get("country"),
        }
        entity["address"] = {k: v for k, v in address.items() if v}

        if data.get("lat") and data.get("lng"):
            entity["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": data.get("lat"),
                "longitude": data.get("lng"),
            }

    # Opening hours
    if data.get("opening_hours_spec"):
        entity["openingHoursSpecification"] = data["opening_hours_spec"]

    # Area served
    if data.get("area_served"):
        entity["areaServed"] = data["area_served"]

    # Identifier
    if data.get("identifier_property_id") and data.get("identifier_value"):
        entity["identifier"] = {
            "@type": "PropertyValue",
            "propertyID": data["identifier_property_id"],
            "value": data["identifier_value"],
        }
    elif data.get("identifier_values"):
        entity["identifier"] = data["identifier_values"]

    # hasMap
    if data.get("has_map"):
        entity["hasMap"] = data["has_map"]

    # makesOffer
    if data.get("makes_offer"):
        entity["makesOffer"] = [
            {
                "@type": "Offer",
                "name": o["name"],
                "description": o["description"],
                "url": o["url"],
            }
            for o in data["makes_offer"]
        ]

    # hasOfferCatalog
    if data.get("offer_catalog_services"):
        catalog = {
            "@type": "OfferCatalog",
            "name": data.get("offer_catalog_name") or "Services",
            "itemListElement": [],
        }

        if data.get("offer_catalog_mode") == "offer_wrapped":
            for s in data["offer_catalog_services"]:
                catalog["itemListElement"].append(
                    {
                        "@type": "Offer",
                        "itemOffered": {
                            "@type": "Service",
                            "name": s["name"],
                            "description": s["description"],
                            "url": s["url"],
                        },
                    }
                )
        else:
            for s in data["offer_catalog_services"]:
                catalog["itemListElement"].append(
                    {
                        "@type": "Service",
                            "name": s["name"],
                            "description": s["description"],
                            "url": s["url"],
                    }
                )

        entity["hasOfferCatalog"] = catalog

    # mainEntityOfPage
    if data.get("main_entity_of_page"):
        entity["mainEntityOfPage"] = {
            "@type": "WebPage",
            **data["main_entity_of_page"],
        }
    elif data.get("main_entity_of_page_url"):
        entity["mainEntityOfPage"] = data["main_entity_of_page_url"]

    blocks = [entity]

    # WebSite block
    website_schema = data.get("website_schema")
    if website_schema and website_schema.get("url"):
        website = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "@id": website_schema["url"].rstrip("/") + "#website",
            "url": website_schema["url"],
            "name": website_schema.get("name"),
        }

        if website_schema.get("sameAs"):
            website["sameAs"] = website_schema["sameAs"]

        if website_schema.get("potentialAction"):
            website["potentialAction"] = website_schema["potentialAction"]

        blocks.append(website)

    # FAQPage
    if data.get("faqs"):
        faq_block = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": f["answer"],
                    },
                }
                for f in data["faqs"]
            ],
        }
        blocks.append(faq_block)

    return blocks if len(blocks) > 1 else entity


# -------------------------
# Service Page Schema
# -------------------------
def service_page_schema(data: dict):
    url = (data.get("url") or "").rstrip("/")
    page_id = f"{url}/#webpage" if url else None
    service_id = f"{url}/#service" if url else None

    graph = [
        {
            "@type": "WebPage",
            "@id": page_id,
            "url": data.get("url"),
            "name": data.get("service_name"),
            "description": data.get("service_description"),
            "isPartOf": {
                "@type": "WebSite",
                "name": data.get("site_name"),
                "url": data.get("site_url")
            },
            "about": {"@id": service_id}
        },
        {
            "@type": "Service",
            "@id": service_id,
            "name": data.get("service_name"),
            "description": data.get("service_description"),
            "url": data.get("url"),
            "provider": {
                "@type": data.get("provider_type") or "LocalBusiness",
                "name": data.get("provider_name"),
                "url": data.get("provider_url")
            },
            "areaServed": data.get("area_served")
        }
    ]

    if data.get("breadcrumb_enabled"):
        graph.append({
            "@type": "BreadcrumbList",
            "@id": f"{url}/#breadcrumb" if url else None,
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": b["name"],
                    "item": b["url"]
                }
                for i, b in enumerate(data.get("breadcrumbs", []))
            ]
        })

    if data.get("faq_enabled"):
        graph.append({
            "@type": "FAQPage",
            "@id": f"{url}/#faq" if url else None,
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f["question"],
                    "acceptedAnswer": {"@type": "Answer", "text": f["answer"]}
                }
                for f in data.get("faqs", [])
            ]
        })

    return _clean_schema({
        "@context": "https://schema.org",
        "@graph": graph
    })


# -------------------------
# Collection / Category Schema
# -------------------------
def collection_schema(data: dict):
    url = (data.get("url") or "").rstrip("/")
    page_id = f"{url}/#collectionpage" if url else None
    itemlist_id = f"{url}/#itemlist" if url else None

    products = data.get("products", [])
    item_list = {
        "@type": "ItemList",
        "@id": itemlist_id,
        "itemListElement": []
    }

    for i, p in enumerate(products):
        product_obj = {
            "@type": "Product",
            "name": p.get("name"),
            "url": p.get("url"),
            "image": p.get("image"),
        }
        if p.get("price"):
            product_obj["offers"] = {
                "@type": "Offer",
                "url": p.get("url"),
                "price": p.get("price"),
                "priceCurrency": p.get("currency") or data.get("default_currency") or "USD",
                "availability": p.get("availability") or "https://schema.org/InStock"
            }

        item_list["itemListElement"].append({
            "@type": "ListItem",
            "position": i + 1,
            "url": p.get("url"),
            "item": product_obj
        })

    graph = [
        {
            "@type": "CollectionPage",
            "@id": page_id,
            "url": data.get("url"),
            "name": data.get("name"),
            "description": data.get("description"),
            "mainEntity": {"@id": itemlist_id}
        },
        item_list
    ]

    if data.get("breadcrumb_enabled"):
        graph.append({
            "@type": "BreadcrumbList",
            "@id": f"{url}/#breadcrumb" if url else None,
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": b["name"],
                    "item": b["url"]
                }
                for i, b in enumerate(data.get("breadcrumbs", []))
            ]
        })

    if data.get("faq_enabled"):
        graph.append({
            "@type": "FAQPage",
            "@id": f"{url}/#faq" if url else None,
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f["question"],
                    "acceptedAnswer": {"@type": "Answer", "text": f["answer"]}
                }
                for f in data.get("faqs", [])
            ]
        })

    return _clean_schema({
        "@context": "https://schema.org",
        "@graph": graph
    })


# -------------------------
# Local Business Schema
# -------------------------
def local_business_schema(data: dict):
    """
    Local Business page schema (single-location page).
    Reuses universal homepage_schema() internally, but returns ONLY the business entity (dict),
    not the extra WebSite/FAQ blocks.
    Keeps your existing Streamlit Local Business form keys/toggles unchanged.
    """

    business_type = (data.get("business_type") or "LocalBusiness").strip()
    site_url = (data.get("url") or "").strip()
    if not site_url:
        raise ValueError("local_business_schema: 'url' is required.")

    adapted = {
        "business_type": business_type,
        "site_url": site_url,
        "name": data.get("name"),

        "legal_name": data.get("legal_name"),
        "description": data.get("description"),
        "telephone": data.get("telephone"),
        "email": data.get("email"),
        "image": data.get("image"),
        "logo": data.get("logo"),
        "price_range": data.get("price_range"),

        "street": data.get("street"),
        "city": data.get("city"),
        "state": data.get("state"),
        "zip": data.get("zip"),
        "country": data.get("country"),
        "lat": data.get("lat"),
        "lng": data.get("lng"),
    }

    if data.get("rating_enabled"):
        adapted["aggregate_rating"] = {
            "rating_value": data.get("rating_value"),
            "review_count": data.get("review_count"),
        }

    if data.get("map_enabled"):
        adapted["has_map"] = data.get("map_url")

    if data.get("sameas_enabled"):
        adapted["same_as"] = data.get("same_as", [])

    if data.get("additional_type_enabled"):
        adapted["additional_types"] = data.get("additional_types", [])

    if data.get("alternate_name_enabled"):
        adapted["alternate_names"] = data.get("alternate_names", [])

    if data.get("knows_about_enabled"):
        adapted["knows_about"] = data.get("knows_about", [])

    if data.get("area_served_enabled"):
        adapted["area_served"] = {
            "@type": "AdministrativeArea",
            "name": data.get("area_name"),
            "geo": {"@type": "GeoShape", "postalCode": data.get("postal_codes", [])},
            "containsPlace": [{"@type": "City", "name": c} for c in data.get("served_cities", [])],
        }

    if data.get("hours_enabled"):
        adapted["opening_hours_spec"] = [
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": h.get("dayOfWeek"),
                "opens": h.get("opens"),
                "closes": h.get("closes"),
            }
            for h in data.get("opening_hours", [])
        ]

    if data.get("identifier_enabled"):
        adapted["identifier_property_id"] = data.get("identifier_property_id")
        adapted["identifier_value"] = data.get("identifier_value")

    if data.get("founder_enabled"):
        adapted["founders"] = [{
            "name": data.get("founder_name"),
            "job_title": data.get("founder_job_title"),
            "same_as": data.get("founder_same_as", []),
        }]

    if data.get("language_enabled"):
        adapted["knows_language"] = data.get("knows_language")

    if data.get("catalog_enabled"):
        adapted["offer_catalog_mode"] = "offer_wrapped"
        adapted["offer_catalog_name"] = data.get("catalog_name")
        adapted["offer_catalog_services"] = data.get("services", [])

    adapted["website_schema"] = {}
    adapted["faqs"] = []

    blocks = homepage_schema(adapted)
    return blocks[0]


# -------------------------
# Product Schema
# -------------------------
def product_schema(data: dict):
    schema = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": data.get("product_name"),
        "description": data.get("product_description"),
        "sku": data.get("sku"),
        "brand": {"@type": "Brand", "name": data.get("brand")},
        "image": data.get("product_images", []),
        "offers": {
            "@type": "Offer",
            "url": data.get("url"),
            "priceCurrency": data.get("currency"),
            "price": data.get("price"),
            "availability": data.get("availability")
        }
    }

    if data.get("main_entity_enabled"):
        schema["mainEntityOfPage"] = {
            "@type": "WebPage",
            "name": data.get("page_name") or data.get("product_name"),
            "url": data.get("url"),
            "description": data.get("page_description") or data.get("product_description"),
            "isPartOf": {
                "@type": "WebSite",
                "url": data.get("site_url"),
                "name": data.get("site_name")
            }
        }

    if data.get("gtin"):
        schema["gtin"] = data.get("gtin")
    if data.get("mpn"):
        schema["mpn"] = data.get("mpn")

    if data.get("product_rating_enabled"):
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": data.get("product_rating_value"),
            "reviewCount": data.get("product_review_count"),
            "bestRating": data.get("product_best_rating") or "5"
        }

    offer = schema["offers"]

    if data.get("item_condition"):
        offer["itemCondition"] = data.get("item_condition")

    if data.get("price_valid_until"):
        offer["priceValidUntil"] = data.get("price_valid_until")

    if data.get("seller_enabled"):
        offer["seller"] = {
            "@type": "Organization",
            "name": data.get("seller_name"),
            "url": data.get("seller_url")
        }

    if data.get("shipping_enabled"):
        offer["shippingDetails"] = {
            "@type": "OfferShippingDetails",
            "shippingDestination": {
                "@type": "DefinedRegion",
                "addressCountry": data.get("shipping_country")
            },
            "deliveryTime": {
                "@type": "ShippingDeliveryTime",
                "handlingTime": {
                    "@type": "QuantitativeValue",
                    "minValue": data.get("handling_min_days"),
                    "maxValue": data.get("handling_max_days"),
                    "unitCode": "d"
                },
                "transitTime": {
                    "@type": "QuantitativeValue",
                    "minValue": data.get("transit_min_days"),
                    "maxValue": data.get("transit_max_days"),
                    "unitCode": "d"
                }
            }
        }

    if data.get("return_policy_enabled"):
        offer["hasMerchantReturnPolicy"] = {
            "@type": "MerchantReturnPolicy",
            "returnPolicyCategory": data.get("return_policy_category"),
            "merchantReturnDays": data.get("return_days"),
            "returnMethod": data.get("return_method"),
            "returnFees": data.get("return_fees")
        }

    if data.get("breadcrumb_enabled"):
        schema["breadcrumb"] = {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": b["name"], "item": b["url"]}
                for i, b in enumerate(data.get("breadcrumbs", []))
            ]
        }

    return _clean_schema(schema)

def render_schema_blocks(schema) -> str:
    """
    Accepts:
      - dict (single schema)
      - list[dict] (multiple schemas)
    Returns JSON-LD <script> tags.
    """
    if not schema:
        return ""

    if isinstance(schema, dict):
        return to_script_tag(schema)

    if isinstance(schema, list):
        return "\n\n".join(to_script_tag(block) for block in schema)

    raise TypeError("render_schema_blocks expects dict or list of dicts")