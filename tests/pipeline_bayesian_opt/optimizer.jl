# optimizer.jl
# Módulo de optimización bayesiana: Ajuste de Proceso Gaussiano (GP) y optimización
# de la función de adquisición Expected Improvement (EI).
using DelimitedFiles
using JSON
using AbstractGPs, KernelFunctions, Optim, Distributions, LinearAlgebra

function main()
    # 1. Leer los límites centralizados del espacio paramétrico
    bounds_data = JSON.parsefile("bounds.json")
    bounds = [Float64.(b) for b in bounds_data["bounds"]]
    n_dims = length(bounds)

    # 2. Leer historia acumulada desde CSV [iter, p1..pD, mae]
    data = readdlm("history.csv", ',', Float64, skipstart=1)
    X_train = ColVecs(Matrix(data[:, 2:(1 + n_dims)]'))
    y_train = data[:, end]

    # 3. Ajustar el GP con Matérn 5/2 y ARD (Automatic Relevance Determination)
    # Longitudes de correlación independientes por dimensión proporcionales al rango de búsqueda
    ranges = [b[2] - b[1] for b in bounds]
    inv_ls = 1.0 ./ (0.25 .* ranges)
    k = 1.0 * (Matern52Kernel() ∘ ARDTransform(inv_ls))
    # 1e-4 actúa como "nugget" numérico para garantizar estabilidad en la inversión de matrices
    gp = posterior(GP(mean(y_train), k)(X_train, 1e-4), y_train)

    y_best = minimum(y_train)

    # 4. Expected Improvement (EI): equilibra explotación (minimizar media) y exploración (incertidumbre)
    function expected_improvement(θ)
        dist = marginals(gp(ColVecs(reshape(θ, :, 1))))[1]
        μ, σ = mean(dist), std(dist)
        σ <= 1e-6 && return 0.0
        z = (y_best - μ) / σ
        std_norm = Normal()
        return (y_best - μ) * cdf(std_norm, z) + σ * pdf(std_norm, z)
    end

    # 5. Maximizar adquisición mediante optimización multi-start (Fminbox L-BFGS acotado)
    # Múltiples arranques aleatorios para sortear óptimos locales en la superficie de adquisición
    lb = [b[1] for b in bounds]
    ub = [b[2] for b in bounds]
    best_cand = zeros(n_dims)
    best_ei = -Inf

    for _ in 1:40
        θ0 = lb .+ rand(n_dims) .* (ub .- lb)
        res = optimize(θ -> -expected_improvement(θ), lb, ub, θ0, Fminbox(LBFGS()))
        if -Optim.minimum(res) > best_ei
            best_ei = -Optim.minimum(res)
            best_cand = Optim.minimizer(res)
        end
    end

    # 6. Escribir propuesta de parámetros para la siguiente simulación física
    writedlm("current_params.txt", best_cand')
end

main()