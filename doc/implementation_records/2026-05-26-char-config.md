# 卡池配置重构记录

- 日期：2026-05-26
- 适用范围：角色池配置、武器池配置、配置加载器、评分标签来源、Web 卡池展示

## 本次变更

1. 角色池和武器池都改为强迁移，不再兼容旧 `char_pool.json` / `weapon_pool.json`。
2. 新增共享基础角色池：`configs/char_pool_base.json`。
3. 新增共享基础武器池：`configs/weapon_pool_base.json`。
4. 每个角色卡池新增 `config_*/char_banner.json`，显式声明：
   - `featured.current_up`
   - `featured.past_up`
   - `featured.normal`
   - `rates.up_6star_total_prob`
5. 每个配置目录新增 `config_*/weapon_banners.json`，一个配置可声明多个武器卡池；每个条目显式声明：
   - `id`
   - `featured.current_up`
   - `rates.up_6star_total_prob`
6. `GlobalConfigLoader.get_pool_data("char"|"weapon")` 只接受显式 banner 配置，并在运行时标准化为抽卡内核使用的池数据。
7. 旧 `config_*/char_pool.json` / `weapon_pool.json` 已移出运行时路径，仅保留在 `legacy/configs/` 归档。
8. `constants.json` 新增 `banner_defaults`，吸收 `base_profile`、默认 UP 总概率和空覆盖字段，减少每期 banner 重复。

## 迁移规则

- 共享 6 星常驻普通池、5 星池、4 星池抽出到 `char_pool_base.json`
- 每期 `current_up` 取自原 `gacha_rules.json.char.up_char_name`
- 每期 `past_up` 按当前业务事实显式填入两个往期角色
- `past_up` 仅作为评分标签，不参与当期 UP 概率
- 多个当期时，若未给单角色权重，运行时均分 `rates.up_6star_total_prob`
- `featured.current_up` 允许为空；为空时要求 `rates.up_6star_total_prob = 0`

## 影响

- `gacha_core/config.py`
  - `GlobalConfigLoader`
  - `CharGacha`
- `scheduler/workers.py`
- `scheduler/scoring.py`
- `server/routes.py`

## 明确决定

- 武器池配置已同步改为基础池 + 当期配置，不再读取旧 `weapon_pool.json`
- 角色池标签来源以 `char_banner.json` 为准，不再读取 `gacha_rules.json.char.up_char_name`
- 武器池名称与当前 UP 来源以 `weapon_banners.json` 中的活动条目为准，不再读取旧池文件
- 评分层优先使用显式 `current_up/past_up` 标签，`ScoringPreferences.past_up_character_names` 仅保留为补充名单
