--[[  
版权声明和许可信息  
]]  

-- Chisel 脚本描述  
description = "Print the data read and written for any FD. Combine this script with a filter to restrict what it shows. This chisel is compatible with containers using the sysdig -pc or -pcontainer argument, otherwise no container information will be shown. (Blue represents  [Write], and Red represents [Read] for all data except when the -pc or -pcontainer argument is used. If used the container.name and container.id will be represented as: Green [host], and Cyan [container]) Container information will contain '[]' around container.name and container.id.";  
short_description = "Print the data read and written by processes.";  
category = "I/O";  

-- 定义脚本参数  
args =  {}  

-- 引入必要的模块  
require "common"  
terminal = require "ansiterminal"  
terminal.enable_color(true)  

-- 参数设置回调函数  
function on_set_arg(name, val)  
        -- 如果设置了 disable_color 参数，则禁用颜色输出  
        if name == "disable_color" and val == "disable_color" then  
                terminal.enable_color(false)  
        end  

        return true  
end  

-- 初始化回调函数  
function on_init()
        -- 增加捕获长度以获取更多对话内容  
        sysdig.set_snaplen(10000)  

        chisel.set_filter("((evt.category=net or (evt.category=ipc and evt.type=write) or evt.category=process or evt.category=file) and container.id!='host' and container.id!='' and proc.name!=hypercorn)") 
        chisel.set_event_formatter("%proc.vpid %proc.pid %thread.tid %evt.num %evt.info %proc.name %evt.dir %evt.type %evt.outputtime %evt.category")  
        return true  
end  

-- 事件解析回调函数  
function on_event() 
    return true 
end  

-- 结束回调函数
function on_capture_end()
    return true
end
