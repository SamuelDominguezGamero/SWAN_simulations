# model.jl
# Motor físico sintético para calibración de parámetros de oleaje.
# Simula elevación de superficie libre η(t) a partir de una ecuación no lineal parametrizada.
using DelimitedFiles
using Random

# Parámetros físicos reales (Ground Truth) a descubrir por la optimización bayesiana
const TRUE_PARAMS = [2.5, 0.8, 1.4, 3.2]

# Ecuación sintética de dispersión/oleaje gobernada por θ = [a, b, c, d]
function wave_physics(θ::Vector{Float64}, t::Vector{Float64})
    a, b, c, d = θ
    return @. a * sin(0.2 * t + c) * cos(0.05 * t * b) + 0.5 * sin(d * 0.1 * t)
end

function main()
    mode = ARGS[1]
    out_file = ARGS[2]
    t = collect(0.0:0.5:200.0)

    if mode == "truth"
        # Genera datos experimentales de referencia con ruido gaussiano añadido
        Random.seed!(42)
        clean = wave_physics(TRUE_PARAMS, t)
        obs = clean .+ randn(length(t)) .* 0.05
        writedlm(out_file, [t obs], ',')
    elseif mode == "sim"
        # Simula el modelo físico con los parámetros candidatos propuestos
        params_file = ARGS[3]
        θ = vec(readdlm(params_file, Float64))
        sim = wave_physics(θ, t)
        writedlm(out_file, [t sim], ',')
    end
end

main()