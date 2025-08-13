import datetime
import json
import os
import random
import string
import uuid

from config import RANDOM_SEED
from utils.seed import set_all_seeds


def random_string(length=8):
    """生成随机字符串"""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def random_path():
    """生成随机文件路径"""
    dirs = [
        "documents",
        "images",
        "videos",
        "projects",
        "users",
        "system",
        "temp",
        "logs",
    ]
    depth = random.randint(1, 3)
    path_parts = [random.choice(dirs)]

    for _ in range(depth):
        path_parts.append(random_string(5))

    filename = (
        f"{random_string(8)}.{random.choice(['txt', 'jpg', 'pdf', 'doc', 'html'])}"
    )
    path_parts.append(filename)

    return "/" + "/".join(path_parts)


def generate_http_request():
    """生成 HTTP 请求"""
    verbs = [
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTION",
        "PATCH",
        "HEAD",
    ]
    endpoints = [
        "/api/users",
        "/api/documents",
        "/api/projects",
        "/api/files",
        "/api/search",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/settings",
        "/api/comments",
    ]

    verb = random.choice(verbs)
    uri = random.choice(endpoints)

    # 生成参数
    num_params = random.randint(1, 5)
    params = {}

    # 确保至少有一个 ID 参数，这将用于匹配
    params["id"] = str(uuid.uuid4())[:8]

    # 添加其他随机参数
    param_names = [
        "name",
        "title",
        "description",
        "status",
        "type",
        "category",
        "tags",
        "author",
        "date",
        "query",
    ]
    for _ in range(num_params - 1):
        param_name = random.choice(param_names)
        if param_name not in params:  # 避免重复参数
            if param_name in ["name", "title", "author"]:
                params[param_name] = random_string(8).capitalize()
            elif param_name == "description":
                params[param_name] = (
                    f"This is a {random_string(5)} description for {random_string(4)}"
                )
            elif param_name == "status":
                params[param_name] = random.choice(
                    ["active", "inactive", "pending", "deleted"]
                )
            elif param_name == "type":
                params[param_name] = random.choice(
                    ["document", "image", "video", "project"]
                )
            elif param_name == "category":
                params[param_name] = random.choice(
                    ["work", "personal", "shared", "archived"]
                )
            elif param_name == "tags":
                tags = [random_string(4) for _ in range(random.randint(1, 3))]
                params[param_name] = ",".join(tags)
            elif param_name == "date":
                date = datetime.datetime.now() - datetime.timedelta(
                    days=random.randint(0, 365)
                )
                params[param_name] = date.strftime("%Y-%m-%d")
            elif param_name == "query":
                params[param_name] = random_string(6)

    # 计算请求大小（简化模拟）
    bytes_sent = (
        len(json.dumps(params)) + len(uri) + len(verb) + random.randint(50, 200)
    )

    return {
        "verb": verb,
        "uri": uri,
        "bytes_sent": bytes_sent,
        "num_params": len(params),
        "params": params,
    }


def generate_db_statement(http_request, is_match=True):
    """生成数据库语句"""
    db_types = ["INSERT", "SELECT", "UPDATE", "DELETE"]
    tables = [
        "users",
        "documents",
        "projects",
        "files",
        "comments",
        "settings",
        "logs",
        "sessions",
    ]

    # 根据 HTTP 请求的 URI 选择表
    uri = http_request["uri"]
    if "/users" in uri:
        table = "users"
    elif "/documents" in uri:
        table = "documents"
    elif "/projects" in uri:
        table = "projects"
    elif "/files" in uri:
        table = "files"
    elif "/comments" in uri:
        table = "comments"
    elif "/settings" in uri:
        table = "settings"
    elif "/auth" in uri:
        table = "sessions"
    else:
        table = random.choice(tables)

    # 根据 HTTP 请求的动词选择数据库操作类型
    verb = http_request["verb"]
    if verb == "GET":
        db_type = "SELECT"
    elif verb == "POST":
        db_type = "INSERT"
    elif verb == "PUT":
        db_type = "UPDATE"
    elif verb == "DELETE":
        db_type = "DELETE"
    else:
        db_type = random.choice(db_types)

    # 生成列
    columns = {}

    # 如果是匹配的数据库语句，确保有一个参数与 HTTP 请求匹配
    if is_match:
        # 选择一个 HTTP 参数进行匹配
        match_param = "id"  # 默认使用 id 参数
        if match_param in http_request["params"]:
            columns[match_param] = http_request["params"][match_param]
        else:
            # 如果没有 id 参数，随机选择一个参数
            param_name, param_value = random.choice(
                list(http_request["params"].items())
            )
            columns[param_name] = param_value

    # 添加其他列
    column_names = [
        "id",
        "name",
        "title",
        "description",
        "status",
        "type",
        "category",
        "created_at",
        "updated_at",
        "user_id",
        "content",
    ]
    num_columns = random.randint(3, 8)

    for _ in range(num_columns):
        column_name = random.choice(column_names)
        if column_name not in columns:  # 避免重复列
            if column_name == "id" and column_name not in columns:
                columns[column_name] = str(uuid.uuid4())[:8]
            elif column_name in ["name", "title"]:
                columns[column_name] = random_string(8).capitalize()
            elif column_name == "description":
                columns[column_name] = f"This is a {random_string(5)} description"
            elif column_name == "status":
                columns[column_name] = random.choice(
                    ["active", "inactive", "pending", "deleted"]
                )
            elif column_name == "type":
                columns[column_name] = random.choice(
                    ["document", "image", "video", "project"]
                )
            elif column_name == "category":
                columns[column_name] = random.choice(
                    ["work", "personal", "shared", "archived"]
                )
            elif column_name in ["created_at", "updated_at"]:
                date = datetime.datetime.now() - datetime.timedelta(
                    days=random.randint(0, 365)
                )
                columns[column_name] = date.strftime("%Y-%m-%d %H:%M:%S")
            elif column_name == "user_id":
                columns[column_name] = str(uuid.uuid4())[:8]
            elif column_name == "content":
                columns[column_name] = f"Content for {random_string(8)}"

    return {"type": db_type, "table": table, "columns": columns, "is_match": is_match}


def generate_fs_operation(http_request, is_match=True):
    """生成文件系统操作"""
    operations = ["create", "read", "update", "delete", "copy", "move"]

    # 根据 HTTP 请求的动词选择文件系统操作
    verb = http_request["verb"]
    if verb == "GET":
        operation = "read"
    elif verb == "POST":
        operation = "create"
    elif verb == "PUT":
        operation = "update"
    elif verb == "DELETE":
        operation = "delete"
    elif verb == "OPTION":
        operation = "copy"
    elif verb == "PATCH":
        operation = "move"
    else:
        operation = random.choice(operations)

    # 生成路径
    source_path = random_path()

    # 如果是匹配的文件系统操作，确保路径中包含 HTTP 请求的某个参数
    if is_match:
        # 选择一个 HTTP 参数进行匹配
        match_param = "id"  # 默认使用 id 参数
        if match_param in http_request["params"]:
            # 在路径中添加匹配的参数
            param_value = http_request["params"][match_param]
            parts = source_path.split("/")
            parts[-1] = f"{param_value}_{parts[-1]}"
            source_path = "/".join(parts)

    # 对于复制和移动操作，需要目标路径
    destination_path = None
    if operation in ["copy", "move"]:
        destination_path = random_path()

    # 随机决定是文件还是目录
    is_directory = random.random() < 0.2  # 20% 的概率是目录

    return {
        "operation": operation,
        "source_path": source_path,
        "destination_path": destination_path,
        "is_directory": is_directory,
        "is_match": is_match,
    }


def generate_sample_data(num_samples=100):
    """生成样本数据"""
    samples = []

    for _ in range(num_samples):
        # 生成 HTTP 请求
        http_request = generate_http_request()

        # 为每个 HTTP 请求生成匹配的数据库语句和文件系统操作
        num_db_matches = random.randint(1, 3)
        num_fs_matches = random.randint(1, 3)

        db_statements = []
        fs_operations = []

        # 生成匹配的数据库语句
        for _ in range(num_db_matches):
            db_statements.append(generate_db_statement(http_request, is_match=True))

        # 生成匹配的文件系统操作
        for _ in range(num_fs_matches):
            fs_operations.append(generate_fs_operation(http_request, is_match=True))

        # 生成不匹配的数据库语句（数量与匹配的相同）
        for _ in range(num_db_matches):
            db_statements.append(generate_db_statement(http_request, is_match=False))

        # 生成不匹配的文件系统操作（数量与匹配的相同）
        for _ in range(num_fs_matches):
            fs_operations.append(generate_fs_operation(http_request, is_match=False))

        # 添加到样本列表
        samples.append(
            {
                "http_request": http_request,
                "db_statements": db_statements,
                "fs_operations": fs_operations,
            }
        )

    return samples


def save_samples(samples, output_file):
    """保存样本到文件"""
    # 确保目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(samples, f, indent=2)

    print(f"已保存 {len(samples)} 个样本到 {output_file}")


if __name__ == "__main__":
    # 设置种子
    set_all_seeds(RANDOM_SEED)

    # 生成 100 个样本
    samples = generate_sample_data(100)

    # 保存到文件
    save_samples(samples, "data/samples.json")
