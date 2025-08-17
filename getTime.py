import os
import re
from collections import defaultdict

# 日志文件夹路径
log_dir = "10times"
# 输出结果文件
output_file = "execution_time_comparison.txt"

# 存储数据：key为(station, satellite, coroutine)，value为{system: time}
data = defaultdict(dict)

# 匹配文件名的正则表达式
# ecs1文件名格式：result_ecs1_1000_20000_1_1.log
ecs_pattern = re.compile(r"result_ecs1_(\d+)_(\d+)_\d+_(\d+)\.log")
# kube文件名格式：result_kube_1000_20000_1_16.log
kube_pattern = re.compile(r"result_kube_(\d+)_(\d+)_\d+_(\d+)\.log")

# 时间转换函数：将xxmxxs格式转换为总秒数
def convert_time(time_str):
    # 匹配分钟和秒部分（如5m50.143266663s）
    match = re.match(r"(\d+)m([\d.]+)s", time_str)
    if match:
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        return minutes * 60 + seconds
    # 匹配纯秒格式（如53.190711559s）
    match = re.match(r"([\d.]+)s", time_str)
    if match:
        return float(match.group(1))
    return 0.0  # 无法解析的时间

# 遍历日志文件夹
for filename in os.listdir(log_dir):
    file_path = os.path.join(log_dir, filename)
    
    # 处理ecs1日志
    ecs_match = ecs_pattern.match(filename)
    if ecs_match:
        station, satellite, coroutine = ecs_match.groups()
        key = (station, satellite, coroutine)
        
        with open(file_path, "r") as f:
            content = f.read()
        
        # 提取Total update time
        time_match = re.search(r"Total update time:\s+(\d+m[\d.]+\s*s|\d+\.\d+\s*s)", content)
        if time_match:
            time_str = time_match.group(1).strip()
            total_seconds = convert_time(time_str)
            avg_time = total_seconds / 10  # 计算单次平均时间
            data[key]["ecs1"] = avg_time
        else:
            print(f"警告：{filename} 中未找到Total update time")
        continue
    
    # 处理kube日志
    kube_match = kube_pattern.match(filename)
    if kube_match:
        station, satellite, coroutine = kube_match.groups()
        key = (station, satellite, coroutine)
        
        with open(file_path, "r") as f:
            content = f.read()
        
        # 提取interval
        time_match = re.search(r"interval\s*=\s+(\d+m[\d.]+\s*s|\d+\.\d+\s*s)", content)
        if time_match:
            time_str = time_match.group(1).strip()
            total_seconds = convert_time(time_str)
            avg_time = total_seconds / 10  # 计算单次平均时间
            data[key]["kube"] = avg_time
        else:
            print(f"警告：{filename} 中未找到interval")
        continue

# 保存结果到文件
with open(output_file, "w") as f:
    # 写入表头
    f.write("station,satellite,coroutine,ecs1_avg_time(s),kube_avg_time(s),improvement_percent(%)\n")
    
    # 按key排序输出
    for key in sorted(data.keys(), key=lambda x: (int(x[0]), int(x[1]), int(x[2]))):
        station, satellite, coroutine = key
        ecs_time = data[key].get("ecs1", None)
        kube_time = data[key].get("kube", None)
        
        # 计算提升百分比
        improvement = ""
        if ecs_time is not None and kube_time is not None and kube_time > 0:
            improvement = (kube_time - ecs_time) / kube_time * 100
            improvement_str = f"{improvement:.2f}%"
        else:
            improvement_str = "数据不完整"
        
        # 写入行数据
        ecs_str = f"{ecs_time:.6f}" if ecs_time is not None else "N/A"
        kube_str = f"{kube_time:.6f}" if kube_time is not None else "N/A"
        f.write(f"{station},{satellite},{coroutine},{ecs_str},{kube_str},{improvement_str}\n")

print(f"结果已保存至 {output_file}")