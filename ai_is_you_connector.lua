moving = 0

function dump(o)
    if type(o) == 'table' then
        local s = '{ '
        for k,v in pairs(o) do
            if type(k) ~= 'number' then k = '"'..k..'"' end
            s = s .. '['..k..'] = ' .. dump(v) .. ','
        end
        return s .. '} '
    else
        return tostring(o)
    end
end

names_to_indices = {}
idx = 0
for i,tile in pairs(tileslist) do
    if tile.name ~= nil then
        names_to_indices[tile.name] = idx
        -- print(tile.name .. ":" .. idx)
        idx = idx + 1
    end
end

print('cfg:' .. idx)

function get_unit_map_str(player_found)
    local tiles = {}
    for i=1,roomsizex-2 do
        for j=1,roomsizey-2 do
            local tileid = i + j * roomsizex
            if unitmap[tileid] ~= nil then
                for k, v in pairs(unitmap[tileid]) do
                    unitObj = mmf.newObject(v)

                    if names_to_indices[unitObj.strings[UNITNAME]] ~= nil then
                        table.insert(tiles, table.concat({i, j, names_to_indices[unitObj.strings[UNITNAME]], unitObj.values[DIR]}, ","))
                    end
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

table.insert(mod_hook_functions["level_win"],
        function()
            print('level_win')
        end
)

table.insert(mod_hook_functions["level_restart"],
        function()
            print(get_unit_map_str(1))
        end
)

