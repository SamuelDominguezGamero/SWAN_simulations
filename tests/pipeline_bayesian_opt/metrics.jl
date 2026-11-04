# metrics.jl
# Evaluación cuantitativa de discrepancia entre observaciones y simulación física.
# Uso: julia --project=@. metrics.jl <obs.csv> <sim.csv> <output.txt> [metric]

using DelimitedFiles
using Statistics

function compute_metric(obs::Vector{Float64}, sim::Vector{Float64}, metric::String)
    diff = sim .- obs
    
    # MAE (métrica por defecto): robusta frente a oscilaciones bruscas y ruido puntual
    if metric == "mae"
        return mean(abs.(diff))
    elseif metric == "rmse"
        return sqrt(mean(diff.^2))
    elseif metric == "mse"
        return mean(diff.^2)
    elseif metric == "bias"
        return mean(diff)
    elseif metric == "si"  # Scatter Index (dispersión normalizada, típica en oceanografía)
        return sqrt(mean((diff .- mean(diff)).^2)) / mean(obs)
    else
        error("Métrica no reconocida: $metric. Opciones válidas: mae, rmse, mse, bias, si")
    end
end

function main()
    if length(ARGS) < 3
        println(stderr, "Uso: julia metrics.jl <obs.csv> <sim.csv> <output.txt> [metric]")
        exit(1)
    end

    obs_file = ARGS[1]
    sim_file = ARGS[2]
    out_file = ARGS[3]
    metric_name = length(ARGS) >= 4 ? lowercase(ARGS[4]) : "mae"

    # Se asume formato CSV con columna 1 = tiempo, columna 2 = elevación/altura
    obs_data = readdlm(obs_file, ',', Float64)
    sim_data = readdlm(sim_file, ',', Float64)

    obs = obs_data[:, 2]
    sim = sim_data[:, 2]

    val = compute_metric(obs, sim, metric_name)

    writedlm(out_file, [val])
end

main()