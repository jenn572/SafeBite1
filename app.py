# ============================================================
#  SafeBite - Sprint 2
#  The user selects a product and sees its ingredients,
#  ingredient warnings, allergy alerts, and can browse a
#  full Ingredient Dictionary of harmful & healthy ingredients.
#
#  HOW TO RUN:
#     python3 -m pip install -r requirements.txt
#     python3 -m streamlit run app.py
# ============================================================

import streamlit as st


# ---- 1. OUR SMALL BUILT-IN FOOD LIST ------------------------

PRODUCTS = {
    "Breakfast Cereal": [
        "Whole Grain Wheat",
        "Sugar",
        "Salt",
        "BHT",
    ],
    "Fast Food Bread Bun": [
        "Enriched Flour",
        "Water",
        "Azodicarbonamide",
        "Soybean Oil",
    ],
    "Peanut Snack Bar": [
        "Peanuts",
        "Sugar",
        "Palm Oil",
        "Salt",
    ],
    "Instant Noodles": [
        "Wheat Flour",
        "Palm Oil",
        "Salt",
        "Disodium Inosinate",
    ],
    "Greek Yogurt": [
        "Milk",
        "Live Cultures",
        "Honey",
    ],
    "Mixed Nuts Trail Mix": [
        "Almonds",
        "Walnuts",
        "Chia Seeds",
        "Dried Cranberries",
    ],
}


# ---- 2. INGREDIENT DICTIONARY --------------------------------
# Every ingredient we know about, tagged as "harmful" or
# "healthy", with a plain-language explanation and a note on
# the health concern (harmful) or health benefit (healthy).

INGREDIENT_DICTIONARY = {
    # ---------------- HARMFUL / WATCH-LIST ----------------
    "BHT": {
        "type": "harmful",
        "explanation": "A man-made preservative that keeps oils and fats "
                        "in packaged food from going bad too quickly.",
        "concern": "Linked to possible hormone disruption and health "
                    "concerns in some animal studies.",
    },
    "Azodicarbonamide": {
        "type": "harmful",
        "explanation": "A chemical used to make bread dough softer and "
                        "help it rise more evenly.",
        "concern": "Breaks down into compounds linked to breathing issues; "
                    "banned as a food additive in the EU and UK.",
    },
    "Disodium Inosinate": {
        "type": "harmful",
        "explanation": "A flavor enhancer often paired with MSG to make "
                        "savory foods taste richer.",
        "concern": "Usually made from meat or fish, so it isn't vegetarian-"
                    "friendly, and can cause reactions in sensitive people.",
    },
    "Palm Oil": {
        "type": "harmful",
        "explanation": "A cheap vegetable oil used to add texture and "
                        "shelf life to processed snacks.",
        "concern": "High in saturated fat, which can raise cholesterol "
                    "if eaten often.",
    },
    "Sugar": {
        "type": "harmful",
        "explanation": "A sweetener added to make food taste better, "
                        "often in larger amounts than people realize.",
        "concern": "Eating too much added sugar is linked to weight gain, "
                    "energy crashes, and long-term health risks.",
    },
    "Salt": {
        "type": "harmful",
        "explanation": "Used to preserve food and boost flavor.",
        "concern": "Too much sodium over time can raise blood pressure.",
    },
    "High Fructose Corn Syrup": {
        "type": "harmful",
        "explanation": "A cheap liquid sweetener made from corn starch, "
                        "common in sodas and packaged sweets.",
        "concern": "Linked to weight gain and blood sugar spikes when "
                    "consumed regularly.",
    },
    "Artificial Food Dye": {
        "type": "harmful",
        "explanation": "Man-made coloring (like Red 40 or Yellow 5) added "
                        "to make food look more appealing.",
        "concern": "Some studies link certain dyes to hyperactivity in "
                    "children; a few are being phased out in the US.",
    },
    "Sodium Nitrite": {
        "type": "harmful",
        "explanation": "A preservative used in cured meats like bacon and "
                        "deli slices to keep them pink and fresh-looking.",
        "concern": "Can form compounds linked to cancer risk when meat "
                    "is cooked at high heat.",
    },
    "Trans Fat (Partially Hydrogenated Oil)": {
        "type": "harmful",
        "explanation": "An artificially hardened oil once common in fried "
                        "and baked packaged foods.",
        "concern": "Raises bad cholesterol and lowers good cholesterol; "
                    "banned in many countries.",
    },
    "Monosodium Glutamate (MSG)": {
        "type": "harmful",
        "explanation": "A flavor enhancer that makes savory foods taste "
                        "more intense.",
        "concern": "Considered safe in moderation by most health bodies, "
                    "but can trigger headaches or discomfort in sensitive "
                    "people.",
    },

    # ---------------- HEALTHY ----------------
    "Whole Grain Wheat": {
        "type": "healthy",
        "explanation": "Wheat that keeps its natural bran and germ instead "
                        "of being stripped down to white flour.",
        "concern": "Good source of fiber that supports digestion and "
                    "helps you feel full longer.",
    },
    "Live Cultures": {
        "type": "healthy",
        "explanation": "Beneficial bacteria (probiotics) found in yogurt "
                        "and fermented foods.",
        "concern": "Supports gut health and digestion.",
    },
    "Honey": {
        "type": "healthy",
        "explanation": "A natural sweetener made by bees from flower "
                        "nectar.",
        "concern": "A gentler alternative to refined sugar, though still "
                    "best in moderation.",
    },
    "Almonds": {
        "type": "healthy",
        "explanation": "A nutrient-dense tree nut, often eaten as a snack "
                        "or ground into flour and milk.",
        "concern": "Rich in healthy fats, protein, and vitamin E.",
    },
    "Walnuts": {
        "type": "healthy",
        "explanation": "A tree nut with a distinct wrinkled shape and "
                        "rich, slightly bitter flavor.",
        "concern": "One of the best plant sources of omega-3 fatty acids, "
                    "which support heart and brain health.",
    },
    "Chia Seeds": {
        "type": "healthy",
        "explanation": "Tiny seeds that swell up and turn gel-like when "
                        "soaked in liquid.",
        "concern": "High in fiber and omega-3s, which support digestion "
                    "and heart health.",
    },
    "Dried Cranberries": {
        "type": "healthy",
        "explanation": "Cranberries with the water removed, often lightly "
                        "sweetened.",
        "concern": "Contain antioxidants, though watch for added sugar "
                    "in sweetened varieties.",
    },
    "Olive Oil": {
        "type": "healthy",
        "explanation": "An oil pressed from olives, common in "
                        "Mediterranean cooking.",
        "concern": "Rich in heart-healthy monounsaturated fats.",
    },
    "Oats": {
        "type": "healthy",
        "explanation": "A whole grain often rolled or ground for cereals "
                        "and baked goods.",
        "concern": "High in soluble fiber, which can help lower "
                    "cholesterol.",
    },
    "Greek Yogurt Cultures": {
        "type": "healthy",
        "explanation": "Strains of good bacteria used to ferment milk "
                        "into thick, tangy yogurt.",
        "concern": "Supports digestion and provides protein.",
    },
    "Flaxseed": {
        "type": "healthy",
        "explanation": "A small seed that's often ground for easier "
                        "digestion and added to baked goods or smoothies.",
        "concern": "A great plant source of fiber and omega-3 fatty "
                    "acids.",
    },
}

# Kept separate for the ingredient-check logic on the Scan page.
WATCH_LIST = {
    name: data["concern"]
    for name, data in INGREDIENT_DICTIONARY.items()
    if data["type"] == "harmful"
}

HEALTHY_HIGHLIGHTS = {
    name: data["concern"]
    for name, data in INGREDIENT_DICTIONARY.items()
    if data["type"] == "healthy"
}

# Common allergens to flag.
ALLERGENS = [
    "Peanuts",
    "Wheat",
    "Soybean Oil",
    "Milk",
    "Egg",
    "Almonds",
    "Walnuts",
]


# ---- 3. PAGE SETUP ------------------------------------------

st.set_page_config(
    page_title="SafeBite",
    page_icon="🌿",
    layout="centered",
)

if "scan_count" not in st.session_state:
    st.session_state.scan_count = 16  # starting stat, like the app mockup

if "last_result" not in st.session_state:
    st.session_state.last_result = None


# ---- 4. APP-STYLE CSS ----------------------------------------

st.markdown(
    """
    <style>
        /* Main page background */
        .stApp {
            background-color: #FDF7EF;
        }

        .block-container {
            max-width: 480px;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }

        /* Header row */
        .safebite-header {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            margin-bottom: 0;
        }
        .safebite-title {
            color: #526539;
            font-size: 2.4rem;
            font-weight: 800;
            text-align: center;
            margin-bottom: 0;
        }
        .safebite-slogan {
            color: #8C9B5D;
            font-size: 1rem;
            text-align: center;
            margin-top: 0;
            margin-bottom: 1.5rem;
        }

        /* Greeting card */
        .greeting-card {
            background-color: #FFFFFF;
            border-radius: 18px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 10px rgba(82, 101, 57, 0.08);
        }
        .greeting-title {
            font-size: 1.3rem;
            font-weight: 700;
            color: #33421F;
            margin-bottom: 0.1rem;
        }
        .greeting-sub {
            color: #7A8B63;
            font-size: 0.9rem;
        }

        /* Stat pills */
        .stat-card {
            background-color: #FFFFFF;
            border: 1px solid #DCE4C9;
            border-radius: 16px;
            padding: 0.8rem;
            text-align: center;
            box-shadow: 0 2px 8px rgba(82, 101, 57, 0.06);
        }
        .stat-number {
            font-size: 1.4rem;
            font-weight: 800;
            color: #526539;
        }
        .stat-label {
            font-size: 0.78rem;
            color: #8C9B5D;
        }

        /* Hero scan card */
        .hero-card {
            background: linear-gradient(135deg, #DCE4C9 0%, #C6D2A8 100%);
            border-radius: 20px;
            padding: 1.4rem 1.4rem;
            margin: 1rem 0 1.3rem 0;
        }
        .hero-title {
            font-size: 1.4rem;
            font-weight: 800;
            color: #33421F;
            margin-bottom: 0.2rem;
        }
        .hero-sub {
            font-size: 0.9rem;
            color: #4C5A38;
            margin-bottom: 0;
        }

        /* Section headers */
        .section-title {
            color: #526539;
            font-weight: 700;
            font-size: 1.1rem;
            margin: 1.2rem 0 0.5rem 0;
        }

        /* Instruction / info card */
        .instruction-card {
            background-color: #DCE4C9;
            color: #526539;
            padding: 0.9rem 1.1rem;
            border-radius: 14px;
            margin-bottom: 1.2rem;
            font-size: 0.9rem;
        }

        /* Buttons */
        .stButton > button {
            width: 100%;
            background-color: #526539;
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.7rem 1rem;
            font-weight: 600;
        }
        .stButton > button:hover {
            background-color: #8C9B5D;
            color: white;
            border: none;
        }

        /* Ingredient item cards */
        .ingredient-card {
            background-color: white;
            border: 1px solid #DCE4C9;
            border-radius: 10px;
            padding: 0.65rem 0.8rem;
            margin-bottom: 0.5rem;
        }

        /* Dictionary entry cards */
        .dict-card {
            border-radius: 14px;
            padding: 0.9rem 1.1rem;
            margin-bottom: 0.7rem;
            border: 1px solid;
        }
        .dict-card.harmful {
            background-color: #FDECEA;
            border-color: #F3B9B4;
        }
        .dict-card.healthy {
            background-color: #EAF3E2;
            border-color: #BBD9A0;
        }
        .dict-name {
            font-weight: 700;
            font-size: 1.02rem;
            margin-bottom: 0.15rem;
        }
        .dict-name.harmful { color: #A23B2E; }
        .dict-name.healthy { color: #3F6B24; }
        .dict-badge {
            display: inline-block;
            font-size: 0.7rem;
            font-weight: 700;
            padding: 0.1rem 0.55rem;
            border-radius: 999px;
            margin-left: 0.4rem;
            vertical-align: middle;
        }
        .dict-badge.harmful { background-color: #E8776B; color: white; }
        .dict-badge.healthy { background-color: #78A855; color: white; }
        .dict-explanation { color: #4A4A4A; font-size: 0.88rem; margin: 0.3rem 0; }
        .dict-concern { font-size: 0.85rem; font-style: italic; }
        .dict-concern.harmful { color: #A23B2E; }
        .dict-concern.healthy { color: #3F6B24; }

        /* Sidebar background */
        [data-testid="stSidebar"] {
            background-color: #DCE4C9;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---- 5. HEADER ----------------------------------------------

st.markdown(
    '<p class="safebite-title">🌿 SafeBite</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="safebite-slogan">Love your food. Trust your bite.</p>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="greeting-card">
        <div class="greeting-title">Hi there! 👋</div>
        <div class="greeting-sub">You're on your way to stronger, healthier habits.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

stat_col1, stat_col2 = st.columns(2)
with stat_col1:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-number">{st.session_state.scan_count}</div>
            <div class="stat-label">Scans &middot; Keep it up!</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with stat_col2:
    st.markdown(
        """
        <div class="stat-card">
            <div class="stat-number">⭐ 4.8</div>
            <div class="stat-label">Community Rating</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---- 6. TOP NAVIGATION ---------------------------------------

tab_scan, tab_dictionary = st.tabs(["🔍  Scanner", "📖  Dictionary"])


# ============================================================
#  SCANNER TAB
# ============================================================

with tab_scan:

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">Scan food ingredients</div>
            <p class="hero-sub">
                Choose a product below to detect harmful ingredients
                and make smarter choices.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<p class="section-title">🔎 Check a product</p>', unsafe_allow_html=True)

    choice = st.selectbox(
        "Choose a product",
        list(PRODUCTS.keys()),
        help="Select one food product from the list.",
        label_visibility="collapsed",
    )

    check_button = st.button("Tap to Scan", type="primary")

    if check_button:
        st.session_state.scan_count += 1
        st.session_state.last_result = choice

    if st.session_state.last_result:
        result_choice = st.session_state.last_result
        ingredients = PRODUCTS[result_choice]

        st.divider()
        st.subheader(f"📦 {result_choice}")
        st.write("#### Ingredients")

        for ingredient in ingredients:
            st.markdown(
                f'<div class="ingredient-card">🌱 {ingredient}</div>',
                unsafe_allow_html=True,
            )

        st.write("")

        # ---- Harmful / watch-list check ----
        flagged = [i for i in ingredients if i in WATCH_LIST]

        if flagged:
            st.warning("⚠️ Ingredients to watch out for")
            for ingredient in flagged:
                st.write(f"**{ingredient}:** {WATCH_LIST[ingredient]}")
        else:
            st.success("✅ No ingredients from our watch list were found.")

        # ---- Healthy highlights ----
        healthy_found = [i for i in ingredients if i in HEALTHY_HIGHLIGHTS]
        if healthy_found:
            st.info("🌿 Healthy ingredients spotted")
            for ingredient in healthy_found:
                st.write(f"**{ingredient}:** {HEALTHY_HIGHLIGHTS[ingredient]}")

        # ---- Allergen check ----
        allergen_hits = [i for i in ingredients if i in ALLERGENS]

        if allergen_hits:
            st.error("🚨 Allergy alert: " + ", ".join(allergen_hits))
        else:
            st.info("No allergens from our current allergen list were found.")


# ============================================================
#  DICTIONARY TAB
# ============================================================

with tab_dictionary:

    st.markdown(
        """
        <div class="instruction-card">
            <strong>Ingredient Dictionary</strong> — search any ingredient to
            see a simple explanation and whether it's something to enjoy
            or watch out for.
        </div>
        """,
        unsafe_allow_html=True,
    )

    search_term = st.text_input(
        "Search ingredients",
        placeholder="Search an ingredient, e.g. 'Palm Oil'",
        label_visibility="collapsed",
    )

    filter_choice = st.radio(
        "Filter",
        ["All", "⚠️ Harmful", "🌿 Healthy"],
        horizontal=True,
        label_visibility="collapsed",
    )

    entries = sorted(INGREDIENT_DICTIONARY.items(), key=lambda x: x[0])

    if search_term:
        entries = [
            (name, data) for name, data in entries
            if search_term.lower() in name.lower()
        ]

    if filter_choice == "⚠️ Harmful":
        entries = [(n, d) for n, d in entries if d["type"] == "harmful"]
    elif filter_choice == "🌿 Healthy":
        entries = [(n, d) for n, d in entries if d["type"] == "healthy"]

    st.markdown(f'<p class="section-title">{len(entries)} ingredient(s)</p>', unsafe_allow_html=True)

    if not entries:
        st.info("No ingredients match your search.")

    for name, data in entries:
        kind = data["type"]
        badge_text = "HARMFUL" if kind == "harmful" else "HEALTHY"
        icon = "⚠️" if kind == "harmful" else "🌿"
        concern_label = "Health concern" if kind == "harmful" else "Health benefit"

        st.markdown(
            f"""
            <div class="dict-card {kind}">
                <span class="dict-name {kind}">{icon} {name}</span>
                <span class="dict-badge {kind}">{badge_text}</span>
                <div class="dict-explanation">{data['explanation']}</div>
                <div class="dict-concern {kind}">{concern_label}: {data['concern']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---- 7. SIDEBAR ---------------------------------------------

with st.sidebar:
    st.header("🌿 About SafeBite")

    st.write(
        "SafeBite helps people understand the ingredients "
        "in the foods they eat."
    )

    st.divider()

    st.write("**Sprint 2**")
    st.write("Product scanning + full Ingredient Dictionary")

    st.caption(
        "SafeBite is an educational tool and should not replace "
        "professional medical advice or official product labels."
    )

