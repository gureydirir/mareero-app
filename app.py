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

# --- HIDE FOOTER CSS ---
st.markdown("""
<style>
#MainMenu {visibility: hidden !important;}
header {visibility: hidden !important; height: 0 !important;}
footer {visibility: hidden !important; display: none !important;}
div[data-testid="stDecoration"] {visibility: hidden !important; height: 0 !important;}
.main {padding-bottom: 0 !important;}
div.block-container {padding-bottom: 0 !important; margin-bottom: -150px !important;}
div[data-testid="stStatusWidget"] {visibility: hidden !important; display: none !important;}
</style>
""", unsafe_allow_html=True)

# --- 1. SETUP DATABASE ---
try:
    # Uses [connections.gsheets] in secrets.toml by default
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Get the specific URL from secrets if you need to target a specific sheet
    SHEET_URL = st.secrets["gcp_sheet_url"] 
except Exception as e:
    st.error(f"⚠️ Error connecting to Database: {e}")
    st.stop()

# --- 2. REPORT ENGINES ---

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
    
    # Colors
    primary_color = colors.HexColor("#8B0000") 
    text_color = colors.HexColor("#2C3E50")    
    
    # Header
    c.setFillColor(primary_color)
    c.rect(0, height-100, width, 100, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width/2, height-60, "MAREERO AUTO SPARE PARTS STAFF REPORT")
    
    c.setFont("Helvetica", 12)
    date_str = datetime.now().strftime('%d %B %Y')
    c.drawCentredString(width/2, height-80, f"Taariikhda: {date_str}")

    # Metrics
    total = len(df)
    # Safety check for empty dataframe or missing columns
    if not df.empty and 'Category' in df.columns:
        missing = len(df[df['Category'] == 'Maqan'])
        new_req = len(df[df['Category'] == 'Dalab Cusub'])
    else:
        missing = 0
        new_req = 0

    # Summary Section
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height-150, "1. KOOBITAAN (SUMMARY):")
    
    c.setStrokeColor(colors.lightgrey)
    c.rect(40, height-230, 515, 60, fill=0)
    
    c.setFont("Helvetica", 12)
    c.drawString(60, height-190, f"Wadarta Shaqooyinka: {total}")
    c.drawString(240, height-190, f"Alaabta Maqan: {missing}")
    c.drawString(420, height-190, f"Dalabyada Cusub: {new_req}")

    # Charts Section
    y_chart = height-280
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_chart, "2. SHAXDA XOGTA (CHARTS):")
    
    if not df.empty and 'Category' in df.columns and 'Branch' in df.columns:
        # Pie Chart
        fig1, ax1 = plt.subplots(figsize=(4, 3))
        category_counts = df['Category'].value_counts()
        if not category_counts.empty:
            ax1.pie(category_counts, labels=category_counts.index, autopct='%1.0f%%', colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
            ax1.set_title("Qeybaha", fontsize=10)
            
            img1 = io.BytesIO()
            plt.savefig(img1, format='png', bbox_inches='tight')
            plt.close(fig1) # IMPORTANT: Close plot to prevent memory leak
            img1.seek(0)
            c.drawImage(ImageReader(img1), 40, y_chart-220, width=240, height=180)
        
        # Bar Chart
        fig2, ax2 = plt.subplots(figsize=(4, 3))
        branch_counts = df['Branch'].value_counts()
        if not branch_counts.empty:
            branch_counts.plot(kind='bar', color='#8B0000', ax=ax2)
            ax2.set_title("Laamaha", fontsize=10)
            plt.xticks(rotation=45, ha='right')
            
            img2 = io.BytesIO()
            plt.savefig(img2, format='png', bbox_inches='tight')
            plt.close(fig2) # IMPORTANT: Close plot
            img2.seek(0)
            c.drawImage(ImageReader(img2), 300, y_chart-220, width=240, height=180)
    else:
        c.drawString(40, y_chart-50, "Xog kuma filna shaxda.")

    # Critical List
    y_list = y_chart - 260
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y_list, "3. ALAABTA MUHIIMKA AH (CRITICAL ITEMS):")
    
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
    
    if not df.empty and 'Category' in df.columns:
        critical_df = df[df['Category'].isin(['Maqan', 'Dalab Sare'])].head(15)
        for _, row in critical_df.iterrows():
            c.drawString(50, y_row, str(row['Category']))
            c.drawString(150, y_row, str(row.get('Item', ''))[:25])
            c.drawString(300, y_row, str(row.get('Branch', '')))
            c.drawString(420, y_row, str(row.get('Note', ''))[:20])
            c.line(40, y_row-5, 555, y_row-5)
            y_row -= 20
            
            if y_row < 50:
                c.showPage()
                y_row = height - 50

    c.save()
    buffer.seek(0)
    return buffer

# --- 3. APP UI ---
st.title("🏢 Mareero Auto Spare Parts")

tab_staff, tab_manager = st.tabs(["📝 Qeybta Shaqaalaha (Staff)", "🔐 Maamulka (Manager)"])

# --- STAFF TAB ---
with tab_staff:
    st.info("Fadlan halkan ku diiwaangeli warbixintaada maalinlaha ah.")
    
    with st.form("log_form", clear_on_submit=True): # clear_on_submit helps UX
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
            category_selection = st.selectbox("📂 Nooca Warbixinta", list(cat_map.keys()))
            item = st.text_input("📦 Magaca Alaabta (Item Name)")
        
        note = st.text_input("📝 Faahfaahin / Tirada (Note/Qty)")
        submitted = st.form_submit_button("🚀 Gudbi (Submit)")
        
        if submitted:
            if employee and item:
                try:
                    data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
                    # Handle case where sheet is totally empty
                    if data is None:
                        data = pd.DataFrame(columns=["Date", "Branch", "Employee", "Category", "Item", "Note"])
                    else:
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
                    st.cache_data.clear() # Clear cache to force reload next time
                    st.success("✅ Waa la gudbiyay! (Sent Successfully)")
                except Exception as e:
                    st.error(f"Error submitting data: {e}")
            else:
                st.error("⚠️ Fadlan buuxi Magacaaga iyo Alaabta.")

# --- MANAGER TAB ---
with tab_manager:
    password = st.text_input("Geli Furaha (Password)", type="password")
    
    if password == "mareero2025":
        st.success("🔓 Soo dhawoow Maamule")
        
        # Load Data
        try:
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
            df = df.dropna(how="all")
        except:
            df = pd.DataFrame() 

        if not df.empty:
            # 1. LIVE METRICS
            m1, m2, m3 = st.columns(3)
            m1.metric("Wadarta Guud", len(df))
            m2.metric("Alaabta Maqan", len(df[df['Category'] == 'Maqan']) if 'Category' in df.columns else 0)
            m3.metric("Dalabyada Cusub", len(df[df['Category'] == 'Dalab Cusub']) if 'Category' in df.columns else 0)
            
            st.divider()
            
            # 2. DOWNLOAD BUTTONS
            st.subheader("📄 Warbixinada (Reports)")
            col_pdf, col_xls = st.columns(2)
            
            with col_pdf:
                if st.button("Download PDF Report"):
                    with st.spinner("Samaynaya PDF..."):
                        try:
                            pdf_bytes = generate_pdf(df)
                            st.download_button(
                                label="📥 Click to Save PDF",
                                data=pdf_bytes,
                                file_name=f"Mareero_Report_{datetime.now().date()}.pdf",
                                mime="application/pdf"
                            )
                        except Exception as e:
                            st.error(f"Error generating PDF: {e}")
            
            with col_xls:
                if st.button("Download Excel Data"):
                    with st.spinner("Samaynaya Excel..."):
                        xls_bytes = generate_excel(df)
                        st.download_button(
                            label="📥 Click to Save Excel",
                            data=xls_bytes,
                            file_name=f"Mareero_Data_{datetime.now().date()}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

            st.divider()

            # 3. EDIT / DELETE SECTION
            st.subheader("🛠️ Wax ka bedel / Tirtir (Edit/Delete)")
            
            # A. Add a temporary 'Delete' column for the checkboxes
            df_with_delete = df.copy()
            df_with_delete.insert(0, "Delete", False)

            # B. The Data Editor
            edited_df = st.data_editor(
                df_with_delete,
                num_rows="fixed", # This hides the messy toolbar icons
                hide_index=True,  # This hides the 0, 1, 2 numbers (The "hera")
                use_container_width=True,
                key="data_editor",
                column_config={
                    "Delete": st.column_config.CheckboxColumn(
                        "Tirtir?",
                        help="Select rows to delete",
                        default=False,
                    )
                }
            )
            
            # C. The Action Buttons
            col_save, col_delete = st.columns([1, 1])

            with col_save:
                if st.button("💾 Kaydi Isbedelka (Save Edits)"):
                    try:
                        # Remove the 'Delete' column before saving
                        final_df = edited_df.drop(columns=["Delete"])
                        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                        st.cache_data.clear()
                        st.success("✅ Updated Successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            with col_delete:
                # The DELETE Button (Red)
                if st.button("🗑️ Delete Selected Rows", type="primary"):
                    try:
                        # 1. Filter out the rows where 'Delete' is True
                        rows_to_keep = edited_df[edited_df["Delete"] == False]
                        
                        # 2. Drop the 'Delete' column so we don't save it to Google Sheets
                        final_df = rows_to_keep.drop(columns=["Delete"])
                        
                        # 3. Update Google Sheets
                        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=final_df)
                        
                        st.cache_data.clear()
                        st.success("✅ Items Deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting: {e}")

        else:
            st.warning("⚠️ Xog ma jiro (No Data Found)")
            
    elif password:
        st.error("Furaha waa khalad (Wrong Password)")
