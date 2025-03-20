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

# **Energieproduktion berechnen (jetzt abhängig von Wellenbewegung)**
def energy_output(speed, temp, wave_factor):
    efficiency_factor = 1 - 0.002 * abs(temp - 20)
    return round(5 * speed**2 * efficiency_factor * wave_factor, 2)  # Wellen verstärken Energieproduktion

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
    wave_factor = abs(np.sin(wave_frequency * time_step))  # Wellenstärke schwankt mit der Zeit
    wave_force = wave_factor * wave_amplitude * 2000
    platform_body.apply_force_at_local_point((wave_force, 0), (0, 0))

    # **Unwetter & Materialermüdung simulieren**
    if random.random() < 0.01:
        storm_intensity = random.uniform(2, 8)
        wind_speed += storm_intensity
    wind_speed *= 0.98  
    material_fatigue += (current_speed * 0.001)  

    # **Bohrkopf bewegt sich nach unten**
    if bohrtiefe < 5000:
        bohrtiefe += bohrgeschwindigkeit
        ölförderung = bohrtiefe * 0.002  # Öl steigt mit der Tiefe
    else:
        ölförderung = min(ölförderung + 0.1, 50)  # Maximal 50 Barrel pro Sekunde

    # **Ölförderung steigt, sobald der Bohrer tief genug ist**
    if bohrtiefe > 1000:
        ölförderung += 0.05

    # Wasser zeichnen
    water_level = HEIGHT - 120 + wave_amplitude * np.sin(wave_frequency * time_step)
    pygame.draw.rect(screen, BLUE, (0, water_level, WIDTH, HEIGHT - water_level))

    # Plattform zeichnen
    pygame.draw.rect(screen, GRAY, (
        int(platform_body.position.x - PLATFORM_WIDTH // 2),
        int(platform_body.position.y - PLATFORM_HEIGHT // 2),
        PLATFORM_WIDTH, PLATFORM_HEIGHT))

    # **Säulen wieder hinzufügen**
    for column_body in column_bodies:
        pygame.draw.rect(screen, GRAY, (
            int(column_body.position.x - COLUMN_RADIUS),
            int(column_body.position.y - COLUMN_HEIGHT // 2),
            2 * COLUMN_RADIUS, COLUMN_HEIGHT))

    # **Energieproduktion jetzt abhängig von Wellenbewegung**
    power = energy_output(current_speed, temperature, wave_factor)
    font = pygame.font.Font(None, 20)
    screen.blit(font.render(f"Energie: {power} kW", True, YELLOW), (20, 90))
    screen.blit(font.render(f"Ölförderung: {ölförderung:.2f} Barrel/s", True, WHITE), (20, 130))
    screen.blit(font.render(f"Materialermüdung: {material_fatigue:.3f}", True, RED), (20, 110))

    # **Matplotlib-Plot aktualisieren**
    energy_history.append(power)
    energy_line.set_xdata(np.arange(len(energy_history)))
    energy_line.set_ydata(list(energy_history))
    ax.relim()
    ax.autoscale_view()
    plt.pause(0.01)

    # **Physik-Simulation aktualisieren**
    space.step(1 / 60.0)

    # **Ereignisverarbeitung (Schließen des Fensters)**
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    pygame.display.flip()
    time_step += 1
    pygame.time.delay(30)

pygame.quit()
plt.ioff()
plt.show()