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
            daily_planning_cleaned = daily_planning_df.iloc[:, [0, 1, 2]].copy()
            daily_planning_cleaned.columns = ["Arr_Flight", "Dep_Flight", "Gate"]
            
            daily_planning_cleaned["Arr_Time"] = date.strftime("%Y-%m-%d")
            daily_planning_cleaned["Flight"] = daily_planning_cleaned["Arr_Flight"].str.replace("ACA", "QK", regex=False)
            daily_planning_cleaned["Date"] = pd.to_datetime(daily_planning_cleaned["Arr_Time"]).dt.date
            daily_planning_cleaned["Gate"] = daily_planning_cleaned["Gate"].astype(str).str.strip()
            
            ac_fids_df = ac_fids.parse(ac_fids.sheet_names[0])
            ac_fids_cleaned = ac_fids_df.iloc[:, [0, 2, 5]].copy()
            ac_fids_cleaned.columns = ["Flight", "Date", "Gate"]
            ac_fids_cleaned["Date"] = pd.to_datetime(ac_fids_cleaned["Date"], errors='coerce').dt.date
            ac_fids_cleaned["Gate"] = ac_fids_cleaned["Gate"].astype(str).str.strip()
            
            # Gate Mismatches Section
            st.header("Gate Mismatches")
            
            comparison_df = pd.merge(
                daily_planning_cleaned, 
                ac_fids_cleaned, 
                on=["Flight", "Date"], 
                how="inner", 
                suffixes=("_DailyPlanning", "_ACFIDS")
            )
            
            gate_mismatches = comparison_df[comparison_df["Gate_DailyPlanning"] != comparison_df["Gate_ACFIDS"]]
            
            if len(gate_mismatches) > 0:
                st.subheader("Gate Assignment Mismatches:")
                st.dataframe(gate_mismatches[["Flight", "Date", "Gate_DailyPlanning", "Gate_ACFIDS"]])
            else:
                st.success("No gate mismatches found.")
            
            # YTZ Gate Optimization Section
            st.header("YTZ Gate Optimization")
            
            # Get relevant columns: Gate (F) and Airport (G)
            ac_fids_ytz = ac_fids.parse(ac_fids.sheet_names[0])
            ac_fids_ytz = ac_fids_ytz.iloc[:, [5, 6]].copy()  # F is index 5, G is index 6
            ac_fids_ytz.columns = ["Gate", "Airport"]
            
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
                st.warning(f"Found {len(ytz_gates)} YTZ flights on gates 17-34:")
                
                # Create a styled dataframe for display
                display_df = pd.DataFrame({
                    'Gate': ytz_gates['Gate'].astype(int),
                    'Warning': ['⚠️ YTZ flight suggested to use other gate'] * len(ytz_gates)
                })
                
                st.dataframe(
                    display_df,
                    hide_index=True,
                    column_config={
                        "Gate": "Gate Number",
                        "Warning": "Status"
                    }
                )
                
                st.error(f"⚠️ {len(ytz_gates)} YTZ flights suggested to be moved to other gates")
            else:
                st.success("No YTZ flights found on gates 17-34 (Good!)")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}") 
