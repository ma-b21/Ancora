## 依赖安装

在仓库目录下运行`pipenv install`来安装依赖项。

## 新场景基础

1. 记目标场景为`env`（如`CVE-2015-8562`），在项目目录下创建`env`文件夹，并将vulhub对应文件夹复制到`env`目录下
2. 创建`env/request_api.py`文件，在其中**编写数据库与文件操作业务流量生成逻辑**
3. 从`CVE-2021-26120`复制`db`、`fs`两个目录到`env`目录下
4. 在`db`目录下，**修改`analyze.py:extract_request_syscalls`函数**来对系统调用进行单元分割，若**数据库类型或版本更改**，需要对应**修改`analyze.py:analyze_mysql_data`和`analyze.py:extract_tuple_for_single_request`**,该文件输出为`db_results.json`(用于验证准确率)、`matched_data.jsonl`(用于进行恢复)
5. 在`fs`目录下，**修改`analyze.py:analyze_single_process_data`**来对系统调用进行单元分割。该文件输出为`fs_results.json`(用于恢复)、`matchare_res.json`(用于验证准确率)、`req_info.json`(请求ID与请求体映射)

## 基本流程

1. 工作目录为`start_request.py`所在目录
2. 在`./{env}/{env}`目录下`docker compose up`启动场景
3. `sudo sysdig -s 10000 -w ./capture/capture_dir/capture.scap`
4. 在`start_request.py`中指定`env`和`HOST`，以及并发数和时间，生成流量（可以在登录逻辑之类完成之后再启动sysdig，减少干扰）
5. 停止sysdig，`python ./capture/load_logs.py`，生成`./capture/capture.jsonl`
6. 开始分析，`python ./{env}/{db/fs}/analyze.py`

## 数据库

### 恢复验证

- 在启动场景后，先配置`./{env}/db/config.py`
- 启动数据库备份：`python ./{env}/db/db_backup.py`
- 停止sysdig之后停止备份程序，之后`python ./{env}/db/analyze.py`
- 在得到的`db_results.json`中挑选一个请求ID，输入`./{env}/db/restore_db.py`中并运行，观察数据库状态是否符合预期，恢复了该请求执行的操作。
- 数据库类型更改时·`./{env}/db/db_backup.py`与`./{env}/db/restore_db.py`需对应修改。

### 准确率对比验证

先根据正常流程低并发得到一组结果，并根据该结果在`./{env}/request_api.py`中写入标准答案（参考`CVE-2021-26120/request_api.py`）

#### Matchare

- **训练阶段：**
  - 根据正常流程得到一组`db_results.json`作为训练样本，`python ./utils/generate_training_data.py`（需要修改代码确认为数据库训练数据）在`./webfix-matchare/data/`下生成`training_data.json`作为格式化模型训练数据。
  - 工作目录为`./webfix-matchare`，训练模型 `python train.py --model-type db --epochs 50 --batch-size 32 --lr 0.01`。
- **推理验证阶段：**
  - 运行`start_request.py`得到标准答案
  - 获取数据库应用日志，并在`./utils/generate_verify_data.py`中配置路径，其中`get_db_logs`需要随数据库版本、类型不同更改，得到需要的返回值
  - 运行`python ./utils/generate_verify_data.py`，得到`./webfix-matchare/data/verify_data.json`.
  - 在`./webfix-matchare/`下运行`python verify.py --type db`，得到预测结果`./webfix-matchare/predictions.json`
  - 配置`./utils/calculate_accuracy.py`，设置`env`、`answer_type=db`.
  - 在项目目录下运行`python ./utils/calculate_accuracy.py`，得到准确率。

#### WebFix

- 正常流程得到`db_results.json`
- `python ./utils/generate_webfix_predictions.py`(需要改代码确认为数据库)
- 配置`./utils/calculate_accuracy.py`，设置`env`、`answer_type=db`.
- 在项目目录下运行`python ./utils/calculate_accuracy.py`，得到准确率。

## 文件操作

### 恢复验证

- 在启动场景后，先配置`./{env}/fs/config.py`
- 启动数据库备份：`python ./{env}/fs/watch.py`
- 停止sysdig之后停止备份程序，之后`python ./{env}/fs/analyze.py`
- 在得到的`fs_results.json`中挑选一个请求ID，输入`./{env}/fs/restore_fs.py`中并运行，观察文件状态是否符合预期，恢复了该请求执行的操作。

### 准确率对比验证

先根据正常流程低并发得到一组结果，并根据该结果在`./{env}/request_api.py`中写入标准答案（参考`CVE-2021-26120/request_api.py`）

#### Matchare

- **训练阶段：**
  - 根据正常流程得到一组`matchare_res.json`和`req_info.json`作为训练样本，`python ./utils/generate_training_data.py`（需要修改代码确认为文件操作训练数据）在`./webfix-matchare/data/`下生成`training_data.json`作为格式化模型训练数据。
  - 工作目录为`./webfix-matchare`，训练模型 `python train.py --model-type fs --epochs 50 --batch-size 32 --lr 0.01`。
- **推理验证阶段：**
  - 需要将数据目录映射出来，并修改权限确保watchdog能访问（参考`CVE-2021-26120`）
  - 运行基本流程前配置并运行`python ./utils/watch_for_fs_verify.py`(配置`env`和`volumn_map`)
  - 运行`start_request.py`得到标准答案
  - 结束`./utils/watch_for_fs_verify.py`得到文件日志，在`./utils/generate_verify_data.py`中配置路径
  - 运行`python ./utils/generate_verify_data.py`，得到`./webfix-matchare/data/verify_data.json`.
  - 在`./webfix-matchare/`下运行`python verify.py --type fs`，得到预测结果`./webfix-matchare/predictions.json`
  - 配置`./utils/calculate_accuracy.py`，设置`env`、`answer_type=fs`.
  - 在项目目录下运行`python ./utils/calculate_accuracy.py`，得到准确率。

#### WebFix

- 正常流程得到`matchare_res.json`和`req_info.json`
- `python ./utils/generate_webfix_predictions.py`(需要改代码确认为文件)
- 配置`./utils/calculate_accuracy.py`，设置`env`、`answer_type=fs`.
- 在项目目录下运行`python ./utils/calculate_accuracy.py`，得到准确率。