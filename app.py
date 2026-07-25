# ============================================================
#  SafeBite  -  Sprint 1 (simple version, no camera needed)
#  The user picks a product and sees its ingredients, with
#  warnings for allergens and ingredients to watch out for.
#
#  HOW TO RUN (Mac):
#     python3 -m pip install -r requirements.txt
#     python3 -m streamlit run app.py
# ============================================================

import streamlit as st

# ---- 1. OUR SMALL BUILT-IN FOOD LIST ------------------------
# Later you can add more products here, or load them from a file.
PRODUCTS = {
    "Breakfast Cereal": ["Whole Grain Wheat", "Sugar", "Salt", "BHT"],
    "Fast Food Bread Bun": ["Enriched Flour", "Water", "Azodicarbonamide", "Soybean Oil"],
    "Peanut Snack Bar": ["Peanuts", "Sugar", "Palm Oil", "Salt"],
    "Instant Noodles": ["Wheat Flour", "Palm Oil", "Salt", "Disodium Inosinate"],
}

# Ingredients we want to warn users about, and why.
WATCH_LIST = {
    "BHT": "A preservative linked to health concerns.",
    "Azodicarbonamide": "A dough conditioner linked to breathing issues.",
    "Disodium Inosinate": "A flavor enhancer, often hidden in processed foods.",
    "Palm Oil": "High in saturated fat.",
}

# Common allergens to flag.
ALLERGENS = ["Peanuts", "Wheat", "Soybean Oil", "Milk", "Egg"]

# ---- 2. PAGE SETUP ------------------------------------------
st.set_page_config(page_title="SafeBite", page_icon="🥗")
st.title("🥗 SafeBite")
st.subheader("Love your food. Trust your bite.")
st.write("Pick a product to see what is really inside it.")

st.divider()

# ---- 3. LET THE USER PICK A PRODUCT -------------------------
choice = st.selectbox("Choose a product:", list(PRODUCTS.keys()))

if st.button("Check ingredients"):
    ingredients = PRODUCTS[choice]

    st.write("### Ingredients")
    st.write(", ".join(ingredients))

    # ---- 4. CHECK FOR INGREDIENTS TO WATCH ------------------
    flagged = [i for i in ingredients if i in WATCH_LIST]
    if flagged:
        st.warning("Ingredients to watch out for:")
        for i in flagged:
            st.write(f"- **{i}**: {WATCH_LIST[i]}")
    else:
        st.success("No ingredients on our watch list. Looks clean!")

    # ---- 5. CHECK FOR ALLERGENS -----------------------------
    allergen_hits = [i for i in ingredients if i in ALLERGENS]
    if allergen_hits:
        st.error("Allergy alert: " + ", ".join(allergen_hits))

# ---- 6. SIDEBAR ---------------------------------------------
st.sidebar.header("About")
st.sidebar.write("SafeBite helps you understand the ingredients in the food you eat.")
