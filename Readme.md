# PROJECT TITLE: AI Data Analyst Agent (CSV-Based Analysis)

**Employee Name:** Gunasaivallu

---

## 1. Research Question / Hypothesis

Can a Planner–Validator–Executor–Explainer architecture powered by Large Language Models enable **reproducible, safe, and structured analysis of CSV datasets**, while preventing hallucinated computations and non-deterministic execution?

---

## 2. Motivation and Relevance

While LLMs are increasingly used for data analysis, many existing systems suffer from:

* Non-deterministic execution
* Hidden or opaque computation steps
* Hallucinated results presented as facts

This project addresses these issues by **strictly separating reasoning from execution**. LLMs are used only for planning and explanation, while all computations are performed deterministically using Pandas. This design mirrors real-world requirements for trustworthy analytics systems in enterprise and decision-support environments.

---

## 3. Project Overview

This project implements an AI-powered Data Analyst Agent that performs structured, reproducible data analysis on user-uploaded CSV files.

The system allows users to ask analytical questions in natural language and automatically:

* Generates a structured JSON analysis plan
* Validates the plan against a strict schema
* Executes the plan deterministically using Pandas
* Produces tables and visualizations
* Explains results in clear, human-readable language

The application is delivered as an interactive **Streamlit web interface**.

---

## 4. System Architecture

**Architecture Pattern:** Planner → Validator → Executor → Explainer

**Execution Flow:**
User → Streamlit UI → Planner Agent → Plan Validator → Executor → Explainer Agent → Results

### Component Responsibilities

* **Planner Agent:** Converts natural-language questions into structured JSON analysis plans
* **Validator:** Ensures the plan uses only allowed operations and valid columns
* **Executor:** Performs deterministic computations using Pandas and Plotly
* **Explainer Agent:** Generates natural-language insights from numerical outputs

The LLM never directly accesses or manipulates the dataset.

---

## 5. Models and Versions Used

* **LLaMA 3.1 – 8B Instant** (via Groq API)

  * Used for planning and explanation
  * Temperature controlled to reduce variability

No fine-tuning was performed.

---

## 6. Prompting Strategy

* Structured system prompts enforcing JSON-only output
* Explicit schema instructions for allowed operations
* Defensive parsing and validation
* No free-form code generation

This approach minimizes hallucinations and enforces predictable planner behavior.

---

## 7. Evaluation Protocol

Evaluation was conducted using:

* **Automated evaluation:** Verification of aggregation, filtering, grouping, and sorting correctness
* **Human evaluation:** Assessment of clarity and usefulness of generated insights

All evaluation configurations are defined declaratively in `experiments/*.yaml` and referenced in `report.pdf`.

---

## 8. Key Results

* Deterministic execution across repeated runs
* High accuracy for aggregation and comparison queries
* Clear separation between reasoning and execution logic

Detailed results and analysis are provided in **Sections 4–6 of `report.pdf`**.

---

## 9. Limitations and Ethical Considerations

### Limitations

* Planner accuracy depends on LLM reliability
* Complex multi-step queries may require iterative planning

### Ethical Considerations

* No private or sensitive data is used
* Users provide their own datasets
* Execution is restricted to predefined safe operations

---

## 10. Installation Steps

1. Clone the repository

```bash
git clone <your-repository-url>
cd ai-data-analyst
```

2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Set environment variables
   Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

---

## 11. How to Run the Application

```bash
streamlit run app.py
```

Then open the URL shown in the terminal (usually [http://localhost:8501](http://localhost:8501)).

---

## 12. Example Queries

* Compare total SALES by COUNTRY
* Show average SALES for each REGION
* Show sales distribution
* Find correlation between SALES and PROFIT
* Describe the dataset
* Give dataset summary

---

## 13. Features

* CSV file upload and preview
* Natural language query interface
* JSON-based analysis planning
* Schema validation for safety
* Deterministic Pandas execution
* Interactive visualizations (Plotly)
* AI-generated insights
* Dataset-level metadata and insights

---

## 14. Reproducibility Notes

* Fixed random seeds are used where applicable
* Execution logic is fully deterministic
* Known nondeterminism is limited to LLM generation

Full details are documented in `reproducibility.md`.

---

## 15. Use of Generative Tools (Disclosure)

Generative AI tools were used for:

* Code scaffolding
* Prompt design
* Documentation drafting

All outputs were reviewed and validated manually.

---

## 16. Technology Stack

**Language:** Python
**LLM:** Groq API (LLaMA 3.1 – 8B Instant)
**Data Processing:** Pandas
**Visualization:** Plotly
**UI:** Streamlit
**Validation & Safety:** Custom JSON schema validation
