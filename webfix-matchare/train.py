import argparse
import logging
import os

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm
import pickle

from config import (
    BATCH_SIZE,
    DATA_FILE,
    LEARNING_RATE,
    MATCH_THRESHOLD,
    MODEL_CONFIG,
    MODEL_SAVE_DIR,
    NUM_EPOCHS,
    RANDOM_SEED,
    WEIGHT_DECAY,
)
from data.dataset import create_dataloaders
from data.preprocessing import create_encoders, load_and_preprocess_data
from models.db_model import DBMatchModel
from models.fs_model import FSMatchModel
from utils.metrics import evaluate_model
from utils.seed import set_all_seeds

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def train_model(
    model,
    train_dataloader,
    test_dataloader,
    device,
    model_save_path,
    learning_rate,
    num_epochs,
):
    """训练模型"""
    # 定义损失函数和优化器
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(
        model.parameters(), lr=learning_rate, weight_decay=WEIGHT_DECAY
    )

    # 创建保存模型的目录
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)

    # 记录最佳F1分数
    best_metrics = {"f1": 0.0}

    # 训练循环
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0

        # 使用tqdm显示进度条
        with tqdm(train_dataloader, unit="batch") as tepoch:
            for features, labels in tepoch:
                tepoch.set_description(f"Epoch {epoch+1}/{num_epochs}")

                features = features.to(device)
                labels = labels.to(device)

                # 前向传播
                outputs = model(features)
                loss = criterion(outputs.squeeze(), labels)

                # 反向传播和优化
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                running_loss += loss.item()
                tepoch.set_postfix(loss=loss.item())

        # 计算平均损失
        epoch_loss = running_loss / len(train_dataloader)

        # 评估模型
        metrics = evaluate_model(model, test_dataloader, device, MATCH_THRESHOLD)

        logger.info(
            f"Epoch {epoch+1}/{num_epochs}, Loss: {epoch_loss:.4f}, "
            f"Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1']:.4f}, "
            f"Precision: {metrics['precision']:.4f}, Recall: {metrics['recall']:.4f}, "
            f"AUC: {metrics['auc']:.4f}"
        )

        # 保存最佳模型
        if metrics["f1"] > best_metrics["f1"]:
            best_metrics = metrics
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "loss": epoch_loss,
                    "metrics": metrics,
                },
                model_save_path,
            )
            logger.warning(
                f"Model saved to {model_save_path} with F1: {best_metrics['f1']:.4f}"
            )

    logger.warning(
        f"Training completed. "
        f"Best F1: {best_metrics['f1']:.4f}, "
        f"Accuracy: {best_metrics['accuracy']:.4f}, "
        f"Precision: {best_metrics['precision']:.4f}, "
        f"Recall: {best_metrics['recall']:.4f}, "
        f"AUC: {best_metrics['auc']:.4f}"
    )


def main():
    parser = argparse.ArgumentParser(description="Train Matchare models")
    parser.add_argument("--data", type=str, default=DATA_FILE, help="Path to data file")
    parser.add_argument(
        "--model-type",
        type=str,
        choices=["db", "fs", "all"],
        default="all",
        help="Type of model to train (db, fs, or all)",
    )
    parser.add_argument(
        "--epochs", type=int, default=NUM_EPOCHS, help="Number of epochs"
    )
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Batch size")
    parser.add_argument("--lr", type=float, default=LEARNING_RATE, help="Learning rate")
    args = parser.parse_args()

    # 初始化种子
    # set_all_seeds(RANDOM_SEED)

    # 设置设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    # 加载并预处理数据
    logger.info(f"Loading data from {args.data}...")
    samples, feature_info = load_and_preprocess_data(args.data)
    logger.info(f"Loaded {len(samples)} samples")

    # 创建编码器
    encoders_and_scalers = create_encoders(feature_info)

    # 保存编码器和缩放器
    with open(f"{MODEL_SAVE_DIR}/encoders_and_scalers.pkl", "wb") as f:
        pickle.dump(encoders_and_scalers, f)
    logger.info(f"Encoders and scalers saved to {MODEL_SAVE_DIR}/encoders_and_scalers.pkl")

    # 确定要训练的模型类型
    model_types = ["db", "fs"] if args.model_type == "all" else [args.model_type]

    # 对每种模型类型进行训练
    for model_type in model_types:
        logger.info(f"Training {model_type.upper()} model...")

        # 创建数据加载器
        train_dataloader, test_dataloader, feature_dims = create_dataloaders(
            samples,
            encoders_and_scalers["encoders"],
            encoders_and_scalers["scalers"],
            model_type,
            batch_size=args.batch_size,
        )

        # 获取特征维度
        http_feature_dim = feature_dims["http_feature_dim"]
        operation_feature_dim = feature_dims["operation_feature_dim"]

        logger.info(f"HTTP feature dimension: {http_feature_dim}")
        logger.info(f"Operation feature dimension: {operation_feature_dim}")

        # 创建模型
        if model_type == "db":
            model = DBMatchModel(http_feature_dim, operation_feature_dim).to(device)
        elif model_type == "fs":
            model = FSMatchModel(http_feature_dim, operation_feature_dim).to(device)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # 训练模型
        train_model(
            model,
            train_dataloader,
            test_dataloader,
            device,
            MODEL_CONFIG[model_type]["save_path"],
            learning_rate=args.lr,
            num_epochs=args.epochs,
        )

        logger.info(f"Finished training {model_type.upper()} model")


if __name__ == "__main__":
    main()
