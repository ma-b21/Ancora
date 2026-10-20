import torch  
import torch.nn as nn  
from torch.utils.data import DataLoader
import numpy as np
from config import VERIFY_DATA_FILE, MODEL_CONFIG, MATCH_THRESHOLD, MODEL_SAVE_DIR
import json
import logging
from argparse import ArgumentParser
import pickle

from data.dataset import create_dataloaders
from data.preprocessing import create_encoders, load_and_preprocess_data
from models.db_model import DBMatchModel
from models.fs_model import FSMatchModel


# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


model_type = "db"  # or "fs"


def evaluate_model(model, dataloader, device, threshold=MATCH_THRESHOLD):
    index = 0
    true_indexs = []
    with torch.no_grad():
        model.eval()

        for features, _ in dataloader:
            features = features.to(device)
            outputs = model(features)
            probs = torch.sigmoid(outputs).cpu().numpy()
            preds = (probs >= threshold).astype(int)

            if preds[0][0] == 1:
                true_indexs.append(index)
            
            index += 1
    logger.info(f"True indexs: {true_indexs}")
    return true_indexs


def main():
    parser = ArgumentParser(description="Verify Matchare models")
    parser.add_argument(
        "--type",
        type=str,
        choices=["db", "fs"],
        default="db",
        help="Type of model to verify (db or fs)",
    )
    args = parser.parse_args()
    model_type = args.type
    logger.info(f"Verifying {model_type.upper()} model")

    with open(VERIFY_DATA_FILE, "r") as f:
        requests = json.load(f)

    predictions = {}
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    datas = [value for _, value in requests.items()]
    multiple_samples, _ = load_and_preprocess_data(data=datas, use_multiple_samples=True)
    # encoders_and_scalers = create_encoders(feature_info)
    with open(f"{MODEL_SAVE_DIR}/encoders_and_scalers.pkl", "rb") as f:
        encoders_and_scalers = pickle.load(f)

    zipped_data = zip(requests.keys(), multiple_samples)
    for key, samples in zipped_data:
        test_dataloader, _, feature_dims = create_dataloaders(
            samples,
            encoders_and_scalers["encoders"],
            encoders_and_scalers["scalers"],
            model_type,
            batch_size=1,
            verify=True,
        )
        # 获取特征维度
        http_feature_dim = feature_dims["http_feature_dim"]
        operation_feature_dim = feature_dims["operation_feature_dim"]
        if http_feature_dim == 0 or operation_feature_dim == 0:
            logger.error(f"Invalid feature dimensions for {key}: http_feature_dim={http_feature_dim}, operation_feature_dim={operation_feature_dim}")
            continue
        logger.info(f"HTTP feature dimension: {http_feature_dim}")
        logger.info(f"Operation feature dimension: {operation_feature_dim}")
        # 创建模型
        if model_type == "db":
            model = DBMatchModel(http_feature_dim, operation_feature_dim)
        elif model_type == "fs":
            model = FSMatchModel(http_feature_dim, operation_feature_dim)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        # 加载模型
        checkpoint = torch.load(MODEL_CONFIG[model_type]["save_path"], map_location=device, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        model.eval()

        # 评估模型
        true_indexs = evaluate_model(model, test_dataloader, device)
        predictions[key] = {
            "http_request": requests[key]["http_request"],
            "db_statements": [requests[key]["db_statements"][i] for i in true_indexs] if model_type == "db" else [],
            "fs_operations": [requests[key]["fs_operations"][i] for i in true_indexs] if model_type == "fs" else [],
        }
        print(f"Finished evaluating {model_type.upper()} model for {key} data")
    
    # 保存预测结果
    with open("predictions.json", "w") as f:
        json.dump(predictions, f, indent=4)


if __name__ == "__main__":
    main()