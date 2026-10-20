import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import json


env = "CVE-2023-49070"
volumn_map = (
    "CVE-2023-49070/CVE-2023-49070/data", "/usr/src/apache-ofbiz/runtime/uploads"
)

log_file = f"{env}/file_ops.json"
logs = []
operation_dict = {
    "created": "create",
    "modified": "update",
    "moved": "move",
    "deleted": "delete",
}


class WatchdogHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        # 获取事件信息
        src_path = event.src_path
        dest_path = event.dest_path if event.dest_path else None  # 目标路径
        event_type = event.event_type  # 事件类型
        is_directory = event.is_directory  # 是否为目录

        if event_type == "opened" or event_type == "closed" or event_type == "closed_no_write":
            return
        if event_type == "modified" and is_directory:
            return

        logs.append(
            {
                "timestamp": time.time(),
                "info":
                    {
                        "operation": operation_dict.get(event_type, event_type),
                        "source_path": src_path.replace(volumn_map[0], volumn_map[1]),
                        "destination_path": dest_path.replace(volumn_map[0], volumn_map[1]) if dest_path else None,
                        "is_directory": is_directory,
                        "is_match": True
                    },
            }
        )
        print(logs[-1]["info"])

def main():
    src_dir = volumn_map[0]
    if not os.path.exists(src_dir):
        os.makedirs(src_dir)

    event_handler = WatchdogHandler()
    observer = Observer()
    observer.schedule(event_handler, path=src_dir, recursive=True)

    print(f"Monitoring directory: {src_dir}")
    try:
        observer.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

    with open(log_file, "w") as f:
        json.dump(logs, f, indent=4)

if __name__ == "__main__":
    main()