import pygame
import pymunk
import numpy as np
import random
import matplotlib.pyplot as plt
from collections import deque

# Pygame-Initialisierung
pygame.init()

# Bildschirmgröße
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("TideFlow Nexus - Offshore Simulation")

# Farben
WHITE = (255, 255, 255)
BLUE = (0, 102, 204)
DARK_BLUE = (0, 51, 102)
GRAY = (160, 160, 160)
YELLOW = (1.0, 0.8, 0.0)
RED = (255, 50, 50)
BLACK = (0, 0, 0)

# Plattform-Koordinaten
PLATFORM_WIDTH, PLATFORM_HEIGHT = 500, 40
PLATFORM_X, PLATFORM_Y = (WIDTH - PLATFORM_WIDTH) // 2, 180

# Säulen-Daten
NUM_COLUMNS = 6
COLUMN_RADIUS = 30
COLUMN_HEIGHT = 200
COLUMN_SPACING = PLATFORM_WIDTH // NUM_COLUMNS
COLUMN_Y = HEIGHT - 100

# Bohrturm & Bohrkopf
BOHRTURM_X = PLATFORM_X + PLATFORM_WIDTH // 2
BOHRTURM_Y = PLATFORM_Y - 50
BOHRKOPF_Y = BOHRTURM_Y + 50
bohrtiefe = 0  # Fortschritt des Bohrens in Metern
bohrgeschwindigkeit = 0.5  # Geschwindigkeit des Bohrprozesses

# Physik-Engine
space = pymunk.Space()
space.gravity = (0, 1000)

# **Statische Säulen als Verankerung**
column_bodies = []
for i in range(NUM_COLUMNS):
    x = PLATFORM_X + (i + 0.5) * COLUMN_SPACING
    column_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    column_body.position = (x, COLUMN_Y + COLUMN_HEIGHT // 2)
    column_shape = pymunk.Poly.create_box(column_body, (COLUMN_RADIUS, COLUMN_HEIGHT))
    space.add(column_body, column_shape)
    column_bodies.append(column_body)

# **Dynamische Plattform**
platform_body = pymunk.Body(10, pymunk.moment_for_box(10, (PLATFORM_WIDTH, PLATFORM_HEIGHT)), body_type=pymunk.Body.DYNAMIC)
platform_body.position = (PLATFORM_X + PLATFORM_WIDTH // 2, PLATFORM_Y)
platform_shape = pymunk.Poly.create_box(platform_body, (PLATFORM_WIDTH, PLATFORM_HEIGHT))
space.add(platform_body, platform_shape)

# **Pin Joints: Plattform fest mit Säulen verbinden**
for column_body in column_bodies:
    pin_joint = pymunk.PinJoint(platform_body, column_body, (0, 0), (0, COLUMN_HEIGHT // 2))
    space.add(pin_joint)

# Strömungs- & Wetterparameter
wave_amplitude = 15
wave_frequency = 0.02
current_speed = 2.0  
wind_speed = 0.0  
temperature = 15.0  
storm_intensity = 0  
material_fatigue = 0  
ölförderung = 0  # Menge des geförderten Öls

# Energieproduktion Historie für Graphen
energy_history = deque(maxlen=100)

# **Energieproduktion berechnen**
def energy_output(speed, temp):
    efficiency_factor = 1 - 0.002 * abs(temp - 20)
    return round(5 * speed**2 * efficiency_factor, 2)

# Matplotlib Setup für Live-Graph
plt.ion()
fig, ax = plt.subplots()
ax.set_xlabel("Zeit")
ax.set_ylabel("Energie (kW)")
ax.set_title("Energieproduktion über Zeit")
energy_line, = ax.plot([], [], color=YELLOW)

# Haupt-Simulationsschleife
running = True
time_step = 0
while running:
    screen.fill(DARK_BLUE)

    # **Wellenbewegung wirkt auf Plattform & Säulen**
    wave_force = np.sin(wave_frequency * time_step) * wave_amplitude * 2000
    platform_body.apply_force_at_local_point((wave_force, 0), (0, 0))

    # **Wind beeinflusst Plattformneigung leicht**
    tilt_force = wind_speed * 1000
    platform_body.apply_force_at_local_point((tilt_force, 0), (PLATFORM_WIDTH // 2, 0))

    # **Unwetter & Materialermüdung simulieren**
    if random.random() < 0.01:
        storm_intensity = random.uniform(2, 8)
        wind_speed += storm_intensity
    wind_speed *= 0.98  

    material_fatigue += (current_speed * 0.001)  

    # Temperatur dynamisch verändern
    temperature += random.uniform(-0.1, 0.1)

    # **Bohrkopf bewegt sich nach unten**
    if bohrtiefe < 5000:  # Max. 5000m
        bohrtiefe += bohrgeschwindigkeit
        ölförderung = bohrtiefe * 0.002  # Öl steigt mit der Tiefe
    else:
        ölförderung = min(ölförderung + 0.1, 50)  # Maximal 50 Barrel pro Sekunde

    # **Ölförderung steigt, sobald der Bohrer tief genug ist**
    if bohrtiefe > 1000:
        ölförderung += 0.05

    # Wasser zeichnen (höhere Linie)
    water_level = HEIGHT - 120 + wave_amplitude * np.sin(wave_frequency * time_step)
    pygame.draw.rect(screen, BLUE, (0, water_level, WIDTH, HEIGHT - water_level))

    # Plattform zeichnen
    pygame.draw.rect(screen, GRAY, (
        int(platform_body.position.x - PLATFORM_WIDTH // 2),
        int(platform_body.position.y - PLATFORM_HEIGHT // 2),
        PLATFORM_WIDTH, PLATFORM_HEIGHT))

    # Bohrturm zeichnen
    pygame.draw.rect(screen, BLACK, (BOHRTURM_X - 15, BOHRTURM_Y, 30, 80))
    
    # Bohrkopf zeichnen
    pygame.draw.circle(screen, RED, (BOHRTURM_X, int(BOHRKOPF_Y + bohrtiefe * 0.05)), 10)

    # Energieproduktion anzeigen
    power = energy_output(current_speed, temperature)
    font = pygame.font.Font(None, 20)
    text = font.render(f"Energie: {power} kW", True, YELLOW)
    screen.blit(text, (20, 90))

    # Öl-Förderung anzeigen
    oil_text = font.render(f"Ölförderung: {ölförderung:.2f} Barrel/s", True, WHITE)
    screen.blit(oil_text, (20, 130))

    # Wetteranzeige
    temp_text = font.render(f"Temperatur: {temperature:.1f}°C", True, WHITE)
    wind_text = font.render(f"Windstärke: {wind_speed:.1f} m/s", True, WHITE)
    fatigue_text = font.render(f"Materialermüdung: {material_fatigue:.3f}", True, RED)
    
    screen.blit(temp_text, (20, 50))
    screen.blit(wind_text, (20, 70))
    screen.blit(fatigue_text, (20, 110))

    # Physik-Simulation aktualisieren
    space.step(1 / 60.0)

    # Ereignisverarbeitung
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    pygame.display.flip()
    time_step += 1
    pygame.time.delay(30)

pygame.quit()
plt.ioff()
plt.show()