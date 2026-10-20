import torch
import torch.nn as nn
import torch.nn.functional as F


class DBMatchModel(nn.Module):
    def __init__(self, http_feature_dim, db_feature_dim):
        """
        数据库操作匹配模型

        Args:
            http_feature_dim: HTTP请求特征维度
            db_feature_dim: 数据库操作特征维度
        """
        super(DBMatchModel, self).__init__()

        # 特征维度
        self.input_dim = http_feature_dim + db_feature_dim

        # 深度CNN（实际上是一个深度全连接网络，因为我们的输入不是图像）
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
        x = torch.tanh(x)  # 使用tanh激活函数，与论文中的描述一致

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
        x = F.relu(x)  # 使用ReLU激活函数，保证输出为非负值

        return x
