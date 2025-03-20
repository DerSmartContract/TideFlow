import pygame
import pymunk
import numpy as np
import random
import matplotlib.pyplot as plt
from collections import deque
import math
import time

# Pygame-Initialisierung
pygame.init()

# Bildschirmgröße
WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("TideFlow Nexus - Erweiterte Offshore-Simulation")

# Farben für Pygame (RGB 0-255)
WHITE = (255, 255, 255)
BLUE = (0, 102, 204)
DARK_BLUE = (0, 51, 102)
LIGHT_BLUE = (100, 150, 255)
GRAY = (160, 160, 160)
DARK_GRAY = (100, 100, 100)
YELLOW = (255, 204, 0)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLACK = (0, 0, 0)
BROWN = (139, 69, 19)

# Farben für Matplotlib (RGB 0-1)
YELLOW_MPL = (1.0, 0.8, 0.0)  # Entspricht YELLOW für Matplotlib
BLACK_MPL = (0.0, 0.0, 0.0)   # Entspricht BLACK für Matplotlib

# Plattform-Koordinaten
PLATFORM_WIDTH, PLATFORM_HEIGHT = 500, 40
PLATFORM_X, PLATFORM_Y = (WIDTH - PLATFORM_WIDTH) // 2, 180

# Säulen-Daten
NUM_COLUMNS = 6
COLUMN_RADIUS = 30
COLUMN_HEIGHT = 250
COLUMN_SPACING = PLATFORM_WIDTH // NUM_COLUMNS
COLUMN_Y = HEIGHT - 120

# Bohrturm & Bohrkopf
BOHRTURM_X = PLATFORM_X + PLATFORM_WIDTH // 2
BOHRTURM_Y = PLATFORM_Y - 50
BOHRTURM_WIDTH, BOHRTURM_HEIGHT = 60, 80
BOHRKOPF_Y = BOHRTURM_Y + 50
bohrtiefe = 0  # Fortschritt des Bohrens in Metern
bohrgeschwindigkeit = 0.5  # Geschwindigkeit des Bohrprozesses
bohrer_verschleiss = 0  # Verschleiß des Bohrkopfes

# Geologische Schichten
SCHICHTEN = [
    {"tiefe": 0, "name": "Wasser", "farbe": BLUE, "widerstand": 1, "oelgehalt": 0},
    {"tiefe": 300, "name": "Sediment", "farbe": BROWN, "widerstand": 3, "oelgehalt": 0.1},
    {"tiefe": 1000, "name": "Sandstein", "farbe": (194, 178, 128), "widerstand": 8, "oelgehalt": 0.3},
    {"tiefe": 2000, "name": "Ölreservoir", "farbe": (50, 50, 50), "widerstand": 5, "oelgehalt": 1.0},
    {"tiefe": 3500, "name": "Grundgestein", "farbe": (100, 100, 100), "widerstand": 15, "oelgehalt": 0.2}
]

# Physik-Engine
space = pymunk.Space()
space.gravity = (0, 1000)

# Statische Säulen als Verankerung
column_bodies = []
column_shapes = []
column_health = []  # Gesundheitszustand der Säulen

for i in range(NUM_COLUMNS):
    x = PLATFORM_X + (i + 0.5) * COLUMN_SPACING
    column_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    column_body.position = (x, COLUMN_Y + COLUMN_HEIGHT // 2)
    column_shape = pymunk.Poly.create_box(column_body, (COLUMN_RADIUS, COLUMN_HEIGHT))
    column_shape.elasticity = 0.5
    column_shape.friction = 0.7
    space.add(column_body, column_shape)
    column_bodies.append(column_body)
    column_shapes.append(column_shape)
    column_health.append(100.0)  # 100% Gesundheit zu Beginn

# Dynamische Plattform
platform_body = pymunk.Body(100, pymunk.moment_for_box(100, (PLATFORM_WIDTH, PLATFORM_HEIGHT)))
platform_body.position = (PLATFORM_X + PLATFORM_WIDTH // 2, PLATFORM_Y)
platform_shape = pymunk.Poly.create_box(platform_body, (PLATFORM_WIDTH, PLATFORM_HEIGHT))
platform_shape.elasticity = 0.4
platform_shape.friction = 0.5
space.add(platform_body, platform_shape)

# Dämpfungs-Federn statt Pin-Joints für realistischere Bewegung
springs = []
for i, column_body in enumerate(column_bodies):
    spring = pymunk.DampedSpring(
        platform_body, column_body,
        ((-PLATFORM_WIDTH // 2) + (i + 0.5) * COLUMN_SPACING, 0), 
        (0, -COLUMN_HEIGHT // 2),
        0, 8000, 500)  # Länge, Steifheit, Dämpfung
    space.add(spring)
    springs.append(spring)

# Strömungs- & Wetterparameter
wave_amplitude = 15
wave_frequency = 0.01
current_speed = 2.0  
wind_speed = 5.0
wind_direction = 0  # In Grad (0 = Ost, 90 = Nord, usw.)
temperature = 15.0  
storm_intensity = 0  
material_fatigue = 0  
oelfoerderung = 0  # Menge des geförderten Öls
reservoir_druck = 100.0  # Anfangsdruck im Reservoir

# Tageszeit und Wettersimulation
tageszeit = 0  # 0-24 Stunden
wetterbedingungen = {
    "regen": 0,  # 0-10 Skala
    "nebel": 0,  # 0-10 Skala
    "wolken": 3  # 0-10 Skala
}

# Energieproduktion Historie für Graphen
energy_history = deque(maxlen=200)
oil_history = deque(maxlen=200)

# Wind-Turbinen auf der Plattform
class WindTurbine:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 20
        self.blades_rotation = 0
        self.efficiency = 0.9
        self.health = 100
    
    def update(self, wind_speed, wind_direction):
        # Rotationsgeschwindigkeit basierend auf Wind und Ausrichtung
        wind_factor = wind_speed * abs(math.cos(math.radians(wind_direction)))
        self.blades_rotation += wind_factor * 5
        if self.blades_rotation > 360:
            self.blades_rotation -= 360
        
        # Turbine wird durch extreme Winde beschädigt
        if wind_speed > 25:
            self.health -= 0.1
            self.efficiency = max(0.5, self.health / 100)
    
    def draw(self, surface):
        # Turm
        pygame.draw.rect(surface, DARK_GRAY, (self.x - 5, self.y - 30, 10, 30))
        
        # Propellergehäuse
        pygame.draw.circle(surface, GRAY, (self.x, self.y - 30), 8)
        
        # Propellerblätter
        for i in range(3):
            angle = math.radians(self.blades_rotation + i * 120)
            end_x = self.x + math.cos(angle) * self.radius
            end_y = (self.y - 30) + math.sin(angle) * self.radius
            pygame.draw.line(surface, WHITE, (self.x, self.y - 30), (end_x, end_y), 3)

# Wellengenerator unterhalb der Plattform
class WaveGenerator:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 20
        self.efficiency = 0.85
        self.health = 100
    
    def update(self, wave_amplitude):
        # Generatoreffizienz sinkt mit der Zeit
        self.health -= 0.005
        self.efficiency = max(0.6, self.health / 100)
    
    def draw(self, surface):
        pygame.draw.rect(surface, DARK_GRAY, (self.x - self.width//2, self.y - self.height//2, 
                                             self.width, self.height))
        # Statusanzeige
        health_color = (int(255 * (1 - self.health/100)), int(255 * self.health/100), 0)
        pygame.draw.rect(surface, health_color, (self.x - self.width//2, self.y - self.height//2 - 5, 
                                               self.width * self.health/100, 3))

# Erstelle Windturbinen
wind_turbines = [
    WindTurbine(PLATFORM_X + 100, PLATFORM_Y),
    WindTurbine(PLATFORM_X + PLATFORM_WIDTH - 100, PLATFORM_Y)
]

# Erstelle Wellengeneratoren
wave_generators = [
    WaveGenerator(PLATFORM_X + 150, PLATFORM_Y + PLATFORM_HEIGHT//2 + 20),
    WaveGenerator(PLATFORM_X + PLATFORM_WIDTH - 150, PLATFORM_Y + PLATFORM_HEIGHT//2 + 20)
]

# Energieproduktion berechnen
def energy_output(wind_turbines, wave_generators, wind_speed, wave_factor):
    # Wind-Energie
    wind_energy = sum([turbine.efficiency * wind_speed**2 * 0.2 for turbine in wind_turbines])
    
    # Wellen-Energie
    wave_energy = sum([gen.efficiency * wave_factor**2 * 15 for gen in wave_generators])
    
    return round(wind_energy + wave_energy, 2)

# Aktuelle geologische Schicht ermitteln
def get_current_layer(tiefe):
    for i in range(len(SCHICHTEN)-1, -1, -1):
        if tiefe >= SCHICHTEN[i]["tiefe"]:
            return SCHICHTEN[i]
    return SCHICHTEN[0]

# Gezeitenfunktion
def tide_level(time):
    # Einfache Sinusfunktion für Gezeiten (12-Stunden-Zyklus)
    return 30 * math.sin(time * 0.0001)

# Matplotlib Setup für Live-Graph
plt.ion()
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))
ax1.set_xlabel("Zeit")
ax1.set_ylabel("Energie (kW)")
ax1.set_title("Energieproduktion")
energy_line, = ax1.plot([], [], color=YELLOW_MPL)  # Hier Matplotlib-Farbwert verwenden

ax2.set_xlabel("Zeit")
ax2.set_ylabel("Öl (Barrel/s)")
ax2.set_title("Ölförderung")
oil_line, = ax2.plot([], [], color=BLACK_MPL)  # Hier Matplotlib-Farbwert verwenden

# Display-Oberfläche für Statistiken
stats_surface = pygame.Surface((350, 200))

# Uhr für die Zeitmessung
clock = pygame.time.Clock()
last_time = time.time()
fps_history = deque(maxlen=30)

# Haupt-Simulationsschleife
running = True
time_step = 0
while running:
    # FPS berechnen
    current_time = time.time()
    dt = current_time - last_time
    last_time = current_time
    if dt > 0:
        fps = 1.0 / dt
        fps_history.append(fps)
    
    screen.fill(DARK_BLUE)
    
    # Tageszeit aktualisieren
    tageszeit = (tageszeit + 0.01) % 24
    
    # Himmelsfarbe je nach Tageszeit anpassen
    if 6 <= tageszeit < 18:  # Tag
        sky_color = (100, 150, 255)
    elif 5 <= tageszeit < 6 or 18 <= tageszeit < 19:  # Dämmerung
        sky_color = (255, 150, 100)
    else:  # Nacht
        sky_color = (20, 20, 50)
    
    # Himmel zeichnen
    pygame.draw.rect(screen, sky_color, (0, 0, WIDTH, COLUMN_Y - 50))
    
    # Zufällige Wetteränderungen
    if random.random() < 0.005:
        wetterbedingungen["wolken"] = min(10, max(0, wetterbedingungen["wolken"] + random.uniform(-2, 2)))
        wetterbedingungen["regen"] = min(10, max(0, wetterbedingungen["regen"] + random.uniform(-1, 1)))
        wetterbedingungen["nebel"] = min(10, max(0, wetterbedingungen["nebel"] + random.uniform(-0.5, 0.5)))
    
    # Wetter zeichnen
    # Wolken
    if wetterbedingungen["wolken"] > 2:
        for i in range(int(wetterbedingungen["wolken"])):
            cloud_x = (time_step * 0.5 + i * 200) % (WIDTH + 200) - 100
            cloud_y = 50 + i * 20
            cloud_radius = 30 + i * 5
            pygame.draw.circle(screen, (220, 220, 220), (int(cloud_x), cloud_y), cloud_radius)
    
    # Regen
    if wetterbedingungen["regen"] > 3:
        for i in range(int(wetterbedingungen["regen"] * 10)):
            rain_x = random.randint(0, WIDTH)
            rain_y = random.randint(0, COLUMN_Y)
            rain_length = random.randint(5, 15)
            pygame.draw.line(screen, LIGHT_BLUE, (rain_x, rain_y), 
                           (rain_x - 2, rain_y + rain_length), 1)
    
    # Mehrdimensionale Wellenbewegung
    wave_factor_x = abs(np.sin(wave_frequency * time_step))
    wave_factor_y = abs(np.sin(wave_frequency * time_step * 0.7))
    wave_force_x = wave_factor_x * wave_amplitude * 2000
    wave_force_y = wave_factor_y * wave_amplitude * 1000
    
    # Plattform reagiert auf Wellen und Wind
    wind_force = wind_speed * 100 * math.cos(math.radians(wind_direction))
    platform_body.apply_force_at_local_point((wave_force_x + wind_force, wave_force_y), (0, 0))
    
    # Unwetter & Materialermüdung simulieren
    if random.random() < 0.002:
        storm_intensity = random.uniform(2, 15)
        wind_speed += storm_intensity
        wind_direction += random.uniform(-30, 30)
        wave_amplitude += storm_intensity * 0.3
    
    # Wetterfaktoren abklingen lassen
    wind_speed = max(2.0, wind_speed * 0.995)
    wave_amplitude = max(10.0, wave_amplitude * 0.998)
    
    # Wind-Richtung ändern
    wind_direction = (wind_direction + random.uniform(-1, 1)) % 360
    
    # Materialermüdung für Säulen individuell berechnen
    for i, health in enumerate(column_health):
        # Ermüdung basierend auf Wellenbelastung und Alter
        stress_factor = (wave_factor_x + wave_factor_y) * 0.01
        column_health[i] -= stress_factor + 0.001  # Grundlegende Alterung
        
        # Säulen reparieren wenn zu starke Beschädigung
        if column_health[i] < 50 and random.random() < 0.05:
            column_health[i] += 10  # Reparatur
    
    # Bohrkopf-Simulation
    current_layer = get_current_layer(bohrtiefe)
    if bohrtiefe < 5000:
        # Bohrgeschwindigkeit hängt vom Gesteinstyp ab
        effective_speed = bohrgeschwindigkeit / current_layer["widerstand"]
        if bohrer_verschleiss < 100:  # Bohrer ist noch funktionsfähig
            bohrtiefe += effective_speed
            bohrer_verschleiss += 0.01 * current_layer["widerstand"]
    
    # Öl-Förderung
    if bohrtiefe > SCHICHTEN[2]["tiefe"]:  # Nach dem Erreichen der ölhaltigen Schicht
        base_rate = current_layer["oelgehalt"] * 0.5
        oelfoerderung = base_rate * (reservoir_druck / 100)
        reservoir_druck = max(10, reservoir_druck - 0.01)  # Druck nimmt langsam ab
    
    # Bohrkopf-Reparatur wenn stark verschlissen
    if bohrer_verschleiss > 90 and random.random() < 0.1:
        bohrer_verschleiss = max(0, bohrer_verschleiss - 30)
    
    # Gezeiten-Effekt berechnen
    tide = tide_level(time_step)
    water_level = COLUMN_Y + tide

    # Welleneffekt auf Wasseroberfläche
    water_height = HEIGHT - water_level
    for x in range(0, WIDTH, 5):
        wave_y = water_level + wave_amplitude * 0.5 * math.sin(wave_frequency * (time_step + x * 0.2))
        pygame.draw.rect(screen, BLUE, (x, wave_y, 5, HEIGHT - wave_y))
    
    # Unterwasser-Sedimentschichten zeichnen
    for i, schicht in enumerate(SCHICHTEN):
        if schicht["tiefe"] > bohrtiefe:
            layer_y = water_level + 50 + schicht["tiefe"] * 0.05  # Skalierung für die Anzeige
            if layer_y < HEIGHT:
                pygame.draw.rect(screen, schicht["farbe"], (0, layer_y, WIDTH, HEIGHT - layer_y))
    
    # Bohrloch zeichnen
    if bohrtiefe > 0:
        pygame.draw.line(screen, DARK_GRAY, 
                       (BOHRTURM_X, BOHRKOPF_Y),
                       (BOHRTURM_X, BOHRKOPF_Y + min(HEIGHT - BOHRKOPF_Y, bohrtiefe * 0.05)), 4)
    
    # Aktueller Bohrkopf
    current_y = BOHRKOPF_Y + min(HEIGHT - BOHRKOPF_Y, bohrtiefe * 0.05)
    if current_y < HEIGHT:
        drill_color = GREEN if bohrer_verschleiss < 50 else (
            YELLOW if bohrer_verschleiss < 80 else RED)
        pygame.draw.circle(screen, drill_color, (BOHRTURM_X, int(current_y)), 5)
    
    # Windturbinen aktualisieren und zeichnen
    for turbine in wind_turbines:
        turbine.update(wind_speed, wind_direction)
        turbine.draw(screen)
    
    # Wellengeneratoren aktualisieren und zeichnen
    for generator in wave_generators:
        generator.update(wave_amplitude)
        generator.draw(screen)
    
    # Säulen mit Gesundheitsanzeige zeichnen
    for i, column_body in enumerate(column_bodies):
        health = column_health[i]
        health_color = (int(255 * (1 - health/100)), int(255 * health/100), 0)
        
        pygame.draw.rect(screen, GRAY, (
            int(column_body.position.x - COLUMN_RADIUS),
            int(column_body.position.y - COLUMN_HEIGHT // 2),
            2 * COLUMN_RADIUS, COLUMN_HEIGHT))
            
        # Gesundheitsbalken
        pygame.draw.rect(screen, health_color, (
            int(column_body.position.x - COLUMN_RADIUS),
            int(column_body.position.y - COLUMN_HEIGHT // 2) - 10,
            int(2 * COLUMN_RADIUS * health / 100), 5))
    
    # Plattform zeichnen
    pygame.draw.rect(screen, GRAY, (
        int(platform_body.position.x - PLATFORM_WIDTH // 2),
        int(platform_body.position.y - PLATFORM_HEIGHT // 2),
        PLATFORM_WIDTH, PLATFORM_HEIGHT))
    
    # Bohrturm zeichnen
    pygame.draw.rect(screen, DARK_GRAY, (
        BOHRTURM_X - BOHRTURM_WIDTH // 2,
        BOHRTURM_Y - BOHRTURM_HEIGHT,
        BOHRTURM_WIDTH, BOHRTURM_HEIGHT))
    
    # Energieberechnung
    power = energy_output(wind_turbines, wave_generators, wind_speed, wave_factor_x)
    
    # Statistiken aktualisieren und anzeigen
    stats_surface.fill((0, 0, 0, 150))
    font = pygame.font.Font(None, 24)
    
    stats_texts = [
        f"Energie: {power} kW",
        f"Ölförderung: {oelfoerderung:.2f} Barrel/s",
        f"Bohrtiefe: {bohrtiefe:.1f}m",
        f"Aktuell: {current_layer['name']}",
        f"Wellenhöhe: {wave_amplitude:.1f}m",
        f"Wind: {wind_speed:.1f} km/h, {wind_direction:.0f}°",
        f"Reservoirdruck: {reservoir_druck:.1f}%",
        f"Bohrkopf: {100-bohrer_verschleiss:.0f}%",
        f"Tageszeit: {int(tageszeit)}:{int((tageszeit % 1) * 60):02d}",
        f"FPS: {sum(fps_history)/len(fps_history):.1f}" if fps_history else "FPS: -"
    ]
    
    for i, text in enumerate(stats_texts):
        color = YELLOW if "Energie" in text else (
                RED if "Bohrkopf" in text and bohrer_verschleiss > 70 else WHITE)
        text_surface = font.render(text, True, color)
        stats_surface.blit(text_surface, (10, 10 + i * 25))
    
    screen.blit(stats_surface, (10, 10))
    
    # Graphen aktualisieren
    energy_history.append(power)
    oil_history.append(oelfoerderung)
    
    energy_line.set_xdata(np.arange(len(energy_history)))
    energy_line.set_ydata(list(energy_history))
    ax1.relim()
    ax1.autoscale_view()
    
    oil_line.set_xdata(np.arange(len(oil_history)))
    oil_line.set_ydata(list(oil_history))
    ax2.relim()
    ax2.autoscale_view()
    
    if time_step % 10 == 0:  # Update alle 10 Frames, um Effizienz zu erhöhen
        plt.pause(0.001)
    
    # Physik-Simulation aktualisieren
    space.step(1 / 60.0)
    
    # Ereignisverarbeitung
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # Tastendruck für Steuerung
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                bohrgeschwindigkeit += 0.2
            elif event.key == pygame.K_DOWN:
                bohrgeschwindigkeit = max(0.1, bohrgeschwindigkeit - 0.2)
            elif event.key == pygame.K_r:
                # Bohrkopf reparieren
                bohrer_verschleiss = 0
            elif event.key == pygame.K_s:
                # Sturm auslösen
                storm_intensity = random.uniform(10, 20)
                wind_speed += storm_intensity
                wave_amplitude += storm_intensity * 0.5
    
    pygame.display.flip()
    time_step += 1
    clock.tick(60)  # Begrenze auf 60 FPS

pygame.quit()
plt.ioff()
plt.close()