# Matchare 复现

## 1. 代码入口

代码入口为：`train.py ` 

## 2. 示例用法

在`start.sh`中有示例用法：

```
# 生成假数据
python gen_fake_data.py

# 训练所有模型
python train.py --data data/samples.json --model-type all --epochs 50 --batch-size 32 --lr 0.01

# 只训练数据库模型
# python train.py --data data/samples.json --model-type db --epochs 50 --batch-size 32 --lr 0.01

# 只训练文件模型
# python train.py --data data/samples.json --model-type fs --epochs 50 --batch-size 32 --lr 0.01
```

## 3. 假数据生成

可以看到，调用`gen_fake_data.py`，可以生成假数据，生成一个`data/samples.json`。

---

## 4. 配置 

- epoch数量、batch_size、learning_rate可以通过命令行直接设置。
- 其他参数可以看`config.py`中的默认配置。

---

## 5. 目前训练结果

对于db类型：

```
2025-04-16 02:56:41,107 - __main__ - WARNING - Training completed. Best F1: 0.9176, Accuracy: 0.9125, Precision: 0.8667, Recall: 0.9750, AUC: 0.8856
```

对于fs类型：

```
2025-04-16 02:56:55,189 - __main__ - WARNING - Training completed. Best F1: 0.9888, Accuracy: 0.9875, Precision: 1.0000, Recall: 0.9778, AUC: 0.9889
```

---

## 6. 后续使用建议

后续替换为真实实验场景中的数据，需要按照假数据的格式，构造一个json文件。

具体可以参考[samples.example.json](./samples.example.json)（使用`python gen_fake_data.py`，可以快速构造一个例子，保存在`data/samples.json`）。

对于每个http request，

- 给出数量接近的匹配的db opeartion；以及不匹配的db operation。
- 给出数量接近的匹配的fs opeartion；以及不匹配的fs operation。

所有字段均取材自sanare论文，因此不必进行改动。
