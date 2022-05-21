TileMap = {
    new = function(id)
        tbl = {}
        tbl[0] = { get_x = function(self, x, y)
                return 255
                --unit_list = unitmap[x + y * roomsizex]
                --if unit_list == nil or #unit_list == 0 then
                --    return 255
                --else
                --    return 1
                --end
            end }
        return tbl
    end
}

names_to_indices = {}
num_tiles = 0
for i,tile in pairs(tileslist) do
    if tile.name ~= nil then
        names_to_indices[tile.name] = num_tiles
        -- print(tile.name .. ":" .. idx)
        num_tiles = num_tiles + 1
    end
end

function get_unit_map()
    local tiles = {}
    for i=1,roomsizex-2 do
        for j=1,roomsizey-2 do
            local tileid = i + j * roomsizex
            if unitmap[tileid] ~= nil then
                for k, v in pairs(unitmap[tileid]) do
                    unitObj = mmf.newObject(v)

                    if names_to_indices[unitObj.strings[UNITNAME]] ~= nil then
                        table.insert(tiles, {i, j, names_to_indices[unitObj.strings[UNITNAME]], unitObj.values[DIR]})
                    end
                end
            end
        end
    end

    return tiles
end

mmf_objstore = {
    spritedata = { strings = {}, values = {
        FIXEDTILESIZE = 1
    }, flags = {} },
    generaldata = { strings = {}, values = {}, flags = {}},
    generaldata2 = { strings = {}, values = {}, flags = {}},
    generaldata3 = { strings = {}, values = {}, flags = {}},
    generaldata4 = { strings = {}, values = {}, flags = {}},
    generaldata5 = { strings = {}, values = {}, flags = {}},
    units = {}
}

test_world = 'baba'
mmf_objstore['generaldata'].values[MODE] = 0
mmf_objstore['generaldata'].strings[WORLD] = test_world
MF_setfile("world","Data/Worlds/" .. test_world .. "/world_data.txt")

mmf_objstore['generaldata'].strings[CURRLEVEL] = ''
mmf_objstore['generaldata'].strings[LANG] = 'en'
mmf_objstore['generaldata'].values[UPDATE] = 0
mmf_objstore['generaldata'].flags[LOGGING] = 1
mmf_objstore['generaldata5'].values[AUTO_ON] = 0


mmf = {
    newObject = function (id)
        if mmf_objstore[id] ~= nil then
            return mmf_objstore[id]
        else
            return mmf_objstore['units'][id]
        end
    end
}

changes = {}

function MF_create(id)
    mmf_objstore['units'][id] = { strings = {}, values = {}, flags = {} }
    return id
end

function MF_changesprite(id, sprite, root)

end

function MF_cleanremove(id)

end

function MF_removeblockeffect(id)

end

function MF_cleandecors()

end

function MF_update()

end

function MF_log(event, key, details)
    MF_alert('[' .. event .. ']: ' .. key .. ': ' .. details)
end

function MF_setcolour(id, c1, c2)

end

function MF_defaultcolour(id)

end

function MF_animframe(id, frame)

end

function MF_musicstate(state)

end

function MF_particles(name, x, y, param4, color1, color2, param7, param8)

end

function MF_restart(param)

end

function MF_remove(id)
    mmf_objstore['units'][id] = nil
end

function mock_addunit(id, className, xpos, ypos, dir, float)
    MF_create(id)
    obj = mmf.newObject(id)
    obj.className = className
    obj.fixed = id
    obj.values[XPOS] = xpos
    obj.values[YPOS] = ypos
    obj.values[FLOAT] = float
    obj.values[DIR] = dir
    obj.flags[DEAD] = false
    addunit(id)
end

function mock_clearunits()
    mmf_objstore['units'] = {}
    clearunits()
end

function mock_undo()
    if #mock_undobuffer > 0 then
        mock_clearunits()
        mmf_objstore['units'] = mock_undobuffer[#mock_undobuffer]
        for key, val in pairs(mmf_objstore['units']) do
            addunit(key)
        end

        table.remove(mock_undobuffer)
        updatecode = 1
        code()
    end
end

function deepcopy(obj, seen)
    -- Handle non-tables and previously-seen tables.
    if type(obj) ~= 'table' then return obj end
    if seen and seen[obj] then return seen[obj] end

    -- New table; mark it as seen and copy recursively.
    local s = seen or {}
    local res = {}
    s[obj] = res
    for k, v in pairs(obj) do res[deepcopy(k, s)] = deepcopy(v, s) end
    return setmetatable(res, getmetatable(obj))
end

mock_undobuffer = {}
function mock_undo_checkpoint()
    this_table = {}
    for key, val in pairs(mmf_objstore['units']) do
        if type(key) == 'number' and key >= 1000 then
            this_table[key] = deepcopy(val)
        end
    end
    table.insert(mock_undobuffer, this_table)
end