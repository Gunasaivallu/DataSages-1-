import streamlit as st
import pandas as pd

from agents.planner import PlannerAgent
from agents.explainer import ExplainerAgent
from executor.executor import execute_plan
from agents.dataset_analyzer import analyze_dataset
from schemas.plan_validator import validate_plan
from config import MODEL_NAME


def is_dataset_info_query(question: str) -> bool:
    keywords = [
        "dataset information",
        "dataset info",
        "describe dataset",
        "data overview",
        "summary of dataset",
        "about the dataset",
        "dataset summary"
    ]
    q = question.lower()
    return any(k in q for k in keywords)

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="AI Data Analyst Agent",
    page_icon="📊",
    layout="wide"
)

# ==================================================
# CUSTOM CSS
# ==================================================
st.markdown("""
<style>
.main {
    background-color: #f8f9fa;
}

.card {
    background-color: white;
    padding: 1.25rem;
    border-radius: 10px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.08);
    margin-bottom: 1.2rem;
}

h1, h2, h3 {
    color: #1f2937;
}

div.stButton > button {
    border-radius: 8px;
    font-weight: 600;
}

div[data-testid="stAlert"] {
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# SESSION STATE INIT
# ==================================================
if "history" not in st.session_state:
    st.session_state.history = []

# ==================================================
# HEADER
# ==================================================
st.markdown("""
# 📊 AI Data Analyst Agent  
**Ask questions in plain English and get precise insights from your entire dataset.**

🔹 Upload any CSV dataset  
🔹 Ask analytical questions  
🔹 Get exact answers with full data analysis  
""")

st.divider()

# ==================================================
# SIDEBAR
# ==================================================
with st.sidebar:
    st.header("📁 Upload Dataset")

    uploaded_file = st.file_uploader(
        "Upload a CSV file",
        type=["csv"],
        help="Upload any tabular CSV file for analysis"
    )

    st.markdown("---")

    if st.button("🧹 Clear History"):
        st.session_state.history = []
        st.success("Session history cleared!")

# ==================================================
# MAIN CONTENT
# ==================================================
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(uploaded_file, encoding="latin1")

    # ---------------- Dataset Preview ----------------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.expander("📋 Dataset Preview", expanded=True):
        st.dataframe(df.head(20), use_container_width=True)
        st.caption(f"📊 Total: {df.shape[0]:,} rows × {df.shape[1]} columns")
    st.markdown('</div>', unsafe_allow_html=True)

    # ---------------- Question Input ----------------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🧠 Ask a Data Question")

    question = st.text_input(
        "",
        placeholder="e.g. Which country has the highest and lowest population?"
    )

    analyze_col, clear_col = st.columns([1, 1])

    with analyze_col:
        analyze_clicked = st.button("🚀 Analyze", use_container_width=True)

    with clear_col:
        if st.button("🧹 Clear Input"):
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ==================================================
    # ANALYSIS FLOW
    # ==================================================
    if analyze_clicked and question:
        try:
            # DATASET INFO QUERY
            if is_dataset_info_query(question):
                dataset_table = analyze_dataset(df)

                st.markdown("### 📄 Dataset Information")
                st.dataframe(dataset_table, use_container_width=True)

                explainer = ExplainerAgent()

                with st.spinner("💡 Generating dataset insights..."):
                    insight = explainer.explain_dataset(df)

                st.success("💡 Dataset Insights")
                st.markdown(insight)

                st.stop()
        
            planner = PlannerAgent()
            explainer = ExplainerAgent()

            with st.spinner("🧠 Analyzing your question..."):
                plan = planner.generate_plan(list(df.columns), question)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            with st.expander("🧠 Analysis Plan", expanded=False):
                st.json(plan)
                user_intent = plan.get("user_intent", {})
                st.info(f"""
**Detected Intent:**
- Focus: {user_intent.get('focus', 'general')}
- Explicit Limit: {user_intent.get('explicit_limit', 'None (full dataset)')}
- Show Highest: {user_intent.get('show_highest', False)}
- Show Lowest: {user_intent.get('show_lowest', False)}
""")
            st.markdown('</div>', unsafe_allow_html=True)
            
            validate_plan(plan, list(df.columns))

            with st.spinner("⚙️ Executing analysis on full dataset..."):
                result_df, fig, original_filtered_df = execute_plan(df, plan)

            # ============================================================
            # CRITICAL FIX: Generate insights BEFORE limiting display
            # This ensures explainer sees the FULL dataset results
            # ============================================================
            with st.spinner("💡 Analyzing full dataset..."):
                # Pass FULL result_df and original_df to explainer
                insight = explainer.explain(
                    question, 
                    result_df,  # Full results, not limited
                    plan=plan, 
                    # original_df=original_filtered_df  # Original data for accurate extremes
                )

            # ---------------- Results Display ----------------
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 📊 Analysis Results")
            
            user_intent = plan.get("user_intent", {})
            
            # NOW we limit what's DISPLAYED (but insights were already generated from full data)
            if user_intent.get("focus") in ["highest", "lowest"]:
                # Show only the answer (top 1)
                st.dataframe(result_df.head(1), use_container_width=True)
                st.caption(f"✅ Showing the {user_intent['focus']} value from {len(result_df):,} total records analyzed")
                
            elif user_intent.get("focus") == "both":
                # Show highest and lowest
                combined = pd.concat([
                    result_df.head(1),
                    result_df.tail(1)
                ]).drop_duplicates()
                st.dataframe(combined, use_container_width=True)
                st.caption(f"✅ Showing highest and lowest from {len(result_df):,} total records analyzed")
                
            else:
                # Show all results (or limited for display)
                display_limit = min(50, len(result_df))
                st.dataframe(result_df.head(display_limit), use_container_width=True)
                
                if len(result_df) > display_limit:
                    st.caption(f"📊 Showing first {display_limit:,} of {len(result_df):,} total results")
                else:
                    st.caption(f"📊 Showing all {len(result_df):,} results")

            if fig:
                # Limit visualization for performance, but insights are from full data
                st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # ---------------- Display Insights (Already Generated) ----------------
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.success("💡 Key Insights")
            st.markdown(insight)
            st.caption(f"✅ Analysis performed on complete dataset ({len(df):,} rows)")
            st.markdown('</div>', unsafe_allow_html=True)

            # ---------------- Save to History ----------------
            st.session_state.history.append({
                "question": question,
                "plan": plan,
                "result": result_df,
                "insight": insight
            })

        except Exception as e:
            st.error("❌ Analysis Failed")
            st.exception(e)

    # ==================================================
    # SESSION HISTORY
    # ==================================================
    if st.session_state.history:
        st.markdown("## 🕘 Analysis History")

        for idx, item in enumerate(reversed(st.session_state.history), 1):
            with st.expander(f"Query {idx}: {item['question']}"):
                st.markdown("**🧠 Analysis Plan**")
                st.json(item["plan"])

                st.markdown("**📊 Results**")
                st.dataframe(item["result"].head(10), use_container_width=True)

                st.markdown("**💡 Answer**")
                st.markdown(item["insight"])

else:
    st.info("👈 Upload a CSV file from the sidebar to begin analysis")