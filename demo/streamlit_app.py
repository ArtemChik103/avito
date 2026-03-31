import streamlit as st
import httpx
import json
import os

# --- Visual Theme and CSS ---
# Deep dark background, semi-transparent frosted glass containers, clear typography
st.set_page_config(page_title="Avito Services Splitter Demo", layout="centered", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    [data-testid="stAppViewContainer"] {
        background-color: #0b0f19;
        background-image: radial-gradient(circle at 15% 50%, rgba(30, 60, 114, 0.15) 0%, transparent 50%),
                          radial-gradient(circle at 85% 30%, rgba(42, 82, 152, 0.15) 0%, transparent 50%);
        color: #e2e8f0;
    }

    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.6) !important;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }

    .glass-panel {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }

    .success-panel {
        background: rgba(16, 185, 129, 0.1) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-left: 4px solid #10b981 !important;
    }

    .neutral-panel {
        background: rgba(100, 116, 139, 0.1) !important;
        border: 1px solid rgba(100, 116, 139, 0.3) !important;
        border-left: 4px solid #64748b !important;
    }

    .error-text {
        color: #ef4444 !important;
        font-weight: 600;
    }

    h1, h2, h3, h4 {
        color: #f8fafc !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
    }

    .draft-card {
        background: rgba(15, 23, 42, 0.8);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .draft-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        border-color: rgba(255, 255, 255, 0.1);
    }

    .draft-title {
        color: #38bdf8;
        font-size: 1.1em;
        font-weight: 600;
        margin-bottom: 4px;
    }

    .draft-meta {
        color: #94a3b8;
        font-size: 0.85em;
        margin-bottom: 12px;
    }

    .block-title {
        color: #60a5fa;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-size: 0.75rem;
        font-weight: 800;
        margin-bottom: 12px;
    }

    /* Additional Streamlit overrides */
    section[data-testid="stSidebar"] div.stButton > button {
        background-color: #3b82f6 !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Logic setup ---
DEMO_CASES_PATH = os.path.join(os.path.dirname(__file__), "demo_cases.json")
ITEM_ID_KEY = "input_item_id"
MC_ID_KEY = "input_mc_id"
MC_TITLE_KEY = "input_mc_title"
DESCRIPTION_KEY = "input_description"

@st.cache_data
def load_demo_cases():
    try:
        with open(DEMO_CASES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load demo cases: {e}")
        return []

cases = load_demo_cases()
case_options = {c["label"]: c for c in cases}

def check_backend(url):
    try:
        r = httpx.get(f"{url}/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def apply_form_data(item):
    st.session_state.form_data = item
    st.session_state[ITEM_ID_KEY] = item["itemId"]
    st.session_state[MC_ID_KEY] = item["mcId"]
    st.session_state[MC_TITLE_KEY] = item["mcTitle"]
    st.session_state[DESCRIPTION_KEY] = item["description"]

# --- App State ---
if 'form_data' not in st.session_state:
    apply_form_data({
        "itemId": 1000,
        "mcId": 201,
        "mcTitle": "Ремонт квартир и домов под ключ",
        "description": ""
    })
if 'selected_expected' not in st.session_state:
    st.session_state.selected_expected = None

# Sidebar
with st.sidebar:
    st.title("⚙️ Settings & Status")
    
    default_backend_url = os.getenv("AVITO_BACKEND_URL", "http://127.0.0.1:8000")
    backend_url = st.text_input("Backend URL", value=default_backend_url)
    
    is_online = check_backend(backend_url)
    if is_online:
        st.markdown("🟢 **Backend Status**: Online")
    else:
        st.markdown("🔴 **Backend Status**: Offline")
        st.caption("Run: `uvicorn src.avito_splitter.api:app --reload`")
    
    st.markdown("---")
    st.subheader("📋 Load Demo Case")
    
    selected_label = st.selectbox("Select a scenario:", options=list(case_options.keys()))
    
    if st.button("Подставить кейс", use_container_width=True, type="primary"):
        c = case_options[selected_label]
        apply_form_data(c["item"])
        st.session_state.selected_expected = {
            "shouldSplit": c["expectedShouldSplit"],
            "draftMcIds": c["expectedDraftMcIds"]
        }
        st.rerun()

# Main UI
st.title("Avito Services Splitter")
st.markdown("""
Система анализирует объявление об услугах и определяет, содержит ли оно **несколько самостоятельных услуг**, из которых можно выделить отдельные черновики (drafts). 
Проект работает поверх уже существующего Backend API по HTTP.
""")

st.markdown('<div class="block-title">ADVERTISEMENT FORM</div>', unsafe_allow_html=True)
st.caption("Ниже поля исходного объявления: itemId, mcId, mcTitle и description.")
with st.container():
    c1, c2 = st.columns(2)
    item_id = c1.number_input("Item ID", value=st.session_state.form_data["itemId"], step=1, format="%d", key=ITEM_ID_KEY)
    mc_id = c2.number_input("Microcategory ID", value=st.session_state.form_data["mcId"], step=1, format="%d", key=MC_ID_KEY)
    
    mc_title = st.text_input("Microcategory Title", value=st.session_state.form_data["mcTitle"], key=MC_TITLE_KEY)
    description = st.text_area("Description", value=st.session_state.form_data["description"], height=150, key=DESCRIPTION_KEY)
    
    process_btn = st.button("Обработать объявление", type="primary", use_container_width=True)

if process_btn:
    if not description.strip():
        st.error("Ошибка: Описание (description) не может быть пустым.")
    elif not is_online:
        st.error(f"Ошибка связи: Backend недоступен по адресу {backend_url}. Пожалуйста, запустите API: \n`uvicorn src.avito_splitter.api:app --reload`")
    else:
        payload = {
            "itemId": item_id,
            "mcId": mc_id,
            "mcTitle": mc_title,
            "description": description
        }
        
        with st.spinner("Analyzing advertisement..."):
            try:
                response = httpx.post(f"{backend_url}/split", json=payload, timeout=10.0)
                if response.status_code == 200:
                    try:
                        result = response.json()
                        should_split = result.get("shouldSplit", False)
                        drafts = result.get("drafts", [])
                        
                        st.markdown('<div class="block-title">BACKEND DECISION</div>', unsafe_allow_html=True)
                        
                        panel_class = "success-panel" if should_split else "neutral-panel"
                        verdict_text = "ДА (Обнаружено несколько услуг)" if should_split else "НЕТ (Самодостаточная услуга или нет маркеров)"
                        
                        st.markdown(f'''
                        <div class="glass-panel {panel_class}">
                            <h2 style="margin-top: 0; margin-bottom: 8px;">shouldSplit = {str(should_split).lower()}</h2>
                            <p style="margin: 0; opacity: 0.9;">Verdict: {verdict_text}</p>
                        </div>
                        ''', unsafe_allow_html=True)
                        
                        exp = st.session_state.selected_expected
                        if exp and description == st.session_state.form_data.get("description"):
                            exp_should, exp_drafts = exp["shouldSplit"], exp["draftMcIds"]
                            actual_drafts = [d["mcId"] for d in drafts]
                            
                            has_mismatch = (bool(exp_should) != bool(should_split)) or (set(exp_drafts) != set(actual_drafts))
                            if has_mismatch:
                                st.warning(f"⚠️ **Mismatch with Demo Expectations!**\n\n"
                                           f"Expected shouldSplit: {exp_should}, Actual: {should_split}\n\n"
                                           f"Expected drafts: {exp_drafts}, Actual: {actual_drafts}")
                            else:
                                st.success("✅ Сверен с эталоном (demo case): 100% совпадение")

                        if should_split and drafts:
                            st.markdown('<div class="block-title">GENERATED DRAFTS</div>', unsafe_allow_html=True)
                            st.markdown(f'<p style="color: #94a3b8; font-size: 0.9em; margin-bottom: 16px;">Количество черновиков: {len(drafts)}</p>', unsafe_allow_html=True)
                            
                            for i, d in enumerate(drafts):
                                st.markdown(f'''
                                <div class="draft-card">
                                    <div class="draft-title">{d.get("mcTitle", "Unknown")}</div>
                                    <div class="draft-meta">Microcategory ID: {d.get("mcId", "N/A")}</div>
                                    <div style="color: #e2e8f0; font-size: 0.95em; line-height: 1.5; white-space: pre-wrap;">{d.get("text", "")}</div>
                                </div>
                                ''', unsafe_allow_html=True)
                        elif not should_split and drafts:
                            st.warning("Внимание: shouldSplit=false, но backend вернул список drafts.")
                            
                        with st.expander("Показать Raw JSON Ответ"):
                            st.json(result)

                    except json.JSONDecodeError:
                        st.error("Ошибка ответа: Backend вернул невалидный JSON.")
                else:
                    st.error(f"Ошибка backend (HTTP {response.status_code}):\n\n{response.text}")
            except httpx.ReadTimeout:
                st.error("Ошибка связи: Backend request timeout.")
            except httpx.RequestError as e:
                st.error(f"Ошибка связи: Не удалось подключиться к backend ({e}).")
