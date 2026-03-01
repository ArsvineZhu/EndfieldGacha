from flask import Flask, render_template, request, jsonify, session
import json
import os
import hashlib
from core import CharGacha, WeaponGacha

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.secret_key = 'endfield_gacha_secret_key_Arsvine_20260228'

# 用户数据存储文件夹路径
USER_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'users')

# 确保用户数据文件夹存在
os.makedirs(USER_DATA_FOLDER, exist_ok=True)

# 获取用户 IP 地址
def get_user_ip():
    """获取用户的真实 IP 地址"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

# 生成用户唯一标识
def generate_user_id(ip_address, user_agent=None):
    """基于 IP 地址和 User-Agent 生成用户唯一标识"""
    identifier = f"{ip_address}:{user_agent or ''}"
    return hashlib.md5(identifier.encode('utf-8')).hexdigest()

# 获取用户文件路径
def get_user_file_path(user_id):
    """获取用户数据文件路径"""
    return os.path.join(USER_DATA_FOLDER, f"{user_id}.json")

# 加载用户数据
def load_user(user_id):
    """加载指定用户的数据"""
    user_file = get_user_file_path(user_id)
    if os.path.exists(user_file):
        with open(user_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# 保存用户数据
def save_user(user_id, user_data):
    """保存用户数据"""
    user_file = get_user_file_path(user_id)
    with open(user_file, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

# 创建新用户
def create_new_user(user_id):
    """创建新的用户数据"""
    return {
        'user_id': user_id,
        'created_at': __import__('datetime').datetime.now().isoformat(),
        'last_visit': __import__('datetime').datetime.now().isoformat(),
        'char_gacha': {
            'total_draws': 0,
            'no_6star_draw': 0,
            'no_5star_plus_draw': 0,
            'no_up_draw': 0,
            'up_guarantee_used': False,
            'history': []
        },
        'weapon_gacha': {
            'total_draws': 0,
            'total_apply': 0,
            'no_6star_apply': 0,
            'no_up_apply': 0,
            'up_guarantee_used': False,
            'history': []
        },
        'collection': {
            'chars': {},
            'weapons': {}
        },
        'resources': {
            'urgent_recruitment': 0,
            'urgent_used': False,
            'chartered_permits': 10,
            'oroberyl': 50000,
            'arsenal_tickets': 8000,
            'origeometry': 100,
            'total_recharge': 0,
            'first_recharge': {
                '6': True,
                '30': True,
                '98': True,
                '198': True,
                '328': True,
                '648': True
            }
        }
    }

# 获取或创建当前用户
def get_or_create_current_user():
    """获取或创建当前用户"""
    user_id = generate_user_id(get_user_ip(), request.headers.get('User-Agent'))
    user_data = load_user(user_id)
    
    if user_data is None:
        user_data = create_new_user(user_id)
        save_user(user_id, user_data)
    
    return user_id, user_data

# 主页
@app.route('/')
def index():
    # 自动获取或创建用户数据
    user_id, user_data = get_or_create_current_user()
    # 更新最后访问时间
    user_data['last_visit'] = __import__('datetime').datetime.now().isoformat()
    save_user(user_id, user_data)
    
    # 将用户ID存储在session中（可选，用于后续请求识别）
    session['user_id'] = user_id
    
    return render_template('index.html')

# 抽卡 API
@app.route('/api/gacha', methods=['POST'])
def gacha():
    data = request.json
    pool_type = data.get('pool_type')
    count = data.get('count', 1)
    
    if pool_type not in ['char', 'weapon']:
        return jsonify({'error': 'Invalid pool type'}), 400
    
    if count < 1 or count > 10:
        return jsonify({'error': 'Invalid count'}), 400
    
    # 获取当前用户
    user_id, user_info = get_or_create_current_user()
    
    # 检查并消耗资源
    if pool_type == 'char':
        # 特许寻访消耗
        if count == 1:
            # 单抽：1 张特许寻访凭证或 500 个嵌晶玉
            if user_info['resources']['chartered_permits'] >= 1:
                user_info['resources']['chartered_permits'] -= 1
            elif user_info['resources']['oroberyl'] >= 500:
                user_info['resources']['oroberyl'] -= 500
            else:
                return jsonify({'error': '资源不足，无法进行单抽'}), 400
        elif count == 10:
            # 十连：优先使用凭证，不足部分用嵌晶玉补充
            available_permits = user_info['resources'].get('chartered_permits', 0)
            available_oroberyl = user_info['resources'].get('oroberyl', 0)
            
            # 需要的凭证和玉
            required_permits = 10
            required_oroberyl = 0
            
            # 计算需要消耗的凭证和玉
            if available_permits >= required_permits:
                # 凭证足够
                user_info['resources']['chartered_permits'] -= required_permits
            else:
                # 凭证不足，用玉补充
                used_permits = available_permits
                user_info['resources']['chartered_permits'] = 0
                
                remaining_permits = required_permits - used_permits
                required_oroberyl = remaining_permits * 500
                
                if available_oroberyl >= required_oroberyl:
                    user_info['resources']['oroberyl'] -= required_oroberyl
                else:
                    return jsonify({'error': '资源不足，无法进行十连抽'}), 400
    else:  # weapon
        # 武库申领消耗：1980 个武库配额
        if user_info['resources']['arsenal_tickets'] >= 1980:
            user_info['resources']['arsenal_tickets'] -= 1980
        else:
            return jsonify({'error': '武库配额不足，无法进行申领'}), 400
    
    if pool_type == 'char':
        # 初始化角色卡池实例
        char_gacha = CharGacha()
        # 恢复计数器状态
        char_gacha.total_draws = user_info['char_gacha']['total_draws']
        char_gacha.no_6star_draw = user_info['char_gacha']['no_6star_draw']
        char_gacha.no_5star_plus_draw = user_info['char_gacha']['no_5star_plus_draw']
        char_gacha.no_up_draw = user_info['char_gacha']['no_up_draw']
        char_gacha.up_guarantee_used = user_info['char_gacha']['up_guarantee_used']
        
        results = []
        for _ in range(count):
            result = char_gacha.draw_once()
            results.append({
                'name': result.name,
                'star': result.star,
                'quota': result.quota,
                'is_up_g': result.is_up_g,
                'is_6_g': result.is_6_g,
                'is_5_g': result.is_5_g
            })
            
            # 更新收藏
            if result.name not in user_info['collection']['chars']:
                user_info['collection']['chars'][result.name] = {
                    'star': result.star,
                    'count': 0
                }
            user_info['collection']['chars'][result.name]['count'] += 1
            
            # 发放武库配额奖励
            user_info['resources']['arsenal_tickets'] = user_info['resources'].get('arsenal_tickets', 0) + result.quota
        
        # 保存计数器状态
        user_info['char_gacha']['total_draws'] = char_gacha.total_draws
        user_info['char_gacha']['no_6star_draw'] = char_gacha.no_6star_draw
        user_info['char_gacha']['no_5star_plus_draw'] = char_gacha.no_5star_plus_draw
        user_info['char_gacha']['no_up_draw'] = char_gacha.no_up_draw
        user_info['char_gacha']['up_guarantee_used'] = char_gacha.up_guarantee_used
        
        # 记录历史
        user_info['char_gacha']['history'].extend(results)
        
        # 检查累计奖励：加急招募
        if char_gacha.total_draws >= 30 and not user_info['resources']['urgent_used']:
            user_info['resources']['urgent_recruitment'] += 1
            user_info['resources']['urgent_used'] = True
        
    else:  # weapon
        # 初始化武器卡池实例
        weapon_gacha = WeaponGacha()
        # 恢复计数器状态
        weapon_gacha.total_draws = user_info['weapon_gacha']['total_draws']
        weapon_gacha.total_apply = user_info['weapon_gacha']['total_apply']
        weapon_gacha.no_6star_apply = user_info['weapon_gacha']['no_6star_apply']
        weapon_gacha.no_up_apply = user_info['weapon_gacha']['no_up_apply']
        weapon_gacha.up_guarantee_used = user_info['weapon_gacha']['up_guarantee_used']
        
        results = []
        for _ in range(count):
            apply_results = weapon_gacha.apply_once()
            for result in apply_results:
                results.append({
                    'name': result.name,
                    'star': result.star,
                    'quota': result.quota,
                    'is_up_g': result.is_up_g,
                    'is_6_g': result.is_6_g,
                    'is_5_g': result.is_5_g
                })
                
                # 更新收藏
                if result.name not in user_info['collection']['weapons']:
                    user_info['collection']['weapons'][result.name] = {
                        'star': result.star,
                        'count': 0
                    }
                user_info['collection']['weapons'][result.name]['count'] += 1
        
        # 保存计数器状态
        user_info['weapon_gacha']['total_draws'] = weapon_gacha.total_draws
        user_info['weapon_gacha']['total_apply'] = weapon_gacha.total_apply
        user_info['weapon_gacha']['no_6star_apply'] = weapon_gacha.no_6star_apply
        user_info['weapon_gacha']['no_up_apply'] = weapon_gacha.no_up_apply
        user_info['weapon_gacha']['up_guarantee_used'] = weapon_gacha.up_guarantee_used
        
        # 记录历史
        user_info['weapon_gacha']['history'].extend(results)
    
    # 更新最后访问时间
    user_info['last_visit'] = __import__('datetime').datetime.now().isoformat()
    
    # 保存用户数据
    save_user(user_id, user_info)
    
    return jsonify({'results': results})

# 加急招募 API
@app.route('/api/urgent_recruitment', methods=['POST'])
def urgent_recruitment():
    # 获取当前用户
    user_id, user_info = get_or_create_current_user()
    
    # 检查是否有加急招募次数
    if user_info['resources']['urgent_recruitment'] < 1:
        return jsonify({'error': '加急招募次数不足'}), 400
    
    # 消耗 1 个加急招募次数
    user_info['resources']['urgent_recruitment'] -= 1
    
    # 创建新的 CharGacha 实例（不计入先前卡池的保底计数）
    urgent_gacha = CharGacha()
    
    # 执行 10 连抽
    results = []
    for _ in range(10):
        result = urgent_gacha.draw_once()
        results.append({
            'name': result.name,
            'star': result.star,
            'quota': result.quota,
            'is_up_g': result.is_up_g,
            'is_6_g': result.is_6_g,
            'is_5_g': result.is_5_g
        })
        
        # 更新收藏
        if result.name not in user_info['collection']['chars']:
            user_info['collection']['chars'][result.name] = {
                'star': result.star,
                'count': 0
            }
        user_info['collection']['chars'][result.name]['count'] += 1
        
        # 发放武库配额奖励
        user_info['resources']['arsenal_tickets'] = user_info['resources'].get('arsenal_tickets', 0) + result.quota
    
    # 记录历史
    user_info['char_gacha']['history'].extend(results)
    
    # 更新最后访问时间
    user_info['last_visit'] = __import__('datetime').datetime.now().isoformat()
    
    # 保存用户数据
    save_user(user_id, user_info)
    
    return jsonify({'results': results})

# 获取累计奖励 API
@app.route('/api/rewards', methods=['GET'])
def get_rewards():
    # 获取当前用户
    user_id, user_info = get_or_create_current_user()
    
    # 获取卡池类型参数，默认为角色卡池
    pool_type = request.args.get('pool_type', 'char')
    
    if pool_type == 'char':
        # 使用 core.py 中的 get_accumulated_reward 方法获取角色池奖励
        char_gacha = CharGacha()
        char_gacha.total_draws = user_info['char_gacha']['total_draws']
        reward_tuples = char_gacha.get_accumulated_reward()
        
        # 转换为前端需要的格式
        rewards = []
        for reward_name, count in reward_tuples:
            rewards.append(f'{reward_name} × {count}')
            
            # 检查是否是信物奖励，如果是，更新对应干员的收藏数量
            if '信物' in reward_name:
                # 提取干员名称（假设信物格式为"干员名称的信物"）
                char_name = reward_name.replace('的信物', '')
                # 更新干员收藏数量
                if char_name in user_info['collection']['chars']:
                    user_info['collection']['chars'][char_name]['count'] += count
                else:
                    # 如果干员不存在，创建新记录（假设为 6 星干员）
                    user_info['collection']['chars'][char_name] = {
                        'star': 6,
                        'count': count
                    }
    else:  # weapon
        # 使用 core.py 中的 get_accumulated_reward 方法获取武器池奖励
        weapon_gacha = WeaponGacha()
        weapon_gacha.total_apply = user_info['weapon_gacha']['total_apply']
        reward_tuples = weapon_gacha.get_accumulated_reward()
        
        # 转换为前端需要的格式
        rewards = []
        for reward_name, count in reward_tuples:
            rewards.append(f'{reward_name} × {count}')
    
    # 更新最后访问时间
    user_info['last_visit'] = __import__('datetime').datetime.now().isoformat()
    
    # 保存用户数据
    save_user(user_id, user_info)
    
    return jsonify({'rewards': rewards})

# 获取用户数据 API
@app.route('/api/user_data', methods=['GET'])
def get_user_data():
    user_id, user_info = get_or_create_current_user()
    return jsonify(user_info)

# 清空数据 API
@app.route('/api/clear_data', methods=['POST'])
def clear_data():
    # 获取当前用户
    user_id, user_info = get_or_create_current_user()
    
    # 重置用户数据（保留用户 ID 和创建时间）
    new_user_data = {
        'user_id': user_id,
        'created_at': user_info.get('created_at', __import__('datetime').datetime.now().isoformat()),
        'last_visit': __import__('datetime').datetime.now().isoformat(),
        'char_gacha': {
            'total_draws': 0,
            'no_6star_draw': 0,
            'no_5star_plus_draw': 0,
            'no_up_draw': 0,
            'up_guarantee_used': False,
            'history': []
        },
        'weapon_gacha': {
            'total_draws': 0,
            'total_apply': 0,
            'no_6star_apply': 0,
            'no_up_apply': 0,
            'up_guarantee_used': False,
            'history': []
        },
        'collection': {
            'chars': {},
            'weapons': {}
        },
        'resources': {
            'urgent_recruitment': 0,
            'urgent_used': False,
            'chartered_permits': 10,
            'oroberyl': 50000,
            'arsenal_tickets': 8000,
            'origeometry': 100,
            'total_recharge': 0,
            'first_recharge': {
                '6': True,
                '30': True,
                '98': True,
                '198': True,
                '328': True,
                '648': True
            }
        }
    }
    
    # 保存用户数据
    save_user(user_id, new_user_data)
    
    return jsonify({'message': '数据已清空'})

# 充值 API
@app.route('/api/recharge', methods=['POST'])
def recharge():
    data = request.json
    amount = data.get('amount', 0)
    
    if amount <= 0:
        return jsonify({'error': '无效的充值金额'}), 400
    
    # 获取当前用户
    user_id, user_info = get_or_create_current_user()
    
    # 定义充值挡位：基本数量 + 额外赠送数量
    recharge_tiers = {
        6: {'base': 2, 'extra': 1, 'total': 3},  # 2+1
        30: {'base': 12, 'extra': 3, 'total': 15},  # 12+3
        98: {'base': 42, 'extra': 8, 'total': 50},  # 42+8
        198: {'base': 85, 'extra': 17, 'total': 102},  # 85+17
        328: {'base': 141, 'extra': 30, 'total': 171},  # 141+30
        648: {'base': 280, 'extra': 70, 'total': 350}  # 280+70
    }
    
    if amount not in recharge_tiers:
        return jsonify({'error': '无效的充值金额，只支持 6、30、98、198、328、648 元'}), 400
    
    # 检查是否是首充
    is_first_recharge = user_info['resources'].get('first_recharge', {}).get(str(amount), False)
    
    # 计算源石数量
    if is_first_recharge:
        if amount == 6:
            # 6 元档特殊，给 6 个源石
            origeometry_amount = 6
        else:
            # 其他档位双倍：基本数量 × 2
            base = recharge_tiers[amount]['base']
            origeometry_amount = base * 2
        
        # 标记首充已使用
        user_info['resources']['first_recharge'][str(amount)] = False
    else:
        # 非首充，正常数量：基本数量 + 额外赠送数量
        origeometry_amount = recharge_tiers[amount]['total']
    
    # 增加源石
    user_info['resources']['origeometry'] = user_info['resources'].get('origeometry', 0) + origeometry_amount
    
    # 更新累计充值金额
    user_info['resources']['total_recharge'] = user_info['resources'].get('total_recharge', 0) + amount
    
    # 更新最后访问时间
    user_info['last_visit'] = __import__('datetime').datetime.now().isoformat()
    
    # 保存用户数据
    save_user(user_id, user_info)
    
    # 构建返回消息
    if is_first_recharge:
        message = f'成功充值 {amount} 元，获得 {origeometry_amount} 个衍质源石（首充双倍）'
    else:
        message = f'成功充值 {amount} 元，获得 {origeometry_amount} 个衍质源石'
    
    return jsonify({'message': message, 'is_first_recharge': is_first_recharge, 'origeometry_amount': origeometry_amount})

# 兑换 API
@app.route('/api/exchange', methods=['POST'])
def exchange():
    data = request.json
    from_resource = data.get('from')
    to_resource = data.get('to')
    amount = data.get('amount', 1)
    
    if not from_resource or not to_resource:
        return jsonify({'error': '无效的兑换参数'}), 400
    
    # 获取当前用户
    user_id, user_info = get_or_create_current_user()
    
    # 检查兑换规则
    if from_resource == 'origeometry':
        if to_resource == 'oroberyl':
            # 1 衍质源石 → 75 嵌晶玉
            if user_info['resources'].get('origeometry', 0) >= amount:
                user_info['resources']['origeometry'] -= amount
                user_info['resources']['oroberyl'] = user_info['resources'].get('oroberyl', 0) + amount * 75
                # 更新最后访问时间
                user_info['last_visit'] = __import__('datetime').datetime.now().isoformat()
                # 保存用户数据
                save_user(user_id, user_info)
                return jsonify({'message': f'成功兑换 {amount} 衍质源石为 {amount * 75} 嵌晶玉'})
            else:
                return jsonify({'error': '衍质源石不足'}), 400
        elif to_resource == 'arsenal_tickets':
            # 1 衍质源石 → 25 武库配额
            if user_info['resources'].get('origeometry', 0) >= amount:
                user_info['resources']['origeometry'] -= amount
                user_info['resources']['arsenal_tickets'] = user_info['resources'].get('arsenal_tickets', 0) + amount * 25
                # 更新最后访问时间
                user_info['last_visit'] = __import__('datetime').datetime.now().isoformat()
                # 保存用户数据
                save_user(user_id, user_info)
                return jsonify({'message': f'成功兑换 {amount} 衍质源石为 {amount * 25} 武库配额'})
            else:
                return jsonify({'error': '衍质源石不足'}), 400
        else:
            return jsonify({'error': '无效的兑换目标'}), 400
    else:
        return jsonify({'error': '仅支持从衍质源石兑换其他资源'}), 400

# 获取历史记录 API
@app.route('/api/history', methods=['GET'])
def get_history():
    # 获取当前用户
    user_id, user_info = get_or_create_current_user()
    
    # 获取卡池类型参数
    pool_type = request.args.get('pool_type', 'char')
    
    if pool_type not in ['char', 'weapon']:
        return jsonify({'error': 'Invalid pool type'}), 400
    
    # 获取对应的历史记录
    if pool_type == 'char':
        history = user_info['char_gacha'].get('history', [])
    else:
        history = user_info['weapon_gacha'].get('history', [])
    
    return jsonify({'history': history})

# 获取卡池信息API
@app.route('/api/pool_info', methods=['GET'])
def get_pool_info():
    import json
    import os
    
    # 获取卡池类型参数，默认为角色卡池
    pool_type = request.args.get('pool_type', 'char')
    
    # 构建卡池配置文件路径
    pool_config_path = os.path.join(os.path.dirname(__file__), 'config', f'{pool_type}_pool.json')
    
    # 构建常量配置文件路径
    constants_path = os.path.join(os.path.dirname(__file__), 'config', 'constants.json')
    
    try:
        with open(pool_config_path, 'r', encoding='utf-8') as f:
            pool_data = json.load(f)
        
        with open(constants_path, 'r', encoding='utf-8') as f:
            constants = json.load(f)
    except FileNotFoundError as e:
        return jsonify({'error': f'配置文件不存在: {str(e)}'}), 404
    except json.JSONDecodeError as e:
        return jsonify({'error': f'配置文件格式错误: {str(e)}'}), 500
    
    # 提取概率提升的物品（up_prob > 0 的物品）
    boosted_items = []
    for star in pool_data:
        for item in pool_data[star]:
            if item.get('up_prob', 0) > 0:
                boosted_items.append({
                    'name': item['name'],
                    'star': int(star),
                    'type': item.get('type', '')
                })
    
    # 从常量配置文件中获取卡池名称
    if pool_type == 'char':
        pool_name = constants.get('text_constants', {}).get('char_pool_name', '特许寻访')
    else:
        pool_name = constants.get('text_constants', {}).get('weapon_pool_name', '武库申领')
    
    return jsonify({
        'pool_name': pool_name,
        'boosted_items': boosted_items
    })


# 添加静态资源映射函数
def get_static_url(filename):
    """根据原始文件名获取哈希化后的URL"""
    try:
        from app.utils.compress import load_manifest
        manifest = load_manifest()
        return manifest.get(filename, filename)
    except:
        # 如果无法加载manifest，返回原始文件名
        return filename


# 添加模板全局函数
@app.context_processor
def inject_static_url():
    return dict(get_static_url=get_static_url)

def compress_static_files():
    """压缩静态文件"""
    try:
        from app.utils.compress import main as compress_main
        print('正在压缩静态文件...')
        compress_main()
        print('静态文件压缩完成，启动服务')
    except Exception as e:
        print(f'压缩静态文件时出错：{e}')

if __name__ == '__main__':
    compress_static_files()
    app.run(debug=False, port=5000)
