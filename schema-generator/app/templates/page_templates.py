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
# Homepage Schema
# -------------------------
def homepage_schema(data: dict):
    base_url = (data.get("site_url") or "").rstrip("/")
    website_id = f"{base_url}/#website" if base_url else None
    org_id = f"{base_url}/#organization" if base_url else None

    graph = [
        {
            "@type": "WebSite",
            "@id": website_id,
            "name": data.get("site_name"),
            "url": data.get("site_url"),
            "description": data.get("description"),
        },
        {
            "@type": data.get("org_type") or "Organization",
            "@id": org_id,
            "name": data.get("org_name"),
            "url": data.get("site_url"),
            "logo": data.get("logo"),
            "image": data.get("image"),
            "telephone": data.get("telephone"),
            "sameAs": data.get("same_as", []),
            "additionalType": data.get("additional_types", []),
            "about": [{"@type": "Thing", "sameAs": u} for u in data.get("about_entities", [])]
        }
    ]

    if data.get("search_enabled"):
        graph[0]["potentialAction"] = {
            "@type": "SearchAction",
            "target": data.get("search_url"),
            "query-input": "required name=search_term_string"
        }

    return _clean_schema({
        "@context": "https://schema.org",
        "@graph": graph
    })


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
# YOUR EXISTING LOCAL BUSINESS SCHEMA
# -------------------------
def local_business_schema(data: dict):
    schema = {
        "@context": "https://schema.org",
        "@type": data.get("business_type", "LocalBusiness"),
        "name": data.get("name"),
        "legalName": data.get("legal_name"),
        "description": data.get("description"),
        "url": data.get("url"),
        "telephone": data.get("telephone"),
        "email": data.get("email"),
        "image": data.get("image"),
        "logo": data.get("logo"),
        "priceRange": data.get("price_range"),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": data.get("street"),
            "addressLocality": data.get("city"),
            "addressRegion": data.get("state"),
            "postalCode": data.get("zip"),
            "addressCountry": data.get("country")
        }
    }

    lat = data.get("lat")
    lng = data.get("lng")
    if lat and lng:
        schema["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": lat,
            "longitude": lng
        }

    if data.get("rating_enabled"):
        schema["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": data.get("rating_value"),
            "reviewCount": data.get("review_count")
        }

    if data.get("map_enabled"):
        schema["hasMap"] = data.get("map_url")

    if data.get("sameas_enabled"):
        schema["sameAs"] = data.get("same_as", [])

    if data.get("additional_type_enabled"):
        schema["additionalType"] = data.get("additional_types", [])

    if data.get("alternate_name_enabled"):
        schema["alternateName"] = data.get("alternate_names", [])

    if data.get("knows_about_enabled"):
        schema["knowsAbout"] = data.get("knows_about", [])

    if data.get("area_served_enabled"):
        schema["areaServed"] = {
            "@type": "AdministrativeArea",
            "name": data.get("area_name"),
            "geo": {"@type": "GeoShape", "postalCode": data.get("postal_codes", [])},
            "containsPlace": [{"@type": "City", "name": c} for c in data.get("served_cities", [])]
        }

    if data.get("hours_enabled"):
        schema["openingHoursSpecification"] = [
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": h.get("dayOfWeek"),
                "opens": h.get("opens"),
                "closes": h.get("closes")
            }
            for h in data.get("opening_hours", [])
        ]

    if data.get("identifier_enabled"):
        schema["identifier"] = {
            "@type": "PropertyValue",
            "propertyID": data.get("identifier_property_id"),
            "value": data.get("identifier_value")
        }

    if data.get("founder_enabled"):
        schema["founder"] = {
            "@type": "Person",
            "name": data.get("founder_name"),
            "jobTitle": data.get("founder_job_title"),
            "sameAs": data.get("founder_same_as", [])
        }

    if data.get("language_enabled"):
        schema["knowsLanguage"] = data.get("knows_language")

    if data.get("catalog_enabled"):
        schema["hasOfferCatalog"] = {
            "@type": "OfferCatalog",
            "name": data.get("catalog_name"),
            "itemListElement": [
                {
                    "@type": "Offer",
                    "itemOffered": {
                        "@type": "Service",
                        "name": s.get("name"),
                        "description": s.get("description"),
                        "url": s.get("url")
                    }
                }
                for s in data.get("services", [])
            ]
        }

    return _clean_schema(schema)


# -------------------------
# YOUR EXISTING PRODUCT SCHEMA
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