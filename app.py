"""Ghithaaey app: Lab 7 + Lab 8 (Streamlit), with memory (Lab 14), tools (Lab 13) and n8n (Lab 15/16).
UI follows our Claude Design screens: navy leaf background, our logo, cards, right-to-left.

The user journey:
  1. ملفك: fill the profile once                -> no retyping age, height, weight in every chat
  2. خطتي: exact numbers, instantly             -> calculated in Python, not guessed by the AI
  3. قيمة الأكل: look up a food, pick grams, log it -> what is left today
  4. اسأل غذائي: the AI already knows the profile and today's log; answers cite MOH/WHO/SFDA
  5. المصادر: where every answer comes from

Run:  streamlit run app.py
Keys: .streamlit/secrets.toml (see secrets.toml.example)
"""
import base64
import json
from pathlib import Path

import streamlit as st

from assistant import ask, build_agent, new_thread_id
from settings import CONFIG, WEB_SOURCES, get_secret
from tools import FOOD_LOGS, PROFILES, check_food, compute_plan, parse_food, plan_blocker

ASSETS = Path(__file__).parent / "assets"
LOGO = ASSETS / "logo.png"
st.set_page_config(page_title="غذائي | Ghithaaey", page_icon=str(LOGO), layout="wide")


@st.cache_data
def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


# ---------- Lab 8: our design (colours from our logo, our background) ----------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&family=Inter:wght@500;600;700&display=swap');
:root {{ --ink:#F2F7FF; --muted:#A9BCDB; --soft:#CFDDF2; --line:rgba(120,170,255,.18); --blue:#5AB0FA; --btn:#2563EB;
        --card:rgba(10,30,68,.82); --tile:rgba(255,255,255,.06); --amber:#F5B454; --violet:#A78BFA; --green:#34D399; }}
.stApp {{ background:#04112B url(data:image/jpeg;base64,{b64(ASSETS / "background.jpg")}) center top / cover no-repeat fixed; }}
.stApp, .stApp * {{ font-family:'IBM Plex Sans Arabic', sans-serif; }}
.stApp .material-symbols-rounded, .stApp [data-testid="stIconMaterial"] {{ font-family:'Material Symbols Rounded' !important; }}
header[data-testid="stHeader"] {{ background:transparent; }}
.block-container {{ padding-top:2rem; max-width:1240px; }}
.stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stApp h1, .stApp h2, .stApp h3 {{ color:var(--ink); }}
[data-testid="stMainBlockContainer"], section[data-testid="stSidebar"] {{ direction:rtl; text-align:right; }}
[data-testid="stHorizontalBlock"] {{ direction:rtl; }}
section[data-testid="stSidebar"] {{ background:rgba(4,17,43,.86); backdrop-filter:blur(12px); border-left:1px solid var(--line); }}
.num {{ font-family:Inter,'IBM Plex Sans Arabic',sans-serif !important; font-variant-numeric:tabular-nums; }}

/* cards */
.g-card {{ background:var(--card); border:1px solid var(--line); border-radius:20px; padding:22px; backdrop-filter:blur(10px);
          box-shadow:0 10px 30px rgba(0,0,0,.25); direction:rtl; text-align:right; height:100%; box-sizing:border-box; }}
.g-hero {{ background:linear-gradient(135deg,#1B4FA0,#2F7FE6); border:0; }}
.g-label {{ font-size:13px; font-weight:500; color:var(--muted) !important; margin:0; }}
.g-title {{ font-size:16px; font-weight:600; margin:0 0 12px; }}
.g-big {{ font-size:30px; font-weight:700; line-height:1.1; margin:6px 0 0; }}
.g-row {{ display:flex; justify-content:space-between; align-items:center; gap:12px; padding:9px 0; border-bottom:1px solid rgba(255,255,255,.08); }}
.g-row:last-child {{ border-bottom:0; }}
.g-track {{ height:8px; border-radius:99px; background:rgba(255,255,255,.10); overflow:hidden; margin:12px 0 10px; }}
.g-track > div {{ height:100%; border-radius:99px; }}
.g-pill {{ font-size:12px; font-weight:600; color:#BFEFFF !important; background:rgba(90,176,250,.16); padding:4px 10px; border-radius:99px; }}
.g-tile {{ background:var(--tile); border-radius:14px; padding:14px; }}
.g-grid {{ display:grid; gap:12px; }}
.g-page-title {{ font-size:30px; font-weight:700; margin:2px 0 0; }}
.g-note {{ font-size:12px; color:var(--muted) !important; line-height:1.7; }}
.g-warn {{ background:rgba(245,180,84,.12); border:1px solid rgba(245,180,84,.35); border-radius:14px; padding:16px; color:#FBD38D !important; }}

/* inputs */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="base-input"], .stNumberInput input, .stTextInput input {{
    background:rgba(255,255,255,.05) !important; color:var(--ink) !important; border-color:rgba(120,170,255,.30) !important; border-radius:12px !important; }}
.stNumberInput button {{ background:rgba(255,255,255,.06) !important; color:var(--ink) !important; }}
[data-testid="stForm"] {{ background:var(--card); border:1px solid var(--line); border-radius:20px; padding:28px; backdrop-filter:blur(10px); }}
.stRadio [role="radiogroup"] {{ gap:8px; }}
.stRadio [role="radiogroup"] > label {{ background:rgba(255,255,255,.04); border:1px solid rgba(120,170,255,.30); border-radius:12px;
    padding:10px 14px; min-height:44px; margin:0; }}
.stRadio [role="radiogroup"] > label:has(input:checked) {{ border:2px solid var(--blue); background:rgba(90,176,250,.14); }}

/* buttons */
.stButton > button, .stFormSubmitButton > button {{ border-radius:12px; min-height:44px; font-weight:600;
    background:rgba(255,255,255,.04); color:var(--ink); border:1px solid rgba(120,170,255,.30); }}
.stButton > button:hover {{ border-color:var(--blue); color:#FFFFFF; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button {{ background:var(--btn); border:0; color:#FFFFFF; }}
.stButton > button[kind="primary"]:hover {{ background:#3B82F6; }}
[data-testid="stPills"] button, [data-testid="stButtonGroup"] button {{ background:rgba(255,255,255,.04); color:var(--ink); border-color:rgba(120,170,255,.30); }}
[data-testid="stPills"] button[aria-checked="true"], [data-testid="stButtonGroup"] button[aria-checked="true"] {{
    border:2px solid var(--blue); background:rgba(90,176,250,.16); }}

/* sidebar nav */
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{ padding-top:1rem; }}
[class*="st-key-nav_"] button {{ justify-content:flex-start; background:transparent; border:0; min-height:46px;
    padding:0 14px; color:#CFDDF2; font-size:15px; font-weight:500; direction:rtl; gap:10px; }}
[class*="st-key-nav_"] button:hover {{ background:rgba(255,255,255,.06); color:#FFFFFF; border:0; }}
[class*="st-key-nav_"] button[kind="primary"] {{ background:rgba(90,176,250,.16); color:#BFEFFF; font-weight:700;
    box-shadow:inset -3px 0 0 #5AB0FA; }}
[class*="st-key-nav_"] button p {{ font-size:15px; }}
[class*="st-key-nav_"] {{ margin-bottom:-10px; }}
.st-key-edit_profile button {{ min-height:36px; font-size:13px; }}
.st-key-new_chat button {{ background:transparent; border:1px solid rgba(248,113,113,.40); color:#FCA5A5; }}
.st-key-new_chat button:hover {{ border-color:#F87171; color:#FECACA; }}
.g-side-sep {{ height:1px; background:rgba(120,170,255,.16); margin:14px 0; }}

/* chat */
[data-testid="stChatMessage"] {{ background:var(--card); border:1px solid var(--line); border-radius:18px; padding:14px 16px; direction:rtl; }}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{ background:linear-gradient(135deg,#2563EB,#3B9BF5); border:0; }}
[data-testid="stChatMessageContent"] {{ text-align:right; }}
[data-testid="stChatInput"] {{ background:rgba(10,30,68,.92) !important; border:2px solid var(--blue); border-radius:16px; }}
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] [data-baseweb] {{ background:transparent !important; }}
[data-testid="stChatInput"] button {{ background:var(--btn) !important; color:#FFFFFF !important; border-radius:10px; }}
[data-testid="stSpinner"] p {{ color:var(--muted) !important; }}
[data-testid="stChatInput"], [data-testid="stChatInput"] > div {{ direction:rtl !important; }}
[data-testid="stChatInput"] textarea {{ color:var(--ink) !important; -webkit-text-fill-color:var(--ink); direction:rtl !important;
    text-align:right !important; unicode-bidi:plaintext; padding-right:16px !important; }}
[data-testid="stChatInput"] textarea::placeholder {{ text-align:right; }}
[data-testid="stChatInput"] textarea::placeholder {{ color:var(--muted) !important; -webkit-text-fill-color:var(--muted); }}
[data-testid="stBottomBlockContainer"], [data-testid="stBottom"] > div {{ background:transparent; }}
[data-testid="stExpander"] details {{ background:rgba(255,255,255,.03); border-color:var(--line); border-radius:12px; }}
a {{ color:var(--blue) !important; }}
</style>
""", unsafe_allow_html=True)

# ---------- Labels: the user sees Arabic, the tools get English values ----------
SEX = {"male": "ذكر", "female": "أنثى"}
ACTIVITY = {
    "sedentary": "قليل الحركة · شغل مكتبي بدون رياضة",
    "light": "خفيف · رياضة 1–3 أيام بالأسبوع",
    "moderate": "متوسط · رياضة 3–5 أيام بالأسبوع",
    "active": "عالي · رياضة 6–7 أيام بالأسبوع",
    "very_active": "عالي جداً · عمل بدني أو تمرين مرتين يومياً",
}
GOAL = {"lose": "إنقاص الوزن", "maintain": "المحافظة", "gain": "زيادة الوزن"}
CONDITION = {"none": "لا يوجد", "pregnancy": "حامل أو مرضعة", "diabetes": "السكري",
             "hypertension": "ضغط الدم المرتفع", "kidney": "أمراض الكلى", "other": "حالة أخرى"}
BMI_AR = {"underweight": ("نقص في الوزن", "#93C5FD"), "normal": ("وزن طبيعي", "#34D399"),
          "overweight": ("زيادة في الوزن", "#F5B454"), "obese": ("سمنة", "#F87171")}
MEAL_NAMES = ["الفطور", "الغداء", "العشاء", "وجبة خفيفة"]
# Common Saudi foods -> the USDA name our n8n workflow searches for
FOODS = {
    "تمر": "dates medjool", "رز أبيض مطبوخ": "rice white cooked", "رز بني مطبوخ": "rice brown cooked",
    "صدر دجاج مطبوخ": "chicken breast cooked", "لحم غنم مطبوخ": "lamb cooked", "سمك سلمون مطبوخ": "salmon cooked",
    "بيض مسلوق": "egg whole hard-boiled", "خبز أبيض": "bread white", "خبز بر": "bread whole-wheat",
    "شوفان": "oats", "عدس مطبوخ": "lentils cooked", "حمص مطبوخ": "chickpeas cooked", "فول مطبوخ": "fava beans cooked",
    "حليب كامل الدسم": "milk whole", "لبن زبادي": "yogurt plain whole milk", "جبن فيتا": "cheese feta",
    "تفاح": "apples raw", "موز": "bananas raw", "برتقال": "oranges raw", "خيار": "cucumber raw",
    "طماطم": "tomatoes raw", "بطاطس مسلوقة": "potatoes boiled", "لوز": "almonds", "زيت زيتون": "olive oil",
}
TOOL_LABELS = {"search_knowledge_base": "قاعدة المعرفة", "calculator": "الآلة الحاسبة", "nutrition_plan": "حاسبة التغذية",
               "save_profile": "حفظ بياناتك", "check_food": "القيم الغذائية (n8n)", "tavily_search": "بحث الويب"}
REQUIRED = ("age", "sex", "weight_kg", "height_cm", "activity", "goal")
PAGES = ["خطتي", "اسأل غذائي", "قيمة الأكل وسجل اليوم", "المصادر"]
PROFILE_PAGE = "ملفك"
NAV_ICONS = [":material/space_dashboard:", ":material/forum:", ":material/restaurant:", ":material/menu_book:"]


def html(markup: str):
    """Our cards are plain HTML (st.html keeps our styles, no markdown processing)."""
    st.html("".join(line.strip() for line in markup.splitlines()))


def n(x, digits=0) -> str:
    """Number with thousands separator, in Latin digits like the design."""
    return f'<span class="num">{x:,.{digits}f}</span>' if digits else f'<span class="num">{round(x):,}</span>'


def bar(value, goal, color) -> str:
    pct = 0 if not goal else max(0, min(value / goal, 1)) * 100
    return f'<div class="g-track"><div style="width:{pct:.0f}%;background:{color}"></div></div>'


def pick(options: dict, value):
    keys = list(options)
    return keys.index(value) if value in keys else None


@st.cache_resource(show_spinner=False)
def get_agent():
    return build_agent()


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def lookup_food(name: str) -> dict | None:
    """Same n8n workflow the agent uses; cached so the same food is not asked twice (USDA rate limit)."""
    return parse_food(check_food.invoke({"food": name}))


# ---------- Lab 14: one thread_id per chat ----------
if "thread_id" not in st.session_state:
    st.session_state.thread_id = new_thread_id()
    st.session_state.messages = []
thread = st.session_state.thread_id
profile = PROFILES.setdefault(thread, {})
food_log = FOOD_LOGS.setdefault(thread, [])
ready = all(k in profile for k in REQUIRED)
blocker = plan_blocker(profile) if ready else None
plan = compute_plan(profile) if ready and not blocker else None
eaten = {k: sum(item[k] for item in food_log) for k in ("kcal", "protein", "carbs", "fat")}
if not ready:
    st.session_state.page = PROFILE_PAGE
page = st.session_state.get("page", PAGES[0])

# ---------- Sidebar: logo, navigation, profile ----------
with st.sidebar:
    html(f"""<div style="display:flex;align-items:center;gap:12px;direction:rtl;margin-bottom:8px">
        <img src="data:image/png;base64,{b64(LOGO)}" alt="شعار غذائي" style="width:46px;height:46px;border-radius:12px">
        <div><p style="margin:0;font-size:20px;font-weight:700;color:#F2F7FF">غذائي</p>
        <p style="margin:0;font-size:12px;color:#A9BCDB">مساعدك الغذائي الموثوق</p></div></div>""")
    if ready:
        for name, icon in zip(PAGES, NAV_ICONS):
            if st.button(name, key=f"nav_{PAGES.index(name)}", icon=icon, width="stretch",
                         type="primary" if page == name else "secondary"):
                st.session_state.page = name
                st.rerun()
        html('<div class="g-side-sep"></div>')
        html(f"""<div class="g-card" style="padding:16px;border-radius:16px">
            <div style="display:flex;justify-content:space-between;align-items:center">
            <p class="g-label">ملفك</p><span class="g-pill">{GOAL[profile['goal']]}</span></div>
            <p style="margin:10px 0 0;font-size:15px;font-weight:700">{SEX[profile['sex']]} · {n(profile['age'])} سنة</p>
            <p style="margin:4px 0 0;font-size:13px;color:#A9BCDB">{n(profile['height_cm'])} سم · {n(profile['weight_kg'])} كجم ·
            نشاط {ACTIVITY[profile['activity']].split(' ·')[0]}</p></div>""")
        if st.button("تعديل الملف", key="edit_profile", icon=":material/edit:", width="stretch",
                     type="primary" if page == PROFILE_PAGE else "secondary"):
            st.session_state.page = PROFILE_PAGE
            st.rerun()
        html('<div class="g-side-sep"></div>')
    if st.button("محادثة جديدة", key="new_chat", icon=":material/restart_alt:", width="stretch",
                 help="تبدأ من جديد وتمسح ملفك وسجل اليوم"):
        PROFILES.pop(thread, None)  # privacy (Lab 4): nothing is kept after a new chat
        FOOD_LOGS.pop(thread, None)
        st.session_state.clear()
        st.rerun()
    html('<p class="g-note" style="direction:rtl">بياناتك تبقى في هذه الجلسة فقط ولا تُحفظ على أي خادم.</p>')
    html(f'<p class="g-note" style="direction:rtl">{CONFIG["disclaimer"]}</p>')


# ---------- Page: ملفك (onboarding / edit profile) ----------
def page_profile():
    form_col, side_col = st.columns([3, 2], gap="large")
    with form_col:
        with st.form("profile"):
            html("""<h1 class="g-page-title" style="direction:rtl;color:#F2F7FF">خلّنا نعرفك</h1>
                <p style="direction:rtl;color:#A9BCDB;font-size:16px;line-height:1.7;margin:8px 0 0">عبّي بياناتك مرة وحدة، ونحسب لك
                احتياجك اليومي بدقة، وغذائي يجاوبك على أساسها بدون ما يسألك من جديد.</p>
                <p style="direction:rtl;color:#5AB0FA;font-weight:600;font-size:13px;margin:22px 0 0">١ · عنك</p>""")
            sex = st.radio("الجنس", list(SEX), pick(SEX, profile.get("sex")), format_func=SEX.get, horizontal=True)
            c = st.columns(3)
            age = c[0].number_input("العمر (سنة)", 10, 100, profile.get("age"), placeholder="25")
            height = c[1].number_input("الطول (سم)", 120.0, 230.0, profile.get("height_cm"), 1.0, placeholder="175")
            weight = c[2].number_input("الوزن (كجم)", 30.0, 300.0, profile.get("weight_kg"), 0.5, placeholder="80")
            html('<p style="direction:rtl;color:#5AB0FA;font-weight:600;font-size:13px;margin:18px 0 0">٢ · نشاطك اليومي</p>')
            activity = st.radio("مستوى النشاط", list(ACTIVITY), pick(ACTIVITY, profile.get("activity")),
                                format_func=ACTIVITY.get, label_visibility="collapsed")
            html('<p style="direction:rtl;color:#5AB0FA;font-weight:600;font-size:13px;margin:18px 0 0">٣ · هدفك</p>')
            goal = st.radio("هدفك", list(GOAL), pick(GOAL, profile.get("goal")), format_func=GOAL.get,
                            horizontal=True, label_visibility="collapsed")
            target = st.number_input("الوزن المستهدف (اختياري، كجم)", 30.0, 300.0, profile.get("target_weight_kg"), 0.5,
                                     placeholder="—")
            html("""<p style="direction:rtl;color:#5AB0FA;font-weight:600;font-size:13px;margin:18px 0 0">٤ · صحتك</p>
                <p style="direction:rtl;color:#A9BCDB;font-size:14px;margin:4px 0 0">إذا عندك حالة خاصة، ما نعطيك أرقام سعرات،
                ونوجهك للطبيب أو أخصائي التغذية.</p>""")
            condition = st.radio("الحالة الصحية", list(CONDITION), pick(CONDITION, profile.get("condition", "none")),
                                 format_func=CONDITION.get, horizontal=True, label_visibility="collapsed")
            saved = st.form_submit_button("احسب خطتي", width="stretch")
        if saved:
            values = dict(age=age, sex=sex, height_cm=height, weight_kg=weight, activity=activity, goal=goal)
            if any(v is None for v in values.values()):
                st.error("كمّل الحقول: الجنس، العمر، الطول، الوزن، النشاط، والهدف.")
            else:
                profile.clear()
                profile.update(values, condition=condition)
                if target and goal != "maintain":
                    profile["target_weight_kg"] = target
                st.session_state.page = PAGES[0]
                st.rerun()
    with side_col:
        if plan:
            html(f"""<div class="g-card g-hero">
                <p class="g-label" style="color:#BFEFFF !important">خطتك الحالية</p>
                <p class="g-big num" style="font-size:46px">{plan['target']:,}</p>
                <p style="margin:4px 0 16px;color:#CFE0F7">سعرة يومياً · {GOAL[plan['goal']]}</p>
                <div class="g-grid" style="grid-template-columns:repeat(3,1fr)">
                <div class="g-tile" style="background:rgba(255,255,255,.10)"><p class="g-label" style="color:#CFE0F7 !important">بروتين</p><p class="num" style="margin:4px 0 0;font-size:18px;font-weight:700">{plan['protein']} g</p></div>
                <div class="g-tile" style="background:rgba(255,255,255,.10)"><p class="g-label" style="color:#CFE0F7 !important">كربوهيدرات</p><p class="num" style="margin:4px 0 0;font-size:18px;font-weight:700">{plan['carbs']} g</p></div>
                <div class="g-tile" style="background:rgba(255,255,255,.10)"><p class="g-label" style="color:#CFE0F7 !important">دهون</p><p class="num" style="margin:4px 0 0;font-size:18px;font-weight:700">{plan['fat']} g</p></div>
                </div></div>""")
        tick = '<span style="color:#5AB0FA;font-weight:700">✓</span>'
        html(f"""<div class="g-card" style="margin-top:16px">
            <p class="g-title">ليش نسأل؟</p>
            <p style="line-height:1.8;margin:0 0 10px">{tick} العمر والطول والوزن والجنس تحدد حرقك وقت الراحة.</p>
            <p style="line-height:1.8;margin:0 0 10px">{tick} النشاط يحدد سعرات الثبات، والهدف يحدد الزيادة أو النقص.</p>
            <p style="line-height:1.8;margin:0">{tick} الحالة الصحية تحميك: بعض الحالات تحتاج طبيب، مو أرقام عامة.</p>
            </div>
            <p class="g-note" style="direction:rtl;margin-top:12px">مبني على إرشادات وزارة الصحة ومنظمة الصحة العالمية والهيئة العامة للغذاء والدواء.</p>""")


# ---------- Page: خطتي (calculated directly, no AI, no waiting) ----------
def page_plan():
    html('<p class="g-label" style="direction:rtl">احتياجك اليومي</p><h1 class="g-page-title" style="direction:rtl">خطتك اليوم</h1>')
    if blocker:
        if blocker.startswith("MEDICAL_CONDITION"):
            msg = (f"لأن عندك حالة خاصة ({CONDITION[profile['condition']]})، ما نعطيك أرقام سعرات أو ماكروز. احتياجك يحدده "
                   "الطبيب أو أخصائي التغذية. تقدر تسأل غذائي عن معلومات التغذية العامة من مصادر وزارة الصحة.")
        elif blocker.startswith("UNDER_18"):
            msg = "للأعمار تحت 18 سنة ما نعطي أهداف سعرات. الأفضل تتكلم مع أهلك والطبيب."
        else:
            msg = "الطول أو الوزن يبدو غير صحيح، راجع ملفك."
        html(f'<div class="g-warn" style="direction:rtl;margin-top:16px">{msg}</div>')
        return

    left = plan["target"] - eaten["kcal"]
    circ = 527.8
    done = circ * max(0, min(eaten["kcal"] / plan["target"], 1))
    ring_col, macro_col = st.columns([1.1, 2], gap="medium")
    with ring_col:
        html(f"""<div class="g-card" style="text-align:center">
            <div style="display:flex;justify-content:space-between;align-items:center"><p class="g-title" style="margin:0">السعرات</p>
            <span class="g-pill">{GOAL[plan['goal']]}</span></div>
            <div style="position:relative;width:200px;height:200px;margin:14px auto">
            <svg width="200" height="200" viewBox="0 0 200 200" role="img" aria-label="السعرات اليوم">
            <circle cx="100" cy="100" r="84" fill="none" stroke="rgba(255,255,255,.10)" stroke-width="16"></circle>
            <circle cx="100" cy="100" r="84" fill="none" stroke="#5AB0FA" stroke-width="16" stroke-linecap="round"
             stroke-dasharray="{done:.1f} {circ}" transform="rotate(-90 100 100)"></circle></svg>
            <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center">
            <span class="num" style="font-size:38px;font-weight:700;line-height:1">{abs(left):,.0f}</span>
            <span style="font-size:13px;color:#A9BCDB;margin-top:6px">{'سعرة باقية' if left >= 0 else 'سعرة زيادة'}</span></div></div>
            <div style="display:grid;grid-template-columns:1fr 1fr;border-top:1px solid rgba(255,255,255,.10);padding-top:14px">
            <div><p class="g-label">هدفك اليومي</p><p class="num" style="margin:4px 0 0;font-size:20px;font-weight:700">{plan['target']:,}</p></div>
            <div style="border-right:1px solid rgba(255,255,255,.10)"><p class="g-label">أكلت</p>
            <p class="num" style="margin:4px 0 0;font-size:20px;font-weight:700">{eaten['kcal']:,.0f}</p></div></div></div>""")
    with macro_col:
        cards = ""
        for key, label, color, hint in (("protein", "البروتين", "#5AB0FA", "يبني العضل ويشبعك"),
                                        ("carbs", "الكربوهيدرات", "#F5B454", "فضّل الحبوب الكاملة"),
                                        ("fat", "الدهون", "#A78BFA", "زيت الزيتون والمكسرات")):
            goal_g, got = plan[key], eaten[key]
            cards += f"""<div class="g-card"><div style="display:flex;justify-content:space-between;align-items:center">
                <p class="g-title" style="margin:0">{label}</p><span style="width:10px;height:10px;border-radius:99px;background:{color}"></span></div>
                <p style="margin:12px 0 0"><span class="num" style="font-size:30px;font-weight:700">{got:.0f}</span>
                <span class="num" style="font-size:15px;color:#A9BCDB"> / {goal_g} g</span></p>{bar(got, goal_g, color)}
                <p class="g-label">باقي {n(max(goal_g - got, 0))} جم · {hint}</p></div>"""
        protein_left = plan["protein"] - eaten["protein"]
        if protein_left > 5:
            chicken = int(round(min(protein_left, 50) / 0.31, -1))  # cooked chicken breast ≈ 31 g protein / 100 g (USDA)
            tip = f"باقي لك {n(protein_left)} جم بروتين. صدر دجاج {n(chicken)} جم يعطيك حوالي {n(chicken * 0.31)} جم منه."
        else:
            tip = "وصلت لهدف البروتين اليوم. كمّل باقي سعراتك بالخضار والحبوب الكاملة."
        html(f"""<div class="g-grid" style="grid-template-columns:repeat(3,1fr);direction:rtl">{cards}</div>
            <div class="g-card g-hero" style="margin-top:12px;display:flex;align-items:center;gap:14px;padding:16px 20px">
            <p style="margin:0;flex:1;font-size:15px">{tip}</p></div>""")

    st.write("")
    bmi_col, goal_col = st.columns([2, 1], gap="medium")
    bmi_label, bmi_color = BMI_AR.get(plan["bmi_category"], (plan["bmi_category"], "#F2F7FF"))
    with bmi_col:
        marker = max(0, min(plan["bmi"], 40)) / 40 * 100
        html(f"""<div class="g-card"><p class="g-title">جسمك</p>
            <div class="g-grid" style="grid-template-columns:repeat(4,1fr)">
            <div><p class="g-label">مؤشر كتلة الجسم</p><p class="g-big num">{plan['bmi']}</p><p style="margin:2px 0 0;font-size:13px;font-weight:600;color:{bmi_color}">{bmi_label}</p></div>
            <div><p class="g-label">الوزن الصحي لطولك</p><p class="g-big num">{plan['healthy_min']}–{plan['healthy_max']}</p><p class="g-label">كجم</p></div>
            <div><p class="g-label">الحرق وقت الراحة</p><p class="g-big num">{plan['bmr']:,}</p><p class="g-label">سعرة · BMR</p></div>
            <div><p class="g-label">سعرات الثبات</p><p class="g-big num">{plan['tdee']:,}</p><p class="g-label">سعرة · مع نشاطك</p></div></div>
            <div dir="ltr" style="position:relative;display:grid;grid-template-columns:18.5fr 6.5fr 5fr 10fr;gap:4px;height:10px;margin-top:22px">
            <div style="background:#93C5FD;border-radius:99px"></div><div style="background:#34D399;border-radius:99px"></div>
            <div style="background:#F5B454;border-radius:99px"></div><div style="background:#F87171;border-radius:99px"></div>
            <div style="position:absolute;left:{marker:.1f}%;top:-5px;width:4px;height:20px;background:#FFFFFF;border-radius:2px"></div></div>
            <div dir="ltr" style="display:grid;grid-template-columns:18.5fr 6.5fr 5fr 10fr;gap:4px;margin-top:8px;font-size:12px;color:#A9BCDB">
            <span>نقص</span><span>طبيعي</span><span>زيادة</span><span>سمنة</span></div></div>""")
    with goal_col:
        if plan["weeks"]:
            body = (f"""<div style="display:flex;align-items:baseline;gap:12px"><span class="num" style="font-size:28px;font-weight:700">{profile['weight_kg']:g}</span>
                <span style="color:#A9BCDB">←</span><span class="num" style="font-size:28px;font-weight:700;color:#5AB0FA">{plan['target_weight']:g}</span>
                <span style="color:#A9BCDB">كجم</span></div>
                <p style="margin:12px 0 0;font-size:15px">حوالي <b class="num">{plan['weeks']}</b> أسبوع بمعدل آمن {n(plan['per_week'], 1)} كجم بالأسبوع</p>""")
            if plan["target_too_low"]:
                body += f'<p style="margin:10px 0 0;color:#FBD38D;font-size:14px">هدفك أقل من الوزن الصحي لطولك ({plan["healthy_min"]} كجم). ننصحك بهدف أعلى.</p>'
        else:
            body = f'<p style="margin:0;font-size:15px">{GOAL[plan["goal"]]}. أضف وزن مستهدف في ملفك لنحسب لك المدة.</p>'
        delta = plan["target"] - plan["tdee"]
        html(f"""<div class="g-card"><p class="g-title">هدفك</p>{body}
            <p class="g-label" style="margin-top:12px">{'عجز' if delta < 0 else 'زيادة'} {n(abs(delta))} سعرة يومياً عن سعرات الثبات.</p>
            {'<p class="g-label">رفعنا السعرات للحد الأدنى الآمن.</p>' if plan['raised_to_minimum'] else ''}</div>""")

    st.write("")
    meals_col, limits_col, log_col = st.columns(3, gap="medium")
    with meals_col:
        rows = "".join(f'<div class="g-row"><span>{m.split("/ ")[-1]}</span><span class="num" style="font-weight:600">{k:,} kcal</span></div>'
                       for m, k in plan["meals"].items())
        html(f'<div class="g-card"><p class="g-title">توزيع الوجبات</p>{rows}</div>')
    with limits_col:
        html(f"""<div class="g-card"><p class="g-title">يومياً</p>
            <div class="g-row"><span>الماء</span><b>على الأقل {n(plan['water'], 1)} لتر</b></div>
            <div class="g-row"><span>الألياف</span><b>حوالي {n(plan['fiber'])} جم</b></div>
            <div class="g-row"><span>السكر المضاف</span><b>أقل من {n(plan['sugar_max'])} جم</b></div>
            <div class="g-row"><span>الدهون المشبعة</span><b>أقل من {n(plan['sat_fat_max'])} جم</b></div>
            <div class="g-row"><span>الملح</span><b>أقل من {n(5)} جم</b></div></div>""")
    with log_col:
        rows = "".join(f"""<div class="g-row"><div><p style="margin:0;font-weight:600">{item['name']}</p>
            <p class="g-label">{n(item['grams'])} جم · {item.get('meal', '')}</p></div><span class="num" style="font-weight:600">{item['kcal']:.0f}</span></div>"""
                       for item in food_log[-4:]) or '<p class="g-label">ما سجلت شي اليوم. أضف أكلك من «قيمة الأكل وسجل اليوم».</p>'
        html(f'<div class="g-card"><p class="g-title">أكلك اليوم</p>{rows}</div>')
    html('<p class="g-note" style="direction:rtl;margin-top:12px">الأرقام محسوبة بمعادلة Mifflin-St Jeor وإرشادات وزارة الصحة '
         'ومنظمة الصحة العالمية. تقديرات عامة للبالغين الأصحاء وليست استشارة طبية.</p>')


# ---------- Page: اسأل غذائي (the AI already knows the profile and today's log) ----------
def page_chat():
    chat_col, side_col = st.columns([3, 1.1], gap="large")
    with chat_col:
        html('<h1 class="g-page-title" style="direction:rtl">اسأل غذائي</h1><p class="g-label" style="direction:rtl;margin-top:4px">'
             'يجاوبك من مصادر وزارة الصحة ومنظمة الصحة العالمية والغذاء والدواء، ويذكر المصدر.</p>')
        box = st.container(height=520, border=False)
        with box:
            if not st.session_state.messages:
                html(f'<div class="g-card" style="margin-top:8px"><p style="margin:0;line-height:1.8">{CONFIG["welcome"]}</p></div>')
            for message in st.session_state.messages:
                avatar = str(LOGO) if message["role"] == "assistant" else ":material/person:"
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])
                    if message.get("tools"):
                        st.caption("الأدوات: " + " · ".join(dict.fromkeys(TOOL_LABELS.get(s["tool"], s["tool"]) for s in message["tools"])))
            pending = st.session_state.pop("awaiting", None)
            if pending:
                with st.chat_message("assistant", avatar=str(LOGO)):
                    with st.spinner("غذائي يفكر…"):
                        try:
                            answer, tool_log = ask(get_agent(), pending, thread)
                        except Exception:
                            answer, tool_log = CONFIG["friendly_error"], []
                st.session_state.messages.append({"role": "assistant", "content": answer, "tools": tool_log})
                st.rerun()
        examples = (["اشرح لي خطتي ببساطة", "كم باقي لي سعرات اليوم؟", "وش أفطر عشان أوصل لبروتيني؟"] if plan else []) \
            + CONFIG["examples"]
        chip = st.pills("اقتراحات", examples[:5], label_visibility="collapsed", key=f"chip{len(st.session_state.messages)}")
        question = st.chat_input("اسألني أي شي عن التغذية…") or chip
        if question:
            st.session_state.messages.append({"role": "user", "content": question})
            st.session_state.awaiting = question
            st.rerun()
        html('<p class="g-note" style="text-align:center">غذائي يعطي معلومات عامة وليس بديلاً عن الطبيب أو أخصائي التغذية.</p>')
    with side_col:
        today = ""
        if plan:
            today = f"""<div style="border-top:1px solid rgba(255,255,255,.10);margin-top:14px;padding-top:14px">
                <p class="g-title" style="font-size:14px">اليوم</p>
                <div style="display:flex;justify-content:space-between;font-size:14px"><span class="g-label">السعرات</span><span class="num">{eaten['kcal']:,.0f} / {plan['target']:,}</span></div>
                {bar(eaten['kcal'], plan['target'], '#5AB0FA')}
                <div style="display:flex;justify-content:space-between;font-size:14px"><span class="g-label">البروتين</span><span class="num">{eaten['protein']:.0f} / {plan['protein']} g</span></div>
                {bar(eaten['protein'], plan['protein'], '#5AB0FA')}</div>"""
        target = f"إلى {n(profile['target_weight_kg'])} كجم" if profile.get("target_weight_kg") else ""
        html(f"""<div class="g-card"><p class="g-title" style="margin-bottom:2px">غذائي يعرف عنك</p>
            <p class="g-label" style="margin-bottom:10px">ما يحتاج تعيد بياناتك في كل سؤال.</p>
            <div class="g-row"><span class="g-label">العمر</span><span class="num">{profile['age']}</span></div>
            <div class="g-row"><span class="g-label">الطول / الوزن</span><span class="num">{profile['height_cm']:g} / {profile['weight_kg']:g}</span></div>
            <div class="g-row"><span class="g-label">النشاط</span><span>{ACTIVITY[profile['activity']].split(' ·')[0]}</span></div>
            <div class="g-row"><span class="g-label">الهدف</span><span>{GOAL[profile['goal']]} {target}</span></div>
            <div class="g-row"><span class="g-label">حالة صحية</span><span>{CONDITION[profile.get('condition', 'none')]}</span></div>
            {today}</div>
            <div class="g-warn" style="margin-top:14px;direction:rtl;font-size:13px;line-height:1.7">إذا عندك حالة صحية أو حامل، غذائي ما يعطيك أرقام سعرات ويوجهك للطبيب.</div>""")


# ---------- Page: قيمة الأكل وسجل اليوم (n8n + USDA) ----------
def page_food():
    html('<p class="g-label" style="direction:rtl">بيانات رسمية من USDA FoodData Central</p><h1 class="g-page-title" style="direction:rtl">قيمة الأكل</h1>')
    main_col, log_col = st.columns([1.4, 1], gap="large")
    with main_col:
        if not get_secret("N8N_URL"):
            html('<div class="g-warn" style="direction:rtl">أداة القيم الغذائية تحتاج رابط n8n (N8N_URL) في ملف الأسرار.</div>')
        else:
            c1, c2 = st.columns([2, 1])
            choice = c1.selectbox("وش أكلت؟", list(FOODS) + ["أكل آخر (اكتبه بالإنجليزي)"])
            grams = c2.number_input("الكمية (جم)", 1, 2000, st.session_state.get("grams", 100), 10)
            custom = st.text_input("اسم الأكل بالإنجليزي", placeholder="e.g. hummus, kabsa, dates") if choice not in FOODS else ""
            quick = st.segmented_control("كمية سريعة", [50, 100, 150, 200], format_func=lambda g: f"{g} g", key="quick")
            if quick and quick != st.session_state.get("last_quick"):
                st.session_state.grams = st.session_state.last_quick = quick
                st.rerun()
            if st.button("احسب القيم", type="primary", width="stretch"):
                name = FOODS.get(choice) or custom.strip()
                if not name:
                    st.error("اكتب اسم الأكل.")
                else:
                    with st.spinner("نجيب القيم من USDA…"):
                        result = lookup_food(name)
                    st.session_state.food_result = {"label": choice if choice in FOODS else name, **result} if result else None
                    if not result:
                        st.error("ما لقينا هذا الأكل. جرّب اسم أبسط بالإنجليزي، مثل: rice white cooked.")

            r = st.session_state.get("food_result")
            if r:
                f = grams / 100
                kcal = r["kcal"] * f
                share = ""
                if plan:
                    after = plan["target"] - eaten["kcal"] - kcal
                    share = f"""<p class="g-label" style="margin-top:16px">من هدفك اليومي</p>{bar(kcal, plan['target'], '#5AB0FA')}
                        <p style="margin:0;font-size:14px;color:#CFDDF2">هذي الأكلة {n(kcal / plan['target'] * 100)}% من سعراتك اليوم ·
                        بعدها يبقى لك {n(after)} سعرة</p>"""
                html(f"""<div class="g-card" style="margin-top:12px">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
                    <div><p style="margin:0;font-size:20px;font-weight:700">{r['label']} · {n(grams)} جم</p>
                    <p class="g-label" dir="ltr" style="text-align:right;margin-top:4px">USDA: {r['name']}</p></div><span class="g-pill">مصدر رسمي</span></div>
                    <div class="g-grid" style="grid-template-columns:1.2fr 1fr 1fr 1fr;margin-top:16px">
                    <div class="g-tile"><p class="g-label">السعرات</p><p class="g-big num">{kcal:.0f}</p></div>
                    <div class="g-tile"><p class="g-label">بروتين</p><p class="num" style="margin:8px 0 0;font-size:22px;font-weight:700;color:#5AB0FA">{r['protein'] * f:.1f} g</p></div>
                    <div class="g-tile"><p class="g-label">كربوهيدرات</p><p class="num" style="margin:8px 0 0;font-size:22px;font-weight:700;color:#F5B454">{r['carbs'] * f:.1f} g</p></div>
                    <div class="g-tile"><p class="g-label">دهون</p><p class="num" style="margin:8px 0 0;font-size:22px;font-weight:700;color:#A78BFA">{r['fat'] * f:.1f} g</p></div></div>
                    {share}
                    <div class="g-grid" style="grid-template-columns:repeat(3,1fr);margin-top:14px;font-size:14px;color:#CFDDF2">
                    <span>السكريات <b class="num">{r['sugars'] * f:.1f}</b> جم</span><span>الألياف <b class="num">{r['fiber'] * f:.1f}</b> جم</span>
                    <span>الصوديوم <b class="num">{r['sodium_mg'] * f:.0f}</b> ملجم</span></div></div>""")
                m1, m2 = st.columns([1, 2])
                meal = m1.selectbox("الوجبة", MEAL_NAMES)
                m2.write("")
                if m2.button("أضف لسجل اليوم", type="primary", width="stretch"):
                    food_log.append({"name": r["label"], "grams": grams, "meal": meal, "kcal": kcal, "protein": r["protein"] * f,
                                     "carbs": r["carbs"] * f, "fat": r["fat"] * f})
                    st.toast(f"أضفنا {r['label']} لسجل اليوم")
                    st.rerun()
    with log_col:
        top = ""
        if plan:
            top = f"""<div style="display:flex;justify-content:space-between"><span class="g-label">السعرات</span>
                <span class="num" style="font-weight:600">{eaten['kcal']:,.0f} / {plan['target']:,}</span></div>{bar(eaten['kcal'], plan['target'], '#5AB0FA')}
                <div class="g-grid" style="grid-template-columns:repeat(3,1fr);text-align:center;margin-bottom:8px">
                <div class="g-tile" style="padding:10px"><p class="g-label">بروتين</p><p class="num" style="margin:4px 0 0;font-weight:700">{eaten['protein']:.0f} / {plan['protein']}</p></div>
                <div class="g-tile" style="padding:10px"><p class="g-label">كربوهيدرات</p><p class="num" style="margin:4px 0 0;font-weight:700">{eaten['carbs']:.0f} / {plan['carbs']}</p></div>
                <div class="g-tile" style="padding:10px"><p class="g-label">دهون</p><p class="num" style="margin:4px 0 0;font-weight:700">{eaten['fat']:.0f} / {plan['fat']}</p></div></div>"""
        groups = ""
        for meal in MEAL_NAMES:
            items = [i for i in food_log if i.get("meal") == meal]
            if items:
                groups += f'<p class="g-label" style="margin-top:14px;font-weight:600">{meal}</p>' + "".join(
                    f"""<div class="g-row"><div><p style="margin:0;font-weight:600">{i['name']}</p><p class="g-label">{n(i['grams'])} جم</p></div>
                    <span class="num" style="font-weight:600">{i['kcal']:.0f}</span></div>""" for i in items)
        if not food_log:
            groups = '<p class="g-label" style="margin-top:12px">ما سجلت شي اليوم.</p>'
        html(f'<div class="g-card"><p class="g-title" style="font-size:18px">سجل اليوم</p>{top}{groups}</div>')
        if food_log and st.button("مسح السجل", width="stretch"):
            food_log.clear()
            st.rerun()
    html('<p class="g-note" style="direction:rtl;margin-top:12px">القيم لكل 100 جم من USDA FoodData Central عبر سير عمل n8n، '
         'ومضروبة في الكمية اللي اخترتها.</p>')


# ---------- Page: المصادر ----------
def page_sources():
    html('<h1 class="g-page-title" style="direction:rtl">المصادر</h1><p class="g-label" style="direction:rtl;margin-top:4px">'
         'غذائي يجاوب من هذه المصادر الرسمية فقط، ويذكر المصدر في كل إجابة.</p>')
    sources = [s for s in json.loads(WEB_SOURCES.read_text(encoding="utf-8")) if not s.get("skip")]
    publishers = list(dict.fromkeys(s["publisher"] for s in sources))
    cols = st.columns(2, gap="medium")
    for i, publisher in enumerate(publishers):
        links = "".join(f'<div class="g-row"><a href="{s["url"]}" target="_blank">{s["topic"]}</a></div>'
                        for s in sources if s["publisher"] == publisher)
        with cols[i % 2]:
            html(f'<div class="g-card" style="margin-bottom:16px"><div style="display:flex;justify-content:space-between">'
                 f'<p class="g-title">{publisher}</p><span class="g-pill num">{sum(s["publisher"] == publisher for s in sources)}</span></div>{links}</div>')
    with cols[len(publishers) % 2]:
        html('<div class="g-card"><p class="g-title">القيم الغذائية للأطعمة</p><div class="g-row">'
             '<a href="https://fdc.nal.usda.gov/" target="_blank">USDA FoodData Central</a><span class="g-label">عبر n8n</span></div></div>')


{PROFILE_PAGE: page_profile, PAGES[0]: page_plan, PAGES[1]: page_chat, PAGES[2]: page_food, PAGES[3]: page_sources}[page]()
