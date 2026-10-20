import subprocess
import os

env = "CVE-2021-26120" # 环境名称

user_count = 30 # 用户数
HOST = "http://localhost" # 服务地址
run_time = 60 # seconds
request_api_path = f"{os.path.dirname(__file__)}/{env}/request_api.py" # 请求脚本路径
def start_request():
    try:
        res = subprocess.run(
            [
                "locust",
                "--headless",
                "-f",
                request_api_path,
                "-H",
                HOST,
                "-u",
                str(user_count),
                "-r",
                str(user_count),
                "--run-time",
                f"{run_time}s",
                "--stop-timeout",
                "60",
            ],
            # capture_output=True,
            check=False,
        )
    except KeyboardInterrupt:
        print("Process interrupted by user.")
    # os.system(f"locust --headless -f {request_api_path} --host={HOST} -u {user_count} -r {user_count} --run-time {run_time}s --stop-timeout 30")


if __name__ == "__main__":
    start_request()