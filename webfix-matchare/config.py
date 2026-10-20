"""
Matchare配置文件
"""
import os

# 种子
RANDOM_SEED = 20130630

# 数据路径
DATA_FILE = "data/training_data.json"
VERIFY_DATA_FILE = "data/verify_data.json"

# 训练参数
BATCH_SIZE = 32
LEARNING_RATE = 0.001
NUM_EPOCHS = 50
WEIGHT_DECAY = 1e-5
MATCH_THRESHOLD = 0.7

# 模型保存路径
MODEL_SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")

# 模型配置
MODEL_CONFIG = {
    "db": {"name": "DBMatchModel", "save_path": f"{MODEL_SAVE_DIR}/db_match_model.pth"},
    "fs": {"name": "FSMatchModel", "save_path": f"{MODEL_SAVE_DIR}/fs_match_model.pth"},
}
