import streamlit as st
# 1. Force Matplotlib to run in "headless" mode (Prevents white screen hang)
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="Mareero System", page_icon="🏢", layout="wide")

# --- CSS: HIDE WATERMARKS & STYLE BUTTONS ---
st.markdown("""
<style>
    /* Hide Streamlit Logos & Menus */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    
    /* Adjust top padding for mobile */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
    
    /* Make the Delete Icon Button Red and Round-ish */
    div[data-testid="stButton"] button {
        border-radius: 5px;
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

# --- 2. PROFESSIONAL REPORT ENGINES ---

def generate_excel(df):
    output = io.BytesIO()
    # Use OpenPyXL engine to allow formatting
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Warbixin')
            
            # Auto-Adjust Column Widths
            worksheet = writer.sheets['Warbixin']
            for i, col in enumerate(df.columns):
                max_len = max(
                    df[col].astype(str).map(len).max(),
                    len(str(col))
                ) + 2
                col_letter = chr(65 + i)
                worksheet.column_dimensions[col_letter].width = max_len
    except Exception as e:
        # Fallback if openpyxl fails
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
            
    output.seek(0)
    return output

def generate_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # --- COLORS & STYLES ---
    primary_color = colors.HexColor("#8B0000") # Dark Red
    text_color = colors.HexColor("#2C3E50")    # Dark Blue/Grey
    
    # --- HEADER ---
    c.setFillColor(primary_color)
    c.rect(0, height-100, width, 100, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width/2, height-60, "MAREERO OPERATION REPORT")
    
    c.setFont("Helvetica", 12)
    date_str = datetime.now().strftime('%d %B %Y')
    c.drawCentredString(width/2, height-80, f"Taariikhda: {date_str}")

    # --- SECTION 1: SUMMARY ---
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height-140, "1. KOOBITAAN (SUMMARY):")
    
    # SOMALI DESCRIPTION
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.darkgrey)
    c.drawString(40, height-160, "Halkan waxaa ku qoran warbixinta guud ee maanta, oo ay ku jiraan tirada shaqooyinka,")
    c.drawString(40, height-175, "alaabta maqan, iyo dalabyada cusub ee la diiwaangeliyay.")
    
    # Calc Metrics
    total = len(df)
    missing = len(df[df['Category'] == 'Maqan']) if not df.empty and 'Category' in df.columns else 0
    new_req = len(df[df['Category'] == 'Dalab Cusub']) if not df.empty and 'Category' in df.columns else 0
    
    # Draw Summary Box
    c.setStrokeColor(colors.lightgrey)
    c.rect(40, height-250, 515, 60, fill=0)
    
    c.setFillColor(text_color)
    c.setFont("Helvetica", 12)
    c.drawString(60, height-210, f"Wadarta (Total): {total}")
    c.drawString(240, height-210, f"Maqan (Missing): {missing}")
    c.drawString(420, height-210, f"Dalab (Requests): {new_req}")

    # --- SECTION 2: CHARTS ---
    y_chart = height-300
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_chart, "2. SHAXDA XOGTA (CHARTS):")
    
    # SOMALI DESCRIPTION
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.darkgrey)
    c.drawString(40, y_chart-20, "Shaxdan hoose waxay kala dhigdhigeysaa xogta iyadoo loo eegayo Qeybaha (Categories)")
    c.drawString(40, y_chart-35, "iyo Laamaha (Branches) si loo fahmo halka shaqadu u badan tahay.")
    
    if not df.empty and 'Category' in df.columns and 'Branch' in df.columns:
        try:
            # Chart 1: Pie
            fig1, ax1 = plt.subplots(figsize=(4, 3))
            category_counts = df['Category'].value_counts()
            if not category_counts.empty:
                ax1.pie(category_counts, labels=category_counts.index, autopct='%1.0f%%', colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
                ax1.set_title("Qeybaha", fontsize=10)
                
                img1 = io.BytesIO()
                plt.savefig(img1, format='png', bbox_inches='tight')
                plt.close(fig1)
                img1.seek(0)
                c.drawImage(ImageReader(img1), 40, y_chart-260, width=240, height=180)
            
            # Chart 2: Bar
            fig2, ax2 = plt.subplots(figsize=(4, 3))
            branch_counts = df['Branch'].value_counts()
            if not branch_counts.empty:
                branch_counts.plot(kind='bar', color='#8B0000', ax=ax2)
                ax2.set_title("Laamaha", fontsize=10)
                plt.xticks(rotation=45, ha='right')
                
                img2 = io.BytesIO()
                plt.savefig(img2, format='png', bbox_inches='tight')
                plt.close(fig2)
                img2.seek(0)
                c.drawImage(ImageReader(img2), 300, y_chart-260, width=240, height=180)
        except Exception:
            c.drawString(40, y_chart-60, "Error generating charts.")
    else:
        c.drawString(40, y_chart-60, "Xog kuma filna shaxda.")

    # --- SECTION 3: CRITICAL LIST ---
    y_list = y_chart - 290
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_list, "3. ALAABTA MUHIIMKA AH (CRITICAL ITEMS):")

    # SOMALI DESCRIPTION
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.darkgrey)
    c.drawString(40, y_list-20, "Liiskan wuxuu muujinayaa alaabta 'Maqan' ama 'Dalabka Sare' ah ee u baahan fiiro gaar ah.")
    
    # Table Header
    c.setFillColor(colors.lightgrey)
    c.rect(40, y_list-50, 515, 20, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_list-45, "CATEGORY")
    c.drawString(150, y_list-45, "ITEM NAME")
    c.drawString(300, y_list-45, "BRANCH")
    c.drawString(420, y_list-45, "NOTE")
    
    y_row = y_list - 70
    c.setFont("Helvetica", 10)
    
    if not df.empty and 'Category' in df.columns:
        # Filter for Maqan or Dalab Sare
        critical_df = df[df['Category'].isin(['Maqan', 'Dalab Sare'])].head(15)
        for _, row in critical_df.iterrows():
            c.drawString(50, y_row, str(row.get('Category', '')))
            c.drawString(150, y_row, str(row.get('Item', ''))[:25]) # Cut text if too long
            c.drawString(300, y_row, str(row.get('Branch', '')))
            c.drawString(420, y_row, str(row.get('Note', ''))[:20])
            c.line(40, y_row-5, 555, y_row-5) # Underline
            y_row -= 20
            
            if y_row < 50: # New page check
                c.showPage()
                y_row = height - 50

    c.save()
    buffer.seek(0)
    return buffer

# --- 3. THE APP UI ---
st.title("🏢 Mareero System")

# TABS (RESTORED BILINGUAL NAMES)
tab_staff, tab_manager = st.tabs(["📝 Qeybta Shaqaalaha (Staff)", "🔐 Maamulka (Manager)"])

# --- STAFF TAB ---
with tab_staff:
    st.info("Fadlan halkan ku diiwaangeli warbixintaada maalinlaha ah.")
    
    with st.form("log_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            branch_options = ["Kaydka M.Hassan", "Branch 1", "Branch 3", "Branch 4", "Branch 5"]
            branch = st.selectbox("📍 Branch", branch_options)
            employee = st.text_input("👤 Magacaaga (Your Name)")
        with c2:
            cat_map = {
                "Alaab Maqan (Missing)": "Maqan",
                "Dalab Sare (High Demand)": "Dalab Sare",
                "Dalab Cusub (New Request)": "Dalab Cusub"
            }
            category_selection = st.selectbox("📂 Nooca Warbixinta (Report Type)", list(cat_map.keys()))
            item = st.text_input("📦 Magaca Alaabta (Item Name)")
        
        note = st.text_input("📝 Faahfaahin / Tirada (Note/Qty)")
        
        if st.form_submit_button("🚀 Gudbi (Submit)", use_container_width=True):
            if employee and item:
                try:
                    data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
                    if data is None: data = pd.DataFrame()
                    data = data.dropna(how="all")
                    
                    real_category = cat_map[category_selection]
                    
                    new_row = pd.DataFrame([{
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Branch": branch,
                        "Employee": employee,
                        "Category": real_category,
                        "Item": item,
                        "Note": note
                    }])
                    
                    updated = pd.concat([data, new_row], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated)
                    st.cache_data.clear()
                    st.success("✅ Waa la gudbiyay! (Sent Successfully)")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("⚠️ Fadlan buuxi Magacaaga iyo Alaabta.")

# --- MANAGER TAB ---
with tab_manager:
    
    # --- 1. LOGIN ROW WITH ENTER BUTTON ---
    # [5, 1] means input is wide, button is small
    c_pass, c_btn = st.columns([5, 1], vertical_alignment="bottom")
    
    with c_pass:
        password = st.text_input("Geli Furaha (Password)", type="password", placeholder="Enter Password...", label_visibility="collapsed")
    with c_btn:
        # The Enter Button (Arrow Icon)
        login_click = st.button("➡️", help="Enter")

    if password == "mareero2025" or login_click:
        if password == "mareero2025":
            st.success("🔓 Soo dhawoow Maamule")
            
            # Load Data
            try:
                df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
                if df is None: df = pd.DataFrame()
                df = df.dropna(how="all")
            except:
                df = pd.DataFrame()

            if not df.empty:
                # METRICS (CRASH FIX: SPLIT LINES TO PREVENT SYNTAX ERROR)
                count_total = len(df)
                count_missing = len(df[df['Category'] == 'Maqan']) if 'Category' in df.columns else 0
                count_new = len(df[df['Category'] == 'Dalab Cusub']) if 'Category' in df.columns else 0
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Wadarta (Total)", count_total)
                m2.metric("Maqan (Missing)", count_missing)
                m3.metric("Dalab (New Req)", count_new)
                
                st.divider()
                
                # DOWNLOAD BUTTONS
                st.subheader("📄 Warbixinada (Reports)")
                col_pdf, col_xls = st.columns(2)
                
                with col_pdf:
                    if st.button("Download PDF Report", use_container_width=True):
                        st.download_button("📥 Download PDF", generate_pdf(df), "mareero_report.pdf", "application/pdf")
                with col_xls:
                    if st.button("Download Excel Data", use_container_width=True):
                        st.download_button("📥 Download Excel", generate_excel(df), "mareero_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                st.divider()

                # --- 2. EDIT/DELETE TABLE ---
                st.subheader("🛠️ Wax ka bedel / Tirtir (Edit/Delete)")
                
                # Add Checkbox Column
                df_with_delete = df.copy()
                df_with_delete.insert(0, "Select", False)

                # The Table
                edited_df = st.data_editor(
                    df_with_delete,
                    num_rows="fixed",
                    hide_index=True,
                    use_container_width=True,
                    key="data_editor",
                    column_config={
                        "Select": st.column_config.CheckboxColumn("❌", width="small")
                    }
                )
                
                st.write("") # Spacer
                
                # ACTION BUTTONS LAYOUT
                # Save (Left) ----- Spacer ----- Delete Icon (Right)
                c_save, c_mid, c_del = st.columns([3, 4, 1])

                with c_save:
                    if st.button("💾 Kaydi Isbedelka (Save)", use_container_width=True):
                        try:
                            # Remove 'Select' before saving
                            final_df = edited_df.drop(columns=["Select"])
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                            st.cache_data.clear()
                            st.success("✅ Saved!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

                with c_del:
                    # THE SMALL DELETE ICON
                    if st.button("🗑️", type="primary", help="Delete Selected Rows"):
                        try:
                            # Filter and Delete
                            rows_to_keep = edited_df[edited_df["Select"] == False]
                            final_df = rows_to_keep.drop(columns=["Select"])
                            
                            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                            st.cache_data.clear()
                            st.success("Deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.warning("⚠️ Xog ma jiro (No Data Found)")
                
        else:
            st.error("Furaha waa khalad (Wrong Password)")
