# generate verify data for matchare

from generate_training_data import parse_sql_statements
import pandas as pd
import json
import os
import re
from datetime import datetime, timezone

db_log_path = "CVE-2021-26120/CVE-2021-26120/logs/mysql.log"
http_log_path = "CVE-2021-26120/answers.json"
fs_log_path = "CVE-2021-26120/file_ops.json"

def get_db_logs():
    if not os.path.exists(db_log_path):
        db_logs = None
    else:
        with open(db_log_path, "r") as f:
            db_logs = f.read().split("autovacuum launcher started\n")[-1].split("\n")
        db_logs = [log.strip() for log in db_logs] # 此处log为 timestamp + sql语句
    
    def trans_log(log: str, separator: str="statement: ") -> dict:
        """
        将数据库日志转换为字典格式
        """
        timestamp = float(log.split(" ")[0])
        sql_statement = [f"{stmt};" for stmt in log.split(separator)[1].strip().split("--")[0].strip().split(";") if "SELECT" not in stmt]

        # 解析SQL语句
        db_statements = parse_sql_statements(sql_statement, is_match=True)
        return {
            "timestamp": timestamp,
            "db_statements": db_statements[0]
        }
    if db_logs:
        # # For CVE-2024-38856
        # for i in range(len(db_logs) - 1, -1, -1):
        #     if "DETAIL:  parameters:" in db_logs[i]:
        #         params = [p.split("=") for p in db_logs[i].split("DETAIL:  parameters: ")[1].strip(" .").split(", $")]
        #         print(f"params: {params}")
        #         params = {'$' + k.strip('$ '): v.strip() for k, v in params}
        #         for key, value in reversed(params.items()):
        #             db_logs[i - 1] = db_logs[i - 1].replace(key, value)
        #         db_logs.pop(i)
        # for i in range(len(db_logs)):
        #     db_logs[i] = re.sub(r"execute .*?:", "statement:", db_logs[i])
        
        # # For CVE-2023-25157
        # for i in range(len(db_logs) - 1, -1, -1):
        #     if db_logs[i] == "RETURNING *":
        #         db_logs[i - 1] += db_logs[i]
        #         db_logs.pop(i)
        # for i in range(len(db_logs)):
        #     db_logs[i] = re.sub(r"execute .*?:", "statement:", db_logs[i])

        # # For CVE-2022-4223
        # for i in range(len(db_logs) - 1, -1, -1):
        #     if not "LOG:  statement:" in db_logs[i]:
        #         db_logs[i - 1] += " "
        #         db_logs[i - 1] += db_logs[i]
        #         db_logs.pop(i)

        # # For CVE-None-self_made_fastapi
        # for i in range(len(db_logs) - 1, -1, -1):
        #     if "DETAIL:  Parameters:" in db_logs[i]:
        #         params = [p.split("=") for p in db_logs[i].split("DETAIL:  Parameters: ")[1].strip(" .").split(", $")]
        #         print(f"params: {params}")
        #         params = {'$' + k.strip('$ '): v.strip() for k, v in params}
        #         for key, value in reversed(params.items()):
        #             db_logs[i - 1] = db_logs[i - 1].replace(key, value)
        #         db_logs.pop(i)
        # for i in range(len(db_logs)):
        #     db_logs[i] = re.sub(r"execute .*?:", "statement:", db_logs[i])
        for log in db_logs:
            print(log)
        db_logs = [trans_log(log, "statement: ") for log in db_logs if "LOG: " in log]
        db_logs = pd.DataFrame(db_logs)
        
    return db_logs

def get_mysql_logs():
    def parse_mysql_log_to_timestamp_float(log_content: str):
        result = {}
        current_ts = None
        current_sql = []

        # 正则匹配形如 2025-07-20T04:53:16.132844Z 的时间戳行
        pattern = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+\d+\s+Query\s+(.*)?")

        for line in log_content.splitlines():
            match = pattern.match(line)
            if match:
                # 如果已经缓存了之前的语句，就保存它
                if current_ts is not None and current_sql:
                    joined_sql = " ".join(current_sql).strip()
                    result[current_ts] = re.sub(r"\s+", " ", joined_sql)

                # 提取并转换时间戳为 float
                timestamp_str = match.group(1)  # 带Z的 ISO 格式
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                timestamp_float = dt.timestamp()  # 转为 float

                current_ts = timestamp_float
                sql_part = match.group(2) or ""
                current_sql = [sql_part]
            else:
                if re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z", line):
                    continue
                # 补充 SQL 后续行
                if current_sql is not None:
                    current_sql.append(line.strip())

        # 处理最后一条记录
        if current_ts is not None and current_sql:
            joined_sql = " ".join(current_sql).strip()
            result[current_ts] = re.sub(r"\s+", " ", joined_sql)

        return result

    if not os.path.exists(db_log_path):
        db_logs = None
    else:
        with open(db_log_path, "r") as f:
            db_logs = f.read()
        
        db_logs = parse_mysql_log_to_timestamp_float(db_logs.replace("`", ""))
        db_logs = [f"{key} statement: {value}" for key,value in db_logs.items() if value.startswith(("INSERT", "UPDATE", "DELETE"))]
        # print(db_logs)
        # db_logs = [log.strip() for log in db_logs] # 此处log为 timestamp + sql语句
    
    # For CVE-2021-26120
    def statement_filter(statement: str):
        tables = statement.split(" ")
        if "cms_adminlog" in tables:
            return True
        if "cms_locks" in tables:
            return True
        if "cms_content_props" in tables:
            if not "content_en" in statement:
                return False
            return True
        if "cms_layout_templates" in tables:
            if not "name" in statement:
                return False
            return True
        if "cms_content" not in tables:
            return False
        if statement.startswith("UPDATE"):
            if "content_name" not in statement:
                return False
        return True
    # # For CVE-2015-8562
    # def statement_filter(statement: str):
    #     tables = statement.split(" ")
    #     if "j_contentitem_tag_map" in tables:
    #         return True
    #     if "j_ucm_history" in tables:
    #         if "INSERT" in statement:
    #             return False
    #         return True
    #     if "j_content" in tables:
    #         if "SET ordering" in statement or "asset_id" in statement:
    #             return False
    #         return True
    #     return False

    def trans_log(log: str, separator: str="statement: ") -> dict:
        """
        将数据库日志转换为字典格式
        """
        timestamp = float(log.split(" ")[0])
        sql_statement = [log.split(separator)[1].strip()]
        if not statement_filter(sql_statement[0]):
            return None

        # 解析SQL语句
        db_statements = parse_sql_statements(sql_statement, is_match=True)
        if db_statements:
            return {
                "timestamp": timestamp,
                "db_statements": db_statements[0]
            }
        else:
            return None
    if db_logs:
        
        for log in db_logs:
            if "function" in log:
                print(log)
        db_logs = [trans_log(log.replace("\\'", ""), "statement: ") for log in db_logs if trans_log(log, "statement: ") is not None]
        db_logs = pd.DataFrame(db_logs)
        print(db_logs)
        
    return db_logs

db_logs = get_db_logs() if "mysql" not in db_log_path else get_mysql_logs()

with open(http_log_path, "r") as f:
    http_logs = json.load(f)

def get_fs_logs():
    if not os.path.exists(fs_log_path):
        fs_logs = None
    else:
        with open(fs_log_path, "r") as f:
            fs_logs = json.load(f)
    if fs_logs:
        fs_logs = pd.DataFrame(fs_logs)
    return fs_logs
fs_logs = get_fs_logs()


def generate_verify_data():
    """
    生成验证数据
    """
    verify_data = {}
    for x_request_id, request in http_logs.items():
        if db_logs is not None:
            db_logs_in_window = db_logs[
                (db_logs["timestamp"] >= (request["request_time"] - 1.5)) &
                (db_logs["timestamp"] <= (request["request_time"] + 1.5))
            ]
        if fs_logs is not None:
            fs_logs_in_window = fs_logs[
                (fs_logs["timestamp"] >= (request["request_time"] - 1.5)) &
                (fs_logs["timestamp"] <= (request["request_time"] + 1.5))
            ]
            # print(fs_logs_in_window)
            # For CVE-2023-25157
            # fs_logs_in_window = fs_logs_in_window[fs_logs_in_window["info"].apply(lambda x: not "global.xml" in x["source_path"])]
        verify_data[x_request_id] = {
            "http_request": request["http_request"],
            "db_statements": db_logs_in_window["db_statements"].tolist() if db_logs is not None else [
                {
                    "type": "test",
                    "table": "test",
                    "columns": {},
                    "is_match": True
                }
            ],
            "fs_operations": fs_logs_in_window["info"].tolist() if fs_logs is not None else [
                {
                    "operation": "test",
                    "source_path": "test",
                    "destination_path": None,
                    "is_directory": True,
                    "is_match": True
                }
            ]
        }
    # 将验证数据保存为JSON文件
    with open("webfix-matchare/data/verify_data.json", "w") as f:
        json.dump(verify_data, f, indent=4)
    print("验证数据生成完毕，保存在verify_data.json文件中")


if __name__ == "__main__":
    generate_verify_data()
