import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="Mareero System", page_icon="🏢", layout="wide")

# --- 1. REMOVE STREAMLIT WATERMARKS & MENUS ---
st.markdown("""
<style>
    /* 1. Hide the Hamburger Menu (Top Right) */
    #MainMenu {visibility: hidden;}
    
    /* 2. Hide the Top Header Bar */
    header {visibility: hidden;}
    
    /* 3. Hide the "Made with Streamlit" Footer */
    footer {visibility: hidden;}
    
    /* 4. Aggressively hide the deploy button and decorations */
    .stDeployButton {display:none;}
    div[data-testid="stDecoration"] {display:none;}
    
    /* 5. Adjust top padding since header is gone */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SETUP DATABASE ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_URL = st.secrets["gcp_sheet_url"] 
except Exception as e:
    st.error(f"⚠️ Connection Error: {e}")
    st.stop()

# --- 3. REPORT ENGINES ---
def generate_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Warbixin')
    output.seek(0)
    return output

def generate_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Header
    c.setFillColor(colors.HexColor("#8B0000"))
    c.rect(0, height-100, width, 100, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width/2, height-60, "MAREERO OPERATION REPORT")
    
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, height-80, f"Date: {datetime.now().strftime('%d %B %Y')}")

    # Metrics
    total = len(df)
    missing = len(df[df['Category'] == 'Maqan']) if not df.empty and 'Category' in df.columns else 0
    new_req = len(df[df['Category'] == 'Dalab Cusub']) if not df.empty and 'Category' in df.columns else 0

    # Summary
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height-150, "SUMMARY:")
    c.setFont("Helvetica", 12)
    c.drawString(40, height-180, f"Total Jobs: {total}  |  Missing Items: {missing}  |  New Requests: {new_req}")

    # Table
    y = height-230
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "RECENT ITEMS:")
    y -= 20
    c.setFont("Helvetica", 10)
    
    if not df.empty:
        for i, row in df.head(20).iterrows():
            text = f"{row.get('Branch','')} - {row.get('Category','')} - {row.get('Item','')} ({row.get('Note','')})"
            c.drawString(40, y, text[:90]) # Limit text length
            y -= 15
            if y < 50: break

    c.save()
    buffer.seek(0)
    return buffer

# --- 4. APP UI ---
st.title("🏢 Mareero Auto Spare Parts")

tab_staff, tab_manager = st.tabs(["📝 Staff Area", "🔐 Manager Area"])

# --- STAFF TAB ---
with tab_staff:
    st.info("Fadlan halkan ku diiwaangeli warbixintaada maalinlaha ah.")
    with st.form("log_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            branch = st.selectbox("📍 Branch", ["Kaydka M.Hassan", "Branch 1", "Branch 3", "Branch 4", "Branch 5"])
            employee = st.text_input("👤 Magacaaga")
        with c2:
            cat_map = {"Alaab Maqan": "Maqan", "Dalab Sare": "Dalab Sare", "Dalab Cusub": "Dalab Cusub"}
            cat_key = st.selectbox("📂 Nooca", list(cat_map.keys()))
            item = st.text_input("📦 Magaca Alaabta")
        
        note = st.text_input("📝 Note / Qty")
        if st.form_submit_button("🚀 Submit"):
            if employee and item:
                try:
                    data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0) or pd.DataFrame()
                    data = data.dropna(how="all")
                    new_row = pd.DataFrame([{
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Branch": branch, "Employee": employee,
                        "Category": cat_map[cat_key], "Item": item, "Note": note
                    }])
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=pd.concat([data, new_row], ignore_index=True))
                    st.cache_data.clear()
                    st.success("Sent!")
                except Exception as e: st.error(e)
            else: st.error("Fill Name & Item")

# --- MANAGER TAB ---
with tab_manager:
    # 1. LOGIN ROW (Password + Enter Button)
    c_pass, c_btn = st.columns([4, 1])
    with c_pass:
        password = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Enter Password Here...")
    with c_btn:
        st.markdown("""<style>div.stButton > button {width: 100%;}</style>""", unsafe_allow_html=True)
        login_click = st.button("🔓 Enter")

    # 2. MANAGER DASHBOARD
    if password == "mareero2025" or login_click: # Simple check, for real security rely on session state
        if password == "mareero2025":
            st.success("✅ Logged In")
            
            try:
                df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0) or pd.DataFrame()
                df = df.dropna(how="all")
            except: df = pd.DataFrame()

            if not df.empty:
                # Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Total", len(df))
                m2.metric("Missing", len(df[df['Category']=='Maqan']) if 'Category' in df.columns else 0)
                m3.metric("New Req", len(df[df['Category']=='Dalab Cusub']) if 'Category' in df.columns else 0)
                
                # Downloads
                c_pdf, c_xls = st.columns(2)
                with c_pdf:
                    if st.button("📄 PDF Report"):
                        st.download_button("⬇️ Download PDF", generate_pdf(df), "report.pdf", "application/pdf")
                with c_xls:
                    if st.button("📊 Excel Data"):
                        st.download_button("⬇️ Download Excel", generate_excel(df), "data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                st.divider()
                st.write("### 🛠️ Edit / Delete Items")
                
                # Data Editor with Checkbox
                df_edit = df.copy()
                df_edit.insert(0, "Delete", False)
                
                edited = st.data_editor(
                    df_edit,
                    key="editor",
                    num_rows="fixed",
                    hide_index=True,
                    use_container_width=True,
                    column_config={"Delete": st.column_config.CheckboxColumn("❌", width="small")}
                )

                # Action Buttons (Save Left, Delete Right)
                c_save, c_mid, c_del = st.columns([2, 3, 1])
                
                with c_save:
                    if st.button("💾 Save Changes"):
                        try:
                            final = edited.drop(columns=["Delete"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final)
                            st.cache_data.clear()
                            st.success("Saved!")
                            st.rerun()
                        except Exception as e: st.error(e)
                
                with c_del:
                    # Small Professional Delete Button
                    if st.button("🗑️ Delete", type="primary"):
                        try:
                            final = edited[edited["Delete"]==False].drop(columns=["Delete"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final)
                            st.cache_data.clear()
                            st.success("Deleted!")
                            st.rerun()
                        except Exception as e: st.error(e)

            else: st.warning("No Data Found")
        else: st.error("Wrong Password")
