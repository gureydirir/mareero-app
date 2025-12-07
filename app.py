import streamlit as st

# ---------------------------------------------------------
# PAGE CONFIGURATION (MUST BE FIRST)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Mareero System",
    page_icon="🏢",
    layout="wide"
)

# --- IMPORTS ---
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz 
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import io
import random

# --- SET TIMEZONE ---
def get_local_time():
    tz = pytz.timezone('Africa/Mogadishu') 
    return datetime.now(tz)

# --- CSS: PROFESSIONAL THEME (FORCED DARK MODE COMPATIBILITY) ---
# This CSS forces dark backgrounds on containers so white text is always visible
st.markdown("""
<style>
    /* FORCE MAIN BACKGROUND */
    .stApp {
        background-color: #0f172a; /* Dark Navy */
    }
    
    /* HIDE DEFAULT MENUS */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* INPUT FIELDS - MAKE THEM VISIBLE */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
        background-color: #1e293b !important; /* Slate 800 */
        color: white !important;
        border: 1px solid #475569 !important;
    }
    
    /* TEXT LABEL COLORS */
    .stMarkdown p, label {
        color: #e2e8f0 !important; /* Light Grey Text */
    }

    /* METRIC CARDS */
    div[data-testid="stMetric"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 15px;
        border-radius: 8px;
    }
    div[data-testid="stMetricLabel"] { color: #94a3b8 !important; }
    div[data-testid="stMetricValue"] { color: #f8fafc !important; }

    /* TABS */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        color: #cbd5e1;
        border-radius: 4px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important; /* Professional Blue */
        color: white !important;
    }
    
    /* BUTTONS */
    div[data-testid="stButton"] button {
        border-radius: 6px;
        font-weight: 600;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. SETUP DATABASE ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_URL = st.secrets["gcp_sheet_url"] 
except Exception as e:
    st.error(f"⚠️ Connection Error: {e}")
    st.stop()

# --- 2. EXCEL GENERATION (RESTORED) ---
def clean_text(text):
    if pd.isna(text) or str(text).lower() == 'nan':
        return "-"
    return str(text)

def generate_excel(df):
    output = io.BytesIO()
    df_export = df.fillna("-")
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Warbixin')
            # Auto-adjust column width
            worksheet = writer.sheets['Warbixin']
            for i, col in enumerate(df_export.columns):
                max_len = max(df_export[col].astype(str).map(len).max(), len(str(col))) + 2
                col_letter = chr(65 + i)
                worksheet.column_dimensions[col_letter].width = max_len
    except:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False)
    output.seek(0)
    return output

# --- 3. PDF GENERATION (FIXED CHARTS) ---
def generate_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # PDF Colors (Professional Blue/Slate)
    header_bg = colors.HexColor("#0f172a") # Dark Navy
    text_color = colors.HexColor("#334155")
    
    # --- HEADER ---
    c.setFillColor(header_bg)
    c.rect(0, height-100, width, 100, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(40, height-50, "MAREERO SYSTEM")
    c.setFont("Helvetica", 12)
    c.drawString(40, height-70, "Mareero General Trading LLC")
    
    # Date/Time
    current_time = get_local_time()
    c.drawRightString(width-40, height-50, "OPERATIONAL REPORT")
    c.setFont("Helvetica", 10)
    c.drawRightString(width-40, height-65, f"Date: {current_time.strftime('%d %B %Y')}")
    c.drawRightString(width-40, height-80, f"Time: {current_time.strftime('%I:%M %p')}")

    # --- SUMMARY ---
    y_pos = height - 140
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y_pos, "1. KOOBITAAN (SUMMARY)")
    
    total = len(df)
    missing = len(df[df['Category'] == 'alabaha Maqan']) if not df.empty else 0
    requests = len(df[df['Category'] == 'bahiyaha Dadweynaha']) if not df.empty else 0
    
    # Summary Boxes
    box_w, box_h, gap = 160, 50, 15
    start_x = 40
    metrics = [("Total Reports", str(total)), ("Alaabta Maqan", str(missing)), ("Requests (Dalab)", str(requests))]
    
    for i, (label, value) in enumerate(metrics):
        x = start_x + (i * (box_w + gap))
        c.setStrokeColor(colors.lightgrey)
        c.roundRect(x, y_pos-60, box_w, box_h, 6, fill=0, stroke=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(x + box_w/2, y_pos-35, value)
        c.setFillColor(colors.grey)
        c.setFont("Helvetica", 10)
        c.drawCentredString(x + box_w/2, y_pos-50, label)

    # --- CHARTS (FIXED FOR PRINTING) ---
    y_pos -= 80
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y_pos, "2. SHAXDA XOGTA (CHARTS)")
    
    if not df.empty:
        try:
            # RESET MATPLOTLIB STYLE FOR PDF (White Background, Black Text)
            plt.rcdefaults() 
            
            # Pie Chart
            fig1, ax1 = plt.subplots(figsize=(4, 3))
            cat_counts = df['Category'].value_counts()
            ax1.pie(cat_counts, labels=cat_counts.index, autopct='%1.0f%%', colors=['#3b82f6', '#94a3b8', '#cbd5e1'])
            
            img1 = io.BytesIO()
            plt.savefig(img1, format='png', bbox_inches='tight')
            img1.seek(0)
            c.drawImage(ImageReader(img1), 40, y_pos-220, width=220, height=165)
            plt.close(fig1)

            # Bar Chart
            fig2, ax2 = plt.subplots(figsize=(4, 3))
            branch_counts = df['Branch'].value_counts()
            branch_counts.plot(kind='bar', color='#0f172a', ax=ax2)
            ax2.set_xlabel("Laamaha (Branches)")
            plt.xticks(rotation=45, ha='right', fontsize=8)
            
            img2 = io.BytesIO()
            plt.savefig(img2, format='png', bbox_inches='tight')
            img2.seek(0)
            c.drawImage(ImageReader(img2), 300, y_pos-220, width=240, height=180)
            plt.close(fig2)
        except:
            pass

    # --- TABLE ---
    y_pos -= 240
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y_pos, "3. LIISKA FAAHFAAHSAN (DETAILS)")
    
    # Table Header
    y_curr = y_pos - 30
    col_widths = [70, 140, 100, 90, 115] 
    headers = ["TYPE", "ITEM NAME", "BRANCH", "STAFF", "NOTES"]
    
    c.setFillColor(header_bg)
    c.rect(40, y_curr-6, sum(col_widths), 22, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    
    x_pos = 45
    for i, h in enumerate(headers):
        c.drawString(x_pos, y_curr+2, h)
        x_pos += col_widths[i]
        
    y_curr -= 22
    c.setFont("Helvetica", 9)
    row_count = 0
    
    if not df.empty:
        # Sort by Item Name
        if 'Item' in df.columns:
            df = df.sort_values(by=['Item'])
            
        for _, row in df.iterrows():
            if row_count % 2 == 0:
                c.setFillColor(colors.HexColor("#f1f5f9"))
                c.rect(40, y_curr-6, sum(col_widths), 18, fill=1, stroke=0)
            
            # Highlight Missing Items in Red Text
            cat = clean_text(row.get('Category', ''))
            is_missing = cat == 'Maqan'
            c.setFillColor(colors.red if is_missing else colors.black)
            
            vals = [
                cat[:12],
                clean_text(row.get('Item', ''))[:24],
                clean_text(row.get('Branch', '')).replace("Branch", "Br."),
                clean_text(row.get('Employee', ''))[:14],
                clean_text(row.get('Note', ''))[:20]
            ]
            
            x_pos = 45
            for i, val in enumerate(vals):
                c.drawString(x_pos, y_curr, val)
                x_pos += col_widths[i]
            
            y_curr -= 18
            row_count += 1
            
            if y_curr < 60:
                c.showPage()
                y_curr = height - 50

    c.save()
    buffer.seek(0)
    return buffer

# --- 3. APP UI ---

st.markdown("""
<div style="text-align: center; margin-bottom: 20px;">
    <h1 style='color: #3b82f6; margin:0;'>MAREERO SYSTEM</h1>
    <p style='color: #94a3b8;'>General Trading & Spare Parts LLC</p>
</div>
""", unsafe_allow_html=True)

# Tabs
tab_staff, tab_manager = st.tabs(["📝 SHAQAALAHA (Staff)", "🔐 MAAMULKA (Manager)"])

# --- STAFF TAB ---
with tab_staff:
    st.info("👋 Fadlan halkan ku diiwaangeli warbixintaada maalinlaha ah.")
    
    with st.form("log_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            branch_options = ["Head Quater", "Branch 1", "Branch 3", "Branch 4", "Branch 5" , "Kaydka M.hassan"]
            branch = st.selectbox("📍 Xulo Laanta (Select Branch)", branch_options)
            employee = st.text_input("👤 Magacaaga (Your Name)")
        with col2:
            cat_map = {
                "alaabta Maqan (Missing)": "Maqan",
                "alaabta Suqqa leh (High Demand)": "Suuq leh",
                "bahiyaha Dadweynaha (New Request)": "Dadweynaha"
            }
            category_selection = st.selectbox("📂 Nooca Warbixinta (Type)", list(cat_map.keys()))
            item = st.text_input("📦 Magaca Alaabta (Item Name)")
        
        note = st.text_input("📝 Notes / Faahfaahin (Optional)")
        
        st.write("")
        submit_btn = st.form_submit_button("🚀 GUDBI (Submit Report)", use_container_width=True)
        
        if submit_btn:
            if employee and item:
                try:
                    data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
                    if data is None: data = pd.DataFrame()
                    data = data.dropna(how="all")
                    
                    real_category = cat_map[category_selection]
                    current_local_time = get_local_time().strftime("%Y-%m-%d %H:%M")
                    
                    new_row = pd.DataFrame([{
                        "Date": current_local_time,
                        "Branch": branch,
                        "Employee": employee,
                        "Category": real_category,
                        "Item": item,
                        "Note": note if note else "-"
                    }])
                    
                    updated = pd.concat([data, new_row], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated)
                    st.cache_data.clear()
                    st.success(f"✅ Success! Entry logged at {current_local_time}")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("⚠️ Fadlan buuxi Magacaaga iyo Alaabta.")

# --- MANAGER TAB ---
with tab_manager:
    # LOGIN
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        c_pass, c_btn = st.columns([4, 1], vertical_alignment="bottom")
        with c_pass:
            password = st.text_input("🔑 Geli Furaha (Password)", type="password", placeholder="******")
        with c_btn:
            if st.button("Login", type="primary"):
                if password == "mareero2025":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Furaha waa khalad (Wrong Password)")
    
    # DASHBOARD
    if st.session_state.logged_in:
        c_head, c_logout = st.columns([4,1])
        with c_head:
            st.subheader("📊 Welcome Maamule")
        with c_logout:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.rerun()
            
        try:
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
            if df is None: df = pd.DataFrame()
            df = df.dropna(how="all")
        except:
            df = pd.DataFrame()

        if not df.empty:
            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            
            count_total = len(df)
            count_missing = len(df[df['Category'] == 'Maqan']) if 'Category' in df.columns else 0
            count_new = len(df[df['Category'] == 'Dadweynaha']) if 'Category' in df.columns else 0
            
            m1.metric("Total", count_total)
            m2.metric("Missing (Maqan)", count_missing, delta_color="inverse")
            m3.metric("New Requests", count_new)
            m4.metric("Branches", df['Branch'].nunique() if 'Branch' in df.columns else 0)
            
            st.markdown("---")
            
            # REPORTS
            st.subheader("📄 Warbixinada (Reports)")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    label="📥 Download PDF Report",
                    data=generate_pdf(df),
                    file_name=f"Mareero_Report_{get_local_time().strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            with c2:
                # EXCEL RESTORED HERE
                st.download_button(
                    label="📥 Download Excel File",
                    data=generate_excel(df),
                    file_name=f"Mareero_Data_{get_local_time().strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            st.markdown("---")

            # EDIT TABLE
            with st.expander("🛠️ Wax ka bedel / Tirtir (Edit/Delete)", expanded=False):
                df_with_delete = df.copy()
                df_with_delete.insert(0, "Select", False)

                edited_df = st.data_editor(
                    df_with_delete,
                    num_rows="fixed",
                    hide_index=True,
                    use_container_width=True,
                    key="data_editor",
                    column_config={"Select": st.column_config.CheckboxColumn("❌", width="small")}
                )
                
                col_save, col_del = st.columns([1,1])
                with col_save:
                    if st.button("💾 Kaydi (Save)", use_container_width=True):
                        try:
                            final_df = edited_df.drop(columns=["Select"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                            st.cache_data.clear()
                            st.success("✅ Waa la keydiyay!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                with col_del:
                    if st.button("🗑️ Tirtir (Delete)", type="primary", use_container_width=True):
                        try:
                            rows_to_keep = edited_df[edited_df["Select"] == False]
                            final_df = rows_to_keep.drop(columns=["Select"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                            st.cache_data.clear()
                            st.success("✅ Waa la tirtiray!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
        else:
            st.info("No data found.")
