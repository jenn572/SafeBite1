# ============================================================
#  PureBites - Sprint 2
#  The user selects a product and sees its ingredients,
#  ingredient warnings, allergy alerts, and can browse a
#  full Ingredient Dictionary of harmful & healthy ingredients.
#
#  HOW TO RUN:
#     python3 -m pip install -r requirements.txt
#     python3 -m streamlit run app.py
# ============================================================

import base64
import hashlib
import html
import io
import json
import os
import re
import secrets
from datetime import datetime, timedelta

import psycopg2
import requests
from psycopg2.extras import RealDictCursor
from PIL import Image

import streamlit as st
import streamlit.components.v1 as components

# pyzbar needs a system library (libzbar0) that's installed via
# packages.txt on Streamlit Cloud. If it's missing, don't crash the
# whole app — just disable the barcode feature with a helpful message.
try:
    from pyzbar.pyzbar import decode as decode_barcode
    BARCODE_SCANNING_AVAILABLE = True
except Exception:
    BARCODE_SCANNING_AVAILABLE = False


# ---- 0. LOGO IMAGE (base64-encoded so it renders inline) -----

LOGO_PATH = os.path.join(os.path.dirname(__file__), "purebites_logo.webp")


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


# ---- 0.6 SPONSOR / AD SIDEBAR IMAGES --------------------------
# Small ad images shown in a fixed sidebar on the right-hand side of
# the screen. Each image links out to the sponsor's website. Like the
# logo above, these are base64-encoded so they render without needing
# a public image host — just drop the files next to app.py in the repo.

AD_ANNIES_PATH = os.path.join(os.path.dirname(__file__), "ad_annies.jpg")
AD_SKINNYPOP_PATH = os.path.join(os.path.dirname(__file__), "ad_skinnypop.jpeg")
AD_BELVITA_PATH = os.path.join(os.path.dirname(__file__), "ad_belvita.png")
AD_STONYFIELD_PATH = os.path.join(os.path.dirname(__file__), "ad_stonyfield.jpg")
AD_KINDBAR_PATH = os.path.join(os.path.dirname(__file__), "ad_kindbar.avif")


def _get_image_base64(path):
    """Same idea as _get_logo_base64: read an image file next to app.py
    and return it as base64. Returns None (and the ad is simply skipped)
    if the file isn't found, so a missing ad image never crashes the app."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None


# Each entry: the base64 image data, its MIME type (must match the
# actual file type), the destination URL, and alt text for accessibility.
AD_SIDEBAR_ADS = [
    {
        "base64": _get_image_base64(AD_ANNIES_PATH),
        "mime": "image/jpeg",
        "url": "https://www.annies.com/",
        "alt": "Annie's",
    },
    {
        "base64": _get_image_base64(AD_SKINNYPOP_PATH),
        "mime": "image/jpeg",
        "url": "https://www.hersheyland.com/skinnypop",
        "alt": "SkinnyPop",
    },
    {
        "base64": _get_image_base64(AD_BELVITA_PATH),
        "mime": "image/png",
        "url": "https://belvitastore.com/",
        "alt": "belVita",
    },
    {
        "base64": _get_image_base64(AD_STONYFIELD_PATH),
        "mime": "image/jpeg",
        "url": (
            "https://www.stonyfield.com/products/whole-milk-probiotic-yogurt-vanilla-32-oz/"
            "?gclsrc=aw.ds&gad_source=1&gad_campaignid=19421618393"
            "&gbraid=0AAAAAC1KvtbZhhPfhp-wEfHYvOIGFk3k7"
            "&gclid=Cj0KCQjw-MDTBhCgARIsAKAkdlTlog35q-MaPE82lHwtxJ9GVaBtZ9C_qheqUXi5CA02oxHby8vJlvQaAhBoEALw_wcB"
        ),
        "alt": "Stonyfield Organic",
    },
    {
        "base64": _get_image_base64(AD_KINDBAR_PATH),
        "mime": "image/avif",
        "url": (
            "https://www.kindsnacks.com/search?q=breakfast+protein&lang=en_US"
            "&gad_source=1&gad_campaignid=20627637314"
            "&gbraid=0AAAAADpgMU2SSrbuTOEaBMbt-EZc9hGuf"
            "&gclid=Cj0KCQjwm8bTBhDWARIsAC9Hi8n_OQmUeHFRitLzywm7f6fdVgI4B09_0V9OMYRRqeU-Nyv2XfdBi4gaAtbDEALw_wcB"
        ),
        "alt": "KIND Breakfast Protein Bar",
    },
]


def render_ad_sidebar():
    """Renders the fixed right-hand ad sidebar. Because this is called
    once, outside of any st.tabs() block, and uses CSS position:fixed,
    it stays on screen no matter which tab the user is on and can't be
    dismissed/closed. Ads with a missing image file are silently
    skipped rather than breaking the whole sidebar."""
    cards_html = ""
    for ad in AD_SIDEBAR_ADS:
        if not ad["base64"]:
            continue
        cards_html += (
            f'<a class="purebites-ad-card" href="{ad["url"]}" '
            f'target="_blank" rel="noopener noreferrer">'
            f'<img src="data:{ad["mime"]};base64,{ad["base64"]}" alt="{html.escape(ad["alt"])}">'
            f'</a>'
        )

    if not cards_html:
        return  # none of the ad images were found on disk — skip quietly

    st.markdown(
        f"""
        <div class="purebites-ad-sidebar">
            <div class="purebites-ad-sidebar-title">🌿 Our Partners</div>
            {cards_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---- 0.7 AI HELPER (floating chat bubble) ----------------------
# A small floating chat widget, bottom-right corner, on every tab.
# Uses the free tier of Google's Gemini API. If no GEMINI_API_KEY
# secret is configured, the widget still renders but replies with a
# friendly setup message instead of crashing the app.

GEMINI_MODEL = "gemini-3.1-flash-lite"

AI_HELPER_SYSTEM_INSTRUCTION = (
    "You are the PureBites AI Helper, a friendly nutrition and food-"
    "ingredient assistant built into a grocery food-scanning app. "
    "Answer questions about ingredients, nutrition claims, and food "
    "safety clearly and concisely (2-4 short sentences, plain "
    "language, no medical jargon). You are not a doctor: for "
    "questions about a specific person's health risk (e.g. 'can my "
    "toddler eat this', allergies, medical conditions), give general "
    "food-safety information but also remind the user to check with "
    "a pediatrician, doctor, or dietitian for anything specific to "
    "their situation. Stay focused on food, nutrition, and "
    "ingredients."
)


def ask_ai_helper(question, user_context=""):
    """Sends a question to the Gemini API and returns the reply text.

    Fails soft: if the API key is missing or the request errors out,
    returns a friendly message instead of raising, so a flaky network
    call never crashes the rest of the app.
    """
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        return (
            "The AI Helper isn't fully set up yet — ask the app owner "
            "to add a GEMINI_API_KEY secret in Streamlit Cloud settings."
        )

    system_instruction = AI_HELPER_SYSTEM_INSTRUCTION
    if user_context:
        system_instruction += " " + user_context

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except requests.exceptions.HTTPError:
        # Log the response body (Google's actual error message, e.g. bad
        # key, region-blocked, model not found) to Streamlit Cloud's app
        # logs, viewable via "Manage app" — without exposing it to users.
        print(f"[ai_helper] Gemini HTTP error {resp.status_code}: {resp.text}", flush=True)
        return (
            "Sorry, I couldn't get an answer just now — please try "
            "again in a moment."
        )
    except Exception as e:
        print(f"[ai_helper] Gemini request failed: {type(e).__name__}: {e}", flush=True)
        return (
            "Sorry, I couldn't get an answer just now — please try "
            "again in a moment."
        )


def render_ai_helper():
    """Renders the floating AI Helper chat bubble + panel. Called once,
    outside of st.tabs(), so (like the ad sidebar) it stays fixed to
    the bottom-right corner of the screen no matter which tab the user
    is on. Requires Streamlit 1.34+ for st.container(key=...) to emit
    a CSS-targetable class."""

    if "ai_chat_open" not in st.session_state:
        st.session_state.ai_chat_open = False
    if "ai_chat_messages" not in st.session_state:
        st.session_state.ai_chat_messages = []

    with st.container(key="ai_helper_bubble"):
        icon = "✕" if st.session_state.ai_chat_open else "💬"
        if st.button(icon, key="ai_helper_toggle"):
            st.session_state.ai_chat_open = not st.session_state.ai_chat_open
            st.rerun()

    if not st.session_state.ai_chat_open:
        return

    with st.container(key="ai_helper_panel"):
        st.markdown(
            '<div class="ai-helper-title">🌿 PureBites AI Helper</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Ask about ingredients, nutrition, or food safety. "
            "Educational only — not medical advice."
        )

        for msg in st.session_state.ai_chat_messages[-8:]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        with st.form(key="ai_helper_form", clear_on_submit=True):
            question = st.text_input(
                "Ask a question",
                key="ai_helper_question",
                label_visibility="collapsed",
                placeholder="e.g. Is Greek yogurt healthier?",
            )
            submitted = st.form_submit_button("Send")

        if submitted and question.strip():
            st.session_state.ai_chat_messages.append(
                {"role": "user", "content": question.strip()}
            )

            context = ""
            current = st.session_state.get("auth_user")
            if current and not is_guest_user(current):
                allergies = get_user_allergies(current)
                dietary = get_user_dietary_restrictions(current)
                if allergies:
                    context += f" The user has these allergies: {', '.join(allergies)}."
                if dietary:
                    context += (
                        " The user follows these dietary restrictions: "
                        f"{', '.join(dietary)}."
                    )

            with st.spinner("Thinking..."):
                answer = ask_ai_helper(question.strip(), context)

            st.session_state.ai_chat_messages.append(
                {"role": "assistant", "content": answer}
            )
            st.rerun()


# ---- 0.5 ACCOUNT DATABASE -------------------------------------
# Accounts are stored in a hosted Postgres database (Supabase) instead
# of a local file, so they survive redeploys and app restarts. The
# connection string lives in Streamlit's secrets manager, never in
# the code itself.

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

STARTING_SCAN_COUNT = 0  # new accounts start with 0 scans

if "DATABASE_URL" not in st.secrets:
    st.error(
        "Database isn't configured yet. Add a DATABASE_URL secret in "
        "Streamlit Cloud → your app → Settings → Secrets."
    )
    st.stop()


def get_db_connection():
    """Open a fresh connection to the Postgres database. Each function
    below opens one, uses it briefly, and closes it — this matches how
    Supabase's Session pooler connection string is meant to be used."""
    return psycopg2.connect(st.secrets["DATABASE_URL"], cursor_factory=RealDictCursor)


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            scan_count INTEGER DEFAULT 0,
            streak_count INTEGER DEFAULT 0,
            last_login_date TEXT,
            allergies TEXT DEFAULT '[]',
            dietary_restrictions TEXT DEFAULT '[]',
            profile_picture TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    # Migration-safe: adds these columns if an older version of the
    # table already exists without them. Postgres supports "IF NOT
    # EXISTS" directly on ADD COLUMN, unlike SQLite.
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS streak_count INTEGER DEFAULT 0")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_date TEXT")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS allergies TEXT DEFAULT '[]'")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS dietary_restrictions TEXT DEFAULT '[]'")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_picture TEXT")
    conn.commit()
    cur.close()
    conn.close()


@st.cache_resource
def _ensure_schema():
    """Run init_db() only once per running app (not on every rerun) —
    st.cache_resource keeps this from hitting the database on every
    single click."""
    init_db()
    return True


_ensure_schema()


def is_valid_email(email):
    return bool(EMAIL_PATTERN.match(email.strip()))


PASSWORD_REQUIREMENTS_TEXT = (
    "Password must have a minimum of 6 characters, 1 symbol, and 1 number"
)


def is_strong_password(password):
    """At least 6 characters, at least one digit, at least one symbol."""
    if len(password) < 6:
        return False
    has_digit = any(ch.isdigit() for ch in password)
    has_symbol = any(not ch.isalnum() for ch in password)
    return has_digit and has_symbol


def hash_password(password, salt=None):
    """Salt + hash a password with PBKDF2-SHA256. Never store plain text."""
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
    ).hex()
    return salt, pwd_hash


def get_user(email):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email.strip().lower(),))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return dict(row)


def create_user(email, password, name):
    email = email.strip().lower()
    salt, pwd_hash = hash_password(password)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (email, name, salt, password_hash, scan_count, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (
            email,
            name.strip(),
            salt,
            pwd_hash,
            STARTING_SCAN_COUNT,
            datetime.now().strftime("%B %Y"),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def verify_login(email, password):
    user = get_user(email)
    if not user:
        return None
    _, pwd_hash = hash_password(password, salt=user["salt"])
    if secrets.compare_digest(pwd_hash, user["password_hash"]):
        return user
    return None


def get_client_local_date():
    """Best-effort local calendar date for the person using the app
    right now, based on their browser's timezone offset
    (st.context.timezone_offset — minutes, positive when the browser
    is behind UTC). Falls back to the server's UTC date if that isn't
    available. Streamlit Cloud always runs the app in UTC, so without
    this, an evening login from anyone west of UTC can already land on
    "tomorrow" server-side — making the next real day's login look
    like the same day (streak doesn't move) or a 2-day gap (streak
    resets to 1) purely because of the clock mismatch, not an actual
    missed day."""
    try:
        offset_minutes = st.context.timezone_offset
    except Exception:
        offset_minutes = None
    utc_now = datetime.utcnow()
    if offset_minutes is None:
        return utc_now.date()
    return (utc_now - timedelta(minutes=offset_minutes)).date()


def record_login_streak(email):
    """Update (and return) the user's daily login streak.

    - Logging in again on the same day doesn't change the streak.
    - Logging in exactly one day after the last login adds a day.
    - Logging in after a gap of more than one day resets the streak to 1.
    - A first-ever login (e.g. right after sign up) starts the streak at 1.

    "Day" is judged by the person's own browser timezone (see
    get_client_local_date), not the server's UTC clock.
    """
    user = get_user(email)
    today = get_client_local_date()
    today_str = today.strftime("%Y-%m-%d")
    last_login = user["last_login_date"]
    streak = user["streak_count"] or 0

    if last_login == today_str:
        new_streak = streak if streak else 1
    elif last_login:
        last_date = datetime.strptime(last_login, "%Y-%m-%d").date()
        gap_days = (today - last_date).days
        new_streak = streak + 1 if gap_days == 1 else 1
    else:
        new_streak = 1

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET streak_count = %s, last_login_date = %s WHERE email = %s",
        (new_streak, today_str, email.strip().lower()),
    )
    conn.commit()
    cur.close()
    conn.close()

    user["streak_count"] = new_streak
    user["last_login_date"] = today_str
    return user


def update_scan_count(email, new_count):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET scan_count = %s WHERE email = %s",
        (new_count, email.strip().lower()),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_user_allergies(user):
    """Parse a user's stored allergies (JSON text) into a Python list."""
    try:
        return json.loads(user["allergies"]) if user["allergies"] else []
    except (TypeError, ValueError):
        return []


def update_user_allergies(email, allergies_list):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET allergies = %s WHERE email = %s",
        (json.dumps(allergies_list), email.strip().lower()),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_user_dietary_restrictions(user):
    """Parse a user's stored dietary restrictions (JSON text) into a
    Python list."""
    try:
        return (
            json.loads(user["dietary_restrictions"])
            if user.get("dietary_restrictions")
            else []
        )
    except (TypeError, ValueError):
        return []


def update_user_dietary_restrictions(email, restrictions_list):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET dietary_restrictions = %s WHERE email = %s",
        (json.dumps(restrictions_list), email.strip().lower()),
    )
    conn.commit()
    cur.close()
    conn.close()


def update_profile_picture(email, picture_base64):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET profile_picture = %s WHERE email = %s",
        (picture_base64, email.strip().lower()),
    )
    conn.commit()
    cur.close()
    conn.close()


def process_profile_picture(uploaded_file):
    """Resize an uploaded image down to a small square-ish thumbnail and
    return it as a base64 JPEG string, so the database stays lightweight."""
    image = Image.open(uploaded_file).convert("RGB")
    image.thumbnail((320, 320))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode()



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

# A food-specific emoji for each sample product, used in place of the
# generic package emoji when showing scan results.
PRODUCT_EMOJIS = {
    "Breakfast Cereal": "🥣",
    "Fast Food Bread Bun": "🍞",
    "Peanut Snack Bar": "🥜",
    "Instant Noodles": "🍜",
    "Greek Yogurt": "🥛",
    "Mixed Nuts Trail Mix": "🌰",
    "Frozen Pizza": "🍕",
    "Fruit Juice": "🧃",
    "Ice Cream": "🍦",
    "Canned Soup": "🥫",
    "Flavored Chips": "🥔",
    "Chocolate Chip Cookies": "🍪",
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
        "type": "moderate",
        "explanation": "A flavor enhancer often paired with MSG to make "
                        "savory foods taste richer.",
        "concern": "Usually made from meat or fish, so it isn't vegetarian-"
                    "friendly, and can cause reactions in sensitive people.",
    },
    "Palm Oil": {
        "type": "moderate",
        "explanation": "A cheap vegetable oil used to add texture and "
                        "shelf life to processed snacks.",
        "concern": "High in saturated fat, which can raise cholesterol "
                    "if eaten often.",
    },
    "Sugar": {
        "type": "moderate",
        "explanation": "A sweetener added to make food taste better, "
                        "often in larger amounts than people realize.",
        "concern": "Eating too much added sugar is linked to weight gain, "
                    "energy crashes, and long-term health risks.",
    },
    "Salt": {
        "type": "moderate",
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
        "type": "moderate",
        "explanation": "A flavor enhancer that makes savory foods taste "
                        "more intense.",
        "concern": "Considered safe in moderation by most health bodies, "
                    "but can trigger headaches or discomfort in sensitive "
                    "people.",
    },
    "Excess Sodium": {
        "type": "moderate",
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
        "type": "moderate",
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
        "type": "moderate",
        "explanation": "Sugar added during processing rather than "
                        "occurring naturally in the food.",
        "concern": "Regularly eating extra added sugar is tied to weight "
                    "gain and other long-term health risks.",
    },
    "Corn Syrup": {
        "type": "moderate",
        "explanation": "A sweet syrup made from corn starch, used to "
                        "sweeten and add texture to processed foods.",
        "concern": "Adds extra sugar and calories with little "
                    "nutritional value.",
    },
    "Carrageenan": {
        "type": "moderate",
        "explanation": "A thickener extracted from red seaweed, used to "
                        "give creamy foods a smooth texture.",
        "concern": "Considered safe by most regulators, but some people "
                    "prefer to avoid it due to possible digestive "
                    "irritation.",
    },
    "Mono- and Diglycerides": {
        "type": "moderate",
        "explanation": "Emulsifiers that help keep water and fat blended "
                        "together in foods like ice cream and baked goods.",
        "concern": "Generally recognized as safe, though small amounts "
                    "can be derived from trans fats.",
    },
    "Modified Food Starch": {
        "type": "moderate",
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

    # ---------------- MPH FOOD ADDITIVES LIST ----------------
    "Sodium Nitrate": {
        "type": "harmful",
        "explanation": "A preservative added to processed meats like bacon, hot dogs, and deli meats to stop bacterial growth and keep the color pink.",
        "concern": "Linked to cancer risk in humans, especially with regular consumption of processed meats.",
    },
    "Sulfites": {
        "type": "moderate",
        "explanation": "A group of preservatives used to keep prepared and dried foods looking fresh and prevent browning.",
        "concern": "Can cause breathing difficulties in people who are sensitive to sulfites, such as some asthma sufferers.",
    },
    "Potassium Bromate": {
        "type": "harmful",
        "explanation": "An additive used in some breads to help the dough rise higher and give it more volume.",
        "concern": "Linked to cancer in humans; banned as a food additive in several countries.",
    },
    "Propyl Gallate": {
        "type": "harmful",
        "explanation": "A preservative added to fat-containing foods like meats, popcorn, and soup mixes to keep them from spoiling.",
        "concern": "Shown to cause cancer in animal studies and is banned in some countries, though still considered safe by the FDA.",
    },
    "BHA": {
        "type": "harmful",
        "explanation": "A synthetic preservative, often paired with BHT, used to keep oils and fats in packaged food from going bad too quickly.",
        "concern": "Linked to cancerous tumor growth in some animal studies.",
    },
    "Propylene Glycol": {
        "type": "moderate",
        "explanation": "A thickener related to antifreeze that's used to keep dairy products and salad dressings smooth and blended.",
        "concern": "Considered 'generally safe' by the FDA, though some prefer to avoid it given its industrial origins.",
    },
    "Butane": {
        "type": "harmful",
        "explanation": "A gas sometimes used in processing chicken nuggets and other foods to help keep them tasting fresh.",
        "concern": "A known carcinogen.",
    },
    "Disodium Guanylate": {
        "type": "moderate",
        "explanation": "A flavor enhancer often used alongside MSG in snack foods to make savory flavors taste richer.",
        "concern": "Contains MSG, which can cause reactions in people sensitive to it.",
    },
    "Enriched Flour": {
        "type": "moderate",
        "explanation": "Refined wheat flour that's had synthetic vitamins and minerals added back in after processing strips out the bran and germ.",
        "concern": "Lower in fiber and nutrients than whole grain flour, and digests into sugar more quickly.",
    },
    "Recombinant Bovine Growth Hormone (rBGH)": {
        "type": "harmful",
        "explanation": "A genetically-engineered version of a natural growth hormone given to cows to boost milk production.",
        "concern": "Raises IGF-1 levels in milk, which some research links to increased cancer risk.",
    },
    "Refined Vegetable Oil": {
        "type": "moderate",
        "explanation": "Heavily processed oils like soybean, corn, safflower, canola, and peanut oil, common in packaged and fried foods.",
        "concern": "High in omega-6 fats, which in excess are thought to contribute to heart disease and inflammation.",
    },
    "Sodium Benzoate": {
        "type": "harmful",
        "explanation": "A preservative used in salad dressings and carbonated beverages to stop mold and bacteria from growing.",
        "concern": "Considered a carcinogen by some researchers and may cause DNA damage in combination with vitamin C.",
    },
    "Brominated Vegetable Oil": {
        "type": "harmful",
        "explanation": "An additive used to keep citrus flavor oils evenly mixed into soft drinks instead of separating.",
        "concern": "Contains bromine, which can build up in the body and cause organ damage; not required to be listed on food labels in some regions.",
    },
    "Olestra": {
        "type": "moderate",
        "explanation": "A fat substitute used in some snack foods that passes through the body unabsorbed.",
        "concern": "Can cause digestive discomfort and interferes with the absorption of some vitamins.",
    },
    "Polysorbate 60": {
        "type": "harmful",
        "explanation": "A thickener and emulsifier used to keep baked goods and other foods smooth and well-blended.",
        "concern": "Linked to cancer in laboratory animal studies.",
    },
    "Carnauba Wax": {
        "type": "harmful",
        "explanation": "A wax from palm leaves used to give chewing gum and candy a glossy coating.",
        "concern": "Some studies link high exposure to tumor growth.",
    },
    "Magnesium Sulphate": {
        "type": "harmful",
        "explanation": "A mineral compound sometimes used in tofu processing.",
        "concern": "Linked to cancer in laboratory animal studies.",
    },
    "Chlorine Dioxide": {
        "type": "harmful",
        "explanation": "A bleaching agent used to whiten flour.",
        "concern": "Linked to tumor growth and hyperactivity in children in some studies.",
    },
    "Paraben": {
        "type": "harmful",
        "explanation": "A preservative used to stop mold and yeast from growing in packaged foods.",
        "concern": "Can disrupt hormones in the body and has been studied for a possible link to breast cancer.",
    },
    "Sodium Carboxymethyl Cellulose": {
        "type": "moderate",
        "explanation": "A thickener used in salad dressings and other processed foods to give them body.",
        "concern": "May carry cancer risk in very high quantities, though typical food-use levels are considered low-risk.",
    },
    "Aluminum": {
        "type": "harmful",
        "explanation": "A metal sometimes used as a preservative in packaged and processed foods.",
        "concern": "Linked to cancer risk with regular high exposure.",
    },
    "Saccharin": {
        "type": "harmful",
        "explanation": "An artificial sweetener hundreds of times sweeter than sugar, used in diet products.",
        "concern": "Found to cause bladder cancer in rat studies.",
    },
    "Aspartame": {
        "type": "harmful",
        "explanation": "An artificial sweetener widely used in diet sodas and sugar-free products.",
        "concern": "Considered an excitotoxin by some researchers and linked to dizziness, headaches, blurred vision, and stomach problems.",
    },
    "Acesulfame Potassium": {
        "type": "harmful",
        "explanation": "An artificial sweetener often blended with other sweeteners in diet sodas and ice cream.",
        "concern": "Linked to lung and breast tumors in rat studies.",
    },
    "Sucralose": {
        "type": "harmful",
        "explanation": "An artificial sweetener (brand name Splenda) made by chemically altering sugar.",
        "concern": "Linked to liver and kidney swelling and thymus gland shrinkage in animal studies.",
    },
    "Agave Nectar": {
        "type": "moderate",
        "explanation": "A sweetener derived from the agave cactus, often marketed as a 'natural' alternative to sugar.",
        "concern": "Very high in fructose, which in excess is linked to insulin resistance, liver strain, and inflammation.",
    },
    "Bleached Starch": {
        "type": "moderate",
        "explanation": "A chemically treated starch used as a thickener in some dairy products.",
        "concern": "Some researchers link it to asthma and skin irritation.",
    },
    "Tert-Butylhydroquinone (TBHQ)": {
        "type": "harmful",
        "explanation": "A synthetic preservative used to keep fish and other products from spoiling.",
        "concern": "Linked to stomach tumors in animal studies at high doses.",
    },
    "Blue 1": {
        "type": "harmful",
        "explanation": "A synthetic blue dye used in bakery products, candy, and soft drinks.",
        "concern": "Some studies link it to chromosome damage and cancer risk.",
    },
    "Blue 2": {
        "type": "harmful",
        "explanation": "A synthetic blue dye used in candy and pet food.",
        "concern": "Some studies link it to brain tumor development.",
    },
    "Citrus Red 1": {
        "type": "harmful",
        "explanation": "A dye sprayed on orange peels to make the fruit look more ripe.",
        "concern": "Some studies link it to chromosome damage and cancer risk.",
    },
    "Citrus Red 2": {
        "type": "harmful",
        "explanation": "A dye used to color orange peels.",
        "concern": "Linked to cancer risk if the peel itself is eaten.",
    },
    "Green 3": {
        "type": "harmful",
        "explanation": "A synthetic green dye used in candy and beverages.",
        "concern": "Some studies link it to bladder tumor development.",
    },
    "Yellow 5": {
        "type": "harmful",
        "explanation": "A synthetic yellow dye used in desserts, candy, and baked goods.",
        "concern": "Some studies link it to kidney tumor development.",
    },
    "Red 2": {
        "type": "harmful",
        "explanation": "A synthetic red food coloring.",
        "concern": "Some studies link it to asthma and cancer risk.",
    },
    "Red 3": {
        "type": "harmful",
        "explanation": "A synthetic red dye added to cherry pie filling, ice cream, and baked goods.",
        "concern": "Linked to nerve damage and thyroid cancer in some studies.",
    },
    "Caramel Coloring": {
        "type": "moderate",
        "explanation": "A common coloring used in soft drinks, sauces, pastries, and breads.",
        "concern": "When manufactured using ammonia, it can carry cancer risk in animal studies; companies aren't always required to disclose which method was used.",
    },
    "Brown HT": {
        "type": "harmful",
        "explanation": "A synthetic dye used in various packaged foods.",
        "concern": "Some studies link it to hyperactivity in children, asthma, and cancer risk.",
    },
    "Orange B": {
        "type": "moderate",
        "explanation": "A food dye used in hot dog and sausage casings.",
        "concern": "High doses have been linked to liver and bile duct strain.",
    },
    "Bixin": {
        "type": "moderate",
        "explanation": "A natural-origin food coloring used to give foods an orange-yellow hue.",
        "concern": "Some studies link it to hyperactivity in children and asthma.",
    },
    "Norbixin": {
        "type": "moderate",
        "explanation": "A natural-origin food coloring related to Bixin.",
        "concern": "Some studies link it to hyperactivity in children and asthma.",
    },
    "Annatto": {
        "type": "moderate",
        "explanation": "A natural food coloring derived from achiote tree seeds.",
        "concern": "Some studies link it to hyperactivity in children and asthma.",
    },
}

# Kept separate for the ingredient-check logic on the Scan page.
# Three tiers: clearly harmful (bigger score hit), moderate/"semi-harmful"
# (a smaller hit — common ingredients that are only a concern in excess,
# like sugar, salt, or palm oil), and healthy.
WATCH_LIST = {
    name: data["concern"]
    for name, data in INGREDIENT_DICTIONARY.items()
    if data["type"] == "harmful"
}

MODERATE_LIST = {
    name: data["concern"]
    for name, data in INGREDIENT_DICTIONARY.items()
    if data["type"] == "moderate"
}

HEALTHY_HIGHLIGHTS = {
    name: data["concern"]
    for name, data in INGREDIENT_DICTIONARY.items()
    if data["type"] == "healthy"
}

# Common allergens to flag (used by the general product allergen check).
ALLERGENS = [
    "Peanuts",
    "Wheat",
    "Soybean Oil",
    "Milk",
    "Egg",
    "Almonds",
    "Walnuts",
]

# ---- 2.5 PERSONAL ALLERGY PROFILE ----------------------------
# The full list of common allergens a user can pick from on their
# profile page.

COMMON_ALLERGENS = [
    "Milk", "Eggs", "Peanuts", "Tree Nuts", "Almonds", "Walnuts", "Cashews",
    "Pecans", "Pistachios", "Hazelnuts", "Macadamia Nuts", "Brazil Nuts",
    "Wheat", "Soy", "Fish", "Shellfish", "Shrimp", "Crab", "Lobster",
    "Scallops", "Clams", "Mussels", "Oysters", "Sesame", "Corn", "Mustard",
    "Celery", "Lupin", "Sulfites", "Oats", "Rye", "Barley", "Gluten",
    "Coconut", "Sunflower Seeds", "Chickpeas", "Lentils", "Peas", "Beans",
    "Tomatoes", "Strawberries", "Kiwi", "Bananas", "Avocado", "Pineapple",
    "Peaches", "Apples", "Citrus", "Mango", "Garlic", "Onion", "Chocolate",
    "Cocoa", "Coffee", "Vanilla", "Yeast", "Beef", "Chicken", "Pork",
    "Turkey", "Gelatin",
]

# A couple of the options above are umbrella categories that group
# several more specific items right below them in the list — when a
# user selects the umbrella term, treat the specific items as covered
# too when scanning a product.
DIETARY_RESTRICTION_OPTIONS = [
    "Vegan", "Vegetarian", "Pescatarian", "Halal", "Kosher",
    "Gluten-Free", "Dairy-Free", "Low-Sodium", "Diabetic-Friendly",
    "Low-Sugar", "Keto", "Paleo", "Low-Carb", "Non-GMO", "Organic Only",
]

ALLERGY_CATEGORY_EXPANSIONS = {
    "Tree Nuts": [
        "Almonds", "Walnuts", "Cashews", "Pecans", "Pistachios",
        "Hazelnuts", "Macadamia Nuts", "Brazil Nuts",
    ],
    "Shellfish": [
        "Shrimp", "Crab", "Lobster", "Scallops", "Clams", "Mussels",
        "Oysters",
    ],
}


def find_matching_allergens(ingredients, user_allergies):
    """Return which of the user's saved allergies show up in this
    product's ingredient list (case-insensitive, matching either
    direction so e.g. "Wheat" matches an ingredient like "Wheat Flour").
    """
    if not user_allergies:
        return []

    ingredients_lower = [i.lower() for i in ingredients]
    matched = []
    for allergy in user_allergies:
        terms = [allergy] + ALLERGY_CATEGORY_EXPANSIONS.get(allergy, [])
        terms_lower = [t.lower() for t in terms]
        hit = any(
            term in ing or ing in term
            for term in terms_lower
            for ing in ingredients_lower
        )
        if hit:
            matched.append(allergy)
    return matched


# ---- 2.55 PERSONAL DIETARY RESTRICTION CONFLICTS ---------------
# For each dietary restriction option, the ingredient keywords that
# would conflict with it (matched the same case-insensitive,
# either-direction way as allergies above).
DIETARY_RESTRICTION_INGREDIENT_FLAGS = {
    "Vegan": [
        "Milk", "Cream", "Egg Yolks", "Eggs", "Honey", "Butter", "Cheese",
        "Mozzarella Cheese", "Whey", "Gelatin", "Yogurt",
    ],
    "Vegetarian": ["Beef", "Chicken", "Pork", "Turkey", "Gelatin", "Fish"],
    "Pescatarian": ["Beef", "Chicken", "Pork", "Turkey", "Gelatin"],
    "Halal": ["Pork", "Gelatin"],
    "Kosher": [
        "Pork", "Shellfish", "Shrimp", "Crab", "Lobster", "Scallops",
        "Clams", "Mussels", "Oysters",
    ],
    "Gluten-Free": [
        "Wheat", "Wheat Flour", "Whole Grain Wheat", "Whole Wheat Flour",
        "Whole Wheat Crust", "Enriched Flour", "Refined White Flour",
        "Oats", "Rye", "Barley", "Bleached Starch",
    ],
    "Dairy-Free": [
        "Milk", "Cream", "Butter", "Cheese", "Mozzarella Cheese", "Whey",
    ],
    "Low-Sodium": [
        "Salt", "Sea Salt", "Excess Sodium", "Sodium Nitrite",
        "Sodium Nitrate", "Sodium Benzoate",
        "Sodium Carboxymethyl Cellulose", "Disodium Inosinate",
        "Disodium Guanylate",
    ],
    "Diabetic-Friendly": [
        "Sugar", "Added Sugar", "High Fructose Corn Syrup", "Corn Syrup",
        "Agave Nectar", "Honey",
    ],
    "Low-Sugar": [
        "Sugar", "Added Sugar", "High Fructose Corn Syrup", "Corn Syrup",
        "Agave Nectar",
    ],
    "Keto": [
        "Sugar", "Added Sugar", "High Fructose Corn Syrup", "Corn Syrup",
        "Wheat Flour", "Whole Wheat Flour", "Enriched Flour", "Oats",
        "Honey", "Agave Nectar",
    ],
    "Paleo": [
        "Sugar", "Wheat Flour", "Enriched Flour", "Oats", "Beans",
        "Lentils", "Milk", "Cheese", "Corn Syrup",
        "Monosodium Glutamate (MSG)",
    ],
    "Low-Carb": [
        "Sugar", "Wheat Flour", "Enriched Flour", "Oats", "Corn Syrup",
        "High Fructose Corn Syrup",
    ],
    "Non-GMO": [
        "High Fructose Corn Syrup", "Soybean Oil", "Corn Syrup",
        "Modified Food Starch",
    ],
    "Organic Only": [],
}

# Nutrition-based thresholds, checked only when real nutrition facts
# are available (i.e. for barcode-scanned products, not the sample
# dropdown items which have no nutrition data). Values are grams per
# 100g, based on the UK FSA's public "high" traffic-light bands —
# the same bands already used in compute_health_score above.
DIETARY_RESTRICTION_NUTRITION_FLAGS = {
    "Low-Sugar": ("sugar_100g", 22.5, "high sugar"),
    "Diabetic-Friendly": ("sugar_100g", 22.5, "high sugar"),
    "Keto": ("sugar_100g", 22.5, "high sugar"),
    "Low-Carb": ("sugar_100g", 22.5, "high sugar"),
    "Low-Sodium": ("sodium_100g", 0.6, "high sodium"),
}


def find_matching_dietary_conflicts(ingredients, user_restrictions, nutrition=None):
    """Return (restriction, reason) pairs for each of the user's saved
    dietary restrictions that this product conflicts with.

    Checks ingredient keywords first (e.g. "Milk" conflicts with
    "Vegan"), then falls back to nutrition thresholds when real
    nutrition facts are available (e.g. high sugar conflicting with
    "Low-Sugar" even if no ingredient explicitly says "Sugar")."""
    if not user_restrictions:
        return []

    ingredients_lower = [i.lower() for i in ingredients]
    nutrition = nutrition or {}
    conflicts = []

    for restriction in user_restrictions:
        reason = None

        for term in DIETARY_RESTRICTION_INGREDIENT_FLAGS.get(restriction, []):
            term_lower = term.lower()
            if any(term_lower in ing or ing in term_lower for ing in ingredients_lower):
                reason = term
                break

        if not reason and restriction in DIETARY_RESTRICTION_NUTRITION_FLAGS:
            nutrient_key, threshold, label = DIETARY_RESTRICTION_NUTRITION_FLAGS[restriction]
            value = nutrition.get(nutrient_key)
            if value is not None and value > threshold:
                reason = label

        if reason:
            conflicts.append((restriction, reason))

    return conflicts


def render_warning_banner(allergy_matches, dietary_conflicts):
    """Render the same pulsing red warning banner for personal allergy
    matches and/or dietary restriction conflicts found in a scanned
    product. Renders nothing if there's nothing to warn about."""
    if not allergy_matches and not dietary_conflicts:
        return

    lines = []
    if allergy_matches:
        matches_text = ", ".join(html.escape(a) for a in allergy_matches)
        lines.append(f"⚠️ allergy warning<br>this product contains: {matches_text}")
    if dietary_conflicts:
        conflicts_text = ", ".join(
            f"{html.escape(restriction)} ({html.escape(reason)})"
            for restriction, reason in dietary_conflicts
        )
        lines.append(
            f"⚠️ dietary restriction warning<br>conflicts with: {conflicts_text}"
        )

    st.markdown(
        f"""
        <div class="allergy-warning-banner">
            {"<br><br>".join(lines)}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---- 2.6 BARCODE SCANNING (real products via Open Food Facts) ----

def decode_barcode_image(uploaded_photo):
    """Try to read a barcode out of a photo. Returns the barcode number
    as a string, or None if no barcode could be found."""
    image = Image.open(uploaded_photo).convert("RGB")
    decoded_objects = decode_barcode(image)
    if not decoded_objects:
        return None
    return decoded_objects[0].data.decode("utf-8")


OPENFOODFACTS_HEADERS = {
    # Open Food Facts asks API clients to identify themselves — requests
    # without a real User-Agent can be throttled or rejected.
    "User-Agent": "PureBites-StreamlitApp/1.0 (educational project)"
}


@st.cache_data(ttl=86400, show_spinner=False)
def translate_to_english(text, source_lang):
    """Translate ingredient text to English using the free MyMemory API.

    Many products on Open Food Facts only have their ingredient list in
    the language it was originally submitted in (French, German, etc.),
    with no English version available. Without translating, ingredients
    show up in that original language AND fail to match anything in our
    English ingredient dictionary — so harmful/moderate/healthy
    ingredients silently go undetected.

    Returns (translated_text, was_translated). On any failure (network
    issue, rate limit, etc.) it falls back to the original text rather
    than breaking the scan."""
    if not text or not source_lang or source_lang == "en":
        return text, False
    try:
        response = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text[:490], "langpair": f"{source_lang}|en"},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
        translated = data.get("responseData", {}).get("translatedText")
        if translated and translated.strip():
            return translated, True
    except (requests.RequestException, ValueError):
        pass
    return text, False


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_openfoodfacts_product(barcode):
    """A single raw lookup against Open Food Facts for one exact barcode.
    Returns (product_dict, None) on success, (None, None) if the barcode
    genuinely isn't in the database, or (None, error_message) if the
    request itself failed (network, timeout, bad response, etc.)."""
    try:
        response = requests.get(
            f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json",
            headers=OPENFOODFACTS_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return None, f"Request failed: {exc}"
    except ValueError as exc:
        return None, f"Couldn't parse the response: {exc}"

    if data.get("status") != 1:
        return None, None
    return data.get("product", {}), None


def _barcode_variants(barcode):
    """Open Food Facts mostly stores barcodes as 13-digit EAN-13, but
    many US products scan as 12-digit UPC-A. Without trying both forms,
    a real, well-known product can wrongly come back as "not found"
    just because of this formatting difference."""
    variants = [barcode]
    if len(barcode) == 12:
        variants.append("0" + barcode)  # UPC-A -> EAN-13
    if len(barcode) == 13 and barcode.startswith("0"):
        variants.append(barcode[1:])  # EAN-13 -> UPC-A

    seen = set()
    unique_variants = []
    for candidate in variants:
        if candidate not in seen:
            unique_variants.append(candidate)
            seen.add(candidate)
    return unique_variants


def _build_scan_result(product, matched_barcode, translate_ingredients=True):
    """Turn a raw Open Food Facts product dict into the result shape
    the rest of the app works with (name, ingredients, nutrition,
    category, etc). Shared by a direct barcode lookup and by the
    healthier-alternatives search below, so both produce identical,
    fully-detailed product cards.

    translate_ingredients=False skips the (slower, per-product) call
    to translate_to_english — used when scoring many alternative
    candidates at once, where only ones with existing English text
    are usable anyway."""
    name = (
        product.get("product_name")
        or product.get("product_name_en")
        or "Unknown product"
    )

    # Open Food Facts often only has an ingredients list in whatever
    # language the product was originally submitted in. Prefer an
    # English version if one exists; otherwise translate the original
    # text to English so ingredients both display in English and can
    # be matched against our (English) ingredient dictionary.
    source_lang = product.get("lang")
    ingredients_text_en = product.get("ingredients_text_en")
    ingredients_text_native = product.get("ingredients_text") or ""

    translation_note = None
    if ingredients_text_en:
        ingredients_text_final = ingredients_text_en
    elif (
        ingredients_text_native
        and translate_ingredients
        and source_lang
        and source_lang != "en"
    ):
        translated_text, was_translated = translate_to_english(
            ingredients_text_native, source_lang
        )
        if was_translated:
            ingredients_text_final = translated_text
            translation_note = (
                f"Ingredients were translated from \"{source_lang}\" to English."
            )
        else:
            ingredients_text_final = ingredients_text_native
            translation_note = (
                "Couldn't translate these ingredients — showing the "
                "original language."
            )
    else:
        ingredients_text_final = ingredients_text_native

    ingredients_list = [
        part.strip().title()
        for part in ingredients_text_final.split(",")
        if part.strip()
    ]

    nutriments = product.get("nutriments", {})

    # Open Food Facts' categories_tags run general -> specific (e.g.
    # ["en:cereals-and-potatoes", "en:breakfast-cereals"]), so the last
    # tag is the most specific one to search similar products against.
    categories_tags = product.get("categories_tags") or []
    category_tag = categories_tags[-1] if categories_tags else None

    return {
        "barcode": matched_barcode,
        "name": name,
        "brand": product.get("brands", ""),
        "ingredients_list": ingredients_list,
        "translation_note": translation_note,
        "image_url": product.get("image_front_small_url") or product.get("image_url"),
        "sugar_100g": nutriments.get("sugars_100g"),
        "sodium_100g": nutriments.get("sodium_100g"),
        "saturated_fat_100g": nutriments.get("saturated-fat_100g"),
        "fiber_100g": nutriments.get("fiber_100g"),
        "category_tag": category_tag,
    }


def lookup_openfoodfacts(barcode):
    """Look up a barcode on Open Food Facts, trying a couple of common
    barcode-format variants before giving up. Returns (result_dict,
    None) on success, (None, None) if genuinely not found, or (None,
    error_message) if the request itself failed."""
    product = None
    matched_barcode = barcode
    last_error = None
    for candidate in _barcode_variants(barcode):
        product, error = _fetch_openfoodfacts_product(candidate)
        if error:
            last_error = error
        if product:
            matched_barcode = candidate
            break

    if not product:
        return None, last_error

    return _build_scan_result(product, matched_barcode, translate_ingredients=True), None


@st.cache_data(ttl=3600, show_spinner=False)
def _search_openfoodfacts_category(category_tag, page_size=24):
    """Raw search against Open Food Facts for popular products in a
    given category. Returns (products_list, error_message)."""
    if not category_tag:
        return [], None
    try:
        response = requests.get(
            "https://world.openfoodfacts.org/api/v2/search",
            headers=OPENFOODFACTS_HEADERS,
            params={
                "categories_tags": category_tag,
                "sort_by": "unique_scans_n",
                "page_size": page_size,
                "fields": (
                    "code,product_name,product_name_en,brands,"
                    "image_front_small_url,image_url,ingredients_text,"
                    "ingredients_text_en,lang,nutriments,categories_tags"
                ),
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return [], f"Request failed: {exc}"
    except ValueError as exc:
        return [], f"Couldn't parse the response: {exc}"

    return data.get("products", []), None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_healthier_alternatives(category_tag, exclude_barcode, min_score=70, max_results=5):
    """Search Open Food Facts for popular products in the same category
    as a scanned product, score each candidate with the app's own
    health-score logic, and return up to max_results products scoring
    at or above min_score, best first — the same data (ingredients,
    nutrition) shown for the original scanned product is available for
    each one. Returns (alternatives_list, error_message)."""
    if not category_tag:
        return [], None

    raw_products, error = _search_openfoodfacts_category(category_tag)
    if error:
        return [], error

    scored = []
    seen_names = set()
    for product in raw_products:
        code = product.get("code")
        if not code or code == exclude_barcode:
            continue

        candidate = _build_scan_result(product, code, translate_ingredients=False)
        if not candidate["ingredients_list"]:
            continue

        name_key = (candidate["name"].strip().lower(), candidate["brand"].strip().lower())
        if name_key in seen_names:
            continue

        score, _, _, _ = compute_health_score(
            candidate["ingredients_list"],
            {
                "sugar_100g": candidate["sugar_100g"],
                "sodium_100g": candidate["sodium_100g"],
                "saturated_fat_100g": candidate["saturated_fat_100g"],
                "fiber_100g": candidate["fiber_100g"],
            },
        )
        if score >= min_score:
            seen_names.add(name_key)
            candidate["score"] = score
            scored.append(candidate)

    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[:max_results], None


def compute_health_score(ingredients_list, nutrition):
    """A 0-100 health score: starts at 100, loses points for harmful
    and moderate/"semi-harmful" ingredients and less healthy nutrition
    levels, gains a small bonus for healthy ingredients and fiber.
    Nutrition thresholds are based on the UK FSA's public high/medium/low
    "traffic light" bands.

    Harmful ingredients (additives with clearer red flags, like
    artificial dyes or trans fat) cost more points than moderate ones
    (everyday ingredients like sugar or salt that are only a concern
    in excess) — so a product like Nutella, which mostly contains
    moderate ingredients, doesn't score as harshly as one full of
    artificial additives."""
    score = 100
    matched_harmful = []
    matched_moderate = []
    matched_healthy = []

    for ingredient in ingredients_list:
        ing_lower = ingredient.lower()
        for dict_name, data in INGREDIENT_DICTIONARY.items():
            dict_lower = dict_name.lower()
            if dict_lower in ing_lower or ing_lower in dict_lower:
                if data["type"] == "harmful":
                    matched_harmful.append(dict_name)
                elif data["type"] == "moderate":
                    matched_moderate.append(dict_name)
                else:
                    matched_healthy.append(dict_name)
                break

    score -= len(matched_harmful) * 8
    score -= len(matched_moderate) * 3
    score += min(len(matched_healthy) * 2, 10)

    sugar = nutrition.get("sugar_100g")
    if sugar is not None:
        if sugar > 22.5:
            score -= 10
        elif sugar > 5:
            score -= 5

    sodium = nutrition.get("sodium_100g")
    if sodium is not None:
        if sodium > 0.6:
            score -= 10
        elif sodium > 0.1:
            score -= 5

    sat_fat = nutrition.get("saturated_fat_100g")
    if sat_fat is not None:
        if sat_fat > 5:
            score -= 10
        elif sat_fat > 1.5:
            score -= 5

    fiber = nutrition.get("fiber_100g")
    if fiber is not None:
        if fiber > 6:
            score += 5
        elif fiber > 3:
            score += 2

    score = max(0, min(100, round(score)))
    return score, matched_harmful, matched_moderate, matched_healthy


def classify_ingredient(ingredient_name):
    """Return 'harmful', 'moderate', or 'healthy' for an ingredient
    name if it matches something in our dictionary (same
    case-insensitive, either-direction matching used elsewhere, e.g.
    "Wheat" matches "Wheat Flour"). Returns None if unclassified."""
    ing_lower = ingredient_name.lower()
    for dict_name, data in INGREDIENT_DICTIONARY.items():
        dict_lower = dict_name.lower()
        if dict_lower in ing_lower or ing_lower in dict_lower:
            return data["type"]
    return None


def render_ingredient_card(ingredient_name):
    """Render one ingredient as a card color-coded the same way as the
    Dictionary tab: red for harmful, yellow for moderate/semi-harmful,
    green for healthy. Unclassified ingredients fall back to the
    plain neutral card style."""
    kind = classify_ingredient(ingredient_name)
    if kind == "harmful":
        css_class, icon = "ingredient-card ingredient-harmful", "⚠️"
    elif kind == "moderate":
        css_class, icon = "ingredient-card ingredient-moderate", "🟡"
    elif kind == "healthy":
        css_class, icon = "ingredient-card ingredient-healthy", "🌿"
    else:
        css_class, icon = "ingredient-card", "🌱"

    st.markdown(
        f'<div class="{css_class}">{icon} {html.escape(ingredient_name)}</div>',
        unsafe_allow_html=True,
    )


def render_product_scan_result(result, current_user, show_alternatives=True):
    """Render the full result view for one Open Food Facts product:
    personal allergy/dietary warnings, health score, ingredient list,
    and the harmful/moderate/healthy breakdown. When show_alternatives
    is True and the score comes in under 70, also looks up and lists
    healthier alternatives in the same category (Yuka-style) that the
    user can tap to view in the same amount of detail. Returns the
    computed health score."""

    user_allergies = get_user_allergies(current_user)
    personal_matches = find_matching_allergens(result["ingredients_list"], user_allergies)

    user_dietary_restrictions = get_user_dietary_restrictions(current_user)
    dietary_conflicts = find_matching_dietary_conflicts(
        result["ingredients_list"],
        user_dietary_restrictions,
        nutrition={
            "sugar_100g": result["sugar_100g"],
            "sodium_100g": result["sodium_100g"],
        },
    )

    render_warning_banner(personal_matches, dietary_conflicts)

    st.divider()

    if result["image_url"]:
        img_col, info_col = st.columns([1, 2])
        with img_col:
            st.image(result["image_url"], width=100)
        with info_col:
            st.subheader(result["name"])
            if result["brand"]:
                st.caption(result["brand"])
    else:
        st.subheader(result["name"])
        if result["brand"]:
            st.caption(result["brand"])

    score, matched_harmful, matched_moderate, matched_healthy = compute_health_score(
        result["ingredients_list"],
        {
            "sugar_100g": result["sugar_100g"],
            "sodium_100g": result["sodium_100g"],
            "saturated_fat_100g": result["saturated_fat_100g"],
            "fiber_100g": result["fiber_100g"],
        },
    )
    if score >= 70:
        score_color = "#3F6B24"
    elif score >= 40:
        score_color = "#B8860B"
    else:
        score_color = "#A23B2E"

    st.markdown(
        f"""
        <div class="stat-card" style="border-color:{score_color};">
            <div class="stat-number" style="color:{score_color};">{score}/100</div>
            <div class="stat-label">Health Score</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    if result["ingredients_list"]:
        st.write("#### Ingredients")
        if result.get("translation_note"):
            st.caption(f"🌐 {result['translation_note']}")
        for ingredient in result["ingredients_list"]:
            render_ingredient_card(ingredient)
    else:
        st.caption("No ingredient list was available for this product.")

    st.write("")

    if matched_harmful:
        st.warning("⚠️ Harmful ingredients found")
        for name in matched_harmful:
            st.write(f"**{name}:** {WATCH_LIST.get(name, INGREDIENT_DICTIONARY[name]['concern'])}")
    else:
        st.success("✅ No harmful ingredients from our list were found.")

    if matched_moderate:
        st.markdown(
            '<div class="instruction-card" style="background-color:#FDF3E2;'
            'border-color:#F0D8A0;color:#8A6300;font-weight:600;">'
            '🟡 Semi-harmful ingredients found — fine in moderation'
            '</div>',
            unsafe_allow_html=True,
        )
        for name in matched_moderate:
            st.write(f"**{name}:** {MODERATE_LIST.get(name, INGREDIENT_DICTIONARY[name]['concern'])}")

    if matched_healthy:
        st.info("🌿 Healthy ingredients spotted")
        for name in matched_healthy:
            st.write(f"**{name}:** {HEALTHY_HIGHLIGHTS.get(name, INGREDIENT_DICTIONARY[name]['concern'])}")

    if show_alternatives and score < 70:
        st.divider()
        st.markdown('<p class="section-title">🌟 Healthier Alternatives</p>', unsafe_allow_html=True)
        st.caption(
            "Other products in the same Open Food Facts category "
            "scoring 70+ on our health score."
        )

        if not result.get("category_tag"):
            st.caption(
                "This product isn't categorized on Open Food Facts, so "
                "we can't look up alternatives for it."
            )
        else:
            with st.spinner("Looking for healthier alternatives..."):
                alternatives, alt_error = fetch_healthier_alternatives(
                    result["category_tag"], exclude_barcode=result["barcode"]
                )

            if alt_error:
                st.caption("Couldn't load alternatives right now — try again later.")
            elif not alternatives:
                st.caption("No stronger alternatives found in this category yet.")
            else:
                for alt in alternatives:
                    alt_img_col, alt_info_col, alt_btn_col = st.columns([1, 2.4, 1])
                    with alt_img_col:
                        if alt["image_url"]:
                            st.image(alt["image_url"], width=60)
                    with alt_info_col:
                        st.markdown(f"**{html.escape(alt['name'])}**")
                        if alt["brand"]:
                            st.caption(alt["brand"])
                        st.markdown(
                            f'<span style="color:#3F6B24; font-weight:700;">'
                            f'{alt["score"]}/100</span>',
                            unsafe_allow_html=True,
                        )
                    with alt_btn_col:
                        st.write("")
                        if st.button("View", key=f"view_alt_{alt['barcode']}"):
                            st.session_state.viewing_alternative_barcode = alt["barcode"]
                            st.rerun()
                    st.markdown(
                        '<hr style="margin:0.3rem 0 0.7rem 0; border:none; '
                        'border-top:1px solid #DCE4C9;">',
                        unsafe_allow_html=True,
                    )

    return score


# ---- 3. PAGE SETUP ------------------------------------------

st.set_page_config(
    page_title="PureBites",
    page_icon="🌿",
    layout="centered",
)

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None  # holds the logged-in user's DB record

if "scan_count" not in st.session_state:
    st.session_state.scan_count = STARTING_SCAN_COUNT  # starting stat, like the app mockup

if "streak_count" not in st.session_state:
    st.session_state.streak_count = 0

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "barcode_result" not in st.session_state:
    st.session_state.barcode_result = None

if "last_barcode_fingerprint" not in st.session_state:
    st.session_state.last_barcode_fingerprint = None

if "viewing_alternative_barcode" not in st.session_state:
    st.session_state.viewing_alternative_barcode = None

# Show the splash screen only once per browser session (the very first
# script run) — not on every rerun triggered by clicks, tabs, etc.
if "splash_shown" not in st.session_state:
    show_splash = True
    st.session_state.splash_shown = True
else:
    show_splash = False


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
            /* On phones the ad partners live in a slim bar docked to
               the bottom of the screen (see .purebites-ad-sidebar
               below), so we reserve space at the bottom instead of
               the right — this keeps every tab's content, including
               the tab labels themselves, fully visible and unclipped. */
            padding-bottom: 7.5rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        /* Logo */
        .purebites-logo-wrap {
            display: flex;
            justify-content: center;
            margin-bottom: 0.75rem;
        }
        .purebites-logo {
            width: 170px;
            height: auto;
        }
        /* Smaller logo on narrow / mobile screens */
        @media (max-width: 600px) {
            .purebites-logo {
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
        /* Color-coded variants — same palette as the Dictionary tab's
           harmful/moderate/healthy cards, so a red/yellow/green
           ingredient here means the same thing it does there. */
        .ingredient-card.ingredient-harmful {
            background-color: #FDECEA;
            border: 1px solid #F3B9B4;
            color: #A23B2E;
            font-weight: 600;
        }
        .ingredient-card.ingredient-moderate {
            background-color: #FDF3E2;
            border: 1px solid #F0D8A0;
            color: #8A6300;
            font-weight: 600;
        }
        .ingredient-card.ingredient-healthy {
            background-color: #EAF3E2;
            border: 1px solid #BBD9A0;
            color: #3F6B24;
            font-weight: 600;
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
        .dict-card.moderate {
            background-color: #FDF3E2;
            border-color: #F0D8A0;
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
        .dict-name.moderate { color: #B8860B; }
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
        .dict-badge.moderate { background-color: #E0A83A; color: white; }
        .dict-badge.healthy { background-color: #78A855; color: white; }
        .dict-explanation { color: #4A4A4A; font-size: 0.88rem; margin: 0.3rem 0; }
        .dict-concern { font-size: 0.85rem; font-style: italic; }
        .dict-concern.harmful { color: #A23B2E; }
        .dict-concern.moderate { color: #B8860B; }
        .dict-concern.healthy { color: #3F6B24; }

        /* Sidebar background */
        [data-testid="stSidebar"] {
            background-color: #DCE4C9;
        }

        /* ---------------------------------------------------------
           Streamlit's built-in accent color defaults to red. The
           .streamlit/config.toml theme fixes most of this app-wide,
           but these rules act as a CSS-level backup for the same
           elements shown in red before (tabs, selected pills/tags).
        --------------------------------------------------------- */
        /* Center the tab row instead of it hugging the left edge —
           applies on both mobile and desktop since it's just flexbox
           centering, with wrapping so tabs don't overflow narrow
           phone screens. */
        .stTabs [data-baseweb="tab-list"] {
            justify-content: center !important;
            flex-wrap: wrap !important;
            overflow-x: visible !important;
            row-gap: 0.4rem;
            column-gap: 0.15rem;
        }
        /* Let each tab shrink/wrap its own label instead of forcing a
           single unbroken line — this is what was letting the tab row
           run wider than the screen and disappear behind the ad
           sidebar/bar on phones. */
        .stTabs [data-baseweb="tab"] {
            white-space: normal !important;
            height: auto !important;
            min-height: 2.4rem;
        }
        @media (max-width: 600px) {
            .stTabs [data-baseweb="tab"] {
                font-size: 0.82rem !important;
                padding: 0.5rem 0.6rem !important;
            }
        }
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: #526539 !important;
        }
        .stTabs [data-baseweb="tab"] {
            color: #6B7B57 !important;
        }
        .stTabs button[aria-selected="true"] {
            color: #526539 !important;
        }
        .stMultiSelect [data-baseweb="tag"] {
            background-color: #8C9B5D !important;
        }
        .stRadio [role="radiogroup"] label div:first-child {
            border-color: #8C9B5D !important;
        }
        .stRadio [role="radiogroup"] label[data-baseweb="radio"] div:first-child div {
            background-color: #526539 !important;
        }

        /* Login / Sign up text inputs */
        .stTextInput > div > div > input {
            border-radius: 10px !important;
            border: 1px solid #DCE4C9 !important;
        }
        .stTextInput > div > div > input:focus {
            border: 1px solid #8C9B5D !important;
            box-shadow: 0 0 0 1px #8C9B5D !important;
        }

        /* Log In / Create Account buttons (form submit buttons aren't
           covered by the .stButton rule above, so they're styled here) */
        .stFormSubmitButton > button {
            width: 100%;
            background-color: #2E7D32 !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.7rem 1rem !important;
            font-weight: 600 !important;
        }
        .stFormSubmitButton > button:hover {
            background-color: #26692A !important;
            color: white !important;
            border: none !important;
        }

        /* Validation messages on the Log In / Sign Up page (dark green
           instead of Streamlit's default red alerts) */
        .auth-message {
            background-color: #E8F3E8;
            border: 1px solid #2E7D32;
            color: #2E7D32;
            border-radius: 12px;
            padding: 0.65rem 1rem;
            margin-bottom: 0.8rem;
            font-size: 0.9rem;
        }
        .auth-password-hint {
            color: #2E7D32;
            font-size: 0.82rem;
            margin-top: -0.6rem;
            margin-bottom: 0.6rem;
        }

        /* Cute flickering fire animation for the streak stat */
        .fire-emoji {
            display: inline-block;
            animation: fire-flicker 1.3s infinite ease-in-out;
            transform-origin: center bottom;
        }
        @keyframes fire-flicker {
            0%, 100% {
                transform: scale(1) rotate(-3deg);
                filter: drop-shadow(0 0 2px rgba(255, 140, 0, 0.5));
            }
            25% {
                transform: scale(1.1) rotate(2deg);
                filter: drop-shadow(0 0 4px rgba(255, 100, 0, 0.6));
            }
            50% {
                transform: scale(0.94) rotate(-2deg);
                filter: drop-shadow(0 0 6px rgba(255, 80, 0, 0.7));
            }
            75% {
                transform: scale(1.06) rotate(3deg);
                filter: drop-shadow(0 0 4px rgba(255, 120, 0, 0.6));
            }
        }

        /* ---------------------------------------------------------
           RESPONSIVE SIZING
           Phones stay compact (the default sizing above).
           Tablets (iPad-sized) and desktop screens get a wider
           layout with larger text and roomier cards so nothing
           feels cramped on a bigger screen.
        --------------------------------------------------------- */

        /* Tablets / iPad */
        @media (min-width: 768px) {
            .block-container {
                max-width: 640px;
                padding-top: 2rem;
                /* Ads move back to a right-hand sidebar at this width,
                   so we no longer need the bottom clearance and instead
                   reserve room on the right (130px sidebar + gap). */
                padding-bottom: 3.5rem;
                padding-left: 1.5rem;
                padding-right: 1.5rem;
                margin-right: 160px;
            }
            .purebites-logo { width: 190px; }
            .greeting-card { padding: 1.15rem 1.4rem; }
            .greeting-title { font-size: 1.45rem; }
            .greeting-sub { font-size: 0.98rem; }
            .stat-card { padding: 0.95rem; }
            .stat-number { font-size: 1.6rem; }
            .stat-label { font-size: 0.85rem; }
            .hero-card { padding: 1.6rem 1.6rem; }
            .hero-title { font-size: 1.55rem; }
            .hero-sub { font-size: 0.98rem; }
            .section-title { font-size: 1.2rem; }
            .instruction-card { font-size: 0.95rem; padding: 1rem 1.2rem; }
            .ingredient-card { font-size: 1rem; padding: 0.75rem 0.9rem; }
            .dict-card { padding: 1rem 1.2rem; }
            .dict-name { font-size: 1.08rem; }
            .dict-explanation { font-size: 0.92rem; }
            .dict-concern { font-size: 0.88rem; }
        }

        /* Desktop */
        @media (min-width: 1024px) {
            .block-container {
                max-width: 860px;
                padding-top: 2.5rem;
                padding-bottom: 4rem;
                padding-left: 1.75rem;
                padding-right: 1.75rem;
                /* ad sidebar grows to 175px at this size, plus gap */
                margin-right: 210px;
            }
            .purebites-logo { width: 220px; }
            .greeting-card { padding: 1.3rem 1.6rem; }
            .greeting-title { font-size: 1.7rem; }
            .greeting-sub { font-size: 1.05rem; }
            .stat-card { padding: 1.1rem; }
            .stat-number { font-size: 1.9rem; }
            .stat-label { font-size: 0.92rem; }
            .hero-card { padding: 1.9rem 2rem; }
            .hero-title { font-size: 1.9rem; }
            .hero-sub { font-size: 1.05rem; }
            .section-title { font-size: 1.35rem; }
            .instruction-card { font-size: 1rem; padding: 1.1rem 1.3rem; }
            .ingredient-card { font-size: 1.05rem; padding: 0.85rem 1.1rem; }
            .dict-card { padding: 1.1rem 1.3rem; }
            .dict-name { font-size: 1.15rem; }
            .dict-explanation { font-size: 0.95rem; }
            .dict-concern { font-size: 0.92rem; }
            .stButton > button { font-size: 1.02rem; padding: 0.8rem 1.1rem; }
        }

        /* Wide desktop — ad sidebar is at its full 220px size here, so
           content gets extra room to keep the same comfortable gap. */
        @media (min-width: 1300px) {
            .block-container {
                padding-left: 2rem;
                padding-right: 2rem;
                margin-right: 255px;
            }
        }

        /* ---------------------------------------------------------
           SPLASH SCREEN
           A full-screen overlay shown once when the app first
           loads. It pops in, holds for about two seconds, then
           dissolves away to reveal the app underneath.
        --------------------------------------------------------- */
        .purebites-splash {
            position: fixed;
            inset: 0;
            background-color: #FDF7EF;
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: purebites-splash-fade-out 0.8s ease forwards;
            animation-delay: 2s;
        }
        .purebites-splash-inner {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1.4rem;
            animation: purebites-splash-pop-in 0.5s ease;
        }
        .purebites-splash-logo {
            width: min(200px, 42vw);
            height: auto;
        }
        .purebites-splash-tagline {
            color: #8C9B5D;
            font-size: clamp(0.85rem, 2vw, 1.05rem);
            letter-spacing: 0.02em;
            margin: 0;
        }
        @keyframes purebites-splash-pop-in {
            0% { opacity: 0; transform: translateY(10px) scale(0.96); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes purebites-splash-fade-out {
            0% { opacity: 1; visibility: visible; }
            99% { opacity: 0; visibility: visible; }
            100% { opacity: 0; visibility: hidden; pointer-events: none; }
        }

        /* The spinning "loading" circle made of 8 fading blades */
        .lds-spinner {
            position: relative;
            display: inline-block;
            width: 64px;
            height: 64px;
        }
        .lds-spinner div {
            transform-origin: 32px 32px;
            animation: lds-spinner-fade 1.2s linear infinite;
        }
        .lds-spinner div:after {
            content: " ";
            display: block;
            position: absolute;
            top: 3px;
            left: 29px;
            width: 6px;
            height: 16px;
            border-radius: 20%;
            background: #8C9B5D;
        }
        .lds-spinner div:nth-child(1) { transform: rotate(0deg); animation-delay: -1.1s; }
        .lds-spinner div:nth-child(2) { transform: rotate(45deg); animation-delay: -1s; }
        .lds-spinner div:nth-child(3) { transform: rotate(90deg); animation-delay: -0.9s; }
        .lds-spinner div:nth-child(4) { transform: rotate(135deg); animation-delay: -0.8s; }
        .lds-spinner div:nth-child(5) { transform: rotate(180deg); animation-delay: -0.7s; }
        .lds-spinner div:nth-child(6) { transform: rotate(225deg); animation-delay: -0.6s; }
        .lds-spinner div:nth-child(7) { transform: rotate(270deg); animation-delay: -0.5s; }
        .lds-spinner div:nth-child(8) { transform: rotate(315deg); animation-delay: -0.4s; }
        @keyframes lds-spinner-fade {
            0% { opacity: 1; }
            100% { opacity: 0.15; }
        }

        /* Slightly smaller splash elements on narrow phone screens */
        @media (max-width: 420px) {
            .lds-spinner { transform: scale(0.8); }
            .purebites-splash-inner { gap: 1.1rem; }
        }

        /* Personal allergy warning banner — the first thing shown in a
           scan result when a saved allergy is found in the product. */
        .allergy-warning-banner {
            background-color: #FFEAEA;
            border: 2px solid #FF6B6B;
            color: #FF6B6B;
            text-transform: uppercase;
            font-weight: 800;
            text-align: center;
            padding: 1rem 1.1rem;
            border-radius: 16px;
            margin-bottom: 1.1rem;
            letter-spacing: 0.02em;
            line-height: 1.4;
            animation: allergy-pulse 1.1s infinite ease-in-out;
        }
        @keyframes allergy-pulse {
            0%, 100% {
                transform: scale(1);
                box-shadow: 0 0 0 rgba(255, 107, 107, 0.35);
            }
            50% {
                transform: scale(1.02);
                box-shadow: 0 0 16px rgba(255, 107, 107, 0.55);
            }
        }

        /* Profile picture avatar */
        .profile-avatar-wrap {
            display: flex;
            justify-content: center;
            margin-bottom: 0.75rem;
        }
        .profile-avatar-img {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid #DCE4C9;
        }
        .profile-avatar-placeholder {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background-color: #8C9B5D;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.4rem;
            font-weight: 700;
            border: 3px solid #DCE4C9;
        }

        /* Allergy chips shown on the profile page */
        .allergy-chip {
            display: inline-block;
            background-color: #EAF3E2;
            border: 1px solid #BBD9A0;
            color: #3F6B24;
            border-radius: 999px;
            padding: 0.25rem 0.75rem;
            margin: 0.2rem 0.3rem 0.2rem 0;
            font-size: 0.85rem;
            font-weight: 600;
        }

        /* Dietary restriction chips shown on the profile page —
           same pill shape/theme as allergy chips, distinct accent
           color so the two sections stay easy to tell apart. */
        .dietary-chip {
            display: inline-block;
            background-color: #F3EEE2;
            border: 1px solid #D9C9A0;
            color: #6B5424;
            border-radius: 999px;
            padding: 0.25rem 0.75rem;
            margin: 0.2rem 0.3rem 0.2rem 0;
            font-size: 0.85rem;
            font-weight: 600;
        }

        /* Hide Streamlit's built-in "Press Enter to submit form" hint
           that overlaps the password reveal (eye) icon on login/signup */
        div[data-testid="InputInstructions"] {
            display: none;
        }

        /* ---- Allergies page ---- */

        /* Quick-tip callout card */
        .tip-card {
            background-color: #FDF3E2;
            border: 1px solid #F0D8A0;
            color: #6B4E00;
            border-radius: 16px;
            padding: 1rem 1.2rem;
            margin-bottom: 1.2rem;
            font-size: 0.92rem;
            line-height: 1.5;
        }
        .tip-card strong {
            color: #8A6300;
        }

        /* Click-to-play YouTube preview */
        .video-preview-wrap {
            position: relative;
            width: 100%;
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 1.2rem;
            box-shadow: 0 2px 10px rgba(82, 101, 57, 0.12);
            cursor: pointer;
        }
        .video-preview-wrap img {
            width: 100%;
            display: block;
        }
        .video-play-button {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 68px;
            height: 68px;
            background-color: rgba(82, 101, 57, 0.9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .video-play-button::after {
            content: "";
            border-style: solid;
            border-width: 12px 0 12px 20px;
            border-color: transparent transparent transparent #FFFFFF;
            margin-left: 5px;
        }

        /* Emergency resources */
        .emergency-card {
            background-color: #FBEAEA;
            border: 1px solid #E8B4B4;
            border-radius: 16px;
            padding: 1rem 1.2rem;
            margin-bottom: 0.8rem;
        }
        .emergency-card-title {
            color: #963A3A;
            font-weight: 700;
            font-size: 1rem;
            margin-bottom: 0.3rem;
        }
        .emergency-card-body {
            color: #6E2C2C;
            font-size: 0.9rem;
            line-height: 1.5;
        }

        /* ---- Donate page ---- */

        /* GoFundMe card */
        .gofundme-card {
            background: linear-gradient(135deg, #DCE4C9 0%, #C6D2A8 100%);
            border-radius: 20px;
            padding: 1.6rem 1.6rem;
            margin-bottom: 1.4rem;
            text-align: center;
        }
        .gofundme-card-title {
            font-size: 1.15rem;
            font-weight: 800;
            color: #33421F;
            margin-bottom: 0.3rem;
        }
        .gofundme-card-sub {
            font-size: 0.9rem;
            color: #4C5A38;
            margin-bottom: 1rem;
        }
        .gofundme-link-button {
            display: inline-block;
            background-color: #526539;
            color: #FFFFFF !important;
            font-weight: 700;
            font-size: 0.95rem;
            text-decoration: none;
            border-radius: 999px;
            padding: 0.7rem 1.8rem;
            box-shadow: 0 3px 10px rgba(82, 101, 57, 0.25);
            transition: transform 0.15s ease;
        }
        .gofundme-link-button:hover {
            transform: translateY(-2px);
        }

        /* Feeding America partner card */
        .partner-card {
            background-color: #FFFFFF;
            border: 1px solid #DCE4C9;
            border-radius: 20px;
            padding: 1.6rem 1.6rem;
            text-align: center;
            box-shadow: 0 2px 10px rgba(82, 101, 57, 0.08);
            margin-bottom: 1.2rem;
        }
        .partner-logo {
            max-width: 260px;
            width: 80%;
            margin: 0 auto 1.2rem auto;
            display: block;
        }
        .donate-now-button {
            display: inline-block;
            background-color: #526539;
            color: #FFFFFF !important;
            font-weight: 800;
            font-size: 1rem;
            letter-spacing: 0.02em;
            text-decoration: none;
            border-radius: 999px;
            padding: 0.85rem 2.6rem;
            box-shadow: 0 4px 12px rgba(82, 101, 57, 0.3);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            margin: 0.4rem 0 1.3rem 0;
        }
        .donate-now-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(82, 101, 57, 0.38);
        }
        .partner-statement {
            color: #4C5A38;
            font-size: 0.92rem;
            line-height: 1.6;
            text-align: left;
            margin-top: 0.4rem;
        }

        /* ---------------------------------------------------------
           RIGHT-HAND AD SIDEBAR
           A custom fixed panel that mirrors the look of Streamlit's
           native left sidebar (same background color, rounded white
           cards, soft shadow) but sits on the right and has no
           built-in "collapse" control, so it can't be closed. It's
           rendered once outside of st.tabs(), so it stays put no
           matter which tab is active.

           On phones (below 768px) there just isn't enough horizontal
           room for a right-hand column without it eating into (or
           outright covering) page content like the tab labels — so
           on phones this renders as a slim horizontal bar docked to
           the *bottom* of the screen instead. .block-container adds
           matching bottom padding on phones (set above) so the last
           bit of page content never sits behind that bar.

           From 768px up there's enough width for the original
           right-hand column, and .block-container gets a matching
           margin-right (set alongside each breakpoint above) so page
           content keeps a comfortable gap from it.
        --------------------------------------------------------- */
        .purebites-ad-sidebar {
            position: fixed;
            left: 0;
            right: 0;
            bottom: 0;
            width: 100%;
            height: auto;
            max-height: 6.5rem;
            background-color: #DCE4C9;
            padding: 0.6rem 0.75rem;
            overflow-x: auto;
            overflow-y: hidden;
            z-index: 998;
            box-shadow: 0 -2px 10px rgba(82, 101, 57, 0.12);
            display: flex;
            flex-direction: row;
            align-items: center;
            gap: 0.6rem;
        }
        .purebites-ad-sidebar-title {
            /* No room for a title on phones — icon/logo ads only */
            display: none;
        }
        .purebites-ad-card {
            display: block;
            flex: 0 0 auto;
            width: 4.6rem;
            height: 4.6rem;
            background-color: #FFFFFF;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(82, 101, 57, 0.1);
            text-decoration: none;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .purebites-ad-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 14px rgba(82, 101, 57, 0.2);
        }
        .purebites-ad-card img {
            width: 100%;
            height: 100%;
            display: block;
            object-fit: cover;
        }

        /* Tablets / small laptops — switch to the right-hand column */
        @media (min-width: 768px) {
            .purebites-ad-sidebar {
                left: auto;
                bottom: auto;
                top: 0;
                right: 0;
                width: 130px;
                height: 100vh;
                max-height: none;
                padding: 1.25rem 0.65rem;
                flex-direction: column;
                align-items: stretch;
                gap: 0;
                overflow-x: hidden;
                overflow-y: auto;
                box-shadow: -2px 0 10px rgba(82, 101, 57, 0.1);
            }
            .purebites-ad-card {
                width: 100%;
                height: auto;
                margin-bottom: 0.85rem;
            }
        }

        /* Desktop — enough room for the title again */
        @media (min-width: 1024px) {
            .purebites-ad-sidebar {
                width: 175px;
                padding: 1.5rem 0.85rem;
            }
            .purebites-ad-sidebar-title {
                display: block;
                color: #33421F;
                font-weight: 700;
                font-size: 0.82rem;
                margin-bottom: 1rem;
                text-align: center;
                letter-spacing: 0.02em;
            }
            .purebites-ad-card {
                border-radius: 14px;
                margin-bottom: 1rem;
            }
        }

        /* Wide desktop — full size */
        @media (min-width: 1300px) {
            .purebites-ad-sidebar {
                width: 220px;
                padding: 1.75rem 1rem;
            }
            .purebites-ad-sidebar-title {
                font-size: 0.95rem;
                margin-bottom: 1.1rem;
            }
            .purebites-ad-card {
                border-radius: 16px;
                margin-bottom: 1.25rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

render_ad_sidebar()

# ---- 4.4 AI HELPER CSS + RENDER ---------------------------------
st.markdown(
    """
    <style>
        /* AI Helper bubble + panel, positioned to sit beside the ad
           partner sidebar rather than on top of it. On phones the ad
           sidebar is a bottom bar (see .purebites-ad-sidebar above),
           so the bubble floats just above it. From 768px up the ad
           sidebar becomes a right-hand column, so the bubble sits to
           its left, at the same width the sidebar uses at that
           breakpoint, with a small gap between them.
        */
        .st-key-ai_helper_bubble {
            position: fixed;
            bottom: calc(6.5rem + 12px);
            right: 12px;
            z-index: 10001;
        }
        .st-key-ai_helper_bubble .stButton > button {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background-color: #8C9B5D !important;
            color: white !important;
            font-size: 1.5rem;
            line-height: 1;
            border: 3px solid white !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
            padding: 0;
        }
        .st-key-ai_helper_bubble .stButton > button:hover {
            background-color: #798552 !important;
            color: white !important;
        }
        .st-key-ai_helper_panel {
            position: fixed;
            bottom: calc(6.5rem + 84px);
            right: 12px;
            width: min(300px, 92vw);
            max-height: 55vh;
            overflow-y: auto;
            background-color: white;
            border-radius: 16px;
            padding: 1rem 1rem 0.5rem 1rem;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.22);
            z-index: 10000;
        }
        .ai-helper-title {
            font-weight: 700;
            font-size: 1.05rem;
            color: #4A5A32;
            margin-bottom: 0.15rem;
        }

        /* Tablets and up — the ad sidebar occupies the entire right
           edge as a full-height column (see .purebites-ad-sidebar
           above), so there's no vertical slice of the right edge
           that's ever free of it. Trying to tuck the bubble beside
           that column kept landing it in the wrong spot, so on
           desktop it now anchors to the opposite corner — bottom-LEFT
           of the viewport — well clear of both the ad sidebar and the
           main content column (which is centered with its own side
           margins, see .block-container rules above). It's also
           bumped up in size here since desktop has the room for it.
           A very high z-index keeps it above every other fixed/sticky
           element on the page, in case the ad sidebar's stacking
           context was ever burying it. */
        @media (min-width: 768px) {
            .st-key-ai_helper_bubble {
                bottom: 28px;
                left: 28px;
                right: auto;
                z-index: 999999;
            }
            .st-key-ai_helper_bubble .stButton > button {
                width: 84px;
                height: 84px;
                font-size: 2.2rem;
                border-width: 4px;
            }
            .st-key-ai_helper_panel {
                bottom: 122px;
                left: 28px;
                right: auto;
                width: min(360px, 85vw);
                max-height: 60vh;
                z-index: 999998;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# NOTE: render_ai_helper() is called further down (search "render_ai_helper()"),
# after current_user / is_guest_user are defined — it needs those to exist.


# ---- 4.5 SPLASH SCREEN -----------------------------------------
# Shown once, right when the app first loads. It sits on top of
# everything else (position: fixed) and dissolves away on its own
# via the CSS animation defined above — no page reload needed.

if show_splash:
    if LOGO_BASE64:
        _splash_logo_html = (
            f'<img class="purebites-splash-logo" '
            f'src="data:image/webp;base64,{LOGO_BASE64}" alt="PureBites logo">'
        )
    else:
        _splash_logo_html = (
            '<p style="color:#526539; font-size:2rem; font-weight:800;">'
            '🌿 PureBites</p>'
        )

    st.markdown(
        f"""
        <div class="purebites-splash">
            <div class="purebites-splash-inner">
                {_splash_logo_html}
                <div class="lds-spinner">
                    <div></div><div></div><div></div><div></div>
                    <div></div><div></div><div></div><div></div>
                </div>
                <p class="purebites-splash-tagline">Loading your healthier bite…</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---- 5. HEADER ----------------------------------------------

if LOGO_BASE64:
    st.markdown(
        f"""
        <div class="purebites-logo-wrap">
            <img class="purebites-logo" src="data:image/webp;base64,{LOGO_BASE64}" alt="PureBites logo">
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    # Fallback text header in case the logo file isn't found.
    st.markdown(
        '<p style="color:#526539; font-size:2.4rem; font-weight:800; '
        'text-align:center; margin-bottom:0;">🌿 PureBites</p>',
        unsafe_allow_html=True,
    )


# ---- 5.5 LOGIN / SIGN UP GATE ---------------------------------
# The rest of the app only renders once someone is logged in.

def auth_message(text):
    """A validation message styled in the app's dark green instead of
    Streamlit's default red st.error() styling."""
    st.markdown(
        f'<div class="auth-message">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def make_guest_user():
    """A throwaway, in-memory-only user record for people who don't want
    to create an account. It has the same shape as a real DB user row so
    the rest of the app can treat it identically — it just never touches
    the database, has no email, and is flagged with is_guest=True so a
    few features (profile picture, saved allergies) know to be a no-op."""
    return {
        "email": None,
        "name": "Guest",
        "salt": None,
        "password_hash": None,
        "scan_count": STARTING_SCAN_COUNT,
        "streak_count": 0,
        "last_login_date": None,
        "allergies": "[]",
        "dietary_restrictions": "[]",
        "profile_picture": None,
        "created_at": datetime.now().strftime("%B %Y"),
        "is_guest": True,
    }


def is_guest_user(user):
    return bool(user and user.get("is_guest"))


def render_auth_page():
    st.markdown(
        """
        <div class="instruction-card">
            <strong>Welcome to PureBites!</strong> Log in or create a free
            account to start scanning ingredients and track your progress.
        </div>
        """,
        unsafe_allow_html=True,
    )

    login_tab, signup_tab = st.tabs(["🔐 Log In", "✨ Sign Up"])

    # ---- Log In ----
    with login_tab:
        with st.form("login_form"):
            login_email = st.text_input(
                "Email address", placeholder="you@gmail.com", key="login_email"
            )
            login_password = st.text_input(
                "Password", type="password", key="login_password"
            )
            login_submit = st.form_submit_button("Log In", type="primary")

        if login_submit:
            if not login_email or not login_password:
                auth_message("Please enter both your email and password.")
            elif not is_valid_email(login_email):
                auth_message("Please enter a valid email address.")
            else:
                user = verify_login(login_email, login_password)
                if user:
                    user = record_login_streak(user["email"])
                    st.session_state.auth_user = user
                    st.session_state.scan_count = user["scan_count"]
                    st.session_state.streak_count = user["streak_count"]
                    st.session_state.last_result = None
                    st.session_state.pop("allergy_select", None)
                    st.session_state.pop("dietary_select", None)
                    st.session_state.viewing_alternative_barcode = None
                    st.session_state.pop("last_uploaded_pic_fingerprint", None)
                    st.rerun()
                else:
                    auth_message("Incorrect email or password.")

    # ---- Sign Up ----
    with signup_tab:
        with st.form("signup_form"):
            signup_name = st.text_input(
                "Your name", placeholder="First Name", key="signup_name"
            )
            signup_email = st.text_input(
                "Email address", placeholder="you@gmail.com", key="signup_email"
            )
            signup_password = st.text_input(
                "Password", type="password", key="signup_password"
            )
            st.markdown(
                f'<p class="auth-password-hint">{PASSWORD_REQUIREMENTS_TEXT}</p>',
                unsafe_allow_html=True,
            )
            signup_confirm = st.text_input(
                "Confirm password", type="password", key="signup_confirm"
            )
            signup_submit = st.form_submit_button("Create Account", type="primary")

        if signup_submit:
            if not signup_name or not signup_email or not signup_password:
                auth_message("Please fill in all fields.")
            elif not is_valid_email(signup_email):
                auth_message("Please enter a valid email address.")
            elif not is_strong_password(signup_password):
                auth_message(PASSWORD_REQUIREMENTS_TEXT + ".")
            elif signup_password != signup_confirm:
                auth_message("Those passwords don't match.")
            elif get_user(signup_email):
                auth_message(
                    "An account with that email already exists — try "
                    "logging in instead."
                )
            else:
                create_user(signup_email, signup_password, signup_name)
                user = record_login_streak(signup_email)
                st.session_state.auth_user = user
                st.session_state.scan_count = user["scan_count"]
                st.session_state.streak_count = user["streak_count"]
                st.session_state.last_result = None
                st.session_state.pop("allergy_select", None)
                st.session_state.pop("dietary_select", None)
                st.session_state.viewing_alternative_barcode = None
                st.session_state.pop("last_uploaded_pic_fingerprint", None)
                st.success("Account created! Redirecting...")
                st.rerun()

    st.write("")
    st.markdown(
        '<p style="text-align:center; opacity:0.7;">or</p>',
        unsafe_allow_html=True,
    )
    if st.button("Continue as Guest", key="guest_login", use_container_width=True):
        st.session_state.auth_user = make_guest_user()
        st.session_state.scan_count = STARTING_SCAN_COUNT
        st.session_state.streak_count = 0
        st.session_state.last_result = None
        st.session_state.pop("allergy_select", None)
        st.session_state.pop("dietary_select", None)
        st.session_state.viewing_alternative_barcode = None
        st.session_state.pop("last_uploaded_pic_fingerprint", None)
        st.rerun()
    st.caption(
        "As a guest you can use every feature, but you can't set a "
        "profile picture, and your allergies won't be saved once you "
        "leave."
    )


if st.session_state.auth_user is None:
    render_auth_page()
    st.stop()

current_user = st.session_state.auth_user
display_name = current_user["name"] or current_user["email"].split("@")[0]

render_ai_helper()


def render_greeting_and_stats():
    """The 'Hi, name!' card plus the scans/streak stat pills. Called at
    the top of the Scanner and Dictionary tabs (the Profile tab has its
    own, more detailed version of this) so it appears right under the
    tab bar rather than above it."""
    st.markdown(
        f"""
        <div class="greeting-card">
            <div class="greeting-title">Hi, {html.escape(display_name)}! 👋</div>
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
            f"""
            <div class="stat-card">
                <div class="stat-number"><span class="fire-emoji">🔥</span> {st.session_state.streak_count}</div>
                <div class="stat-label">Day Streak</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---- 6. TOP NAVIGATION ---------------------------------------
# The tab bar now sits directly under the logo, above the greeting
# card and stats — so navigation is always the first thing visible,
# on every screen size, without needing to scroll past the stats.

tab_profile, tab_scan, tab_dictionary, tab_allergies, tab_games, tab_donate = st.tabs(
    ["👤  Profile", "🔍  Scanner", "📖  Dictionary", "🚨  Allergies", "🎮  Games", "💝  Donate"]
)


# ============================================================
#  SCANNER TAB
# ============================================================

with tab_scan:

    render_greeting_and_stats()

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">Scan food ingredients</div>
            <p class="hero-sub">
                Scan a real product's barcode, or choose from our sample
                products below, to detect harmful ingredients and make
                smarter choices.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Real barcode scanning (Open Food Facts) ----
    st.markdown('<p class="section-title">📷 Scan a Barcode</p>', unsafe_allow_html=True)

    def _run_barcode_lookup(barcode_value):
        """Look up a barcode and store the result (or show why it
        failed). Shared by both the camera photo and manual entry."""
        with st.spinner("Looking up product..."):
            product_data, lookup_error = lookup_openfoodfacts(barcode_value)

        if lookup_error:
            st.session_state.barcode_result = None
            st.error(
                "Couldn't reach Open Food Facts right now — this is a "
                "connection problem, not a missing product. Try again "
                "in a moment."
            )
            with st.expander("Technical details"):
                st.code(lookup_error)
        elif not product_data:
            st.session_state.barcode_result = None
            st.warning(
                f"Barcode **{barcode_value}** isn't in the Open Food "
                "Facts database yet."
            )
            st.caption(
                "You can check "
                f"[openfoodfacts.org](https://world.openfoodfacts.org/product/{barcode_value}) "
                "directly to confirm whether this product is listed."
            )
        else:
            st.session_state.barcode_result = product_data
            st.session_state.viewing_alternative_barcode = None
            st.session_state.scan_count += 1
            if not is_guest_user(current_user):
                update_scan_count(current_user["email"], st.session_state.scan_count)

    if not BARCODE_SCANNING_AVAILABLE:
        st.info(
            "Barcode scanning isn't available right now — this usually "
            "means the `libzbar0` system package hasn't been installed. "
            "Make sure a `packages.txt` file containing `libzbar0` is in "
            "the same repo as app.py."
        )
    else:
        if "show_camera" not in st.session_state:
            st.session_state.show_camera = False

        st.caption(
            "Take a clear, well-lit, straight-on photo of a product's "
            "barcode."
        )

        if not st.session_state.show_camera:
            if st.button("📷 Open Camera to Scan", key="open_camera_btn", type="primary"):
                st.session_state.show_camera = True
                st.rerun()

        barcode_photo = None
        if st.session_state.show_camera:
            barcode_photo = st.camera_input(
                "Scan a barcode", key="barcode_camera", label_visibility="collapsed"
            )
            if st.button("Close Camera", key="close_camera_btn"):
                st.session_state.show_camera = False
                st.rerun()

        if barcode_photo is not None:
            # camera_input keeps returning the same photo on every rerun
            # until a new one is taken, so fingerprint it to avoid
            # reprocessing (and re-querying the API) on every interaction.
            photo_fingerprint = f"{barcode_photo.size}"
            if st.session_state.last_barcode_fingerprint != photo_fingerprint:
                st.session_state.last_barcode_fingerprint = photo_fingerprint
                with st.spinner("Reading barcode..."):
                    barcode_value = decode_barcode_image(barcode_photo)

                if not barcode_value:
                    st.session_state.barcode_result = None
                    st.warning(
                        "Couldn't read a barcode in that photo. Try "
                        "getting closer, holding steady, and making sure "
                        "it's in focus and well lit — or type the number "
                        "in manually below."
                    )
                else:
                    _run_barcode_lookup(barcode_value)

        # ---- Manual entry fallback ----
        # Useful when the camera can't get a clean read (glare, a small
        # or curved barcode, low light), and also handy for testing —
        # e.g. try 3017620422003 (Nutella), a barcode reliably in the
        # Open Food Facts database with full ingredient data.
        with st.expander("Can't scan it? Type the barcode number instead"):
            manual_barcode = st.text_input(
                "Barcode number",
                placeholder="e.g. 3017620422003",
                key="manual_barcode_input",
            )
            if st.button("Look Up", key="manual_barcode_submit"):
                manual_barcode_clean = manual_barcode.strip()
                if not manual_barcode_clean.isdigit():
                    st.warning("Enter a barcode using numbers only.")
                else:
                    _run_barcode_lookup(manual_barcode_clean)

        # ---- Viewing a suggested alternative product's full details ----
        if st.session_state.viewing_alternative_barcode:
            if st.button("← Back to your scanned product", key="back_from_alt"):
                st.session_state.viewing_alternative_barcode = None
                st.rerun()

            st.markdown(
                '<p class="section-title">🌟 Alternative Product</p>',
                unsafe_allow_html=True,
            )
            with st.spinner("Loading product..."):
                alt_result, alt_lookup_error = lookup_openfoodfacts(
                    st.session_state.viewing_alternative_barcode
                )
            if alt_lookup_error or not alt_result:
                st.warning("Couldn't load that product's details right now.")
            else:
                # No further nested alternatives — keeps the tap-through
                # to one level deep, like Yuka's swap screen.
                render_product_scan_result(alt_result, current_user, show_alternatives=False)

        elif st.session_state.barcode_result:
            render_product_scan_result(
                st.session_state.barcode_result, current_user, show_alternatives=True
            )

    st.divider()

    # ---- Sample product dropdown ----
    st.markdown('<p class="section-title">🔎 Or Browse Our Sample Products</p>', unsafe_allow_html=True)

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
        if not is_guest_user(current_user):
            update_scan_count(current_user["email"], st.session_state.scan_count)

    if st.session_state.last_result:
        result_choice = st.session_state.last_result
        ingredients = PRODUCTS[result_choice]

        # ---- Personal allergy warning + dietary restriction conflicts
        # (shown first, above everything) ----
        user_allergies = get_user_allergies(current_user)
        personal_matches = find_matching_allergens(ingredients, user_allergies)

        user_dietary_restrictions = get_user_dietary_restrictions(current_user)
        dietary_conflicts = find_matching_dietary_conflicts(
            ingredients, user_dietary_restrictions
        )

        render_warning_banner(personal_matches, dietary_conflicts)

        st.divider()
        st.subheader(f"{PRODUCT_EMOJIS.get(result_choice, '📦')} {result_choice}")
        st.write("#### Ingredients")

        for ingredient in ingredients:
            render_ingredient_card(ingredient)

        st.write("")

        # ---- Harmful / watch-list check ----
        flagged = [i for i in ingredients if i in WATCH_LIST]

        if flagged:
            st.warning("⚠️ Harmful ingredients found")
            for ingredient in flagged:
                st.write(f"**{ingredient}:** {WATCH_LIST[ingredient]}")
        else:
            st.success("✅ No harmful ingredients from our list were found.")

        # ---- Semi-harmful / moderate check ----
        moderate_found = [i for i in ingredients if i in MODERATE_LIST]
        if moderate_found:
            st.markdown(
                '<div class="instruction-card" style="background-color:#FDF3E2;'
                'border-color:#F0D8A0;color:#8A6300;font-weight:600;">'
                '🟡 Semi-harmful ingredients found — fine in moderation'
                '</div>',
                unsafe_allow_html=True,
            )
            for ingredient in moderate_found:
                st.write(f"**{ingredient}:** {MODERATE_LIST[ingredient]}")

        # ---- Healthy highlights ----
        healthy_found = [i for i in ingredients if i in HEALTHY_HIGHLIGHTS]
        if healthy_found:
            st.info("🌿 Healthy ingredients spotted")
            for ingredient in healthy_found:
                st.write(f"**{ingredient}:** {HEALTHY_HIGHLIGHTS[ingredient]}")

        # ---- Allergen check ----
        allergen_hits = [i for i in ingredients if i in ALLERGENS]

        if allergen_hits:
            auth_message("🚨 Allergy alert: " + ", ".join(allergen_hits))
        else:
            st.info("No allergens from our current allergen list were found.")


# ============================================================
#  DICTIONARY TAB
# ============================================================

with tab_dictionary:

    render_greeting_and_stats()

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
        ["All", "⚠️ Harmful", "🟡 Semi-Harmful", "🌿 Healthy"],
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
    elif filter_choice == "🟡 Semi-Harmful":
        entries = [(n, d) for n, d in entries if d["type"] == "moderate"]
    elif filter_choice == "🌿 Healthy":
        entries = [(n, d) for n, d in entries if d["type"] == "healthy"]

    st.markdown(f'<p class="section-title">{len(entries)} ingredient(s)</p>', unsafe_allow_html=True)

    if not entries:
        st.info("No ingredients match your search.")

    for name, data in entries:
        kind = data["type"]
        if kind == "harmful":
            badge_text, icon, concern_label = "HARMFUL", "⚠️", "Health concern"
        elif kind == "moderate":
            badge_text, icon, concern_label = "SEMI-HARMFUL", "🟡", "Worth watching"
        else:
            badge_text, icon, concern_label = "HEALTHY", "🌿", "Health benefit"

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


# ============================================================
#  ALLERGIES TAB
# ============================================================

YOUTUBE_VIDEO_ID = "9ZBCIVpFYgM"

with tab_allergies:

    render_greeting_and_stats()

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">Understanding allergic reactions</div>
            <p class="hero-sub">
                An allergic reaction starts when your immune system mistakes
                a harmless substance — like a food protein — for a threat.
                It releases chemicals such as histamine, which can trigger
                symptoms like hives, itching, swelling, an upset stomach, or
                trouble breathing within minutes to a couple of hours of
                exposure. Reactions can stay mild or escalate quickly into
                anaphylaxis, a severe, life-threatening reaction — so it's
                important to know what to watch for and act fast.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Quick tip ----
    st.markdown('<p class="section-title">⚡ Quick Tip</p>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="tip-card">
            <strong>If someone is having an allergic reaction:</strong>
            Stay calm and watch closely for signs it's getting worse
            (swelling of the lips/tongue/throat, trouble breathing,
            dizziness, or hives spreading). If they have a prescribed
            epinephrine auto-injector (EpiPen), use it right away —
            don't wait to see if symptoms improve on their own.
            Epinephrine is the only medication that can stop a severe
            reaction from progressing, and using it early is always
            safer than waiting.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Click-to-play YouTube video ----
    st.markdown('<p class="section-title">🎥 What to Do — Video Guide</p>', unsafe_allow_html=True)

    if "allergies_video_playing" not in st.session_state:
        st.session_state.allergies_video_playing = False

    if st.session_state.allergies_video_playing:
        st.video(f"https://youtu.be/{YOUTUBE_VIDEO_ID}")
        if st.button("← Back to preview", key="allergies_video_close"):
            st.session_state.allergies_video_playing = False
            st.rerun()
    else:
        st.markdown(
            f"""
            <div class="video-preview-wrap">
                <img src="https://img.youtube.com/vi/{YOUTUBE_VIDEO_ID}/hqdefault.jpg" alt="Video preview">
                <div class="video-play-button"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("▶  Play Video", key="allergies_video_play", type="primary"):
            st.session_state.allergies_video_playing = True
            st.rerun()

    st.write("")

    # ---- Emergency resources ----
    st.markdown('<p class="section-title">🚨 If It Gets Worse</p>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="emergency-card">
            <div class="emergency-card-title">📞 Call Emergency Services</div>
            <div class="emergency-card-body">
                In the US, call <strong>911</strong> immediately if you see
                signs of a severe reaction (anaphylaxis) — swelling of the
                face/throat, trouble breathing or swallowing, a rapid or
                weak pulse, dizziness, or fainting. Outside the US, call
                your local emergency number. Do this even after using an
                EpiPen — epinephrine can wear off, and a second reaction
                can follow.
            </div>
        </div>
        <div class="emergency-card">
            <div class="emergency-card-title">💉 Use Epinephrine First</div>
            <div class="emergency-card-body">
                If a person has a prescribed auto-injector, use it right
                away for any signs of a severe reaction — it's always
                better to use it too early than too late. A second dose
                can be given after about 5–15 minutes if symptoms haven't
                improved and more is available.
            </div>
        </div>
        <div class="emergency-card">
            <div class="emergency-card-title">🧍 While You Wait for Help</div>
            <div class="emergency-card-body">
                Help the person lie down and raise their legs, unless
                they're having trouble breathing or vomiting, in which
                case let them sit up or lie on their side. Loosen tight
                clothing, stay with them, and don't leave them alone.
            </div>
        </div>
        <div class="emergency-card">
            <div class="emergency-card-title">☎️ Poison Control (US)</div>
            <div class="emergency-card-body">
                For non-emergency questions about an ingredient or
                exposure, contact Poison Control at
                <strong>1-800-222-1222</strong>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "PureBites is an educational tool and does not replace professional "
        "medical advice. If you're ever unsure, treat it as an emergency."
    )


# ============================================================
#  GAMES TAB
# ============================================================

HEALTHY_CATCH_HEALTHY_EMOJIS = ["🍎", "🍇", "🥦", "🥕", "🍌", "🍓", "🥑", "🍊", "🍍", "🍉"]
HEALTHY_CATCH_UNHEALTHY_EMOJIS = ["🍩", "🍕", "🍫", "🧁", "🍟", "🍪", "🍭", "🥤"]

HEALTHY_CATCH_HTML = """
<style>
    * { box-sizing: border-box; }
    body { margin: 0; padding: 0; }

    .hc-app {
        max-width: 480px;
        margin: 0 auto;
        background-color: #FCF7E8;
        border: 1px solid #EADFC0;
        border-radius: 26px;
        padding: 18px 18px 20px 18px;
        box-shadow: 0 4px 16px rgba(82, 101, 57, 0.12);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        user-select: none;
    }

    .hc-badge {
        display: inline-block;
        background-color: #526539;
        color: #FFFFFF;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.06em;
        padding: 4px 14px;
        border-radius: 999px;
        margin-bottom: 8px;
    }

    .hc-title {
        font-size: 28px;
        font-weight: 900;
        color: #33421F;
        letter-spacing: 0.01em;
        line-height: 1.05;
        margin-bottom: 4px;
    }

    .hc-subtitle {
        font-size: 14px;
        color: #6B7A52;
        margin-bottom: 14px;
    }

    .hc-playfield {
        position: relative;
        width: 100%;
        height: 460px;
        border-radius: 20px;
        overflow: hidden;
        background: linear-gradient(180deg, #8FCBF2 0%, #CFEBFC 100%);
        box-shadow: inset 0 2px 10px rgba(0,0,0,0.08);
    }

    .hc-cloud {
        position: absolute;
        background-color: rgba(255,255,255,0.75);
        border-radius: 50%;
        z-index: 1;
    }

    .hc-hud {
        position: absolute;
        top: 12px;
        left: 12px;
        right: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        z-index: 5;
    }

    .hc-pill {
        background-color: rgba(255,255,255,0.95);
        border-radius: 999px;
        padding: 8px 14px;
        font-weight: 800;
        font-size: 15px;
        color: #33421F;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        border: none;
        cursor: pointer;
    }

    .hc-pause-btn {
        padding: 8px 13px;
        font-size: 16px;
        line-height: 1;
    }

    .hc-items-layer {
        position: absolute;
        inset: 0;
        z-index: 3;
    }

    .hc-food {
        position: absolute;
        font-size: 42px;
        line-height: 1;
        pointer-events: none;
        filter: drop-shadow(0 3px 4px rgba(0,0,0,0.18));
    }

    .hc-float {
        position: absolute;
        font-weight: 800;
        font-size: 20px;
        pointer-events: none;
        z-index: 6;
        animation: hc-float-up 0.7s ease forwards;
    }
    .hc-float-good { color: #2F7D32; }
    .hc-float-bad { color: #B23A3A; }

    @keyframes hc-float-up {
        0%   { transform: translateY(0);    opacity: 1; }
        100% { transform: translateY(-32px); opacity: 0; }
    }

    .hc-shelf {
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 46px;
        background: linear-gradient(180deg, #A5713E 0%, #7A4E28 100%);
        border-top: 3px solid #5E3B1E;
        z-index: 2;
    }

    .hc-cart {
        position: absolute;
        bottom: 46px;
        width: 74px;
        height: 64px;
        font-size: 52px;
        line-height: 64px;
        text-align: center;
        cursor: grab;
        z-index: 4;
        filter: drop-shadow(0 4px 5px rgba(0,0,0,0.25));
        touch-action: none;
    }
    .hc-cart:active { cursor: grabbing; }

    .hc-arrow {
        position: absolute;
        bottom: 54px;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #4C7A3D;
        color: #FFFFFF;
        border: none;
        font-size: 18px;
        font-weight: 800;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        cursor: pointer;
        z-index: 5;
    }
    .hc-arrow-left { left: 10px; }
    .hc-arrow-right { right: 10px; }

    .hc-overlay {
        position: absolute;
        inset: 0;
        background-color: rgba(252, 247, 232, 0.94);
        backdrop-filter: blur(2px);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 24px;
        z-index: 10;
    }

    .hc-overlay-emoji { font-size: 46px; margin-bottom: 6px; }

    .hc-overlay-title {
        font-size: 21px;
        font-weight: 900;
        color: #33421F;
        margin-bottom: 8px;
    }

    .hc-overlay-text {
        font-size: 14px;
        color: #5B6B47;
        margin-bottom: 18px;
        max-width: 300px;
    }

    .hc-overlay-summary {
        display: flex;
        gap: 18px;
        margin-bottom: 14px;
        flex-wrap: wrap;
        justify-content: center;
    }
    .hc-summary-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
    }
    .hc-summary-count {
        font-size: 26px;
        font-weight: 900;
    }
    .hc-summary-count.hc-count-good { color: #2F7D32; }
    .hc-summary-count.hc-count-bad { color: #B23A3A; }
    .hc-summary-label {
        font-size: 12px;
        font-weight: 700;
        color: #6B7A52;
    }

    .hc-overlay-fact {
        background-color: #EFF6E5;
        border: 1px solid #CADBAF;
        border-radius: 14px;
        padding: 12px 14px;
        font-size: 13px;
        line-height: 1.45;
        color: #33421F;
        margin-bottom: 20px;
        max-width: 320px;
    }

    .hc-duration-select {
        display: flex;
        gap: 10px;
        margin-bottom: 18px;
        width: 100%;
        max-width: 260px;
    }
    .hc-duration-btn {
        flex: 1;
        border: 2px solid #CADBAF;
        background-color: #FFFFFF;
        color: #526539;
        border-radius: 999px;
        padding: 9px 10px;
        font-size: 13px;
        font-weight: 800;
        cursor: pointer;
    }
    .hc-duration-btn.hc-duration-btn-active {
        background-color: #526539;
        border-color: #526539;
        color: #FFFFFF;
    }

    .hc-overlay-buttons {
        display: flex;
        flex-direction: column;
        gap: 10px;
        width: 100%;
        max-width: 260px;
    }

    .hc-btn {
        border: none;
        border-radius: 999px;
        padding: 13px 22px;
        font-size: 15px;
        font-weight: 800;
        cursor: pointer;
        width: 100%;
    }
    .hc-btn-primary { background-color: #526539; color: #FFFFFF; }
    .hc-btn-secondary { background-color: #FFFFFF; color: #526539; border: 2px solid #526539; }

    .hc-tip-banner {
        display: flex;
        align-items: center;
        gap: 10px;
        background-color: #E7F0DA;
        border: 1px solid #CADBAF;
        border-radius: 16px;
        padding: 12px 14px;
        margin-top: 14px;
    }
    .hc-tip-icon { font-size: 22px; }
    .hc-tip-title { font-weight: 800; color: #33421F; font-size: 14px; }
    .hc-tip-sub { font-size: 12.5px; color: #6B7A52; }
</style>

<div class="hc-app">
    <div class="hc-badge">GAME</div>
    <div class="hc-title">HEALTHY CATCH</div>
    <div class="hc-subtitle">Catch the healthy foods!</div>

    <div class="hc-playfield" id="hcPlayfield">
        <div class="hc-cloud" style="width:70px;height:26px;top:36px;left:20px;"></div>
        <div class="hc-cloud" style="width:50px;height:20px;top:70px;left:60px;"></div>
        <div class="hc-cloud" style="width:80px;height:28px;top:90px;right:24px;"></div>
        <div class="hc-cloud" style="width:54px;height:22px;top:120px;right:60px;"></div>

        <div class="hc-hud">
            <button class="hc-pill hc-pause-btn" id="hcPauseBtn">⏸</button>
            <div class="hc-pill">🍎 <span id="hcHealthyCount">0</span> &middot; 🍩 <span id="hcUnhealthyCount">0</span></div>
            <div class="hc-pill">⏱ <span id="hcTimer">01:00</span></div>
        </div>

        <div class="hc-items-layer" id="hcItemsLayer"></div>

        <div class="hc-cart" id="hcCart">🛒</div>

        <button class="hc-arrow hc-arrow-left" id="hcArrowLeft">←</button>
        <button class="hc-arrow hc-arrow-right" id="hcArrowRight">→</button>

        <div class="hc-shelf"></div>

        <div class="hc-overlay" id="hcStartOverlay">
            <div class="hc-overlay-emoji">🛒</div>
            <div class="hc-overlay-title">Ready to play?</div>
            <div class="hc-overlay-text">
                Drag your cart left and right to catch healthy foods and
                dodge the junk. Pick a round length to get started!
            </div>
            <div class="hc-duration-select" id="hcDurationSelect">
                <button class="hc-duration-btn" data-seconds="10">⚡ 10 Seconds</button>
                <button class="hc-duration-btn hc-duration-btn-active" data-seconds="60">⏱ 1 Minute</button>
            </div>
            <button class="hc-btn hc-btn-primary" id="hcStartBtn">▶ Start New Game</button>
        </div>

        <div class="hc-overlay" id="hcPauseOverlay" style="display:none;">
            <div class="hc-overlay-title">⏸ Paused</div>
            <button class="hc-btn hc-btn-primary" id="hcResumeBtn">▶ Resume</button>
        </div>

        <div class="hc-overlay" id="hcOverOverlay" style="display:none;">
            <div class="hc-overlay-emoji">🎉</div>
            <div class="hc-overlay-title">Round Over!</div>
            <div class="hc-overlay-summary" id="hcOverSummary"></div>
            <div class="hc-overlay-fact" id="hcOverFact"></div>
            <div class="hc-overlay-buttons" id="hcOverButtons"></div>
        </div>
    </div>

    <div class="hc-tip-banner">
        <span class="hc-tip-icon">🎯</span>
        <div>
            <div class="hc-tip-title">Catch healthy foods</div>
            <div class="hc-tip-sub">Avoid the unhealthy ones!</div>
        </div>
    </div>
</div>

<script>
(function () {
    const HEALTHY = __HEALTHY_JSON__;
    const UNHEALTHY = __UNHEALTHY_JSON__;

    // Facts about how healthy vs. unhealthy foods affect the body over
    // the long term — one is shown after each round, cycling through
    // the list in order (via roundsPlayed below) so a player doesn't
    // see the same fact twice in a row.
    const FACTS = [
        "Fruits and vegetables are packed with fiber, vitamins, and antioxidants that lower long-term risk of heart disease — while regularly eating sugary, fried foods raises that risk over time.",
        "Whole foods like fruit and veggies give you steady, lasting energy. Foods high in added sugar cause quick energy spikes followed by crashes that leave you more tired.",
        "A diet rich in produce supports a healthy gut microbiome, which affects digestion, immunity, and even mood — while heavily processed foods tend to disrupt it.",
        "Vegetables and fruit help maintain healthy blood sugar levels over time, while frequent sugary snacks and drinks are linked to a higher long-term risk of type 2 diabetes.",
        "Antioxidants in colorful fruits and vegetables help protect your cells from damage that builds up over years — a protection processed, sugary foods don't offer.",
        "Eating plenty of fruits and vegetables is linked to better long-term brain health, while diets high in processed and fried foods are linked to faster cognitive decline.",
    ];

    let roundsPlayed = 0;

    function nextFact() {
        const fact = FACTS[roundsPlayed % FACTS.length];
        roundsPlayed += 1;
        return fact;
    }

    const playfield = document.getElementById('hcPlayfield');
    const itemsLayer = document.getElementById('hcItemsLayer');
    const cart = document.getElementById('hcCart');
    const healthyCountEl = document.getElementById('hcHealthyCount');
    const unhealthyCountEl = document.getElementById('hcUnhealthyCount');
    const timerEl = document.getElementById('hcTimer');
    const startOverlay = document.getElementById('hcStartOverlay');
    const pauseOverlay = document.getElementById('hcPauseOverlay');
    const overOverlay = document.getElementById('hcOverOverlay');
    const overSummaryEl = document.getElementById('hcOverSummary');
    const overFactEl = document.getElementById('hcOverFact');
    const overButtons = document.getElementById('hcOverButtons');
    const pauseBtn = document.getElementById('hcPauseBtn');
    const startBtn = document.getElementById('hcStartBtn');
    const resumeBtn = document.getElementById('hcResumeBtn');
    const arrowLeft = document.getElementById('hcArrowLeft');
    const arrowRight = document.getElementById('hcArrowRight');
    const durationBtns = document.querySelectorAll('.hc-duration-btn');

    let ROUND_SECONDS = 60;
    const CART_WIDTH = 74;
    const CART_BOTTOM = 46;
    const CART_HEIGHT = 64;
    const ITEM_SIZE = 42;

    let healthyCaught = 0;
    let unhealthyCaught = 0;
    let timeLeft = ROUND_SECONDS;
    let items = [];
    let itemIdCounter = 0;
    let cartX = 0;
    let running = false;
    let paused = false;
    let lastSpawn = 0;
    let spawnGap = 1100;
    let rafId = null;
    let timerId = null;
    let dragging = false;
    let lastFrame = null;

    function fieldWidth() { return playfield.clientWidth; }
    function fieldHeight() { return playfield.clientHeight; }

    function clampCartX(x) {
        const max = fieldWidth() - CART_WIDTH;
        return Math.max(0, Math.min(max, x));
    }

    function setCartX(x) {
        cartX = clampCartX(x);
        cart.style.left = cartX + 'px';
    }

    function centerCart() {
        setCartX(fieldWidth() / 2 - CART_WIDTH / 2);
    }

    // ---- Dragging (mouse + touch, via Pointer Events) ----
    let dragStartClientX = 0;
    let dragStartCartX = 0;

    cart.addEventListener('pointerdown', function (e) {
        if (!running || paused) return;
        dragging = true;
        dragStartClientX = e.clientX;
        dragStartCartX = cartX;
        try { cart.setPointerCapture(e.pointerId); } catch (err) {}
    });
    playfield.addEventListener('pointermove', function (e) {
        if (!dragging) return;
        setCartX(dragStartCartX + (e.clientX - dragStartClientX));
    });
    window.addEventListener('pointerup', function () { dragging = false; });

    // Tap/click anywhere in the playfield to move the cart there directly —
    // makes the cart easy to control even without a precise drag.
    playfield.addEventListener('pointerdown', function (e) {
        if (!running || paused) return;
        if (e.target === cart) return;
        const rect = playfield.getBoundingClientRect();
        const x = e.clientX - rect.left;
        setCartX(x - CART_WIDTH / 2);
    });

    arrowLeft.addEventListener('click', function () {
        if (!running || paused) return;
        setCartX(cartX - 55);
    });
    arrowRight.addEventListener('click', function () {
        if (!running || paused) return;
        setCartX(cartX + 55);
    });

    // ---- Spawning ----
    function spawnItem() {
        const isHealthy = Math.random() < 0.55;
        const pool = isHealthy ? HEALTHY : UNHEALTHY;
        const emoji = pool[Math.floor(Math.random() * pool.length)];
        const x = Math.random() * (fieldWidth() - ITEM_SIZE);
        const el = document.createElement('div');
        el.className = 'hc-food';
        el.style.left = x + 'px';
        el.style.top = '-56px';
        el.textContent = emoji;
        itemsLayer.appendChild(el);
        items.push({
            id: itemIdCounter++,
            el: el,
            x: x,
            y: -56,
            healthy: isHealthy,
            speed: 55 + Math.random() * 25   // slow-medium fall speed (px/sec)
        });
    }

    function showFloatText(x, y, text, cls) {
        const el = document.createElement('div');
        el.className = 'hc-float ' + cls;
        el.style.left = x + 'px';
        el.style.top = y + 'px';
        el.textContent = text;
        itemsLayer.appendChild(el);
        setTimeout(function () { el.remove(); }, 700);
    }

    function updateCounts(isHealthy) {
        if (isHealthy) {
            healthyCaught += 1;
            healthyCountEl.textContent = healthyCaught;
        } else {
            unhealthyCaught += 1;
            unhealthyCountEl.textContent = unhealthyCaught;
        }
    }

    // ---- Main loop ----
    function loop(ts) {
        if (!running || paused) { rafId = null; return; }
        if (lastFrame === null) lastFrame = ts;
        const dt = (ts - lastFrame) / 1000;
        lastFrame = ts;

        if (ts - lastSpawn > spawnGap) {
            spawnItem();
            lastSpawn = ts;
            spawnGap = 850 + Math.random() * 650;
        }

        const cartTop = fieldHeight() - CART_BOTTOM - CART_HEIGHT;
        const cartLeft = cartX;
        const cartRight = cartX + CART_WIDTH;

        for (let i = items.length - 1; i >= 0; i--) {
            const it = items[i];
            it.y += it.speed * dt;
            it.el.style.top = it.y + 'px';

            const itCenterX = it.x + ITEM_SIZE / 2;
            if (it.y + ITEM_SIZE >= cartTop && it.y < cartTop + 44) {
                if (itCenterX >= cartLeft - 8 && itCenterX <= cartRight + 8) {
                    if (it.healthy) {
                        updateCounts(true);
                        showFloatText(it.x, it.y, '+1', 'hc-float-good');
                    } else {
                        updateCounts(false);
                        showFloatText(it.x, it.y, '+1', 'hc-float-bad');
                    }
                    it.el.remove();
                    items.splice(i, 1);
                    continue;
                }
            }

            if (it.y > fieldHeight()) {
                it.el.remove();
                items.splice(i, 1);
            }
        }

        rafId = requestAnimationFrame(loop);
    }

    // ---- Timer ----
    function formatTime(seconds) {
        const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
        const ss = String(seconds % 60).padStart(2, '0');
        return mm + ':' + ss;
    }

    function tick() {
        if (paused) return;
        timeLeft -= 1;
        timerEl.textContent = formatTime(timeLeft);
        if (timeLeft <= 0) {
            endGame();
        }
    }

    function selectDuration(seconds) {
        ROUND_SECONDS = seconds;
        durationBtns.forEach(function (btn) {
            const isActive = parseInt(btn.dataset.seconds, 10) === seconds;
            btn.classList.toggle('hc-duration-btn-active', isActive);
        });
        if (!running) {
            timeLeft = ROUND_SECONDS;
            timerEl.textContent = formatTime(ROUND_SECONDS);
        }
    }

    function startGame() {
        healthyCaught = 0;
        unhealthyCaught = 0;
        timeLeft = ROUND_SECONDS;
        healthyCountEl.textContent = '0';
        unhealthyCountEl.textContent = '0';
        timerEl.textContent = formatTime(ROUND_SECONDS);
        items.forEach(function (it) { it.el.remove(); });
        items = [];
        running = true;
        paused = false;
        lastFrame = null;
        lastSpawn = 0;
        centerCart();
        startOverlay.style.display = 'none';
        pauseOverlay.style.display = 'none';
        overOverlay.style.display = 'none';
        pauseBtn.textContent = '⏸';

        if (timerId) clearInterval(timerId);
        timerId = setInterval(tick, 1000);
        if (rafId) cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(loop);
    }

    function togglePause() {
        if (!running) return;
        paused = !paused;
        if (paused) {
            pauseOverlay.style.display = 'flex';
            pauseBtn.textContent = '▶';
        } else {
            pauseOverlay.style.display = 'none';
            pauseBtn.textContent = '⏸';
            lastFrame = null;
            rafId = requestAnimationFrame(loop);
        }
    }

    function endGame() {
        running = false;
        paused = false;
        clearInterval(timerId);
        if (rafId) cancelAnimationFrame(rafId);

        overSummaryEl.innerHTML =
            '<div class="hc-summary-item">' +
                '<div class="hc-summary-count hc-count-good">🍎 ' + healthyCaught + '</div>' +
                '<div class="hc-summary-label">Healthy caught</div>' +
            '</div>' +
            '<div class="hc-summary-item">' +
                '<div class="hc-summary-count hc-count-bad">🍩 ' + unhealthyCaught + '</div>' +
                '<div class="hc-summary-label">Unhealthy caught</div>' +
            '</div>';

        overFactEl.textContent = '💡 ' + nextFact();

        overButtons.innerHTML = '';

        const playAgainBtn = document.createElement('button');
        playAgainBtn.className = 'hc-btn hc-btn-primary';
        playAgainBtn.textContent = '🔄 Play Again';
        playAgainBtn.onclick = startGame;
        overButtons.appendChild(playAgainBtn);

        const exitBtn = document.createElement('button');
        exitBtn.className = 'hc-btn hc-btn-secondary';
        exitBtn.textContent = '🚪 Exit';
        exitBtn.onclick = exitGame;
        overButtons.appendChild(exitBtn);

        overOverlay.style.display = 'flex';
    }

    function exitGame() {
        overOverlay.style.display = 'none';
        startOverlay.style.display = 'flex';
        items.forEach(function (it) { it.el.remove(); });
        items = [];
        healthyCaught = 0;
        unhealthyCaught = 0;
        healthyCountEl.textContent = '0';
        unhealthyCountEl.textContent = '0';
        timerEl.textContent = formatTime(ROUND_SECONDS);
    }

    startBtn.addEventListener('click', startGame);
    resumeBtn.addEventListener('click', togglePause);
    pauseBtn.addEventListener('click', togglePause);
    durationBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            selectDuration(parseInt(btn.dataset.seconds, 10));
        });
    });

    centerCart();
    window.addEventListener('resize', function () { if (!dragging && !running) centerCart(); });
})();
</script>
"""

with tab_games:

    render_greeting_and_stats()

    st.markdown(
        """
        <div class="instruction-card">
            <strong>Healthy Catch</strong> — drag your cart left and right
            to catch falling foods. Try to catch the healthy foods and
            dodge the junk! Choose a 10-second or 1-minute round, then
            see how many of each you caught.
        </div>
        """,
        unsafe_allow_html=True,
    )

    _healthy_catch_html = (
        HEALTHY_CATCH_HTML
        .replace("__HEALTHY_JSON__", json.dumps(HEALTHY_CATCH_HEALTHY_EMOJIS))
        .replace("__UNHEALTHY_JSON__", json.dumps(HEALTHY_CATCH_UNHEALTHY_EMOJIS))
    )

    components.html(_healthy_catch_html, height=790, scrolling=False)


# ============================================================
#  PROFILE TAB
# ============================================================

with tab_profile:

    # ---- Profile picture ----
    if current_user["profile_picture"]:
        st.markdown(
            f"""
            <div class="profile-avatar-wrap">
                <img class="profile-avatar-img"
                     src="data:image/jpeg;base64,{current_user['profile_picture']}"
                     alt="Profile picture">
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        initial = display_name[0].upper() if display_name else "?"
        st.markdown(
            f"""
            <div class="profile-avatar-wrap">
                <div class="profile-avatar-placeholder">{html.escape(initial)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if is_guest_user(current_user):
        st.caption(
            "🔒 Create a free account to set a profile picture — guest "
            "sessions can't save one."
        )
    else:
        uploaded_pic = st.file_uploader(
            "Change profile picture",
            type=["png", "jpg", "jpeg"],
            key="profile_pic_uploader",
        )
        if uploaded_pic is not None:
            # file_uploader keeps returning the same file on every rerun until
            # a new one is chosen, so fingerprint it to avoid reprocessing
            # (and re-triggering st.rerun()) on every single interaction.
            pic_fingerprint = f"{uploaded_pic.name}-{uploaded_pic.size}"
            if st.session_state.get("last_uploaded_pic_fingerprint") != pic_fingerprint:
                picture_b64 = process_profile_picture(uploaded_pic)
                update_profile_picture(current_user["email"], picture_b64)
                current_user["profile_picture"] = picture_b64
                st.session_state.auth_user = current_user
                st.session_state.last_uploaded_pic_fingerprint = pic_fingerprint
                st.success("Profile picture updated!")
                st.rerun()

    profile_subtitle = (
        "Guest session — not saved" if is_guest_user(current_user)
        else current_user["email"]
    )
    st.markdown(
        f"""
        <div class="greeting-card">
            <div class="greeting-title">{html.escape(display_name)}</div>
            <div class="greeting-sub">{html.escape(profile_subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    prof_col1, prof_col2, prof_col3 = st.columns(3)
    with prof_col1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">{st.session_state.scan_count}</div>
                <div class="stat-label">Total Scans</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with prof_col2:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number"><span class="fire-emoji">🔥</span> {st.session_state.streak_count}</div>
                <div class="stat-label">Day Streak</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with prof_col3:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">{html.escape(current_user['created_at'])}</div>
                <div class="stat-label">Member Since</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # ---- Allergies ----
    st.markdown('<p class="section-title">🚫 Your Allergies</p>', unsafe_allow_html=True)
    if is_guest_user(current_user):
        st.caption(
            "Pick any allergies below — we'll warn you if a scanned "
            "product contains them. 🔒 As a guest, these won't be saved "
            "once you leave — create a free account to keep them."
        )
    else:
        st.caption(
            "Pick any allergies below — we'll warn you if a scanned product "
            "contains them. Add or remove allergies here any time."
        )

    current_allergies = get_user_allergies(current_user)

    def _save_allergies():
        selected = st.session_state.get("allergy_select", [])
        if not is_guest_user(current_user):
            update_user_allergies(current_user["email"], selected)
        current_user["allergies"] = json.dumps(selected)
        st.session_state.auth_user = current_user

    st.multiselect(
        "Your allergies",
        options=COMMON_ALLERGENS,
        default=current_allergies,
        key="allergy_select",
        on_change=_save_allergies,
        label_visibility="collapsed",
        placeholder="Search and select allergies...",
    )

    if current_allergies:
        chips_html = "".join(
            f'<span class="allergy-chip">{html.escape(a)}</span>'
            for a in current_allergies
        )
        st.markdown(chips_html, unsafe_allow_html=True)
    else:
        st.caption("No allergies saved yet.")

    st.write("")

    # ---- Dietary Restrictions ----
    st.markdown('<p class="section-title">🥗 Dietary Restrictions</p>', unsafe_allow_html=True)
    if is_guest_user(current_user):
        st.caption(
            "Pick any dietary preferences below — health concerns like "
            "diabetes, religious restrictions, or lifestyle choices like "
            "vegan and vegetarian. 🔒 As a guest, these won't be saved "
            "once you leave — create a free account to keep them."
        )
    else:
        st.caption(
            "Pick any dietary preferences below — health concerns like "
            "diabetes, religious restrictions, or lifestyle choices like "
            "vegan and vegetarian. Add or remove these here any time."
        )

    current_dietary_restrictions = get_user_dietary_restrictions(current_user)

    def _save_dietary_restrictions():
        selected = st.session_state.get("dietary_select", [])
        if not is_guest_user(current_user):
            update_user_dietary_restrictions(current_user["email"], selected)
        current_user["dietary_restrictions"] = json.dumps(selected)
        st.session_state.auth_user = current_user

    st.multiselect(
        "Your dietary restrictions",
        options=DIETARY_RESTRICTION_OPTIONS,
        default=current_dietary_restrictions,
        key="dietary_select",
        on_change=_save_dietary_restrictions,
        label_visibility="collapsed",
        placeholder="Search and select dietary preferences...",
    )

    if current_dietary_restrictions:
        dietary_chips_html = "".join(
            f'<span class="dietary-chip">{html.escape(d)}</span>'
            for d in current_dietary_restrictions
        )
        st.markdown(dietary_chips_html, unsafe_allow_html=True)
    else:
        st.caption("No dietary restrictions saved yet.")

    st.write("")
    st.write("")

    if st.button("Log Out", key="profile_logout"):
        st.session_state.auth_user = None
        st.session_state.scan_count = STARTING_SCAN_COUNT
        st.session_state.streak_count = 0
        st.session_state.last_result = None
        st.session_state.pop("allergy_select", None)
        st.session_state.pop("dietary_select", None)
        st.session_state.viewing_alternative_barcode = None
        st.session_state.pop("last_uploaded_pic_fingerprint", None)
        st.rerun()


# ============================================================
#  DONATE TAB
# ============================================================

FEEDING_AMERICA_DONATE_URL = (
    "https://give.feedingamerica.org/JikGJ41QV0GIR-DFe7Qciw2"
    "?r=n&ms=26-T2A&oa_onsite_promo=header"
)
FEEDING_AMERICA_LOGO_URL = (
    "https://www.feedingamerica.org/themes/custom/ts_feeding_america/"
    "images/svgs/logo-2020.svg"
)

with tab_donate:

    render_greeting_and_stats()

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">Support the fight against hunger</div>
            <p class="hero-sub">
                PureBites is about helping people eat safely — supporting
                these causes helps make sure people have enough to eat in
                the first place.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Feeding America ----
    st.markdown('<p class="section-title">🍽️ Feeding America</p>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="partner-card">
            <img class="partner-logo" src="{FEEDING_AMERICA_LOGO_URL}" alt="Feeding America logo">
            <div>
                <a class="donate-now-button" href="{FEEDING_AMERICA_DONATE_URL}" target="_blank" rel="noopener noreferrer">
                    Donate Now
                </a>
            </div>
            <div class="partner-statement">
                Feeding America is a nonprofit organization that supports
                millions of Americans struggling with hunger and food
                insecurity. Through a nationwide network of food banks,
                they turn donations into meals, delivering food directly
                to local communities so that no one has to go without.
                Every dollar donated helps stock food banks with fresh
                groceries, provide meals for children and seniors, and
                bring relief to families facing hard times. Supporting
                Feeding America means standing with neighbors across the
                country and helping build a future where hunger is no
                longer a barrier to a healthy life.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "You'll be taken to Feeding America's official, secure donation "
        "page in a new tab."
    )



with st.sidebar:
    st.header("🌿 About PureBites")

    st.write(
        "PureBites helps people understand the ingredients "
        "in the foods they eat."
    )

    st.divider()

    st.write("**Sprint 2**")
    st.write("Product scanning + full Ingredient Dictionary")

    st.caption(
        "PureBites is an educational tool and should not replace "
        "professional medical advice or official product labels."
    )

    st.divider()

    if is_guest_user(current_user):
        st.write("Browsing as **Guest**")
    else:
        st.write(f"Logged in as **{current_user['email']}**")
    if st.button("Log Out", key="sidebar_logout"):
        st.session_state.auth_user = None
        st.session_state.scan_count = STARTING_SCAN_COUNT
        st.session_state.streak_count = 0
        st.session_state.last_result = None
        st.session_state.pop("allergy_select", None)
        st.session_state.pop("dietary_select", None)
        st.session_state.viewing_alternative_barcode = None
        st.session_state.pop("last_uploaded_pic_fingerprint", None)
        st.rerun()
