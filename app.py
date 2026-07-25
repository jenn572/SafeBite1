# ============================================================
#  SafeBite - Sprint 1
#  The user selects a product and sees its ingredients,
#  ingredient warnings, and allergy alerts.
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
}

# Ingredients we want to warn users about, and why.
WATCH_LIST = {
    "BHT": "A preservative linked to health concerns.",
    "Azodicarbonamide": "A dough conditioner linked to breathing issues.",
    "Disodium Inosinate": "A flavor enhancer often found in processed foods.",
    "Palm Oil": "High in saturated fat.",
}

# Common allergens to flag.
ALLERGENS = [
    "Peanuts",
    "Wheat",
    "Soybean Oil",
    "Milk",
    "Egg",
]


# ---- 2. PAGE SETUP ------------------------------------------

st.set_page_config(
    page_title="SafeBite",
    page_icon="🌿",
    layout="centered",
)


# ---- 3. SIMPLE SAFEBITE STYLING -----------------------------

st.markdown(
    """
    <style>
        /* Main page background */
        .stApp {
            background-color: #FDF7EF;
        }

        /* Reduce empty space at the top of the page */
        .block-container {
            max-width: 800px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        /* SafeBite title */
        .safebite-title {
            color: #526539;
            font-size: 3rem;
            font-weight: 700;
            text-align: center;
            margin-bottom: 0;
        }

        /* SafeBite slogan */
        .safebite-slogan {
            color: #8C9B5D;
            font-size: 1.2rem;
            text-align: center;
            margin-top: 0;
            margin-bottom: 2rem;
        }

        /* Introductory instruction card */
        .instruction-card {
            background-color: #DCE4C9;
            color: #526539;
            padding: 1rem 1.25rem;
            border-radius: 14px;
            margin-bottom: 1.5rem;
        }

        /* Main action button */
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

        /* Sidebar background */
        [data-testid="stSidebar"] {
            background-color: #DCE4C9;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---- 4. HEADER ----------------------------------------------

st.markdown(
    '<h1 class="safebite-title">🌿 SafeBite</h1>',
    unsafe_allow_html=True,
)

st.markdown(
    '<p class="safebite-slogan">Love your food. Trust your bite.</p>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="instruction-card">
        <strong>How it works:</strong>
        Choose a food product below and press
        <strong>Check ingredients</strong> to learn what is inside it.
    </div>
    """,
    unsafe_allow_html=True,
)


# ---- 5. PRODUCT SELECTION -----------------------------------

st.subheader("🔎 Check a product")

choice = st.selectbox(
    "Choose a product",
    list(PRODUCTS.keys()),
    help="Select one food product from the list.",
)

check_button = st.button(
    "Check ingredients",
    type="primary",
)


# ---- 6. DISPLAY THE RESULTS ---------------------------------

if check_button:
    ingredients = PRODUCTS[choice]

    st.divider()

    st.subheader(f"📦 {choice}")

    st.write("#### Ingredients")

    # Display each ingredient separately to make the list easier to read.
    for ingredient in ingredients:
        st.markdown(
            f'<div class="ingredient-card">🌱 {ingredient}</div>',
            unsafe_allow_html=True,
        )

    st.write("")

    # ---- 7. CHECK FOR INGREDIENTS TO WATCH ------------------

    flagged = [
        ingredient
        for ingredient in ingredients
        if ingredient in WATCH_LIST
    ]

    if flagged:
        st.warning("⚠️ Ingredients to watch out for")

        for ingredient in flagged:
            st.write(
                f"**{ingredient}:** {WATCH_LIST[ingredient]}"
            )
    else:
        st.success(
            "✅ No ingredients from our watch list were found."
        )

    # ---- 8. CHECK FOR ALLERGENS -----------------------------

    allergen_hits = [
        ingredient
        for ingredient in ingredients
        if ingredient in ALLERGENS
    ]

    if allergen_hits:
        st.error(
            "🚨 Allergy alert: "
            + ", ".join(allergen_hits)
        )
    else:
        st.info(
            "No allergens from our current allergen list were found."
        )


# ---- 9. SIDEBAR ---------------------------------------------

with st.sidebar:
    st.header("🌿 About SafeBite")

    st.write(
        "SafeBite helps people understand the ingredients "
        "in the foods they eat."
    )

    st.divider()

    st.write("**Sprint 1**")
    st.write("Product and ingredient checking")

    st.caption(
        "SafeBite is an educational tool and should not replace "
        "professional medical advice or official product labels."
    )

