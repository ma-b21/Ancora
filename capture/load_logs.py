import gzip
import json
import multiprocessing
import os
import re

import msgpack
from loguru import logger
from tqdm import tqdm
import subprocess

fields = [
    "evt.num",
    "fs.path.name",
    "fs.path.source",
    "fs.path.target",
    "proc.name",
    "proc.vpid",
    # "proc.pid",
    "thread.tid",
    "thread.vtid",
    "thread.pvtid",
    "thread.cvtid",
    "proc.pvpid",
    "proc.cvpid",
    "evt.type",
    "evt.category",
    "evt.info",
    "evt.is_io_read",
    "evt.is_io_write",
    "evt.arg.data",
    "evt.dir",
    "evt.datetime",
    "fd.name",
    "fd.type",
    "fd.cip",
    "fd.cport",
    "fd.sip",
    "fd.sport",
]

subproc_dict = {}
subthread_dict = {}
tid_vtid_dict = {}
vtid_ptid_dict = {}

def exec_command(command: list[str], check=True):
    print(f"executing command: {command}")
    try:
        res = subprocess.run(command, check=check)
        logger.debug(f"Command {command} executed successfully")
        logger.debug(f"Output: {res.stdout}")
        logger.debug(f"Error: {res.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error: {e.stderr}")
        raise


CAPTURE_BASE_PATH = os.path.dirname(os.path.realpath(__file__))
CAPTURED_PATH = f"{CAPTURE_BASE_PATH}/capture_dir"
CAPTURED_DIVIDED_PATH = f"{CAPTURED_PATH}/divided"

is_sysdig_loaded = False

cpu_count_ = os.cpu_count()
if cpu_count_ is None:
    raise ValueError
cpu_count = int(cpu_count_)


def process_scap(idx: int):
    path = f"{CAPTURED_DIVIDED_PATH}/capture.scap{idx}"
    os.system(
        f"sysdig -r {path} -c {CAPTURE_BASE_PATH}/print_fields_new.lua | gzip > {CAPTURED_DIVIDED_PATH}/capture{idx}.gz"
    )
    # os.system(f"rm -f {path}")


def load_gz(idx: int):
    path = f"{CAPTURED_DIVIDED_PATH}/capture{idx}.gz"
    with gzip.open(path, "rb") as f:
        unpacker = msgpack.Unpacker(raw=False, strict_map_key=False)
        while True:
            data = f.read(50 * 1024 * 1024)
            print(f"read {len(data)} bytes")
            if not data:
                break
            unpacker.feed(data)
            for obj in unpacker:
                yield obj


def load_objs():
    idx = -1
    while True:
        idx += 1
        if not os.path.exists(f"{CAPTURED_DIVIDED_PATH}/capture{idx}.gz"):
            break

    evt_num = 0
    for idx_ in range(idx):
        gen = load_gz(idx_)
        field_names = next(gen)
        for obj_ in gen:
            if isinstance(obj_, list):
                obj = {field_names[i - 1]: obj_[i] for i in range(len(obj_))}
            else:
                obj = {field_names[i - 1]: obj_[i] for i in obj_.keys()}
                obj.update(
                    {key: None for key in field_names if key not in obj.keys()}
                )
            obj["evt.num"] = evt_num
            evt_num += 1
            yield obj


def load_sysdig():
    global is_sysdig_loaded

    if not is_sysdig_loaded:
        is_sysdig_loaded = True

        exec_command(["mkdir", "-p", CAPTURED_DIVIDED_PATH])
        files = os.listdir(CAPTURED_DIVIDED_PATH)
        for file in files:
            exec_command(["rm", "-f", f"{CAPTURED_DIVIDED_PATH}/{file}"])

        exec_command(
            [
                "sysdig",
                "-r",
                f"{CAPTURED_PATH}/capture.scap",
                "-P",
                "-C",
                "100MB",
                "-w",
                f"{CAPTURED_DIVIDED_PATH}/capture.scap",
            ]
        )

        idx = -1
        while True:
            idx += 1
            if not os.path.exists(f"{CAPTURED_DIVIDED_PATH}/capture.scap{idx}"):
                break

        for batch in tqdm(range(0, idx, cpu_count)):
            cur_batch = (batch, min(batch + cpu_count, idx))
            cur_processors: list[multiprocessing.Process] = []

            for i in range(*cur_batch):
                p = multiprocessing.Process(target=process_scap, args=(i,))
                cur_processors.append(p)
                p.start()

            for p in cur_processors:
                p.join()

    for obj in tqdm(load_objs()):
        try:
            obj["proc.cvpid"] = None
            obj["proc.vpid"] = str(obj["proc.vpid"])
            obj["proc.pvpid"] = str(obj["proc.pvpid"])

            obj["thread.vtid"] = str(obj["thread.vtid"])
            obj["thread.tid"] = str(obj["thread.tid"])
            obj["thread.cvtid"] = None
            obj["thread.pvtid"] = None
    
            if obj["evt.dir"] == ">":
                if obj["evt.type"] != "copy_file_range":
                    continue
            if obj["evt.type"] == "vfork" or obj["evt.type"] == "clone" or obj["evt.type"] == "clone3":
                if obj["evt.info"].startswith("res="):
                    res = re.search(r"res=(-?\d+)", obj["evt.info"]).group(1)
                    if int(res) < 0:
                        continue
                    elif int(res) == 0:
                        vtid = obj["thread.vtid"]
                        ptid = re.search(r"ptid=(\d+)", obj["evt.info"]).group(1)
                        if obj["evt.type"] == "vfork":
                            try:
                                subthread_dict[vtid] += 1
                                obj["thread.vtid"] = f"{vtid}.{subthread_dict[vtid]}"
                            except KeyError:
                                obj["thread.vtid"] = f"{vtid}.1"
                                subthread_dict[vtid] = 1
                            vtid_ptid_dict[obj["thread.vtid"]] = ptid
                        continue
                    else:
                        try:
                            subproc_dict[res] += 1
                            obj["proc.cvpid"] = f"{res}.{subproc_dict[res]}"
                        except KeyError:
                            obj["proc.cvpid"] = f"{res}.1"
                            subproc_dict[res] = 1
                        if obj["evt.type"] == "vfork":
                            obj["thread.cvtid"] = f"{res}.{subthread_dict[res]}"
                        else:
                            try:
                                subthread_dict[res] += 1
                                obj["thread.cvtid"] = f"{res}.{subthread_dict[res]}"
                            except KeyError:
                                obj["thread.cvtid"] = f"{res}.1"
                                subthread_dict[res] = 1
                            vtid_ptid_dict[obj["thread.cvtid"]] = obj["thread.tid"]
                else:
                    continue
            if obj["proc.vpid"] in subproc_dict:
                obj["proc.vpid"] = f"{obj['proc.vpid']}.{subproc_dict[obj['proc.vpid']]}"
            if obj["proc.pvpid"] in subproc_dict:
                obj["proc.pvpid"] = f"{obj['proc.pvpid']}.{subproc_dict[obj['proc.pvpid']]}"
            
            if obj["thread.vtid"] in subthread_dict:
                obj["thread.vtid"] = f"{obj['thread.vtid']}.{subthread_dict[obj['thread.vtid']]}"
            tid_vtid_dict[obj["thread.tid"]] = obj["thread.vtid"]

            if obj["thread.vtid"] in vtid_ptid_dict:
                obj["thread.pvtid"] = tid_vtid_dict[vtid_ptid_dict[obj["thread.vtid"]]]

            if obj["thread.pvtid"] in subthread_dict:
                obj["thread.pvtid"] = f"{obj['thread.pvtid']}.{subthread_dict[obj['thread.pvtid']]}"
            # print(json.dumps(vtid_ptid_dict, indent=4))

            obj["fs.path.name"] = obj["fs.path.name"] if "fs.path.name" in obj else None
            obj["fs.path.source"] = obj["fs.path.source"] if "fs.path.source" in obj else None
            obj["fs.path.target"] = obj["fs.path.target"] if "fs.path.target" in obj else None

            obj["fd.cport"] = str(int(obj["fd.cport"])) if obj["fd.cport"] is not None else None
            obj["fd.sport"] = str(int(obj["fd.sport"])) if obj["fd.sport"] is not None else None
            required_obj = {key: obj[key] for key in fields}
            yield required_obj
        except Exception as e:
            logger.exception(e)
            print(json.dumps(obj))
            raise


def main():
    with open("./capture/capture.jsonl", "w") as out:
        for line in load_sysdig():
            out.write(json.dumps(line) + "\n")

if __name__ == "__main__":
    main()
