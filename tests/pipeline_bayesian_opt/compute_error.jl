# Script de cálculo de MAE contra la observación

using JSON

function main()
    obs_data = JSON.parsefile(ARGS[1])
    sim_data = JSON.parsefile(ARGS[2])

    y_obs = Float64.(obs_data["wave_height"])
    y_sim = Float64.(sim_data["wave_height"])

    mae = sum(abs.(y_obs .- y_sim)) / length(y_obs)

    open(ARGS[3], "w") do io
        JSON.print(io, Dict("mae" => mae), 2)
    end
    println("MAE calculado: $(round(mae, digits=5))")
end

main()
