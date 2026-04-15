import streamlit as st

st.set_page_config(layout="wide")
st.markdown("""
    <style>
    /* Reduce spacing between list items */
    ul {
        margin-top: 0px;
        margin-bottom: 0px;
    }

    li {
        margin-bottom: 2px;   /* adjust this value */
    }

    /* Reduce spacing in markdown blocks */
    div[data-testid="stMarkdownContainer"] p {
        margin-bottom: 4px;
    }
    div[data-testid="stExpander"] details summary p{
        font-size: 1.5rem !important;
        font-weight: 600 !important;
    }
    </style>
""", unsafe_allow_html=True)

def render_daily_summary(summary: str):
    st.markdown(f"""
    <div style="
        background-color:#e5f6df;
        padding:18px 20px;
        border-radius:12px;
        border:2px solid #198450;
        font-size:17px;
        line-height:1.6;
        color:#111827;
    ">
        {summary}
    </div>
    """, unsafe_allow_html=True)

def render_top_trends(trends):
    st.markdown("## 🔥 Top Trends")

    cols = st.columns(len(trends))

    for col, trend in zip(cols, trends):
        with col:
            st.markdown(f"### {trend['name']}")
            st.write(trend["description"])
            st.caption(f"{trend['article_count']} articles")

def render_top_articles(top_articles):
    st.markdown("## 📰 Top Stories")

    cols = st.columns(3)
    for col, article in zip(cols, top_articles):
        with col:
            st.markdown(f"### {article['title']}")
            st.write(article["reason"])

def render_emerging_signals(signals):
    st.markdown("## 🧭 Emerging Signals")

    html = " ".join([
        f"<span style='display:inline-block; font-size:16px; padding:5px 15px; margin:3px; "
        f"background:#1f2937; color:white; border-radius:12px; margin-right:6px;'>"
        f"⚡ {s}</span>"
        for s in signals
    ])
    st.markdown(html, unsafe_allow_html=True)

def render_key_entities(entities):
    st.markdown("## 🧩 Who’s Driving the News")

    st.markdown("#### Companies")
    comp_html = " ".join(
        [f"<span style='font-size:16px; padding:4px 8px; "
        f"background-color:#1f2937; color:white; border-radius:8px; margin-right:6px;'>{c}</span>"
        for c in entities.get("companies", [])]
    )
    st.markdown(comp_html, unsafe_allow_html=True)

    st.markdown("#### Technologies")
    tech_html = " ".join(
        [f"<span style='font-size:16px; padding:4px 8px; "
        f"background-color:#1f2937; color:white; border-radius:8px; margin-right:6px;'>{t}</span>"
        for t in entities.get("technologies", [])]
    )
    st.markdown(tech_html, unsafe_allow_html=True)

def extract_filter_options(articles):
    categories = set()
    companies = set()
    technologies = set()
    products = set()

    for art in articles:
        categories.add(art.get("category"))

        ent = art.get("entities", {})
        companies.update(ent.get("companies", []))
        technologies.update(ent.get("technologies", []))
        products.update(ent.get("products", []))

    return {
        "categories": sorted(categories),
        "companies": sorted(companies),
        "technologies": sorted(technologies),
        "products": sorted(products)
    }

def render_filters(filter_options):
    col1, col2, col3, col4 = st.columns(4)
    selected = {}
    with col1:
        selected["category"] = st.multiselect(
            "Category", filter_options["categories"]
        )
    with col2:
        selected["companies"] = st.multiselect(
            "Companies", filter_options["companies"]
        )
    with col3:
        selected["technologies"] = st.multiselect(
            "Technologies", filter_options["technologies"]
        )
    with col4:
        selected["products"] = st.multiselect(
            "Products", filter_options["products"]
        )

    return selected

def filter_articles(articles, filters):
    def match(article):
        # Category
        if filters["category"]:
            if article.get("category") not in filters["category"]:
                return False

        ent = article.get("entities", {})

        # Companies
        if filters["companies"]:
            if not set(ent.get("companies", [])) & set(filters["companies"]):
                return False

        # Technologies
        if filters["technologies"]:
            if not set(ent.get("technologies", [])) & set(filters["technologies"]):
                return False

        # Products
        if filters["products"]:
            if not set(ent.get("products", [])) & set(filters["products"]):
                return False

        return True

    return [a for a in articles if match(a)]

def render_tags(items, color="#1f2937"):
    if not items:
        return ""

    return " ".join([
        f"""<span style='
            display:inline-block;
            padding:5px 12px;
            margin:3px 4px 3px 0;
            font-size:15px;
            border-radius:8px;
            background-color:{color};
            color:white;
        '>{i}</span>"""
        for i in items
    ])

def render_article_explorer(articles):
    for art in articles:
        with st.expander(art["title"]):
            st.caption("by " + art.get("author", ""))
            st.markdown("**Summary**")
            st.write(art["summary"])

            ent = art.get("entities", {})
            col1, col2, col3 = st.columns([3, 1, 2])
            with col1:
                st.markdown("**Key Points**")
                for kp in art.get("key_points", []):
                    st.markdown(f"- {kp}")
            with col2:
                st.markdown(f"**Category:**")
                st.markdown(render_tags([art.get('category')], color="#374151"), unsafe_allow_html=True)
                if ent:
                    if ent.get("companies"):
                        st.markdown("**Companies**")
                        st.markdown(render_tags(ent.get("companies"), color="#2563eb"), unsafe_allow_html=True)
            with col3:
                if ent:
                    if ent.get("products"):
                        st.markdown("**Products**")
                        st.markdown(render_tags(ent.get("products"), color="#059669"), unsafe_allow_html=True)
                    if ent.get("technologies"):
                        st.markdown("**Technologies**")
                        st.markdown(render_tags(ent.get("technologies"), color="#7c3aed"), unsafe_allow_html=True)
            st.markdown(f"[Read the full article here]({art.get('link', '')})")

def display_app(insights, articles, audio):
    """
    Renders the Streamlit UI for the AI News Dashboard.

    Sections:
    - Header + audio brief
    - Sidebar (search + controls)
    - Daily summary
    - Trends and signals
    - Top stories
    - Article explorer with filters
    """

    # Title
    st.markdown(
        "<h1 style='text-align: center;'>🧠 Daily AI Brief</h1>", 
        unsafe_allow_html=True
    )
    st.audio(audio, sample_rate=24000) # Audio summary player

    # Sidebar (controls)
    with st.sidebar:
        st.header("🔎 Search...")
        search_word = st.text_input('search', 'Enter Keyword')
        if st.button("🗞️ Regenerate News...", use_container_width=True):
            # TODO: Hook into pipeline rerun
            print("regeneration")

    # -----------------------------
    # Main content
    # -----------------------------

    # Daily summary (highlight section)
    render_daily_summary(insights["daily_summary"])

    # Top trends
    render_top_trends(insights["top_trends"])

    # Signals + Entities (2-column layout)
    left_col, right_col = st.columns(2)
    with left_col:
        render_emerging_signals(insights["emerging_signals"])
    with right_col:
        render_key_entities(insights["key_entities"])

    # Top stories
    render_top_articles(insights["top_articles"])

    # Article Explorer
    st.markdown("## 📚 Explore Articles")
    filter_options = extract_filter_options(articles) # extract filter options
    selected_filters = render_filters(filter_options) # ender filter UI
    filtered_articles = filter_articles(articles, selected_filters) # apply filters
    render_article_explorer(filtered_articles) # display articles