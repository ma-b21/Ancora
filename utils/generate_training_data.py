# generate training data for matchare

import re  
import json 
import copy
import random
from urllib.parse import unquote
from calculate_accuracy import check_fs_operation

def parse_request_info(request_info, ret_id=False):  
    # 分割请求行  
    lines = request_info.split('..')  
    # print("lines:", lines)
    # 解析第一行（HTTP请求行）  
    http_line = lines[0]
    method, uri, _ = http_line.split(' ')
    
    # 解析请求体  
    body_match = [line for line in lines if line.startswith('{')]  
    body = body_match[0] if body_match else '{}'
    
    try:  
        body_json = json.loads(body)  
    except:  
        body_json = {}  

    if ret_id:
        try:
            req_id = [line for line in lines if line.startswith('x_request_id:')][0].split(': ')[1]
        except:
            req_id = None

    # 提取参数  
    params = {}

    # 提取 URI 中的查询参数
    if '?' in uri:
        query_string = uri.split('?')[1]
        query_params = query_string.split('&')
        for param in query_params:
            try:
                key, value = param.split('=')
                # 对key和value进行URL解码
                key = unquote(key)
                value = unquote(value)
                params[key] = value
            except ValueError:
                params[f"param{query_params.index(param)}"] = unquote(param)

    # 解析 multipart/form-data（处理 mode, currentpath, filename）
    boundary_match = re.search(r'boundary=(.+?)\.\.\.\.', request_info)
    if boundary_match:
        boundary = boundary_match.group(1)
        # print("boundary:", boundary)
        parts = request_info.split('--' + boundary)
        # print("parts:", parts)
        for part in parts:
            if 'Content-Disposition' in part:
                # 提取 name
                name_match = re.search(r'name="([^"]+)"', part)
                if name_match:
                    name = name_match.group(1)
                    if name == 'newfile' or name == 'Filedata[]' or name == 'm1_files[]':
                        # 提取 filename
                        filename_match = re.search(r'filename="([^"]+)"', part)
                        if filename_match:
                            params['filename'] = filename_match.group(1)
                    else:
                        # 提取对应的值
                        value_match = re.search(r'\.\.\.\.(.*?)\.\.', part, re.DOTALL)
                        if value_match:
                            value = value_match.group(1).strip()
                            params[name] = value

    for key, value in body_json.items():  
        params[key] = str(value)  
    
    # 解析www-form-urlencoded
    if 'application/x-www-form-urlencoded' in request_info:
        formdata = lines[-1]
        formdata = formdata.split('&')
        for item in formdata:
            key, value = item.split('=')
            # 对key和value进行URL解码
            key = unquote(key)
            value = unquote(value)
            params[key] = value

    if 'xml' in request_info:
        params['xml'] = lines[-1]

    if not ret_id:
        return {  
            "verb": method,  
            "uri": uri,  
            "bytes_sent": len(request_info),  
            "num_params": len(params),  
            "params": params  
        }
    
    return {
        "verb": method,  
        "uri": uri,  
        "bytes_sent": len(request_info),  
        "num_params": len(params),  
        "params": params,
        "req_id": req_id
    }


def parse_sql_statements(statements: list[str], is_match=True):
    db_statements = []
    def convert_ascii_sql_logs(logs: list[str]) -> list[str]:
        result = []
        for line in logs:
            # 替换 .. 为换行，再压缩为空格
            sql = line.replace("..", " ")
            sql = ' '.join(sql.split())  # 去掉多余空格
            sql = sql.strip(" .")
            if not sql.endswith(";"):
                sql += ";"
            result.append(sql)
        return result
    statements = convert_ascii_sql_logs(statements)
    for stmt in statements:  
        # 识别SQL类型
        stmt = stmt.replace("`", '"')
        db_statement = {}
        if stmt.startswith("SELECT"):  
            sql_type = "SELECT"   
            select_match = re.match(r'SELECT\s+(.+)\s+FROM\s+"?([\w\.]+)"?\.?(\s+WHERE\s+(.+))?\.?', stmt, re.DOTALL)  
            
            if select_match:
                table = select_match.group(2)  
                columns_dict = {}  
                
                # 如果有 WHERE 子句  
                if select_match.group(3):  
                    where_clause = select_match.group(4)  
                    where_match = re.search(r'"?(\w+)"?\s*=\s*(\d+)', where_clause)  
                    if where_match:  
                        columns_dict[where_match.group(1)] = where_match.group(2)  
                
                db_statement = {  
                    "type": sql_type,  
                    "table": table,  
                    "columns": columns_dict,  
                    "is_match": is_match  
                }  
            else:  
                continue
        elif stmt.startswith("INSERT"):  
            sql_type = "INSERT"  
            # 匹配 INSERT 语句  
            insert_match = re.match(r'INSERT\s+INTO\s+"?([\w\.]+)"?\s*\(([^)]+)\)\s*VALUES\s*\((.+)\)\.?', stmt, re.DOTALL)  
            if insert_match:  
                table = insert_match.group(1)  
                def smart_sql_value_split(value_str):
                    values = []
                    current = ''
                    in_string = False

                    for char in value_str.strip():  # 去掉最外层圆括号
                        if char == "'":
                            in_string = not in_string
                            # current += char
                        elif char == ',' and not in_string:
                            # 字符串外的逗号，断开
                            values.append(current.strip().split("::")[0])
                            current = ''
                        else:
                            current += char

                    if current:
                        values.append(current.strip().split("::")[0])

                    return values
                column_names = [col.strip().replace('"', '') for col in insert_match.group(2).split(',')]  
                column_values = smart_sql_value_split(insert_match.group(3))
                # column_values = [val.strip().strip("'").split("::")[0].strip("'") for val in insert_match.group(3).split(',')]  
                columns_dict = dict(zip(column_names, column_values))  
                
                db_statement = {  
                    "type": sql_type,  
                    "table": table,  
                    "columns": columns_dict,  
                    "is_match": is_match
                }  
            
        elif stmt.startswith("UPDATE"):  
            sql_type = "UPDATE"  
            # 匹配 UPDATE 语句  
            update_match = re.match(r'UPDATE\s+"?([\w\.]+)"?\s+SET\s+(.+)\s+WHERE\s+(.+)\.?', stmt, re.DOTALL)  
            if update_match:  
                table = update_match.group(1)  
                
                # 解析 SET 子句
                set_clauses = re.findall(r'"?(\w+)"?\s*=\s*[\'"]?([^\']+)[\'"]?,', update_match.group(2).split("::")[0].strip() + ',')  
                set_dict = dict(set_clauses)
                # print(set_dict)
                
                # 解析 WHERE 子句  
                where_match = re.findall(r'"?(\w+)"?\s*=\s*\'?(\w+)\'?', update_match.group(3))  
                if where_match:
                    # set_dict[where_match[0]] = where_match[1]
                    for key, value in where_match:
                        if key in set_dict:
                            set_dict.pop(key)
                            continue
                        set_dict[key] = value

                set_dict = {key.strip(): value.strip() for key, value in set_dict.items()}
                
                db_statement = {  
                    "type": sql_type,  
                    "table": table,  
                    "columns": set_dict,  
                    "is_match": is_match
                }  
            
        elif stmt.startswith("DELETE"):  
            sql_type = "DELETE"  
            # 匹配 DELETE 语句  
            delete_match = re.match(r'DELETE\s+FROM\s+"?([\w\.]+)"?\s+WHERE\s+(.+)\.?', stmt, re.DOTALL)  
            if delete_match:  
                table = delete_match.group(1)  
                where_clause = delete_match.group(2)  
                columns_dict = {}
                
                # 处理 IN 子句  
                in_match = re.search(r'"?(\w+)"?\s+IN\s*\(([^)]+)\)', where_clause)
                if in_match:
                    columns_dict = {  
                        in_match.group(1): in_match.group(2).strip()  
                    }
                # columns_dict = {  
                #     in_match.group(1) if in_match else 'unknown':   
                #     in_match.group(2).strip() if in_match else 'unknown'  
                # }  

                # 处理其他条件
                other_match = re.findall(r'"?(\w+)"?\s*=\s*\'?([\w]+)\'?', where_clause)
                for single_match in other_match:
                    columns_dict[single_match[0]] = single_match[1]

                
                db_statement = {  
                    "type": sql_type,  
                    "table": table,  
                    "columns": columns_dict,  
                    "is_match": is_match
                }  
        
        else:  
            # 未识别的语句类型  
            db_statement = {  
                "type": "UNKNOWN",  
                "table": "unknown",  
                "columns": {},  
                "is_match": is_match
            }  
            # continue
        # print(stmt)
        db_statements.append(db_statement) if db_statement else None  
    
    return db_statements


def generate_db_training_data():
    with open("./db_results.json", "r") as f:
        db_data:dict = json.load(f)
    parsed_data = []
    print(len(db_data))
    for key, value in db_data.items():
        # print(value)
        parsed_http = parse_request_info(value["request_info"], ret_id=True)
        if parsed_http["req_id"] is None:
            # print(f"request_id not found: {key}")
            continue
        parsed_http.pop("req_id")
        parsed_sql = parse_sql_statements(value["statement"], is_match=True)
        # 在data中随机选一个不同于当前的request_id
        random_key = key
        num = len(parsed_sql)
        if num == 0:
            # print(f"sql not found: {key}")
            continue
        while len(parsed_sql) != 2 * num:
            random_key = random.choice(list(db_data.keys()))
            while random_key == key or parse_request_info(db_data[random_key]["request_info"])["uri"] == parsed_http["uri"]:
                random_key = random.choice(list(db_data.keys()))
            parsed_sql2 = parse_sql_statements(db_data[random_key]["statement"], is_match=False)
            parsed_sql = parsed_sql + parsed_sql2
            if len(parsed_sql) >= 2 * num:
                parsed_sql = parsed_sql[:2 * num]

        parsed_data.append({  
            "http_request": parsed_http,
            "db_statements": parsed_sql,
            "fs_operations": [
                {
                    "operation": "test",
                    "source_path": "test",
                    "destination_path": None,
                    "is_directory": True,
                    "is_match": True
                }
            ]
        })
    print(len(parsed_data))
    # 将解析后的数据保存为JSON文件
    with open("./webfix-matchare/data/training_data.json", "w") as f:
        json.dump(parsed_data, f, indent=2)


def generate_fs_training_data():
    with open("./matchare_res.json", "r") as f:
        fs_data:dict = json.load(f)
    with open("./req_info.json", "r") as f:
        req_data:dict = json.load(f)
    parsed_data = []
    print(len(fs_data))

    for key, value in fs_data.items():
        if key not in req_data:
            continue
        parsed_http = parse_request_info(req_data[key], ret_id=True)
        if len(value) == 0:
            continue
        if parsed_http["req_id"] is None:
            print(f"request_id not found: {key}")
            continue
        parsed_http.pop("req_id")

        fs_operations = copy.deepcopy(value)
        for fs_operation in fs_operations:
            fs_operation["is_match"] = True
        
        radom_key = key
        num = len(fs_operations)
        if num == 0:
            print(f"fs_operations not found: {key}")
            continue
        while len(fs_operations) != 2 * num:
            radom_key = random.choice(list(fs_data.keys()))
            while radom_key == key or (parse_request_info(req_data[radom_key])["uri"] == parsed_http["uri"] and parse_request_info(req_data[radom_key])["num_params"] == parsed_http["num_params"]) \
                                   or parse_request_info(req_data[radom_key], ret_id=True)["req_id"] is None:
                radom_key = random.choice(list(fs_data.keys()))
            if radom_key not in req_data:
                continue
            fs_operations2 = copy.deepcopy(fs_data[radom_key])
            for fs_operation in fs_operations2:
                for fs in fs_operations:
                    if check_fs_operation(fs_operation, fs):
                        # print(f"fs_operation match: {fs_operation} vs {fs}")
                        fs_operations2.remove(fs_operation)
                        break
            for fs_operation in fs_operations2:
                fs_operation["is_match"] = False
            
            fs_operations += fs_operations2
            if len(fs_operations) >= 2 * num:
                fs_operations = fs_operations[:2 * num]

        # while radom_key == key or len(fs_data[radom_key]) != len(value):
        #     radom_key = random.choice(list(fs_data.keys()))
        # fs_operations2 = copy.deepcopy(fs_data[radom_key])
        # for fs_operation in fs_operations2:
        #     fs_operation["is_match"] = False
        # fs_operations += fs_operations2
        parsed_data.append({  
            "http_request": parsed_http,
            "db_statements": [
                {
                    "type": "test",
                    "table": "test",
                    "columns": {},
                    "is_match": True
                }
            ],
            "fs_operations": fs_operations
        })
    print(len(parsed_data))
    # 将解析后的数据保存为JSON文件
    with open("./webfix-matchare/data/training_data.json", "w") as f:
        json.dump(parsed_data, f, indent=2)


if __name__ == "__main__":
    generate_db_training_data()
    # generate_fs_training_data()