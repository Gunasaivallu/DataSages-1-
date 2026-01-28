# 📄 Reproducibility Statement
## 1. Hardware Assumptions

- The system is designed to run on a CPU-only environment

- No GPU is required

- Tested on a standard cloud-based virtual machine and local development machines

**Minimum recommended resources:**

- 8 GB RAM

- Python 3.10+

## 2. Runtime Estimates

- Planner (LLM call): ~2–4 seconds per query (network dependent)

- Validation + execution (Pandas): < 1 second per query

- Visualization generation (Plotly): < 1 second

- End-to-end runtime per query: ~3–6 seconds

- Runtime may vary based on network latency and API response times.

## 3. Random Seed Handling

**All experiments declare a fixed random seed:**

- seed: 42


- The execution layer (Pandas-based) is fully deterministic

- The Planner Agent is configured with temperature = 0.0, resulting in deterministic JSON plan generation

- While the current system does not rely on stochastic sampling, the seed is included to:

- Ensure reproducibility if randomness is introduced in future extensions

- Maintain consistency across experimental configurations

## 4. Known Sources of Nondeterminism

- The system is designed to minimize nondeterminism. Remaining sources include:

**LLM API behavior:**

- External API latency

- Backend model updates by the provider

**Floating-point arithmetic:**

- Minor numerical differences may occur across platforms, though Pandas operations are deterministic in practice

- No nondeterminism exists in the core data execution pipeline.

## 5. Cost Considerations

- The system uses the Groq API (LLaMA 3.1 – 8B Instant) for planning and explanation

- No GPU or paid compute resources are required

**Estimated API cost:**

- Low usage due to short prompts and strict JSON output

- Total cost expected to be minimal (a few dollars at most) for evaluation runs

- No additional infrastructure or storage costs are incurred.

## 6. Reproducibility Summary

- All experiments are declaratively defined in experiments/*.yaml

- Core logic is implemented exclusively in src/

- Notebooks are supplementary and run top-to-bottom without errors

- No private or sensitive data is used

- No secrets are committed to the repository

- This project is fully reproducible given access to the specified environment and API credentials.