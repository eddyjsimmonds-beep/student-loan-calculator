import streamlit as st
import pandas as pd
import altair as alt

# --- Page Config ---
st.set_page_config(page_title="Rethink Repayment Calculator", page_icon="🎓", layout="wide")

# --- Custom Styling ---
st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #dee2e6; }
    .share-box { border: 2px dashed #4CAF50; padding: 15px; border-radius: 10px; background-color: #e8f5e9; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
col_head1, col_head2 = st.columns([1, 4])
with col_head1:
    try:
        st.image("logo.png", width=120)
    except:
        st.markdown("# 🎓")

with col_head2:
    st.title("Student Loan Reality Check")
    st.markdown("### The true cost of Plan 2 loans (RPI + 3%)")
    st.markdown("Use this tool to project your long-term repayment trajectory.")

st.divider()

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("1. Your Profile")
    current_balance = st.number_input("Current Loan Balance (£)", value=45000, step=1000)
    annual_salary = st.number_input("Current Annual Salary (£)", value=30000, step=500)
    
    st.header("2. Career Projection")
    career_type = st.selectbox(
        "Projected Income Trajectory",
        ("Steady Growth (Public Sector/Standard)", 
         "Fast Track (Tech/Finance/Law)", 
         "Late Bloomer (Doctor/PhD)", 
         "Custom Flat Rate"),
    )
    
    custom_rate = 0.025
    if career_type == "Custom Flat Rate":
        custom_rate = st.slider("Annual Growth %", 0.0, 10.0, 2.5, 0.1) / 100

    st.header("3. Economic Assumptions")
    rpi = st.slider("RPI (Inflation) %", 0.0, 15.0, 3.5, 0.1, help="Controls interest rate (RPI to RPI+3%).") / 100
    
    # --- UPDATED SECTION ---
    st.header("4. Voluntary Overpayments")
    st.caption("Is it worth paying more?")
    extra_payment = st.number_input("Monthly Overpayment (£)", value=0, step=50, help="Add a voluntary monthly payment to see if it clears the debt faster.")

# --- Constants (Plan 2) ---
repayment_threshold = 27295
lower_interest_threshold = 28470
upper_interest_threshold = 51245
term_years = 30

# --- Logic Engine ---
def get_growth_rate(year, type, custom):
    if type == "Custom Flat Rate": return custom
    if "Steady" in type: return 0.025
    if "Fast Track" in type: return 0.10 if year < 5 else (0.05 if year < 10 else 0.03)
    if "Late" in type: return 0.01 if year < 4 else (0.25 if year == 4 else 0.03)
    return 0.025

def run_simulation():
    data = []
    total_paid = 0
    balance = current_balance
    salary = annual_salary
    
    for month in range(term_years * 12):
        year = month // 12
        
        # Annual Salary Bump
        if month > 0 and month % 12 == 0:
            salary *= (1 + get_growth_rate(year, career_type, custom_rate))

        # 1. Interest Rate
        if salary <= lower_interest_threshold: interest_rate = rpi
        elif salary >= upper_interest_threshold: interest_rate = rpi + 0.03
        else:
            scale = (salary - lower_interest_threshold) / (upper_interest_threshold - lower_interest_threshold)
            interest_rate = rpi + (scale * 0.03)
            
        monthly_rate = interest_rate / 12
        
        # 2. Repayment
        monthly_salary = salary / 12
        monthly_thresh = repayment_threshold / 12
        mandatory_pay = (monthly_salary - monthly_thresh) * 0.09 if monthly_salary > monthly_thresh else 0
        
        total_monthly_pay = mandatory_pay + extra_payment
        
        # 3. Balance Update
        interest_accrued = balance * monthly_rate
        balance = balance + interest_accrued - total_monthly_pay
        total_paid += total_monthly_pay
        
        # Record Year End
        if month % 12 == 0 or month == (term_years * 12) - 1:
            data.append({
                "Year": year,
                "Balance": max(0, balance),
                "Paid": total_paid,
                "Salary": salary,
                "Interest": interest_accrued * 12 
            })
            
        if balance <= 0:
            balance = 0
            break
            
    return pd.DataFrame(data), balance, total_paid

df, final_balance, total_repaid = run_simulation()
multiple = total_repaid / current_balance

# --- THE VERDICT SECTION ---
st.subheader("📊 The Verdict")

c1, c2, c3, c4 = st.columns(4)

# 1. Original Loan
c1.metric("Original Loan", f"£{current_balance:,.0f}")

# 2. Total Paid (NOW RED if high)
# delta_color="inverse" means: Positive numbers (increase) are RED, Negative numbers are GREEN.
c2.metric(
    "Total You Pay", 
    f"£{total_repaid:,.0f}", 
    delta=f"{multiple:.1f}x Original Loan", 
    delta_color="inverse" 
)

# 3. Write Off
c3.metric("Amount Written Off", f"£{max(0, final_balance):,.0f}")

# 4. Time
if final_balance > 0:
    c4.metric("Debt Free In", "Never (30 Years)", delta="Term Ends", delta_color="off")
else:
    c4.metric("Debt Free In", f"{len(df)} Years", delta="Cleared!", delta_color="normal")

# Dynamic Status Badge
st.markdown("---")
if final_balance > 0:
    if multiple > 2.0:
        st.error(f"### 🛑 Status: The Debt Trap\nYou will pay back **{multiple:.1f}x** what you borrowed, but the interest is so high that the debt never clears. This is negative amortization.")
    else:
        st.warning(f"### 🟠 Status: The 'Graduate Tax'\nYou will likely never clear the balance. The loan functions as a 9% tax on your income for 30 years.")
else:
    st.success(f"### 🟢 Status: The Repayer\nCongratulations! You are projected to clear the loan in Year {len(df)}.")

# --- Interactive Charts ---
tab1, tab2 = st.tabs(["📉 Visualise Trajectory", "📲 Share Result"])

with tab1:
    st.markdown("#### Debt Balance (Red) vs Cumulative Payments (Blue)")
    
    base = alt.Chart(df).encode(x=alt.X('Year', title='Years since graduation'))
    
    area_balance = base.mark_area(opacity=0.3, color='#ff4b4b').encode(
        y=alt.Y('Balance', title='Amount (£)'),
        tooltip=['Year', 'Balance', 'Salary']
    )
    
    line_paid = base.mark_line(color='#1E90FF', strokeWidth=4).encode(
        y='Paid',
        tooltip=['Year', 'Paid']
    )

    st.altair_chart((area_balance + line_paid).interactive(), use_container_width=True)
    
    if extra_payment > 0:
         st.info(f"ℹ️ **Overpayment Analysis:** You are paying an extra £{extra_payment}/mo. Toggle this to £0 in the sidebar to compare the difference.")

with tab2:
    st.subheader("📢 Spread the Word")
    st.write("Copy the summary below to share your reality check:")
    
    share_text = f"""
🚨 My Student Loan Reality Check

💸 Borrowed: £{current_balance:,.0f}
📉 Paying Back: £{total_repaid:,.0f} ({multiple:.1f}x original)
🛑 Debt Remaining: £{final_balance:,.0f}

I will pay {multiple:.1f} times my loan and still not clear it.
The system is broken.
    """
    st.code(share_text, language="text")

# --- Data Table ---
with st.expander("📂 View Detailed Data Table"):
    st.dataframe(df.style.format({"Balance": "£{:,.0f}", "Paid": "£{:,.0f}", "Salary": "£{:,.0f}", "Interest": "£{:,.0f}"}))
