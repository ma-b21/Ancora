import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    roc_auc_score,
)


def evaluate_model(model, dataloader, device, threshold=0.7):
    """
    评估模型性能

    Args:
        model: 模型
        dataloader: 数据加载器
        device: 设备（CPU或GPU）
        threshold: 分类阈值

    Returns:
        评估指标字典
    """
    model.eval()

    all_preds = []
    all_labels = []
    all_probs = []

    with torch.no_grad():
        for features, labels in dataloader:
            features = features.to(device)
            labels = labels.to(device)

            outputs = model(features)
            probs = outputs.squeeze().cpu().numpy()
            preds = (probs >= threshold).astype(int)

            all_probs.extend(probs)
            all_preds.extend(preds)
            all_labels.extend(labels.cpu().numpy())

    # 计算评估指标
    precision, recall, f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, average="binary"
    )
    accuracy = accuracy_score(all_labels, all_preds)

    # 计算AUC
    try:
        auc = roc_auc_score(all_labels, all_probs)
    except:
        auc = 0.5  # 如果所有标签都相同，则AUC无法计算

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auc": auc,
    }
