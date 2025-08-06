import os
import re
import matplotlib.pyplot as plt
import numpy as np

# 确保输出文件夹结构
os.makedirs("comparison_plots/strategy_vs_load", exist_ok=True)  # 策略vs负载（同wg/block）
os.makedirs("comparison_plots/param_impact", exist_ok=True)      # 参数影响
os.makedirs("comparison_plots/env_comparison", exist_ok=True)   # 环境对比（含miss rate）
os.makedirs("comparison_plots/llc_details", exist_ok=True)      # LLC细节

# 日志根目录（根据实际路径调整）
root_log_dir = "."

# 数据结构：data[numa_type][round][sta][wg][block][system][sat] = (avg_time, llc_loads, llc_misses, miss_percent)
data = {}

# 1. 解析日志文件（逻辑不变）
for round_dir in os.listdir(root_log_dir):
    round_match = re.match(r"(\d+)times_(numa|nonuma)", round_dir)
    if not round_match:
        continue
    round_val = round_match.group(1)
    numa_type = round_match.group(2)
    round_path = os.path.join(root_log_dir, round_dir)
    
    for filename in os.listdir(round_path):
        file_match = re.match(r"result_(ecs[01])_(\d+)_(\d+)_(\d+)_(\d+)\.log", filename)
        if not file_match:
            print(f"Skipping invalid file: {filename}")
            continue
        system = file_match.group(1)
        sta = int(file_match.group(2))
        sat = int(file_match.group(3))
        wg = int(file_match.group(4))
        block = int(file_match.group(5))
        file_path = os.path.join(round_path, filename)
        
        with open(file_path, "r") as f:
            content = f.read()
        
        # 解析平均时间
        time_match = re.search(r"Total update time:\s+((\d+)m)?(\d+\.\d+)(s|ms)", content)
        if not time_match:
            print(f"Warning: {file_path} - Time data missing")
            continue
        minutes = time_match.group(2)
        time_val = float(time_match.group(3))
        unit = time_match.group(4)
        total_sec = 0.0
        if minutes:
            total_sec += int(minutes) * 60
        total_sec += time_val / 1000.0 if unit == "ms" else time_val
        avg_time = total_sec / int(round_val)
        
        # 解析LLC数据
        ref_match = re.search(r"([\d,]+)\s+cache-references", content)
        miss_match = re.search(r"([\d,]+)\s+cache-misses", content)
        if not ref_match or not miss_match:
            print(f"Warning: {file_path} - LLC data missing")
            continue
        llc_loads = int(ref_match.group(1).replace(",", ""))
        llc_misses = int(miss_match.group(1).replace(",", ""))
        miss_percent = (llc_misses / llc_loads) * 100 if llc_loads != 0 else 0
        percent_match = re.search(r"#\s+(\d+\.\d+)%\s+of all cache refs", content)
        if percent_match:
            miss_percent = float(percent_match.group(1))
        
        # 初始化数据结构
        if numa_type not in data:
            data[numa_type] = {}
        if round_val not in data[numa_type]:
            data[numa_type][round_val] = {}
        if sta not in data[numa_type][round_val]:
            data[numa_type][round_val][sta] = {}
        if wg not in data[numa_type][round_val][sta]:
            data[numa_type][round_val][sta][wg] = {}
        if block not in data[numa_type][round_val][sta][wg]:
            data[numa_type][round_val][sta][wg][block] = {}
        if system not in data[numa_type][round_val][sta][wg][block]:
            data[numa_type][round_val][sta][wg][block][system] = {}
        
        data[numa_type][round_val][sta][wg][block][system][sat] = (
            avg_time, llc_loads, llc_misses, miss_percent
        )

# 2. 生成图表：维度1 - 并行策略vs负载规模（仅保留wg和block完全相同的组合）
def plot_strategy_vs_load():
    for numa in data:
        for round_val in data[numa]:
            for sta in data[numa][round_val]:
                # 获取当前sta下所有的wg
                all_wg = data[numa][round_val][sta].keys()
                for wg in all_wg:
                    # 获取当前wg下所有的block
                    all_blocks = data[numa][round_val][sta][wg].keys()
                    for block in all_blocks:
                        # 关键校验：只有当两种策略（ecs0和ecs1）在相同wg和block下都有数据时，才生成对比图
                        if "ecs0" in data[numa][round_val][sta][wg][block] and "ecs1" in data[numa][round_val][sta][wg][block]:
                            systems = ["ecs0", "ecs1"]
                            
                            # 获取两种策略共有的卫星数（确保数据点一一对应）
                            sats_ecs0 = set(data[numa][round_val][sta][wg][block]["ecs0"].keys())
                            sats_ecs1 = set(data[numa][round_val][sta][wg][block]["ecs1"].keys())
                            common_sats = sorted(sats_ecs0 & sats_ecs1)  # 交集
                            if not common_sats:
                                continue  # 无共同卫星数据，跳过
                            
                            # 计算链路数（sta * sat）
                            links_list = [sta * sat for sat in common_sats]
                            
                            # 生成时间对比图（严格同wg/block）
                            plt.figure(figsize=(10, 6))
                            for sys in systems:
                                strategy = "inter-block (ecs0)" if sys == "ecs0" else "intra-block (ecs1)"
                                # 提取对应卫星的数据（保证顺序一致）
                                times = [data[numa][round_val][sta][wg][block][sys][sat][0] for sat in common_sats]
                                # 按链路数排序
                                sorted_pairs = sorted(zip(links_list, times))
                                sorted_links, sorted_times = zip(*sorted_pairs)
                                plt.plot(sorted_links, sorted_times, marker='o', label=strategy)
                            
                            plt.xlabel("Number of Links (Stations × Satellites)")
                            plt.ylabel("Average Time (seconds)")
                            plt.title(f"{numa} - Stations={sta}, WG={wg}, Block={block}\nStrategy Comparison (Same WG/Block)")
                            plt.legend()
                            plt.grid(alpha=0.3)
                            plt.xticks(rotation=45)
                            plt.tight_layout()
                            save_path = f"comparison_plots/strategy_vs_load/{numa}_sta{sta}_wg{wg}_block{block}_time.png"
                            plt.savefig(save_path, dpi=300)
                            plt.close()
                            print(f"Saved: {save_path}")
                            
                            # 生成LLC缺失率对比图（严格同wg/block）
                            plt.figure(figsize=(10, 6))
                            for sys in systems:
                                strategy = "inter-block (ecs0)" if sys == "ecs0" else "intra-block (ecs1)"
                                misses = [data[numa][round_val][sta][wg][block][sys][sat][3] for sat in common_sats]
                                sorted_pairs = sorted(zip(links_list, misses))
                                sorted_links, sorted_misses = zip(*sorted_pairs)
                                plt.plot(sorted_links, sorted_misses, marker='x', label=strategy)
                            
                            plt.xlabel("Number of Links (Stations × Satellites)")
                            plt.ylabel("LLC Miss Percentage (%)")
                            plt.title(f"{numa} - Stations={sta}, WG={wg}, Block={block}\nStrategy Comparison (Same WG/Block)")
                            plt.legend()
                            plt.grid(alpha=0.3)
                            plt.xticks(rotation=45)
                            plt.tight_layout()
                            save_path = f"comparison_plots/strategy_vs_load/{numa}_sta{sta}_wg{wg}_block{block}_llc_miss.png"
                            plt.savefig(save_path, dpi=300)
                            plt.close()
                            print(f"Saved: {save_path}")
                        else:
                            # 跳过只有一种策略或参数不匹配的组合
                            print(f"Skipping: {numa}_sta{sta}_wg{wg}_block{block} (missing ecs0 or ecs1)")

# 3. 生成图表：维度2 - 参数（wg/block）对单一策略的影响（固定负载）
def plot_param_impact():
    target_links = 500 * 1000  # 可调整为实际中间负载
    for numa in data:
        for round_val in data[numa]:
            for sta in data[numa][round_val]:
                target_sat = target_links // sta
                if target_sat <= 0:
                    continue
                for wg in data[numa][round_val][sta]:
                    for block in data[numa][round_val][sta][wg]:
                        for sys in ["ecs0", "ecs1"]:
                            if sys not in data[numa][round_val][sta][wg][block] or target_sat not in data[numa][round_val][sta][wg][block][sys]:
                                continue
                            # 收集不同wg的数据（固定block和负载）
                            wg_list = sorted(data[numa][round_val][sta].keys())
                            times = []
                            valid_wg = []
                            for w in wg_list:
                                if block not in data[numa][round_val][sta][w] or sys not in data[numa][round_val][sta][w][block] or target_sat not in data[numa][round_val][sta][w][block][sys]:
                                    continue
                                valid_wg.append(w)
                                times.append(data[numa][round_val][sta][w][block][sys][target_sat][0])
                            if len(valid_wg) < 2:
                                continue
                            
                            plt.figure(figsize=(10, 6))
                            strategy = "inter-block (ecs0)" if sys == "ecs0" else "intra-block (ecs1)"
                            plt.plot(valid_wg, times, marker='o', color='b' if sys == "ecs0" else 'g')
                            plt.xlabel("Number of Work Groups (WG)")
                            plt.ylabel("Average Time (seconds)")
                            plt.title(f"{numa} - {strategy}, Stations={sta}, Block={block}, Links≈{target_links}\nTime vs WG")
                            plt.grid(alpha=0.3)
                            plt.tight_layout()
                            save_path = f"comparison_plots/param_impact/{numa}_{sys}_sta{sta}_block{block}_time_vs_wg.png"
                            plt.savefig(save_path, dpi=300)
                            plt.close()
                            print(f"Saved: {save_path}")

# 4. 生成图表：维度3 - 环境（numa vs nonuma）对比（含时间和miss rate）
def plot_env_comparison():
    for round_val in data.get("numa", {}):
        if round_val not in data.get("nonuma", {}):
            continue
        for sta in data["numa"][round_val]:
            if sta not in data["nonuma"][round_val]:
                continue
            for wg in data["numa"][round_val][sta]:
                if wg not in data["nonuma"][round_val][sta]:
                    continue
                for block in data["numa"][round_val][sta][wg]:
                    if block not in data["nonuma"][round_val][sta][wg]:
                        continue
                    for sys in ["ecs0", "ecs1"]:
                        if sys not in data["numa"][round_val][sta][wg][block] or sys not in data["nonuma"][round_val][sta][wg][block]:
                            continue
                        
                        # 筛选两种环境共有的卫星数
                        sats = sorted(set(
                            sat for sat in data["numa"][round_val][sta][wg][block][sys].keys()
                            if sat in data["nonuma"][round_val][sta][wg][block][sys].keys()
                        ))
                        if not sats:
                            continue
                        links_list = [sta * sat for sat in sats]
                        
                        # 1. 时间对比图
                        numa_times = [data["numa"][round_val][sta][wg][block][sys][sat][0] for sat in sats]
                        nonuma_times = [data["nonuma"][round_val][sta][wg][block][sys][sat][0] for sat in sats]
                        sorted_numa = sorted(zip(links_list, numa_times))
                        sorted_nonuma = sorted(zip(links_list, nonuma_times))
                        sorted_links, numa_sorted = zip(*sorted_numa)
                        _, nonuma_sorted = zip(*sorted_nonuma)
                        
                        plt.figure(figsize=(10, 6))
                        strategy = "inter-block (ecs0)" if sys == "ecs0" else "intra-block (ecs1)"
                        plt.plot(sorted_links, numa_sorted, marker='o', label="NUMA")
                        plt.plot(sorted_links, nonuma_sorted, marker='s', label="Non-NUMA")
                        plt.xlabel("Number of Links (Stations × Satellites)")
                        plt.ylabel("Average Time (seconds)")
                        plt.title(f"{strategy}, Stations={sta}, WG={wg}, Block={block}\nNUMA vs Non-NUMA (Time)")
                        plt.legend()
                        plt.grid(alpha=0.3)
                        plt.xticks(rotation=45)
                        plt.tight_layout()
                        save_path = f"comparison_plots/env_comparison/{sys}_sta{sta}_wg{wg}_block{block}_time.png"
                        plt.savefig(save_path, dpi=300)
                        plt.close()
                        print(f"Saved: {save_path}")
                        
                        # 2. LLC miss rate对比图
                        numa_miss = [data["numa"][round_val][sta][wg][block][sys][sat][3] for sat in sats]
                        nonuma_miss = [data["nonuma"][round_val][sta][wg][block][sys][sat][3] for sat in sats]
                        sorted_numa_miss = sorted(zip(links_list, numa_miss))
                        sorted_nonuma_miss = sorted(zip(links_list, nonuma_miss))
                        sorted_links, numa_miss_sorted = zip(*sorted_numa_miss)
                        _, nonuma_miss_sorted = zip(*sorted_nonuma_miss)
                        
                        plt.figure(figsize=(10, 6))
                        plt.plot(sorted_links, numa_miss_sorted, marker='o', label="NUMA")
                        plt.plot(sorted_links, nonuma_miss_sorted, marker='s', label="Non-NUMA")
                        plt.xlabel("Number of Links (Stations × Satellites)")
                        plt.ylabel("LLC Miss Percentage (%)")
                        plt.title(f"{strategy}, Stations={sta}, WG={wg}, Block={block}\nNUMA vs Non-NUMA (Miss Rate)")
                        plt.legend()
                        plt.grid(alpha=0.3)
                        plt.xticks(rotation=45)
                        plt.tight_layout()
                        save_path = f"comparison_plots/env_comparison/{sys}_sta{sta}_wg{wg}_block{block}_miss_rate.png"
                        plt.savefig(save_path, dpi=300)
                        plt.close()
                        print(f"Saved: {save_path}")

# 5. 生成图表：维度4 - LLC细节对比（访问量和缺失量）
def plot_llc_details():
    for numa in data:
        for round_val in data[numa]:
            for sta in data[numa][round_val]:
                for wg in data[numa][round_val][sta]:
                    for block in data[numa][round_val][sta][wg]:
                        # 仅处理两种策略都存在的情况
                        if "ecs0" in data[numa][round_val][sta][wg][block] and "ecs1" in data[numa][round_val][sta][wg][block]:
                            systems = ["ecs0", "ecs1"]
                            sats_ecs0 = set(data[numa][round_val][sta][wg][block]["ecs0"].keys())
                            sats_ecs1 = set(data[numa][round_val][sta][wg][block]["ecs1"].keys())
                            common_sats = sorted(sats_ecs0 & sats_ecs1)
                            if not common_sats:
                                continue
                            links_list = [sta * sat for sat in common_sats]
                            
                            plt.figure(figsize=(10, 6))
                            for sys in systems:
                                strategy = "inter-block (ecs0)" if sys == "ecs0" else "intra-block (ecs1)"
                                # LLC访问量
                                loads = [data[numa][round_val][sta][wg][block][sys][sat][1] for sat in common_sats]
                                sorted_loads = sorted(zip(links_list, loads))
                                s_links, s_loads = zip(*sorted_loads)
                                plt.plot(s_links, s_loads, marker='o', linestyle='-', label=f"{strategy} - LLC Loads")
                                # LLC缺失量
                                misses = [data[numa][round_val][sta][wg][block][sys][sat][2] for sat in common_sats]
                                sorted_misses = sorted(zip(links_list, misses))
                                s_links, s_misses = zip(*sorted_misses)
                                plt.plot(s_links, s_misses, marker='x', linestyle='--', label=f"{strategy} - LLC Misses")
                            plt.xlabel("Number of Links (Stations × Satellites)")
                            plt.ylabel("Count")
                            plt.title(f"{numa} - Stations={sta}, WG={wg}, Block={block}\nLLC Loads vs Misses (Same WG/Block)")
                            plt.legend()
                            plt.grid(alpha=0.3)
                            plt.xticks(rotation=45)
                            plt.tight_layout()
                            save_path = f"comparison_plots/llc_details/{numa}_sta{sta}_wg{wg}_block{block}_llc_details.png"
                            plt.savefig(save_path, dpi=300)
                            plt.close()
                            print(f"Saved: {save_path}")

# 执行绘图
if __name__ == "__main__":
    plot_strategy_vs_load()
    plot_param_impact()
    plot_env_comparison()
    plot_llc_details()
    print("All comparison plots generated successfully")
