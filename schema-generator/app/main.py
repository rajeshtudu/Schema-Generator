import streamlit as st
import json

from templates.page_templates import (
    local_business_schema,
    product_schema,
    homepage_schema,
    service_page_schema,
    collection_schema,
    entity_recommendations
)

from utils.schema_helpers import clean_list, to_script_tag

st.set_page_config(page_title="Schema Generator", layout="wide")
st.sidebar.title("Schema Generator")


# ✅ NEW: parse nested about input (Parent | url1, url2 then "- Child | url1, url2")
def parse_about_nested(lines):
    """
    Input format:
      ParentName | url1, url2
        - ChildName | url1, url2

    Output:
      [
        {
          "name": "ParentName",
          "same_as": ["url1","url2"],
          "has_part": [
            {"name":"ChildName","same_as":["url1","url2"]}
          ]
        }
      ]
    """
    result = []
    current_parent = None

    for raw in lines or []:
        line = (raw or "").strip()
        if not line:
            continue

        is_child = line.startswith("-") or line.startswith("•") or line.startswith("—") or line.startswith("–")
        if is_child:
            if not current_parent:
                continue
            line = line.lstrip("-•—–").strip()

        if "|" in line:
            name, urls = line.split("|", 1)
            name = name.strip()
            urls_list = [u.strip() for u in urls.split(",") if u.strip()]
        else:
            name = line.strip()
            urls_list = []

        if not is_child:
            current_parent = {"name": name, "same_as": urls_list, "has_part": []}
            result.append(current_parent)
        else:
            current_parent["has_part"].append({"name": name, "same_as": urls_list})

    # remove empty has_part
    for p in result:
        if not p.get("has_part"):
            p.pop("has_part", None)

    return result


page_type = st.sidebar.selectbox(
    "Select Page Type",
    [
        "Homepage",
        "Local Business",
        "Service Page",
        "Collection / Category Page",
        "Product Page"
    ]
)

output_mode = st.sidebar.radio("Output Mode", ["JSON-LD", "Script Tag"])
st.title("Schema Generator (Streamlit)")

# -----------------------------------
# Recommendation Panel (Dynamic)
# -----------------------------------
recs = entity_recommendations(page_type)
if recs:
    with st.expander("✅ Recommended Entities for This Page Type", expanded=True):
        st.markdown("### ✅ Must-have")
        st.write(", ".join(recs.get("must_have", [])))
        st.markdown("### ⭐ Strongly Recommended")
        st.write(", ".join(recs.get("recommended", [])))
        st.markdown("### ➕ Optional")
        st.write(", ".join(recs.get("optional", [])))

schema = {}

# -----------------------------------
# HOMEPAGE (UNIVERSAL)
# -----------------------------------
if page_type == "Homepage":
    st.subheader("Homepage Schema (Universal: works for ANY business type)")

    homepage_entity_type = st.radio(
        "Homepage Entity Type (required)",
        ["Organization", "LocalBusiness"],
        help="Choose LocalBusiness ONLY if customers visit a physical location."
        )

    col1, col2 = st.columns(2)

    with col1:
        site_url = st.text_input("Website URL (required)")
        name = st.text_input("Business / Brand Name (required)")
        org_name = st.text_input("Legal / Organization Name (optional)", value="")
        description = st.text_area("Description (optional)")
        logo = st.text_input("Logo URL (optional)")
        image = st.text_input("Image URL (optional)")
        telephone = st.text_input("Telephone (optional)")
        email = st.text_input("Email (optional)")
        price_range = st.text_input("Price Range (optional)", value="")

        common_types = [
            "LocalBusiness",
            "Organization",
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
        ]
        bt_pick = st.selectbox("Schema.org @type (required)", common_types, index=0)
        bt_custom_enabled = st.checkbox("Use a custom @type", value=False)
        business_type = st.text_input("Custom @type", value=bt_pick) if bt_custom_enabled else bt_pick

        same_as_enabled = st.checkbox("Add sameAs (recommended)", value=True)
        same_as = clean_list(st.text_area("sameAs Links (one per line)")) if same_as_enabled else []

        alternate_name_enabled = st.checkbox("Add alternateName (optional)")
        alternate_names = clean_list(st.text_area("alternateName (one per line)")) if alternate_name_enabled else []

        language_enabled = st.checkbox("Add knowsLanguage (optional)")
        knows_language = st.text_input("knowsLanguage (e.g. en-US)", value="en-US") if language_enabled else ""

        # ✅ Optional: additionalType + knowsAbout at BUSINESS level
        additional_type_enabled = st.checkbox("Add additionalType (optional)")
        additional_types = clean_list(st.text_area("additionalType URLs (one per line)")) if additional_type_enabled else []

        knows_about_enabled = st.checkbox("Add knowsAbout (optional)")
        knows_about = clean_list(st.text_area("knowsAbout URLs (one per line)")) if knows_about_enabled else []

    with col2:
        st.markdown("### Location (optional)")
        location_enabled = st.checkbox("Add Address + Geo (recommended for local businesses)", value=False)

        street = city = state = zip_code = country = lat = lng = ""
        if location_enabled:
            street = st.text_input("Street Address")
            city = st.text_input("City")
            state = st.text_input("State / Region")
            zip_code = st.text_input("Zip / Postal Code")
            country = st.text_input("Country", value="US")
            lat = st.text_input("Latitude")
            lng = st.text_input("Longitude")

        map_enabled = st.checkbox("Add hasMap (optional)")
        has_map = None
        if map_enabled:
            map_url = st.text_input("Map URL (Google Maps link)")
            has_map = map_url

        hours_enabled = st.checkbox("Add openingHoursSpecification (optional)")
        opening_hours_spec = []
        if hours_enabled:
            st.caption("Add rows like: dayOfWeek | opens | closes (one per line)")
            lines = clean_list(st.text_area("Opening Hours"))
            for line in lines:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) == 3:
                    day, opens, closes = parts
                    opening_hours_spec.append({
                        "@type": "OpeningHoursSpecification",
                        "dayOfWeek": day,
                        "opens": opens,
                        "closes": closes
                    })

        area_served_enabled = st.checkbox("Add areaServed (optional)")
        area_served = []
        if area_served_enabled:
            st.caption("Tip: paste JSON list/dict for areaServed (schema-ready).")
            area_served_raw = st.text_area("areaServed JSON (list or dict)")
            try:
                if area_served_raw.strip():
                    area_served = json.loads(area_served_raw)
            except Exception:
                st.warning("areaServed JSON is invalid. Leave empty or fix JSON.")

        identifier_enabled = st.checkbox("Add identifier (optional)")
        identifier_property_id = identifier_value = ""
        identifier_values = []
        if identifier_enabled:
            mode = st.radio("Identifier mode", ["propertyID + value", "value list"], horizontal=True)
            if mode == "propertyID + value":
                identifier_property_id = st.text_input("identifier propertyID (e.g. kgmid, mapsCid)")
                identifier_value = st.text_input("identifier value (URL or ID)")
            else:
                identifier_values = clean_list(st.text_area("identifier values (one per line)"))

        st.markdown("### Offers / Services (optional)")

        makes_offer_enabled = st.checkbox("Add makesOffer (retail categories / offers)", value=False)
        makes_offer = []
        if makes_offer_enabled:
            st.caption("Add offers like: name | description | url (one per line)")
            offer_lines = clean_list(st.text_area("makesOffer"))
            for line in offer_lines:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) == 3:
                    makes_offer.append({"name": parts[0], "description": parts[1], "url": parts[2]})

        catalog_enabled = st.checkbox("Add hasOfferCatalog (services catalog)", value=False)
        offer_catalog_services = []
        offer_catalog_mode = "service_list"
        offer_catalog_name = ""
        if catalog_enabled:
            offer_catalog_name = st.text_input("OfferCatalog Name (optional)", value="Services")
            offer_catalog_mode = st.selectbox(
                "OfferCatalog shape",
                ["service_list", "offer_wrapped"],
                help="service_list = itemListElement is [Service]. "
                     "offer_wrapped = itemListElement is [Offer -> itemOffered -> Service]."
            )
            st.caption("Add services like: name | description | url (one per line)")
            svc_lines = clean_list(st.text_area("Services"))
            for line in svc_lines:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) == 3:
                    offer_catalog_services.append({
                        "name": parts[0],
                        "description": parts[1],
                        "url": parts[2]
                    })

        faq_enabled = st.checkbox("Add FAQPage (recommended if you have FAQs)", value=False)
        faqs = []
        if faq_enabled:
            st.caption("Add FAQ like: Question | Answer (one per line)")
            faq_lines = clean_list(st.text_area("FAQs"))
            for line in faq_lines:
                if "|" in line:
                    q, a = line.split("|", 1)
                    faqs.append({"question": q.strip(), "answer": a.strip()})

        website_block_enabled = st.checkbox("Add a separate WebSite block (recommended)", value=True)
        website_schema = {}
        if website_block_enabled:
            site_name = st.text_input("WebSite Name (optional)", value=name)
            search_enabled = st.checkbox("Add SearchAction to WebSite (recommended)", value=True)
            potential_action = None
            if search_enabled and site_url.strip():
                search_target = st.text_input(
                    "Search URL template (use {search_term_string})",
                    value=f"{site_url.rstrip('/')}/search?q={{search_term_string}}"
                )
                potential_action = {
                    "@type": "SearchAction",
                    "target": search_target,
                    "query-input": "required name=search_term_string"
                }

            website_schema = {
                "name": site_name,
                "url": site_url,
                "sameAs": same_as if same_as_enabled else [],
                "potentialAction": potential_action
            }

        st.markdown("### mainEntityOfPage (optional)")
        meop_mode = st.radio("mainEntityOfPage mode", ["None", "WebPage object", "String URL"], horizontal=True)

        main_entity_of_page = {}
        main_entity_of_page_url = ""
        if meop_mode == "WebPage object":
            meop_name = st.text_input("WebPage name", value="Home")
            meop_url = st.text_input("WebPage url", value=site_url)
            meop_id = st.text_input("WebPage @id", value=site_url)
            add_types = clean_list(st.text_area("WebPage additionalType (one per line)"))

            # ✅ UPDATED: nested about input WITH NAMES + hasPart
            st.markdown("#### WebPage about (nested)")
            st.caption(
                "Format:\n"
                "ParentName | wikiURL, wikidataURL\n"
                "  - ChildName | wikiURL, wikidataURL\n"
                "Example:\n"
                "Furniture | https://en.wikipedia.org/wiki/Furniture, https://www.wikidata.org/wiki/Q14745\n"
                "  - Bed | https://en.wikipedia.org/wiki/Bed, https://www.wikidata.org/wiki/Q1262753\n"
                "  - Sofa | https://en.wikipedia.org/wiki/Couch, https://www.wikidata.org/wiki/Q215380"
            )
            about_nested_lines = clean_list(st.text_area("About (parent + hasPart)"))

            mentions_urls = clean_list(st.text_area("WebPage mentions URLs (one per line)"))

            main_entity_of_page = {
                "name": meop_name,
                "url": meop_url,
                "@id": meop_id,
                "additionalType": add_types,
                "about": parse_about_nested(about_nested_lines),
                "mentions": [{"@type": "Thing", "name": u, "sameAs": u} for u in mentions_urls],
            }
        elif meop_mode == "String URL":
            main_entity_of_page_url = st.text_input("mainEntityOfPage URL (string)", value="")

    data = {
        "homepage_entity_type": homepage_entity_type,
        "business_type": business_type,
        "site_url": site_url,
        "name": name,

        "org_name": org_name,
        "description": description,
        "logo": logo,
        "image": image,
        "telephone": telephone,
        "email": email,
        "price_range": price_range,

        "same_as": same_as,
        "alternate_names": alternate_names,
        "knows_language": knows_language,

        # ✅ business-level optional fields
        "additional_types": additional_types,
        "knows_about": knows_about,

        "street": street,
        "city": city,
        "state": state,
        "zip": zip_code,
        "country": country,
        "lat": lat,
        "lng": lng,

        "has_map": has_map,
        "opening_hours_spec": opening_hours_spec,
        "area_served": area_served,

        "identifier_property_id": identifier_property_id,
        "identifier_value": identifier_value,
        "identifier_values": identifier_values,

        "makes_offer": makes_offer,
        "offer_catalog_name": offer_catalog_name,
        "offer_catalog_services": offer_catalog_services,
        "offer_catalog_mode": offer_catalog_mode,

        "main_entity_of_page": main_entity_of_page,
        "main_entity_of_page_url": main_entity_of_page_url,

        "website_schema": website_schema,
        "faqs": faqs,
    }

    schema = homepage_schema(data)

# -----------------------------------
# LOCAL BUSINESS
# -----------------------------------
elif page_type == "Local Business":
    st.subheader("Local Business Schema")

    col1, col2 = st.columns(2)

    with col1:
        business_type = st.selectbox("Business Type", [
            "LocalBusiness", "ProfessionalService", "MedicalBusiness",
            "HVACBusiness", "Plumber", "Physiotherapy"
        ])
        name = st.text_input("Business Name")
        legal_name = st.text_input("Legal Name", value=name)
        description = st.text_area("Description")
        url = st.text_input("Website URL")
        telephone = st.text_input("Telephone")
        email = st.text_input("Email")
        image = st.text_input("Image URL")
        logo = st.text_input("Logo URL")
        price_range = st.text_input("Price Range", value="$$")

    with col2:
        street = st.text_input("Street Address")
        city = st.text_input("City")
        state = st.text_input("State")
        zip_code = st.text_input("Zip / Postal Code")
        country = st.text_input("Country", value="US")
        lat = st.text_input("Latitude")
        lng = st.text_input("Longitude")

    st.markdown("### Optional Blocks")
    rating_enabled = st.checkbox("Add Aggregate Rating")
    map_enabled = st.checkbox("Add Map")
    sameas_enabled = st.checkbox("Add sameAs Links")
    additional_type_enabled = st.checkbox("Add additionalType")
    alternate_name_enabled = st.checkbox("Add alternateName")
    knows_about_enabled = st.checkbox("Add knowsAbout")
    area_served_enabled = st.checkbox("Add areaServed (postal codes + cities)")
    hours_enabled = st.checkbox("Add openingHoursSpecification")
    identifier_enabled = st.checkbox("Add identifier (PropertyValue)")
    founder_enabled = st.checkbox("Add founder (Person)")
    language_enabled = st.checkbox("Add knowsLanguage")
    catalog_enabled = st.checkbox("Add hasOfferCatalog (Services list)")

    rating_value = review_count = ""
    if rating_enabled:
        rating_value = st.text_input("Rating Value", value="4.9")
        review_count = st.text_input("Review Count", value="100")

    map_url = ""
    if map_enabled:
        map_url = st.text_input("Google Maps URL")

    same_as, additional_types, alternate_names, knows_about = [], [], [], []
    postal_codes, served_cities, area_name = [], [], ""

    if sameas_enabled:
        same_as = clean_list(st.text_area("sameAs Links (one per line)"))

    if additional_type_enabled:
        additional_types = clean_list(st.text_area("additionalType URLs (one per line)"))

    if alternate_name_enabled:
        alternate_names = clean_list(st.text_area("alternateName keywords (one per line)"))

    if knows_about_enabled:
        knows_about = clean_list(st.text_area("knowsAbout URLs (one per line)"))

    if area_served_enabled:
        area_name = st.text_input("Area Name", value=f"{city}, {state}")
        postal_codes = clean_list(st.text_area("Postal Codes (one per line)"))
        served_cities = clean_list(st.text_area("Served Cities (one per line)"))

    opening_hours = []
    if hours_enabled:
        st.markdown("#### Opening Hours")
        st.caption("Add rows like: dayOfWeek | opens | closes")
        lines = clean_list(st.text_area("Opening Hours (one per line)"))
        for line in lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 3:
                day, opens, closes = parts
                opening_hours.append({"dayOfWeek": day, "opens": opens, "closes": closes})

    identifier_property_id = identifier_value = ""
    if identifier_enabled:
        identifier_property_id = st.text_input("Identifier propertyID (e.g. kgmid, mapsCid)")
        identifier_value = st.text_input("Identifier value (URL or ID)")

    founder_name = founder_job_title = ""
    founder_same_as = []
    if founder_enabled:
        founder_name = st.text_input("Founder Name")
        founder_job_title = st.text_input("Founder Job Title", value="Founder")
        founder_same_as = clean_list(st.text_area("Founder sameAs Links (one per line)"))

    knows_language = ""
    if language_enabled:
        knows_language = st.text_input("knowsLanguage (e.g. en-US)", value="en-US")

    catalog_name = ""
    services = []
    if catalog_enabled:
        catalog_name = st.text_input("Catalog Name", value="Services")
        st.caption("Add services like: name | description | url (one per line)")
        svc_lines = clean_list(st.text_area("Services"))
        for line in svc_lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 3:
                services.append({"name": parts[0], "description": parts[1], "url": parts[2]})

    data = {
        "business_type": business_type,
        "name": name,
        "legal_name": legal_name,
        "description": description,
        "url": url,
        "telephone": telephone,
        "email": email,
        "image": image,
        "logo": logo,
        "price_range": price_range,
        "street": street,
        "city": city,
        "state": state,
        "zip": zip_code,
        "country": country,
        "lat": lat,
        "lng": lng,

        "rating_enabled": rating_enabled,
        "rating_value": rating_value,
        "review_count": review_count,

        "map_enabled": map_enabled,
        "map_url": map_url,

        "sameas_enabled": sameas_enabled,
        "same_as": same_as,

        "additional_type_enabled": additional_type_enabled,
        "additional_types": additional_types,

        "alternate_name_enabled": alternate_name_enabled,
        "alternate_names": alternate_names,

        "knows_about_enabled": knows_about_enabled,
        "knows_about": knows_about,

        "area_served_enabled": area_served_enabled,
        "area_name": area_name,
        "postal_codes": postal_codes,
        "served_cities": served_cities,

        "hours_enabled": hours_enabled,
        "opening_hours": opening_hours,

        "identifier_enabled": identifier_enabled,
        "identifier_property_id": identifier_property_id,
        "identifier_value": identifier_value,

        "founder_enabled": founder_enabled,
        "founder_name": founder_name,
        "founder_job_title": founder_job_title,
        "founder_same_as": founder_same_as,

        "language_enabled": language_enabled,
        "knows_language": knows_language,

        "catalog_enabled": catalog_enabled,
        "catalog_name": catalog_name,
        "services": services
    }

    schema = local_business_schema(data)

# -----------------------------------
# SERVICE PAGE
# -----------------------------------
elif page_type == "Service Page":
    st.subheader("Service Page Schema (WebPage + Service + FAQ + Breadcrumb)")

    col1, col2 = st.columns(2)

    with col1:
        service_name = st.text_input("Service Name")
        service_description = st.text_area("Service Description")
        url = st.text_input("Service Page URL")
        provider_type = st.selectbox("Provider Type", ["LocalBusiness", "Organization", "ProfessionalService"])
        provider_name = st.text_input("Provider Name")
        provider_url = st.text_input("Provider URL")

    with col2:
        site_name = st.text_input("Website Name (optional)")
        site_url = st.text_input("Website URL (optional)")
        area_served = st.text_input("Area Served (optional)")

        breadcrumb_enabled = st.checkbox("Add BreadcrumbList (recommended)")
        breadcrumbs = []
        if breadcrumb_enabled:
            st.markdown("Enter breadcrumbs like: Name | URL (one per line)")
            bc_lines = clean_list(st.text_area("Breadcrumbs"))
            for line in bc_lines:
                if "|" in line:
                    n, u = line.split("|", 1)
                    breadcrumbs.append({"name": n.strip(), "url": u.strip()})

        faq_enabled = st.checkbox("Add FAQPage (recommended)")
        faqs = []
        if faq_enabled:
            st.markdown("Enter FAQ like: Question | Answer (one per line)")
            faq_lines = clean_list(st.text_area("FAQ"))
            for line in faq_lines:
                if "|" in line:
                    q, a = line.split("|", 1)
                    faqs.append({"question": q.strip(), "answer": a.strip()})

    data = {
        "service_name": service_name,
        "service_description": service_description,
        "url": url,
        "provider_type": provider_type,
        "provider_name": provider_name,
        "provider_url": provider_url,
        "site_name": site_name,
        "site_url": site_url,
        "area_served": {"@type": "Place", "name": area_served} if area_served else None,
        "breadcrumb_enabled": breadcrumb_enabled,
        "breadcrumbs": breadcrumbs,
        "faq_enabled": faq_enabled,
        "faqs": faqs
    }

    schema = service_page_schema(data)

# -----------------------------------
# COLLECTION / CATEGORY PAGE
# -----------------------------------
elif page_type == "Collection / Category Page":
    st.subheader("Collection / Category Page Schema (CollectionPage + ItemList + FAQ)")

    name = st.text_input("Collection Name")
    url = st.text_input("Collection URL")
    description = st.text_area("Description")
    default_currency = st.text_input("Default Currency", value="USD")

    breadcrumb_enabled = st.checkbox("Add BreadcrumbList (recommended)")
    breadcrumbs = []
    if breadcrumb_enabled:
        st.markdown("Enter breadcrumbs like: Name | URL (one per line)")
        bc_lines = clean_list(st.text_area("Breadcrumbs"))
        for line in bc_lines:
            if "|" in line:
                n, u = line.split("|", 1)
                breadcrumbs.append({"name": n.strip(), "url": u.strip()})

    st.markdown("Enter products like: Name | URL | Image | Price | Currency | Availability (one per line)")
    prod_lines = clean_list(st.text_area("Products"))
    products = []
    for line in prod_lines:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            p = {"name": parts[0], "url": parts[1], "image": parts[2]}
            if len(parts) >= 4:
                p["price"] = parts[3]
            if len(parts) >= 5:
                p["currency"] = parts[4]
            if len(parts) >= 6:
                p["availability"] = parts[5]
            products.append(p)

    faq_enabled = st.checkbox("Add FAQPage (recommended)")
    faqs = []
    if faq_enabled:
        st.markdown("Enter FAQ like: Question | Answer (one per line)")
        faq_lines = clean_list(st.text_area("FAQ"))
        for line in faq_lines:
            if "|" in line:
                q, a = line.split("|", 1)
                faqs.append({"question": q.strip(), "answer": a.strip()})

    data = {
        "name": name,
        "url": url,
        "description": description,
        "products": products,
        "default_currency": default_currency,
        "breadcrumb_enabled": breadcrumb_enabled,
        "breadcrumbs": breadcrumbs,
        "faq_enabled": faq_enabled,
        "faqs": faqs
    }

    schema = collection_schema(data)

# -----------------------------------
# PRODUCT PAGE
# -----------------------------------
elif page_type == "Product Page":
    st.subheader("Product Schema")

    product_name = st.text_input("Product Name")
    product_description = st.text_area("Description")
    product_images = clean_list(st.text_area("Product Images (one per line)"))
    sku = st.text_input("SKU")
    brand = st.text_input("Brand")
    url = st.text_input("Product URL")

    currency = st.text_input("Currency", value="USD")
    price = st.text_input("Price")

    availability = st.selectbox("Availability", [
        "https://schema.org/InStock",
        "https://schema.org/OutOfStock",
        "https://schema.org/PreOrder"
    ])

    breadcrumb_enabled = st.checkbox("Add Breadcrumbs")
    breadcrumbs = []
    if breadcrumb_enabled:
        st.markdown("Enter breadcrumbs like: Name | URL (one per line)")
        bc_lines = clean_list(st.text_area("Breadcrumbs"))
        for line in bc_lines:
            if "|" in line:
                n, u = line.split("|", 1)
                breadcrumbs.append({"name": n.strip(), "url": u.strip()})

    st.markdown("### Optional Product Enhancements")
    main_entity_enabled = st.checkbox("Add mainEntityOfPage (WebPage)")
    product_rating_enabled = st.checkbox("Add Product aggregateRating")
    seller_enabled = st.checkbox("Add seller (Organization)")
    shipping_enabled = st.checkbox("Add shippingDetails")
    return_policy_enabled = st.checkbox("Add Merchant Return Policy")
    offer_extras_enabled = st.checkbox("Add Offer Extras (condition, priceValidUntil)")
    identifiers_enabled = st.checkbox("Add Product Identifiers (gtin/mpn)")

    page_name = page_description = site_url = site_name = ""
    if main_entity_enabled:
        page_name = st.text_input("Page Name", value=product_name)
        page_description = st.text_area("Page Description", value=product_description)
        site_url = st.text_input("Site URL", value="")
        site_name = st.text_input("Site Name", value="")

    product_rating_value = product_review_count = product_best_rating = ""
    if product_rating_enabled:
        product_rating_value = st.text_input("Rating Value", value="4.7")
        product_review_count = st.text_input("Review Count", value="150")
        product_best_rating = st.text_input("Best Rating", value="5")

    seller_name = seller_url = ""
    if seller_enabled:
        seller_name = st.text_input("Seller Name")
        seller_url = st.text_input("Seller URL")

    shipping_country = ""
    handling_min_days = handling_max_days = ""
    transit_min_days = transit_max_days = ""
    if shipping_enabled:
        shipping_country = st.text_input("Shipping Country Code", value="US")
        handling_min_days = st.text_input("Handling Min Days", value="1")
        handling_max_days = st.text_input("Handling Max Days", value="2")
        transit_min_days = st.text_input("Transit Min Days", value="2")
        transit_max_days = st.text_input("Transit Max Days", value="5")

    return_policy_category = return_days = return_method = return_fees = ""
    if return_policy_enabled:
        return_policy_category = st.text_input(
            "Return Policy Category (URL)",
            value="https://schema.org/MerchantReturnFiniteReturnWindow"
        )
        return_days = st.text_input("Merchant Return Days", value="30")
        return_method = st.text_input("Return Method (URL)", value="https://schema.org/ReturnByMail")
        return_fees = st.text_input("Return Fees (URL)", value="https://schema.org/FreeReturn")

    item_condition = price_valid_until = ""
    if offer_extras_enabled:
        item_condition = st.text_input("Item Condition (URL)", value="https://schema.org/NewCondition")
        price_valid_until = st.text_input("Price Valid Until (YYYY-MM-DD)", value="")

    gtin = mpn = ""
    if identifiers_enabled:
        gtin = st.text_input("GTIN")
        mpn = st.text_input("MPN")

    data = {
        "product_name": product_name,
        "product_description": product_description,
        "product_images": product_images,
        "sku": sku,
        "brand": brand,
        "url": url,
        "currency": currency,
        "price": price,
        "availability": availability,

        "breadcrumb_enabled": breadcrumb_enabled,
        "breadcrumbs": breadcrumbs,

        "main_entity_enabled": main_entity_enabled,
        "page_name": page_name,
        "page_description": page_description,
        "site_url": site_url,
        "site_name": site_name,

        "product_rating_enabled": product_rating_enabled,
        "product_rating_value": product_rating_value,
        "product_review_count": product_review_count,
        "product_best_rating": product_best_rating,

        "seller_enabled": seller_enabled,
        "seller_name": seller_name,
        "seller_url": seller_url,

        "shipping_enabled": shipping_enabled,
        "shipping_country": shipping_country,
        "handling_min_days": handling_min_days,
        "handling_max_days": handling_max_days,
        "transit_min_days": transit_min_days,
        "transit_max_days": transit_max_days,

        "return_policy_enabled": return_policy_enabled,
        "return_policy_category": return_policy_category,
        "return_days": return_days,
        "return_method": return_method,
        "return_fees": return_fees,

        "item_condition": item_condition,
        "price_valid_until": price_valid_until,

        "gtin": gtin,
        "mpn": mpn
    }

    schema = product_schema(data)

# -----------------------------------
# Output
# -----------------------------------
st.markdown("## Output")

if output_mode == "JSON-LD":
    st.code(json.dumps(schema, indent=2), language="json")
else:
    st.code(to_script_tag(schema), language="html")

st.download_button(
    "Download JSON-LD",
    data=json.dumps(schema, indent=2),
    file_name="schema.json",
    mime="application/json"
)