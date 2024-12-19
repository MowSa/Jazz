import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Jazz Flight Gate Checker", page_icon="✈️")

st.title("Jazz Flight Gate Checker")

# Date input
date = st.date_input("Select Date")

# File uploaders
daily_planning_file = st.file_uploader("Upload ADM Gates File", type=['xlsx'])
ac_fids_file = st.file_uploader("Upload AC FIDS File", type=['xlsx'])

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
            
            daily_planning_cleaned["Arr_Time"] = date.strftime("%Y-%m-%d")
            daily_planning_cleaned["Flight"] = daily_planning_cleaned["Dep_Flight"].str.replace("ACA", "QK", regex=False)
            daily_planning_cleaned["Date"] = pd.to_datetime(daily_planning_cleaned["Arr_Time"]).dt.date
            
            # Debug print before gate cleaning
            st.write("Debug - Daily Planning Gates before cleaning:", daily_planning_cleaned[["Flight", "Gate"]].head(10))
            
            daily_planning_cleaned["Gate"] = daily_planning_cleaned["Gate"].astype(str).str.extract('(\d+)').fillna(daily_planning_cleaned["Gate"])
            
            # Debug print after gate cleaning
            st.write("Debug - Daily Planning Gates after cleaning:", daily_planning_cleaned[["Flight", "Gate"]].head(10))
            
            ac_fids_df = ac_fids.parse(ac_fids.sheet_names[0])
            ac_fids_cleaned = ac_fids_df.iloc[:, [0, 2, 7]].copy()
            ac_fids_cleaned.columns = ["Flight", "Date", "Gate"]
            ac_fids_cleaned["Date"] = pd.to_datetime(ac_fids_cleaned["Date"], errors='coerce').dt.date
            
            # Debug print before gate cleaning
            st.write("Debug - AC FIDS Gates before cleaning:", ac_fids_cleaned[["Flight", "Gate"]].head(10))
            
            ac_fids_cleaned["Gate"] = ac_fids_cleaned["Gate"].astype(str).str.extract('(\d+)').fillna(ac_fids_cleaned["Gate"])
            
            # Debug print after gate cleaning
            st.write("Debug - AC FIDS Gates after cleaning:", ac_fids_cleaned[["Flight", "Gate"]].head(10))
            
            # Gate Mismatches Section
            st.header("Gate Mismatches")
            
            comparison_df = pd.merge(
                daily_planning_cleaned, 
                ac_fids_cleaned, 
                on=["Flight", "Date"], 
                how="inner", 
                suffixes=("_DailyPlanning", "_ACFIDS")
            )
            
            # Debug print merged data
            st.write("Debug - Merged Data:", comparison_df[["Flight", "Gate_DailyPlanning", "Gate_ACFIDS"]].head(10))
            
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
            ac_fids_ytz = ac_fids_ytz.iloc[:, [0, 7, 9]].copy()  # Added flight number column
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
            ac_fids_crj = ac_fids_crj.iloc[:, [0, 5, 7]].copy()  # Added flight number column
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
