# -*- coding: utf-8 -*-
"""角色卡池演示与统计。"""

from gacha_core import CharGacha

from ._demo_ui import Color, colorprint


def demo_char_draw(config, width, draw_times: int = 5):
    """角色卡池抽卡示例"""
    title = "「熔火灼痕」寻访示例"
    print(f"\n{title.center(width['draw_num']+width['star']+width['quota']+20, '-')}")
    gacha = CharGacha(config)
    header = (
        f"{'寻访数':<{width['draw_num']}} | "
        f"{'星级':<{width['star']}} | "
        f"{'武库配额':<{width['quota']}}  | "
        f"名称"
    )
    print(header)
    print("-" * int(len(header) * 1.5))
    quota_sum = 0
    for i in range(draw_times):
        result = gacha.attempt()
        quota_sum += result.quota
        line = (
            f"{f'第{i+1}寻访':<{width['draw_num']}} | "
            f" {f'{result.star}星':<{width['star']}} | "
            f"{f'武库配额：{result.quota}':<{width['quota']}} | "
        )
        if result.star == 6:
            line += f"{Color.RED}{result.name}{Color.RESET}"
        elif result.star == 5:
            line += f"{Color.YELLOW}{result.name}{Color.RESET}"
        elif result.star == 4:
            line += f"{Color.PURPLE}{result.name}{Color.RESET}"
        else:
            line += f"{result.name}"
        if result.is_5_g:
            line += "【十连保底】"
        if result.is_6_g:
            line += "【非酋保底】"
        if result.is_up_g:
            line += "【UP保底】"
        print(line)

    rewards = gacha.get_accumulated_reward()
    rewards_str = "\n".join([f"{name}×{count}" for name, count in rewards]) if rewards else ""
    colorprint(
        "\n{}累计奖励：\n{}数量：{}\n{}".format(
            "「熔火灼痕」", "武库配额", quota_sum, rewards_str,
        ),
        Color.RED,
    )


def stats_char_quota(config, width, draw_times: int = 50000, gragh: bool = False, **_kw):
    """统计120抽角色池配额数量"""
    from tqdm import trange

    print("正在统计抽 120 次角色池获得的配额数量...")
    quota_list = []
    total_quota = 0
    for _ in trange(draw_times):
        gacha = CharGacha(config)
        round_quota = 0
        for _ in range(120):
            round_quota += gacha.attempt().quota
        quota_list.append(round_quota)
        total_quota += round_quota
    colorprint(f"平均配额：{round(total_quota / draw_times, 1)}", Color.RED)

    if gragh:
        import matplotlib.pyplot as plt
        import numpy as np
        from scipy import stats

        max_quota = max(quota_list)
        min_quota = min(quota_list)
        bin_width = 200
        start_quota = (min_quota // bin_width) * bin_width
        bins = list(range(start_quota, max_quota + bin_width * 2, bin_width))
        counts, _ = np.histogram(quota_list, bins=bins)
        probabilities = counts / draw_times * 100
        bin_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins) - 1)]
        print("\nQuota Range Probability Distribution：")
        for label, prob in zip(bin_labels, probabilities):
            if prob > 0:
                print(f"{label}: {prob:.2f}%")

        plt.figure(figsize=(12, 6))
        plt.bar(range(len(bin_labels)), probabilities, color="skyblue", edgecolor="black", label="Actual Distribution")
        quota_mean = np.mean(quota_list)
        quota_std = np.std(quota_list)
        x = np.linspace(min(quota_list), max(quota_list), 100)
        y = stats.norm.pdf(x, quota_mean, quota_std) * bin_width * 100
        x_norm = (x - start_quota) / bin_width
        plt.plot(x_norm, y, "r-", linewidth=2,
                 label=f"Normal Fit (μ={quota_mean:.0f}, σ={quota_std:.0f})")
        interval = max(1, len(bin_labels) // 10)
        tick_indices = range(0, len(bin_labels), interval)
        tick_labels = [bin_labels[i] for i in tick_indices]
        plt.xticks(tick_indices, tick_labels, rotation=45, ha="right")
        plt.title("120 Draws Char Pool Quota Distribution")
        plt.xlabel("Quota Range")
        plt.ylabel("Prob (%)")
        plt.grid(axis="y", alpha=0.75)
        plt.legend()
        plt.tight_layout()
        plt.show()


def stats_char_draw(config, draw_times: int = 50000, gragh: bool = False, **_kw):
    """统计120抽角色池的6星角色数量及概率分布"""
    from tqdm import trange

    print("正在统计抽 120 次角色池获得的6星角色数量...")
    six_star_counts = []
    total_six_stars = 0
    star_counts = {4: 0, 5: 0, 6: 0}
    for _ in trange(draw_times):
        gacha = CharGacha(config)
        round_six_stars = 0
        for _ in range(120):
            result = gacha.attempt()
            star_counts[result.star] += 1
            if result.star == 6:
                round_six_stars += 1
        six_star_counts.append(round_six_stars)
        total_six_stars += round_six_stars

    avg_six_stars = total_six_stars / draw_times
    colorprint(f"平均6星角色数量：{round(avg_six_stars, 2)}", Color.RED)
    total_chars = sum(star_counts.values())
    print("\nStar Distribution Probability:")
    for star in [4, 5, 6]:
        prob = star_counts[star] / total_chars * 100
        c = Color.PURPLE if star == 4 else Color.YELLOW if star == 5 else Color.RED
        colorprint(f"{star}星角色：{prob:.2f}%", c)

    if gragh:
        import matplotlib.pyplot as plt
        import numpy as np
        from scipy import stats

        max_six = max(six_star_counts)
        min_six = min(six_star_counts)
        bin_width = 1
        bins = list(range(min_six, max_six + bin_width * 2, bin_width))
        counts, _ = np.histogram(six_star_counts, bins=bins)
        probabilities = counts / draw_times * 100
        bin_labels = [f"{bins[i]}" for i in range(len(bins) - 1)]
        print("\n6-Star Character Count Probability Distribution:")
        for label, prob in zip(bin_labels, probabilities):
            if prob > 0:
                print(f"{label}: {prob:.2f}%")

        plt.figure(figsize=(12, 6))
        plt.bar(range(len(bin_labels)), probabilities, color="skyblue", edgecolor="black", label="Actual Distribution")
        six_mean = np.mean(six_star_counts)
        six_std = np.std(six_star_counts)
        x = np.linspace(min(six_star_counts), max(six_star_counts), 100)
        y = stats.norm.pdf(x, six_mean, six_std) * bin_width * 100
        plt.plot(x - min_six, y, "r-", linewidth=2,
                 label=f"Normal Fit (μ={six_mean:.2f}, σ={six_std:.2f})")
        interval = max(1, len(bin_labels) // 10)
        tick_indices = range(0, len(bin_labels), interval)
        tick_labels = [bin_labels[i] for i in tick_indices]
        plt.xticks(tick_indices, tick_labels, rotation=45, ha="right")
        plt.title("120 Draws Char Pool 6-Star Character Count Distribution")
        plt.xlabel("6-Star Character Count")
        plt.ylabel("Prob (%)")
        plt.grid(axis="y", alpha=0.75)
        plt.legend()
        plt.tight_layout()
        plt.show()


def stats_char_up_prob(config, test_times: int = 50000, gragh: bool = False, limit: int = 0, **_kw):
    """统计抽中UP角色所需的抽数"""
    from tqdm import trange

    print("正在统计抽中UP角色所需的抽数...")
    up_draw_counts = []
    for _ in trange(test_times):
        gacha = CharGacha(config)
        draw_count = 0
        up_char_names = gacha.star_up_prob[6][0]
        while True:
            draw_count += 1
            result = gacha.attempt()
            if result.star == 6 and result.name in up_char_names:
                up_draw_counts.append(draw_count)
                break

    if limit:
        up_draw_counts = [c for c in up_draw_counts if c <= limit]
        print(f"\n已截断{limit}抽以内的数据，有效样本数：{len(up_draw_counts)}")

    avg_draws = sum(up_draw_counts) / len(up_draw_counts)
    colorprint(f"平均抽中UP角色所需抽数：{round(avg_draws, 2)}", Color.RED)

    import numpy as np
    max_draws = max(up_draw_counts)
    min_draws = min(up_draw_counts)
    bin_width = 1
    start_draws = (min_draws // bin_width) * bin_width
    bins = list(range(start_draws, max_draws + bin_width * 2, bin_width))
    counts, _ = np.histogram(up_draw_counts, bins=bins)
    probabilities = counts / len(up_draw_counts) * 100
    bin_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins) - 1)]
    print("\nUP Character Draw Count Probability Distribution：")
    for label, prob in zip(bin_labels, probabilities):
        if prob > 0:
            print(f"{label}: {prob:.2f}%")

    print("\n特定区间概率分布：")
    intervals = [
        (1, 65, "提前金"), (66, 80, "小保底"), (81, 119, ""), (120, 120, "大保底"),
    ]
    for start, end, desc in intervals:
        if end > limit > 0:
            continue
        count = sum(1 for x in up_draw_counts if start <= x <= end)
        prob = count / len(up_draw_counts) * 100
        print(f"{start}-{end}（{desc}）：{prob:.2f}%" if desc else f"{start}-{end}：{prob:.2f}%")

    if gragh:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(12, 6))
        plt.bar(range(len(bin_labels)), probabilities, color="skyblue", edgecolor="black", label="Actual Distribution")
        interval = max(1, len(bin_labels) // 10)
        tick_indices = range(0, len(bin_labels), interval)
        tick_labels = [bin_labels[i] for i in tick_indices]
        plt.xticks(tick_indices, tick_labels, rotation=45, ha="right")
        plt.title("UP Character Draw Count Distribution")
        plt.xlabel("Draw Count Range")
        plt.ylabel("Prob (%)")
        plt.grid(axis="y", alpha=0.75)
        plt.legend()
        plt.tight_layout()
        plt.show()


def stats_char_potential(config, draw_times: int = 50000, gragh: bool = False, **_kw):
    """统计将指定角色满潜所需的抽数"""
    from tqdm import trange

    print("正在统计将指定角色满潜所需的抽数...")
    potential_draw_counts = []
    for _ in trange(draw_times):
        gacha = CharGacha(config)
        urgent_gacha = CharGacha(config)
        urgent_used = False
        draw_count = 0
        char_count = 0
        token_count = 0
        up_char_names = gacha.star_up_prob[6][0]

        while True:
            if char_count + token_count >= 6:
                potential_draw_counts.append(draw_count)
                break
            draw_count += 1
            result = gacha.attempt()
            if result.star == 6 and result.name in up_char_names:
                char_count += 1
            rewards = gacha.get_accumulated_reward()
            for reward in rewards:
                if reward[0].startswith("寻访情报书") and not urgent_used:
                    urgent_used = True
                    for _ in range(10):
                        r = urgent_gacha.attempt()
                        if r.star == 6 and r.name in up_char_names:
                            char_count += 1
                if reward[0].endswith("的信物"):
                    token_count = reward[1]

    avg_draws = sum(potential_draw_counts) / len(potential_draw_counts)
    colorprint(f"平均抽中UP角色满潜所需抽数：{round(avg_draws, 2)}", Color.RED)

    if gragh:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(12, 6))
        plt.hist(potential_draw_counts,
                 bins=range(0, max(potential_draw_counts) + 10, 10),
                 color="skyblue", edgecolor="black")
        plt.title("UP Character Potential Draw Count Distribution")
        plt.xlabel("Draw Count")
        plt.ylabel("Frequency")
        plt.grid(axis="y", alpha=0.75)
        plt.tight_layout()
        plt.show()
