# Bayesian Optimization Pipeline for Wave Parameter Calibration

An Pipeline designed to optimize physical parameters of numerical wave models (e.g., SWAN, SWASH, or synthetic wave generators) using **Gaussian Process Regression (GP)** and **Expected Improvement (EI)**.

The framework avoids parameter grid discretization (which scales poorly via the curse of dimensionality) by treating the physical solver as an expensive black-box function $f: \mathbb{R}^D \to \mathbb{R}$, sequentially probing the parameter space with minimal evaluations.

---

## 1. Directory Structure

The setup eliminates file proliferation by relying on **two persistent data files** and **two transient scratch buffers**:

```text
.
├── data/
│   ├── observations.csv     # Target wave measurements (t, eta) from buoys
│   └── best_sim.csv         # Best calibrated physical simulation
├── figures/
│   └── optimization_summary.png # 3-panel diagnostic plot (Convergence, Params, Fit)
├── bounds.json              # Centralized parameter search boundaries
├── history.csv              # Cumulative database: (iter, p1..pD, mae)
├── current_params.txt       # Transient buffer: Single row of proposed parameters
├── current_sim.csv          # Transient buffer: Output time series from solver
├── current_error.txt        # Transient buffer: Single scalar MAE value
├── model.jl                 # Numerical physics engine / solver interface
├── optimizer.jl             # Gaussian Process emulator & Acquisition optimizer
├── metrics.jl               # Metric evaluation interface (MAE, RMSE, SI)
├── Snakefile                # Atomic rule definitions for workflow management
└── run_pipeline.py          # Orchestration loop (LHS warm-up + Active BO + Plots)
```

## 2. Mathematical Framework

### A. The Optimization Problem
Given experimental records at fixed stations $X_{\text{obs}}(s, t)$ and model outputs $X_{\text{sim}}(s, t; \vec{\theta})$ governed by parameters $\vec{\theta} \in \Omega \subset \mathbb{R}^D$: $$\vec{\theta}^* = \arg\min_{\vec{\theta} \in \Omega} \text{MAE}(\vec{\theta})$$

$$\text{MAE}(\vec{\theta}) = \frac{1}{S \cdot T} \sum_{s=1}^{S} \sum_{t=1}^{T} \left\vert{} X_{\text{obs}}(s, t) - X_{\text{sim}}(s, t; \vec{\theta}) \right\vert{}$$

In this Toy-Model based pipeline, real data are simulated by a parametrized model: `model.jl`, and a surrogate model (Gaussian Process) tries to find the real values of its parameters.

### B. Surrogate Model: Gaussian Process
We place a GP prior over the objective function:
$$f(\vec{\theta}) \sim \mathcal{GP}\left(m(\vec{\theta}), \, k(\vec{\theta}, \vec{\theta}')\right)$$

* **Prior mean**: Constant, set to the empirical mean of observed evaluations: $m(\vec{\theta}) = \bar{y}$.
* **Covariance Kernel**: Matérn 5/2 with Automatic Relevance Determination (ARD). This enforces twice-differentiable sample paths ($C^2$), preventing the over-smoothing and pathological stiffness of the standard Radial Basis Function (RBF) kernel, where $l_d$ represents the independent correlation length-scale along parameter dimension $d$.:
$$k(\vec{\theta}, \vec{\theta}') = \sigma_f^2 \left(1 + \sqrt{5}r + \frac{5}{3}r^2\right) \exp\left(-\sqrt{5}r\right)$$
$$r = \sqrt{\sum_{d=1}^{D} \frac{(\theta_d - \theta'_d)^2}{l_d^2}}$$


* **Posterior Conditioning**: Given $N$ completed simulations $\mathcal{D}_N = \{(\vec{\theta}_i, y_i)\}_{i=1}^N$, the posterior distribution at an unobserved point $\vec{\theta}_*$ is analytical:
$$f(\vec{\theta}_*) \mid \mathcal{D}_N \sim \mathcal{N}\left(\mu(\vec{\theta}_*), \, \sigma^2(\vec{\theta}_*)\right)$$
$$\mu(\vec{\theta}_*) = \mathbf{k}_*^T (\mathbf{K} + \sigma_n^2 \mathbf{I})^{-1} \mathbf{y}$$
$$\sigma^2(\vec{\theta}_*) = k(\vec{\theta}_*, \vec{\theta}_*) - \mathbf{k}_*^T (\mathbf{K} + \sigma_n^2 \mathbf{I})^{-1} \mathbf{k}_*$$
where $\sigma_n^2 \approx 10^{-4}$ is a numerical nugget ensuring matrix inversion stability.

### C. Acquisition Function: Expected Improvement (EI)
To balance exploitation ($\mu \to \min$) and exploration ($\sigma \to \max$), the next simulation query $\vec{\theta}_{\text{next}}$ maximizes the expected reduction over the current best error $y^+ = \min_{i} y_i$:
$$\alpha_{\text{EI}}(\vec{\theta}) = \mathbb{E}\left[\max(0, \, y^+ - Y)\right], \quad Y \sim \mathcal{N}(\mu(\vec{\theta}), \sigma^2(\vec{\theta}))$$
$$\alpha_{\text{EI}}(\vec{\theta}) = (y^+ - \mu(\vec{\theta})) \Phi\left(\frac{y^+ - \mu(\vec{\theta})}{\sigma(\vec{\theta})}\right) + \sigma(\vec{\theta}) \phi\left(\frac{y^+ - \mu(\vec{\theta})}{\sigma(\vec{\theta})}\right)$$
where $\Phi(\cdot)$ and $\phi(\cdot)$ denote the standard Gaussian CDF and PDF, respectively.

---

## 3. Step-by-Step Pipeline Mechanics

```text
[ Phase 1: Warm-up ]
            Latin Hypercube Sampling (LHS)
            Generates N_init design points
                           │
                           ▼
          Runs model.jl & computes real MAE
                           │
                           ▼
       Initializes history.csv with real evaluations
                           │
 ┌─────────────────────────┴──────────────────────────────┐
 │               Phase 2: Active BO Loop                  │
 │                                                        │
 │ 1. ASK (Julia)                                         │
 │    optimizer.jl fits GP on history.csv                 │
 │    Solves: argmax EI(θ) via multi-start L-BFGS-B       │
 │    Overwrites: current_params.txt                      │
 │                                                        │
 │ 2. RUN (Snakemake -> Local/SLURM)                      │
 │    Reads: current_params.txt                           │
 │    Executes: model.jl sim                              │
 │    Overwrites: current_sim.csv                         │
 │                                                        │
 │ 3. EVALUATE                                            │
 │    Compares: current_sim.csv vs observations.csv       │
 │    Computes MAE and overwrites: current_error.txt      │
 │                                                        │
 │ 4. TELL                                                │
 │    Appends single line to history.csv:                 │
 │    iter, p1, ..., pD, MAE                              │
 └─────────────────────────┬──────────────────────────────┘
                           │
             Repeat until budget is reached

```

---

## 4. Execution & CLI Options

The pipeline is orchestrated with `run_pipeline.py` and executed within the project environment via `pixi`:

```bash
# Clean run from scratch (purges previous history, buffers, and unlocks Snakemake)
pixi run python tests/pipeline_bayesian_opt/run_pipeline.py -r

# Custom warm-up and active optimization budget
pixi run python tests/pipeline_bayesian_opt/run_pipeline.py -r --lhs 6 --iters 20

# Resume an existing run without purging history.csv
pixi run python tests/pipeline_bayesian_opt/run_pipeline.py --iters 10
```

### CLI Arguments
* `-r`, `--restart`: Resets and purges history, transient buffers, and unlocks Snakemake lockfiles.
* `--lhs <int>`: Number of Latin Hypercube Sampling initial exploration points (default: `6`).
* `--iters <int>`: Number of active Bayesian Optimization iterations (default: `20`).

---

## 5. Diagnostic Plots & Outputs

Upon convergence or completion of the optimization loop, the pipeline generates:
* **`history.csv`**: Complete record of all evaluated design points `(iter, p1..pD, mae)`.
* **`data/best_sim.csv`**: High-resolution physical simulation evaluated with the optimal parameter set found.
* **`figures/optimization_summary.png`**: Publication-quality diagnostic plot comprising:
  1. **Convergence Curve**: MAE vs Iteration (LHS exploration vs BO iterations) with the cumulative best-so-far envelope.
  2. **Parameter Trajectories**: Parameter evolution paths contrasted against ground truth reference values.
  3. **Physical Response**: Time-series comparison of target observations $\eta(t)$ against the calibrated model response.