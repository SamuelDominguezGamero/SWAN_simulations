 # Modelo implementado en Julia para la Física del oleaje sintético y generador de observaciones

using JSON
using Random

const TRUE_PARAMS = [2.5, 0.8, 1.4, 3.2]

function wave_physics(θ::Vector{Float64}, t::Vector{Float64})
    a, b, c, d = θ
    η = @. a * sin(0.2 * t + c) * cos(0.05 * t * b) + 0.5 * sin(d * 0.1 * t)
    return η
end

function main()
    mode = ARGS[1]
    out_file = ARGS[2]
    t = collect(0.0:0.5:200.0)

    if mode == "truth"
        Random.seed!(42)
        clean_signal = wave_physics(TRUE_PARAMS, t)
        noise = randn(length(t)) .* 0.05
        obs = clean_signal .+ noise
        
        open(out_file, "w") do io
            JSON.print(io, Dict("t" => t, "wave_height" => obs), 2)
        end
        println("Datos experimentales de referencia generados en: $out_file")

    elseif mode == "sim"
        params_file = ARGS[3]
        payload = JSON.parsefile(params_file)
        θ = Float64.(payload["params"])
        
        sim_signal = wave_physics(θ, t)
        
        open(out_file, "w") do io
            JSON.print(io, Dict("t" => t, "wave_height" => sim_signal), 2)
        end
    end
end

main()
