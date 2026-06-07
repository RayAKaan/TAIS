import uuid, math, random, json, time, heapq
from collections import defaultdict
from flask import Flask, Response, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ---------- constants ----------
GRID = 8
NUM_MOTES = 28
NUM_PREDATORS = 3
ENERGY_MAX = 150
ENERGY_BIRTH = 80
SPEECH_COST = 4
MOVE_COST = 0.6
PREDATOR_KILL_RADIUS = 0.45
PEAK_ENERGY_RADIUS = 1.6
PEAK_RECHARGE = 0.18
MEMORY_SIZE = 50
STONE_MAX = 12
STONE_COOLDOWN = 8

CONCEPTS = ["FOOD_HIGH", "PREDATOR", "SAFE", "SHELTER", "WATER"]

LEXICON_BASE = {
    "food": "FOOD_HIGH", "eat": "FOOD_HIGH", "yum": "FOOD_HIGH",
    "pred": "PREDATOR", "danger": "PREDATOR", "run": "PREDATOR",
    "safe": "SAFE", "home": "SAFE", "nest": "SAFE",
    "shelter": "SHELTER", "hide": "SHELTER", "cover": "SHELTER",
    "water": "WATER", "drink": "WATER", "wet": "WATER",
}

LEXICON_ORDER = 3
LEXICON_MAX_LEN = 2

# ---------- helpers ----------
def dist(a, b):
    return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)

def clamp(v, lo=0, hi=GRID):
    return max(lo, min(hi, v))

def lerp(a, b, t):
    return a + (b - a) * t

def random_pos(margin=0.3):
    return {"x": random.uniform(margin, GRID - margin), "y": random.uniform(margin, GRID - margin)}

# ---------- mote ----------
class Mote:
    uid = 0

    def __init__(self, x=None, y=None, parent=None):
        self.id = Mote.uid; Mote.uid += 1
        p = random_pos() if x is None else {"x": x, "y": y}
        self.x = p["x"]; self.y = p["y"]
        self.energy = ENERGY_BIRTH
        self.fitness = random.uniform(0.4, 1.6)
        self.age = 0
        self.alive = True
        self.genome = {"order": LEXICON_ORDER, "max_len": LEXICON_MAX_LEN}
        self.lexicon = {}
        self.lexicon_updates = 0
        self.spoke = 0
        self.directed = 0
        self.broadcast = 0
        self.silent_choice = 0
        self.silent_fear = 0
        self.last_intent = None
        self.pred_dist = 99
        self.recent_utterances = []
        self.memory = []
        self.stone_cooldown = 0

        if parent and random.random() < 0.4:
            inherit_count = min(5, len(parent.memory))
            if inherit_count:
                self.memory = random.sample(parent.memory, inherit_count)
            inherit_lex = {k: v for k, v in parent.lexicon.items() if random.random() < 0.3}
            self.lexicon.update(inherit_lex)

    def memorize(self, entry):
        self.memory.append(entry)
        if len(self.memory) > MEMORY_SIZE:
            self.memory = self.memory[-MEMORY_SIZE:]

    def drop_stone(self, world_stones):
        if self.stone_cooldown > 0: return None
        if self.energy < 20: return None
        if not self.memory: return None
        mem_slice = random.sample(self.memory, min(3, len(self.memory)))
        stone = {
            "id": f"stone-{self.id}-{len(world_stones)}",
            "x": self.x, "y": self.y,
            "memories": mem_slice,
            "lexicon_snapshot": dict(list(self.lexicon.items())[:4]),
            "mote_id": self.id,
            "tick": self.tick if hasattr(self, 'tick') else 0,
        }
        self.stone_cooldown = STONE_COOLDOWN
        self.energy -= 6
        self.memorize({"type": "stone", "data": f"dropped stone at ({self.x:.1f},{self.y:.1f})", "tick": self.tick if hasattr(self, 'tick') else 0})
        return stone

    def read_stone(self, stone):
        learned = 0
        for word, concept in stone.get("lexicon_snapshot", {}).items():
            if word not in self.lexicon:
                self.lexicon[word] = {"concept": concept, "weight": random.uniform(0.3, 0.7)}
                self.lexicon_updates += 1
                learned += 1
        for mem in stone.get("memories", []):
            self.memorize({**mem, "source": "stone"})
        if learned:
            self.memorize({"type": "stone_read", "data": f"learned {learned} words from stone", "tick": self.tick if hasattr(self, 'tick') else 0})
        return learned

    def decide(self, neighbors, predators, peaks):
        if not self.alive: return None, None
        self.age += 1
        self.stone_cooldown = max(0, self.stone_cooldown - 1)
        self.energy -= 0.15

        nearest_pred = min(predators, key=lambda p: dist(self.__dict__, p)) if predators else None
        self.pred_dist = dist(self.__dict__, nearest_pred) if nearest_pred else 99
        in_danger = self.pred_dist < PREDATOR_KILL_RADIUS * 2.5

        if self.energy <= 0:
            self.alive = False
            return "death", {}

        if in_danger and random.random() < 0.45:
            self.silent_fear += 1
            self.last_intent = "SILENT_FEAR"
            return "silence", {"reason": "fear"}

        move_chance = 0.35 if not in_danger else 0.6
        if random.random() < move_chance:
            dx = random.uniform(-0.5, 0.5)
            dy = random.uniform(-0.5, 0.5)
            if in_danger and nearest_pred:
                angle = math.atan2(self.y - nearest_pred["y"], self.x - nearest_pred["x"])
                dx += math.cos(angle) * 0.3
                dy += math.sin(angle) * 0.3
            nx = clamp(self.x + dx); ny = clamp(self.y + dy)
            self.x = nx; self.y = ny
            self.energy -= MOVE_COST
            if random.random() < 0.1:
                self.last_intent = "EXPLORE"
                return "move", {"x": nx, "y": ny}
            return None, None

        nearby_peaks = [p for p in peaks if dist(self.__dict__, p) < PEAK_ENERGY_RADIUS]
        for p in nearby_peaks:
            self.energy = min(ENERGY_MAX, self.energy + PEAK_RECHARGE)

        if self.energy > 35 and random.random() < 0.15:
            self.last_intent = "PREDATOR"
            return None, None

        if self.energy < 25 and nearby_peaks:
            dx = (nearby_peaks[0]["x"] - self.x) * 0.08
            dy = (nearby_peaks[0]["y"] - self.y) * 0.08
            self.x = clamp(self.x + dx); self.y = clamp(self.y + dy)
            return None, None

        if random.random() < 0.18 and self.energy > SPEECH_COST:
            return self._speak(neighbors)

        if random.random() < 0.08:
            self.silent_choice += 1
            self.last_intent = "SILENT_CHOICE"
            return "silence", {"reason": "chose_silence"}

        return None, None

    def _speak(self, neighbors):
        self.energy -= SPEECH_COST
        tokens = random.sample(list(LEXICON_BASE.keys()), min(self.genome["order"], random.randint(1, 2)))
        text = " ".join(tokens)
        self.spoke += 1
        self.last_intent = "SPEAK"
        self.recent_utterances.append(text)
        if len(self.recent_utterances) > 6: self.recent_utterances.pop(0)

        concepts_used = [LEXICON_BASE.get(t, "UNKNOWN") for t in tokens]
        dominant = max(set(concepts_used), key=concepts_used.count) if concepts_used else "UNKNOWN"

        is_broadcast = random.random() < 0.3
        target = None
        if not is_broadcast and neighbors:
            target = random.choice(neighbors)

        if target:
            self.directed += 1
            tgt_id = target["id"]
            self.memorize({"type": "directed", "data": f"{text} -> #{tgt_id}", "tick": self.tick if hasattr(self, 'tick') else 0})
            return "utterance", {"text": text, "tokens": tokens, "intent": dominant, "is_broadcast": False, "is_player": False, "target_id": tgt_id, "position": (self.x, self.y)}
        else:
            self.broadcast += 1
            self.memorize({"type": "broadcast", "data": text, "tick": self.tick if hasattr(self, 'tick') else 0})
            return "utterance", {"text": text, "tokens": tokens, "intent": dominant, "is_broadcast": True, "is_player": False, "position": (self.x, self.y)}

    def to_dict(self):
        return {
            "id": self.id, "x": round(self.x, 2), "y": round(self.y, 2),
            "energy": round(self.energy, 1), "fitness": round(self.fitness, 2),
            "age": self.age, "alive": self.alive,
            "genome": self.genome,
            "top_lexicon": {k: v for k, v in sorted(self.lexicon.items(), key=lambda kv: kv[1]["weight"], reverse=True)[:8]},
            "lexicon_updates": self.lexicon_updates,
            "spoke": self.spoke, "directed": self.directed, "broadcast": self.broadcast,
            "silent_choice": self.silent_choice, "silent_fear": self.silent_fear,
            "last_intent": self.last_intent, "pred_dist": round(self.pred_dist, 2),
            "recent_utterances": self.recent_utterances[-4:],
            "memory_size": len(self.memory),
        }

# ---------- predator ----------
class Predator:
    def __init__(self):
        p = random_pos()
        self.x = p["x"]; self.y = p["y"]
        self.target_x = self.x; self.target_y = self.y

    def update(self, motes):
        alive = [m for m in motes if m.alive]
        if not alive: return None
        target = min(alive, key=lambda m: dist(self.__dict__, m.__dict__))
        d = dist(self.__dict__, target.__dict__)
        self.target_x, self.target_y = target.x, target.y
        if d > 0.3:
            dx = (target.x - self.x) / d * 0.08
            dy = (target.y - self.y) / d * 0.08
            self.x += dx; self.y += dy
        if d < PREDATOR_KILL_RADIUS:
            target.alive = False
            return target.id
        return None

    def to_dict(self):
        return {"x": round(self.x, 2), "y": round(self.y, 2),
                "target_x": round(self.target_x, 2), "target_y": round(self.target_y, 2)}

# ---------- world ----------
class World:
    def __init__(self):
        self.tick = 0
        self.motes = [Mote() for _ in range(NUM_MOTES)]
        self.predators = [Predator() for _ in range(NUM_PREDATORS)]
        self.peaks = [{"x": random.uniform(1, GRID - 1), "y": random.uniform(1, GRID - 1), "s": random.uniform(2, 4)} for _ in range(5)]
        self.stones = []
        self.events = []
        self.total_directed = 0
        self.total_spoke = 0
        self.total_choice_silence = 0
        self.total_fear_silence = 0
        self.total_lexicon_updates = 0

    def tick_step(self):
        self.tick += 1
        self.events = []
        alive = [m for m in self.motes if m.alive]
        dead = [m for m in self.motes if not m.alive]

        for m in alive:
            m.tick = self.tick
            neighbors = [mm.to_dict() for mm in alive if mm.id != m.id and dist(m.__dict__, mm.__dict__) < 2.0]
            pred_dicts = [p.to_dict() for p in self.predators]
            event_type, event_data = m.decide(neighbors, pred_dicts, self.peaks)
            if event_type:
                ev = {"type": event_type, "tick": self.tick, "mote_id": m.id, "energy": round(m.energy, 1)}
                if event_data:
                    ev.update(event_data)
                self.events.append(ev)
                if event_type == "utterance":
                    self.total_spoke += 1
                    if not event_data.get("is_broadcast"):
                        self.total_directed += 1

            if m.energy > 60 and random.random() < 0.006 and len(alive) < NUM_MOTES * 1.5:
                child = Mote(x=m.x + random.uniform(-0.3, 0.3), y=m.y + random.uniform(-0.3, 0.3), parent=m)
                child.energy = ENERGY_BIRTH * 0.7
                m.energy -= 15
                self.motes.append(child)
                self.events.append({"type": "birth", "tick": self.tick, "mote_id": child.id, "parent_id": m.id, "energy": round(child.energy, 1)})
                child.memorize({"type": "birth", "data": f"born from #{m.id}", "tick": self.tick})

            if random.random() < 0.04 and m.energy > 25:
                stone = m.drop_stone(self.stones)
                if stone:
                    self.stones.append(stone)
                    if len(self.stones) > STONE_MAX:
                        self.stones.pop(0)
                    self.events.append({"type": "stone_drop", "tick": self.tick, "mote_id": m.id, "x": round(m.x, 1), "y": round(m.y, 1)})

            for stone in self.stones:
                if dist(m.__dict__, stone) < 0.5 and random.random() < 0.08:
                    learned = m.read_stone(stone)
                    if learned:
                        self.total_lexicon_updates += learned
                        self.events.append({"type": "stone_read", "tick": self.tick, "mote_id": m.id, "learned": learned})

        for p in self.predators:
            killed = p.update(self.motes)
            if killed is not None:
                self.events.append({"type": "death", "tick": self.tick, "mote_id": killed})

        if len(alive) < NUM_MOTES * 0.5:
            for _ in range(3):
                self.motes.append(Mote())
                self.events.append({"type": "birth", "tick": self.tick, "mote_id": self.motes[-1].id, "energy": round(self.motes[-1].energy, 1)})

        # Collect stats
        for m in alive:
            self.total_lexicon_updates += m.lexicon_updates
            if m.silent_fear > 0:
                self.total_fear_silence += 1
            if m.silent_choice > 0:
                self.total_choice_silence += 1

    def handle_player_speak(self, text, concept, teaching, fitness, x, y):
        event = {"type": "utterance", "tick": self.tick, "mote_id": None, "text": text, "concept": concept, "is_player": True, "is_broadcast": False, "position": (x, y)}
        self.events.append(event)
        alive = [m for m in self.motes if m.alive]
        for m in alive:
            if dist({"x": x, "y": y}, m.__dict__) < 2.5:
                m.memorize({"type": "player_speech", "data": text, "tick": self.tick})
                if teaching and concept and random.random() < 0.3:
                    if text not in m.lexicon:
                        m.lexicon[text] = {"concept": concept, "weight": random.uniform(0.4, 0.9)}
                        m.lexicon_updates += 1
                        self.total_lexicon_updates += 1
                    else:
                        m.lexicon[text]["weight"] = min(1.0, m.lexicon[text]["weight"] + 0.1)
                    event["taught"] = True

    def handle_player_move(self, x, y):
        self.events.append({"type": "player", "tick": self.tick, "mote_id": None, "text": f"moved to ({x:.1f}, {y:.1f})"})

    def handle_player_teach(self, word, concept):
        self.events.append({"type": "teaching", "tick": self.tick, "mote_id": None, "text": word, "concept": concept})
        alive = [m for m in self.motes if m.alive]
        taught = 0
        for m in alive:
            if word not in m.lexicon and random.random() < 0.2:
                m.lexicon[word] = {"concept": concept, "weight": random.uniform(0.3, 0.7)}
                m.lexicon_updates += 1
                self.total_lexicon_updates += 1
                taught += 1
        return taught

    def get_state(self, player_pos):
        alive = [m for m in self.motes if m.alive]
        dead = [m for m in self.motes if not m.alive]
        return {
            "tick": self.tick,
            "population": len(alive),
            "motes": [m.to_dict() for m in alive],
            "predators": [p.to_dict() for p in self.predators],
            "peaks": self.peaks,
            "stones": self.stones,
            "concepts": CONCEPTS,
            "player": player_pos,
            "stats": {
                "directed_ratio": self.total_directed / max(1, self.total_spoke),
                "spoke": self.total_spoke,
                "choice_silence": self.total_choice_silence,
                "fear_silence": self.total_fear_silence,
                "lexicon_updates": self.total_lexicon_updates,
            },
            "events": self.events[-60:],
        }


# ---------- app state ----------
world = World()
player_pos = {"x": 4, "y": 4, "fitness": 1.0, "stones_read": 0, "stones_dropped": 0}


@app.route("/stream")
def stream():
    def gen():
        while True:
            for _ in range(2):
                world.tick_step()
            state = world.get_state(player_pos)
            state["player"].update(player_pos)
            yield f"data: {json.dumps(state)}\n\n"
            time.sleep(0.35)
    return Response(gen(), mimetype="text/event-stream")


@app.route("/player/move", methods=["POST"])
def player_move():
    data = request.get_json()
    x = clamp(data["x"])
    y = clamp(data["y"])
    player_pos.update({"x": x, "y": y})
    world.handle_player_move(x, y)
    return jsonify({"ok": True})


@app.route("/player/speak", methods=["POST"])
def player_speak():
    data = request.get_json()
    text = data.get("text", "hello")
    concept = data.get("concept")
    teaching = data.get("teaching", False)
    fitness = data.get("fitness", 8.0)
    x = clamp(data.get("x", player_pos["x"]))
    y = clamp(data.get("y", player_pos["y"]))
    player_pos["fitness"] = fitness
    world.handle_player_speak(text, concept, teaching, fitness, x, y)
    return jsonify({"ok": True})


@app.route("/player/teach", methods=["POST"])
def player_teach():
    data = request.get_json()
    word = data.get("word", "food")
    concept = data.get("concept", "FOOD_HIGH")
    taught = world.handle_player_teach(word, concept)
    return jsonify({"ok": True, "taught": taught})


@app.route("/reset", methods=["POST"])
def reset():
    global world
    world = World()
    player_pos.update({"x": 4, "y": 4, "fitness": 1.0, "stones_read": 0, "stones_dropped": 0})
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("V4 server on :5124   World  Memory  Reference")
    app.run(host="0.0.0.0", port=5124, threaded=True)
