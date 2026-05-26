# -*- coding: utf-8 -*-
"""武器卡池演示与统计。"""

from gacha_core import WeaponGacha

from ._demo_ui import Color, colorprint


def demo_weapon_apply(config, width, apply_times: int = 1):
    """武器卡池申领示例"""
    title = "「熔铸申领」申领示例"
    print(f"\n{title.center(width['draw_num']+width['star']+width['quota']+40, '-')}")

    gacha = WeaponGacha(config)
    quota_sum = 0
    for apply_idx in range(apply_times):
        print(f"\n【第{apply_idx+1}次申领】")
        apply_result = gacha.attempt()
        header = (
            f"{'抽数':<{width['draw_num']}} | "
            f"{'星级':<{width['star']}} | "
            f"{'集成配额':<{width['quota']}}  | "
            f"名称"
        )
        print(header)
        print("-" * len(header) * 2)
        for idx, result in enumerate(apply_result):
            quota_sum += result.quota
            line = (
                f"{f'第{idx+1}抽':<{width['draw_num']}} | "
                f" {f'{result.star}星':<{width['star']}} | "
                f"{f'集成配额：{result.quota}':<{width['quota']}} | "
            )
            if result.star == 6:
                line += f"{Color.RED}{result.name}{Color.RESET}"
            elif result.star == 5:
                line += f"{Color.YELLOW}{result.name}{Color.RESET}"
            else:
                line += f"{result.name}"
            if result.is_6_g:
                line += "【保底】"
            if result.is_5_g:
                line += "【十连保底】"
            if result.is_up_g:
                line += "【UP保底】"
            print(line)

    rewards = gacha.get_accumulated_reward()
    rewards_str = "\n".join([f"{name}×{count}" for name, count in rewards]) if rewards else ""
    colorprint(
        "\n{}累计奖励：\n{}数量：{}\n{}".format("「熔铸申领」", "集成配额", quota_sum, rewards_str),
        Color.RED,
    )


def stats_weapon_quota(config, draw_times: int = 50000, gragh: bool = False, **_kw):
    """统计8次武器池申领配额数量"""
    from tqdm import trange

    print("正在统计 8 次武器池申领获得的配额数量...")
    quota_list = []
    total_quota = 0
    for _ in trange(draw_times):
        gacha = WeaponGacha(config)
        round_quota = 0
        for _ in range(8):
            for result in gacha.attempt():
                round_quota += result.quota
        quota_list.append(round_quota)
        total_quota += round_quota
    colorprint(f"平均配额：{round(total_quota / draw_times, 1)}", Color.RED)

    if gragh:
        import matplotlib.pyplot as plt
        import numpy as np
        from scipy import stats

        max_quota = max(quota_list)
        min_quota = min(quota_list)
        bin_width = 25
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
        plt.title("8 Applications Weapon Pool Quota Distribution")
        plt.xlabel("Quota Range")
        plt.ylabel("Prob (%)")
        plt.grid(axis="y", alpha=0.75)
        plt.legend()
        plt.tight_layout()
        plt.show()


def stats_weapon_draw(config, draw_times: int = 50000, gragh: bool = False, **_kw):
    """统计8次武器池申领的6星武器数量及概率分布"""
    from tqdm import trange

    print("正在统计 8 次武器池申领获得的6星武器数量...")
    six_star_counts = []
    total_six_stars = 0
    star_counts = {4: 0, 5: 0, 6: 0}
    for _ in trange(draw_times):
        gacha = WeaponGacha(config)
        round_six_stars = 0
        for _ in range(8):
            for result in gacha.attempt():
                star_counts[result.star] += 1
                if result.star == 6:
                    round_six_stars += 1
        six_star_counts.append(round_six_stars)
        total_six_stars += round_six_stars

    avg = total_six_stars / draw_times
    colorprint(f"平均6星武器数量：{round(avg, 2)}", Color.RED)
    total_weapons = sum(star_counts.values())
    print("\nStar Distribution Probability:")
    for star in [4, 5, 6]:
        prob = star_counts[star] / total_weapons * 100
        c = Color.PURPLE if star == 4 else Color.YELLOW if star == 5 else Color.RED
        colorprint(f"{star}星武器：{prob:.2f}%", c)

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
        print("\n6-Star Weapon Count Probability Distribution:")
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
        plt.title("8 Applications Weapon Pool 6-Star Weapon Count Distribution")
        plt.xlabel("6-Star Weapon Count")
        plt.ylabel("Prob (%)")
        plt.grid(axis="y", alpha=0.75)
        plt.legend()
        plt.tight_layout()
        plt.show()


def stats_weapon_up_prob(config, test_times: int = 50000, gragh: bool = False, limit: int = 0, **_kw):
    """统计抽中UP武器所需的抽数"""
    from tqdm import trange

    print("正在统计抽中UP武器所需的抽数...")
    up_draw_counts = []
    for _ in trange(test_times):
        gacha = WeaponGacha(config)
        draw_count = 0
        up_weapon_names = gacha.star_up_prob[6][0]
        while True:
            apply_result = gacha.attempt()
            draw_count += len(apply_result)
            for result in apply_result:
                if result.star == 6 and result.name in up_weapon_names:
                    up_draw_counts.append(draw_count)
                    break
            else:
                continue
            break

    if limit:
        up_draw_counts = [c for c in up_draw_counts if c <= limit]
        print(f"\n已截断{limit}抽以内的数据，有效样本数：{len(up_draw_counts)}")

    avg_draws = sum(up_draw_counts) / len(up_draw_counts)
    colorprint(f"平均抽中UP武器所需抽数：{round(avg_draws, 2)}", Color.RED)

    import numpy as np
    max_draws = max(up_draw_counts)
    min_draws = min(up_draw_counts)
    bin_width = 10
    start_draws = (min_draws // bin_width) * bin_width
    bins = list(range(start_draws, max_draws + bin_width * 2, bin_width))
    counts, _ = np.histogram(up_draw_counts, bins=bins)
    probabilities = counts / len(up_draw_counts) * 100
    bin_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins) - 1)]
    print("\nUP Weapon Draw Count Probability Distribution：")
    for label, prob in zip(bin_labels, probabilities):
        if prob > 0:
            print(f"{label}: {prob:.2f}%")

    if gragh:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(12, 6))
        plt.bar(range(len(bin_labels)), probabilities, color="skyblue", edgecolor="black", label="Actual Distribution")
        interval = max(1, len(bin_labels) // 10)
        tick_indices = range(0, len(bin_labels), interval)
        tick_labels = [bin_labels[i] for i in tick_indices]
        plt.xticks(tick_indices, tick_labels, rotation=45, ha="right")
        plt.title("UP Weapon Draw Count Distribution")
        plt.xlabel("Draw Count Range")
        plt.ylabel("Prob (%)")
        plt.grid(axis="y", alpha=0.75)
        plt.legend()
        plt.tight_layout()
        plt.show()


def stats_urgent_quota(config, draw_times: int = 50000, gragh: bool = False, **_kw):
    """统计加急招募10连抽获得的武库配额数量分布"""
    from tqdm import trange

    from gacha_core import CharGacha

    print("正在统计加急招募10连抽获得的武库配额数量...")
    quota_list = []
    total_quota = 0
    for _ in trange(draw_times):
        urgent_gacha = CharGacha(config)
        round_quota = 0
        for _ in range(10):
            round_quota += urgent_gacha.attempt().quota
        quota_list.append(round_quota)
        total_quota += round_quota
    colorprint(f"平均配额：{round(total_quota / draw_times, 1)}", Color.RED)

    if gragh:
        import matplotlib.pyplot as plt
        import numpy as np

        max_quota = max(quota_list)
        min_quota = min(quota_list)
        bin_width = 100
        start_quota = (min_quota // bin_width) * bin_width
        bins = list(range(start_quota, max_quota + bin_width * 2, bin_width))
        counts, _ = np.histogram(quota_list, bins=bins)
        probabilities = counts / draw_times * 100
        bin_labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins) - 1)]
        print("\nQuota Distribution Probability：")
        for label, prob in zip(bin_labels, probabilities):
            if prob > 0:
                print(f"{label}: {prob:.2f}%")

        plt.figure(figsize=(12, 6))
        plt.bar(range(len(bin_labels)), probabilities, color="skyblue", edgecolor="black", label="Actual Distribution")
        interval = max(1, len(bin_labels) // 10)
        tick_indices = range(0, len(bin_labels), interval)
        tick_labels = [bin_labels[i] for i in tick_indices]
        plt.xticks(tick_indices, tick_labels, rotation=45, ha="right")
        plt.title("Urgent Recruitment Quota Distribution")
        plt.xlabel("Quota Range")
        plt.ylabel("Prob (%)")
        plt.grid(axis="y", alpha=0.75)
        plt.legend()
        plt.tight_layout()
        plt.show()
