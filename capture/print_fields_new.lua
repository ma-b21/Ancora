-- io.stderr:write("Current Lua version: " .. _VERSION .. "\n") 5.1

description = "Print specified fields with null checks and in JSON format"
short_description = "print fields as JSON"
category = "Custom"
local json = require ("./capture/json")
local messagepack = require ("./capture/MessagePack")

args = {}

-- 字段列表
local fields = {
    "container.id",
    "evt.arg.data",
    "evt.arg.filename",
    "evt.arg.newpath",
    "evt.arg.oldpath",
    "evt.arg.pid",
    "evt.buffer", -- 判断是否是A#t#k#F#
    "evt.category",
    "evt.datetime",
    "evt.dir",
    "evt.is_io_read",
    "evt.is_io_write",
    "evt.info",
    "evt.num",
    "evt.rawres",
    "evt.time",
    "evt.outputtime",
    "evt.type",
    "fd.cip",
    "fd.cport",
    "fd.directory",
    "fd.ino",
    "fd.is_server",
    "fd.lip",
    "fd.name",
    "fd.num",
    "fd.rip",
    "fd.sip",
    "fd.sport",
    "fd.type",
    "proc.cmdline",
    "proc.exepath",
    "proc.name",
    "proc.pid",
    "proc.vpid",
    "proc.pvpid",
    "thread.tid",
    "thread.vtid",
    "fs.path.name",
    "fs.path.source",
    "fs.path.target",
}

-- 在这里请求字段
function on_init()
    -- local filename = "./capture_dir/sysdig.json"

    -- 尝试打开文件
    -- outfile, err = io.open(filename, "w")
    -- if err then
    --     io.stderr:write("Error opening file: " .. err .. "\n")
    --     return false
    -- end

    -- 请求需要的字段
    field_handles = {}
    for _, field in ipairs(fields) do
        table.insert(field_handles, chisel.request_field(field))
    end

    index_to_key = {}
    key_to_index = {}

    for i, field in ipairs(fields) do
        index_to_key[i] = field
        key_to_index[field] = i
    end

    io.write(messagepack.pack(index_to_key))

    return true
end

-- 安全获取字段值
function safe_field(field)
    local value = evt.field(field)
    if value == nil then
        return "null"
    end
    return value
end


-- 事件处理函数
function on_event()
    local event_data = {}
    for i, field_name in ipairs(fields) do
        local value = safe_field(field_handles[i])  -- 获取字段值

        -- 处理evt.buffer
        -- if field_name == "evt.buffer" then
        --     if value:sub(1, 8) == "A#t#k#F#" then
        --         value = "malicious"
        --     else
        --         value = "normal"
        --     end
        -- end

        if type(field_name) ~= "string" then
            io.stderr:write("Field name is not a string: " .. type(field_name) .. "\n")
            goto continue
        end

        if type(value) == "string" then
            event_data[field_name] = value
        elseif type(value) == "number" then
            event_data[field_name] = value
        elseif type(value) == "boolean" then
            event_data[field_name] = value
        else
            io.stderr:write("Unknown type: " .. type(value) .. "\n")
        end

        ::continue::
    end
    if event_data["container.id"] ~= "host" and event_data["container.id"] ~= "" and event_data["proc.name"] ~= "hypercorn"
        and (
            event_data["evt.category"] == "net" or (event_data["evt.category"] == "ipc" and event_data["evt.type"] == "write") 
            or event_data["evt.category"] == "process" 
            or (event_data["evt.category"] == "file")
            -- or (event_data["evt.category"] == "other" and event_data["evt.type"] == "exit_group")
            )
        -- and event_data["proc.name"] ~= "postgres"
        -- and event_data["evt.dir"] ~= ">"
        -- and event_data["evt.type"] ~= "accept4" 
        and event_data["evt.type"] ~= "getsockname" and event_data["evt.type"] ~= "getpeername" and event_data["evt.type"] ~= "ioctl"
        and event_data["evt.type"] ~= "connect" and event_data["evt.type"] ~= "socket" and event_data["evt.type"] ~= "prlimit"
        and event_data["evt.type"] ~= "newfstatat" and event_data["evt.type"] ~= "fstat" and event_data["evt.type"] ~= "stat" and event_data["evt.type"] ~= "lstat"
        and event_data["evt.type"] ~= "access"
        then
        new_event_data = {}
        for key, value in pairs(event_data) do
            if value == "null" then
                value = nil
            end
            new_event_data[key_to_index[key]] = value
        end
        local function table_to_json(tbl)
            local function serialize(tbl)
                local result = {}
                for k, v in pairs(tbl) do
                    local key = type(k) == "string" and string.format("%q", k) or k
                    local value
                    if type(v) == "table" then
                        value = serialize(v)
                    elseif type(v) == "string" then
                        value = string.format("%q", v)
                    else
                        value = tostring(v)
                    end
                    table.insert(result, string.format("%s:%s", key, value))
                end
                return "{" .. table.concat(result, ",") .. "}"
            end
            return serialize(tbl)
        end
        -- print(table_to_json(new_event_data))
        io.write(messagepack.pack(new_event_data))
    end
end

function on_capture_end()
    -- outfile:close()
end
