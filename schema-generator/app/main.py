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
# HOMEPAGE
# -----------------------------------
if page_type == "Homepage":
    st.subheader("Homepage Schema (WebSite + Organization)")

    col1, col2 = st.columns(2)

    with col1:
        site_name = st.text_input("Website Name")
        site_url = st.text_input("Website URL")
        org_type = st.selectbox("Entity Type for Brand", ["Organization", "LocalBusiness"])
        org_name = st.text_input("Organization / Business Name")
        logo = st.text_input("Logo URL")
        image = st.text_input("Image URL")
        telephone = st.text_input("Telephone")

    with col2:
        description = st.text_area("Site Description")
        search_enabled = st.checkbox("Add SearchAction (recommended)", value=True)
        search_url = ""
        if search_enabled:
            search_url = st.text_input(
                "Search URL Template",
                value=f"{site_url.rstrip('/')}/search?q={{search_term_string}}"
            )

        same_as_enabled = st.checkbox("Add sameAs (recommended)")
        same_as = clean_list(st.text_area("sameAs Links (one per line)")) if same_as_enabled else []

        additional_type_enabled = st.checkbox("Add additionalType (optional)")
        additional_types = clean_list(st.text_area("additionalType URLs (one per line)")) if additional_type_enabled else []

        about_enabled = st.checkbox("Add about entities (optional)")
        about_entities = clean_list(st.text_area("about URLs (Wikipedia/Wikidata)")) if about_enabled else []

    data = {
        "site_name": site_name,
        "site_url": site_url,
        "org_type": org_type,
        "org_name": org_name,
        "logo": logo,
        "image": image,
        "telephone": telephone,
        "description": description,
        "search_enabled": search_enabled,
        "search_url": search_url,
        "same_as": same_as,
        "additional_types": additional_types,
        "about_entities": about_entities
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
    additional_type_enabled = st.checkbox("Add additionalType (ProductOntology)")
    alternate_name_enabled = st.checkbox("Add alternateName (SEO keywords)")
    knows_about_enabled = st.checkbox("Add knowsAbout (Wikipedia/Wikidata)")
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
                opening_hours.append({
                    "dayOfWeek": day,
                    "opens": opens,
                    "closes": closes
                })

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
                services.append({
                    "name": parts[0],
                    "description": parts[1],
                    "url": parts[2]
                })

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