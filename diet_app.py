import streamlit as st
import pandas as pd
from datetime import date, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---
SHEET_NAME = "My Diet Database"  # Must match your Google Sheet Name
CALORIES_PER_KG_FAT = 7700 

# --- GOOGLE SHEETS CONNECTION (SECRETS EDITION) ---
def get_db_connection():
    # Define scope
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # READ FROM STREAMLIT SECRETS (The Secure Way)
    # We create a dictionary from the secrets to mimic the JSON file structure
    key_dict = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
    }
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME)
    return sheet

# --- BACKEND FUNCTIONS ---

def load_food_db():
    base_db = {
        "Shake A (Morning - Heavy)": {"cal": 457, "p": 14.9, "f": 12.6, "c": 72.0},
        "Shake B (Evening - Lite)": {"cal": 397, "p": 12.8, "f": 7.4, "c": 68.0},
        "Shake B (Maintenance - Banana Only)": {"cal": 282, "p": 9.6, "f": 5.6, "c": 48.0},
        "Eggs (5 Large + Butter)": {"cal": 406, "p": 31.0, "f": 29.0, "c": 2.0},
        "Lunch (6 Roti + Low Oil Sabzi)": {"cal": 620, "p": 18.0, "f": 17.0, "c": 95.0},
        "Chicken Breast (200g + Oil)": {"cal": 365, "p": 60.0, "f": 11.0, "c": 0.0},
        "Pasta (265g Cooked - Bulk)": {"cal": 416, "p": 14.0, "f": 1.5, "c": 85.0},
        "Pasta (150g Cooked - Normal)": {"cal": 235, "p": 8.0, "f": 1.0, "c": 48.0},
        "Apple (1 Medium)": {"cal": 95, "p": 0.5, "f": 0.0, "c": 25.0},
    }
    try:
        sh = get_db_connection()
        worksheet = sh.worksheet("Foods")
        data = worksheet.get_all_records()
        for row in data:
            if row['name']: 
                base_db[row['name']] = {
                    "cal": float(row['cal']), "p": float(row['p']), 
                    "f": float(row['f']), "c": float(row['c'])
                }
    except Exception as e:
        # If connection fails, just use base_db so app doesn't crash
        pass
    return base_db

def save_new_food(name, cal, p, f, c):
    try:
        sh = get_db_connection()
        worksheet = sh.worksheet("Foods")
        worksheet.append_row([name, cal, p, f, c])
        st.success("✅ Saved to Cloud Database!")
    except Exception as e:
        st.error(f"❌ Save failed: {e}")

def log_meal_to_history(selected_date, name, cal, p, f, c):
    try:
        sh = get_db_connection()
        worksheet = sh.worksheet("History")
        worksheet.append_row([str(selected_date), name, cal, p, f, c])
    except Exception as e:
        st.error(f"❌ Log failed: {e}")

def delete_meal_from_history(index_in_list, selected_date, current_display_list):
    try:
        sh = get_db_connection()
        worksheet = sh.worksheet("History")
        all_values = worksheet.get_all_values()
        
        item_to_delete = current_display_list[index_in_list]
        target_name = item_to_delete['name']
        
        row_to_delete = -1
        for i, row in enumerate(all_values):
            if i == 0: continue
            if row[0] == str(selected_date) and row[1] == target_name:
                row_to_delete = i + 1
                break
        
        if row_to_delete > 0:
            worksheet.delete_rows(row_to_delete)
            st.success("Deleted from Cloud.")
            
    except Exception as e:
        st.error(f"Delete failed: {e}")

def get_log_for_date(selected_date):
    try:
        sh = get_db_connection()
        worksheet = sh.worksheet("History")
        data = worksheet.get_all_records()
        filtered = [row for row in data if str(row['date']) == str(selected_date)]
        return filtered
    except:
        return []

def get_weekly_stats():
    try:
        sh = get_db_connection()
        worksheet = sh.worksheet("History")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            return df.groupby('date')[['cal', 'p', 'f', 'c']].sum()
        return None
    except:
        return None

def smart_carb_calc(cal, p, f, c_input):
    if c_input > 0: return c_input
    return max(0, (cal - (p * 4) - (f * 9)) / 4)

# --- FRONTEND ---

st.set_page_config(page_title="My Cloud Diet", page_icon="☁️", layout="wide")
st.title("☁️ Cloud Diet Planner")

# Sidebar
st.sidebar.header("🎯 Goal Settings")
current_w = st.sidebar.number_input("Current Weight (kg)", value=62.0, step=0.1)
target_w = st.sidebar.number_input("Goal Weight (kg)", value=65.0, step=0.1)
maintenance_cal = st.sidebar.number_input("Maintenance Cals", value=2400, step=50)
pace = st.sidebar.slider("Pace (kg/week)", -1.0, 1.0, 0.3, 0.1)

daily_surplus = (pace * CALORIES_PER_KG_FAT) / 7
target_cal = maintenance_cal + daily_surplus
target_p = current_w * 2.4  
target_f = 80               
target_c = smart_carb_calc(target_cal, target_p, target_f, 0)

st.sidebar.divider()
st.sidebar.markdown(f"### 🍽️ Target: **{int(target_cal)}** cal")
st.sidebar.markdown(f"Prot: {int(target_p)}g | Fat: {int(target_f)}g | Carb: {int(target_c)}g")

if pace != 0:
    weeks_needed = abs(target_w - current_w) / abs(pace)
    finish_date = date.today() + timedelta(weeks=weeks_needed)
    st.sidebar.success(f"📅 Reach Goal: **{finish_date.strftime('%b %d')}**")

# MAIN
selected_date = st.date_input("Log for Date:", date.today())

# Load Data
FOOD_DB = load_food_db()
todays_meals = get_log_for_date(selected_date)

total_cal = sum(float(m['cal']) for m in todays_meals)
total_p = sum(float(m['p']) for m in todays_meals)
total_f = sum(float(m['f']) for m in todays_meals)
total_c = sum(float(m['c']) for m in todays_meals)

tab_log, tab_hist = st.tabs(["🍽️ Daily Logger", "📅 History & Trends"])

with tab_log:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Calories", f"{int(total_cal)}", f"{int(total_cal - target_cal)}")
    c1.progress(min(total_cal / target_cal if target_cal > 0 else 0, 1.0))
    c2.metric("Protein", f"{int(total_p)}g", f"{int(total_p - target_p)}g")
    c3.metric("Fat", f"{int(total_f)}g", f"{int(total_f - target_f)}g")
    c4.metric("Carbs", f"{int(total_c)}g", f"{int(total_c - target_c)}g")
    st.divider()
    
    with st.expander("➕ Add Food", expanded=True):
        input_method = st.radio("Method:", ["Menu", "Packet Calc"], horizontal=True)
        if input_method == "Menu":
            col1, col2 = st.columns([3, 1])
            f_choice = col1.selectbox("Search:", list(FOOD_DB.keys()))
            qty = col1.slider("Quantity:", 0.5, 3.0, 1.0, 0.5)
            if col2.button("Add"):
                item = FOOD_DB[f_choice]
                item_c = item.get('c', smart_carb_calc(item['cal'], item['p'], item['f'], 0))
                log_meal_to_history(selected_date, f"{f_choice} ({qty}x)", item['cal']*qty, item['p']*qty, item['f']*qty, item_c*qty)
                st.rerun()
        else:
            col1, col2 = st.columns(2)
            c_name = col1.text_input("Name")
            eaten = col2.number_input("Grams Eaten", 100)
            m1, m2, m3, m4 = st.columns(4)
            p_cal = m1.number_input("Cal/100g", 0); p_prot = m2.number_input("Prot/100g", 0.0); p_fat = m3.number_input("Fat/100g", 0.0); p_carb = m4.number_input("Carb/100g", 0.0)
            save_it = st.checkbox("Save to Menu?")
            if st.button("Calculate & Add"):
                mult = eaten/100
                f_cal, f_p, f_f = p_cal*mult, p_prot*mult, p_fat*mult
                f_c = p_carb*mult if p_carb > 0 else smart_carb_calc(f_cal, f_p, f_f, 0)
                log_meal_to_history(selected_date, f"{c_name} ({eaten}g)", f_cal, f_p, f_f, f_c)
                if save_it: save_new_food(f"{c_name} ({eaten}g)", f_cal, f_p, f_f, f_c)
                st.rerun()

    st.subheader(f"Log for {selected_date}")
    if todays_meals:
        for i, meal in enumerate(todays_meals):
            c1, c2, c3, c4, c5, c6 = st.columns([3, 1, 1, 1, 1, 0.5])
            c1.write(meal['name']); c2.write(f"{int(float(meal['cal']))}"); c3.write(f"{int(float(meal['p']))}"); c4.write(f"{int(float(meal['f']))}"); c5.write(f"{int(float(meal['c']))}")
            if c6.button("❌", key=f"del_{i}"):
                delete_meal_from_history(i, selected_date, todays_meals)
                st.rerun()
    else: st.info("Empty log.")

with tab_hist:
    st.subheader("Progress Over Time")
    stats = get_weekly_stats()
    if stats is not None:
        st.line_chart(stats['cal'])
        st.dataframe(stats.sort_index(ascending=False))