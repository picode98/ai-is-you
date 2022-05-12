moving = 0

function get_unit_map_str(player_found)
    local tiles = {}
    for i=1,roomsizex-2 do
        for j=1,roomsizey-2 do
            local tileid = i + j * roomsizex
            if unitmap[tileid] ~= nil then
                for k, v in pairs(unitmap[tileid]) do
                    unitObj = mmf.newObject(v)
                    table.insert(tiles, table.concat({i, j, unitObj.values[TYPE], unitObj.values[DIR]}, ","))
                end
            end
        end
    end

    return "unit_map:" .. player_found .. ":" .. table.concat(tiles, ";")
end

table.insert(mod_hook_functions["turn_end"],
function(info)
            print(get_unit_map_str(1 - generaldata2.values[NOPLAYER]))
        end
)

table.insert(mod_hook_functions["undoed_after"],
        function()
            print(get_unit_map_str(1 - generaldata2.values[NOPLAYER]))
        end
)

table.insert(mod_hook_functions["level_start"],
        function()
            print(get_unit_map_str(1))
        end
)

