import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# --- Configuration & Page Setup ---
st.set_page_config(page_title="Student Loan Reality Calculator", layout="centered")

st.title("🎓 The Student Loan Reality Check")
st.markdown("""
This calculator helps you visualize the long-term impact of **Plan 2 Student Loans** (post-2012).
It models how high interest rates (RPI + 3%) can cause your loan to grow even while you make repayments.
""")

# --- Sidebar Inputs ---
st.sidebar.header("Your Details")

current_balance = st.sidebar.number_input("Current Loan Balance (£)", value=45000, step=1000)
annual_salary = st.sidebar.number_input("Annual Salary (£)", value=30000, step=500)
salary_growth = st.sidebar.slider("Expected Annual Salary Growth (%)", 0.0, 10.0, 2.5, 0.1) / 100

st.sidebar.header("Economic Assumptions")
rpi = st.sidebar.slider("RPI (Inflation) Rate (%)", 0.0, 15.0, 3.5, 0.1) / 100

st.sidebar.header("Loan Constants (Plan 2)")
# Thresholds as of 2025/26 estimates
repayment_threshold = st.sidebar.number_input("Repayment Threshold (£)", value=29385)
lower_interest_threshold = 28470
upper_interest_threshold = 51245
term_years = 30

# --- Calculation Logic ---

def calculate_loan_trajectory(balance, salary, growth, rpi, repay_thresh):
    data = []
    total_paid = 0
    
    # We simulate month by month for accuracy
    months = term_years * 12
    current_balance = balance
    current_salary = salary
    
    for month in range(months):
        year = month // 12
        
        # Update salary annually
        if month > 0 and month % 12 == 0:
            current_salary *= (1 + growth)
            # NOTE: In reality, thresholds also rise, but currently they are frozen/stagnant.
            # You can uncomment the line below to simulate threshold growth with RPI:
            # repay_thresh *= (1 + rpi) 

        # 1. Calculate Interest Rate for this month
        # Rate is RPI if under lower threshold
        # Rate is RPI + 3% if over upper threshold
        # Rate scales linearly in between
        if current_salary <= lower_interest_threshold:
            interest_rate = rpi
        elif current_salary >= upper_interest_threshold:
            interest_rate = rpi + 0.03
        else:
            scale = (current_salary - lower_interest_threshold) / (upper_interest_threshold - lower_interest_threshold)
            interest_rate = rpi + (scale * 0.03)
            
        monthly_interest_rate = interest_rate / 12
        
        # 2. Calculate Repayment
        # 9% of everything earned above the threshold
        monthly_salary = current_salary / 12
        monthly_threshold = repay_thresh / 12
        
        if monthly_salary > monthly_threshold:
            repayment = (monthly_salary - monthly_threshold) * 0.09
        else:
            repayment = 0
            
        # 3. Apply to Balance
        interest_accrued = current_balance * monthly_interest_rate
        final_balance_change = interest_accrued - repayment
        current_balance += final_balance_change
        
        total_paid += repayment
        
        # Append data for graphing (record end of each year)
        if month % 12 == 0 or month == months - 1:
            data.append({
                "Year": year,
                "Loan Balance": max(0, current_balance),
                "Total Paid": total_paid,
                "Annual Salary": current_salary,
                "Interest Rate": interest_rate * 100
            })
            
        if current_balance <= 0:
            current_balance = 0
            break

    return pd.DataFrame(data), current_balance, total_paid

# --- Run Calculation ---
df, final_balance, total_repaid = calculate_loan_trajectory(
    current_balance, annual_salary, salary_growth, rpi, repayment_threshold
)

# --- Display Results ---

st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Repaid", f"£{total_repaid:,.0f}")
with col2:
    st.metric("Debt Written Off", f"£{max(0, final_balance):,.0f}")
with col3:
    is_paid_off = final_balance <= 0
    st.metric("Did you clear it?", "YES" if is_paid_off else "NO")

# --- The "Ripped Off" Factor ---
# Calculate ratio of payment to original loan
multiple = total_repaid / current_balance
st.subheader(f" The 'Multitude'")
st.markdown(f"You will pay back **{multiple:.2f}x** your current loan balance.")

if not is_paid_off:
    st.warning(f"⚠️ **Negative Amortization Alert:** Despite paying **£{total_repaid:,.0f}**, your debt was written off at **£{final_balance:,.0f}**. You effectively paid a 'graduate tax' for 30 years without clearing the principal.")

# --- Visualisation ---
st.subheader("Projected Loan Balance Over Time")
chart = alt.Chart(df).mark_line(strokeWidth=3).encode(
    x='Year',
    y='Loan Balance',
    tooltip=['Year', 'Loan Balance', 'Total Paid', 'Annual Salary']
).interactive()

st.altair_chart(chart, use_container_width=True)

st.subheader("Data Table")
st.dataframe(df.style.format({"Loan Balance": "£{:,.2f}", "Total Paid": "£{:,.2f}", "Annual Salary": "£{:,.2f}", "Interest Rate": "{:.2f}%"}))

st.markdown("---")
st.caption("Disclaimer: This is for illustrative purposes. Actual RPI and thresholds vary by government policy.")
