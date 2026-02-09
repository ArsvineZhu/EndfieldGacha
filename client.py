from typing import List, Dict
import datetime
import json
import os
from core import CharGacha, WeaponGacha, GlobalConfigLoader
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import subprocess

VERSION = "1.0.0"
AUTHOR = "Arsvine"


class GachaClient:
    def __init__(
        self,
        chartered_permits=0,
        oroberyl=0,
        arsenal_tickets=0,
        origeometry=0,
        urgent_recruitment=0,
    ):
        # 初始化Rich控制台
        self.console = Console()
        self.chartered_permits = chartered_permits
        self.oroberyl = oroberyl
        self.arsenal_tickets = arsenal_tickets
        self.origeometry = origeometry
        self.urgent_recruitment = urgent_recruitment
        self.urgent_used = False
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
            "chartered_permit": "特许寻访凭证",
            "oroberyl": "嵌晶玉",
            "arsenal_ticket": "武库配额",
            "origeometry": "衍质源石",
            "urgent_recruitment": "加急招募",
        }
        self.width = {
            "resource_name": 10,
            "resource_value": 10,
            "menu_option": 5,
            "menu_description": 30,
        }
        # 创建卡池实例，在类中保持
        self.char_gacha = CharGacha()
        self.weapon_gacha = WeaponGacha()
        # 历史记录
        self.history: List[Dict] = []

    def clear_console(self):
        """清理控制台输出"""
        subprocess.run("cls" if os.name == "nt" else "clear", shell=True)

    def add_resources(
        self,
        chartered_permits=0,
        oroberyl=0,
        arsenal_tickets=0,
        origeometry=0,
        urgent_recruitment=0,
    ):
        """添加资源"""
        self.chartered_permits += chartered_permits
        self.oroberyl += oroberyl
        self.arsenal_tickets += arsenal_tickets
        self.origeometry += origeometry
        self.urgent_recruitment += urgent_recruitment
        if (
            chartered_permits > 0
            or oroberyl > 0
            or arsenal_tickets > 0
            or origeometry > 0
            or urgent_recruitment > 0
        ):
            self.console.print("资源数量变化：", style="bold green")
        if chartered_permits > 0:
            self.console.print(
                f"- [red]{self.text['chartered_permit']}[/red]: [green]+{chartered_permits}[/green]"
            )
        if oroberyl > 0:
            self.console.print(
                f"- [red]{self.text['oroberyl']}[/red]: [green]+{oroberyl}[/green]"
            )
        if arsenal_tickets > 0:
            self.console.print(
                f"- [red]{self.text['arsenal_ticket']}[/red]: [green]+{arsenal_tickets}[/green]"
            )
        if origeometry > 0:
            self.console.print(
                f"- [red]{self.text['origeometry']}[/red]: [green]+{origeometry}[/green]"
            )
        if urgent_recruitment > 0:
            self.console.print(
                f"- [red]{self.text['urgent_recruitment']}[/red]: [green]+{urgent_recruitment}[/green]"
            )

    def convert_origeometry(self, to_oroberyl=0, to_arsenal_tickets=0):
        """转换衍质源石"""
        required_origeometry = to_oroberyl + to_arsenal_tickets
        if required_origeometry > self.origeometry:
            self.console.print(
                f"衍质源石不足，当前拥有：{self.origeometry}，需要：{required_origeometry}",
                style="bold red",
            )
            return False

        self.origeometry -= required_origeometry
        self.oroberyl += to_oroberyl * 75
        self.arsenal_tickets += to_arsenal_tickets * 25

        self.console.print("转换完成：", style="bold green")
        if to_oroberyl > 0:
            self.console.print(
                f"- [white]{to_oroberyl}[/white] [red]{self.text['origeometry']}[/red] → [white]{to_oroberyl * 75}[/white] [red]{self.text['oroberyl']}[/red]"
            )
        if to_arsenal_tickets > 0:
            self.console.print(
                f"- [white]{to_arsenal_tickets}[/white] [red]{self.text['origeometry']}[/red] → [white]{to_arsenal_tickets * 25}[/white] [red]{self.text['arsenal_ticket']}[/red]"
            )
        return True

    def check_resources(self):
        """检查当前资源"""
        table = Table(title="当前资源", style="white")
        table.add_column("资源名称", style="white", justify="left")
        table.add_column("数量", style="green", justify="right")

        table.add_row(self.text["chartered_permit"], str(self.chartered_permits))
        table.add_row(self.text["oroberyl"], str(self.oroberyl))
        table.add_row(self.text["arsenal_ticket"], str(self.arsenal_tickets))
        table.add_row(self.text["origeometry"], str(self.origeometry))

        self.console.print(table)

    def can_afford_char_draw(self):
        """检查是否有足够资源进行角色池抽取"""
        return self.chartered_permits >= 1 or self.oroberyl >= 500

    def can_afford_weapon_draw(self):
        """检查是否有足够资源进行武器池抽取"""
        return self.arsenal_tickets >= 1980

    def display_result(self, result, is_weapon=False):
        """显示抽卡结果"""
        name = result.name
        star = result.star

        # 核心标色逻辑：6星红（优先）→ 5星黄 → 4星紫 → 默认色
        if star == 6:
            name_style = "bold red"
            star_style = "bold red"
        elif star == 5:
            name_style = "bold yellow"
            star_style = "bold yellow"
        elif star == 4:
            name_style = "bold purple"
            star_style = "bold purple"
        else:
            name_style = "bold white"
            star_style = "bold white"

        # 构建结果文本
        result_text = Text()
        result_text.append(f"[{star}星] ", style=star_style)
        result_text.append(name, style=name_style)

        # 触发保底时添加【保底】标注
        if result.is_5_g:
            result_text.append("【十连保底】", style="bold white")
        if result.is_6_g:
            result_text.append("【保底】", style="bold white")
        if result.is_up_g:
            result_text.append("【UP保底】", style="bold white")

        self.console.print(result_text)

    def draw_char_once(self):
        """角色池单抽"""
        if not self.can_afford_char_draw():
            self.console.print("资源不足，无法进行角色池抽取！", style="bold red")
            self.console.print("当前拥有：", style="bold yellow")
            self.console.print(
                f"- [red]{self.text['chartered_permit']}[/red]: {self.chartered_permits}"
            )
            self.console.print(f"- [red]{self.text['oroberyl']}[/red]: {self.oroberyl}")
            self.console.print(
                f"所需：1 [red]{self.text['chartered_permit']}[/red] 或 500 [red]{self.text['oroberyl']}[/red]",
                style="bold white",
            )
            return False

        # 优先消耗特许寻访凭证
        if self.chartered_permits >= 1:
            self.chartered_permits -= 1
            cost_type = self.text["chartered_permit"]
            cost_amount = 1
        else:
            self.oroberyl -= 500
            cost_type = self.text["oroberyl"]
            cost_amount = 500

        self.console.print(
            f"消耗：{cost_amount} [red]{cost_type}[/red]", style="bold white"
        )

        # 执行抽卡
        result = self.char_gacha.draw_once()

        # 显示结果
        self.console.print(f"\n{self.text['char_pool']}抽取结果：", style="bold green")
        self.display_result(result)

        # 配额提示与处理
        self.console.print(
            f"\n获得配额：[white]{result.quota}[/white]", style="bold green"
        )
        self.arsenal_tickets += result.quota

        # 显示累计奖励
        rewards = self.char_gacha.get_accumulated_reward()
        if rewards:
            self.console.print("累计奖励：", style="bold green")
            for name, count in rewards:
                if name == self.text["urgent_recruitment"]:
                    if self.urgent_used:
                        self.console.print(f"- [red]{name}[/red][white]（已使用）[/white]")
                        continue
                    else:
                        self.urgent_used = True
                        self.urgent_recruitment += 1
                self.console.print(f"- [red]{name}[/red]×[white]{count}[/white]")

        # 记录历史
        cost = {}
        if cost_type == self.text["chartered_permit"]:
            cost[cost_type] = cost_amount
        else:
            cost[cost_type] = cost_amount
        self.record_history("character", "single", [result], cost)

        return True

    def draw_char_ten(self):
        """角色池10连抽"""

        results = []
        total_cost_permits = 0
        total_cost_oroberyl = 0

        for i in range(10):
            if not self.can_afford_char_draw():
                self.console.print("资源不足，无法完成10连抽！", style="bold red")
                # 恢复已消耗的资源
                self.chartered_permits += total_cost_permits
                self.oroberyl += total_cost_oroberyl
                return False

            # 优先消耗特许寻访凭证
            if self.chartered_permits >= 1:
                self.chartered_permits -= 1
                total_cost_permits += 1
            else:
                self.oroberyl -= 500
                total_cost_oroberyl += 500

            # 执行抽卡
            result = self.char_gacha.draw_once()
            results.append(result)

        # 显示消耗
        self.console.print("消耗：", style="bold yellow")
        if total_cost_permits > 0:
            self.console.print(
                f"- [red]{self.text['chartered_permit']}[/red]: [white]{total_cost_permits}[/white]"
            )
        if total_cost_oroberyl > 0:
            self.console.print(
                f"- [red]{self.text['oroberyl']}[/red]: [white]{total_cost_oroberyl}[/white]"
            )

        # 显示结果
        self.console.print(
            f"\n{self.text['char_pool']}10连抽结果：", style="bold green"
        )
        quota_sum = 0
        for i, result in enumerate(results, 1):
            self.console.print(f"第{i}抽：", end="", style="white")
            self.display_result(result)
            quota_sum += result.quota

        # 配额提示与处理
        self.console.print(
            f"\n获得配额：[white]{quota_sum}[/white]", style="bold green"
        )
        self.arsenal_tickets += quota_sum

        # 显示累计奖励
        rewards = self.char_gacha.get_accumulated_reward()
        if rewards:
            self.console.print("\n累计奖励：", style="bold green")
            for name, count in rewards:
                if name == self.text["urgent_recruitment"]:
                    if self.urgent_used:
                        self.console.print(f"- [red]{name}[/red][white]（已使用）[/white]")
                        continue
                    else:
                        self.urgent_used = True
                        self.urgent_recruitment += 1
                self.console.print(f"- [red]{name}[/red]×[white]{count}[/white]")

        # 记录历史
        cost = {}
        if total_cost_permits > 0:
            cost[self.text["chartered_permit"]] = total_cost_permits
        if total_cost_oroberyl > 0:
            cost[self.text["oroberyl"]] = total_cost_oroberyl
        self.record_history("character", "ten", results, cost)

        return True

    def draw_urgent_recruitment(self):
        """加急招募10连抽"""
        if self.urgent_recruitment < 1:
            self.console.print("加急招募不足，无法进行加急招募抽卡！", style="bold red")
            return False

        # 消耗1个加急招募
        self.urgent_recruitment -= 1
        self.console.print(
            f"消耗：[white]1[/white] [red]{self.text['urgent_recruitment']}[/red]",
            style="bold yellow",
        )

        # 创建新的CharGacha实例（不计入先前卡池的保底计数）
        urgent_gacha = CharGacha()

        # 执行10连抽
        results = []
        quota_sum = 0

        for i in range(10):
            result = urgent_gacha.draw_once()
            results.append(result)
            quota_sum += result.quota

        # 显示结果
        self.console.print(f"\n加急招募结果：", style="bold green")
        for i, result in enumerate(results, 1):
            self.console.print(f"第{i}抽：", end="", style="white")
            self.display_result(result)

        # 配额提示与处理
        self.console.print(
            f"\n获得配额：[white]{quota_sum}[/white]", style="bold green"
        )
        self.arsenal_tickets += quota_sum

        # 记录历史
        cost = {self.text["urgent_recruitment"]: 1}
        self.record_history("character", "urgent", results, cost)

        return True

    def draw_weapon_ten(self):
        """武器池10连抽"""
        if not self.can_afford_weapon_draw():
            self.console.print("资源不足，无法进行武器池抽取！", style="bold red")
            self.console.print("当前拥有：", style="bold yellow")
            self.console.print(
                f"- [red]{self.text['arsenal_ticket']}[/red]: {self.arsenal_tickets}"
            )
            self.console.print(
                f"所需：1980 [red]{self.text['arsenal_ticket']}[/red]",
                style="bold yellow",
            )
            return False

        # 消耗武库配额
        self.arsenal_tickets -= 1980
        self.console.print(
            f"消耗：[white]1980[/white] [red]{self.text['arsenal_ticket']}[/red]",
            style="bold yellow",
        )

        # 执行抽卡
        results = self.weapon_gacha.apply_once()

        # 显示结果
        self.console.print(
            f"\n{self.text['weapon_pool']}10连抽结果：", style="bold green"
        )
        for i, result in enumerate(results, 1):
            self.console.print(f"第{i}抽：", end="", style="bold white")
            self.display_result(result, is_weapon=True)

        # 显示累计奖励
        rewards = self.weapon_gacha.get_accumulated_reward()
        if rewards:
            self.console.print("\n累计奖励：", style="bold green")
            for name, count in rewards:
                self.console.print(f"- [red]{name}[/red]×[white]{count}[/white]")

        # 记录历史
        cost = {self.text["arsenal_ticket"]: 1980}
        self.record_history("weapon", "ten", results, cost)

        return True

    def get_user_input(self, prompt, input_type="int", min_value=None, max_value=None):
        """获取用户输入"""
        while True:
            try:
                user_input = self.console.input(f"{prompt}")
                if input_type == "int":
                    value = int(user_input)
                    if min_value is not None and value < min_value:
                        self.console.print(
                            f"输入值不能小于{min_value}", style="bold red"
                        )
                        continue
                    if max_value is not None and value > max_value:
                        self.console.print(
                            f"输入值不能大于{max_value}", style="bold red"
                        )
                        continue
                    return value
                elif input_type == "float":
                    return float(user_input)
                else:
                    return user_input
            except ValueError:
                self.console.print("输入格式错误，请重新输入！", style="bold red")
            except KeyboardInterrupt:
                self.console.print("\n操作取消", style="bold yellow")
                return None

    def display_menu(self):
        """显示主菜单"""
        # 打印标题面板
        title_panel = Panel(
            f"Endfield Gacha Client 控制台应用 - {VERSION} - {AUTHOR}",
            title="Endfield Gacha Client 控制台",
            title_align="center",
            border_style="bold white",
        )
        self.console.print(title_panel)

        # 创建并显示菜单表格
        menu_table = Table(style="white")
        menu_table.add_column("选项", style="red", justify="center", width=5)
        menu_table.add_column("功能", style="green", justify="left", width=20)
        menu_table.add_column("描述", style="white", justify="left", width=40)

        menu_items = [
            (1, "添加资源", "手动添加各种资源"),
            (2, "转换资源", "将衍质源石转换为其他资源"),
            (
                3,
                "角色池单抽",
                f"消耗1张{self.text['chartered_permit']}或500个{self.text['oroberyl']}",
            ),
            (
                4,
                "角色池10连",
                f"消耗10张{self.text['chartered_permit']}或5000个{self.text['oroberyl']}",
            ),
            (5, "武器池10连", f"消耗1980个{self.text['arsenal_ticket']}"),
            (6, "查看抽卡历史", "查看所有抽卡记录，支持保存"),
            (0, "退出", "退出控制台应用"),
        ]

        for item in menu_items:
            option, title, desc = item
            menu_table.add_row(str(option), title, desc)

        self.console.print(menu_table)
        self.console.print()

        # 创建并显示资源信息表格
        resource_table = Table(title="当前资源", style="white")
        resource_table.add_column("资源名称", style="white", justify="left", width=30)
        resource_table.add_column("数量", style="green", justify="right", width=30)

        resource_table.add_row(
            self.text["chartered_permit"], str(self.chartered_permits)
        )
        resource_table.add_row(self.text["oroberyl"], str(self.oroberyl))
        resource_table.add_row(self.text["arsenal_ticket"], str(self.arsenal_tickets))
        resource_table.add_row(self.text["origeometry"], str(self.origeometry))
        resource_table.add_row(
            self.text["urgent_recruitment"], str(self.urgent_recruitment)
        )

        self.console.print(resource_table)
        self.console.print()

        # 创建并显示卡池信息表格
        pool_table = Table(title="卡池信息", style="white")
        pool_table.add_column("卡池名称", style="white", justify="left", width=30)
        pool_table.add_column("抽取次数", style="blue", justify="right", width=30)

        pool_table.add_row(self.text["char_pool"], str(self.char_gacha.total_draws))
        pool_table.add_row(self.text["weapon_pool"], str(self.weapon_gacha.total_apply))

        self.console.print(pool_table)
        self.console.print()

    def record_history(self, pool_type: str, draw_type: str, results: List, cost: Dict):
        """记录抽卡历史"""
        history_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "pool_type": pool_type,  # "character" 或 "weapon"
            "draw_type": draw_type,  # "single" 或 "ten"
            "cost": cost,
            "results": [
                {
                    "name": result.name,
                    "star": result.star,
                    "is_up_g": result.is_up_g,
                    "is_5_g": result.is_5_g,
                    "is_6_g": result.is_6_g,
                }
                for result in results
            ],
        }
        self.history.append(history_entry)

    def view_history(self):
        """查看抽卡历史"""
        if not self.history:
            self.console.print("暂无抽卡历史记录", style="bold yellow")
            return

        # 创建历史记录面板
        panel = Panel(
            "历史抽卡记录",
            title="历史记录",
            title_align="center",
            border_style="bold blue",
        )
        self.console.print(panel)

        for i, entry in enumerate(self.history, 1):
            timestamp = entry["timestamp"]
            pool_type = "角色池" if entry["pool_type"] == "character" else "武器池"
            draw_type = "单抽" if entry["draw_type"] == "single" else "10连抽"

            # 创建单次抽卡记录的表格
            entry_table = Table(style="white")
            entry_table.add_column("信息", style="bold green", justify="left")
            entry_table.add_column("详情", style="bold white", justify="left")

            entry_table.add_row("序号", str(i))
            entry_table.add_row("时间", timestamp)
            entry_table.add_row("卡池类型", f"[yellow]{pool_type}[/yellow]")
            entry_table.add_row("抽卡方式", draw_type)

            # 添加消耗信息
            cost_str = "\n".join(
                [
                    f"[bold red]{item}[/bold red]: {amount}"
                    for item, amount in entry["cost"].items()
                ]
            )
            entry_table.add_row("消耗", cost_str)

            self.console.print(entry_table)

            # 显示抽卡结果
            for result in entry["results"]:
                star = result["star"]
                name = result["name"]
                guarantees = []
                if result["is_up_g"]:
                    guarantees.append("UP保底")
                if result["is_5_g"]:
                    guarantees.append("十连保底")
                if result["is_6_g"]:
                    guarantees.append("保底")

                # 标色显示
                if star == 6:
                    name_style = "bold red"
                    star_style = "bold red"
                elif star == 5:
                    name_style = "bold yellow"
                    star_style = "bold yellow"
                elif star == 4:
                    name_style = "bold purple"
                    star_style = "bold purple"
                else:
                    name_style = "bold white"
                    star_style = "bold white"

                # 构建结果文本
                result_text = Text()
                result_text.append(f"  [{star}星] ", style=star_style)
                result_text.append(name, style=name_style)
                if guarantees:
                    result_text.append(
                        f" 【{' '.join(guarantees)}】", style="bold white"
                    )

                self.console.print(result_text)

            self.console.print("-" * 60, style="white")

    def save_history(self, filename: str = "gacha_history"):
        """保存抽卡历史到文件"""
        if not self.history:
            self.console.print("暂无抽卡历史记录，无需保存", style="bold yellow")
            return False

        filename += "_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            self.console.print(
                f"抽卡历史已保存到 [green]{filename}[/green]", style="bold green"
            )
            return True
        except Exception as e:
            self.console.print(
                f"保存抽卡历史失败：[red]{str(e)}[/red]", style="bold red"
            )
            return False

    def run(self):
        """运行控制台应用"""
        # 欢迎信息
        welcome_panel = Panel(
            "本应用模拟真实的抽卡体验，包含角色池和武器池。\n\n- 角色池：使用特许寻访凭证或嵌晶玉进行抽取\n- 武器池：使用武库配额进行抽取\n- 支持资源转换和历史记录查看",
            title="Endfield Gacha Client 控制台应用",
            title_align="center",
            border_style="bold green",
        )
        self.console.print(welcome_panel)

        self.console.input("[white]\n按回车键开始...[/white]")
        self.clear_console()

        while True:
            self.display_menu()
            choice = self.get_user_input(
                "[bold white]请选择操作 (0-6)：[/bold white]", "int", 0, 6
            )

            if choice is None:
                self.clear_console()
                continue

            if choice == 1:
                # 添加资源
                self.console.print("\n添加资源：", style="bold green")
                chartered_permits = self.get_user_input(
                    f"{self.text['chartered_permit']}：", "int", 0
                )
                oroberyl = self.get_user_input(f"{self.text['oroberyl']}：", "int", 0)
                arsenal_tickets = self.get_user_input(
                    f"{self.text['arsenal_ticket']}：", "int", 0
                )
                origeometry = self.get_user_input(
                    f"{self.text['origeometry']}：", "int", 0
                )
                urgent_recruitment = self.get_user_input(
                    f"{self.text['urgent_recruitment']}：", "int", 0
                )
                self.add_resources(
                    chartered_permits,
                    oroberyl,
                    arsenal_tickets,
                    origeometry,
                    urgent_recruitment,
                )
            elif choice == 2:
                # 转换资源
                self.console.print("\n转换衍质源石：", style="bold yellow")
                self.console.print(
                    f"当前拥有：[red]{self.origeometry} {self.text['origeometry']}[/red]",
                    style="white",
                )
                self.console.print("转换比例：", style="bold yellow")
                self.console.print(
                    f"1 [red]{self.text['origeometry']}[/red] = [bold white]75[/bold white] [red]{self.text['oroberyl']}[/red]"
                )
                self.console.print(
                    f"1 [red]{self.text['origeometry']}[/red] = [bold white]25[/bold white] [red]{self.text['arsenal_ticket']}[/red]"
                )

                to_oroberyl = self.get_user_input(
                    f"转换为[red]{self.text['oroberyl']}[/red]的数量：", "int", 0
                )
                to_arsenal_tickets = self.get_user_input(
                    f"转换为[red]{self.text['arsenal_ticket']}[/red]的数量：", "int", 0
                )

                if to_oroberyl > 0 or to_arsenal_tickets > 0:
                    self.convert_origeometry(to_oroberyl, to_arsenal_tickets)
            elif choice == 3:
                if self.urgent_recruitment > 0:
                    # 提示用户是否使用加急招募
                    use_urgent = self.console.input(
                        f"您拥有[red]{self.text['urgent_recruitment']}[/red]，是否使用加急招募进行10连抽？(y/n)："
                    ).lower()
                    if use_urgent == "y":
                        self.draw_urgent_recruitment()
                else:
                    # 角色池单抽
                    self.draw_char_once()
                    self.check_resources()
            elif choice == 4:
                if self.urgent_recruitment > 0:
                    # 提示用户是否使用加急招募
                    use_urgent = self.console.input(
                        f"您拥有[red]{self.text['urgent_recruitment']}[/red]，是否使用加急招募进行10连抽？(y/n)："
                    ).lower()
                    if use_urgent == "y":
                        self.draw_urgent_recruitment()
                else:
                    # 角色池10连
                    self.draw_char_ten()
                    self.check_resources()
            elif choice == 5:
                # 武器池10连
                self.draw_weapon_ten()
                self.check_resources()
            elif choice == 6:
                # 查看抽卡历史
                self.clear_console()
                self.view_history()
                # 询问是否保存
                save_choice = self.console.input(
                    "[bold white]\n是否保存抽卡历史到文件？(y/n)：[/bold white]"
                ).lower()
                if save_choice == "y":
                    filename = (
                        self.console.input(
                            "[bold white]请输入保存文件名（默认：gacha_history）：[/bold white]"
                        )
                        or "gacha_history"
                    )
                    self.save_history(filename)
            elif choice == 0:
                # 退出
                exit_panel = Panel(
                    "感谢使用 Endfield Gacha Client 控制台应用",
                    title="Endfield Gacha Client",
                    title_align="center",
                    border_style="bold white",
                )
                self.console.print(exit_panel)
                break

            self.console.input("[white]\n按回车键继续...[/white]")
            self.clear_console()


if __name__ == "__main__":
    # 创建GachaClient实例并运行
    client = GachaClient(
        chartered_permits=11, oroberyl=41180, arsenal_tickets=3280, origeometry=78
    )  # 26.2.9 我大保底42之后攒到现在的全部家产
    client.run()
