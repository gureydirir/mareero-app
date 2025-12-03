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

# --- HIDE STREAMLIT ADMIN ELEMENTS (FINAL FIX) ---
# This code removes the footer, the header bar, and the top-right menu for all viewers.
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            /* Aggressive fix for footer/menu wrappers */
            .css-vk32z5 {visibility: hidden;} 
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)


# --- 1. SETUP DATABASE ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("⚠️ Error: Fadlan hubi internetkaaga ama Database-ka.")
    st.stop()

# --- 2. PROFESSIONAL REPORT ENGINES ---

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
    
    # --- COLORS & STYLES ---
    primary_color = colors.HexColor("#8B0000") # Dark Red
    text_color = colors.HexColor("#2C3E50")    # Dark Blue/Grey
    
    # --- HEADER ---
    c.setFillColor(primary_color)
    c.rect(0, height-100, width, 100, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width/2, height-60, "MAREERO AUTO SPARE PARTS REPORT")
    
    c.setFont("Helvetica", 12)
    date_str = datetime.now().strftime('%d %B %Y')
    c.drawCentredString(width/2, height-80, f"Taariikhda: {date_str}")

    # --- SUMMARY SECTION ---
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height-150, "1. KOOBITAAN (SUMMARY):")
    
    # Calc Metrics
    total = len(df)
    missing = len(df[df['Category'] == 'Maqan']) if not df.empty else 0
    new_req = len(df[df['Category'] == 'Dalab Cusub']) if not df.empty else 0
    
    # Draw Summary Box
    c.setStrokeColor(colors.lightgrey)
    c.rect(40, height-230, 515, 60, fill=0)
    
    c.setFont("Helvetica", 12)
    c.drawString(60, height-190, f"Wadarta Shaqooyinka: {total}")
    c.drawString(240, height-190, f"Alaabta Maqan: {missing}")
    c.drawString(420, height-190, f"Dalabyada Cusub: {new_req}")

    # --- CHARTS SECTION ---
    y_chart = height-280
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_chart, "2. SHAXDA XOGTA (CHARTS):")
    
    if not df.empty:
        # Chart 1: Pie
        fig1, ax1 = plt.subplots(figsize=(4, 3))
        category_counts = df['Category'].value_counts()
        if not category_counts.empty:
            category_counts.plot(kind='pie', autopct='%1.0f%%', ax=ax1, colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
            ax1.set_ylabel('')
            ax1.set_title("Qeybaha", fontsize=10)
            
            img1 = io.BytesIO()
            plt.savefig(img1, format='png', bbox_inches='tight')
            img1.seek(0)
            c.drawImage(ImageReader(img1), 40, y_chart-220, width=240, height=180)
        
        # Chart 2: Bar
        fig2, ax2 = plt.subplots(figsize=(4, 3))
        branch_counts = df['Branch'].value_counts()
        if not branch_counts.empty:
            branch_counts.plot(kind='bar', color='#8B0000', ax=ax2)
            ax2.set_title("Laamaha", fontsize=10)
            
            img2 = io.BytesIO()
            plt.savefig(img2, format='png', bbox_inches='tight')
            img2.seek(0)
            c.drawImage(ImageReader(img2), 300, y_chart-220, width=240, height=180)
    else:
        c.drawString(40, y_chart-50, "Xog kuma filna shaxda.")

    # --- CRITICAL LIST SECTION ---
    y_list = y_chart - 260
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_list, "3. ALAABTA MUHIIMKA AH (CRITICAL ITEMS):")
    
    # Table Header
    c.setFillColor(colors.lightgrey)
    c.rect(40, y_list-30, 515, 20, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_list-25, "CATEGORY")
    c.drawString(150, y_list-25, "ITEM NAME")
    c.drawString(300, y_list-25, "BRANCH")
    c.drawString(420, y_list-25, "NOTE")
    
    y_row = y_list - 50
    c.setFont("Helvetica", 10)
    
    if not df.empty:
        # Filter for Maqan or Dalab Sare
        critical_df = df[df['Category'].isin(['Maqan', 'Dalab Sare'])].head(15)
        for _, row in critical_df.iterrows():
            c.drawString(50, y_row, str(row['Category']))
            c.drawString(150, y_row, str(row['Item'])[:25]) # Cut text if too long
            c.drawString(300, y_row, str(row['Branch']))
            c.drawString(420, y_row, str(row['Note'])[:20])
            c.line(40, y_row-5, 555, y_row-5) # Underline
            y_row -= 20
            
            if y_row < 50: # New page check
                c.showPage()
                y_row = height - 50

    c.save()
    buffer.seek(0)
    return buffer

# --- 3. THE APP UI ---
st.title("🏢 Mareero Auto Spare Parts")

# TABS
tab_staff, tab_manager = st.tabs(["📝 Qeybta Shaqaalaha (Staff)", "🔐 Maamulka (Manager)"])

# --- STAFF TAB (SOMALI) ---
with tab_staff:
    st.info("Fadlan halkan ku diiwaangeli warbixintaada maalinlaha ah.")
    
    with st.form("log_form"):
        c1, c2 = st.columns(2)
        with c1:
            # UPDATED BRANCH LIST
            branch_options = [
                "Kaydka M.Hassan",
                "Branch 1",
                "Branch 3", 
                "Branch 4", 
                "Branch 5"
            ]
            branch = st.selectbox("📍 Branch", branch_options)
            employee = st.text_input("👤 Magacaaga (Your Name)")
        with c2:
            # REMOVED "Damage"
            cat_map = {
                "Alaab Maqan (Missing)": "Maqan",
                "Dalab Sare (High Demand)": "Dalab Sare",
                "Dalab Cusub (New Request)": "Dalab Cusub"
            }
            category_selection = st.selectbox("📂 Nooca Warbixinta (Report Type)", list(cat_map.keys()))
            item = st.text_input("📦 Magaca Alaabta (Item Name)")
        
        note = st.text_input("📝 Faahfaahin / Tirada (Note/Qty)")
        
        submitted = st.form_submit_button("🚀 Gudbi (Submit)")
        
        if submitted:
            if employee and item:
                # Load Data
                data = conn.read(worksheet="Sheet1", ttl=0)
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
                conn.update(worksheet="Sheet1", data=updated)
                st.success("✅ Waa la gudbiyay! (Sent Successfully)")
            else:
                st.error("⚠️ Fadlan buuxi Magacaaga iyo Alaabta.")

# --- MANAGER TAB ---
with tab_manager:
    password = st.text_input("Geli Furaha (Password)", type="password")
    
    if password == "mareero2025":
        st.success("🔓 Soo dhawoow Maamule")
        
        # Load Data
        df = conn.read(worksheet="Sheet1", ttl=0)
        df = df.dropna(how="all")
        
        # 1. LIVE METRICS
        m1, m2, m3 = st.columns(3)
        m1.metric("Wadarta Guud", len(df))
        m2.metric("Alaabta Maqan", len(df[df['Category'] == 'Maqan']))
        m3.metric("Dalabyada Cusub", len(df[df['Category'] == 'Dalab Cusub']))
        
        st.divider()
        
        # 2. DOWNLOAD BUTTONS
        st.subheader("📄 Warbixinada (Reports)")
        col_pdf, col_xls = st.columns(2)
        
        with col_pdf:
            if st.button("Download PDF Report"):
                with st.spinner("Samaynaya PDF..."):
                    pdf_bytes = generate_pdf(df)
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_bytes,
                        file_name=f"Mareero_Report_{datetime.now().date()}.pdf",
                        mime="application/pdf"
                    )
        
        with col_xls:
            if st.button("Download Excel Data"):
                with st.spinner("Samaynaya Excel..."):
                    xls_bytes = generate_excel(df)
                    st.download_button(
                        label="📥 Download Excel",
                        data=xls_bytes,
                        file_name=f"Mareero_Data_{datetime.now().date()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

        st.divider()

        # 3. EDIT / DELETE SECTION
        st.subheader("🛠️ Wax ka bedel / Tirtir (Edit/Delete)")
        st.info("ℹ️ Si aad u tirtirto: Dooro safka (row) kadibna riix 'Delete' oo ku yaal keyboard-kaaga.")
        
        # Editable Data Editor
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            key="data_editor"
        )
        
        # SAVE BUTTON
        if st.button("💾 Kaydi Isbedelka (Save Changes)"):
            try:
                conn.update(worksheet="Sheet1", data=edited_df)
                st.success("✅ Xogta waa la cusbooneysiiyay! (Database Updated)")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error updating: {e}")
        
    elif password:
        st.error("Furaha waa khalad (Wrong Password)")
