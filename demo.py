from dataclasses import dataclass
from core import CharGacha, WeaponGacha, GlobalConfigLoader


@dataclass(frozen=True)
class Color:
    WHITE: str = "\033[37m"
    RED: str = "\033[31m"
    YELLOW: str = "\033[33m"
    PURPLE: str = "\033[35m"
    BLUE: str = "\033[34m"
    RESET: str = "\033[0m"


def colorprint(text: str, color: str) -> None:
    print(f"{color}{text}{Color.RESET}")


class GachaTestTool:
    def __init__(self):
        self.config = GlobalConfigLoader()
        self.text = {
            "char_pool": self.config.get_text("char_pool_name"),
            "weapon_pool": self.config.get_text("weapon_pool_name"),
            "draw": self.config.get_text("draw_text"),
            "apply": self.config.get_text("apply_text"),
            "weapon_draw": self.config.get_text("weapon_draw_text"),
            "star": self.config.get_text("star_text"),
            "up": self.config.get_text("up_text"),
            "rate": self.config.get_text("rate_text"),
            "time": self.config.get_text("time_text"),
            "total_time": self.config.get_text("total_time_text"),
            "per_second": self.config.get_text("per_second_text"),
            "char_quota_name": self.config.get_text("char_quota_name"),
            "weapon_quota_name": self.config.get_text("weapon_quota_name"),
        }
        # 格式化配置：适配中文，名称移至最后
        self.width = {
            "draw_num": 10,  # 抽数/申领次数宽度
            "star": 2,  # 星级宽度（如「6星」）
            "quota": 9,  # 配额列宽度（含配额名称，如「武库配额：2000」）
            "stat_num": 10,  # 测试统计-数字宽度
            "stat_rate": 8,  # 测试统计-概率宽度
        }

    def demo_char_draw(self, draw_times: int = 5):
        """角色卡池抽卡示例"""
        title = f"{self.text['char_pool']}{self.text['draw']}示例"
        print(
            f"\n{title.center(self.width['draw_num']+self.width['star']+self.width['quota']+20, '-')}"
        )
        gacha = CharGacha()
        # 表头（列序：抽数 → 星级 → 配额 → 名称）
        header = (
            f"{'{0}'.format(self.text['draw']+'数'):<{self.width['draw_num']}} | "
            f"{'{0}'.format(self.text['star']+'级'):<{self.width['star']}} | "
            f"{'{0}'.format(self.text['char_quota_name']):<{self.width['quota']}}  | "
            f"名称"
        )
        print(header)
        print("-" * int(len(header) * 1.5))
        # 逐次抽卡输出（仅触发保底时标色，6星红优先）
        quota_sum = 0
        for i in range(draw_times):
            result = gacha.draw_once()
            name = result.name
            star = result.star
            quota = result.quota
            quota_sum += quota

            draw_num = f"第{i+1}{self.text['draw']}"
            star_text = f"{star}{self.text['star']}"
            quota_text = f"{self.text['char_quota_name']}：{quota}"

            # 核心标色逻辑：6星红（优先）→ 5星黄 → 4星紫 → 默认色
            line = (
                f"{draw_num:<{self.width['draw_num']}} | "
                f" {star_text:<{self.width['star']}} | "
                f"{quota_text:<{self.width['quota']}} | "
            )
            if star == 6:
                line += f"{Color.RED}{name}{Color.RESET}"
            elif star == 5:
                line += f"{Color.YELLOW}{name}{Color.RESET}"
            elif star == 4:
                line += f"{Color.PURPLE}{name}{Color.RESET}"
            else:
                line += f"{name}"
            # 触发保底时添加【保底】标注
            if result.is_5_g:
                line += "【十连保底】"
            if result.is_6_g:
                line += "【非酋保底】"
            if result.is_up_g:
                line += "【UP保底】"
            print(line)

        # 累计奖励
        rewards = gacha.get_accumulated_reward()
        rewards_str = (
            "\n".join([f"{name}×{count}" for name, count in rewards]) if rewards else ""
        )
        colorprint(
            "\n{}累计奖励：\n{}数量：{}\n{}".format(
                self.text["char_pool"],
                self.text["char_quota_name"],
                quota_sum,
                rewards_str,
            ),
            Color.RED,
        )

    def demo_weapon_apply(self, apply_times: int = 1):
        """武器卡池申领示例"""
        title = f"{self.text['weapon_pool']}{self.text['apply']}示例"
        print(
            f"\n{title.center(self.width['draw_num']+self.width['star']+self.width['quota']+40, '-')}"
        )

        gacha = WeaponGacha()
        quota_sum = 0
        for apply_idx in range(apply_times):
            print(f"\n【第{apply_idx+1}次{self.text['apply']}】")
            apply_result = gacha.apply_once()  # 接收保底标记
            # 表头（列序：抽数 → 星级 → 配额 → 名称）
            header = (
                f"{'{0}'.format(self.text['weapon_draw']+'数'):<{self.width['draw_num']}} | "
                f"{'{0}'.format(self.text['star']+'级'):<{self.width['star']}} | "
                f"{'{0}'.format(self.text['weapon_quota_name']):<{self.width['quota']}}  | "
                f"名称"
            )
            print(header)
            print("-" * len(header) * 2)
            # 逐抽输出（仅触发保底时标色+标注，6星红优先）
            for idx, result in enumerate(apply_result):
                name = result.name
                star = result.star
                quota = result.quota
                quota_sum += quota

                draw_num = f"第{idx+1}{self.text['weapon_draw']}"
                star_text = f"{star}{self.text['star']}"
                quota_text = f"{self.text['weapon_quota_name']}：{quota}"

                # 核心标色逻辑：6星红（优先）→ 5星黄 → 默认色
                line = (
                    f"{draw_num:<{self.width['draw_num']}} | "
                    f" {star_text:<{self.width['star']}} | "
                    f"{quota_text:<{self.width['quota']}} | "
                )
                if star == 6:
                    line += f"{Color.RED}{name}{Color.RESET}"
                elif star == 5:
                    line += f"{Color.YELLOW}{name}{Color.RESET}"
                else:
                    line += f"{name}"
                # 触发保底时添加【保底】标注
                if result.is_6_g:
                    line += "【保底】"
                if result.is_5_g:
                    line += "【十连保底】"
                if result.is_up_g:
                    line += "【UP保底】"
                print(line)
        # 累计奖励
        rewards = gacha.get_accumulated_reward()
        rewards_str = (
            "\n".join([f"{name}×{count}" for name, count in rewards]) if rewards else ""
        )
        colorprint(
            "\n{}累计奖励：\n{}数量：{}\n{}".format(
                self.text["weapon_pool"],
                self.text["weapon_quota_name"],
                quota_sum,
                rewards_str,
            ),
            Color.RED,
        )

    def stats_char_quota(self, draw_times: int = 50000, gragh: bool = False):
        """统计120抽角色池配额数量"""

        from tqdm import trange

        print(f"正在统计抽 120 次角色池获得的配额数量...")
        quota_list = []  # 记录每次120抽的配额值
        total_quota = 0
        for _ in trange(draw_times):
            gacha = CharGacha()
            round_quota = 0
            for _ in range(120):
                result = gacha.draw_once()
                round_quota += result.quota
            quota_list.append(round_quota)
            total_quota += round_quota
        colorprint(f"平均配额：{round(total_quota / draw_times, 1)}", Color.RED)

        if gragh:
            import matplotlib.pyplot as plt
            import numpy as np

            # 添加正态分布曲线拟合
            from scipy import stats

            # 计算区间边界
            max_quota = max(quota_list)
            min_quota = min(quota_list)

            # 使用200配额为固定区间
            bin_width = 200
            start_quota = (min_quota // bin_width) * bin_width
            bins = list[int](range(start_quota, max_quota + bin_width * 2, bin_width))

            # 计算每个区间的出现次数和概率
            counts, _ = np.histogram(quota_list, bins=bins)
            probabilities = counts / draw_times * 100  # 转换为百分比

            # 生成区间标签
            bin_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins) - 1)]

            # 打印每个区间的概率（只打印有概率的区间）
            print("\nQuota Range Probability Distribution：")
            for label, prob in zip(bin_labels, probabilities):
                if prob > 0:
                    print(f"{label}: {prob:.2f}%")

            # 生成配额分布图
            plt.figure(figsize=(12, 6))
            plt.bar(
                range(len(bin_labels)),
                probabilities,
                color="skyblue",
                edgecolor="black",
                label="Actual Distribution",
            )

            # 计算数据的均值和标准差
            quota_mean = np.mean(quota_list)
            quota_std = np.std(quota_list)

            # 生成拟合曲线的数据点
            x = np.linspace(min(quota_list), max(quota_list), 100)
            # 修正缩放因子：概率密度 * 区间宽度 * 100 = 百分比
            y = stats.norm.pdf(x, quota_mean, quota_std) * bin_width * 100

            # 转换x轴坐标到条形图的索引范围
            x_norm = (x - start_quota) / bin_width

            # 绘制拟合曲线
            plt.plot(
                x_norm,
                y,
                "r-",
                linewidth=2,
                label=f"Normal Fit (μ={quota_mean:.0f}, σ={quota_std:.0f})",
            )

            # 间隔显示xticks
            interval = max(1, len(bin_labels) // 10)  # 最多显示10个标签
            plt.xticks(
                range(0, len(bin_labels), interval),
                [bin_labels[i] for i in range(0, len(bin_labels), interval)],
                rotation=45,
                ha="right",
            )
            plt.title("120 Draws Char Pool Quota Distribution")

            plt.xlabel("Quota Range")
            plt.ylabel("Prob (%)")
            plt.grid(axis="y", alpha=0.75)
            plt.legend()
            plt.tight_layout()
            plt.show()

    def stats_weapon_quota(self, draw_times: int = 50000, gragh: bool = False):
        """统计8次武器池申领配额数量"""

        from tqdm import trange

        print(f"正在统计 8 次武器池申领获得的配额数量...")
        quota_list = []  # 记录每次8次申领的配额值
        total_quota = 0
        for _ in trange(draw_times):
            gacha = WeaponGacha()
            round_quota = 0
            for _ in range(8):
                apply_result = gacha.apply_once()
                # 累加本次申领中所有抽卡的配额
                for result in apply_result:
                    round_quota += result.quota
            quota_list.append(round_quota)
            total_quota += round_quota
        colorprint(f"平均配额：{round(total_quota / draw_times, 1)}", Color.RED)

        if gragh:
            import matplotlib.pyplot as plt
            import numpy as np

            # 添加正态分布曲线拟合
            from scipy import stats

            # 计算区间边界
            max_quota = max(quota_list)
            min_quota = min(quota_list)

            # 使用25配额为固定区间
            bin_width = 25
            start_quota = (min_quota // bin_width) * bin_width
            bins = list[int](range(start_quota, max_quota + bin_width * 2, bin_width))

            # 计算每个区间的出现次数和概率
            counts, _ = np.histogram(quota_list, bins=bins)
            probabilities = counts / draw_times * 100  # 转换为百分比

            # 生成区间标签
            bin_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins) - 1)]

            # 打印每个区间的概率（只打印有概率的区间）
            print("\nQuota Range Probability Distribution：")
            for label, prob in zip(bin_labels, probabilities):
                if prob > 0:
                    print(f"{label}: {prob:.2f}%")

            # 生成配额分布图
            plt.figure(figsize=(12, 6))
            plt.bar(
                range(len(bin_labels)),
                probabilities,
                color="skyblue",
                edgecolor="black",
                label="Actual Distribution",
            )

            # 计算数据的均值和标准差
            quota_mean = np.mean(quota_list)
            quota_std = np.std(quota_list)

            # 生成拟合曲线的数据点
            x = np.linspace(min(quota_list), max(quota_list), 100)
            # 修正缩放因子：概率密度 * 区间宽度 * 100 = 百分比
            y = stats.norm.pdf(x, quota_mean, quota_std) * bin_width * 100

            # 转换x轴坐标到条形图的索引范围
            x_norm = (x - start_quota) / bin_width

            # 绘制拟合曲线
            plt.plot(
                x_norm,
                y,
                "r-",
                linewidth=2,
                label=f"Normal Fit (μ={quota_mean:.0f}, σ={quota_std:.0f})",
            )

            # 间隔显示xticks
            interval = max(1, len(bin_labels) // 10)  # 最多显示10个标签
            plt.xticks(
                range(0, len(bin_labels), interval),
                [bin_labels[i] for i in range(0, len(bin_labels), interval)],
                rotation=45,
                ha="right",
            )
            plt.title("8 Applications Weapon Pool Quota Distribution")

            plt.xlabel("Quota Range")
            plt.ylabel("Prob (%)")
            plt.grid(axis="y", alpha=0.75)
            plt.legend()
            plt.tight_layout()
            plt.show()

    def stats_char_draw(self, draw_times: int = 50000, gragh: bool = False):
        """统计120抽角色池的6星角色数量及概率分布"""

        from tqdm import trange

        print(f"正在统计抽 120 次角色池获得的6星角色数量...")
        six_star_counts = []  # 记录每次120抽获得的6星角色数量
        total_six_stars = 0
        star_counts = {4: 0, 5: 0, 6: 0}  # 记录不同星级角色的总数量

        for _ in trange(draw_times):
            gacha = CharGacha()
            round_six_stars = 0
            for _ in range(120):
                result = gacha.draw_once()
                star_counts[result.star] += 1  # 统计星级分布
                if result.star == 6:
                    round_six_stars += 1  # 统计6星角色数量
            six_star_counts.append(round_six_stars)
            total_six_stars += round_six_stars

        # 计算平均获得的6星角色数量
        avg_six_stars = total_six_stars / draw_times
        colorprint(f"平均6星角色数量：{round(avg_six_stars, 2)}", Color.RED)

        # 计算不同星级角色的概率
        total_chars = sum(star_counts.values())
        print("\nStar Distribution Probability:")
        for star in [4, 5, 6]:
            prob = star_counts[star] / total_chars * 100
            color = (
                Color.PURPLE if star == 4 else Color.YELLOW if star == 5 else Color.RED
            )
            colorprint(f"{star}星角色：{prob:.2f}%", color)

        if gragh:
            import matplotlib.pyplot as plt
            import numpy as np

            # 添加正态分布曲线拟合
            from scipy import stats

            # 计算区间边界
            max_six_stars = max(six_star_counts)
            min_six_stars = min(six_star_counts)

            # 使用1个角色为固定区间
            bin_width = 1
            start_six_stars = min_six_stars
            bins = list[int](
                range(start_six_stars, max_six_stars + bin_width * 2, bin_width)
            )

            # 计算每个区间的出现次数和概率
            counts, _ = np.histogram(six_star_counts, bins=bins)
            probabilities = counts / draw_times * 100  # 转换为百分比

            # 生成区间标签
            bin_labels = [f"{bins[i]}" for i in range(len(bins) - 1)]

            # 打印每个区间的概率（只打印有概率的区间）
            print("\n6-Star Character Count Probability Distribution:")
            for label, prob in zip(bin_labels, probabilities):
                if prob > 0:
                    print(f"{label}: {prob:.2f}%")

            # 生成6星角色数量分布图
            plt.figure(figsize=(12, 6))
            plt.bar(
                range(len(bin_labels)),
                probabilities,
                color="skyblue",
                edgecolor="black",
                label="Actual Distribution",
            )

            # 计算数据的均值和标准差
            six_stars_mean = np.mean(six_star_counts)
            six_stars_std = np.std(six_star_counts)

            # 生成拟合曲线的数据点
            x = np.linspace(min(six_star_counts), max(six_star_counts), 100)
            # 修正缩放因子：概率密度 * 区间宽度 * 100 = 百分比
            y = stats.norm.pdf(x, six_stars_mean, six_stars_std) * bin_width * 100

            # 转换x轴坐标到条形图的索引范围
            x_norm = x - start_six_stars

            # 绘制拟合曲线
            plt.plot(
                x_norm,
                y,
                "r-",
                linewidth=2,
                label=f"Normal Fit (μ={six_stars_mean:.2f}, σ={six_stars_std:.2f})",
            )

            # 间隔显示xticks
            interval = max(1, len(bin_labels) // 10)  # 最多显示10个标签
            plt.xticks(
                range(0, len(bin_labels), interval),
                [bin_labels[i] for i in range(0, len(bin_labels), interval)],
                rotation=45,
                ha="right",
            )
            plt.title("120 Draws Char Pool 6-Star Character Count Distribution")

            plt.xlabel("6-Star Character Count")
            plt.ylabel("Prob (%)")
            plt.grid(axis="y", alpha=0.75)
            plt.legend()
            plt.tight_layout()
            plt.show()

    def stats_weapon_draw(self, draw_times: int = 50000, gragh: bool = False):
        """统计8次武器池申领的6星武器数量及概率分布"""

        from tqdm import trange

        print(f"正在统计 8 次武器池申领获得的6星武器数量...")
        six_star_counts = []  # 记录每次8次申领获得的6星武器数量
        total_six_stars = 0
        star_counts = {4: 0, 5: 0, 6: 0}  # 记录不同星级武器的总数量

        for _ in trange(draw_times):
            gacha = WeaponGacha()
            round_six_stars = 0
            for _ in range(8):
                apply_result = gacha.apply_once()
                for result in apply_result:
                    star_counts[result.star] += 1  # 统计星级分布
                    if result.star == 6:
                        round_six_stars += 1  # 统计6星武器数量
            six_star_counts.append(round_six_stars)
            total_six_stars += round_six_stars

        # 计算平均获得的6星武器数量
        avg_six_stars = total_six_stars / draw_times
        colorprint(f"平均6星武器数量：{round(avg_six_stars, 2)}", Color.RED)

        # 计算不同星级武器的概率
        total_weapons = sum(star_counts.values())
        print("\nStar Distribution Probability:")
        for star in [4, 5, 6]:
            prob = star_counts[star] / total_weapons * 100
            color = (
                Color.PURPLE if star == 4 else Color.YELLOW if star == 5 else Color.RED
            )
            colorprint(f"{star}星武器：{prob:.2f}%", color)

        if gragh:
            import matplotlib.pyplot as plt
            import numpy as np

            # 添加正态分布曲线拟合
            from scipy import stats

            # 计算区间边界
            max_six_stars = max(six_star_counts)
            min_six_stars = min(six_star_counts)

            # 使用1个武器为固定区间
            bin_width = 1
            start_six_stars = min_six_stars
            bins = list[int](
                range(start_six_stars, max_six_stars + bin_width * 2, bin_width)
            )

            # 计算每个区间的出现次数和概率
            counts, _ = np.histogram(six_star_counts, bins=bins)
            probabilities = counts / draw_times * 100  # 转换为百分比

            # 生成区间标签
            bin_labels = [f"{bins[i]}" for i in range(len(bins) - 1)]

            # 打印每个区间的概率（只打印有概率的区间）
            print("\n6-Star Weapon Count Probability Distribution:")
            for label, prob in zip(bin_labels, probabilities):
                if prob > 0:
                    print(f"{label}: {prob:.2f}%")

            # 生成6星武器数量分布图
            plt.figure(figsize=(12, 6))
            plt.bar(
                range(len(bin_labels)),
                probabilities,
                color="skyblue",
                edgecolor="black",
                label="Actual Distribution",
            )

            # 计算数据的均值和标准差
            six_stars_mean = np.mean(six_star_counts)
            six_stars_std = np.std(six_star_counts)

            # 生成拟合曲线的数据点
            x = np.linspace(min(six_star_counts), max(six_star_counts), 100)
            # 修正缩放因子：概率密度 * 区间宽度 * 100 = 百分比
            y = stats.norm.pdf(x, six_stars_mean, six_stars_std) * bin_width * 100

            # 转换x轴坐标到条形图的索引范围
            x_norm = x - start_six_stars

            # 绘制拟合曲线
            plt.plot(
                x_norm,
                y,
                "r-",
                linewidth=2,
                label=f"Normal Fit (μ={six_stars_mean:.2f}, σ={six_stars_std:.2f})",
            )

            # 间隔显示xticks
            interval = max(1, len(bin_labels) // 10)  # 最多显示10个标签
            plt.xticks(
                range(0, len(bin_labels), interval),
                [bin_labels[i] for i in range(0, len(bin_labels), interval)],
                rotation=45,
                ha="right",
            )
            plt.title("8 Applications Weapon Pool 6-Star Weapon Count Distribution")

            plt.xlabel("6-Star Weapon Count")
            plt.ylabel("Prob (%)")
            plt.grid(axis="y", alpha=0.75)
            plt.legend()
            plt.tight_layout()
            plt.show()

    def stats_char_up_prob(
        self, test_times: int = 50000, gragh: bool = False, limit: int = 0
    ):
        """统计抽中UP角色所需的抽数"""

        assert limit >= 0, "limit参数必须为非负整数"

        from tqdm import trange

        print(f"正在统计抽中UP角色所需的抽数...")
        up_draw_counts = []  # 记录每次抽中UP角色所需的抽数

        for _ in trange(test_times):
            gacha = CharGacha()
            draw_count = 0
            # 获取6星UP角色列表
            up_char_names = gacha.star_up_prob[6][0]
            while True:
                draw_count += 1
                result = gacha.draw_once()
                # 检查是否抽中6星UP角色
                if result.star == 6 and result.name in up_char_names:
                    up_draw_counts.append(draw_count)
                    break

        # 处理limit参数
        if limit:
            # 截断一定抽以内的数据
            up_draw_counts = [count for count in up_draw_counts if count <= limit]
            print(f"\n已截断{limit}抽以内的数据，有效样本数：{len(up_draw_counts)}")

        # 计算平均抽数
        avg_draws = sum(up_draw_counts) / len(up_draw_counts)
        colorprint(f"平均抽中UP角色所需抽数：{round(avg_draws, 2)}", Color.RED)

        # 统计抽数的分布情况
        import numpy as np

        # 计算区间边界
        max_draws = max(up_draw_counts)
        min_draws = min(up_draw_counts)

        # 使用1抽为固定区间
        bin_width = 1
        start_draws = (min_draws // bin_width) * bin_width
        bins = list[int](range(start_draws, max_draws + bin_width * 2, bin_width))

        # 计算每个区间的出现次数和概率
        counts, _ = np.histogram(up_draw_counts, bins=bins)
        probabilities = (
            counts / len(up_draw_counts) * 100
        )  # 转换为百分比，基于有效样本数

        # 生成区间标签
        bin_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins) - 1)]

        # 打印每个区间的概率（只打印有概率的区间）
        print("\nUP Character Draw Count Probability Distribution：")
        for label, prob in zip(bin_labels, probabilities):
            if prob > 0:
                print(f"{label}: {prob:.2f}%")

        # 计算特定区间的概率
        print("\n特定区间概率分布：")
        intervals = [
            (1, 65, "提前金"),
            (66, 80, "小保底"),
            (81, 119, ""),
            (120, 120, "大保底"),
        ]
        for start, end, desc in intervals:
            if end > limit and limit > 0:
                continue
            count = sum(1 for x in up_draw_counts if start <= x <= end)
            prob = count / len(up_draw_counts) * 100
            if desc:
                print(f"{start}-{end}（{desc}）：{prob:.2f}%")
            else:
                print(f"{start}-{end}：{prob:.2f}%")

        if gragh:
            import matplotlib.pyplot as plt

            # 生成抽数分布图
            plt.figure(figsize=(12, 6))
            plt.bar(
                range(len(bin_labels)),
                probabilities,
                color="skyblue",
                edgecolor="black",
                label="Actual Distribution",
            )

            # 间隔显示xticks
            interval = max(1, len(bin_labels) // 10)  # 最多显示10个标签
            plt.xticks(
                range(0, len(bin_labels), interval),
                [bin_labels[i] for i in range(0, len(bin_labels), interval)],
                rotation=45,
                ha="right",
            )
            plt.title("UP Character Draw Count Distribution")

            plt.xlabel("Draw Count Range")
            plt.ylabel("Prob (%)")
            plt.grid(axis="y", alpha=0.75)
            plt.legend()
            plt.tight_layout()
            plt.show()

    def stats_weapon_up_prob(
        self, test_times: int = 50000, gragh: bool = False, limit: int = 0
    ):
        """统计抽中UP武器所需的抽数"""

        from tqdm import trange

        print(f"正在统计抽中UP武器所需的抽数...")
        up_draw_counts = []  # 记录每次抽中UP武器所需的抽数

        for _ in trange(test_times):
            gacha = WeaponGacha()
            draw_count = 0
            # 获取6星UP武器列表
            up_weapon_names = gacha.star_up_prob[6][0]
            while True:
                apply_result = gacha.apply_once()
                # 累加本次申领中的抽数（每次申领包含10抽）
                draw_count += len(apply_result)
                # 检查本次申领中是否有6星UP武器
                for result in apply_result:
                    if result.star == 6 and result.name in up_weapon_names:
                        up_draw_counts.append(draw_count)
                        break
                else:
                    # 本次申领中没有抽中UP武器，继续申领
                    continue
                # 抽中了UP武器，退出循环
                break

        # 处理limit参数
        if limit:
            # 截断一定抽以内的数据
            up_draw_counts = [count for count in up_draw_counts if count <= limit]
            print(f"\n已截断{limit}抽以内的数据，有效样本数：{len(up_draw_counts)}")

        # 计算平均抽数
        avg_draws = sum(up_draw_counts) / len(up_draw_counts)
        colorprint(f"平均抽中UP武器所需抽数：{round(avg_draws, 2)}", Color.RED)

        # 统计抽数的分布情况
        import numpy as np

        # 计算区间边界
        max_draws = max(up_draw_counts)
        min_draws = min(up_draw_counts)

        # 使用10抽为固定区间（因为武器池是10抽一申领）
        bin_width = 10
        start_draws = (min_draws // bin_width) * bin_width
        bins = list[int](range(start_draws, max_draws + bin_width * 2, bin_width))

        # 计算每个区间的出现次数和概率
        counts, _ = np.histogram(up_draw_counts, bins=bins)
        probabilities = (
            counts / len(up_draw_counts) * 100
        )  # 转换为百分比，基于有效样本数

        # 生成区间标签
        bin_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins) - 1)]

        # 打印每个区间的概率（只打印有概率的区间）
        print("\nUP Weapon Draw Count Probability Distribution：")
        for label, prob in zip(bin_labels, probabilities):
            if prob > 0:
                print(f"{label}: {prob:.2f}%")

        if gragh:
            import matplotlib.pyplot as plt

            # 生成抽数分布图
            plt.figure(figsize=(12, 6))
            plt.bar(
                range(len(bin_labels)),
                probabilities,
                color="skyblue",
                edgecolor="black",
                label="Actual Distribution",
            )

            # 间隔显示xticks
            interval = max(1, len(bin_labels) // 10)  # 最多显示10个标签
            plt.xticks(
                range(0, len(bin_labels), interval),
                [bin_labels[i] for i in range(0, len(bin_labels), interval)],
                rotation=45,
                ha="right",
            )
            plt.title("UP Weapon Draw Count Distribution")

            plt.xlabel("Draw Count Range")
            plt.ylabel("Prob (%)")
            plt.grid(axis="y", alpha=0.75)
            plt.legend()
            plt.tight_layout()
            plt.show()


# ===================== 主函数 =====================
if __name__ == "__main__":
    # 以下是测试工具代码，如需使用请取消注释
    tool = GachaTestTool()
    # 120保底抽法展示
    tool.demo_char_draw(120)
    tool.demo_weapon_apply(8)

    # 统计在一个角色池中，抽中UP角色时所需的抽数（送的10抽未使用，不计入）
    # 结论：平均抽中UP角色所需抽数为81.57抽（样本量100000）
    # 120大保底概率一骑绝尘！
    # 1-65（提前金）：22.70%
    # 66-80（小保底）：33.09% ~ 1/3
    # 81-119：10.08%
    # 120-120（大保底）：34.13% ~ 1/3
    # tool.stats_char_up_prob(20000, gragh=True)

    # 统计在一个武器池中，抽中UP武器时所需的抽数
    # 结论：平均抽中UP武器所需抽数为55.49抽（样本量100000）
    # 10-20: 9.62%
    # 20-30: 8.60%
    # 30-40: 7.72%
    # 40-50: 11.95%  *
    # 50-60: 7.12%
    # 60-70: 6.31%
    # 70-80: 5.71%
    # 80-90: 42.95%  *
    # tool.stats_weapon_up_prob(20000, gragh=True)

    # 截断尾端大保底数据，最多抽到小保底（80抽）查看期望抽数（送的10抽未使用，不计入）
    # 结论：平均抽中UP角色所需抽数为54.75抽（样本量100000）
    # tool.stats_char_up_prob(20000, gragh=True, limit=80)

    # 截断尾端大保底数据，最多抽到119抽查看期望抽数（送的10抽未使用，不计入）
    # 结论：平均抽中UP角色所需抽数为61.46抽（样本量100000）
    # tool.stats_char_up_prob(20000, gragh=True, limit=119)

    # 统计120次角色池申领配额数量（送的10抽未使用，不计入）
    # 结论：角色池的配额分布近似正态分布，均值为9405，标准差为1590（样本量100000）
    # tool.stats_char_quota(20000, gragh=True)

    # 统计8次武器池申领配额数量
    # 结论：武器池的配额分布近似正态分布，均值为391，标准差为71（样本量100000）
    # tool.stats_weapon_quota(20000, gragh=True)

    # 统计120抽角色池的角色数量及概率分布
    # 结论：120抽角色池的6星角色数量分布近似正态分布，均值为2.09，标准差为0.80（样本量100000）
    # 角色概率分布：
    # 4星：84.98%
    # 5星：13.27%
    # 6星：1.74% (UP = 0.87%)
    # tool.stats_char_draw(20000, gragh=True)

    # 统计8次武器池申领武器数量及概率分布
    # 结论：8次武器池的6星武器数量分布近似正态分布，均值为4.02，标准差为1.43（样本量100000）
    # 武器概率分布：
    # 4星：79.11%
    # 5星：15.87%
    # 6星：5.02% (UP = 1.255%)
    # tool.stats_weapon_draw(20000, gragh=True)
