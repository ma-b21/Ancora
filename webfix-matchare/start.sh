# 生成假数据
python gen_fake_data.py

# 训练所有模型
python train.py --data data/samples.json --model-type all --epochs 50 --batch-size 32 --lr 0.01

# 只训练数据库模型
# python train.py --data data/samples.json --model-type db --epochs 50 --batch-size 32 --lr 0.01

# 只训练文件模型
# python train.py --data data/samples.json --model-type fs --epochs 50 --batch-size 32 --lr 0.01
