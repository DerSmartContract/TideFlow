
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
pygame.display.set_caption("Realistische Offshore-Plattform Simulation")

# Farben
WHITE = (255, 255, 255)
BLUE = (0, 102, 204)
DARK_BLUE = (0, 51, 102)
GRAY = (160, 160, 160)
# Für Matplotlib-Farben besser als RGB-Werte zwischen 0 und 1
YELLOW = (1.0, 0.8, 0.0)  
RED = (255, 50, 50)

# Plattform-Koordinaten
PLATFORM_WIDTH, PLATFORM_HEIGHT = 500, 40
PLATFORM_X, PLATFORM_Y = (WIDTH - PLATFORM_WIDTH) // 2, 100

# Säulen-Daten
NUM_COLUMNS = 6
COLUMN_RADIUS = 30
COLUMN_HEIGHT = 200
COLUMN_SPACING = PLATFORM_WIDTH // NUM_COLUMNS
COLUMN_Y = PLATFORM_Y + PLATFORM_HEIGHT

# Physik-Engine
space = pymunk.Space()
space.gravity = (0, 1000)  # Schwerkraft nach unten

# Plattform als physikalisches Objekt mit realistischen Wellenkräften
platform_body = pymunk.Body(5, pymunk.moment_for_box(5, (PLATFORM_WIDTH, PLATFORM_HEIGHT)))
platform_body.position = (PLATFORM_X + PLATFORM_WIDTH // 2, PLATFORM_Y)
platform_shape = pymunk.Poly.create_box(platform_body, (PLATFORM_WIDTH, PLATFORM_HEIGHT))
platform_shape.friction = 0.8  # Realistische Reibung
space.add(platform_body, platform_shape)

# Strömungs- und Wetterparameter
wave_amplitude = 5
wave_frequency = 0.03
current_speed = 2.0  # m/s
wind_speed = 0.0  # m/s
temperature = 15.0  # °C
storm_intensity = 0  # Zufällige Unwetter-Ereignisse
material_fatigue = 0  # Simulation der strukturellen Belastung

# Energieproduktion Historie für Graphen
energy_history = deque(maxlen=100)

# Energieproduktion berechnen (mit Temperatureinfluss)
def energy_output(speed, temp):
    # Wirkungsgradverlust, wenn Temperatur von ~20 °C abweicht
    efficiency_factor = 1 - 0.002 * abs(temp - 20)
    return round(5 * speed**2 * efficiency_factor, 2)

# Matplotlib Setup für Live-Graph
plt.ion()
fig, ax = plt.subplots()
ax.set_xlabel("Zeit")
ax.set_ylabel("Energie (kW)")
ax.set_title("Energieproduktion über Zeit")

# >>> FIX HIER: color=YELLOW anstelle von YELLOW als dritten Parameter <<<
energy_line, = ax.plot([], [], color=YELLOW)

# Säulenpositionen berechnen
columns = [(PLATFORM_X + (i + 0.5) * COLUMN_SPACING, COLUMN_Y) for i in range(NUM_COLUMNS)]

# Haupt-Simulationsschleife
running = True
time_step = 0
while running:
    screen.fill(DARK_BLUE)  # Hintergrund

    # Unwetter & Materialermüdung simulieren
    if random.random() < 0.01:  # 1% Wahrscheinlichkeit für ein Sturmereignis
        storm_intensity = random.uniform(2, 8)
        wind_speed += storm_intensity  # Windböen verstärken
    wind_speed *= 0.98  # Langsames Abklingen nach Sturm

    material_fatigue += (current_speed * 0.001)  # Langsame Materialbelastung

    # Temperatur dynamisch verändern (kleine Zufallsschwankungen)
    temperature += random.uniform(-0.1, 0.1)

    # Wellenbewegung simulieren mit Wellendruck auf Plattform
    wave_force = np.sin(wave_frequency * time_step) * wave_amplitude * 2000
    platform_body.apply_force_at_local_point((wave_force, 0), (0, 0))

    # Wasser zeichnen
    water_level = HEIGHT - 100 + wave_amplitude * np.sin(wave_frequency * time_step)
    pygame.draw.rect(screen, BLUE, (0, water_level, WIDTH, HEIGHT - water_level))

    # Plattform zeichnen mit realistischer Bewegung
    pygame.draw.rect(
        screen,
        GRAY,
        (
            int(platform_body.position.x - PLATFORM_WIDTH // 2),
            int(platform_body.position.y - PLATFORM_HEIGHT // 2),
            PLATFORM_WIDTH,
            PLATFORM_HEIGHT
        )
    )

    # Säulen zeichnen
    for x, y in columns:
        pygame.draw.rect(screen, GRAY, (x - COLUMN_RADIUS, y, 2 * COLUMN_RADIUS, COLUMN_HEIGHT))

    # Strömungseinfluss auf Plattform
    platform_body.apply_force_at_local_point((current_speed * 3000, 0), (0, 0))

    # Spiralförmige Generatoren
    for x, y in columns:
        for j in range(COLUMN_HEIGHT // 10):
            spiral_x = x + np.sin(j * 0.5 + time_step * 0.1) * 6
            spiral_y = y + j * 10
            pygame.draw.circle(screen, YELLOW, (int(spiral_x), int(spiral_y)), 3)

    # Energieproduktion anzeigen
    power = energy_output(current_speed, temperature)
    font = pygame.font.Font(None, 20)
    text = font.render(f"{power} kW", True, YELLOW)
    screen.blit(text, (20, 90))

    # Wetteranzeige
    temp_text = font.render(f"Temperatur: {temperature:.1f}°C", True, WHITE)
    wind_text = font.render(f"Windstärke: {wind_speed:.1f} m/s", True, WHITE)
    fatigue_text = font.render(f"Materialermüdung: {material_fatigue:.3f}", True, RED)
    screen.blit(temp_text, (20, 50))
    screen.blit(wind_text, (20, 70))
    screen.blit(fatigue_text, (20, 110))

    # Benutzersteuerung
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        current_speed = max(0.5, current_speed - 0.1)
    if keys[pygame.K_RIGHT]:
        current_speed = min(5.0, current_speed + 0.1)
    if keys[pygame.K_UP]:
        wind_speed = min(5.0, wind_speed + 0.1)
    if keys[pygame.K_DOWN]:
        wind_speed = max(-5.0, wind_speed - 0.1)

    # Physik-Simulation aktualisieren
    space.step(1 / 60.0)

    # Energieverlauf aktualisieren
    energy_history.append(power)

    # Matplotlib Live-Update
    energy_line.set_xdata(np.arange(len(energy_history)))
    energy_line.set_ydata(list(energy_history))
    ax.relim()
    ax.autoscale_view()
    plt.pause(0.01)

    # Ereignisverarbeitung (Schließen des Fensters)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    pygame.display.flip()
    time_step += 1
    pygame.time.delay(30)

pygame.quit()
plt.ioff()
plt.show()
