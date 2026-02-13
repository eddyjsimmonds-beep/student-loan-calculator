import streamlit as st
import pandas as pd
import altair as alt
import urllib.parse

# --- Configuration ---
st.set_page_config(page_title="Rethink Repayment Calculator", page_icon="🎓", layout="centered")

# --- CUSTOMIZE YOUR LINK HERE ---
APP_URL = "https://student-loan-reality.streamlit.app"

# --- Custom CSS Styling ---
st.markdown("""
<style>
    .big-font { font-size:24px !important; font-weight: bold; }
    /* Removed the .stMetric block that was breaking Dark Mode */
    
    /* Make buttons full width on mobile for easier tapping */
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold;}
    
    /* Fix logo centering */
    [data-testid="stImage"] { display: block; margin-left: auto; margin-right: auto; }
</style>
""", unsafe_allow_html=True)

# --- Header Section ---
try:
    st.image("https://email-my-mp.rethinkrepayment.com/og-image.png", width=200)
except:
    st.markdown("# 🎓")

st.title("Student Loan Reality Check")
st.markdown("### ⚠️ Are you paying off a loan, or just a lifelong tax?")
st.markdown("Discover the **'negative amortization'** trap: See why your payments might not even cover the interest.")

# --- MOBILE TIP ---
with st.expander("📝 **CLICK HERE to enter your loan details**", expanded=True):
    st.info("👈 **Desktop:** Use the Sidebar on the left.\n\n📱 **Mobile:** Tap the **'>'** arrow at the top-left to open settings.")

st.divider()

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("1. Select Your Plan")
    plan_type = st.radio(
        "Which plan are you on?",
        ("Plan 2 (Uni start 2012-2022)", "Plan 5 (Uni start 2023+)"),
    )
    
    st.header("2. Your Profile")
    current_balance = st.number_input("Current Loan Balance (£)", value=45000, step=1000)
    annual_salary = st.number_input("Current Annual Salary (£)", value=30000, step=500)
    
    st.header("3. Career Projection")
    career_type = st.selectbox(
        "Projected Income Trajectory",
        ("Steady Growth (Public Sector)", 
         "Fast Track (Tech/Finance)", 
         "Late Bloomer (Doctor/PhD)", 
         "Custom Flat Rate"),
    )
    
    custom_rate = 0.025
    if career_type == "Custom Flat Rate":
        custom_rate = st.slider("Annual Growth %", 0.0, 10.0, 2.5, 0.1) / 100

    st.header("4. Economic Assumptions")
    rpi = st.slider("RPI (Inflation) %", 0.0, 15.0, 3.5, 0.1) / 100
    
    st.header("5. Voluntary Overpayments")
    extra_payment = st.number_input("Monthly Overpayment (£)", value=0, step=50)

# --- CALCULATOR ENGINE ---

if "Plan 5" in plan_type:
    repayment_threshold = 25000
    term_years = 40
    is_plan_5 = True
else:
    repayment_threshold = 27295
    term_years = 30
    is_plan_5 = False
    
lower_interest_threshold = 28470
upper_interest_threshold = 51245

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
    
    data.append({"Year": 0, "Balance": balance, "Paid": 0, "Salary": salary, "Interest": 0})
    
    for month in range(term_years * 12):
        year_idx = month // 12
        if month > 0 and month % 12 == 0:
            salary *= (1 + get_growth_rate(year_idx, career_type, custom_rate))

        if is_plan_5:
            interest_rate = rpi
        else:
            if salary <= lower_interest_threshold: interest_rate = rpi
            elif salary >= upper_interest_threshold: interest_rate = rpi + 0.03
            else:
                scale = (salary - lower_interest_threshold) / (upper_interest_threshold - lower_interest_threshold)
                interest_rate = rpi + (scale * 0.03)
            
        monthly_rate = interest_rate / 12
        monthly_salary = salary / 12
        monthly_thresh = repayment_threshold / 12
        
        mandatory_pay = 0
        if monthly_salary > monthly_thresh:
            mandatory_pay = (monthly_salary - monthly_thresh) * 0.09
        
        total_monthly_pay = mandatory_pay + extra_payment
        interest_accrued = balance * monthly_rate
        balance = balance + interest_accrued - total_monthly_pay
        
        if balance < 0:
            total_monthly_pay += balance 
            balance = 0
            
        total_paid += total_monthly_pay
        
        if (month + 1) % 12 == 0:
            data.append({
                "Year": (month + 1) // 12,
                "Balance": balance,
                "Paid": total_paid,
                "Salary": salary,
                "Interest": interest_accrued * 12 
            })

    return pd.DataFrame(data), balance, total_paid

df, final_balance, total_repaid = run_simulation()
multiple = total_repaid / current_balance

# --- VERDICT DASHBOARD ---
st.header("📊 The Verdict")

# Using 2 columns instead of 4 for mobile readability
c1, c2 = st.columns(2)
c1.metric("Original Loan", f"£{current_balance:,.0f}")
c2.metric("Total Paid", f"£{total_repaid:,.0f}", delta=f"{multiple:.1f}x", delta_color="inverse")

c3, c4 = st.columns(2)
c3.metric("Written Off", f"£{max(0, final_balance):,.0f}")

if final_balance > 0:
    c4.metric("Debt Free?", "Never", delta=f"{term_years} Years", delta_color="off")
else:
    clear_year = df[df['Balance'] == 0]['Year'].min()
    c4.metric("Debt Free?", f"Year {int(clear_year)}", delta="Cleared!", delta_color="normal")

st.markdown("---")
if final_balance > 0:
    if multiple > 2.0:
        st.error(f"### 🛑 Status: The Debt Trap\nYou will pay back **{multiple:.1f}x** what you borrowed, but the interest is so high that the debt never clears.")
    else:
        st.warning(f"### 🟠 Status: The 'Lifelong Tax'\nYou will likely never clear the balance. The loan functions as a 9% tax on your income for {term_years} years.")
else:
    st.success(f"### 🟢 Status: The Repayer\nCongratulations! You are projected to clear the loan in Year {int(df[df['Balance'] == 0]['Year'].min())}.")

# --- TABS: VISUALS & SHARING ---
tab1, tab2 = st.tabs(["📉 Visualise Trajectory", "📲 Share Result"])

with tab1:
    st.caption("Debt Balance (Red) vs Cumulative Payments (Blue)")
    
    base = alt.Chart(df).encode(
        x=alt.X('Year', title='Years', scale=alt.Scale(domain=[0, term_years]))
    )
    
    area_balance = base.mark_area(opacity=0.3, color='#ff4b4b').encode(
        y=alt.Y('Balance', title='Amount (£)'),
        tooltip=['Year', 'Balance', 'Salary']
    )
    
    line_paid = base.mark_line(color='#1E90FF', strokeWidth=4).encode(
        y='Paid',
        tooltip=['Year', 'Paid']
    )

    st.altair_chart((area_balance + line_paid), use_container_width=True)
    
    if extra_payment > 0:
         st.info(f"ℹ️ **Overpayment:** You are paying an extra £{extra_payment}/mo.")

    with st.expander("📂 View Detailed Data Table"):
        # FIXED: Added .hide() to remove the duplicate index column
        st.dataframe(
            df.style.format({"Balance": "£{:,.0f}", "Paid": "£{:,.0f}", "Salary": "£{:,.0f}", "Interest": "£{:,.0f}"}).hide(),
            use_container_width=True
        )

with tab2:
    st.subheader("📢 Spread the Word")
    st.write("Click a button to instantly share your reality check.")
    
    plan_name = "Plan 5" if is_plan_5 else "Plan 2"
    
    share_text = f"""
🚨 My Student Loan Reality Check ({plan_name}) 🚨

💸 Borrowed: £{current_balance:,.0f}
📉 Paying Back: £{total_repaid:,.0f} ({multiple:.1f}x)
🛑 Debt Remaining: £{final_balance:,.0f}

I will pay {multiple:.1f}x my loan and still not clear it.
The system is broken.

Check your numbers here: {APP_URL}
#RethinkRepayment
    """
    
    encoded_text = urllib.parse.quote(share_text)
    
    # Grid for buttons
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("💚 WhatsApp", f"https://wa.me/?text={encoded_text}", use_container_width=True)
        st.link_button("🦅 X / Twitter", f"https://twitter.com/intent/tweet?text={encoded_text}", use_container_width=True)
    with col2:
        st.link_button("✈️ Telegram", f"https://t.me/share/url?url={urllib.parse.quote(APP_URL)}&text={encoded_text}", use_container_width=True)
        st.link_button("✉️ Email", f"mailto:?subject=Student%20Loan%20Check&body={encoded_text}", use_container_width=True)

    st.markdown("---")
    st.caption("Copy for Instagram/TikTok:")
    st.code(share_text, language="text")
