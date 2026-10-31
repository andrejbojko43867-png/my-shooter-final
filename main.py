from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.core.window import Window
from kivy.clock import Clock
import math
import random

MAP_WIDTH, MAP_HEIGHT = 2500, 2500
PLAYER_SPEED = 250
BULLET_SPEED = 900

WEAPONS = {
    'pistol': {'name': 'Пистолет', 'price': 0, 'damage': 25, 'fire_rate': 0.3, 'spread': 0.05, 'ammo': 15, 'max_ammo': 120},
    'rifle': {'name': 'Автомат', 'price': 700, 'damage': 20, 'fire_rate': 0.1, 'spread': 0.1, 'ammo': 30, 'max_ammo': 120},
    'shotgun': {'name': 'Дробовик', 'price': 450, 'damage': 80, 'fire_rate': 0.8, 'spread': 0.3, 'ammo': 8, 'max_ammo': 32},
    'sniper': {'name': 'Снайперка', 'price': 950, 'damage': 150, 'fire_rate': 1.5, 'spread': 0.0, 'ammo': 5, 'max_ammo': 30},
}

class Bullet(Widget):
    def __init__(self, pos, angle, team, damage, **kwargs):
        super().__init__(**kwargs)
        self.size = (12, 6)
        self.pos = pos
        self.angle = angle
        self.team = team
        self.damage = damage
        self.alive = True
        with self.canvas:
            Color(1, 1, 0, 1) if team == 'player' else Color(1, 0.5, 0, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
    
    def update(self, dt, obstacles):
        if not self.alive: return
        self.x += math.cos(self.angle) * BULLET_SPEED * dt
        self.y += math.sin(self.angle) * BULLET_SPEED * dt
        self.rect.pos = self.pos
        
        if self.x < 0 or self.x > MAP_WIDTH or self.y < 0 or self.y > MAP_HEIGHT:
            self.alive = False
            return
        for obs in obstacles:
            if obs.collide_point(self.center_x, self.center_y):
                self.alive = False
                return

class Bot(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (44, 44)
        self.hp = 100
        self.alive = True
        self.angle = random.uniform(0, math.pi*2)
        self.shoot_timer = random.uniform(0, 1)
        
        with self.canvas:
            Color(1, 0.2, 0.2, 1)
            self.body = Ellipse(pos=self.pos, size=self.size)
            Color(0, 0, 0, 1)
            self.gun = Line(points=[self.center_x, self.center_y, self.center_x + 25, self.center_y], width=5)
            Color(1, 0, 0, 1)
            self.hp_bar = Line(points=[self.x, self.y - 10, self.x + 44, self.y - 10], width=5)

    def update_visuals(self):
        self.body.pos = self.pos
        self.gun.points = [self.center_x, self.center_y, 
                           self.center_x + math.cos(self.angle)*25, 
                           self.center_y + math.sin(self.angle)*25]
        hp_width = 44 * (self.hp / 100)
        self.hp_bar.points = [self.x, self.y - 10, self.x + hp_width, self.y - 10]

    def shoot(self, target):
        if self.shoot_timer > 0: return None
        self.shoot_timer = 0.6
        self.angle = math.atan2(target[1] - self.center_y, target[0] - self.center_x)
        self.update_visuals()
        return Bullet(pos=(self.center_x, self.center_y), angle=self.angle, team='enemy', damage=15)

class Joystick(Widget):
    def __init__(self, pos_center, **kwargs):
        super().__init__(**kwargs)
        self.center_pos = pos_center
        self.radius = 70
        self.knob_radius = 30
        self.knob_pos = list(pos_center)
        self.active = False
        self.touch_id = None
        self.direction = (0, 0)
        with self.canvas:
            Color(1, 1, 1, 0.2)
            self.bg = Ellipse(pos=(self.center_pos[0] - self.radius, self.center_pos[1] - self.radius), size=(self.radius*2, self.radius*2))
            Color(1, 1, 1, 0.5)
            self.knob = Ellipse(pos=(self.knob_pos[0] - self.knob_radius, self.knob_pos[1] - self.knob_radius), size=(self.knob_radius*2, self.knob_radius*2))
    
    def on_touch_down(self, touch):
        if not self.active and math.dist(touch.pos, self.center_pos) < self.radius * 1.5:
            self.active = True
            self.touch_id = touch.uid
            self._update_knob(touch.pos)
            return True
        return False

    def on_touch_move(self, touch):
        if self.active and touch.uid == self.touch_id:
            self._update_knob(touch.pos)
            return True
        return False

    def on_touch_up(self, touch):
        if self.active and touch.uid == self.touch_id:
            self.active = False
            self.touch_id = None
            self.knob_pos = list(self.center_pos)
            self.knob.pos = (self.center_pos[0] - self.knob_radius, self.center_pos[1] - self.knob_radius)
            self.direction = (0, 0)
            return True
        return False

    def _update_knob(self, touch_pos):
        dx = touch_pos[0] - self.center_pos[0]
        dy = touch_pos[1] - self.center_pos[1]
        dist = math.dist(touch_pos, self.center_pos)
        if dist > self.radius:
            dx = (dx / dist) * self.radius
            dy = (dy / dist) * self.radius
        self.knob_pos = [self.center_pos[0] + dx, self.center_pos[1] + dy]
        self.knob.pos = (self.knob_pos[0] - self.knob_radius, self.knob_pos[1] - self.knob_radius)
        self.direction = (dx / self.radius, dy / self.radius)

class Game(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.money = 800
        self.kills = 0
        self.obstacles = []
        self.bullets = []
        self.bots = []
        self.player_pos = [MAP_WIDTH/2, MAP_HEIGHT/2]
        self.player_angle = 0
        self.player_hp = 100
        self.player_armor = 0
        self.player_weapon = 'pistol'
        self.current_ammo = WEAPONS['pistol']['ammo']
        self.shoot_timer = 0
        
        self.shop_pos = (MAP_WIDTH/2 - 400, MAP_HEIGHT/2)
        self.in_shop = False
        
        self._generate_map()
        self._spawn_bots(4)
        
        self.move_joy = Joystick((150, 150))
        self.aim_joy = Joystick((Window.width - 150, 150))
        Clock.schedule_interval(self.update, 1/60)

    def _generate_map(self):
        for i in range(25):
            w, h = random.randint(80, 350), random.randint(80, 350)
            x, y = random.randint(0, MAP_WIDTH - w), random.randint(0, MAP_HEIGHT - h)
            if math.dist((x + w/2, y + h/2), (MAP_WIDTH/2, MAP_HEIGHT/2)) > 400:
                wall = Widget(size=(w, h), pos=(x, y))
                with wall.canvas:
                    Color(0.2, 0.2, 0.2, 1)
                    Rectangle(pos=wall.pos, size=wall.size)
                    Color(0.4, 0.4, 0.4, 1)
                    Line(rectangle=(wall.x, wall.y, wall.width, wall.height), width=3)
                self.obstacles.append(wall)

    def _spawn_bots(self, count):
        for _ in range(count):
            while True:
                x = random.randint(100, MAP_WIDTH - 100)
                y = random.randint(100, MAP_HEIGHT - 100)
                if math.dist((x, y), (MAP_WIDTH/2, MAP_HEIGHT/2)) > 500:
                    self.bots.append(Bot(pos=(x, y)))
                    break

    def buy_item(self, item):
        if item == 'armor' and self.money >= 350:
            self.money -= 350
            self.player_armor = 100
        elif item in WEAPONS and self.money >= WEAPONS[item]['price']:
            self.money -= WEAPONS[item]['price']
            self.player_weapon = item
            self.current_ammo = WEAPONS[item]['ammo']
        self.show_shop()

    def update(self, dt):
        if self.player_hp <= 0: return

        dx = self.move_joy.direction[0] * PLAYER_SPEED * dt
        dy = self.move_joy.direction[1] * PLAYER_SPEED * dt
        self._move_player(dx, dy)

        if math.dist(self.player_pos, self.shop_pos) < 120:
            if not self.in_shop:
                self.in_shop = True
                self.show_shop()
        else:
            if self.in_shop:
                self.close_shop()

        self.shoot_timer -= dt
        if self.aim_joy.direction != (0, 0) and self.shoot_timer <= 0:
            w = WEAPONS[self.player_weapon]
            if self.current_ammo > 0:
                self.shoot_timer = w['fire_rate']
                self.current_ammo -= 1
                angle = math.atan2(self.aim_joy.direction[1], self.aim_joy.direction[0])
                angle += random.uniform(-w['spread'], w['spread'])
                self.player_angle = angle
                self.bullets.append(Bullet(pos=self.player_pos, angle=angle, team='player', damage=w['damage']))
            else:
                self.current_ammo = w['ammo']

        for bot in self.bots:
            if not bot.alive: continue
            bot.shoot_timer -= dt
            dist = math.dist(bot.center, self.player_pos)
            if dist < 600:
                b = bot.shoot(self.player_pos)
                if b: self.bullets.append(b)
                if dist > 200:
                    b_dx = (self.player_pos[0] - bot.center_x) / dist * 150 * dt
                    b_dy = (self.player_pos[1] - bot.center_y) / dist * 150 * dt
                    bot.x += b_dx
                    bot.y += b_dy
                    bot.update_visuals()

        for b in self.bullets:
            b.update(dt, self.obstacles)
            if not b.alive: continue
            
            if b.team == 'player':
                for bot in self.bots:
                    if bot.alive and math.dist(b.center, bot.center) < 25:
                        bot.hp -= b.damage
                        bot.update_visuals()
                        b.alive = False
                        if bot.hp <= 0:
                            bot.alive = False
                            self.money += 300
                            self.kills += 1
                        break
            else:
                if math.dist(b.center, self.player_pos) < 25:
                    if self.player_armor > 0:
                        self.player_armor -= b.damage * 0.5
                        self.player_hp -= b.damage * 0.5
                    else:
                        self.player_hp -= b.damage
                    b.alive = False

        self.bullets = [b for b in self.bullets if b.alive]
        self.bots = [bot for bot in self.bots if bot.alive]
        if len(self.bots) == 0: self._spawn_bots(4)

        self.draw_game()

    def draw_game(self):
        cam_x = Window.width / 2 - self.player_pos[0]
        cam_y = Window.height / 2 - self.player_pos[1]
        
        self.canvas.clear()
        with self.canvas:
            Color(0.55, 0.5, 0.4, 1)
            Rectangle(pos=(cam_x, cam_y), size=(MAP_WIDTH, MAP_HEIGHT))
            
            Color(0, 0.8, 0, 0.3)
            Ellipse(pos=(self.shop_pos[0] + cam_x - 120, self.shop_pos[1] + cam_y - 120), size=(240, 240))
            Color(0, 1, 0, 1)
            Line(circle=(self.shop_pos[0] + cam_x, self.shop_pos[1] + cam_y, 120), width=4)

            for obs in self.obstacles:
                Color(0.25, 0.25, 0.25, 1)
                Rectangle(pos=(obs.x + cam_x, obs.y + cam_y), size=obs.size)
                Color(0.4, 0.4, 0.4, 1)
                Line(rectangle=(obs.x + cam_x, obs.y + cam_y, obs.width, obs.height), width=3)

            Color(0.2, 0.5, 1, 1)
            Ellipse(pos=(self.player_pos[0] + cam_x - 22, self.player_pos[1] + cam_y - 22), size=(44, 44))
            Color(0, 0, 0, 1)
            Line(points=[self.player_pos[0] + cam_x, self.player_pos[1] + cam_y, 
                         self.player_pos[0] + cam_x + math.cos(self.player_angle)*30, 
                         self.player_pos[1] + cam_y + math.sin(self.player_angle)*30], width=6)

            for bot in self.bots:
                Color(1, 0.2, 0.2, 1)
                Ellipse(pos=(bot.x + cam_x, bot.y + cam_y), size=bot.size)
                Color(0, 0, 0, 1)
                Line(points=[bot.center_x + cam_x, bot.center_y + cam_y, 
                             bot.center_x + cam_x + math.cos(bot.angle)*30, 
                             bot.center_y + cam_y + math.sin(bot.angle)*30], width=6)

            for b in self.bullets:
                Color(1, 1, 0, 1) if b.team == 'player' else Color(1, 0.5, 0, 1)
                Ellipse(pos=(b.x + cam_x, b.y + cam_y), size=b.size)

    def _move_player(self, dx, dy):
        new_x = self.player_pos[0] + dx
        new_y = self.player_pos[1] + dy
        rect = (new_x - 22, new_y - 22, 44, 44)
        for obs in self.obstacles:
            if (rect[0] < obs.x + obs.width and rect[0] + rect[2] > obs.x and
                rect[1] < obs.y + obs.height and rect[1] + rect[3] > obs.y):
                return
        self.player_pos[0] = max(22, min(new_x, MAP_WIDTH - 22))
        self.player_pos[1] = max(22, min(new_y, MAP_HEIGHT - 22))

    def show_shop(self):
        self.clear_widgets()
        shop_layout = BoxLayout(orientation='vertical', size_hint=(0.6, 0.8), pos_hint={'center_x': 0.5, 'center_y': 0.5}, spacing=15, padding=20)
        
        with shop_layout.canvas.before:
            Color(0.1, 0.1, 0.1, 0.9)
            self.bg_rect = Rectangle(pos=shop_layout.pos, size=shop_layout.size)
        
        shop_layout.add_widget(Label(text=f"МАГАЗИН\nДеньги: {self.money}$", font_size='30sp', color=(0,1,0,1)))
        
        btn_rifle = Button(text=f"Автомат ({WEAPONS['rifle']['price']}$)", font_size='22sp')
        btn_rifle.bind(on_press=lambda x: self.buy_item('rifle'))
        shop_layout.add_widget(btn_rifle)
        
        btn_shotgun = Button(text=f"Дробовик ({WEAPONS['shotgun']['price']}$)", font_size='22sp')
        btn_shotgun.bind(on_press=lambda x: self.buy_item('shotgun'))
        shop_layout.add_widget(btn_shotgun)
        
        btn_sniper = Button(text=f"Снайперка ({WEAPONS['sniper']['price']}$)", font_size='22sp')
        btn_sniper.bind(on_press=lambda x: self.buy_item('sniper'))
        shop_layout.add_widget(btn_sniper)
        
        btn_armor = Button(text="Броня (350$)", font_size='22sp')
        btn_armor.bind(on_press=lambda x: self.buy_item('armor'))
        shop_layout.add_widget(btn_armor)

        btn_close = Button(text="ВЫХОД", font_size='22sp', background_color=(0,0.8,0,1))
        btn_close.bind(on_press=lambda x: self.close_shop())
        shop_layout.add_widget(btn_close)
        
        self.add_widget(shop_layout)

    def close_shop(self):
        self.clear_widgets()
        self.add_widget(self.move_joy)
        self.add_widget(self.aim_joy)
        self.in_shop = False
        self.player_pos[0] -= 150 

    def on_touch_down(self, touch):
        if self.in_shop: return super().on_touch_down(touch)
        if self.move_joy.on_touch_down(touch): return True
        if self.aim_joy.on_touch_down(touch): return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.in_shop: return super().on_touch_move(touch)
        if self.move_joy.on_touch_move(touch): return True
        if self.aim_joy.on_touch_move(touch): return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.in_shop: return super().on_touch_up(touch)
        if self.move_joy.on_touch_up(touch): return True
        if self.aim_joy.on_touch_up(touch): return True
        return super().on_touch_up(touch)

class MainMenu(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        layout = BoxLayout(orientation='vertical', size_hint=(0.6, 0.6), pos_hint={'center_x': 0.5, 'center_y': 0.5}, spacing=20, padding=50)
        
        title = Label(text="2D STRIKE CLONE", font_size='50sp', color=(1, 0.6, 0, 1), size_hint=(1, 0.3))
        layout.add_widget(title)
        
        btn_start = Button(text="ОДИНОЧНАЯ ИГРА", font_size='26sp', background_color=(0.8, 0.4, 0, 1))
        btn_start.bind(on_press=self.start_game)
        layout.add_widget(btn_start)
        
        btn_exit = Button(text="ВЫХОД", font_size='26sp', background_color=(0.8, 0.4, 0, 1))
        btn_exit.bind(on_press=App.get_running_app().stop)
        layout.add_widget(btn_exit)
        
        self.add_widget(layout)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def start_game(self, instance):
        self.clear_widgets()
        self.canvas.clear()
        game = Game()
        
        hud = BoxLayout(size_hint=(1, 0.12), pos_hint={'top': 1}, padding=20, spacing=20)
        
        self.money_label = Label(text="800 $", font_size='26sp', color=(0,1,0,1))
        self.hp_label = Label(text="HP: 100 | Броня: 0", font_size='26sp', color=(1,0,0,1))
        self.weapon_label = Label(text="Пистолет 15/120", font_size='26sp', color=(1,1,1,1))
        self.kills_label = Label(text="Убито: 0", font_size='26sp', color=(1,1,1,1))
        
        hud.add_widget(self.money_label)
        hud.add_widget(self.hp_label)
        hud.add_widget(self.weapon_label)
        hud.add_widget(self.kills_label)
        
        game.add_widget(game.move_joy)
        game.add_widget(game.aim_joy)
        game.add_widget(hud)
        
        self.add_widget(game)
        self.game_ref = game
        
        Clock.schedule_interval(self.update_hud, 0.1)

    def update_hud(self, dt):
        if hasattr(self, 'game_ref'):
            g = self.game_ref
            self.money_label.text = f"{g.money} $"
            self.hp_label.text = f"HP: {int(g.player_hp)} | Броня: {int(g.player_armor)}"
            self.weapon_label.text = f"{WEAPONS[g.player_weapon]['name']} {g.current_ammo}/{WEAPONS[g.player_weapon]['max_ammo']}"
            self.kills_label.text = f"Убито: {g.kills}"

class ShooterApp(App):
    def build(self):
        Window.clearcolor = (0, 0, 0, 1)
        return MainMenu()

if __name__ == "__main__":
    ShooterApp().run()
