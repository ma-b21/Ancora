import os
import random

import numpy as np
import torch


def set_all_seeds(seed=42):
    """
    设置所有可能的随机种子，确保结果可复现

    Args:
        seed (int): 随机种子值
    """
    # Python内置random模块
    random.seed(seed)

    # Numpy
    np.random.seed(seed)

    # PyTorch (CPU和GPU)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)  # 如果使用多GPU

    # 设置PyTorch的后端
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    # 设置Python哈希种子
    os.environ["PYTHONHASHSEED"] = str(seed)

    # print(f"所有随机种子已设置为: {seed}")
