"""Ghithaaey app: Lab 7 + Lab 8 (Streamlit), with memory (Lab 14), tools (Lab 13) and n8n (Lab 15/16).

The user journey:
  1. Fill the profile once (sidebar)        -> no retyping age, height, weight in every chat
  2. "My plan" tab: exact numbers, instantly -> calculated in Python, not guessed by the AI
  3. "Food values" tab: look up a food, pick the portion, add it to today's log -> what is left today
  4. "Ask Ghithaaey" tab: the AI already knows the profile and today's log; answers cite MOH/WHO/SFDA
  5. "Sources" tab: where every answer comes from

Run:  streamlit run app.py
Keys: .streamlit/secrets.toml (see secrets.toml.example)
"""
import json

import pandas as pd
import streamlit as st

from assistant import ask, build_agent, new_thread_id
from settings import CONFIG, WEB_SOURCES, get_secret
from tools import FOOD_LOGS, PROFILES, check_food, compute_plan, parse_food, plan_blocker

st.set_page_config(page_title=CONFIG["assistant_name"], page_icon="🥗", layout="wide")

# Lab 8: our colours. Plus right-to-left text for Arabic.
st.markdown("""
<style>
.stApp { background-color: #0B1930; color: #FFFFFF; }
section[data-testid="stSidebar"] { background-color: #142B49; }
.stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp li, .stApp label,
section[data-testid="stSidebar"] * { color: #FFFFFF; }
.stApp p, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp label,
[data-testid="stChatMessageContent"], [data-testid="stMetric"], [data-testid="stAlert"] {
    direction: rtl; text-align: right;
}
[data-testid="stTabs"] [role="tablist"] { direction: rtl; }
[data-testid="stMetric"] { background-color: #1D3658; border-radius: 12px; padding: 12px; }
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] p { color: #FFFFFF !important; }
[data-testid="stChatMessage"] { background-color: #1D3658; color: #FFFFFF; border-radius: 12px; padding: 14px; }
[data-testid="stChatInput"] { background-color: #1D3658; border: 2px solid #4A90E2; border-radius: 12px; }
[data-testid="stChatInput"] textarea {
    color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF; caret-color: #FFFFFF; direction: rtl;
}
[data-testid="stChatInput"] textarea::placeholder { color: #CAD8EA !important; -webkit-text-fill-color: #CAD8EA; }
.stButton > button, .stFormSubmitButton > button { background-color: #2563EB; color: #FFFFFF; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ---------- Labels: the user sees Arabic, the tools get English values ----------
SEX = {"male": "ذكر", "female": "أنثى"}
ACTIVITY = {
    "sedentary": "قليل الحركة (بدون رياضة)",
    "light": "خفيف (رياضة 1-3 أيام بالأسبوع)",
    "moderate": "متوسط (3-5 أيام بالأسبوع)",
    "active": "عالي (6-7 أيام بالأسبوع)",
    "very_active": "عالي جداً (عمل بدني أو تمرين مرتين يومياً)",
}
GOAL = {"lose": "إنقاص الوزن", "maintain": "المحافظة على الوزن", "gain": "زيادة الوزن"}
CONDITION = {
    "none": "لا يوجد",
    "pregnancy": "حامل أو مرضعة",
    "diabetes": "السكري",
    "hypertension": "ضغط الدم المرتفع",
    "kidney": "أمراض الكلى",
    "other": "حالة صحية أخرى",
}
BMI_AR = {"underweight": "نقص في الوزن", "normal": "وزن طبيعي", "overweight": "زيادة في الوزن", "obese": "سمنة"}
MEALS_AR = {"breakfast": "الفطور", "lunch": "الغداء", "dinner": "العشاء", "snacks": "وجبات خفيفة"}
# Common Saudi foods -> the USDA name our n8n workflow searches for
FOODS = {
    "تمر": "dates medjool",
    "رز أبيض مطبوخ": "rice white cooked",
    "رز بني مطبوخ": "rice brown cooked",
    "صدر دجاج مطبوخ": "chicken breast cooked",
    "لحم غنم مطبوخ": "lamb cooked",
    "سمك سلمون مطبوخ": "salmon cooked",
    "بيض مسلوق": "egg whole hard-boiled",
    "خبز أبيض": "bread white",
    "خبز بر (قمح كامل)": "bread whole-wheat",
    "شوفان": "oats",
    "عدس مطبوخ": "lentils cooked",
    "حمص مطبوخ": "chickpeas cooked",
    "فول مطبوخ": "fava beans cooked",
    "حليب كامل الدسم": "milk whole",
    "لبن زبادي": "yogurt plain whole milk",
    "جبن فيتا": "cheese feta",
    "تفاح": "apples raw",
    "موز": "bananas raw",
    "برتقال": "oranges raw",
    "خيار": "cucumber raw",
    "طماطم": "tomatoes raw",
    "بطاطس مسلوقة": "potatoes boiled",
    "لوز": "almonds",
    "زيت زيتون": "olive oil",
}
TOOL_LABELS = {
    "search_knowledge_base": "📚 قاعدة المعرفة",
    "calculator": "🧮 الآلة الحاسبة",
    "nutrition_plan": "🔥 حاسبة التغذية",
    "save_profile": "💾 حفظ بياناتك",
    "check_food": "🍎 القيم الغذائية (n8n)",
    "tavily_search": "🌐 بحث الويب",
}
REQUIRED = ("age", "sex", "weight_kg", "height_cm", "activity", "goal")


@st.cache_resource
def get_agent():
    return build_agent()


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def lookup_food(name: str) -> dict | None:
    """Same n8n workflow the agent uses; cached so the same food is not asked twice (USDA rate limit)."""
    return parse_food(check_food.invoke({"food": name}))


def pick(options: dict, value):
    keys = list(options)
    return keys.index(value) if value in keys else None


# ---------- Lab 14: one thread_id per chat ----------
if "thread_id" not in st.session_state:
    st.session_state.thread_id = new_thread_id()
    st.session_state.messages = []
thread = st.session_state.thread_id
profile = PROFILES.setdefault(thread, {})
food_log = FOOD_LOGS.setdefault(thread, [])
ready = all(k in profile for k in REQUIRED)

# ---------- Sidebar: the profile, filled once ----------
with st.sidebar:
    st.header("👤 ملفك")
    st.caption("عبّيه مرة وحدة، وغذائي يحسب خطتك ويجاوبك على أساسه بدون ما يسألك من جديد.")
    with st.form("profile"):
        c1, c2 = st.columns(2)
        age = c1.number_input("العمر", 10, 100, profile.get("age"), placeholder="سنة")
        sex = c2.selectbox("الجنس", list(SEX), pick(SEX, profile.get("sex")), format_func=SEX.get,
                           placeholder="اختر")
        height = c1.number_input("الطول (سم)", 120.0, 230.0, profile.get("height_cm"), 1.0, placeholder="سم")
        weight = c2.number_input("الوزن (كجم)", 30.0, 300.0, profile.get("weight_kg"), 0.5, placeholder="كجم")
        activity = st.selectbox("مستوى النشاط", list(ACTIVITY), pick(ACTIVITY, profile.get("activity")),
                                format_func=ACTIVITY.get, placeholder="اختر")
        goal = st.selectbox("هدفك", list(GOAL), pick(GOAL, profile.get("goal")), format_func=GOAL.get,
                            placeholder="اختر")
        target = st.number_input("الوزن المستهدف (اختياري)", 30.0, 300.0, profile.get("target_weight_kg"), 0.5,
                                 placeholder="كجم")
        condition = st.selectbox("هل عندك حالة صحية خاصة؟", list(CONDITION),
                                 pick(CONDITION, profile.get("condition", "none")), format_func=CONDITION.get)
        saved = st.form_submit_button("💾 احفظ واحسب خطتي", width="stretch")
    if saved:
        values = dict(age=age, sex=sex, height_cm=height, weight_kg=weight, activity=activity, goal=goal)
        missing = [k for k, v in values.items() if v is None]
        if missing:
            st.error("كمّل الحقول: العمر، الجنس، الطول، الوزن، النشاط، والهدف.")
        else:
            profile.clear()
            profile.update(values, condition=condition)
            if target and goal != "maintain":
                profile["target_weight_kg"] = target
            st.rerun()

    if st.button("🔄 محادثة جديدة (تمسح بياناتك)", width="stretch"):
        PROFILES.pop(thread, None)  # privacy (Lab 4): nothing is kept after a new chat
        FOOD_LOGS.pop(thread, None)
        st.session_state.thread_id = new_thread_id()
        st.session_state.messages = []
        st.rerun()
    st.caption("🔒 بياناتك تبقى في هذه الجلسة فقط ولا تُحفظ على أي خادم.")
    st.caption(CONFIG["disclaimer"])

# ---------- Header ----------
st.title(CONFIG["assistant_name"])
st.write(CONFIG["welcome"])
if not ready:
    st.info("👈 ابدأ بتعبئة ملفك في القائمة الجانبية (العمر، الطول، الوزن، النشاط، الهدف) "
            "عشان نحسب لك سعراتك وبروتينك ونتابع أكلك اليوم.")

tab_plan, tab_chat, tab_food, tab_sources = st.tabs(["📊 خطتي", "💬 اسأل غذائي", "🍎 قيمة الأكل وسجل اليوم", "📚 المصادر"])

# ---------- Tab 1: the plan, calculated directly (no AI, no waiting) ----------
plan = None
with tab_plan:
    if not ready:
        st.write("خطتك تظهر هنا بعد ما تحفظ ملفك.")
    else:
        blocker = plan_blocker(profile)
        if blocker and blocker.startswith("MEDICAL_CONDITION"):
            st.warning(f"لأن عندك حالة خاصة ({CONDITION[profile['condition']]})، ما نعطيك أرقام سعرات أو "
                       "ماكروز. احتياجك يحدده الطبيب أو أخصائي التغذية. تقدر تسأل غذائي عن معلومات "
                       "التغذية العامة من مصادر وزارة الصحة.")
        elif blocker and blocker.startswith("UNDER_18"):
            st.warning("للأعمار تحت 18 سنة ما نعطي أهداف سعرات. الأفضل تتكلم مع أهلك والطبيب.")
        elif blocker:
            st.error("الطول أو الوزن يبدو غير صحيح، راجع ملفك.")
        else:
            plan = compute_plan(profile)
            st.subheader("احتياجك اليومي")
            c = st.columns(4)
            c[0].metric("السعرات", f"{plan['target']} kcal", f"{plan['target'] - plan['tdee']:+} عن الثبات",
                        delta_color="off")
            c[1].metric("البروتين", f"{plan['protein']} g")
            c[2].metric("الكربوهيدرات", f"{plan['carbs']} g")
            c[3].metric("الدهون", f"{plan['fat']} g")
            if plan["raised_to_minimum"]:
                st.caption("رفعنا السعرات للحد الأدنى الآمن.")

            st.subheader("اليوم")
            eaten = {k: round(sum(item[k] for item in food_log)) for k in ("kcal", "protein", "carbs", "fat")}
            if not food_log:
                st.caption("سجل اليوم فاضي. أضف أكلك من تبويب «قيمة الأكل وسجل اليوم».")
            for key, label, goal_value in (("kcal", "السعرات", plan["target"]), ("protein", "البروتين", plan["protein"]),
                                           ("carbs", "الكربوهيدرات", plan["carbs"]), ("fat", "الدهون", plan["fat"])):
                left = goal_value - eaten[key]
                st.progress(min(eaten[key] / goal_value, 1.0),
                            text=f"{label}: {eaten[key]} من {goal_value} — "
                                 + (f"باقي {left}" if left >= 0 else f"زيادة {-left}"))

            st.subheader("جسمك")
            c = st.columns(4)
            c[0].metric("مؤشر كتلة الجسم", plan["bmi"], BMI_AR.get(plan["bmi_category"], plan["bmi_category"]),
                        delta_color="off")
            c[1].metric("الوزن الصحي لطولك", f"{plan['healthy_min']}–{plan['healthy_max']} كجم")
            c[2].metric("الحرق وقت الراحة", f"{plan['bmr']} kcal")
            c[3].metric("سعرات الثبات", f"{plan['tdee']} kcal")
            if plan["weeks"]:
                st.success(f"🎯 توصل لـ {plan['target_weight']} كجم في حوالي {plan['weeks']} أسبوع "
                           f"(بمعدل آمن ~{plan['per_week']} كجم بالأسبوع).")
                if plan["target_too_low"]:
                    st.warning(f"وزنك المستهدف أقل من الوزن الصحي لطولك ({plan['healthy_min']} كجم). "
                               "ننصحك بهدف أعلى.")

            left_col, right_col = st.columns(2)
            with left_col:
                st.subheader("توزيع الوجبات")
                st.table(pd.DataFrame(
                    {"الوجبة": [MEALS_AR.get(m.split(" /")[0], m) for m in plan["meals"]],
                     "السعرات": list(plan["meals"].values())}).set_index("الوجبة"))
            with right_col:
                st.subheader("يومياً")
                st.write(f"💧 الماء: {plan['water']} لتر على الأقل (أكثر مع الرياضة والحر)")
                st.write(f"🌾 الألياف: حوالي {plan['fiber']} جم")
                st.write(f"🍬 السكر المضاف: أقل من {plan['sugar_max']} جم (والأفضل أقل من {plan['sugar_ideal']} جم)")
                st.write(f"🧈 الدهون المشبعة: أقل من {plan['sat_fat_max']} جم")
                st.write("🧂 الملح: أقل من 5 جم (ملعقة صغيرة)")
            st.caption("الأرقام: معادلة Mifflin-St Jeor وإرشادات وزارة الصحة ومنظمة الصحة العالمية. "
                       "تقديرات عامة للبالغين الأصحاء وليست استشارة طبية.")

# ---------- Tab 2: the AI, already knowing the profile and today's log ----------
with tab_chat:
    if ready:
        st.caption("✅ غذائي يعرف ملفك وأكلك اليوم، اسأله مباشرة.")
    examples = (["وش أفطر عشان أوصل لبروتيني؟", "كم باقي لي سعرات اليوم؟", "اشرح لي خطتي ببساطة"] if ready else []) \
        + CONFIG["examples"]
    cols = st.columns(3)
    for i, example in enumerate(examples[:6]):
        if cols[i % 3].button(example, key=f"ex{i}", width="stretch"):
            st.session_state.pending = example

    box = st.container(height=480)
    with box:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if message.get("tools"):
                    with st.expander("الأدوات المستخدمة"):
                        for step in message["tools"]:
                            st.caption(f"{TOOL_LABELS.get(step['tool'], step['tool'])}: {step['args']}")

    question = st.chat_input("اسألني أي شي عن التغذية") or st.session_state.pop("pending", None)
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        try:
            with st.spinner("لحظة..."):
                answer, tool_log = ask(get_agent(), question, thread)
        except Exception:
            answer, tool_log = CONFIG["friendly_error"], []
        st.session_state.messages.append({"role": "assistant", "content": answer, "tools": tool_log})
        st.rerun()

# ---------- Tab 3: food values (n8n + USDA) and today's log ----------
with tab_food:
    if not get_secret("N8N_URL"):
        st.info("أداة القيم الغذائية تحتاج رابط n8n (N8N_URL) في ملف الأسرار.")
    else:
        c1, c2 = st.columns([2, 1])
        choice = c1.selectbox("اختر الأكل", list(FOODS) + ["أكل آخر (اكتبه بالإنجليزي)"])
        custom = c1.text_input("اسم الأكل بالإنجليزي", placeholder="e.g. kabsa, hummus, dates") \
            if choice not in FOODS else ""
        grams = c2.number_input("الكمية (جرام)", 1, 2000, 100, 10)
        if st.button("🔍 احسب القيم", width="stretch"):
            name = FOODS.get(choice) or custom.strip()
            if not name:
                st.error("اكتب اسم الأكل.")
            else:
                with st.spinner("نجيب القيم من USDA..."):
                    result = lookup_food(name)
                if result:
                    st.session_state.food_result = {"label": choice if choice in FOODS else name, **result}
                else:
                    st.session_state.food_result = None
                    st.error("ما لقينا هذا الأكل. جرّب اسم أبسط بالإنجليزي، مثل: rice white cooked.")

        r = st.session_state.get("food_result")
        if r:
            f = grams / 100
            st.subheader(f"{r['label']} — {grams} جم")
            st.caption(f"USDA: {r['name']}")
            c = st.columns(4)
            c[0].metric("السعرات", f"{round(r['kcal'] * f)} kcal")
            c[1].metric("البروتين", f"{round(r['protein'] * f, 1)} g")
            c[2].metric("الكربوهيدرات", f"{round(r['carbs'] * f, 1)} g")
            c[3].metric("الدهون", f"{round(r['fat'] * f, 1)} g")
            st.caption(f"السكريات {round(r['sugars'] * f, 1)} جم · الألياف {round(r['fiber'] * f, 1)} جم · "
                       f"الصوديوم {round(r['sodium_mg'] * f)} ملجم")
            if st.button("➕ أضف لسجل اليوم", width="stretch"):
                food_log.append({"name": r["label"], "grams": grams, "kcal": r["kcal"] * f,
                                 "protein": r["protein"] * f, "carbs": r["carbs"] * f, "fat": r["fat"] * f})
                st.toast(f"أضفنا {r['label']} لسجل اليوم")
                st.rerun()

    st.subheader("سجل اليوم")
    if food_log:
        table = pd.DataFrame(food_log).rename(columns={"name": "الأكل", "grams": "جرام", "kcal": "سعرات",
                                                       "protein": "بروتين", "carbs": "كربوهيدرات", "fat": "دهون"})
        st.dataframe(table.round(1), hide_index=True, width="stretch")
        total = round(sum(item["kcal"] for item in food_log))
        if plan:
            st.write(f"المجموع: {total} من {plan['target']} سعرة — باقي {plan['target'] - total}")
        else:
            st.write(f"المجموع: {total} سعرة")
        if st.button("🗑️ امسح السجل"):
            food_log.clear()
            st.rerun()
    else:
        st.caption("ما سجلت شي اليوم.")

# ---------- Tab 4: where the answers come from ----------
with tab_sources:
    st.write("غذائي يجاوب من هذه المصادر الرسمية فقط، ويذكر المصدر في كل إجابة.")
    sources = [s for s in json.loads(WEB_SOURCES.read_text(encoding="utf-8")) if not s.get("skip")]
    for publisher in dict.fromkeys(s["publisher"] for s in sources):
        with st.expander(f"{publisher} ({sum(s['publisher'] == publisher for s in sources)})"):
            for s in sources:
                if s["publisher"] == publisher:
                    st.markdown(f"- [{s['topic']}]({s['url']})")
    st.markdown("- القيم الغذائية للأطعمة: [USDA FoodData Central](https://fdc.nal.usda.gov/) عبر n8n")
