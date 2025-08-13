import torch
import torch.nn as nn
import torch.nn.functional as F


class FSMatchModel(nn.Module):
    def __init__(self, http_feature_dim, fs_feature_dim):
        """
        文件系统操作匹配模型

        Args:
            http_feature_dim: HTTP请求特征维度
            fs_feature_dim: 文件系统操作特征维度
        """
        super(FSMatchModel, self).__init__()

        # 特征维度
        self.input_dim = http_feature_dim + fs_feature_dim

        # 深度CNN
        self.layer1 = nn.Linear(self.input_dim, 64)
        self.bn1 = nn.BatchNorm1d(64)
        self.layer2 = nn.Linear(64, 32)
        self.bn2 = nn.BatchNorm1d(32)
        self.layer3 = nn.Linear(32, 16)
        self.bn3 = nn.BatchNorm1d(16)
        self.layer4 = nn.Linear(16, 8)
        self.bn4 = nn.BatchNorm1d(8)
        self.layer5 = nn.Linear(8, 4)
        self.bn5 = nn.BatchNorm1d(4)
        self.output = nn.Linear(4, 1)

    def forward(self, x):
        # 第一层
        x = self.layer1(x)
        x = self.bn1(x)
        x = torch.tanh(x)

        # 第二层
        x = self.layer2(x)
        x = self.bn2(x)
        x = torch.tanh(x)

        # 第三层
        x = self.layer3(x)
        x = self.bn3(x)
        x = torch.tanh(x)

        # 第四层
        x = self.layer4(x)
        x = self.bn4(x)
        x = torch.tanh(x)

        # 第五层
        x = self.layer5(x)
        x = self.bn5(x)
        x = torch.tanh(x)

        # 输出层
        x = self.output(x)
        x = F.relu(x)

        return x
