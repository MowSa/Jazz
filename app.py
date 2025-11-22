import streamlit as st
import pandas as pd
import io

def parse_date_part(time_str):
    """
    Parses the 'HHMM/DD F' format to extract the day.
    Returns the day as a string (or int) for comparison.
    Example: '0153/19 S' -> '19'
    """
    if pd.isna(time_str) or not isinstance(time_str, str):
        return None
    try:
        # Split by '/' and take the second part, then take the first 2 chars
        parts = time_str.split('/')
        if len(parts) > 1:
            day_part = parts[1].strip().split(' ')[0]
            return day_part
    except Exception:
        return None
    return None

import re

def clean_gate(gate_str):
    """
    Removes the leading '/ ' and any letters from gate strings.
    Example: '/ A2' -> '2'
    Example: '/ C80' -> '80'
    """
    if pd.isna(gate_str):
        return "Unknown"
    # Remove leading slash and whitespace first
    cleaned = str(gate_str).replace('/', '').strip()
    # Remove all non-digit characters
    cleaned = re.sub(r'[^\d]', '', cleaned)
    return cleaned if cleaned else "Unknown"

def load_data(uploaded_file):
    # Read the file, skipping the first 5 rows which are messy headers
    # We'll manually assign column names based on our analysis
    column_names = [
        "Origin", "Arr_TOD_Origin", "Arr_TOA_YUL", "Arr_PAX", "Arr_Flight",
        "Arr_Gate", "Tail", "Turn_Time",
        "Dep_Gate", "Dep_Flight", "Dep_PAX", "Dep_TOD_YUL", "Dep_TOA_Dest", "Destination"
    ]
    
    # Read CSV, assuming no header in the data area since we skip the messy ones
    df = pd.read_csv(uploaded_file, skiprows=5, header=None, names=column_names)
    
    # Filter out any footer lines or empty lines (like the report parameters at the bottom)
    # We can check if 'Origin' is valid or if 'Tail' is present
    df = df.dropna(subset=['Tail'])
    
    # Parse Days
    df['Arr_Day'] = df['Arr_TOA_YUL'].apply(parse_date_part)
    df['Dep_Day'] = df['Dep_TOD_YUL'].apply(parse_date_part)
    
    # Clean Gates
    df['Arr_Gate_Clean'] = df['Arr_Gate'].apply(clean_gate)
    df['Dep_Gate_Clean'] = df['Dep_Gate'].apply(clean_gate)
    
    return df

def clean_flight_num(flight_str):
    """
    Removes 'QK' or 'QK ' from flight numbers.
    Example: 'QK 7774' -> '7774'
    """
    if pd.isna(flight_str):
        return ""
    return str(flight_str).replace('QK', '').strip()

def identify_tows(df):
    tows = []
    
    # Determine the "Tow Sheet Day" (most frequent day in the data)
    # We combine all days we see to find the mode
    all_days = pd.concat([df['Arr_Day'], df['Dep_Day']]).dropna()
    if all_days.empty:
        return pd.DataFrame()
        
    # Get the mode (most common value)
    tow_sheet_day = all_days.mode()[0]
    
    # Convert to int for comparison if possible, assuming days are numbers
    try:
        tow_sheet_day_int = int(tow_sheet_day)
    except:
        tow_sheet_day_int = 0 # Fallback
        
    st.caption(f"Detected Tow Sheet Day: {tow_sheet_day}")
    
    for index, row in df.iterrows():
        arr_day = row['Arr_Day']
        dep_day = row['Dep_Day']
        arr_gate = row['Arr_Gate_Clean']
        dep_gate = row['Dep_Gate_Clean']
        
        # Handle Tail formatting (remove decimals if present)
        tail = row['Tail']
        try:
            if pd.notna(tail):
                tail = str(int(float(tail)))
            else:
                tail = ""
        except:
            tail = str(tail)

        flight_in = clean_flight_num(row['Arr_Flight'])
        flight_out = clean_flight_num(row['Dep_Flight'])
        dep_time = row['Dep_TOD_YUL']
        
        # Parse days to ints for comparison
        try:
            arr_day_int = int(arr_day) if arr_day else 0
            dep_day_int = int(dep_day) if dep_day else 0
        except:
            continue

        # Logic 1: Arrival was 1 or more days before Tow Sheet Day
        # "if the arrival was 1 or more days before, make it from BSE to the departure gate"
        if arr_day_int < tow_sheet_day_int:
             tows.append({
                "Arrival Flight": "", # No arrival flight needed for past arrivals
                "Tail Number": tail,
                "Tow From": "BSE",
                "Tow To": dep_gate,
                "Sked Pickup": "",
                "Aircraft Release Time": "",
                "Time Gate Open At": "",
                "Actual Pickup": "",
                "Actual Delivery": "",
                "Dep Flight#": flight_out,
                "Dep Time": dep_time
            })

        # Logic 2: Departure is on a future date (after Tow Sheet Day)
        # "if the departure is on a future date, make it from gate to BSE"
        elif dep_day_int > tow_sheet_day_int:
             tows.append({
                "Arrival Flight": flight_in,
                "Tail Number": tail,
                "Tow From": arr_gate,
                "Tow To": "BSE",
                "Sked Pickup": "",
                "Aircraft Release Time": "",
                "Time Gate Open At": "",
                "Actual Pickup": "",
                "Actual Delivery": "",
                "Dep Flight#": "", # No departure flight needed for future departures
                "Dep Time": dep_time
            })

        # Logic 3: Gate to Gate (Same Day, Different Gates)
        # "if arrival and departure gates are diffrent, its a tow"
        elif arr_gate != dep_gate and arr_gate != "Unknown" and dep_gate != "Unknown":
             tows.append({
                "Arrival Flight": flight_in,
                "Tail Number": tail,
                "Tow From": arr_gate,
                "Tow To": dep_gate,
                "Sked Pickup": "",
                "Aircraft Release Time": "",
                "Time Gate Open At": "",
                "Actual Pickup": "",
                "Actual Delivery": "",
                "Dep Flight#": flight_out,
                "Dep Time": dep_time
            })
            
    return pd.DataFrame(tows)

st.set_page_config(page_title="Airline Tow Manager", layout="wide")

st.title("✈️ Airline Tow Move Analyzer")
st.markdown("Upload your turn schedule CSV to identify required tow moves.")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    try:
        df = load_data(uploaded_file)
        
        st.subheader("Flight Data Preview")
        st.dataframe(df.head())
        
        st.subheader("Identified Tow Moves")
        tow_moves = identify_tows(df)
        
        if not tow_moves.empty:
            st.info(f"Found {len(tow_moves)} tow moves.")
            st.table(tow_moves)
        else:
            st.success("No tow moves identified based on current rules.")
            
    except Exception as e:
        st.error(f"Error processing file: {e}")
