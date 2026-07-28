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

import base64
import os

import streamlit as st


# ---- 0. LOGO IMAGE (base64-encoded so it renders inline) -----

LOGO_PATH = os.path.join(os.path.dirname(__file__), "safebite_logo.png")


def _get_logo_base64():
    """Read the logo file and return it as a base64 string.

    Returns None if the logo file isn't found next to app.py, so the
    app still runs even if the image is missing.
    """
    try:
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None


LOGO_BASE64 = _get_logo_base64()


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
    "Frozen Pizza": [
        "Whole Wheat Crust",
        "Tomato Sauce",
        "Mozzarella Cheese",
        "Spinach",
        "Mushrooms",
        "Olive Oil",
        "Sodium Nitrite",
        "Excess Sodium",
        "Artificial Preservatives",
        "Refined White Flour",
    ],
    "Fruit Juice": [
        "100% Fruit Juice",
        "Vitamin C (Ascorbic Acid)",
        "No Added Sugar",
        "High Fructose Corn Syrup",
        "Artificial Colors",
        "Artificial Sweeteners",
        "Added Sugar",
    ],
    "Ice Cream": [
        "Milk",
        "Cream",
        "Egg Yolks",
        "Vanilla Extract",
        "Cocoa",
        "Artificial Colors",
        "Corn Syrup",
        "Carrageenan",
        "Mono- and Diglycerides",
    ],
    "Canned Soup": [
        "Tomatoes",
        "Carrots",
        "Beans",
        "Lentils",
        "Herbs",
        "Olive Oil",
        "Excess Sodium",
        "Modified Food Starch",
        "Monosodium Glutamate (MSG)",
        "Artificial Flavors",
    ],
    "Flavored Chips": [
        "Potatoes",
        "Avocado Oil",
        "Olive Oil",
        "Sea Salt",
        "Artificial Flavors",
        "Monosodium Glutamate (MSG)",
        "Yellow 6",
        "Red 40",
        "Excess Sodium",
    ],
    "Chocolate Chip Cookies": [
        "Whole Wheat Flour",
        "Oats",
        "Butter",
        "Eggs",
        "Vanilla Extract",
        "High Fructose Corn Syrup",
        "Trans Fat (Partially Hydrogenated Oil)",
        "Artificial Flavors",
        "Added Sugar",
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
    "Excess Sodium": {
        "type": "harmful",
        "explanation": "Salt added beyond what's needed, often used to "
                        "preserve food or boost flavor.",
        "concern": "Consuming too much sodium regularly is linked to "
                    "high blood pressure and heart strain.",
    },
    "Artificial Preservatives": {
        "type": "harmful",
        "explanation": "Man-made chemicals added to processed foods to "
                        "extend shelf life.",
        "concern": "Some artificial preservatives have been linked to "
                    "allergic reactions and other concerns in sensitive "
                    "people.",
    },
    "Refined White Flour": {
        "type": "harmful",
        "explanation": "Wheat flour stripped of its bran and germ, "
                        "leaving mostly starch behind.",
        "concern": "Lower in fiber and nutrients than whole grain flour, "
                    "and can cause quicker blood sugar spikes.",
    },
    "Artificial Colors": {
        "type": "harmful",
        "explanation": "Man-made dyes added to make food look more "
                        "vibrant or appealing.",
        "concern": "Some artificial colors have been linked to "
                    "hyperactivity in children and are being phased out "
                    "in several countries.",
    },
    "Artificial Sweeteners": {
        "type": "harmful",
        "explanation": "Man-made sugar substitutes used to sweeten food "
                        "without adding calories.",
        "concern": "Some research links heavy use to changes in gut "
                    "bacteria and continued sugar cravings.",
    },
    "Added Sugar": {
        "type": "harmful",
        "explanation": "Sugar added during processing rather than "
                        "occurring naturally in the food.",
        "concern": "Regularly eating extra added sugar is tied to weight "
                    "gain and other long-term health risks.",
    },
    "Corn Syrup": {
        "type": "harmful",
        "explanation": "A sweet syrup made from corn starch, used to "
                        "sweeten and add texture to processed foods.",
        "concern": "Adds extra sugar and calories with little "
                    "nutritional value.",
    },
    "Carrageenan": {
        "type": "harmful",
        "explanation": "A thickener extracted from red seaweed, used to "
                        "give creamy foods a smooth texture.",
        "concern": "Considered safe by most regulators, but some people "
                    "prefer to avoid it due to possible digestive "
                    "irritation.",
    },
    "Mono- and Diglycerides": {
        "type": "harmful",
        "explanation": "Emulsifiers that help keep water and fat blended "
                        "together in foods like ice cream and baked goods.",
        "concern": "Generally recognized as safe, though small amounts "
                    "can be derived from trans fats.",
    },
    "Modified Food Starch": {
        "type": "harmful",
        "explanation": "A starch that's been chemically or physically "
                        "altered to thicken or stabilize processed foods.",
        "concern": "Highly processed and offers little nutritional "
                    "value; can be a hidden source of extra carbs.",
    },
    "Artificial Flavors": {
        "type": "harmful",
        "explanation": "Lab-made flavor compounds used to mimic natural "
                        "tastes.",
        "concern": "Poorly regulated as a category, so it's hard to know "
                    "exactly what's inside; can trigger sensitivities in "
                    "some people.",
    },
    "Yellow 6": {
        "type": "harmful",
        "explanation": "A synthetic yellow-orange food dye used in "
                        "snacks, candy, and drinks.",
        "concern": "Linked in some studies to hyperactivity in children "
                    "and allergic reactions in sensitive individuals.",
    },
    "Red 40": {
        "type": "harmful",
        "explanation": "A synthetic red food dye, one of the most widely "
                        "used artificial colors.",
        "concern": "Linked in some studies to hyperactivity in children; "
                    "banned as a food additive in some countries.",
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
    "Whole Wheat Crust": {
        "type": "healthy",
        "explanation": "Pizza crust made from whole wheat flour instead "
                        "of refined white flour.",
        "concern": "Provides more fiber and nutrients than a traditional "
                    "white-flour crust.",
    },
    "Tomato Sauce": {
        "type": "healthy",
        "explanation": "A sauce made from cooked tomatoes, often with "
                        "herbs and seasoning.",
        "concern": "Good source of vitamin C and the antioxidant "
                    "lycopene.",
    },
    "Mozzarella Cheese": {
        "type": "healthy",
        "explanation": "A soft, mild cheese made from milk, commonly "
                        "used on pizza.",
        "concern": "Provides protein and calcium, though best enjoyed "
                    "in moderation due to saturated fat.",
    },
    "Spinach": {
        "type": "healthy",
        "explanation": "A leafy green vegetable often added for extra "
                        "nutrition.",
        "concern": "Rich in iron, fiber, and vitamins A and K.",
    },
    "Mushrooms": {
        "type": "healthy",
        "explanation": "An edible fungus used to add texture and umami "
                        "flavor to dishes.",
        "concern": "Low in calories and a good source of B vitamins and "
                    "antioxidants.",
    },
    "100% Fruit Juice": {
        "type": "healthy",
        "explanation": "Juice made entirely from real fruit with "
                        "nothing else added.",
        "concern": "Provides vitamins and antioxidants, though it's "
                    "still best enjoyed in moderation due to natural "
                    "sugar content.",
    },
    "Vitamin C (Ascorbic Acid)": {
        "type": "healthy",
        "explanation": "A vitamin naturally found in fruit, sometimes "
                        "added to boost nutrition or help preserve "
                        "freshness.",
        "concern": "Supports immune health and acts as an antioxidant.",
    },
    "No Added Sugar": {
        "type": "healthy",
        "explanation": "A label meaning no extra sugar was mixed in "
                        "beyond what's naturally in the food.",
        "concern": "Helps you avoid unnecessary added sugar in your "
                    "diet.",
    },
    "Milk": {
        "type": "healthy",
        "explanation": "A natural dairy liquid that's a good source of "
                        "protein and calcium.",
        "concern": "Supports bone health, though those with lactose "
                    "intolerance or a milk allergy should watch for it.",
    },
    "Cream": {
        "type": "healthy",
        "explanation": "The rich, fatty part of milk, used to add "
                        "richness to desserts.",
        "concern": "Adds calcium and richness, though it's high in "
                    "saturated fat, so moderation is key.",
    },
    "Egg Yolks": {
        "type": "healthy",
        "explanation": "The yellow center of an egg, rich in flavor and "
                        "nutrients.",
        "concern": "Good source of protein, healthy fats, and vitamin D.",
    },
    "Vanilla Extract": {
        "type": "healthy",
        "explanation": "A natural flavoring made from vanilla beans.",
        "concern": "Adds flavor without added sugar or artificial "
                    "ingredients.",
    },
    "Cocoa": {
        "type": "healthy",
        "explanation": "Made from ground, roasted cacao beans, used to "
                        "add chocolate flavor.",
        "concern": "Contains antioxidants called flavanols that support "
                    "heart health.",
    },
    "Tomatoes": {
        "type": "healthy",
        "explanation": "A juicy, nutrient-rich fruit commonly used as a "
                        "vegetable in cooking.",
        "concern": "High in vitamin C, potassium, and the antioxidant "
                    "lycopene.",
    },
    "Carrots": {
        "type": "healthy",
        "explanation": "A crunchy root vegetable naturally high in "
                        "beta-carotene.",
        "concern": "Supports eye health and provides fiber and "
                    "vitamin A.",
    },
    "Beans": {
        "type": "healthy",
        "explanation": "A plant-based protein and fiber source used in "
                        "soups and stews.",
        "concern": "Supports digestion and helps stabilize blood sugar.",
    },
    "Lentils": {
        "type": "healthy",
        "explanation": "Small legumes packed with plant protein and "
                        "fiber.",
        "concern": "Supports heart health and helps keep you full "
                    "longer.",
    },
    "Herbs": {
        "type": "healthy",
        "explanation": "Fresh or dried plants used to season food "
                        "naturally.",
        "concern": "Add flavor without needing extra salt or sugar.",
    },
    "Potatoes": {
        "type": "healthy",
        "explanation": "A starchy root vegetable, often sliced and "
                        "fried or baked into chips.",
        "concern": "A good source of potassium and vitamin C when not "
                    "deep-fried in unhealthy oils.",
    },
    "Avocado Oil": {
        "type": "healthy",
        "explanation": "An oil pressed from avocados, often used for "
                        "cooking and frying.",
        "concern": "Rich in heart-healthy monounsaturated fats.",
    },
    "Sea Salt": {
        "type": "healthy",
        "explanation": "Salt harvested from evaporated seawater, less "
                        "processed than table salt.",
        "concern": "Still sodium, so best in moderation, but free of "
                    "the anti-caking additives found in table salt.",
    },
    "Whole Wheat Flour": {
        "type": "healthy",
        "explanation": "Flour ground from the entire wheat kernel, "
                        "keeping the bran and germ.",
        "concern": "Higher in fiber and nutrients than refined white "
                    "flour.",
    },
    "Butter": {
        "type": "healthy",
        "explanation": "A dairy product made by churning cream.",
        "concern": "Adds flavor and some vitamin A, though it's high in "
                    "saturated fat, so moderation is key.",
    },
    "Eggs": {
        "type": "healthy",
        "explanation": "A versatile whole food that's a complete source "
                        "of protein.",
        "concern": "Provides protein, vitamins, and healthy fats.",
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

        /* Logo */
        .safebite-logo-wrap {
            display: flex;
            justify-content: center;
            margin-bottom: 0.75rem;
        }
        .safebite-logo {
            width: 170px;
            height: auto;
        }
        /* Smaller logo on narrow / mobile screens */
        @media (max-width: 600px) {
            .safebite-logo {
                width: 120px;
            }
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

if LOGO_BASE64:
    st.markdown(
        f"""
        <div class="safebite-logo-wrap">
            <img class="safebite-logo" src="data:image/png;base64,{LOGO_BASE64}" alt="SafeBite logo">
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    # Fallback text header in case the logo file isn't found.
    st.markdown(
        '<p style="color:#526539; font-size:2.4rem; font-weight:800; '
        'text-align:center; margin-bottom:0;">🌿 SafeBite</p>',
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



