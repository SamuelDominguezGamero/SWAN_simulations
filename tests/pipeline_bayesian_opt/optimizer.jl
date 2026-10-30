# Proceso Gaussiano con Matérn 5/2 + Expected Improvement
# Uso: julia --project=. optimizer.jl history.json next_candidate.json
using JSON
using AbstractGPs
using KernelFunctions
using Optim
using Distributions
using LinearAlgebra
using Random

# 1. Cargar el historial acumulado desde el archivo JSON
function load_history(filepath::String)
    data = JSON.parsefile(filepath)
    bounds = [Float64.(b) for b in data["bounds"]]
    
    n_samples = length(data["iterations"])
    n_dims = length(bounds)
    
    X_mat = zeros(Float64, n_dims, n_samples)
    y_vec = zeros(Float64, n_samples)
    
    for (i, iter) in enumerate(data["iterations"])
        X_mat[:, i] = Float64.(iter["params"])
        y_vec[i] = Float64(iter["mae"])
    end
    
    return bounds, ColVecs(X_mat), y_vec
end

# 2. Función de Adquisición: Expected Improvement (EI)
function expected_improvement(θ::Vector{Float64}, gp_model, y_best::Float64)
    # Consulta la distribución posterior N(μ, σ²) en el punto candidato θ
    pred_dist = marginals(gp_model(ColVecs(reshape(θ, :, 1))))[1]
    μ = mean(pred_dist)
    σ = std(pred_dist)
    
    # Si la incertidumbre es prácticamente nula, la mejora esperada es cero
    if σ <= 1e-6
        return 0.0
    end
    
    # Para minimización: mejora esperada respecto al mejor error previo
    Δ = y_best - μ
    z = Δ / σ
    std_norm = Normal(0.0, 1.0)
    
    ei = Δ * cdf(std_norm, z) + σ * pdf(std_norm, z)
    return ei
end

# 3. Flujo principal: ajuste del GP y búsqueda del siguiente punto
function main()
    if length(ARGS) < 2
        println("Error: Argumentos insuficientes.")
        println("Uso: julia optimizer.jl <history.json> <output_candidate.json>")
        exit(1)
    end

    history_file = ARGS[1]
    out_file = ARGS[2]

    # Cargar datos pasados
    bounds, X_train, y_train = load_history(history_file)
    n_dims = length(bounds)
    y_best = minimum(y_train)

    # --- Configuración del Proceso Gaussiano ---
    # Escalas características independientes por parámetro (ARD)
    ranges = [b[2] - b[1] for b in bounds]
    inv_length_scales = 1.0 ./ (0.25 .* ranges)
    k = 1.0 * transform(Matern52Kernel(), ARDTransform(inv_length_scales))
    
    # Prior con media constante centrada en la media del historial
    f_prior = GP(mean(y_train), k)
    
    # Posterior: condicionamiento a los datos (1e-4 es el nugget de estabilidad numérica)
    gp_model = posterior(f_prior(X_train, 1e-4), y_train)

    # --- Maximización de Expected Improvement ---
    lb = [b[1] for b in bounds]
    ub = [b[2] for b in bounds]
    
    # Función a minimizar en Optim.jl (-EI para maximizar EI)
    cost_func(θ) = -expected_improvement(θ, gp_model, y_best)

    best_candidate = zeros(n_dims)
    best_ei = -Inf

    # Múltiples reinicios aleatorios para evitar mínimos locales en la superficie de adquisición
    for _ in 1:40
        θ_0 = lb .+ rand(n_dims) .* (ub .- lb)
        res = optimize(cost_func, lb, ub, θ_0, Fminbox(LBFGS()), 
                       Optim.Options(iterations=80, f_tol=1e-5))
        
        current_ei = -Optim.minimum(res)
        if current_ei > best_ei
            best_ei = current_ei
            best_candidate = Optim.minimizer(res)
        end
    end

    # Guardar la sugerencia en formato JSON para el orquestador
    open(out_file, "w") do io
        JSON.print(io, Dict("params" => best_candidate), 2)
    end

    println("Siguiente candidato sugerido: ", round.(best_candidate, digits=4), " (EI: $(round(best_ei, digits=6)))")
end

main()
