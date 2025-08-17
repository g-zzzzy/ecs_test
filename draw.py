import os
import re
import logging
import matplotlib.pyplot as plt
from collections import defaultdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 确保输出文件夹存在
OUTPUT_DIR = "large_scale_plots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_time_string(time_match):
    """解析时间字符串并转换为总秒数"""
    minutes = time_match.group(2)
    time_value = float(time_match.group(3))
    unit = time_match.group(4)
    
    total_seconds = 0.0
    if minutes:
        total_seconds += int(minutes) * 60
    if unit == "ms":
        total_seconds += time_value / 1000.0
    else:  # unit == "s"
        total_seconds += time_value
    return total_seconds

def parse_log_file(file_path, system_type, round_num):
    """解析单个日志文件，仅提取平均时间指标"""
    try:
        with open(file_path, "r") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"无法读取文件 {file_path}: {e}")
        return None
    
    # 提取时间信息
    time_patterns = {
        "ecs1": r"Total update time:\s+((\d+)m)?(\d+\.\d+)(s|ms)",
        "kube": r"interval\s*=\s+((\d+)m)?(\d+\.\d+)(s|ms)"
    }
    
    time_match = re.search(time_patterns[system_type], content)
    if not time_match:
        logger.warning(f"文件 {file_path} 中未找到时间信息")
        return None
    
    try:
        total_seconds = parse_time_string(time_match)
        avg_time = total_seconds / round_num
        return avg_time  # 仅返回平均时间
    except Exception as e:
        logger.error(f"解析时间失败 {file_path}: {e}")
        return None

def collect_data(root_log_dir):
    """收集并组织所有日志文件中的数据（仅保留平均时间）"""
    # 数据结构：data[round][stations][system][satellites][workers] = avg_time
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict))))
    
    for round_dir in os.listdir(root_log_dir):
        round_match = re.match(r"(\d+)times", round_dir)
        if not round_match:
            continue
        
        round_val = int(round_match.group(1))
        round_path = os.path.join(root_log_dir, round_dir)
        logger.info(f"处理轮次目录: {round_path}")
        
        if not os.path.isdir(round_path):
            continue
            
        for filename in os.listdir(round_path):
            # 解析文件名：result_(ecs1|kube)_(sta)_(sat)_(unknown)_(wg).log
            file_match = re.match(r"result_(ecs1|kube)_(\d+)_(\d+)_(\d+)_(\d+)\.log", filename)
            if not file_match:
                continue
            
            system_type, sta_str, sat_str, _, wg_str = file_match.groups()
            try:
                stations = int(sta_str)
                satellites = int(sat_str)
                workers = int(wg_str)
            except ValueError:
                logger.warning(f"文件名 {filename} 包含无效数字")
                continue
            
            file_path = os.path.join(round_path, filename)
            avg_time = parse_log_file(file_path, system_type, round_val)
            
            if avg_time is not None:
                data[round_val][stations][system_type][satellites][workers] = avg_time
                logger.debug(f"成功解析 {filename}: 平均时间={avg_time:.2f}秒")
    
    return data

def generate_avg_time_charts(data):
    """仅生成平均时间图表"""
    for round_val in data:
        for stations in data[round_val]:
            systems = data[round_val][stations].keys()
            if not systems:
                continue
                
            # 收集所有卫星和工作节点数量
            all_satellites = set()
            all_workers = set()
            for system in systems:
                all_satellites.update(data[round_val][stations][system].keys())
                for sat in data[round_val][stations][system]:
                    all_workers.update(data[round_val][stations][system][sat].keys())
            
            sorted_satellites = sorted(all_satellites)
            sorted_workers = sorted(all_workers)
            
            # 仅生成平均时间图表
            plt.figure(figsize=(12, 7))
            
            for system in systems:
                system_data = data[round_val][stations][system]
                for worker in sorted_workers:
                    values = []
                    link_counts = []
                    
                    for sat in sorted_satellites:
                        if sat in system_data and worker in system_data[sat]:
                            link_count = stations * sat
                            link_counts.append(link_count)
                            values.append(system_data[sat][worker])
                    
                    # 按链路数量排序
                    if link_counts and values:
                        combined = sorted(zip(link_counts, values))
                        sorted_links, sorted_values = zip(*combined)
                        plt.plot(
                            sorted_links, sorted_values, 
                            marker='o', 
                            label=f"{system} (wg={worker})"
                        )
            
            plt.xlabel("Number of Links (Stations × Satellites)")
            plt.ylabel("Average Time (seconds)")
            plt.title(f"Round={round_val}, Stations={stations}: Average Time vs Links")
            plt.xticks(sorted(link_counts), rotation=45)
            plt.grid(alpha=0.3)
            plt.legend()
            plt.tight_layout()
            
            # 保存图表
            save_path = os.path.join(
                OUTPUT_DIR, 
                f"round_{round_val}_sta_{stations}_avg_time.png"
            )
            plt.savefig(save_path, dpi=300)
            logger.info(f"平均时间图表已保存: {save_path}")
            plt.close()

def main():
    """主函数：协调数据收集和平均时间图表生成"""
    root_log_dir = "."  # 日志根目录
    logger.info("开始收集日志数据...")
    data = collect_data(root_log_dir)
    
    if not data:
        logger.warning("未收集到任何数据，无法生成图表")
        return
    
    logger.info("开始生成平均时间图表...")
    generate_avg_time_charts(data)
    logger.info("所有平均时间图表生成完成")

if __name__ == "__main__":
    main()