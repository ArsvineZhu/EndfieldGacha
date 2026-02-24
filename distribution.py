from typing import List, Dict
from tqdm import trange
from core import WeaponGacha, CharGacha
from demo import Color


def color(star: int = 0) -> str:
    if star == 6:
        return Color.RED
    elif star == 5:
        return Color.YELLOW
    elif star == 4:
        return Color.PURPLE
    else:
        return Color.RESET


def distribute(
    gacha_type: str = "char", scale: int = 5, disable_guarantee: bool = True
) -> None:
    if gacha_type == "char":
        gacha = CharGacha(size=10240)
    elif gacha_type == "weapon":
        gacha = WeaponGacha(size=10240)
    else:
        raise ValueError("Invalid gacha type")

    scale = max(
        5, min(scale, 9)
    )  # Scale between 5 and 9 for reasonable results and acceptable runtime
    # Due to 10x attempts per arsenal issue, we set a lower scale for weapon gacha to keep consistent with char gacha
    if gacha_type == "weapon":
        scale -= 1
    scale = int(10**scale)

    counter: Dict[str, List[float]] = {}  # name -> [count, star]
    for _ in trange(scale):
        if gacha_type == "char":
            result = gacha.draw_once(disable_guarantee=disable_guarantee)
            counter[result.name] = [
                counter.get(result.name, [0, result.star])[0] + 1,
                result.star,
            ]
        elif gacha_type == "weapon":
            results = gacha.apply_once(disable_guarantee=disable_guarantee)
            for result in results:
                counter[result.name] = [
                    counter.get(result.name, [0, result.star])[0] + 0.1,
                    result.star,
                ]

    # Sort by star and then by count
    counter = dict(
        sorted(counter.items(), key=lambda item: (item[1][1], item[1][0]), reverse=True)
    )

    print("Gacha Results:")
    # Total prob of each star rarity
    total = sum(count[0] for count in counter.values())
    star_counts = {}
    for name, count in counter.items():
        star_counts[count[1]] = star_counts.get(count[1], 0) + count[0]

    for star, count in sorted(star_counts.items(), reverse=True):
        print(f"{color(star)}{star}★ : {count / total * 100:.2f}%{color()}")
    print("=" * 20)

    # Print individual character / weapon distribution
    for name, count in counter.items():
        print(f"{color(count[1])}{name}{color()}: {round(count[0]) / scale * 100:.2f}%")


def main():
    # Disable guarantee to see pure probabilities and distribution without pity system influence
    # Verify that the probabilities of character and weapon matches the
    # expected probabilities based on the defined rules and rates
    distribute("char", 7, disable_guarantee=True)
    distribute("weapon", 7, disable_guarantee=True)


if __name__ == "__main__":
    main()
