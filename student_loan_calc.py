import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# --- Configuration ---
st.set_page_config(page_title="Rethink Repayment Calculator", page_icon="🎓", layout="centered")

# --- Branding Section ---
# Try to display the logo. If it's not uploaded yet, it just skips it without crashing.
try:
    st.image("https://email-my-mp.rethinkrepayment.com/og-image.png", width=200) 
except:
    st.header("🎓 Rethink Repayment")

st.title("The Student Loan Reality Check")
st.markdown("""
**Stop guessing.** See how the **Plan 2** interest trap (RPI + 3%) affects your actual life path.
*Inspired by the Money Gains Podcast & The Rethink Repayment Campaign.*
""")

st.divider()

# --- Sidebar Inputs ---
st.sidebar.header("1. Your Loan")
current_balance = st.sidebar.number_input("Current Loan Balance (£)", value=45000, step=1000)

st.sidebar.header("2. Your Career")
annual_salary = st.sidebar.number_input("Current Annual Salary (£)", value=30000, step=500)

# --- NEW: Career Pathways ---
st.sidebar.subheader("Projected Career Path")
career_type = st.sidebar.selectbox(
    "Select a career trajectory:",
    ("Steady Growth (Public Sector/Standard)", 
     "Fast Track (Tech/Finance/Law)", 
     "Late Bloomer (Doctor/PhD)", 
     "Custom (Set your own flat rate)")
)

# Logic to determine growth rate based on selection
if career_type == "Custom (Set your own flat rate)":
    custom_growth = st.sidebar.slider("Annual Growth %", 0.0, 10.0, 2.5, 0.1) / 100
else:
    st.sidebar.info(f"Using standard assumptions for {career_type.split('(')[0]}")

st.sidebar.header("3. Economy")
rpi = st.sidebar.slider("RPI (Inflation) Rate (%)", 0.0, 15.0, 3.5, 0.1) / 100

# Constants
repayment_threshold = 27295  # Plan 2 Threshold (approx)
lower_interest_threshold = 28470
upper_interest_threshold = 51245
term_years = 30

# --- Calculation Engine ---

def get_growth_rate(year, type, custom_rate=0.025):
    """Returns the growth rate for a specific year based on career type"""
    if type == "Custom (Set your own flat rate)":
        return custom_rate
    
    elif "Steady" in type:
        return 0.025  # Steady 2.5% raises forever
        
    elif "Fast Track" in type:
        # Aggressive growth early career, plateau later
        if year < 5: return 0.10   # 10% jumps first 5 years
        if year < 10: return 0.05  # 5% next 5 years
        return 0.03                # 3% thereafter
        
    elif "Late" in type:
        # Low growth during training, huge jump, then steady
        if year < 4: return 0.01   # 1% (Residency/Training)
        if year == 4: return 0.25  # 25% Jump (Qualifying)
        return 0.03                # Steady thereafter
    
    return 0.025

def calculate_loan_trajectory(balance, start_salary, profile_type, rpi, custom_growth_rate):
    data = []
    total_paid = 0
    current_balance = balance
    current_salary = start_salary
    
    # We simulate month by month
    months = term_years * 12
    
    for month in range(months):
        year_idx = month // 12
        
        # Salary Growth (Happens once a year)
        if month > 0 and month % 12 == 0:
            growth_rate = get_growth_rate(year_idx, profile_type, custom_growth_rate)
            current_salary *= (1 + growth_rate)

        # 1. Interest Rate Calculation
        if current_salary <= lower_interest_threshold:
            interest_rate = rpi
        elif current_salary >= upper_interest_threshold:
            interest_rate = rpi + 0.03
        else:
            scale = (current_salary - lower_interest_threshold) / (upper_interest_threshold - lower_interest_threshold)
            interest_rate = rpi + (scale * 0.03)
            
        monthly_interest_rate = interest_rate / 12
        
        # 2. Repayment Calculation (9% over threshold)
        monthly_salary = current_salary / 12
        monthly_threshold = repayment_threshold / 12
        
        if monthly_salary > monthly_threshold:
            repayment = (monthly_salary - monthly_threshold) * 0.09
        else:
            repayment = 0
            
        # 3. Update Balance
        interest_accrued = current_balance * monthly_interest_rate
        final_balance_change = interest_accrued - repayment
        current_balance += final_balance_change
        
        total_paid += repayment
        
        # Store Data
        if month % 12 == 0 or month == months - 1:
            data.append({
                "Year": year_idx,
                "Loan Balance": max(0, current_balance),
                "Total Paid": total_paid,
                "Annual Salary": current_salary,
                "Interest Rate": interest_rate * 100
            })
            
        if current_balance <= 0:
            current_balance = 0
            break # Loan cleared

    return pd.DataFrame(data), current_balance, total_paid

# --- Run ---
custom_rate = 0.025
if career_type == "Custom (Set your own flat rate)":
    custom_rate = custom_growth

df, final_balance, total_repaid = calculate_loan_trajectory(
    current_balance, annual_salary, career_type, rpi, custom_rate
)

# --- Results Dashboard ---

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total You Will Pay", f"£{total_repaid:,.0f}")
with col2:
    st.metric("Debt Written Off", f"£{max(0, final_balance):,.0f}", help="Amount forgiven after 30 years")
with col3:
    multiple = total_repaid / current_balance
    st.metric("The 'Multitude'", f"{multiple:.2f}x", delta_color="inverse")

# --- Analysis Text ---
if final_balance > 0:
    st.warning(f"⚠️ ** The Trap:** You paid **£{total_repaid:,.0f}**, but the government still wrote off **£{final_balance:,.0f}**. The interest grew faster than you could pay it.")
else:
    st.success(f"🎉 **Freedom:** You actually cleared the debt! It took you {len(df)} years.")

# --- Charts ---
st.subheader("Your Debt vs. Your Cumulative Payments")

# Create a dual-line chart
base = alt.Chart(df).encode(x='Year')

line_debt = base.mark_line(color='#FF4B4B', strokeWidth=3).encode(
    y=alt.Y('Loan Balance', title='Amount (£)'),
    tooltip=['Year', 'Loan Balance', 'Annual Salary']
)

line_paid = base.mark_line(color='#1E90FF', strokeWidth=3, strokeDash=[5,5]).encode(
    y='Total Paid',
    tooltip=['Year', 'Total Paid']
)

st.altair_chart((line_debt + line_paid).interactive(), use_container_width=True)

st.caption("🔴 Red Line: What you owe (Balance) | 🔵 Blue Dashed: Total cash you have handed over")

# --- Detailed Table ---
with st.expander("See Full Data Table"):
    st.dataframe(df.style.format({
        "Loan Balance": "£{:,.2f}", 
        "Total Paid": "£{:,.2f}", 
        "Annual Salary": "£{:,.2f}", 
        "Interest Rate": "{:.2f}%"
    }))
