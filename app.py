import streamlit as st
import pandas as pd
from datetime import datetime, date
import io

st.set_page_config(page_title="Jazz Flight Operations", page_icon="✈️")

# Define tabs
tab1, tab2 = st.tabs(["Gate Checker", "Tow Move Generator"])

# Tab 1: Gate Checker
with tab1:
    st.title("Jazz Flight Gate Checker")

    # Date input
    date = st.date_input("Select Date")

    # File uploaders
    daily_planning_file = st.file_uploader("Upload ADM Gates File", type=['xlsx'], key="gate_checker_daily")
    ac_fids_file = st.file_uploader("Upload AC FIDS File", type=['xlsx'], key="gate_checker_fids")

    if st.button("Check Gates"):
        if daily_planning_file is None or ac_fids_file is None:
            st.error("Please upload both files")
        else:
            try:
                # Load Excel files
                daily_planning = pd.ExcelFile(daily_planning_file)
                ac_fids = pd.ExcelFile(ac_fids_file)
                
                # Process data for gate mismatches
                daily_planning_df = daily_planning.parse(daily_planning.sheet_names[0])
                daily_planning_cleaned = daily_planning_df.iloc[:, [0, 5, 9]].copy()
                daily_planning_cleaned.columns = ["Arr_Flight", "Dep_Flight", "Gate"]
                
                # Create separate dataframes for arrivals and departures
                arrivals = daily_planning_cleaned[["Arr_Flight", "Gate"]].copy()
                arrivals.columns = ["Flight", "Gate"]
                arrivals["Flight"] = arrivals["Flight"].str.replace("ACA", "QK", regex=False)
                
                departures = daily_planning_cleaned[["Dep_Flight", "Gate"]].copy()
                departures.columns = ["Flight", "Gate"]
                departures["Flight"] = departures["Flight"].str.replace("ACA", "QK", regex=False)
                
                # Combine arrivals and departures
                all_flights = pd.concat([arrivals, departures], ignore_index=True)
                all_flights = all_flights.dropna(subset=["Flight"])  # Remove rows with no flight numbers
                
                # Add date column and clean gates (remove A/B suffix)
                all_flights["Date"] = date
                all_flights["Date"] = pd.to_datetime(all_flights["Date"]).dt.date
                all_flights["Gate"] = all_flights["Gate"].astype(str).str.strip()
                all_flights["Gate"] = all_flights["Gate"].str.extract(r'(\d+)').fillna(all_flights["Gate"])
                
                ac_fids_df = ac_fids.parse(ac_fids.sheet_names[0])
                ac_fids_cleaned = ac_fids_df.iloc[:, [0, 2, 7]].copy()
                ac_fids_cleaned.columns = ["Flight", "Date", "Gate"]
                ac_fids_cleaned["Date"] = pd.to_datetime(ac_fids_cleaned["Date"], errors='coerce').dt.date
                ac_fids_cleaned["Gate"] = ac_fids_cleaned["Gate"].astype(str).str.strip()
                ac_fids_cleaned["Gate"] = ac_fids_cleaned["Gate"].str.extract(r'(\d+)').fillna(ac_fids_cleaned["Gate"])
                
                # Gate Mismatches Section
                st.header("Gate Mismatches")
                
                comparison_df = pd.merge(
                    all_flights, 
                    ac_fids_cleaned, 
                    on=["Flight", "Date"], 
                    how="inner", 
                    suffixes=("_DailyPlanning", "_ACFIDS")
                )
                
                # Remove duplicates if any
                comparison_df = comparison_df.drop_duplicates()
                
                gate_mismatches = comparison_df[comparison_df["Gate_DailyPlanning"] != comparison_df["Gate_ACFIDS"]]
                
                if len(gate_mismatches) > 0:
                    st.subheader("Gate Assignment Mismatches:")
                    st.dataframe(gate_mismatches[["Flight", "Date", "Gate_DailyPlanning", "Gate_ACFIDS"]])
                else:
                    st.success("No gate mismatches found.")
                
                # YTZ Gate Optimization Section
                st.header("YTZ Gate Optimization")
                
                # Get relevant columns: Flight (1st), Gate (8th) and Airport (10th)
                ac_fids_ytz = ac_fids.parse(ac_fids.sheet_names[0])
                ac_fids_ytz = ac_fids_ytz.iloc[:, [0, 7, 9]].copy()
                ac_fids_ytz.columns = ["Flight", "Gate", "Airport"]
                
                # Convert gate numbers to numeric, replacing non-numeric values with NaN
                ac_fids_ytz['Gate'] = pd.to_numeric(ac_fids_ytz['Gate'], errors='coerce')
                
                # Filter for YTZ flights on gates 17-34
                ytz_gates = ac_fids_ytz[
                    (ac_fids_ytz['Gate'] >= 17) & 
                    (ac_fids_ytz['Gate'] <= 34) &
                    ac_fids_ytz['Gate'].notna() &
                    ac_fids_ytz['Airport'].str.contains('YTZ', case=False, na=False)
                ].copy()
                
                if len(ytz_gates) > 0:
                    display_df = pd.DataFrame({
                        'Flight': ytz_gates['Flight'],
                        'Gate': ytz_gates['Gate'].astype(int),
                        'Warning': ['⚠️ YTZ flight suggested to use other gate'] * len(ytz_gates)
                    })
                    
                    st.dataframe(
                        display_df,
                        hide_index=True,
                        column_config={
                            "Flight": "Flight Number",
                            "Gate": "Gate Number",
                            "Warning": "Status"
                        }
                    )
                    
                    st.error(f"⚠️ {len(ytz_gates)} YTZ flights suggested to be moved to other gates")
                else:
                    st.success("No YTZ flights found on gates 17-34")
                
                # CRJ Gate Optimization Section
                st.header("CRJ Gate Optimization")
                
                # Get relevant columns: Flight (1st), Aircraft Type (6th), and Gate (8th)
                ac_fids_crj = ac_fids.parse(ac_fids.sheet_names[0])
                ac_fids_crj = ac_fids_crj.iloc[:, [0, 5, 7]].copy()
                ac_fids_crj.columns = ["Flight", "Aircraft", "Gate"]
                
                # Convert gate numbers to numeric
                ac_fids_crj['Gate'] = pd.to_numeric(ac_fids_crj['Gate'], errors='coerce')
                
                # Filter for CRJ on gate 25
                crj_gate_25 = ac_fids_crj[
                    (ac_fids_crj['Gate'] == 25) &
                    ac_fids_crj['Aircraft'].str.contains('CR9', case=False, na=False)
                ].copy()
                
                if len(crj_gate_25) > 0:
                    display_df = pd.DataFrame({
                        'Flight': crj_gate_25['Flight'],
                        'Aircraft': crj_gate_25['Aircraft'],
                        'Gate': crj_gate_25['Gate'].astype(int),
                        'Warning': ['⚠️ CRJ flight suggested to use other gate'] * len(crj_gate_25)
                    })
                    
                    st.dataframe(
                        display_df,
                        hide_index=True,
                        column_config={
                            "Flight": "Flight Number",
                            "Aircraft": "Aircraft Type",
                            "Gate": "Gate Number",
                            "Warning": "Status"
                        }
                    )
                    
                    st.error(f"⚠️ {len(crj_gate_25)} CRJ flights suggested to be moved from gate 25")
                else:
                    st.success("No CRJ flights found on gate 25")
                
                # High Gates Optimization Section
                st.header("U.S Gates Optimization")
                
                # Filter for gates 87-89
                high_gates = ac_fids_crj[
                    (ac_fids_crj['Gate'] >= 87) & 
                    (ac_fids_crj['Gate'] <= 89) &
                    ac_fids_crj['Gate'].notna()
                ].copy()
                
                if len(high_gates) > 0:
                    display_df = pd.DataFrame({
                        'Flight': high_gates['Flight'],
                        'Aircraft': high_gates['Aircraft'],
                        'Gate': high_gates['Gate'].astype(int),
                        'Warning': ['⚠️ Flight suggested to use other gate'] * len(high_gates)
                    })
                    
                    st.dataframe(
                        display_df,
                        hide_index=True,
                        column_config={
                            "Flight": "Flight Number",
                            "Aircraft": "Aircraft Type",
                            "Gate": "Gate Number",
                            "Warning": "Status"
                        }
                    )
                    
                    st.error(f"⚠️ {len(high_gates)} flights suggested to be moved from gates 87-89")
                else:
                    st.success("No flights found on gates 87-89")
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

# Tab 2: Tow Move Generator
with tab2:
    def normalize_gate(gate):
        if pd.isna(gate) or not isinstance(gate, str):
            return ''
        gate = gate.strip().strip('/').upper().strip()
        # Remove leading A, B, or C and return numeric part
        if gate and gate[0] in 'ABC':
            return gate[1:]
        return gate

    def parse_day(time_str, report_date):
        if pd.isna(time_str) or not isinstance(time_str, str):
            return None
        try:
            parts = time_str.split('/')
            if len(parts) > 1:
                day_part = parts[1].split()[0]
                day = int(day_part)
                # Adjust for relative date: assume report_date is today
                report_day = report_date.day
                if day == report_day:
                    return 0  # Today
                elif day == report_day - 1:
                    return -1  # Yesterday
                elif day == report_day + 1:
                    return 1  # Tomorrow
                return day - report_day  # General relative day
        except:
            return None

    def turn_time_to_minutes(turn_str):
        if pd.isna(turn_str) or not isinstance(turn_str, str) or ':' not in turn_str:
            return 0
        try:
            h, m = map(int, turn_str.split(':'))
            return h * 60 + m
        except:
            return 0

    def remove_qk_prefix(flight_num):
        if pd.isna(flight_num) or not isinstance(flight_num, str):
            return ''
        return flight_num.replace('QK ', '').strip()

    st.title("Flight Tow Move Generator")

    # Parse report date from uploaded file or use today
    report_date = date.today()
    uploaded_file = st.file_uploader("Upload your CSV file", type="csv", key="tow_move_csv")

    if uploaded_file is not None:
        try:
            # Read the file content and reset for Pandas
            file_content = uploaded_file.read().decode('utf-8')
            # Parse report date from file content
            lines = file_content.splitlines()
            for line in lines:
                if line.startswith('Report generated at:'):
                    try:
                        report_date_str = line.split(': ')[1].split()[0]
                        report_date = datetime.strptime(report_date_str, '%d%b%y').date()
                    except:
                        pass
                    break
            
            # Use StringIO to create a file-like object for Pandas
            df = pd.read_csv(io.StringIO(file_content), header=1)
            
            # Debug: Display column names and sample row
            st.write("**CSV Columns Detected:**")
            st.write(list(df.columns))
            if not df.empty:
                st.write("**Sample Row:**")
                st.write(df.iloc[0].to_dict())
            
            # Handle possible column names with newlines or duplicates
            try:
                gate_in_col = next(col for col in df.columns if 'Terminal / Gate' in col or 'Terminal\n/ Gate' in col)
                gate_out_col = next(col for col in df.columns if 'Terminal / Gate.1' in col or 'Terminal\n/ Gate.1' in col)
                turn_col = next(col for col in df.columns if 'Turn Time' in col)
                toa_in_col = 'TOA'  # First TOA is inbound
                tod_out_col = 'TOD.1' if 'TOD.1' in df.columns else 'TOD'  # Second TOD is outbound
                tail_col = 'Tail'
                flight_in_col = 'Flight'
                flight_out_col = 'Flight.1' if 'Flight.1' in df.columns else 'Flight'
            except StopIteration as e:
                st.error(f"Error: Could not find required columns in CSV. Expected columns include 'Terminal / Gate', 'Terminal / Gate.1', 'Turn Time', 'TOA', 'TOD', 'Tail', 'Flight'. Got: {list(df.columns)}")
                st.stop()
            
            tows = []
            for idx, row in df.iterrows():
                tail = row.get(tail_col, '')
                if not tail:  # Relaxed tail number check
                    continue
                
                gate_in = row.get(gate_in_col, '')
                gate_out = row.get(gate_out_col, '')
                toa_in = row.get(toa_in_col, '')
                tod_out = row.get(tod_out_col, '')
                turn = row.get(turn_col, '')
                flight_in = row.get(flight_in_col, '')
                flight_out = row.get(flight_out_col, '')
                
                norm_in = normalize_gate(gate_in)
                norm_out = normalize_gate(gate_out)
                
                day_in = parse_day(toa_in, report_date)
                day_out = parse_day(tod_out, report_date)
                
                different_date = day_in is not None and day_out is not None and day_in != day_out
                different_gate = norm_in != norm_out and norm_in and norm_out
                
                turn_min = turn_time_to_minutes(turn)
                over_2h = turn_min > 120
                
                # Debug: Show why a row might be included
                if different_date or different_gate or over_2h:
                    st.write(f"**Row {idx}**: Tail={tail}, Different Date={different_date}, Different Gate={different_gate}, Turn Time={turn} ({turn_min} min), Over 2h={over_2h}")
                
                if different_date or different_gate or over_2h:
                    # Tow logic:
                    # - Arrived yesterday (day_in < 0), departing today or later: tow from BSE to departure gate
                    # - Arriving today (day_in = 0), departing tomorrow (day_out > 0): tow from arrival gate to BSE
                    # - Different gates on same day: tow from arrival gate to departure gate
                    # - Over 2h turn time on same gate: tow from arrival gate to departure gate
                    tow_from = 'BSE' if day_in is not None and day_in < 0 else norm_in
                    tow_to = 'BSE' if day_out is not None and day_out > 0 else norm_out
                    
                    # Skip if both tow_from and tow_to are BSE
                    if tow_from == 'BSE' and tow_to == 'BSE':
                        continue
                        
                    tows.append({
                        'Arrival Flight #': remove_qk_prefix(flight_in),
                        'Tail': tail,
                        'Tow From': tow_from,
                        'Tow To': tow_to,
                        'Sked Pickup': '',
                        'Acft Release Time': '',
                        'Time Gate Opens At': '',
                        'Actual Pickup': '',
                        'Actual Drop': '',
                        'Dep Flight #': remove_qk_prefix(flight_out),
                        'Dep Time': tod_out
                    })
            
            if tows:
                tow_df = pd.DataFrame(tows)
                st.dataframe(tow_df)
                
                # Generate CSV for download
                csv = tow_df.to_csv(index=False)
                
                st.download_button(
                    label="Download Tow Move Sheet",
                    data=csv,
                    file_name="tow_move_sheet.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No tow moves found. Check debug output above for details.")
                
        except Exception as e:
            st.error(f"An error occurred in Tow Move Generator: {str(e)}")
