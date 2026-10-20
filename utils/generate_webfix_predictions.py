import json
from generate_training_data import parse_sql_statements, parse_request_info


def generate_db_predictions():
    with open("./db_results.json", "r") as f:
        db_data:dict = json.load(f)

    parsed_data = {}
    print(len(db_data))
    for key, value in db_data.items():
        parsed_http = parse_request_info(value["request_info"], ret_id=True)
        parsed_sql = parse_sql_statements(value["statement"], is_match=True)
       
        parsed_data[parsed_http["req_id"]] = {  
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
        }
    print(len(parsed_data))
    # 将解析后的数据保存为JSON文件
    with open("./webfix-matchare/predictions.json", "w") as f:
        json.dump(parsed_data, f, indent=2)
    print("DB predictions generated successfully, saved in webfix_predictions.json")


def generate_fs_predictions():
    with open("./matchare_res.json", "r") as f:
        fs_data:dict = json.load(f)
    with open("./req_info.json", "r") as f:
        req_info:dict = json.load(f)

    parsed_data = {}
    print(len(fs_data))
    for key, value in fs_data.items():
        if key not in req_info:
            print(f"Key {key} not found in req_info")
            continue
        parsed_http = parse_request_info(req_info[key], ret_id=True)
       
        parsed_data[parsed_http["req_id"]] = {  
            "http_request": parsed_http,
            "db_statements": [],
            "fs_operations": value
        }
    print(len(parsed_data))
    # 将解析后的数据保存为JSON文件
    with open("./webfix-matchare/predictions.json", "w") as f:
        json.dump(parsed_data, f, indent=2)
    print("FS predictions generated successfully, saved in webfix_predictions.json")


if __name__ == "__main__":
    generate_db_predictions()
    # generate_fs_predictions()