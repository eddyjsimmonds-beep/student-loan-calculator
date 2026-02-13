import streamlit as st
import pandas as pd
import altair as alt

# --- Page Config ---
st.set_page_config(page_title="Rethink Repayment Calculator", page_icon="🎓", layout="wide")

# --- Custom Styling ---
st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    .share-box { border: 2px dashed #4CAF50; padding: 15px; border-radius: 10px; background-color: #e8f5e9; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
col_head1, col_head2 = st.columns([1, 3])
with col_head1:
    # Try to load logo, fallback to emoji
    try:
        st.image("logo.png", width=150)
    except:
        st.markdown("# 🎓")

with col_head2:
    st.title("The Student Loan Reality Check")
    st.markdown("### Are you paying off a loan, or just paying a 30-year tax?")
    st.markdown("Inspired by the **Rethink Repayment** campaign.")

st.divider()

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("1. Your Profile")
    current_balance = st.number_input("Current Loan Balance (£)", value=45000, step=1000, help="Check your student finance portal for the exact number.")
    annual_salary = st.number_input("Current Annual Salary (£)", value=30000, step=500)
    
    st.header("2. Your Future")
    career_type = st.selectbox(
        "Career Trajectory",
        ("Steady Growth (Public Sector/Standard)", 
         "Fast Track (Tech/Finance/Law)", 
         "Late Bloomer (Doctor/PhD)", 
         "Custom Flat Rate"),
        help="How will your salary change? Fast Track assumes big jumps early on."
    )
    
    custom_rate = 0.025
    if career_type == "Custom Flat Rate":
        custom_rate = st.slider("Annual Growth %", 0.0, 10.0, 2.5, 0.1) / 100

    st.header("3. The Economy")
    rpi = st.slider("RPI (Inflation) %", 0.0, 15.0, 3.5, 0.1, help="This dictates your interest rate (RPI to RPI+3%).") / 100
    
    st.header("4. Experiment (New!)")
    extra_payment = st.number_input("Monthly Overpayment (£)", value=0, step=50, help="If you paid extra voluntarily, would it actually help?")

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
                "Interest": interest_accrued * 12 # approx annual interest
            })
            
        if balance <= 0:
            balance = 0
            break
            
    return pd.DataFrame(data), balance, total_paid

df, final_balance, total_repaid = run_simulation()
multiple = total_repaid / current_balance

# --- THE VERDICT SECTION ---
st.subheader("🔮 Your Verdict")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Original Loan", f"£{current_balance:,.0f}")
c2.metric("Total You Pay", f"£{total_repaid:,.0f}", delta=f"{multiple:.1f}x Original")
c3.metric("Written Off", f"£{max(0, final_balance):,.0f}")
c4.metric("Debt Clear Year", "Never (30 Years)" if final_balance > 0 else f"Year {len(df)}")

# Dynamic "Badge"
if final_balance > 0:
    if multiple > 2.0:
        st.error("### 🔴 Status: The Debt Trap")
        st.write("You will pay back **double** what you borrowed and *still* owe money at the end. This is the definition of negative amortization.")
    else:
        st.warning("### 🟠 Status: The Lifetime Tax")
        st.write("You never clear the debt. It acts as a 9% tax on your income for 30 years.")
else:
    st.success("### 🟢 Status: The Escape Artist")
    st.write(f"Congratulations! You beat the interest rates and cleared the loan in {len(df)} years.")
    st.balloons()

# --- Interactive Charts ---
tab1, tab2 = st.tabs(["📉 Visualise the Debt", "📊 Share Your Stats"])

with tab1:
    st.markdown("### Watch your debt grow (Red) vs What you pay (Blue)")
    
    base = alt.Chart(df).encode(x=alt.X('Year', title='Years since graduation'))
    
    # Area chart for Balance (Scary red area)
    area_balance = base.mark_area(opacity=0.3, color='#ff4b4b').encode(
        y=alt.Y('Balance', title='Loan Balance (£)'),
        tooltip=['Year', 'Balance', 'Salary']
    )
    
    # Line for Payments
    line_paid = base.mark_line(color='#1E90FF', strokeWidth=4).encode(
        y='Paid',
        tooltip=['Year', 'Paid']
    )

    st.altair_chart((area_balance + line_paid).interactive(), use_container_width=True)
    
    if extra_payment > 0:
        st.info(f"💡 **Learning Moment:** You are paying an extra £{extra_payment}/month. Toggle it to £0 in the sidebar to see if it actually made a difference!")

with tab2:
    st.markdown("### 📢 Spread the Word")
    st.write("Most people have no idea how this math works. Copy your results below and share them.")
    
    share_text = f"""
🚨 My Student Loan Reality Check 🚨

💸 Borrowed: £{current_balance:,.0f}
📉 Paying Back: £{total_repaid:,.0f}
🛑 Debt Remaining: £{final_balance:,.0f}

I will pay {multiple:.1f}x my original loan and still not clear it.
The system is broken. #RethinkRepayment #StudentLoans
    """
    st.code(share_text, language="text")
    st.caption("Copy the text above and post it on Twitter/Instagram/WhatsApp.")

# --- Data Table (Hidden by default) ---
with st.expander("Show detailed year-by-year breakdown"):
    st.dataframe(df.style.format({"Balance": "£{:,.0f}", "Paid": "£{:,.0f}", "Salary": "£{:,.0f}", "Interest": "£{:,.0f}"}))
