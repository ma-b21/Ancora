# Ancora

Ancora is an intrusion recovery prototype for web applications. This repository
contains the experimental scenarios, syscall-log processing scripts, database
and filesystem recovery scripts, and accuracy-comparison utilities used in the
paper.

The original Chinese README has been preserved as `README_CN.md`.

## Dependency Installation

Install the Python dependencies from the repository root:

```bash
pipenv install
```

The experiments also require Docker, Docker Compose, and sysdig.

## Adding a New Scenario

Assume the target scenario is named `env`, for example `CVE-2015-8562`.

1. Create an `env` directory under the project root and copy the corresponding
   Vulhub scenario files into `env`.
2. Create `env/request_api.py` and implement the workload-generation logic for
   database and filesystem operations.
3. Copy the `db` and `fs` directories from `CVE-2021-26120` into `env`.
4. In the `db` directory, modify `analyze.py:extract_request_syscalls` to
   partition syscalls into request-level units. If the database type or version
   changes, also update `analyze.py:analyze_mysql_data` and
   `analyze.py:extract_tuple_for_single_request`. The script outputs
   `db_results.json` for accuracy validation and `matched_data.jsonl` for
   recovery.
5. In the `fs` directory, modify `analyze.py:analyze_single_process_data` to
   partition syscalls into request-level units. The script outputs
   `fs_results.json` for recovery, `matchare_res.json` for accuracy validation,
   and `req_info.json` for mapping request IDs to request bodies.

## Basic Workflow

1. Use the directory containing `start_request.py` as the working directory.
2. Start the target scenario under `./{env}/{env}`:

   ```bash
   docker compose up
   ```

3. Start syscall collection:

   ```bash
   sudo sysdig -s 10000 -w ./capture/capture_dir/capture.scap
   ```

4. Configure `env`, `HOST`, concurrency, and duration in `start_request.py`,
   then generate workload traffic. To reduce noise, sysdig can be started after
   login or other setup operations are completed.
5. Stop sysdig and convert the capture:

   ```bash
   python ./capture/load_logs.py
   ```

   This generates `./capture/capture.jsonl`.
6. Run database or filesystem analysis:

   ```bash
   python ./{env}/{db/fs}/analyze.py
   ```

## Database Recovery

### Recovery Validation

1. After starting the scenario, configure `./{env}/db/config.py`.
2. Start database backup:

   ```bash
   python ./{env}/db/db_backup.py
   ```

3. After sysdig stops, stop the backup program and run:

   ```bash
   python ./{env}/db/analyze.py
   ```

4. Select a request ID from `db_results.json`, provide it to
   `./{env}/db/restore_db.py`, and run the recovery script. Inspect the database
   state to verify that the operations caused by the selected request have been
   restored as expected.
5. If the database type changes, update `./{env}/db/db_backup.py` and
   `./{env}/db/restore_db.py` accordingly.

### Accuracy Comparison

First run the basic workflow under low concurrency to obtain a reference result,
then write the ground truth into `./{env}/request_api.py`. See
`CVE-2021-26120/request_api.py` for an example.

#### Matchare

Training:

1. Generate `db_results.json` from the normal workflow as training samples.
2. Configure `./utils/generate_training_data.py` for database training data and
   run it. This generates `training_data.json` under `./webfix-matchare/data/`.
3. Train the model from the `./webfix-matchare` directory:

   ```bash
   python train.py --model-type db --epochs 50 --batch-size 32 --lr 0.01
   ```

Inference and validation:

1. Run `start_request.py` to generate the ground truth.
2. Collect database application logs and configure paths in
   `./utils/generate_verify_data.py`. The `get_db_logs` function may need to be
   updated for different database types or versions.
3. Generate verification data:

   ```bash
   python ./utils/generate_verify_data.py
   ```

   This creates `./webfix-matchare/data/verify_data.json`.
4. Run prediction from `./webfix-matchare`:

   ```bash
   python verify.py --type db
   ```

   The output is written to `./webfix-matchare/predictions.json`.
5. Configure `./utils/calculate_accuracy.py` with `env` and `answer_type=db`.
6. Compute accuracy from the project root:

   ```bash
   python ./utils/calculate_accuracy.py
   ```

#### WebFix

1. Run the normal workflow to obtain `db_results.json`.
2. Configure `./utils/generate_webfix_predictions.py` for database prediction
   and run it.
3. Configure `./utils/calculate_accuracy.py` with `env` and `answer_type=db`.
4. Compute accuracy from the project root:

   ```bash
   python ./utils/calculate_accuracy.py
   ```

## Filesystem Recovery

### Recovery Validation

1. After starting the scenario, configure `./{env}/fs/config.py`.
2. Start filesystem backup:

   ```bash
   python ./{env}/fs/watch.py
   ```

3. After sysdig stops, stop the backup program and run:

   ```bash
   python ./{env}/fs/analyze.py
   ```

4. Select a request ID from `fs_results.json`, provide it to
   `./{env}/fs/restore_fs.py`, and run the recovery script. Inspect the
   filesystem state to verify that the operations caused by the selected request
   have been restored as expected.

### Accuracy Comparison

First run the basic workflow under low concurrency to obtain a reference result,
then write the ground truth into `./{env}/request_api.py`. See
`CVE-2021-26120/request_api.py` for an example.

#### Matchare

Training:

1. Generate `matchare_res.json` and `req_info.json` from the normal workflow as
   training samples.
2. Configure `./utils/generate_training_data.py` for filesystem training data
   and run it. This generates `training_data.json` under
   `./webfix-matchare/data/`.
3. Train the model from the `./webfix-matchare` directory:

   ```bash
   python train.py --model-type fs --epochs 50 --batch-size 32 --lr 0.01
   ```

Inference and validation:

1. Expose the target data directory and adjust permissions so that watchdog can
   access it. See `CVE-2021-26120` for an example.
2. Before running the basic workflow, configure and start:

   ```bash
   python ./utils/watch_for_fs_verify.py
   ```

   Configure `env` and `volumn_map` in the script.
3. Run `start_request.py` to generate the ground truth.
4. Stop `./utils/watch_for_fs_verify.py` to obtain filesystem logs, then
   configure the log paths in `./utils/generate_verify_data.py`.
5. Generate verification data:

   ```bash
   python ./utils/generate_verify_data.py
   ```

   This creates `./webfix-matchare/data/verify_data.json`.
6. Run prediction from `./webfix-matchare`:

   ```bash
   python verify.py --type fs
   ```

   The output is written to `./webfix-matchare/predictions.json`.
7. Configure `./utils/calculate_accuracy.py` with `env` and `answer_type=fs`.
8. Compute accuracy from the project root:

   ```bash
   python ./utils/calculate_accuracy.py
   ```

#### WebFix

1. Run the normal workflow to obtain `matchare_res.json` and `req_info.json`.
2. Configure `./utils/generate_webfix_predictions.py` for filesystem prediction
   and run it.
3. Configure `./utils/calculate_accuracy.py` with `env` and `answer_type=fs`.
4. Compute accuracy from the project root:

   ```bash
   python ./utils/calculate_accuracy.py
   ```

## Citation

```bibtex
@article{peng2026ancora,
  title={{ANCORA}: Accurate Intrusion Recovery for Web Applications},
  author={Peng, Yihao and Ma, Biao and Wan, Hai and Zhao, Xibin},
  journal={IEEE Transactions on Dependable and Secure Computing},
  year={2026},
  pages={1--18},
  doi={10.1109/TDSC.2026.3733124},
  url={https://doi.org/10.1109/TDSC.2026.3733124}
}
```
