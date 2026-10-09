# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块（学生骨架）。

你的全部作业都在本文件里：按题面（题面.pdf）各题的规范补全每个标有 TODO 的函数。
- 骨架已提供：Facing / SentryState 枚举、SentryGrid 的构造与只读属性、
  渲染函数 render_frame（demo 用，不进测试）。
- 你要实现：Q1-Q6 与 Bonus 的全部 TODO，以及 SentryGrid 的
  四个方法（current_pos 的 setter、move_forward、turn_left、turn_right）。
- 未实现的函数 raise NotImplementedError：可见测试会自动 skip，
  CI 一开始就是绿的；实现一个，对应测试亮一个。
- `python main.py`（或 PYTHONPATH=src python -m main）可看 ASCII 演示。
"""
import json
import re
from enum import Enum


# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]


# ---------------------------------------------------------------------------
# Q1 机器人自检（题面 Q1·自检状态计算与报告生成）
# ---------------------------------------------------------------------------
def hp_ratio(hp, max_hp):
    """血量百分比，返回 0-100 的 int。"""
    if max_hp <= 0:
        return 0
    pct = (int(hp) * 100) // int(max_hp)
    if pct < 0:
        return 0
    if pct > 100:
        return 100
    return pct


def status_report(name, robot_type, hp, max_hp, battery):
    """一行自检报告字符串，格式见题面 Q1 规范。"""
    if battery >= 50:
        tier = "OK"
    elif battery >= 20:
        tier = "WARNING"
    else:
        tier = "LOW"
    ratio = hp_ratio(hp, max_hp)
    return ("{name:<10}|{robot_type:^10}"
            "|HP {ratio:>3}%|BAT {battery:>3}%|{tier}").format(
        name=name, robot_type=robot_type, ratio=ratio,
        battery=battery, tier=tier)


# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------


def analyze_damage_log(lines):
    """解析混合格式伤害日志，返回固定契约的统计 dict。"""
    by_armor = {"front": 0, "left": 0, "right": 0}
    total = 0
    event_count = 0
    seen_ids = set()
    sensor_re = re.compile(r"^([A-Za-z]):(-?\d+)$")
    key_map = {"F": "front", "L": "left", "R": "right",
               "f": "front", "l": "left", "r": "right"}

    for raw in lines:
        if not isinstance(raw, str):
            continue
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        # JSON 行
        if line.startswith("{"):
            try:
                obj = json.loads(line)
            except (ValueError, TypeError):
                continue
            if not isinstance(obj, dict):
                continue
            armor = obj.get("armor")
            damage = obj.get("damage")
            if armor not in ("front", "left", "right"):
                continue
            if not isinstance(damage, int) or isinstance(damage, bool):
                continue
            if damage <= 0:
                continue
            obj_id = obj.get("id")
            if obj_id is not None:
                if obj_id in seen_ids:
                    continue
                seen_ids.add(obj_id)
            by_armor[armor] += damage
            total += damage
            event_count += 1
            continue

        # 传感器行
        if ":" not in line:
            continue
        try:
            segments = line.split(",")
        except Exception:
            continue
        parsed_any = False
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            m = sensor_re.match(seg)
            if not m:
                parsed_any = False
                break
            letter, num = m.group(1), m.group(2)
            if letter not in key_map:
                parsed_any = False
                break
            try:
                value = int(num)
            except ValueError:
                parsed_any = False
                break
            if value <= 0:
                parsed_any = False
                break
            armor = key_map[letter]
            by_armor[armor] += value
            total += value
            event_count += 1
            parsed_any = True

        if not parsed_any:
            continue

    if event_count == 0:
        most_hit = None
        avg = 0.0
    else:
        most_hit = max(by_armor, key=by_armor.get)
        avg = round(total / event_count, 2)

    return {"total": total, "by_armor": by_armor,
            "most_hit": most_hit, "avg": avg}


# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------
class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        # 障碍坐标存入 set，查询 O(1)——已有实现，勿改。
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        self._pos = self._clamp_cell(start_pos)
        if self._pos in self._obstacles:
            raise ValueError("start_pos 不能位于障碍物上")

    def _clamp_cell(self, cell):
        """已提供：元素转 int 并夹回地图范围（供 __init__ 使用）。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    # -- 只读属性（已提供，勿改） ------------------------------------------
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        """障碍集合的只读视图（内部 set 引用，不要修改它）。"""
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        """已提供：坐标是否为障碍或越界（O(1)）。"""
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    # -- 你要实现的部分 ------------------------------------------------------
    @property
    def current_pos(self):
        """当前位置 (x, y) 的 tuple。"""
        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        """位置 setter；输入校验见题面 Q3 规范第 1 条。"""
        if not isinstance(value, (tuple, list)):
            raise TypeError("current_pos 必须是长度为 2 的 tuple 或 list")
        if len(value) != 2:
            raise TypeError("current_pos 长度必须为 2")
        x = int(value[0])
        y = int(value[1])
        self._pos = (x, y)

    def move_forward(self):
        """朝当前 facing 前进一格，返回执行后的位置；
        碰撞、耗电与断电语义见题面 Q3 规范。"""
        if self._fuel <= 0:
            return self.current_pos

        x, y = self.current_pos
        if self._facing == Facing.UP:
            nx, ny = x, y + 1
        elif self._facing == Facing.DOWN:
            nx, ny = x, y - 1
        elif self._facing == Facing.LEFT:
            nx, ny = x - 1, y
        else:
            nx, ny = x + 1, y

        if self.is_blocked(nx, ny):
            self._collision_count += 1
            return self.current_pos

        self._pos = (nx, ny)
        self._fuel -= 1
        return self.current_pos

    def turn_left(self):
        """原地左转 90°，返回新的 Facing（不耗电）。"""
        mapping = {
            Facing.UP: Facing.LEFT,
            Facing.LEFT: Facing.DOWN,
            Facing.DOWN: Facing.RIGHT,
            Facing.RIGHT: Facing.UP,
        }
        self._facing = mapping[self._facing]
        return self._facing

    def turn_right(self):
        """原地右转 90°，返回新的 Facing（不耗电）。"""
        mapping = {
            Facing.UP: Facing.RIGHT,
            Facing.RIGHT: Facing.DOWN,
            Facing.DOWN: Facing.LEFT,
            Facing.LEFT: Facing.UP,
        }
        self._facing = mapping[self._facing]
        return self._facing

# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------


def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """返回下一步应朝向的 Facing；贪心策略见题面 Q4 规范。"""
    cur_dist = abs(pos[0] - target[0]) + abs(pos[1] - target[1])
    if cur_dist == 0:
        return current_facing

    candidates = []
    for facing in Facing:
        nxt = (pos[0] + facing.delta[0], pos[1] + facing.delta[1])
        if nxt in obstacles:
            continue
        new_dist = abs(nxt[0] - target[0]) + abs(nxt[1] - target[1])
        if new_dist < cur_dist:
            candidates.append(facing)

    if not candidates:
        return current_facing

    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    prefer_x = abs(dx) >= abs(dy)
    for facing in candidates:
        d = facing.delta
        is_x = d[0] != 0
        if is_x == prefer_x:
            return facing
    return candidates[0]


# ---------------------------------------------------------------------------
# Q5 哨兵决策机（题面 Q5·裁判系统决策规则表）
# ---------------------------------------------------------------------------
class SentryState(Enum):
    """哨兵状态机（已提供，勿改）。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


def decide(sensor, state, hp, heat):
    """纯函数决策，返回 (action: str, new_state: SentryState)；
    R1-R7 规则表与非法输入处理见题面 Q5 规范。"""
    if not isinstance(sensor, dict):
        raise ValueError("sensor 必须是 dict")
    for field in ("enemy_frames", "enemy_dist", "robot_type", "max_hp"):
        if field not in sensor:
            raise ValueError("sensor 缺少字段: {}".format(field))
    frames = sensor["enemy_frames"]
    if not isinstance(frames, (tuple, list)):
        raise ValueError("enemy_frames 必须是 tuple 或 list")
    if len(frames) == 0 or len(frames) > 6:
        raise ValueError("enemy_frames 长度须在 1-6 之间")
    if not isinstance(state, SentryState):
        raise ValueError("state 必须是 SentryState 成员")

    max_hp = sensor["max_hp"]
    if max_hp <= 0:
        hp_pct = 0
    else:
        hp_pct = (int(hp) * 100) // int(max_hp)
        if hp_pct < 0:
            hp_pct = 0
        if hp_pct > 100:
            hp_pct = 100

    visible = bool(frames[-1])
    enemy_dist = sensor["enemy_dist"]
    robot_type = sensor["robot_type"]

    if hp_pct <= 30:
        return ("RETREAT", SentryState.RETREAT)

    if state == SentryState.RETREAT:
        return ("RETURN", SentryState.RETURN)

    if state == SentryState.RETURN:
        return ("MOVE_BASE", SentryState.PATROL)

    if state == SentryState.ENGAGE and visible:
        if enemy_dist is not None and enemy_dist <= 3:
            return ("SHOOT", SentryState.ENGAGE)
        if robot_type == "HERO":
            return ("MOVE_RIGHT", SentryState.ENGAGE)
        return ("MOVE_LEFT", SentryState.ENGAGE)

    if state == SentryState.ENGAGE and not visible:
        if len(frames) >= 2 and frames[-2]:
            return ("HOLD_FIRE", SentryState.ENGAGE)
        return ("SCAN", SentryState.SUSPECT)

    if state in (SentryState.PATROL, SentryState.SUSPECT) and visible:
        if len(frames) >= 2 and frames[-2] and frames[-1]:
            if enemy_dist is not None and enemy_dist <= 3:
                return ("SHOOT", SentryState.ENGAGE)
            if robot_type == "HERO":
                return ("MOVE_RIGHT", SentryState.ENGAGE)
            return ("MOVE_LEFT", SentryState.ENGAGE)
        return ("SCAN", SentryState.SUSPECT)

    if state == SentryState.PATROL:
        return ("PATROL_MOVE", SentryState.PATROL)
    return ("SCAN", SentryState.SUSPECT)


# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
def run_patrol(grid, max_steps=500):
    """sense → decide → act 主循环；贪心导航 + 左手沿墙脱困。"""
    left_map = {Facing.UP: Facing.LEFT, Facing.LEFT: Facing.DOWN,
                Facing.DOWN: Facing.RIGHT, Facing.RIGHT: Facing.UP}
    right_map = {Facing.UP: Facing.RIGHT, Facing.RIGHT: Facing.DOWN,
                 Facing.DOWN: Facing.LEFT, Facing.LEFT: Facing.UP}

    def manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def has_greedy_candidate(pos):
        dist = manhattan(pos, grid.enemy_pos)
        for f in (Facing.UP, Facing.DOWN, Facing.LEFT, Facing.RIGHT):
            d = f.delta
            nxt = (pos[0] + d[0], pos[1] + d[1])
            if not grid.is_blocked(*nxt) and manhattan(nxt, grid.enemy_pos) < dist:
                return True
        return False

    visited = set()
    steps = 0
    wall_mode = False
    wall_hand = "L"
    wall_steps = 0
    entry_dist = 0
    limit = grid.width + grid.height

    while (steps < max_steps and grid.fuel > 0
           and not grid.found_enemy):
        pos = grid.current_pos
        visited.add(pos)

        # 切入脱困
        if not wall_mode and not has_greedy_candidate(pos):
            wall_mode = True
            wall_hand = "L"
            wall_steps = 0
            entry_dist = manhattan(pos, grid.enemy_pos)

        if wall_mode:
            side = left_map[grid.facing] if wall_hand == "L" else right_map[grid.facing]
            opposite = right_map[grid.facing] if wall_hand == "L" else left_map[grid.facing]

            def cell(f):
                d = f.delta
                return (pos[0] + d[0], pos[1] + d[1])

            if not grid.is_blocked(*cell(side)):
                target_facing = side
            elif grid.is_blocked(*cell(grid.facing)):
                if not grid.is_blocked(*cell(opposite)):
                    target_facing = opposite
                else:
                    target_facing = right_map[right_map[grid.facing]]
            else:
                target_facing = grid.facing
        else:
            target_facing = next_step_toward(
                pos, grid.enemy_pos, grid.obstacles, grid.facing)

        # 朝向对齐
        rights = {Facing.UP: 0, Facing.RIGHT: 1,
                  Facing.DOWN: 2, Facing.LEFT: 3}
        diff = (rights[target_facing] - rights[grid.facing]) % 4
        if diff == 3:
            grid.turn_left()
        else:
            for _ in range(diff):
                grid.turn_right()

        grid.move_forward()
        steps += 1

        if wall_mode:
            wall_steps += 1
            new_pos = grid.current_pos
            if wall_steps > limit and wall_hand == "L":
                wall_hand = "R"
                wall_steps = 0
            elif wall_steps > 2 * limit:
                wall_mode = False
            elif has_greedy_candidate(new_pos) and \
                    manhattan(new_pos, grid.enemy_pos) < entry_dist + 1:
                wall_mode = False

    visited.add(grid.current_pos)
    success = grid.found_enemy
    return {"steps": steps,
            "collisions": grid.collision_count,
            "visited_count": len(visited),
            "found_enemy": success,
            "success": success}


def report_to_json(stats):
    return json.dumps(stats, sort_keys=True, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------
def bfs_path_length(start, target, obstacles):
    """BFS 全局最短路步数；不可达返回 -1。"""
    from collections import deque
    start = (int(start[0]), int(start[1]))
    target = (int(target[0]), int(target[1]))
    if start == target:
        return 0
    obs = set(obstacles)
    if start in obs or target in obs:
        return -1
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        cur, dist = queue.popleft()
        for nxt in ((cur[0] + 1, cur[1]), (cur[0] - 1, cur[1]),
                    (cur[0], cur[1] + 1), (cur[0], cur[1] - 1)):
            if nxt in obs or nxt in seen:
                continue
            if nxt == target:
                return dist + 1
            seen.add(nxt)
            queue.append((nxt, dist + 1))
    return -1


# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------
def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场；trail 为走过的格子集合。返回 list[str]。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
